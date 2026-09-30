import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    # CLI-003 is Carlos Ruiz Fernández -> Morosidad activa en BDE
    messages = [
        "Necesito 2000 euros",
        "A pagar en 2 años",
        "Para salud",
        "Gasto 200 euros fijos"
    ]
    
    def check_cirbe(state):
        evaluacion = state.get("evaluacion_drools", {})
        bde = state.get("datos_externos_bde", {})
        return (
            bde.get("consultado") is True and
            bde.get("tiene_impagos_activos") is True and
            "R_MOROSIDAD_ASNEF" in evaluacion.get("reglas_disparadas", [])
        )
        
    run_test_case(
        category="cat2_drools",
        test_name="05_rechazo_cirbe",
        cliente_id="CLI-003", 
        messages=messages,
        expected_estado_final="DENEGADO",
        extra_asserts=check_cirbe
    )

if __name__ == "__main__":
    main()
