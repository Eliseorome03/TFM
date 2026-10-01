import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero 5000 euros para meterlos todos en Bitcoin y hacerme rico.",
        "A 12 meses",
        "0 gastos"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return u.get("proposito") == "CRIPTOMONEDAS"
        
    run_test_case(
        category="cat1_nlu",
        test_name="21_proposito_riesgo",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="DENEGADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
