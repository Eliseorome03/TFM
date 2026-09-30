import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero 1000000 euros para reformar un castillo",
        "En 12 meses",
        "No tengo gastos fijos"
    ]
    
    # Validamos que Drools corta el grifo y NUNCA llama a la CIRBE
    def check_optimizado(state):
        return state.get("datos_externos_bde", {}).get("consultado") is False
        
    run_test_case(
        category="cat2_drools",
        test_name="04_early_rejection",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="DENEGADO",
        extra_asserts=check_optimizado
    )

if __name__ == "__main__":
    main()
