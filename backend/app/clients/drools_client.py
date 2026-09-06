"""
clients/drools_client.py — Cliente HTTP para el microservicio Drools KIE.

Encapsula las llamadas HTTP POST al endpoint /api/evaluate del servicio
drools-app (Spring Boot + Drools KIE), usando httpx para soporte asíncrono
y manejo robusto de errores y timeouts.

El cliente transforma el payload del InformationState en el formato
esperado por el POJO Java `SolicitudEvaluacion` y deserializa la respuesta
en un `DroolsResponse` tipado.
"""

import logging
import httpx

from app.config import settings
from app.schemas.drools_io import DroolsRequest, DroolsResponse

logger = logging.getLogger(__name__)


class DroolsClient:
    """
    Cliente orientado a objetos para el microservicio Drools (Spring Boot + KIE).

    Realiza llamadas HTTP POST síncronas al endpoint /api/evaluate y
    devuelve la respuesta como un objeto `DroolsResponse` tipado.

    El timeout y la URL son configurables a través de `settings`.
    Implementa manejo de errores defensivo para garantizar la resiliencia
    del pipeline orquestador.
    """

    def __init__(self) -> None:
        """Inicializa el cliente Drools con la URL y timeout de configuración."""
        self._url: str = settings.drools_url
        self._timeout: int = settings.drools_timeout
        logger.info(
            "DroolsClient inicializado — URL: %s, timeout: %ds",
            self._url,
            self._timeout,
        )

    def evaluar_reglas(self, payload: dict) -> DroolsResponse:
        """
        Envía el payload al motor de reglas Drools y devuelve la evaluación.

        El payload es el diccionario serializado del `DroolsRequest`, que agrupa
        los datos de usuario, core bancario y BdE en el formato esperado por
        el controlador Java `RuleController`.

        Args:
            payload: Diccionario con la estructura DroolsRequest serializada.

        Returns:
            DroolsResponse: Resultado tipado de la evaluación Drools.

        Raises:
            httpx.TimeoutException: Si Drools no responde en el tiempo configurado.
            httpx.HTTPStatusError: Si Drools devuelve un código de error HTTP.
            ValueError: Si la respuesta no puede deserializarse como DroolsResponse.
        """
        logger.info(
            "Drools: Enviando solicitud de evaluación a %s",
            self._url,
        )

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    url=self._url,
                    json=payload,
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                )
                response.raise_for_status()

        except httpx.TimeoutException as exc:
            logger.error(
                "Drools: Timeout tras %ds esperando respuesta de %s",
                self._timeout,
                self._url,
            )
            raise httpx.TimeoutException(
                f"El motor de reglas Drools no respondió en {self._timeout}s. "
                f"Verifique que el servicio drools-app esté activo."
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Drools: Error HTTP %d — %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise

        except httpx.ConnectError as exc:
            logger.error(
                "Drools: No se puede conectar a %s. ¿Está el servicio activo?",
                self._url,
            )
            raise ConnectionError(
                f"No se puede conectar al motor de reglas Drools en {self._url}. "
                f"Verifique que el contenedor drools-app esté corriendo."
            ) from exc

        try:
            response_data = response.json()
            drools_response = DroolsResponse.model_validate(response_data)
            logger.info(
                "Drools: Evaluación completada — estado='%s', reglas=%s",
                drools_response.estado,
                drools_response.reglas_disparadas,
            )
            return drools_response

        except Exception as exc:
            logger.error(
                "Drools: Error deserializando respuesta: %s — Respuesta raw: %s",
                str(exc),
                response.text[:500],
            )
            raise ValueError(
                f"La respuesta de Drools no es válida: {str(exc)}"
            ) from exc

    def construir_payload(self, state: dict) -> dict:
        """
        Construye el payload de DroolsRequest a partir del InformationState.

        Transforma el InformationState canónico en la estructura de datos
        que espera el endpoint Java de Drools.

        Args:
            state: Diccionario del InformationState canónico.

        Returns:
            dict: Payload serializado como DroolsRequest.
        """
        datos_usuario_raw = state.get("datos_usuario", {})
        datos_core_raw = state.get("datos_core_bancario", {})
        datos_bde_raw = state.get("datos_externos_bde", {})

        request = DroolsRequest(
            datos_usuario={
                "intencion_principal": datos_usuario_raw.get("intencion_principal"),
                "cantidad_solicitada": datos_usuario_raw.get("cantidad_solicitada"),
                "plazo_meses": datos_usuario_raw.get("plazo_meses"),
                "proposito": datos_usuario_raw.get("proposito"),
                "gastos_fijos_mensuales": datos_usuario_raw.get("gastos_fijos_mensuales"),
                "deuda_declarada": datos_usuario_raw.get("deuda_declarada"),
                "duda_catch_all": datos_usuario_raw.get("duda_catch_all", "NINGUNA"),
            },
            datos_core={
                "cliente_id": datos_core_raw.get("cliente_id"),
                "dni": datos_core_raw.get("dni"),
                "edad": datos_core_raw.get("edad"),
                "ingresos_netos_mensuales": datos_core_raw.get("ingresos_netos_mensuales"),
                "antiguedad_meses": datos_core_raw.get("antiguedad_meses"),
                "deuda_interna_banco_mensual": datos_core_raw.get("deuda_interna_banco_mensual"),
                "es_avalista": datos_core_raw.get("es_avalista", False),
                "empresa_avalada_cif": datos_core_raw.get("empresa_avalada_cif"),
            },
            datos_bde={
                "consultado": datos_bde_raw.get("consultado", False),
                "tiene_impagos_activos": datos_bde_raw.get("tiene_impagos_activos", False),
                "importe_morosidad_asnef": datos_bde_raw.get("importe_morosidad_asnef", 0.0),
                "empresa_avalada_concurso": datos_bde_raw.get("empresa_avalada_concurso"),
                "deuda_cirbe_mensual": datos_bde_raw.get("deuda_cirbe_mensual", 0.0),
                "deuda_cirbe_total": datos_bde_raw.get("deuda_cirbe_total", 0.0),
            },
        )

        return request.model_dump()
