import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    # CLI-004 is Raúl Sánchez Moreno, 74 years old
    messages = [
        "Quiero pedir un préstamo de 2000 euros",
        "A pagar en 24 meses",
        "Para reforma",
        "No tengo gastos fijos"
    ]
    
    def check_rules(state):
        evaluacion = state.get("evaluacion_drools", {})
        return "R_EDAD_MAXIMA" in evaluacion.get("reglas_disparadas", [])
        
    run_test_case(
        category="cat2_drools",
        test_name="06_choque_reglas",
        cliente_id="CLI-004", 
        messages=messages,
        expected_estado_final="DENEGADO",
        extra_asserts=check_rules
    )

if __name__ == "__main__":
    main()
