import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero 3000 euros para comprar una moto... bueno no, pensándolo mejor, la moto es muy peligrosa, lo voy a usar para pagarme un máster.",
        "A pagar en 12 meses",
        "0 gastos"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return u.get("proposito") == "ESTUDIOS"
        
    run_test_case(
        category="cat1_nlu",
        test_name="19_contradiccion",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
