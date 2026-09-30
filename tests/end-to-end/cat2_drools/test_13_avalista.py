import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    # CLI-002 is María Blanco Torres (Avalista de empresa en quiebra)
    messages = [
        "Quiero 1000 euros a 12 meses",
        "para salud",
        "0 gastos fijos"
    ]
    
    def check_aval(state):
        evaluacion = state.get("evaluacion_drools", {})
        return "R_ALERTA_QUIEBRA_AVAL" in evaluacion.get("reglas_disparadas", [])
        
    run_test_case(
        category="cat2_drools",
        test_name="13_avalista",
        cliente_id="CLI-002", 
        messages=messages,
        expected_estado_final="DENEGADO",
        extra_asserts=check_aval
    )

if __name__ == "__main__":
    main()
