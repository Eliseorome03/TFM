"""
evaluate_nlu.py — Evaluación empírica de la capa NLU de Mistral AI.

Lee las 50 muestras de 'nlu_ground_truth.csv', ejecuta la extracción de entidades
utilizando la clase oficial `MistralClient` del backend (con idénticos system prompt,
schema Pydantic EsquemaNLU y temperatura 0.0), y guarda las predicciones fila a fila
en 'nlu_predictions.csv'.
"""

import csv
import sys
import os
import time

# Configurar path para importar módulos del backend
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
backend_dir = os.path.join(project_root, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.clients.mistral_client import MistralClient
from app.schemas.nlu import EsquemaNLU

GROUND_TRUTH_PATH = os.path.join(current_dir, "nlu_ground_truth.csv")
PREDICTIONS_PATH = os.path.join(current_dir, "nlu_predictions.csv")


def main():
    print("==========================================================================")
    print(" INICIANDO EVALUACIÓN DE LA CAPA NLU (MISTRAL AI)")
    print(f" Dataset de entrada : {GROUND_TRUTH_PATH}")
    print(f" Archivo de salida  : {PREDICTIONS_PATH}")
    print("==========================================================================\n")

    if not os.path.exists(GROUND_TRUTH_PATH):
        print(f"[ERROR] No se encuentra el archivo {GROUND_TRUTH_PATH}")
        sys.exit(1)

    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ground_truth_rows = list(reader)

    total_samples = len(ground_truth_rows)
    print(f"Total de mensajes a evaluar: {total_samples}")

    client = MistralClient()

    output_fieldnames = [
        "id",
        "mensaje",
        "pred_intencion_principal",
        "pred_cantidad_solicitada",
        "pred_plazo_meses",
        "pred_proposito",
        "pred_gastos_fijos_mensuales",
        "pred_deuda_declarada",
        "pred_duda_catch_all"
    ]

    with open(PREDICTIONS_PATH, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=output_fieldnames)
        writer.writeheader()

        for idx, row in enumerate(ground_truth_rows, start=1):
            msg_id = row["id"]
            mensaje = row["mensaje"]

            print(f"[{idx:02d}/{total_samples:02d}] Procesando ID {msg_id}: \"{mensaje[:60]}...\"")

            # Inferencia con reintentos defensivos por posible saturación de API
            max_retries = 3
            res: EsquemaNLU | None = None
            for attempt in range(max_retries):
                try:
                    res = client.extraer_nlu(mensaje)
                    break
                except Exception as e:
                    print(f"   [AVISO] Reintento {attempt + 1}/{max_retries} por error: {e}")
                    time.sleep(2 * (attempt + 1))

            if res is None:
                print(f"   [ERROR] Fallo en la inferencia para el mensaje ID {msg_id}")
                pred_dict = {
                    "id": msg_id,
                    "mensaje": mensaje,
                    "pred_intencion_principal": "ERROR",
                    "pred_cantidad_solicitada": None,
                    "pred_plazo_meses": None,
                    "pred_proposito": None,
                    "pred_gastos_fijos_mensuales": None,
                    "pred_deuda_declarada": None,
                    "pred_duda_catch_all": "ERROR"
                }
            else:
                pred_dict = {
                    "id": msg_id,
                    "mensaje": mensaje,
                    "pred_intencion_principal": res.intencion_principal.value if res.intencion_principal else None,
                    "pred_cantidad_solicitada": res.cantidad_solicitada,
                    "pred_plazo_meses": res.plazo_meses,
                    "pred_proposito": res.proposito.value if res.proposito else None,
                    "pred_gastos_fijos_mensuales": res.gastos_fijos_mensuales,
                    "pred_deuda_declarada": res.deuda_declarada,
                    "pred_duda_catch_all": res.duda_catch_all.value if res.duda_catch_all else None
                }

            writer.writerow(pred_dict)
            out_f.flush()

            print(f"   -> Extraído: Intención={pred_dict['pred_intencion_principal']}, "
                  f"Cant={pred_dict['pred_cantidad_solicitada']}, "
                  f"Plazo={pred_dict['pred_plazo_meses']}, "
                  f"Prop={pred_dict['pred_proposito']}, "
                  f"Gastos={pred_dict['pred_gastos_fijos_mensuales']}, "
                  f"Deuda={pred_dict['pred_deuda_declarada']}")

            # Pausa breve para respetar rate limits de la API
            time.sleep(0.3)

    print("\n==========================================================================")
    print(f" [ÉXITO] Predicciones guardadas exitosamente en {PREDICTIONS_PATH}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
