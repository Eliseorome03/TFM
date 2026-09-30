import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    # Attempt to overload tokens / distract NLU
    noise = "bla " * 100
    messages = [
        "Quiero 2000 euros",
        f"A pagar en 12 meses. {noise} para salud",
        "0 gastos"
    ]
    
    def check_extraction(state):
        u = state.get("datos_usuario", {})
        return u.get("cantidad_solicitada") == 2000.0 and u.get("proposito") == "SALUD"
        
    run_test_case(
        category="cat3_security",
        test_name="18_ruido_extremo",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_extraction
    )

if __name__ == "__main__":
    main()
