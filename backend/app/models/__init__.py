# app/models/__init__.py
from app.models.cliente import ClienteModel
from app.models.traza import TrazaAuditoria

__all__ = ["ClienteModel", "TrazaAuditoria"]
