"""
routers/clientes_router.py — Endpoint GET /api/clientes.

Sirve la lista de clientes disponibles para alimentar el desplegable
de selección de usuario en el frontend.

Devuelve únicamente los campos necesarios para la UI: cliente_id y dni,
sin exponer datos financieros sensibles en este endpoint de catálogo.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.cliente import ClienteModel

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Clientes"],
)


class ClienteResumen(BaseModel):
    """Resumen público de un cliente para el desplegable del frontend."""

    cliente_id: str
    dni: str
    edad: int
    ingresos_netos_mensuales: float
    es_avalista: bool

    model_config = {"from_attributes": True}


class ClientesListResponse(BaseModel):
    """Respuesta del endpoint GET /api/clientes."""

    total: int
    clientes: list[ClienteResumen]


@router.get(
    "/clientes",
    response_model=ClientesListResponse,
    summary="Listar todos los clientes disponibles",
    description=(
        "Devuelve la lista de clientes registrados en el sistema para alimentar "
        "el selector de usuarios del frontend. Solo expone campos no sensibles."
    ),
    status_code=status.HTTP_200_OK,
)
def get_clientes(db: Session = Depends(get_db)) -> ClientesListResponse:
    """
    Endpoint que devuelve el catálogo de clientes disponibles.

    Se usa en el frontend para poblar el desplegable de selección de usuario
    antes de iniciar una conversación.

    Args:
        db: Sesión de base de datos (inyectada por FastAPI).

    Returns:
        ClientesListResponse: Lista de clientes con sus campos básicos.

    Raises:
        HTTPException 500: Si hay un error al consultar la base de datos.
    """
    logger.info("GET /api/clientes — consultando catálogo de clientes")

    try:
        clientes = (
            db.query(ClienteModel)
            .order_by(ClienteModel.cliente_id.asc())
            .all()
        )

        logger.info("GET /api/clientes — %d clientes encontrados", len(clientes))

        return ClientesListResponse(
            total=len(clientes),
            clientes=[
                ClienteResumen(
                    cliente_id=c.cliente_id,
                    dni=c.dni,
                    edad=c.edad,
                    ingresos_netos_mensuales=c.ingresos_netos_mensuales,
                    es_avalista=c.es_avalista,
                )
                for c in clientes
            ],
        )

    except Exception as exc:
        logger.exception("Error al consultar clientes: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el catálogo de clientes: {str(exc)}",
        ) from exc
