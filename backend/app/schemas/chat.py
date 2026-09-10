"""
schemas/chat.py — Contratos de Request/Response del endpoint conversacional.

Define los modelos Pydantic para el endpoint POST /api/chat que consume el frontend.
La respuesta incluye la contestación textual del asistente y el information_state
completo para el panel de depuración JSON del UI.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Payload de entrada del endpoint POST /api/chat.

    El frontend envía el mensaje del usuario, el cliente seleccionado
    y el identificador de sesión único generado en el primer turno.

    Atributos:
        mensaje     — Texto libre introducido por el usuario.
        cliente_id  — ID del cliente seleccionado en el desplegable del UI.
        session_id  — UUID de la sesión conversacional (generado por el frontend).
    """

    mensaje: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Texto libre del mensaje del usuario",
    )
    cliente_id: str = Field(
        ...,
        description="Identificador del cliente seleccionado (de la tabla 'clientes')",
    )
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="UUID único de la sesión conversacional (generado en el frontend)",
    )


class ChatResponse(BaseModel):
    """
    Payload de respuesta del endpoint POST /api/chat.

    El frontend recibe la respuesta textual del asistente y el estado
    completo del sistema para el panel de depuración JSON.

    Atributos:
        respuesta           — Texto natural generado por Mistral NLG.
        information_state   — Snapshot final del estado tras el turno completo.
        session_id          — Echo del session_id para correlación en el frontend.
        turn_id             — Número de turno completado.
        estado_evaluacion   — Estado de la evaluación Drools para el UI.
        acciones_ejecutadas — Lista de las acciones dinámicas ejecutadas en el turno.
    """

    respuesta: str = Field(
        ...,
        description="Respuesta natural generada por el componente NLG (Mistral)",
    )
    information_state: dict = Field(
        ...,
        description="Snapshot completo del InformationState tras el turno",
    )
    session_id: str = Field(
        ...,
        description="Identificador de sesión (echo para correlación)",
    )
    turn_id: int = Field(
        ...,
        description="Número del turno conversacional completado",
    )
    estado_evaluacion: str = Field(
        ...,
        description="Estado de la evaluación Drools (para indicadores visuales del UI)",
    )
    acciones_ejecutadas: list[str] = Field(
        ...,
        description="Lista de acciones ejecutadas por el orquestador en este turno",
    )
