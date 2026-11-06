"""
evaluate_nlg_gemini.py — Evaluación empírica de la capa NLG mediante Gemini como LLM-as-a-Judge.

Reconstruye el contexto EXACTO inyectado (incluidos los datos financieros y cálculos derivados
procedentes de `get_test_cases()`) junto con la respuesta generada almacenada en `nlg_evaluation.csv`,
y solicita a Gemini (gemini-3.5-flash-lite) la evaluación en 3 dimensiones:
  1. Fidelidad a la decisión simbólica
  2. Fundamentación y precisión factual
  3. Calidad comunicativa

Los resultados se almacenan en `nlg_evaluation_gemini.csv`.
"""

import csv
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from evaluate_nlg import get_test_cases, JUDGE_SYSTEM_PROMPT

CSV_INPUT_PATH = os.path.join(CURRENT_DIR, "nlg_evaluation.csv")
CSV_OUTPUT_PATH = os.path.join(CURRENT_DIR, "nlg_evaluation_gemini.csv")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise EnvironmentError(
        "No se ha configurado la variable de entorno GEMINI_API_KEY"
    )

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "fidelidad_decision": {
            "type": "OBJECT",
            "properties": {
                "justification": {"type": "STRING"},
                "score": {"type": "INTEGER"}
            },
            "required": ["justification", "score"]
        },
        "precision_factual": {
            "type": "OBJECT",
            "properties": {
                "justification": {"type": "STRING"},
                "score": {"type": "INTEGER"}
            },
            "required": ["justification", "score"]
        },
        "calidad_comunicativa": {
            "type": "OBJECT",
            "properties": {
                "justification": {"type": "STRING"},
                "score": {"type": "INTEGER"}
            },
            "required": ["justification", "score"]
        }
    },
    "required": ["fidelidad_decision", "precision_factual", "calidad_comunicativa"]
}


def call_gemini_judge(prompt_juez: str, api_key: str, model: str = GEMINI_MODEL) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
    }
    payload = {
        "system_instruction": {
            "parts": [{"text": JUDGE_SYSTEM_PROMPT}]
        },
        "contents": [
            {"parts": [{"text": prompt_juez}]}
        ],
        "generationConfig": {
            "temperature": 0.0,
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=45.0) as response:
        result = json.loads(response.read().decode("utf-8"))

    candidates = result.get("candidates", [])
    if not candidates:
        raise ValueError(f"No se recibieron candidatos de Gemini: {result}")

    text_content = candidates[0]["content"]["parts"][0]["text"]
    return json.loads(text_content)


def run_gemini_evaluation():
    print("=" * 80)
    print(f" EVALUACIÓN DE LA CAPA NLG MEDIANTE {GEMINI_MODEL.upper()} (LLM-AS-A-JUDGE)")
    print("=" * 80)
    print(f"Modelo juez : {GEMINI_MODEL}")
    print(f"Fichero in  : {CSV_INPUT_PATH}")
    print(f"Fichero out : {CSV_OUTPUT_PATH}\n")

    # 1. Cargar las respuestas NLG previamente generadas
    respuestas_por_id = {}
    with open(CSV_INPUT_PATH, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        for r in reader:
            respuestas_por_id[int(r["id"])] = r["respuesta_nlg"]

    # 2. Cargar los test cases con el estado inmutable completo (incluidos datos financieros)
    test_cases = get_test_cases()
    print(f"Cargados {len(test_cases)} casos con contexto financiero completo para evaluar con Gemini...\n")

    results = []

    for idx, tc in enumerate(test_cases, start=1):
        case_id = tc["id"]
        msg = tc["mensaje_usuario"]
        state = tc["state"]
        eval_drools = state.get("evaluacion_drools", {})
        estado = eval_drools.get("estado")
        regla = ", ".join(eval_drools.get("reglas_disparadas", []))
        resp_nlg = respuestas_por_id.get(case_id, "")

        # Reconstruir EXACTAMENTE el mismo contexto inyectado que recibió Mistral
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

        prompt_juez = f"""Evalúa la siguiente respuesta generada por el NLG basándote en la información disponible:

=== INFORMACIÓN DISPONIBLE ===
MENSAJE DEL USUARIO:
"{msg}"

ESTADO DEL SISTEMA (SOLO LECTURA):
{contexto_inyectado}

RESPUESTA GENERADA POR EL NLG:
"{resp_nlg}"
==============================

Emite tu evaluación en formato JSON estructurado con las 3 dimensiones (fidelidad_decision, precision_factual, calidad_comunicativa).
"""

        print(f"[{idx:02d}/{len(test_cases)}] Evaluando Caso ID {case_id}: Estado='{estado}', Regla='{regla}'")

        eval_judge = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                eval_judge = call_gemini_judge(prompt_juez, api_key=GEMINI_API_KEY, model=GEMINI_MODEL)
                break
            except Exception as e:
                logger.warning("Reintento %d/%d para caso %d: %s", attempt + 1, max_retries, case_id, e)
                time.sleep(2)

        if eval_judge:
            sc_fid = int(eval_judge["fidelidad_decision"]["score"])
            just_fid = eval_judge["fidelidad_decision"]["justification"]
            sc_prec = int(eval_judge["precision_factual"]["score"])
            just_prec = eval_judge["precision_factual"]["justification"]
            sc_cal = int(eval_judge["calidad_comunicativa"]["score"])
            just_cal = eval_judge["calidad_comunicativa"]["justification"]
            sc_prom = round((sc_fid + sc_prec + sc_cal) / 3.0, 2)
            print(f"       Gemini -> Fid: {sc_fid}/5 | Prec: {sc_prec}/5 | Cal: {sc_cal}/5 -> Prom: {sc_prom}/5\n")
        else:
            sc_fid = sc_prec = sc_cal = sc_prom = 0
            just_fid = just_prec = just_cal = "ERROR_GEMINI"
            print("       [ERROR] No se pudo obtener veredicto de Gemini.\n")

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
            "respuesta_nlg": resp_nlg,
            "score_fidelidad": sc_fid,
            "justificacion_fidelidad": just_fid,
            "score_precision": sc_prec,
            "justificacion_precision": just_prec,
            "score_calidad": sc_cal,
            "justificacion_calidad": just_cal,
            "score_promedio": sc_prom,
        }
        results.append(row)

        time.sleep(5)

    # Guardar en nlg_evaluation_gemini.csv
    fieldnames = list(results[0].keys())
    with open(CSV_OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[ÉXITO] Resultados guardados en: {CSV_OUTPUT_PATH}")

    # Estadísticas
    avg_fid = sum(float(r["score_fidelidad"]) for r in results) / len(results)
    avg_prec = sum(float(r["score_precision"]) for r in results) / len(results)
    avg_cal = sum(float(r["score_calidad"]) for r in results) / len(results)
    avg_global = sum(float(r["score_promedio"]) for r in results) / len(results)

    print("\n" + "=" * 80)
    print(f" RESUMEN ESTADÍSTICO DE EVALUACIÓN NLG ({GEMINI_MODEL.upper()} COMO JUEZ)")
    print("=" * 80)
    print(f"1. Fidelidad a la decisión simbólica : {avg_fid:.2f} / 5.00")
    print(f"2. Fundamentación y precisión factual: {avg_prec:.2f} / 5.00")
    print(f"3. Calidad comunicativa              : {avg_cal:.2f} / 5.00")
    print("-" * 80)
    print(f" PUNTUACIÓN MEDIA GLOBAL             : {avg_global:.2f} / 5.00")
    print("=" * 80)

    for name, scs in [("Fidelidad", [float(r["score_fidelidad"]) for r in results]),
                      ("Precisión", [float(r["score_precision"]) for r in results]),
                      ("Calidad", [float(r["score_calidad"]) for r in results])]:
        dist = {k: scs.count(k) for k in [5.0, 4.0, 3.0, 2.0, 1.0]}
        print(f"  {name:10s}: 5s={dist[5.0]:2d}, 4s={dist[4.0]:2d}, 3s={dist[3.0]:2d}, 2s={dist[2.0]:2d}, 1s={dist[1.0]:2d}")

    casos_imperfectos = [r for r in results if float(r["score_fidelidad"]) < 5 or float(r["score_precision"]) < 5 or float(r["score_calidad"]) < 5]
    print(f"\nCasos con deducciones (nota < 5): {len(casos_imperfectos)} de {len(results)}")
    for ci in casos_imperfectos:
        print(f" - ID {int(ci['id']):02d} ({ci['estado_drools']}): Prom={ci['score_promedio']} | Fid={ci['score_fidelidad']}, Prec={ci['score_precision']}, Cal={ci['score_calidad']}")
        if float(ci["score_fidelidad"]) < 5:
            print(f"     Fidelidad ({ci['score_fidelidad']}/5): {ci['justificacion_fidelidad']}")
        if float(ci["score_precision"]) < 5:
            print(f"     Precisión ({ci['score_precision']}/5): {ci['justificacion_precision']}")
        if float(ci["score_calidad"]) < 5:
            print(f"     Calidad ({ci['score_calidad']}/5): {ci['justificacion_calidad']}")


if __name__ == "__main__":
    run_gemini_evaluation()
