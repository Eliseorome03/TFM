# app/routers/__init__.py
from app.routers.chat_router import router as chat_router
from app.routers.clientes_router import router as clientes_router
from app.routers.bde_mock_router import router as bde_mock_router

__all__ = ["chat_router", "clientes_router", "bde_mock_router"]
