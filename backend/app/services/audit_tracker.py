"""
services/audit_tracker.py — Registro atómico de trazas de auditoría AI Act.

Implementa la clase `AuditTracker` que persiste cada micro-acción del pipeline
de 6 pasos como una fila inmutable en la tabla `trazas_auditoria`.

Este ledger de auditoría es el mecanismo de trazabilidad exigido por:
- Artículo 14 EU AI Act (Supervisión humana de sistemas de alto riesgo)
- Directiva 2014/17/UE (Gobernanza de decisiones crediticias)

Cada registro captura:
- El input exacto entregado al componente (step_input)
- La respuesta devuelta por el componente (step_output)
- El snapshot completo del information_state tras el paso (information_state)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.traza import TrazaAuditoria

logger = logging.getLogger(__name__)


class AuditTracker:
    """
    Servicio de registro de auditoría por micro-acción.

    Persiste snapshots inmutables de cada paso del pipeline conversacional
    en la tabla `trazas_auditoria`. Cada llamada a `registrar_paso()` crea
    una fila atómica e irrevocable que forma el ledger de auditoría.

    La inmutabilidad se garantiza por diseño: nunca se actualizan filas,
    solo se insertan nuevas. El campo `created_at` usa la función
    del servidor MariaDB para máxima precisión temporal.
    """

    def __init__(self, db: Session) -> None:
        """
        Inicializa el AuditTracker con una sesión de base de datos.

        Args:
            db: Sesión SQLAlchemy activa, inyectada por el orquestador.
        """
        self._db = db
        logger.debug("AuditTracker inicializado con sesión de base de datos")

    def registrar_paso(
        self,
        session_id: str,
        turn_id: int,
        step_order: int,
        action_type: str,
        step_input: dict,
        step_output: dict,
        information_state: dict,
    ) -> TrazaAuditoria:
        """
        Persiste atómicamente una micro-acción del pipeline en la tabla de auditoría.

        Crea una nueva fila inmutable en `trazas_auditoria` con todos los datos
        del paso: qué se entregó al componente, qué devolvió, y cuál era el
        estado completo del sistema tras completarse.

        Args:
            session_id: UUID de la sesión conversacional.
            turn_id: Número de turno conversacional (1, 2, 3...).
            step_order: Orden dentro del turno (1 a 6).
            action_type: Nombre formal de la micro-acción (ej: 'EXTRACT_NLU').
            step_input: Datos exactos entregados al componente.
            step_output: Respuesta devuelta por el componente.
            information_state: Snapshot del estado completo tras el paso.

        Returns:
            TrazaAuditoria: La fila persistida con su ID asignado.

        Raises:
            Exception: Si la persistencia falla (error de BD).
        """
        traza = TrazaAuditoria(
            session_id=session_id,
            turn_id=turn_id,
            step_order=step_order,
            action_type=action_type,
            step_input=step_input,
            step_output=step_output,
            information_state=information_state,
        )

        try:
            self._db.add(traza)
            self._db.commit()
            self._db.refresh(traza)
            logger.info(
                "Auditoría [%s] turno=%d paso=%d action='%s' → ID=%d",
                session_id[:8],
                turn_id,
                step_order,
                action_type,
                traza.id,
            )
            return traza

        except Exception as exc:
            self._db.rollback()
            logger.error(
                "Error al persistir traza de auditoría [session=%s, step=%s]: %s",
                session_id,
                action_type,
                str(exc),
            )
            raise

    def obtener_trazas_sesion(self, session_id: str) -> list[TrazaAuditoria]:
        """
        Recupera todas las trazas de auditoría de una sesión, ordenadas cronológicamente.

        Args:
            session_id: UUID de la sesión conversacional.

        Returns:
            list[TrazaAuditoria]: Lista de trazas ordenadas por turno y paso.
        """
        return (
            self._db.query(TrazaAuditoria)
            .filter(TrazaAuditoria.session_id == session_id)
            .order_by(TrazaAuditoria.turn_id.asc(), TrazaAuditoria.step_order.asc())
            .all()
        )
