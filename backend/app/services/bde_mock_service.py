"""
services/bde_mock_service.py — Simulación del servicio externo CIRBE/ASNEF del BdE.

Implementa la clase `BdeMockService` que devuelve datos simulados de solvencia
patrimonial (CIRBE / ASNEF) basados en el DNI del cliente, leyendo del archivo
`bde.json` ubicado en la raíz del proyecto backend.

Este mock simula la consulta obligatoria al Banco de España que se activa
cuando Drools emite `REQUIERE_ACCION: CONSULTAR_CIRBE_ASNEF`.

En producción, este servicio sería reemplazado por la integración real
con los sistemas del BdE o con proveedores de datos crediticios autorizados.
"""

import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class BdeMockService:
    """
    Servicio de simulación del Banco de España (CIRBE / ASNEF).

    Carga el archivo `bde.json` en memoria al inicializarse y sirve
    datos de solvencia simulados basados en el DNI del cliente.

    Si el DNI no tiene un perfil específico en el mock, devuelve
    los valores por defecto del bloque `_default` (sin impagos ni deudas).

    Atributos de simulación por perfil:
        - tiene_impagos_activos: Si el cliente tiene impagos activos en ASNEF
        - importe_morosidad_asnef: Importe total de morosidad registrada (EUR)
        - empresa_avalada_concurso: Si la empresa avalada está en concurso de acreedores
        - deuda_cirbe_mensual: Cuota mensual de deudas en CIRBE (EUR/mes)
        - deuda_cirbe_total: Importe total de deudas en CIRBE (EUR)
    """

    def __init__(self) -> None:
        """
        Inicializa el servicio cargando los datos del archivo bde.json.

        El archivo se busca en la ruta configurada por `settings.bde_json_path`.
        Si no se encuentra, se lanza una excepción al inicio para fail-fast.
        """
        self._datos: dict = {}
        self._default: dict = {}
        self._cargar_datos()

    def _cargar_datos(self) -> None:
        """
        Carga y parsea el archivo bde.json en memoria.

        Raises:
            FileNotFoundError: Si el archivo bde.json no se encuentra.
            json.JSONDecodeError: Si el archivo no es JSON válido.
        """
        ruta_json = Path(settings.bde_json_path)

        if not ruta_json.exists():
            # Intentar ruta relativa a la raíz del proyecto
            ruta_alternativa = Path(__file__).parent.parent.parent / "bde.json"
            if ruta_alternativa.exists():
                ruta_json = ruta_alternativa
            else:
                raise FileNotFoundError(
                    f"No se encontró el archivo de datos BdE mock en: {ruta_json} "
                    f"ni en: {ruta_alternativa}"
                )

        with open(ruta_json, encoding="utf-8") as f:
            datos_completos = json.load(f)

        self._datos = datos_completos.get("bde_mock_data", {})
        self._default = datos_completos.get("_default", {})

        logger.info(
            "BdeMockService: Cargados %d perfiles de clientes desde %s",
            len(self._datos),
            ruta_json,
        )

    def consultar_por_dni(self, dni: str) -> dict:
        """
        Devuelve los datos de solvencia patrimonial simulados para un DNI dado.

        Si el DNI tiene un perfil específico en el mock, devuelve esos datos.
        En caso contrario, devuelve los valores por defecto (sin impagos).

        Args:
            dni: Documento Nacional de Identidad del cliente.

        Returns:
            dict con los campos:
                - tiene_impagos_activos (bool)
                - importe_morosidad_asnef (float)
                - empresa_avalada_concurso (bool | None)
                - deuda_cirbe_mensual (float)
                - deuda_cirbe_total (float)
                - fuente (str)
                - fecha_consulta (str)
        """
        dni_normalizado = dni.upper().strip()

        if dni_normalizado in self._datos:
            perfil = self._datos[dni_normalizado]
            logger.info(
                "BdeMockService: Perfil específico encontrado para DNI=%s",
                dni_normalizado,
            )
        else:
            perfil = dict(self._default)
            perfil["dni"] = dni_normalizado
            logger.info(
                "BdeMockService: DNI=%s no catalogado — usando perfil por defecto (sin impagos)",
                dni_normalizado,
            )

        # Devolver solo los campos relevantes para el InformationState
        return {
            "consultado": True,
            "tiene_impagos_activos": perfil.get("tiene_impagos_activos", False),
            "importe_morosidad_asnef": perfil.get("importe_morosidad_asnef", 0.0),
            "empresa_avalada_concurso": perfil.get("empresa_avalada_concurso"),
            "deuda_cirbe_mensual": perfil.get("deuda_cirbe_mensual", 0.0),
            "deuda_cirbe_total": perfil.get("deuda_cirbe_total", 0.0),
            "fuente": perfil.get("fuente", "CIRBE / ASNEF - Simulación BdE"),
            "fecha_consulta": perfil.get("fecha_consulta", "2026-01-15"),
        }

    def listar_dnis_catalogados(self) -> list[str]:
        """
        Devuelve la lista de DNIs que tienen un perfil específico en el mock.

        Returns:
            list[str]: Lista de DNIs catalogados en bde.json.
        """
        return list(self._datos.keys())
