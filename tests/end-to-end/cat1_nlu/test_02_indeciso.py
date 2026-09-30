import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Necesito 5000 euros para un vehículo, a pagar en 12 meses",
        "Perdona, me he equivocado, la moto vale más, que sean 8000 euros",
        "Y mejor lo pago en 3 años para que la cuota sea más baja",
        "De gastos fijos tengo 150 euros"
    ]
    
    def check_nlu(state):
        u = state.get("datos_usuario", {})
        return (
            u.get("cantidad_solicitada") == 8000.0 and
            u.get("plazo_meses") == 36 and
            u.get("proposito") == "VEHICULO" and
            u.get("gastos_fijos_mensuales") == 150.0
        )
        
    run_test_case(
        category="cat1_nlu",
        test_name="02_cliente_indeciso",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_nlu
    )

if __name__ == "__main__":
    main()
