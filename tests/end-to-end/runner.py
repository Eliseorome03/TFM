import os
import json
import urllib.request
import time
import uuid
import sys

BASE_URL = "http://localhost:8000/api/chat"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def init_dirs():
    for cat in ["cat1_nlu", "cat2_drools", "cat3_security"]:
        os.makedirs(os.path.join(BASE_DIR, cat), exist_ok=True)

def run_test_case(category, test_name, cliente_id, messages, expected_estado_final=None, extra_asserts=None):
    init_dirs()
    print(f"\n=========================================================")
    print(f" TEST: {test_name} ({category})")
    print(f"=========================================================")
    session_id = str(uuid.uuid4())
    transcript_path = os.path.join(BASE_DIR, category, f"{test_name}.txt")
    metrics_path = os.path.join(BASE_DIR, category, "metrics.txt")
    
    transcript = [f"=== TEST: {test_name} ===", f"Cliente ID: {cliente_id}", f"Session ID: {session_id}", ""]
    start_time = time.time()
    
    last_info_state = {}
    passed = True
    
    for i, msg in enumerate(messages):
        print(f"\n[Turno {i+1}] Usuario: {msg}")
        transcript.append(f"[Turno {i+1}] Usuario: {msg}")
        
        req = urllib.request.Request(BASE_URL, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        payload = {
            "session_id": session_id,
            "cliente_id": cliente_id,
            "mensaje": msg
        }
        
        try:
            with urllib.request.urlopen(req, data=json.dumps(payload).encode("utf-8")) as response:
                result = json.loads(response.read().decode("utf-8"))
                bot_msg = result.get("respuesta", "")
                last_info_state = result.get("information_state", {})
                
                print(f"[Turno {i+1}] Sistema: {bot_msg}")
                transcript.append(f"[Turno {i+1}] Sistema: {bot_msg}")
                
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            print(f"  [!] ERROR HTTP {e.code}: {err_msg}")
            transcript.append(f"ERROR HTTP {e.code}: {err_msg}")
            passed = False
            break
        except Exception as e:
            print(f"  [!] ERROR general: {e}")
            transcript.append(f"ERROR: {e}")
            passed = False
            break
            
    end_time = time.time()
    total_time = end_time - start_time
    avg_time_per_turn = total_time / len(messages) if messages else 0
    
    if not last_info_state:
        print("[FAILED] Fallo en test: no se obtuvo estado.")
        return False
        
    eval_drools = last_info_state.get("evaluacion_drools", {})
    estado_final_real = eval_drools.get("estado", "DESCONOCIDO")
    reglas = eval_drools.get("reglas_disparadas", [])
    bde_consultado = last_info_state.get("datos_externos_bde", {}).get("consultado", False)
    
    print("\n--- Resultados ---")
    if expected_estado_final:
        if estado_final_real == expected_estado_final:
            print(f"[PASSED] ESTADO ESPERADO CUMPLIDO: {estado_final_real}")
        else:
            print(f"[FAILED] ESTADO INCORRECTO: Esperaba {expected_estado_final}, obtuve {estado_final_real}")
            passed = False
            
    if extra_asserts:
        if not extra_asserts(last_info_state):
            print(f"[FAILED] ASERSIONES EXTRA FALLIDAS")
            passed = False
        else:
            print(f"[PASSED] ASERSIONES EXTRA CUMPLIDAS")
            
    print(f"Reglas disparadas en último turno: {reglas}")
    print(f"BDE Consultado a lo largo del test: {bde_consultado}")
    
    transcript.append("\n=== ESTADO FINAL (INFORMATION STATE) ===")
    transcript.append(json.dumps(last_info_state, indent=2, ensure_ascii=False))
    
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write("\n".join(transcript))
        
    with open(metrics_path, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Test: {test_name} | Resultado: {'PASSED' if passed else 'FAILED'} | Tiempo_Medio_Turno: {avg_time_per_turn:.2f}s | BDE_Llamado: {bde_consultado}\n")
        
    return passed
