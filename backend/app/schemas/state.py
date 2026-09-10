"""
schemas/state.py — Esquema canónico del Information State del sistema.

Define la estructura formal `InformationState` que representa la verdad
del sistema en cualquier instante del diálogo. Toda la lógica de negocio
opera sobre este objeto; el LLM solo lo lee en modo solo lectura (NLG).

Basado en el contrato de datos definido en SYSTEM_SPEC.md § 2.
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class EstadoEvaluacion(str, Enum):
    """Estados posibles de la evaluación Drools."""

    EN_PROCESO = "EN_PROCESO"
    REQUIERE_DATOS = "REQUIERE_DATOS"
    REQUIERE_ACCION = "REQUIERE_ACCION"
    REQUIERE_SUPERVISION_HUMANA = "REQUIERE_SUPERVISION_HUMANA"
    DENEGADO = "DENEGADO"
    APROBADO = "APROBADO"


class DatosUsuario(BaseModel):
    """
    Datos extraídos del mensaje del usuario por el componente NLU.
    Se van actualizando turno a turno con los nuevos valores extraídos.
    """

    intencion_principal: str | None = Field(
        default=None,
        description="Intención detectada: SOLICITAR_PRESTAMO | CONSULTAR_DUDA | SALUDAR | OTRA",
    )
    cantidad_solicitada: float | None = Field(
        default=None,
        description="Importe del préstamo solicitado en EUR",
    )
    plazo_meses: int | None = Field(
        default=None,
        description="Plazo de devolución en meses",
    )
    proposito: str | None = Field(
        default=None,
        description=(
            "Propósito del préstamo: VEHICULO | REFORMA | ESTUDIOS | SALUD | OTRO | "
            "CRIPTOMONEDAS | APUESTAS | REFINANCIACION_INFORMAL"
        ),
    )
    gastos_fijos_mensuales: float | None = Field(
        default=None,
        description="Gastos fijos mensuales declarados en EUR (sin incluir deudas)",
    )
    deuda_declarada: float | None = Field(
        default=None,
        description="Importe total de deudas externas declaradas por el usuario en EUR",
    )
    duda_catch_all: str = Field(
        default="NINGUNA",
        description=(
            "Tipo de duda: NINGUNA | REQUISITOS_APROBACION | "
            "CONDICIONES_CANCELACION | NORMATIVA_SOLVENCIA | FUERA_DE_DOMINIO"
        ),
    )


class DatosCoreBancario(BaseModel):
    """
    Datos del perfil bancario core del cliente, recuperados de la tabla `clientes`.
    Se cargan una sola vez en el primer turno y se persisten en el estado.
    """

    cliente_id: str | None = Field(default=None)
    nombre: str | None = Field(default=None, description="Nombre completo del cliente")
    dni: str | None = Field(default=None)
    edad: int | None = Field(default=None)
    ingresos_netos_mensuales: float | None = Field(default=None)
    antiguedad_meses: int | None = Field(default=None)
    deuda_interna_banco_mensual: float | None = Field(
        default=None,
        description="Cuota mensual de deudas activas con este banco (EUR/mes)",
    )
    es_avalista: bool = Field(default=False)
    empresa_avalada_cif: str | None = Field(default=None)


class DatosExternosBde(BaseModel):
    """
    Datos de solvencia externa obtenidos del mock CIRBE/ASNEF del Banco de España.
    Se consultan condicionalmente cuando Drools emite REQUIERE_ACCION.
    """

    consultado: bool = Field(
        default=False,
        description="Indica si ya se realizó la consulta al BdE mock",
    )
    tiene_impagos_activos: bool = Field(default=False)
    importe_morosidad_asnef: float = Field(default=0.0)
    empresa_avalada_concurso: bool | None = Field(default=None)
    deuda_cirbe_mensual: float = Field(default=0.0)
    deuda_cirbe_total: float = Field(default=0.0)


class CalculosDerivados(BaseModel):
    """
    Cálculos financieros derivados ejecutados por Drools.
    Se actualizan en cada evaluación (paso 3 y opcionalmente paso 5).
    """

    cuota_estimada: float | None = Field(
        default=None,
        description="cantidad_solicitada / plazo_meses",
    )
    ratio_endeudamiento: float | None = Field(
        default=None,
        description=(
            "(cuota_estimada + gastos_fijos + deuda_interna + deuda_cirbe) "
            "/ ingresos_netos_mensuales"
        ),
    )
    remanente_subsistencia: float | None = Field(
        default=None,
        description="ingresos_netos - total_compromisos_mensuales",
    )
    edad_al_vencimiento: int | None = Field(
        default=None,
        description="edad + (plazo_meses / 12)",
    )


class EvaluacionDrools(BaseModel):
    """
    Resultado de la evaluación del motor de reglas Drools.
    Representa la decisión normativa auditada del sistema simbólico.
    """

    estado: EstadoEvaluacion = Field(default=EstadoEvaluacion.EN_PROCESO)
    reglas_disparadas: list[str] = Field(default_factory=list)
    accion_requerida: str | None = Field(default=None)
    dato_faltante: str | None = Field(default=None)
    articulo_normativo: str | None = Field(default=None)
    texto_legal: str | None = Field(default=None)
    tono_mensaje: str | None = Field(
        default=None,
        description="Tono recomendado para la respuesta NLG según la regla disparada",
    )


class InformationState(BaseModel):
    """
    Estado canónico del sistema en un instante dado del diálogo.

    Es el objeto central del paradigma ISU (Information State Update):
    toda la lógica de negocio opera sobre él, y el LLM lo recibe en modo
    solo lectura para generar la respuesta natural al usuario.

    Se inicializa vacío al comienzo de cada sesión y se actualiza
    paso a paso durante el pipeline de 6 micro-acciones.
    """

    session_id: str = Field(..., description="UUID de la sesión conversacional")
    turn_id: int = Field(default=1, description="Número de turno conversacional")
    datos_usuario: DatosUsuario = Field(default_factory=DatosUsuario)
    datos_core_bancario: DatosCoreBancario = Field(default_factory=DatosCoreBancario)
    datos_externos_bde: DatosExternosBde = Field(default_factory=DatosExternosBde)
    calculos_derivados: CalculosDerivados = Field(default_factory=CalculosDerivados)
    evaluacion_drools: EvaluacionDrools = Field(default_factory=EvaluacionDrools)

    def as_dict(self) -> dict:
        """Serializa el estado a diccionario para persistencia JSON."""
        return self.model_dump()
