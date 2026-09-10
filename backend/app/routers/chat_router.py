"""
routers/chat_router.py — Endpoint conversacional POST /api/chat.

Punto de entrada principal del sistema desde el frontend.
Recibe el mensaje del usuario, delega en el `PipelineOrchestrator`
y devuelve la respuesta natural junto con el estado completo del sistema.

El router instancia las dependencias de servicio a través de funciones
de fábrica compatibles con `Depends()` de FastAPI.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.clients.mistral_client import MistralClient
from app.clients.drools_client import DroolsClient
from app.services.bde_mock_service import BdeMockService
from app.services.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Chat Conversacional"],
)


# ── Fábricas de dependencias para inyección mediante Depends() ────────────────

def get_mistral_client() -> MistralClient:
    """Fábrica de MistralClient para inyección de dependencias."""
    return MistralClient()


def get_drools_client() -> DroolsClient:
    """Fábrica de DroolsClient para inyección de dependencias."""
    return DroolsClient()


def get_bde_service() -> BdeMockService:
    """Fábrica de BdeMockService para inyección de dependencias."""
    try:
        return BdeMockService()
    except FileNotFoundError as exc:
        logger.error("Archivo bde.json no encontrado: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datos mock del BdE no disponibles: {str(exc)}",
        ) from exc


def get_orchestrator(
    mistral: MistralClient = Depends(get_mistral_client),
    drools: DroolsClient = Depends(get_drools_client),
    bde: BdeMockService = Depends(get_bde_service),
) -> PipelineOrchestrator:
    """Fábrica de PipelineOrchestrator con dependencias inyectadas."""
    return PipelineOrchestrator(
        mistral_client=mistral,
        drools_client=drools,
        bde_service=bde,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Enviar mensaje conversacional al sistema neurosimbólico",
    description=(
        "Recibe el mensaje del usuario y ejecuta el pipeline dinámico de 5 acciones."
        "Devuelve la respuesta textual y el information_state completo para auditoría."
    ),
    status_code=status.HTTP_200_OK,
)
def post_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    """
    Endpoint principal del sistema conversacional.

    Invoca el `PipelineOrchestrator` que ejecuta las acciones dinámicamente,
    registra la auditoría completa y devuelve la respuesta al frontend.

    Args:
        request: Payload con mensaje, cliente_id y session_id.
        db: Sesión de base de datos (inyectada por FastAPI).
        orchestrator: Instancia del orquestador (inyectada por FastAPI).

    Returns:
        ChatResponse: Respuesta textual, estado del sistema y metadatos del turno.

    Raises:
        HTTPException 404: Si el cliente no existe en la base de datos.
        HTTPException 503: Si Drools o Mistral no están disponibles.
        HTTPException 500: Para cualquier otro error interno.
    """
    logger.info(
        "POST /api/chat — cliente_id='%s', session_id='%s', mensaje_len=%d",
        request.cliente_id,
        request.session_id[:8],
        len(request.mensaje),
    )

    try:
        respuesta_texto, information_state, acciones_ejecutadas = orchestrator.procesar_turno_conversacional(
            mensaje=request.mensaje,
            cliente_id=request.cliente_id,
            session_id=request.session_id,
            db=db,
        )

        estado_evaluacion = (
            information_state
            .get("evaluacion_drools", {})
            .get("estado", "EN_PROCESO")
        )
        turn_id = information_state.get("turn_id", 1)

        return ChatResponse(
            respuesta=respuesta_texto,
            information_state=information_state,
            session_id=request.session_id,
            turn_id=turn_id,
            estado_evaluacion=estado_evaluacion,
            acciones_ejecutadas=acciones_ejecutadas,
        )

    except ValueError as exc:
        # Cliente no encontrado u otros errores de validación
        if "no encontrado" in str(exc).lower():
            logger.warning("Cliente no encontrado: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        logger.error("Error de validación en /api/chat: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except ConnectionError as exc:
        logger.error("Servicio Drools no disponible: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"El motor de reglas no está disponible: {str(exc)}",
        ) from exc

    except Exception as exc:
        logger.exception("Error inesperado en /api/chat: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(exc)}",
        ) from exc
