import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "¿Cómo cambio la contraseña de la app? Ah, y también quiero solicitar 3000 euros a 12 meses para salud, 0 gastos fijos."
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        # Esperamos que el sistema sea capaz de ser multitarea:
        # 1. Registrar que hay una duda (duda_catch_all)
        # 2. Extraer los datos del préstamo simultáneamente
        return u.get("duda_catch_all") != "NINGUNA" and u.get("cantidad_solicitada") == 3000.0
        
    run_test_case(
        category="cat1_nlu",
        test_name="21_multi_intencion",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
