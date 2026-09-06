"""
database.py — Configuración del motor SQLAlchemy y gestión de sesiones.

Expone:
  - `engine`: Motor de conexión a MariaDB vía pymysql.
  - `SessionLocal`: Fábrica de sesiones de base de datos.
  - `Base`: Clase declarativa de la que heredan todos los modelos ORM.
  - `get_db()`: Generador de dependencia para inyección en los endpoints FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator

from app.config import settings


# Motor de base de datos — pool_pre_ping activa el health-check de conexiones
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,       # Reciclar conexiones cada hora para evitar timeouts de MariaDB
    echo=False,              # Cambiar a True para depuración de queries SQL
)

# Fábrica de sesiones — autocommit y autoflush desactivados para control explícito
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base declarativa de la que heredan todos los modelos ORM
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Generador de dependencia FastAPI que proporciona una sesión de base de datos
    y garantiza su cierre al finalizar cada request (patrón Unit of Work).

    Uso:
        @router.get("/endpoint")
        def mi_endpoint(db: Session = Depends(get_db)):
            ...
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
