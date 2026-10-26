"""
evaluate_nlg.py — Evaluación empírica de la capa NLG (Generación de Lenguaje Natural)
mediante metodología LLM-as-a-Judge.

Ejecuta 19 turnos conversacionales representativos a través de `MistralClient.generar_nlg()`,
almacena los datos y la respuesta obtenida, y utiliza un LLM como juez independiente
para puntuar de 1 a 5 cada respuesta en 3 dimensiones:
  1. Fidelidad a la decisión simbólica
  2. Fundamentación y precisión factual
  3. Calidad comunicativa
"""

import csv
import json
import logging
import os
import sys
import time
from pydantic import BaseModel, Field

# Asegurar importación del backend
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
backend_dir = os.path.join(project_root, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.clients.mistral_client import MistralClient
from mistralai.client.models import UserMessage, SystemMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CSV_OUTPUT_PATH = os.path.join(current_dir, "nlg_evaluation.csv")


# ────────────────────────────────────────────────────────────────────────────
# Esquemas Pydantic para la evaluación del LLM Judge
# ────────────────────────────────────────────────────────────────────────────

class DimensionEvaluation(BaseModel):
    justification: str = Field(description="Explicación detallada de la puntuación otorgada.")
    score: int = Field(description="Calificación entera de 1 a 5 según la rúbrica.", ge=1, le=5)


class JudgeEvaluation(BaseModel):
    fidelidad_decision: DimensionEvaluation
    precision_factual: DimensionEvaluation
    calidad_comunicativa: DimensionEvaluation


# ────────────────────────────────────────────────────────────────────────────
# Prompt de evaluación del LLM Judge
# ────────────────────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """Eres un evaluador experto e imparcial de sistemas de diálogo para banca y originación de crédito (LLM-as-a-Judge).
Tu misión es evaluar con rigor técnico y objetividad la calidad de una respuesta en lenguaje natural generada por un componente NLG de un asistente bancario.

Recibirás:
1. El mensaje del usuario.
2. El volcado exacto del estado del sistema (Information State y evaluación Drools) que se proporcionó al NLG como entrada de solo lectura.
3. La respuesta textual generada por el NLG para el cliente.

Debes calificar la respuesta de 1 a 5 en TRES dimensiones independientes:

DIMENSIÓN 1: FIDELIDAD A LA DECISIÓN SIMBÓLICA (fidelidad_decision)
- Qué evalúa: Si la respuesta comunica correctamente el resultado de Drools, incluidos los estados provisionales, las condiciones y los siguientes pasos necesarios.
- Criterios:
  * 5: Comunica la decisión exacta (APROBADO, DENEGADO, REQUIERE_DATOS, etc.) con total fidelidad y orienta con precisión sobre los siguientes pasos.
  * 4: Comunica la decisión sustancialmente bien, pero omite un detalle menor de los pasos siguientes.
  * 3: Comunica la decisión de forma ambigua o poco clara, aunque sin contradecirla abiertamente.
  * 2: Confunde el estado o da instrucciones contradictorias con la decisión del motor.
  * 1: Contradice totalmente la decisión de Drools (ej. felicita por aprobación cuando está denegado).

DIMENSIÓN 2: FUNDAMENTACIÓN Y PRECISIÓN FACTUAL (precision_factual)
- Qué evalúa: Si las afirmaciones están respaldadas por el Information State y la evaluación recibida, sin inventar datos, motivos, consultas realizadas ni condiciones.
- Criterios:
  * 5: Totalmente anclada en el estado. No inventa números, no inventa normas legales si texto_legal es nulo, y no revela nombres técnicos internos de reglas.
  * 4: Factualmente correcta, aunque incluye alguna frase de cortesía genérica no respaldada pero inofensiva.
  * 3: Incluye algún dato dudoso, asume condiciones no especificadas o menciona detalles legales no presentes en el estado.
  * 2: Presenta alucinaciones notables (inventa cantidades, plazos o motivos de denegación no existentes en el estado).
  * 1: Alucinación grave o invención total de cifras y normativas.

DIMENSIÓN 3: CALIDAD COMUNICATIVA (calidad_comunicativa)
- Qué evalúa: Si la respuesta es clara, pertinente, suficientemente completa, respetuosa y adecuada a la situación conversacional.
- Criterios:
  * 5: Tono impecable según lo requerido (profesional, respetuoso, trato formal de usted), mensaje conciso, claro, empático y orientado al cliente.
  * 4: Mensaje claro y educado, pero ligeramente redundante o con un estilo algo frío/robótico.
  * 3: Mensaje comprensible pero excesivamente prolijo, demasiado escueto o con un tono que no encaja del todo con la situación.
  * 2: Mensaje confuso, gramaticalmente deficiente o con un tono inadecuado (ej. coloquial excesivo o tuteo).
  * 1: Mensaje ininteligible, grosero o totalmente inadecuado para un contexto bancario.

Devuelve tu evaluación en formato estructurado JSON con la justificación y nota de cada dimensión.
"""


# ────────────────────────────────────────────────────────────────────────────
# Definición de los 20 Casos de Prueba Representativos
# ────────────────────────────────────────────────────────────────────────────

def get_test_cases() -> list[dict]:
    return [
        # Caso 1: Aprobación estándar de préstamo para vehículo
        {
            "id": 1,
            "mensaje_usuario": "Quiero pedir un préstamo de 8000 euros a 36 meses para comprarme un coche",
            "state": {
                "evaluacion_drools": {
                    "estado": "APROBADO",
                    "reglas_disparadas": ["R_APROBACION_ESTANDAR"],
                    "tono_mensaje": "positivo, claro y profesional",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Art. 18.1 Directiva 2014/17/UE - Evaluación de solvencia positiva",
                    "texto_legal": "Tras la evaluación completa de la solvencia del solicitante conforme al artículo 18.1 de la Directiva 2014/17/UE, se ha verificado que la capacidad de pago es adecuada: el ratio de endeudamiento se encuentra dentro de los límites prudenciales, el remanente de subsistencia garantiza el mínimo vital y no se registran incidencias de morosidad activa. La solicitud cumple los requisitos para su aprobación.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 8000.0,
                    "plazo_meses": 36,
                    "proposito": "VEHICULO",
                    "gastos_fijos_mensuales": 450.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 222.22,
                    "ratio_endeudamiento": 0.24,
                    "remanente_subsistencia": 1900.0,
                    "edad_al_vencimiento": 33,
                },
            },
        },
        # Caso 2: Denegación por DTI excesivo (> 40%)
        {
            "id": 2,
            "mensaje_usuario": "Necesito 15.000 euros a 24 meses para hacer reformas en mi casa",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_RATIO_ENDEUDAMIENTO"],
                    "tono_mensaje": "firme, claro y respetuoso",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Art. 18 Directiva 2014/17/UE y criterios del Banco de España",
                    "texto_legal": "El ratio máximo de endeudamiento no debe exceder el 40% de los ingresos netos mensuales del solicitante. La cuota de este préstamo, sumada a sus compromisos de pago actuales, supera dicho umbral, lo que indica que la carga financiera resultante podría comprometer su capacidad de hacer frente a las obligaciones de pago.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 15000.0,
                    "plazo_meses": 24,
                    "proposito": "REFORMA",
                    "gastos_fijos_mensuales": 500.0,
                    "deuda_declarada": 200.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 625.0,
                    "ratio_endeudamiento": 0.52,
                    "remanente_subsistencia": 680.0,
                    "edad_al_vencimiento": 42,
                },
            },
        },
        # Caso 3: Denegación por mínimo de subsistencia (< 700€)
        {
            "id": 3,
            "mensaje_usuario": "Quisiera solicitar 4000 euros a 12 meses para pagar un máster",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_MINIMO_SUBSISTENCIA"],
                    "tono_mensaje": "serio, prudente y respetuoso",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Art. 607 LEC - Mínimo vital inembargable derivado del Salario Mínimo Interprofesional",
                    "texto_legal": "Tras asumir la cuota del préstamo solicitado y el resto de compromisos financieros activos, el remanente mensual disponible quedaría por debajo del mínimo de subsistencia establecido en el artículo 607 de la Ley de Enjuiciamiento Civil, derivado del Salario Mínimo Interprofesional. Esta entidad no puede conceder financiación que comprometa el mínimo vital necesario para el sustento del solicitante.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 4000.0,
                    "plazo_meses": 12,
                    "proposito": "ESTUDIOS",
                    "gastos_fijos_mensuales": 400.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 333.33,
                    "ratio_endeudamiento": 0.38,
                    "remanente_subsistencia": 616.67,
                    "edad_al_vencimiento": 26,
                },
            },
        },
        # Caso 4: Denegación por propósito criptomonedas
        {
            "id": 4,
            "mensaje_usuario": "Quiero 10000 euros a 24 meses para invertir en bitcoin y ethereum",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_PROPOSITO_NO_FINANCIABLE"],
                    "tono_mensaje": "firme, profesional y no acusatorio",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Ley 10/2010 PBC y directrices EBA sobre originación de crédito prudencial",
                    "texto_legal": "El propósito declarado para el préstamo solicitado no se encuentra entre las finalidades financiables por esta entidad, de conformidad con la normativa de prevención del blanqueo de capitales (Ley 10/2010) y las directrices de la Autoridad Bancaria Europea (EBA) sobre originación prudencial de crédito.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 10000.0,
                    "plazo_meses": 24,
                    "proposito": "CRIPTOMONEDAS",
                    "gastos_fijos_mensuales": 300.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 416.67,
                    "ratio_endeudamiento": 0.28,
                    "remanente_subsistencia": 1250.0,
                    "edad_al_vencimiento": 35,
                },
            },
        },
        # Caso 5: Denegación por propósito apuestas
        {
            "id": 5,
            "mensaje_usuario": "Necesito 3000 euros a 12 meses para apuestas deportivas y juegos online",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_PROPOSITO_NO_FINANCIABLE"],
                    "tono_mensaje": "firme, profesional y no acusatorio",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Ley 10/2010 PBC y directrices EBA sobre originación de crédito prudencial",
                    "texto_legal": "El propósito declarado para el préstamo solicitado no se encuentra entre las finalidades financiables por esta entidad, de conformidad con la normativa de prevención del blanqueo de capitales (Ley 10/2010) y las directrices de la Autoridad Bancaria Europea (EBA) sobre originación prudencial de crédito.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 3000.0,
                    "plazo_meses": 12,
                    "proposito": "APUESTAS",
                    "gastos_fijos_mensuales": 200.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 250.0,
                    "ratio_endeudamiento": 0.20,
                    "remanente_subsistencia": 1400.0,
                    "edad_al_vencimiento": 29,
                },
            },
        },
        # Caso 6: Denegación por refinanciación informal
        {
            "id": 6,
            "mensaje_usuario": "Busco 5000 euros en 18 meses para saldar una deuda con un prestamista privado",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_PROPOSITO_NO_FINANCIABLE"],
                    "tono_mensaje": "firme, profesional y no acusatorio",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Ley 10/2010 PBC y directrices EBA sobre originación de crédito prudencial",
                    "texto_legal": "El propósito declarado para el préstamo solicitado no se encuentra entre las finalidades financiables por esta entidad, de conformidad con la normativa de prevención del blanqueo de capitales (Ley 10/2010) y las directrices de la Autoridad Bancaria Europea (EBA) sobre originación prudencial de crédito.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 5000.0,
                    "plazo_meses": 18,
                    "proposito": "REFINANCIACION_INFORMAL",
                    "gastos_fijos_mensuales": 350.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 277.78,
                    "ratio_endeudamiento": 0.22,
                    "remanente_subsistencia": 1350.0,
                    "edad_al_vencimiento": 38,
                },
            },
        },
        # Caso 7: Denegación por edad mínima (< 18 años)
        {
            "id": 7,
            "mensaje_usuario": "Hola, tengo 17 años y quiero pedir 1000 euros a 12 meses para sacarme el carnet de conducir",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_EDAD_MINIMA"],
                    "tono_mensaje": "firme, claro y respetuoso",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Criterios de capacidad legal y riesgo actuarial",
                    "texto_legal": "Los préstamos personales no pueden concederse a personas menores de 18 años, ya que carecen de plena capacidad jurídica para contraer obligaciones financieras según la legislación vigente.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 1000.0,
                    "plazo_meses": 12,
                    "proposito": "VEHICULO",
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {
                    "cuota_estimada": 83.33,
                    "ratio_endeudamiento": None,
                    "remanente_subsistencia": None,
                    "edad_al_vencimiento": 18,
                },
            },
        },
        # Caso 8: Denegación por edad máxima al vencimiento (> 75 años)
        {
            "id": 8,
            "mensaje_usuario": "Buenas, tengo 73 años y me gustaría solicitar 6000 euros a 48 meses para arreglar el tejado",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_EDAD_MAXIMA"],
                    "tono_mensaje": "claro, respetuoso y transparente",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Criterios de capacidad legal y riesgo actuarial por edad",
                    "texto_legal": "Al vencimiento del préstamo, la edad del solicitante superaría los 75 años. Por criterios de riesgo actuarial, la entidad no puede conceder préstamos cuya devolución finalice más allá de dicha edad límite.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 6000.0,
                    "plazo_meses": 48,
                    "proposito": "REFORMA",
                    "gastos_fijos_mensuales": 300.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 125.0,
                    "ratio_endeudamiento": 0.18,
                    "remanente_subsistencia": 1500.0,
                    "edad_al_vencimiento": 77,
                },
            },
        },
        # Caso 9: Denegación por morosidad activa en ASNEF
        {
            "id": 9,
            "mensaje_usuario": "Requiero 3500 euros a 24 meses para una intervención dental urgente",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_MOROSIDAD_ASNEF"],
                    "tono_mensaje": "firme, profesional y especialmente cuidadoso",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Criterios prudenciales de morosidad crediticia",
                    "texto_legal": "Los registros consultados en los ficheros de solvencia patrimonial reflejan la existencia de obligaciones de pago impagadas o situaciones de morosidad activa. De conformidad con los criterios prudenciales de riesgo crediticio, no es posible conceder nueva financiación en esta situación.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 3500.0,
                    "plazo_meses": 24,
                    "proposito": "SALUD",
                    "gastos_fijos_mensuales": 400.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 145.83,
                    "ratio_endeudamiento": 0.25,
                    "remanente_subsistencia": 1200.0,
                    "edad_al_vencimiento": 45,
                },
            },
        },
        # Caso 10: Denegación por avalista de empresa en concurso
        {
            "id": 10,
            "mensaje_usuario": "Quisiera pedir 12000 euros a 36 meses para comprar un vehículo nuevo",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_ALERTA_QUIEBRA_AVAL"],
                    "tono_mensaje": "serio, prudente y respetuoso",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Criterios EBA sobre riesgo concursal indirecto",
                    "texto_legal": "Se ha detectado que el solicitante actúa como avalista de una empresa que se encuentra actualmente en situación de concurso de acreedores. Esta circunstancia genera un riesgo concursal indirecto exigible a corto plazo que impide la concesión de nueva financiación, de conformidad con los criterios de la Autoridad Bancaria Europea (EBA).",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 12000.0,
                    "plazo_meses": 36,
                    "proposito": "VEHICULO",
                    "gastos_fijos_mensuales": 400.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 333.33,
                    "ratio_endeudamiento": 0.30,
                    "remanente_subsistencia": 1700.0,
                    "edad_al_vencimiento": 52,
                },
            },
        },
        # Caso 11: Requiere datos: Faltan cantidad y plazo (sin texto legal)
        {
            "id": 11,
            "mensaje_usuario": "Hola, me gustaría solicitar un préstamo personal para reformar la cocina",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_DATOS",
                    "reglas_disparadas": ["R_CANTIDAD_Y_PLAZO_REQUERIDOS"],
                    "tono_mensaje": "amable, orientativo y conciso",
                    "dato_faltante": "cantidad_solicitada y plazo_meses",
                    "accion_requerida": None,
                    "articulo_normativo": None,
                    "texto_legal": None,
                },
                "datos_usuario": {
                    "cantidad_solicitada": None,
                    "plazo_meses": None,
                    "proposito": "REFORMA",
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
        # Caso 12: Requiere datos: Falta solo plazo en meses
        {
            "id": 12,
            "mensaje_usuario": "Necesito unos 6000 euros para comprar una moto de segunda mano",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_DATOS",
                    "reglas_disparadas": ["R_CANTIDAD_Y_PLAZO_REQUERIDOS"],
                    "tono_mensaje": "amable, orientativo y conciso",
                    "dato_faltante": "plazo_meses",
                    "accion_requerida": None,
                    "articulo_normativo": None,
                    "texto_legal": None,
                },
                "datos_usuario": {
                    "cantidad_solicitada": 6000.0,
                    "plazo_meses": None,
                    "proposito": "VEHICULO",
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
        # Caso 13: Requiere datos: Falta solo cantidad solicitada
        {
            "id": 13,
            "mensaje_usuario": "Quiero devolver el préstamo en 24 meses para hacer un curso de desarrollo web",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_DATOS",
                    "reglas_disparadas": ["R_CANTIDAD_Y_PLAZO_REQUERIDOS"],
                    "tono_mensaje": "amable, orientativo y conciso",
                    "dato_faltante": "cantidad_solicitada",
                    "accion_requerida": None,
                    "articulo_normativo": None,
                    "texto_legal": None,
                },
                "datos_usuario": {
                    "cantidad_solicitada": None,
                    "plazo_meses": 24,
                    "proposito": "ESTUDIOS",
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
        # Caso 14: Requiere datos: Falta propósito
        {
            "id": 14,
            "mensaje_usuario": "Necesito un préstamo de 10000 euros a pagar en 48 meses",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_DATOS",
                    "reglas_disparadas": ["R_PROPOSITO_REQUERIDO"],
                    "tono_mensaje": "amable, cercano y orientativo",
                    "dato_faltante": "proposito",
                    "accion_requerida": None,
                    "articulo_normativo": None,
                    "texto_legal": None,
                },
                "datos_usuario": {
                    "cantidad_solicitada": 10000.0,
                    "plazo_meses": 48,
                    "proposito": None,
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
        # Caso 15: Requiere datos: Faltan gastos fijos mensuales
        {
            "id": 15,
            "mensaje_usuario": "Quiero 5000 euros a 24 meses para una operación dental",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_DATOS",
                    "reglas_disparadas": ["R_GASTOS_FIJOS_REQUERIDOS"],
                    "tono_mensaje": "amable, sencillo y orientativo",
                    "dato_faltante": "gastos_fijos_mensuales",
                    "accion_requerida": None,
                    "articulo_normativo": "Art. 18 Directiva 2014/17/UE",
                    "texto_legal": "Para evaluar su solvencia conforme al Art. 18 de la Directiva 2014/17/UE, necesitamos conocer sus gastos fijos mensuales. Nos referimos a compromisos periódicos ineludibles como el alquiler, los gastos de suministros (luz, agua, gas), seguros u otros recibos fijos. No incluya aquí sus deudas o préstamos, ya que se recogen por separado.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 5000.0,
                    "plazo_meses": 24,
                    "proposito": "SALUD",
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
        # Caso 16: Requiere supervisión humana: Discrepancia CIRBE > 35%
        {
            "id": 16,
            "mensaje_usuario": "Declaré que tengo unos 1000 euros pendientes en una tarjeta de crédito",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_SUPERVISION_HUMANA",
                    "reglas_disparadas": ["R_DISCREPANCIA_DECLARADA"],
                    "tono_mensaje": "neutral, prudente y no acusatorio",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Art. 14 EU AI Act - Supervisión humana ante anomalías no resueltas",
                    "texto_legal": "Se ha detectado una discrepancia significativa entre la deuda declarada por el solicitante y los datos registrados en los ficheros de solvencia patrimonial (CIRBE). De conformidad con el artículo 14 del Reglamento de Inteligencia Artificial de la UE (EU AI Act), esta anomalía requiere revisión por parte de un analista de riesgos antes de que pueda emitirse una decisión automatizada.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 6000.0,
                    "plazo_meses": 24,
                    "proposito": "REFORMA",
                    "gastos_fijos_mensuales": 400.0,
                    "deuda_declarada": 1000.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 250.0,
                    "ratio_endeudamiento": 0.32,
                    "remanente_subsistencia": 1400.0,
                    "edad_al_vencimiento": 39,
                },
            },
        },
        # Caso 17: Aprobación estándar de crédito rápido de salud
        {
            "id": 17,
            "mensaje_usuario": "Necesito 1500 euros a 12 meses para ponerme unas gafas graduadas y empastes",
            "state": {
                "evaluacion_drools": {
                    "estado": "APROBADO",
                    "reglas_disparadas": ["R_APROBACION_ESTANDAR"],
                    "tono_mensaje": "positivo, claro y profesional",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": "Art. 18.1 Directiva 2014/17/UE - Evaluación de solvencia positiva",
                    "texto_legal": "Tras la evaluación completa de la solvencia del solicitante conforme al artículo 18.1 de la Directiva 2014/17/UE, se ha verificado que la capacidad de pago es adecuada: el ratio de endeudamiento se encuentra dentro de los límites prudenciales, el remanente de subsistencia garantiza el mínimo vital y no se registran incidencias de morosidad activa. La solicitud cumple los requisitos para su aprobación.",
                },
                "datos_usuario": {
                    "cantidad_solicitada": 1500.0,
                    "plazo_meses": 12,
                    "proposito": "SALUD",
                    "gastos_fijos_mensuales": 300.0,
                    "deuda_declarada": 0.0,
                },
                "calculos_derivados": {
                    "cuota_estimada": 125.0,
                    "ratio_endeudamiento": 0.16,
                    "remanente_subsistencia": 1850.0,
                    "edad_al_vencimiento": 34,
                },
            },
        },
        # Caso 18: Denegación por edad mínima SIN texto legal disponible (probar contención factual)
        {
            "id": 18,
            "mensaje_usuario": "Tengo 16 años y quiero 500 euros para comprar una consola de videojuegos",
            "state": {
                "evaluacion_drools": {
                    "estado": "DENEGADO",
                    "reglas_disparadas": ["R_EDAD_MINIMA"],
                    "tono_mensaje": "firme, claro y respetuoso",
                    "dato_faltante": None,
                    "accion_requerida": None,
                    "articulo_normativo": None,
                    "texto_legal": None,
                },
                "datos_usuario": {
                    "cantidad_solicitada": 500.0,
                    "plazo_meses": 6,
                    "proposito": "OTRO",
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
        # Caso 19: Requiere datos: Saludo previo con cantidad, falta plazo
        {
            "id": 19,
            "mensaje_usuario": "Buenos días, quería solicitar un préstamo de doce mil euros",
            "state": {
                "evaluacion_drools": {
                    "estado": "REQUIERE_DATOS",
                    "reglas_disparadas": ["R_CANTIDAD_Y_PLAZO_REQUERIDOS"],
                    "tono_mensaje": "amable, orientativo y conciso",
                    "dato_faltante": "plazo_meses",
                    "accion_requerida": None,
                    "articulo_normativo": None,
                    "texto_legal": None,
                },
                "datos_usuario": {
                    "cantidad_solicitada": 12000.0,
                    "plazo_meses": None,
                    "proposito": None,
                    "gastos_fijos_mensuales": None,
                    "deuda_declarada": None,
                },
                "calculos_derivados": {},
            },
        },
    ]


# ────────────────────────────────────────────────────────────────────────────
# Pipeline de Evaluación y Ejecución
# ────────────────────────────────────────────────────────────────────────────

def run_evaluation():
    print("=" * 80)
    print(" EVALUACIÓN DE LA CAPA NLG (MISTRAL AI) MEDIANTE LLM-AS-A-JUDGE")
    print("=" * 80)

    client = MistralClient()
    test_cases = get_test_cases()
    results = []

    print(f"\nIniciando generación y juicio para {len(test_cases)} casos...\n")

    for idx, tc in enumerate(test_cases, start=1):
        case_id = tc["id"]
        msg = tc["mensaje_usuario"]
        state = tc["state"]
        eval_drools = state.get("evaluacion_drools", {})
        estado = eval_drools.get("estado")
        regla = ", ".join(eval_drools.get("reglas_disparadas", []))

        print(f"[{idx:02d}/{len(test_cases)}] Procesando Caso ID {case_id}: Estado Drools='{estado}', Regla='{regla}'")
        print(f"       Mensaje usuario: \"{msg}\"")

        # 1. Generar la respuesta mediante MistralClient.generar_nlg()
        t0 = time.time()
        try:
            respuesta_nlg = client.generar_nlg(state=state, mensaje_usuario=msg)
        except Exception as e:
            logger.error("Error al generar NLG para caso %d: %s", case_id, e)
            respuesta_nlg = f"ERROR_GENERACION: {e}"
        t_gen = time.time() - t0

        print(f"       Respuesta NLG ({t_gen:.2f}s): \"{respuesta_nlg}\"")

        # Reconstruir el contexto exacto inyectado a contexto_estado para el juez
        datos_u = state.get("datos_usuario", {})
        calculos = state.get("calculos_derivados", {})
        contexto_inyectado = f"""ESTADO DE EVALUACIÓN: {estado}
REGLAS DISPARADAS: {regla}
TONO REQUERIDO: {eval_drools.get('tono_mensaje')}
DATO FALTANTE: {eval_drools.get('dato_faltante') or 'Ninguno'}
ACCIÓN REQUERIDA: {eval_drools.get('accion_requerida') or 'Ninguna'}
DATOS FINANCIEROS:
- Cantidad solicitada: {datos_u.get('cantidad_solicitada')} EUR
- Plazo: {datos_u.get('plazo_meses')} meses
- Propósito: {datos_u.get('proposito')}
- Cuota estimada: {calculos.get('cuota_estimada')} EUR/mes
- Ratio de endeudamiento: {calculos.get('ratio_endeudamiento')}
- Remanente: {calculos.get('remanente_subsistencia')} EUR/mes
JUSTIFICACIÓN NORMATIVA:
- Artículo: {eval_drools.get('articulo_normativo') or 'NO DISPONIBLE'}
- Texto legal: {eval_drools.get('texto_legal') or 'NO DISPONIBLE'}"""

        # 2. Invocar al LLM Judge mediante chat.parse()
        prompt_juez = f"""Evalúa la siguiente respuesta generada por el NLG basándote en la información disponible:

=== INFORMACIÓN DISPONIBLE ===
MENSAJE DEL USUARIO:
"{msg}"

ESTADO DEL SISTEMA (SOLO LECTURA):
{contexto_inyectado}

RESPUESTA GENERADA POR EL NLG:
"{respuesta_nlg}"
==============================

Emite tu evaluación en formato JSON estructurado con las 3 dimensiones (fidelidad_decision, precision_factual, calidad_comunicativa).
"""

        t0 = time.time()
        max_retries = 3
        eval_judge = None
        for attempt in range(max_retries):
            try:
                judge_response = client._client.chat.parse(
                    model=client._model,
                    response_format=JudgeEvaluation,
                    messages=[
                        SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                        UserMessage(content=prompt_juez),
                    ],
                    temperature=0.0,
                )
                eval_judge: JudgeEvaluation = judge_response.choices[0].message.parsed
                break
            except Exception as e:
                logger.warning("Reintento %d/%d del juez para caso %d: %s", attempt + 1, max_retries, case_id, e)
                time.sleep(2)

        t_judge = time.time() - t0

        if eval_judge:
            sc_fid = eval_judge.fidelidad_decision.score
            just_fid = eval_judge.fidelidad_decision.justification
            sc_prec = eval_judge.precision_factual.score
            just_prec = eval_judge.precision_factual.justification
            sc_cal = eval_judge.calidad_comunicativa.score
            just_cal = eval_judge.calidad_comunicativa.justification
            sc_prom = round((sc_fid + sc_prec + sc_cal) / 3.0, 2)
            print(f"       Juez ({t_judge:.2f}s) -> Fidelidad: {sc_fid}/5 | Precisión: {sc_prec}/5 | Calidad: {sc_cal}/5 -> Promedio: {sc_prom}/5\n")
        else:
            sc_fid = sc_prec = sc_cal = sc_prom = 0
            just_fid = just_prec = just_cal = "ERROR_JUEZ"
            print("       [ERROR] El juez no pudo emitir veredicto.\n")

        row = {
            "id": case_id,
            "mensaje_usuario": msg,
            "estado_drools": estado,
            "regla_disparada": regla,
            "dato_faltante": eval_drools.get("dato_faltante") or "",
            "accion_requerida": eval_drools.get("accion_requerida") or "",
            "articulo_normativo": eval_drools.get("articulo_normativo") or "",
            "texto_legal": eval_drools.get("texto_legal") or "",
            "tono_requerido": eval_drools.get("tono_mensaje") or "",
            "respuesta_nlg": respuesta_nlg,
            "score_fidelidad": sc_fid,
            "justificacion_fidelidad": just_fid,
            "score_precision": sc_prec,
            "justificacion_precision": just_prec,
            "score_calidad": sc_cal,
            "justificacion_calidad": just_cal,
            "score_promedio": sc_prom,
        }
        results.append(row)
        time.sleep(1)

    # 3. Guardar resultados en CSV
    fieldnames = list(results[0].keys())
    with open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[ÉXITO] Resultados guardados en: {CSV_OUTPUT_PATH}")

    # 4. Estadísticas consolidadas
    avg_fid = sum(r["score_fidelidad"] for r in results) / len(results)
    avg_prec = sum(r["score_precision"] for r in results) / len(results)
    avg_cal = sum(r["score_calidad"] for r in results) / len(results)
    avg_global = sum(r["score_promedio"] for r in results) / len(results)

    print("\n" + "=" * 80)
    print(" RESUMEN ESTADÍSTICO DE EVALUACIÓN NLG (LLM-AS-A-JUDGE)")
    print("=" * 80)
    print(f"1. Fidelidad a la decisión simbólica : {avg_fid:.2f} / 5.00")
    print(f"2. Fundamentación y precisión factual: {avg_prec:.2f} / 5.00")
    print(f"3. Calidad comunicativa              : {avg_cal:.2f} / 5.00")
    print("-" * 80)
    print(f" PUNTUACIÓN MEDIA GLOBAL             : {avg_global:.2f} / 5.00")
    print("=" * 80)

    # Identificar casos con puntuación menor a 5
    casos_imperfectos = [r for r in results if r["score_fidelidad"] < 5 or r["score_precision"] < 5 or r["score_calidad"] < 5]
    print(f"\nCasos con deducciones (nota < 5 en alguna dimensión): {len(casos_imperfectos)} de {len(results)}")
    for ci in casos_imperfectos:
        print(f" - ID {ci['id']:02d} ({ci['estado_drools']}): Prom={ci['score_promedio']} | Fid={ci['score_fidelidad']}, Prec={ci['score_precision']}, Cal={ci['score_calidad']}")
        if ci["score_fidelidad"] < 5:
            print(f"     Fidelidad ({ci['score_fidelidad']}/5): {ci['justificacion_fidelidad']}")
        if ci["score_precision"] < 5:
            print(f"     Precisión ({ci['score_precision']}/5): {ci['justificacion_precision']}")
        if ci["score_calidad"] < 5:
            print(f"     Calidad ({ci['score_calidad']}/5): {ci['justificacion_calidad']}")


if __name__ == "__main__":
    run_evaluation()
