import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Hola buenas tardes, me llamo Juan y tengo 54 años, trabajo en una empresa de seguros desde hace 18 años y gano bien.",
        "Quiero pedir unos 3000 euros para comprarle una moto a mi hijo que cumple 18 años el mes que viene, yo ya digo que me va bien la vida, solo pago 150 de comunidad e internet y no tengo otras deudas ni nada de eso, a ver si me lo podéis dar para devolvéroslo en un año."
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return (
            u.get("cantidad_solicitada") == 3000.0 and
            u.get("plazo_meses") == 12 and
            u.get("proposito") == "VEHICULO" and
            u.get("gastos_fijos_mensuales") == 150.0
        )
        
    run_test_case(
        category="cat1_nlu",
        test_name="03_extraccion_con_ruido",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
