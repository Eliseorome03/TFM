import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Necesito 5000 euros a 24 meses",
        "oye, ¿y qué tipo de interés cobráis por curiosidad?",
        "Ah vale, pues es para un coche",
        "De gastos fijos tengo unos 100 euros al mes"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return u.get("cantidad_solicitada") == 5000.0 and u.get("plazo_meses") == 24
        
    run_test_case(
        category="cat1_nlu",
        test_name="11_topic_shift",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
