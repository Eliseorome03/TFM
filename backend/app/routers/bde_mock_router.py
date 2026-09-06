"""
routers/bde_mock_router.py — Endpoint GET /api/mock/bde/{dni}.

Expone el servicio de simulación del Banco de España (CIRBE/ASNEF)
como un endpoint HTTP independiente. Permite consultar directamente
los datos mock por DNI para pruebas de integración y depuración.

En el pipeline normal, este servicio se llama internamente desde el
`PipelineOrchestrator` sin pasar por este endpoint. Este router existe
para facilitar el testing manual y la integración con otros servicios.
"""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

from app.services.bde_mock_service import BdeMockService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/mock",
    tags=["BdE Mock (CIRBE/ASNEF)"],
)


class BdeConsultaResponse(BaseModel):
    """Respuesta del endpoint de consulta mock al BdE."""

    dni: str
    consultado: bool
    tiene_impagos_activos: bool
    importe_morosidad_asnef: float
    empresa_avalada_concurso: bool | None
    deuda_cirbe_mensual: float
    deuda_cirbe_total: float
    fuente: str
    fecha_consulta: str


def get_bde_service() -> BdeMockService:
    """Fábrica de BdeMockService para inyección de dependencias."""
    return BdeMockService()


@router.get(
    "/bde/{dni}",
    response_model=BdeConsultaResponse,
    summary="Consultar datos CIRBE/ASNEF simulados por DNI",
    description=(
        "Simula la consulta al Banco de España (CIRBE/ASNEF) para un DNI dado. "
        "Devuelve los datos de solvencia patrimonial mock definidos en bde.json. "
        "Si el DNI no tiene perfil específico, devuelve valores por defecto (sin impagos)."
    ),
    status_code=status.HTTP_200_OK,
)
def get_bde_por_dni(
    dni: str,
    bde_service: BdeMockService = Depends(get_bde_service),
) -> BdeConsultaResponse:
    """
    Endpoint de consulta directa al mock del Banco de España.

    Args:
        dni: DNI del cliente a consultar (path parameter).
        bde_service: Servicio mock del BdE (inyectado por FastAPI).

    Returns:
        BdeConsultaResponse: Datos de solvencia patrimonial simulados.

    Raises:
        HTTPException 500: Si hay un error al leer los datos del mock.
    """
    logger.info("GET /api/mock/bde/%s — consultando datos BdE mock", dni)

    try:
        datos = bde_service.consultar_por_dni(dni)

        return BdeConsultaResponse(
            dni=dni.upper().strip(),
            consultado=datos["consultado"],
            tiene_impagos_activos=datos["tiene_impagos_activos"],
            importe_morosidad_asnef=datos["importe_morosidad_asnef"],
            empresa_avalada_concurso=datos.get("empresa_avalada_concurso"),
            deuda_cirbe_mensual=datos["deuda_cirbe_mensual"],
            deuda_cirbe_total=datos["deuda_cirbe_total"],
            fuente=datos.get("fuente", "CIRBE / ASNEF - Simulación BdE"),
            fecha_consulta=datos.get("fecha_consulta", "2026-01-15"),
        )

    except FileNotFoundError as exc:
        logger.error("Archivo bde.json no encontrado: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datos mock del BdE no disponibles: {str(exc)}",
        ) from exc

    except Exception as exc:
        logger.exception("Error al consultar BdE mock para DNI=%s: %s", dni, str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al consultar el BdE mock: {str(exc)}",
        ) from exc


@router.get(
    "/bde",
    summary="Listar DNIs catalogados en el mock BdE",
    description="Devuelve la lista de DNIs con perfil específico en el archivo bde.json.",
    status_code=status.HTTP_200_OK,
)
def get_dnis_catalogados(
    bde_service: BdeMockService = Depends(get_bde_service),
) -> dict:
    """
    Endpoint auxiliar que lista los DNIs con perfil específico en el mock.

    Útil para el desarrollo y testing para conocer qué DNIs tienen
    comportamientos específicos predefinidos.

    Args:
        bde_service: Servicio mock del BdE (inyectado por FastAPI).

    Returns:
        dict: Lista de DNIs catalogados y total.
    """
    dnis = bde_service.listar_dnis_catalogados()
    return {
        "total": len(dnis),
        "dnis_catalogados": dnis,
        "nota": "Los DNIs no listados devuelven perfil limpio (sin impagos)",
    }
