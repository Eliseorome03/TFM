"""
models/traza.py — Modelo ORM de la tabla 'trazas_auditoria'.

Implementa el ledger inmutable de auditoría por micro-acción requerido por el EU AI Act.
Cada registro representa un paso atómico dentro de un turno conversacional,
con snapshot del estado del sistema antes y después de la acción.
"""

from sqlalchemy import Column, BigInteger, Integer, String, JSON
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.sql import func

from app.database import Base


class TrazaAuditoria(Base):
    """
    Representación ORM de la tabla `trazas_auditoria` en MariaDB.

    Registra de forma atómica e inmutable cada micro-acción del pipeline de 5 pasos dinámicos
    (EXTRACT_NLU, FETCH_CORE_DATA, EVALUATE_DROOLS, FETCH_CIRBE_ASNEF,
    GENERATE_NATURAL_RESPONSE).

    Campos:
        id              — BIGINT AUTO_INCREMENT PK. Identificador único de la traza.
        session_id      — VARCHAR(64). Identificador único de la conversación.
        turn_id         — INT. Número de turno conversacional (1, 2, 3...).
        step_order      — INT. Secuencia cronológica dentro del turno (1, 2, 3...).
        action_type     — VARCHAR(64). Nombre formal de la micro-acción.
        step_input      — JSON. Datos exactos entregados al componente.
        step_output     — JSON. Respuesta devuelta por el componente.
        information_state — JSON. Snapshot consolidado del estado tras completarse el paso.
        created_at      — TIMESTAMP. Marca de tiempo precisa para auditoría temporal.
    """

    __tablename__ = "trazas_auditoria"

    id: int = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="Identificador único de la traza (BIGINT AUTO_INCREMENT PK)",
    )
    session_id: str = Column(
        String(64),
        nullable=False,
        index=True,
        comment="Identificador único de la conversación del cliente (UUID)",
    )
    turn_id: int = Column(
        Integer,
        nullable=False,
        comment="Número de turno conversacional (1, 2, 3...)",
    )
    step_order: int = Column(
        Integer,
        nullable=False,
        comment="Secuencia cronológica dentro del turno (1, 2, 3...)",
    )
    action_type: str = Column(
        String(64),
        nullable=False,
        comment=(
            "Nombre formal de la micro-acción: "
            "EXTRACT_NLU | FETCH_CORE_DATA | EVALUATE_DROOLS | "
            "FETCH_CIRBE_ASNEF | GENERATE_NATURAL_RESPONSE"
        ),
    )
    step_input: dict = Column(
        JSON,
        nullable=True,
        comment="Datos exactos entregados al componente en este paso",
    )
    step_output: dict = Column(
        JSON,
        nullable=True,
        comment="Respuesta devuelta por el componente tras ejecutar el paso",
    )
    information_state: dict = Column(
        JSON,
        nullable=True,
        comment="Snapshot consolidado del information_state tras completarse el paso",
    )
    created_at = Column(
        TIMESTAMP(fsp=6),
        nullable=False,
        server_default=func.now(6),
        comment="Marca de tiempo precisa (UTC) con resolución de microsegundos para auditoría temporal",
    )

    def __repr__(self) -> str:
        return (
            f"<TrazaAuditoria("
            f"id={self.id}, "
            f"session_id='{self.session_id}', "
            f"turn_id={self.turn_id}, "
            f"step_order={self.step_order}, "
            f"action_type='{self.action_type}'"
            f")>"
        )
