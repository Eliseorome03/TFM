"""
clients/mistral_client.py — Cliente oficial de Mistral AI para NLU y NLG.

Encapsula dos operaciones lingüísticas estrictamente separadas:

1. `extraer_nlu()` — Structured output vía `chat.parse()`:
   Extrae intención, cantidades, plazos y propósito del mensaje del usuario.
   Garantiza un JSON válido conforme al esquema `EsquemaNLU`.

2. `generar_nlg()` — Generación fiel de texto vía `chat.complete()`:
   Produce la respuesta natural al usuario basándose EXCLUSIVAMENTE en
   el `information_state` final y la justificación normativa de Drools.
   El LLM opera en modo solo lectura: no tiene acceso a herramientas
   de ejecución ni puede tomar decisiones propias.

Arquitectura: Symbolic[Neuro] — el LLM es un servicio encapsulado.
"""

import logging
from mistralai.client import Mistral
from mistralai.client.models import UserMessage, SystemMessage

from app.config import settings
from app.schemas.nlu import EsquemaNLU

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# Prompts del sistema — definidos como constantes de módulo
# ────────────────────────────────────────────────────────────────────────────

_NLU_SYSTEM_PROMPT = """Eres un extractor de entidades financieras para un sistema bancario de evaluación de préstamos personales.
Tu única función es analizar el mensaje del usuario y extraer de forma precisa y estructurada los campos del esquema JSON definido.

REGLAS ESTRICTAS:
1. Extrae SOLO lo que el usuario menciona explícitamente o puedes inferir con certeza absoluta.
2. Si un campo no se menciona ni se puede inferir, devuelve null para ese campo.
3. Convierte cantidades coloquiales: "doce mil" → 12000.0, "12k" → 12000.0, "un millón" → 1000000.0.
4. Convierte plazos en años a meses: "3 años" → 36, "año y medio" → 18.
5. Para `proposito`, mapea solo si hay suficiente certeza: coche/moto/vehículo → VEHICULO, casa/piso/reforma → REFORMA, estudios/universidad/máster → ESTUDIOS, salud/operación/médico → SALUD, cripto/bitcoin → CRIPTOMONEDAS, apuestas/juego → APUESTAS, pagar deudas de prestamistas/refinanciar informalmente → REFINANCIACION_INFORMAL. Si no encaja en ninguno con certeza → OTRO. Si no se menciona → null.
6. `duda_catch_all` solo es relevante si `intencion_principal` es CONSULTAR_DUDA.
7. Gastos fijos mensuales son: alquiler, suministros, seguros, etc. NO incluye deudas bancarias.
8. Deuda declarada es: el importe total de deudas externas que el usuario declara tener.

EJEMPLOS:
---
Usuario: "Hola, buenos días"
JSON: {"intencion_principal": "SALUDAR", "cantidad_solicitada": null, "plazo_meses": null, "proposito": null, "gastos_fijos_mensuales": null, "deuda_declarada": null, "duda_catch_all": "NINGUNA"}

---
Usuario: "Quiero pedir 12 mil euros para devolver en 48 meses para comprarme un coche"
JSON: {"intencion_principal": "SOLICITAR_PRESTAMO", "cantidad_solicitada": 12000.0, "plazo_meses": 48, "proposito": "VEHICULO", "gastos_fijos_mensuales": null, "deuda_declarada": null, "duda_catch_all": "NINGUNA"}

---
Usuario: "Necesito 8000 euros a 2 años para hacer una reforma. Pago 650 de alquiler y tengo una deuda de 5000 euros en otro banco."
JSON: {"intencion_principal": "SOLICITAR_PRESTAMO", "cantidad_solicitada": 8000.0, "plazo_meses": 24, "proposito": "REFORMA", "gastos_fijos_mensuales": 650.0, "deuda_declarada": 5000.0, "duda_catch_all": "NINGUNA"}

---
Usuario: "¿Cuáles son los requisitos para que me aprueben un préstamo?"
JSON: {"intencion_principal": "CONSULTAR_DUDA", "cantidad_solicitada": null, "plazo_meses": null, "proposito": null, "gastos_fijos_mensuales": null, "deuda_declarada": null, "duda_catch_all": "REQUISITOS_APROBACION"}

---
Usuario: "Quiero pedir un préstamo para cripto y apuestas"
JSON: {"intencion_principal": "SOLICITAR_PRESTAMO", "cantidad_solicitada": null, "plazo_meses": null, "proposito": "CRIPTOMONEDAS", "gastos_fijos_mensuales": null, "deuda_declarada": null, "duda_catch_all": "NINGUNA"}

---
Usuario: "Mis gastos fijos son unos 900 euros al mes"
JSON: {"intencion_principal": "SOLICITAR_PRESTAMO", "cantidad_solicitada": null, "plazo_meses": null, "proposito": null, "gastos_fijos_mensuales": 900.0, "deuda_declarada": null, "duda_catch_all": "NINGUNA"}
"""

_NLG_SYSTEM_PROMPT = """Eres el asistente de comunicación de un banco. Tu función es EXCLUSIVAMENTE redactar el mensaje de respuesta al cliente, basándote en el estado del sistema que te proporcionan.

RESTRICCIONES ABSOLUTAS (violación = fallo del sistema):
1. PROHIBIDO tomar decisiones propias. La decisión ya está tomada por el motor de reglas; tú solo la comunicas.
2. PROHIBIDO inventar, añadir o modificar información. Solo usa los datos del estado del sistema.
3. PROHIBIDO incluir explicaciones legales o normativas si el campo `texto_legal` del estado está vacío o es null.
4. PROHIBIDO revelar detalles técnicos internos (nombres de reglas como R_RATIO_ENDEUDAMIENTO, nombres de campos JSON, etc.).
5. PROHIBIDO pedir datos que ya constan en el estado como presentes.
6. El tono del mensaje debe seguir exactamente el indicado en `tono_mensaje` del estado.
7. Si el estado es REQUIERE_DATOS, pide ÚNICAMENTE el dato indicado en `dato_faltante`, de forma natural y conversacional.
8. Si el estado es APROBADO, da la enhorabuena de forma clara y profesional.
9. Si el estado es DENEGADO, comunica la decisión con el tono indicado e incluye la justificación normativa SOLO si `texto_legal` está disponible.
10. Si el estado es REQUIERE_SUPERVISION_HUMANA, informa de que el caso será revisado por un especialista.
11. Redacta en español, en segunda persona (tratamiento de "usted" formal).
12. El mensaje debe ser conciso, claro y orientado al cliente. Sin tecnicismos.
"""


class MistralClient:
    """
    Cliente orientado a objetos para las operaciones lingüísticas con Mistral AI.

    Encapsula la instancia del SDK oficial `mistralai` y expone exactamente
    dos métodos públicos: `extraer_nlu()` para extracción estructurada y
    `generar_nlg()` para generación de respuesta natural.

    El paradigma Symbolic[Neuro] garantiza que este cliente nunca toma
    decisiones de negocio: solo procesa lenguaje.
    """

    def __init__(self) -> None:
        """Inicializa el cliente Mistral con la API Key desde configuración."""
        self._client = Mistral(api_key=settings.mistral_api_key)
        self._model = settings.mistral_model
        logger.info(
            "MistralClient inicializado con modelo: %s",
            self._model,
        )

    def extraer_nlu(self, mensaje: str) -> EsquemaNLU:
        """
        Extrae entidades financieras del mensaje del usuario mediante structured output.

        Utiliza `chat.parse()` del SDK de Mistral, que garantiza que la respuesta
        sea un JSON válido y conforme al esquema Pydantic `EsquemaNLU`.
        Esta garantía es fundamental para la robustez del pipeline.

        Args:
            mensaje: Texto libre introducido por el usuario.

        Returns:
            EsquemaNLU: Objeto Pydantic con los campos extraídos.

        Raises:
            Exception: Si Mistral no puede procesar el mensaje o el structured output falla.
        """
        logger.info("NLU: Procesando mensaje del usuario (longitud: %d chars)", len(mensaje))

        response = self._client.chat.parse(
            model=self._model,
            messages=[
                SystemMessage(content=_NLU_SYSTEM_PROMPT),
                UserMessage(content=mensaje),
            ],
            response_format=EsquemaNLU,
            temperature=0.0,  # Determinismo máximo para extracción de entidades
        )

        parsed_result: EsquemaNLU = response.choices[0].message.parsed
        logger.info(
            "NLU: Extracción completada — intención='%s', cantidad=%s, plazo=%s, propósito=%s",
            parsed_result.intencion_principal,
            parsed_result.cantidad_solicitada,
            parsed_result.plazo_meses,
            parsed_result.proposito,
        )
        return parsed_result

    def generar_nlg(self, state: dict, mensaje_usuario: str) -> str:
        """
        Genera la respuesta textual natural al usuario en modo solo lectura.

        El LLM recibe el volcado completo del `information_state` final
        (después de todas las evaluaciones de Drools) y lo usa EXCLUSIVAMENTE
        para redactar el mensaje. No toma decisiones propias.

        Esta arquitectura Read-Only State Dump mitiga los ataques de prompt injection
        al eliminar toda capacidad transaccional del LLM.

        Args:
            state: Diccionario del InformationState final tras el pipeline.
            mensaje_usuario: Mensaje original del usuario (para contexto conversacional).

        Returns:
            str: Respuesta textual natural lista para mostrar al usuario.

        Raises:
            Exception: Si Mistral no puede generar la respuesta.
        """
        logger.info("NLG: Generando respuesta natural para estado='%s'",
                    state.get("evaluacion_drools", {}).get("estado", "DESCONOCIDO"))

        # Construir el volcado de estado en modo solo lectura
        evaluacion = state.get("evaluacion_drools", {})
        datos_usuario = state.get("datos_usuario", {})
        calculos = state.get("calculos_derivados", {})

        estado_actual = evaluacion.get("estado", "EN_PROCESO")
        dato_faltante = evaluacion.get("dato_faltante")
        accion_requerida = evaluacion.get("accion_requerida")
        articulo_normativo = evaluacion.get("articulo_normativo")
        texto_legal = evaluacion.get("texto_legal")
        tono_mensaje = evaluacion.get("tono_mensaje", "profesional y claro")

        # Construir el contexto de estado para el LLM (solo lectura)
        contexto_estado = f"""
=== ESTADO ACTUAL DEL SISTEMA (SOLO LECTURA — NO MODIFICAR) ===

MENSAJE DEL USUARIO: {mensaje_usuario}

ESTADO DE EVALUACIÓN: {estado_actual}
REGLAS DISPARADAS: {', '.join(evaluacion.get('reglas_disparadas', [])) or 'Ninguna aún'}
TONO REQUERIDO: {tono_mensaje}

DATO FALTANTE (si aplica): {dato_faltante or 'Ninguno'}
ACCIÓN REQUERIDA (si aplica): {accion_requerida or 'Ninguna'}

DATOS FINANCIEROS CONOCIDOS:
- Cantidad solicitada: {datos_usuario.get('cantidad_solicitada', 'No indicada')} EUR
- Plazo: {datos_usuario.get('plazo_meses', 'No indicado')} meses
- Propósito: {datos_usuario.get('proposito', 'No indicado')}
- Cuota estimada: {calculos.get('cuota_estimada', 'No calculada')} EUR/mes
- Ratio de endeudamiento: {calculos.get('ratio_endeudamiento', 'No calculado')}
- Remanente de subsistencia: {calculos.get('remanente_subsistencia', 'No calculado')} EUR/mes

JUSTIFICACIÓN NORMATIVA (incluir SOLO si hay texto_legal y el estado es decisivo):
- Artículo: {articulo_normativo or 'NO DISPONIBLE — NO INVENTAR NORMATIVA'}
- Texto legal: {texto_legal or 'NO DISPONIBLE — NO INCLUIR EXPLICACIÓN LEGAL'}

=== FIN DEL ESTADO DEL SISTEMA ===

Redacta ahora el mensaje para el cliente siguiendo estrictamente las instrucciones de tu sistema.
"""

        response = self._client.chat.complete(
            model=self._model,
            messages=[
                SystemMessage(content=_NLG_SYSTEM_PROMPT),
                UserMessage(content=contexto_estado),
            ],
            temperature=0.3,  # Ligera variabilidad para naturalidad, sin creatividad excesiva
            max_tokens=600,
        )

        respuesta_texto = response.choices[0].message.content.strip()
        logger.info(
            "NLG: Respuesta generada (%d chars)",
            len(respuesta_texto),
        )
        return respuesta_texto
