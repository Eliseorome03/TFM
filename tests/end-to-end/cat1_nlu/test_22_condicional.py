import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero 4000 euros para un coche, 0 gastos fijos.",
        "A pagar en 12 meses si me dais un buen interés, o en 36 meses si es alto."
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        # A nivel técnico, comprobamos el mecanismo Fail-Safe: 
        # devuelve None ante ambigüedad lógica.
        return u.get("plazo_meses") is None
        
    run_test_case(
        category="cat1_nlu",
        test_name="22_condicional",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="REQUIERE_DATOS",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
