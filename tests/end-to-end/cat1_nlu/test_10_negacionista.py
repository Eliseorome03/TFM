import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero 2000 euros para salud",
        "A 12 meses",
        "no tengo ningún gasto fijo, vivo con mis padres, cero patatero"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return u.get("gastos_fijos_mensuales") == 0.0
        
    run_test_case(
        category="cat1_nlu",
        test_name="10_negacionista",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
