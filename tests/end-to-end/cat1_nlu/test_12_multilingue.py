import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "I need 3000 bucks for a car, to be paid in 12 months",
        "I have absolutely zero expenses right now"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return (
            u.get("cantidad_solicitada") == 3000.0 and
            u.get("plazo_meses") == 12 and
            u.get("proposito") == "VEHICULO"
        )
        
    run_test_case(
        category="cat1_nlu",
        test_name="12_multilingue",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
