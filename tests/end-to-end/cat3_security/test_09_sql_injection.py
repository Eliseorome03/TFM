import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner import run_test_case

def main():
    messages = [
        "Quiero 1000 euros'); DROP TABLE trazas_auditoria; -- a pagar en 12 meses",
        "para reforma, 100 gastos"
    ]
    
    def check_security(state):
        # We ensure NLU successfully extracted the data despite the SQL injection attempt
        u = state.get("datos_usuario", {})
        return u.get("cantidad_solicitada") == 1000.0 and u.get("plazo_meses") == 12
        
    run_test_case(
        category="cat3_security",
        test_name="09_sql_injection",
        cliente_id="CLI-001", 
        messages=messages,
        expected_estado_final="APROBADO",
        extra_asserts=check_security
    )

if __name__ == "__main__":
    main()
