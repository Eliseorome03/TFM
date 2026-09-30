import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero pedir un préstamo",
        "1000 euros",
        "2 años",
        "para una reforma",
        "solo pago unos 100 euros de luz y agua al mes"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return (
            u.get("cantidad_solicitada") == 1000.0 and
            u.get("plazo_meses") == 24 and
            u.get("proposito") == "REFORMA" and
            u.get("gastos_fijos_mensuales") == 100.0
        )
        
    run_test_case(
        category="cat1_nlu",
        test_name="01_cliente_telegrafico",
        cliente_id="CLI-001", # Cliente perfecto
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
