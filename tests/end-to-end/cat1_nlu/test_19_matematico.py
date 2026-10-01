import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero pagar una cuota de 130 euros en los próximos 12 meses para reformar la casa.",
        "No tengo ningún gasto fijo"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        # Mistral debe ser capaz de multiplicar cuota x meses implícitamente
        return u.get("cantidad_solicitada") == 1560.0 and u.get("plazo_meses") == 12
        
    run_test_case(
        category="cat1_nlu",
        test_name="19_matematico",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
