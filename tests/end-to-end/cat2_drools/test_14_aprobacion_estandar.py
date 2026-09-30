import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    # Aprobacion feliz en 1 turno
    messages = [
        "Hola quiero 2000 euros a 12 meses para reforma, tengo 100 de gastos fijos."
    ]
    
    def check_aprobado(state):
        return state.get("datos_externos_bde", {}).get("consultado") is True
        
    run_test_case(
        category="cat2_drools",
        test_name="14_aprobacion_estandar",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_aprobado
    )

if __name__ == "__main__":
    main()
