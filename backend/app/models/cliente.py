"""
models/cliente.py — Modelo ORM de la tabla 'clientes'.

Mapea el perfil bancario core de cada cliente.
Esta tabla es de solo lectura durante el pipeline conversacional;
se alimenta mediante el script SQL de inicialización.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean
from app.database import Base


class ClienteModel(Base):
    """
    Representación ORM de la tabla `clientes` en MariaDB.

    Campos:
        cliente_id              — Identificador único del cliente (PK).
        dni                     — Documento Nacional de Identidad.
        edad                    — Edad en años del titular.
        ingresos_netos_mensuales — Ingresos netos tras impuestos (EUR/mes).
        antiguedad_meses        — Años de antigüedad como cliente del banco (en meses).
        deuda_interna_banco_mensual     — Cuota mensual de deudas activas con este banco (EUR/mes).
        es_avalista             — Indica si el cliente actúa como avalista de terceros.
        empresa_avalada_cif     — CIF de la empresa avalada (solo cuando es_avalista=True).
    """

    __tablename__ = "clientes"

    cliente_id: str = Column(
        String(64),
        primary_key=True,
        index=True,
        comment="Identificador único del cliente",
    )
    dni: str = Column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Documento Nacional de Identidad",
    )
    edad: int = Column(
        Integer,
        nullable=False,
        comment="Edad en años del titular",
    )
    ingresos_netos_mensuales: float = Column(
        Float,
        nullable=False,
        comment="Ingresos netos mensuales tras impuestos (EUR/mes)",
    )
    antiguedad_meses: int = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Antigüedad como cliente del banco (en meses)",
    )
    deuda_interna_banco_mensual: float = Column(
        Float,
        nullable=False,
        default=0.0,
        comment="Cuota mensual total de deudas activas con este banco (EUR/mes)",
    )
    es_avalista: bool = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Indica si el cliente actúa como avalista de terceros",
    )
    empresa_avalada_cif: str | None = Column(
        String(20),
        nullable=True,
        default=None,
        comment="CIF de la empresa avalada (solo cuando es_avalista=True)",
    )

    def __repr__(self) -> str:
        return (
            f"<ClienteModel("
            f"cliente_id='{self.cliente_id}', "
            f"dni='{self.dni}', "
            f"edad={self.edad}, "
            f"ingresos={self.ingresos_netos_mensuales}"
            f")>"
        )
