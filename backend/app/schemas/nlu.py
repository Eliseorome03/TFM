"""
schemas/nlu.py — Esquema de salida estructurada del componente NLU (Mistral).

Define los Enums de valores válidos y el modelo Pydantic `EsquemaNLU`
que Mistral debe producir mediante structured output (chat.parse).
Este esquema es el contrato formal entre el LLM y el pipeline de orquestación.
"""

from enum import Enum
from pydantic import BaseModel, Field


class IntencionPrincipal(str, Enum):
    """Intención detectada en el mensaje del usuario."""

    SOLICITAR_PRESTAMO = "SOLICITAR_PRESTAMO"
    CONSULTAR_DUDA = "CONSULTAR_DUDA"
    SALUDAR = "SALUDAR"
    OTRA = "OTRA"


class PropositoPrestamo(str, Enum):
    """Propósito declarado o inferido del préstamo solicitado."""

    VEHICULO = "VEHICULO"
    REFORMA = "REFORMA"
    ESTUDIOS = "ESTUDIOS"
    SALUD = "SALUD"
    OTRO = "OTRO"
    CRIPTOMONEDAS = "CRIPTOMONEDAS"
    APUESTAS = "APUESTAS"
    REFINANCIACION_INFORMAL = "REFINANCIACION_INFORMAL"


class DudaCatchAll(str, Enum):
    """Tipo de duda informativa detectada (solo cuando intencion == CONSULTAR_DUDA)."""

    NINGUNA = "NINGUNA"
    REQUISITOS_APROBACION = "REQUISITOS_APROBACION"
    CONDICIONES_CANCELACION = "CONDICIONES_CANCELACION"
    NORMATIVA_SOLVENCIA = "NORMATIVA_SOLVENCIA"
    FUERA_DE_DOMINIO = "FUERA_DE_DOMINIO"


class EsquemaNLU(BaseModel):
    """
    Esquema de salida estructurada del componente NLU.

    Mistral lo produce mediante `chat.parse()` con structured output garantizado.
    Todos los campos de extracción son opcionales (null) salvo `intencion_principal`
    y `duda_catch_all`, que siempre tienen un valor por defecto.

    Ejemplo de entrada al LLM:
        "Quiero pedir 12 mil euros para devolver en 48 meses para comprarme un coche"

    Ejemplo de salida esperada:
        {
          "intencion_principal": "SOLICITAR_PRESTAMO",
          "cantidad_solicitada": 12000.0,
          "plazo_meses": 48,
          "proposito": "VEHICULO",
          "gastos_fijos_mensuales": null,
          "deuda_declarada": null,
          "duda_catch_all": "NINGUNA"
        }
    """

    intencion_principal: IntencionPrincipal = Field(
        ...,
        description=(
            "Intención principal detectada en el mensaje del usuario. "
            "Debe ser uno de: SOLICITAR_PRESTAMO, CONSULTAR_DUDA, SALUDAR, OTRA."
        ),
    )
    cantidad_solicitada: float | None = Field(
        default=None,
        description=(
            "Importe del préstamo en euros (EUR). "
            "Extraer incluso si se expresa de forma coloquial ('doce mil', '12k'). "
            "Null si no se menciona."
        ),
    )
    plazo_meses: int | None = Field(
        default=None,
        description=(
            "Plazo de devolución en meses. "
            "Convertir desde años si es necesario ('3 años' -> 36). "
            "Null si no se menciona."
        ),
    )
    proposito: PropositoPrestamo | None = Field(
        default=None,
        description=(
            "Propósito declarado o claramente inferido del préstamo. "
            "Null si el usuario no lo ha mencionado o no se puede inferir con certeza."
        ),
    )
    gastos_fijos_mensuales: float | None = Field(
        default=None,
        description=(
            "Gastos fijos mensuales declarados por el usuario en euros "
            "(alquiler, suministros, etc.). NO incluye deudas. "
            "Null si no se menciona."
        ),
    )
    deuda_declarada: float | None = Field(
        default=None,
        description=(
            "Importe total de deudas externas declaradas por el usuario en euros. "
            "Null si no se menciona."
        ),
    )
    duda_catch_all: DudaCatchAll = Field(
        default=DudaCatchAll.NINGUNA,
        description=(
            "Tipo de duda informativa (solo relevante si intencion_principal == CONSULTAR_DUDA). "
            "NINGUNA si la intención no es una duda."
        ),
    )
