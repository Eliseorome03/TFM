import urllib.request
import json
import sys

URL = "http://localhost:8080/api/evaluate"

def run_test(name, payload, expected_estado, expected_regla):
    req = urllib.request.Request(URL, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    data = json.dumps(payload).encode("utf-8")
    try:
        with urllib.request.urlopen(req, data=data) as response:
            result = json.loads(response.read().decode("utf-8"))
            estado = result.get("estado")
            reglas = result.get("reglas_disparadas", [])
            
            if estado == expected_estado and expected_regla in reglas:
                print(f"[PASSED] {name}")
                return True
            else:
                print(f"[FAILED] {name}")
                print(f"   Expected: {expected_estado} with rule {expected_regla}")
                print(f"   Got: {estado} with rules {reglas}")
                return False
    except Exception as e:
        print(f"[ERROR] {name}")
        print(f"   Exception: {e}")
        return False

def base_payload():
    # Base payload representing a fully populated, perfect applicant
    # All required data is present to pass through to APROBADO.
    return {
        "datos_usuario": {
            "intencion_principal": "SOLICITAR_PRESTAMO",
            "cantidad_solicitada": 1000.0,
            "plazo_meses": 12,
            "proposito": "VEHICULO",
            "gastos_fijos_mensuales": 100.0,
            "deuda_declarada": 0.0,
            "duda_catch_all": "NINGUNA"
        },
        "datos_core": {
            "cliente_id": "C123",
            "dni": "12345678A",
            "edad": 30,
            "ingresos_netos_mensuales": 3000.0,
            "antiguedad_meses": 60,
            "deuda_interna_banco_mensual": 0.0,
            "es_avalista": False,
            "empresa_avalada_cif": None
        },
        "datos_bde": {
            "consultado": True,
            "tiene_impagos_activos": False,
            "importe_morosidad_asnef": 0.0,
            "empresa_avalada_concurso": False,
            "deuda_cirbe_mensual": 0.0,
            "deuda_cirbe_total": 0.0
        }
    }

def main():
    print("==================================================")
    print(" INICIANDO BATERÍA DE PRUEBAS DE DROOLS (TFM)")
    print("==================================================\n")
    tests = []

    # 1. R_EDAD_MINIMA
    p = base_payload(); p["datos_core"]["edad"] = 17
    tests.append(run_test("R_EDAD_MINIMA (menor de 18)", p, "DENEGADO", "R_EDAD_MINIMA"))

    # 2. R_EDAD_MAXIMA
    p = base_payload(); p["datos_core"]["edad"] = 74; p["datos_usuario"]["plazo_meses"] = 24
    tests.append(run_test("R_EDAD_MAXIMA (> 75 al vencimiento)", p, "DENEGADO", "R_EDAD_MAXIMA"))

    # 3. R_RATIO_ENDEUDAMIENTO
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 100000.0
    p["datos_usuario"]["plazo_meses"] = 12
    # Cuota: ~8333, Ingresos: 3000 -> Ratio > 0.4
    tests.append(run_test("R_RATIO_ENDEUDAMIENTO (Ratio > 40%)", p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO"))

    # 4. R_MINIMO_SUBSISTENCIA
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 1000.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 100.0
    p["datos_usuario"]["cantidad_solicitada"] = 3600.0
    p["datos_usuario"]["plazo_meses"] = 12
    # Cuota: 300, Ingresos: 1000, Gastos: 100. Remanente: 600 < 700
    tests.append(run_test("R_MINIMO_SUBSISTENCIA (Remanente < 700)", p, "DENEGADO", "R_MINIMO_SUBSISTENCIA"))

    # 5. R_PROPOSITO_NO_FINANCIABLE
    p = base_payload(); p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    tests.append(run_test("R_PROPOSITO_NO_FINANCIABLE", p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE"))

    # 6. R_CANTIDAD_Y_PLAZO_REQUERIDOS
    p = base_payload(); p["datos_usuario"]["cantidad_solicitada"] = None
    tests.append(run_test("R_CANTIDAD_Y_PLAZO_REQUERIDOS (falta cantidad)", p, "REQUIERE_DATOS", "R_CANTIDAD_Y_PLAZO_REQUERIDOS"))
    p = base_payload(); p["datos_usuario"]["plazo_meses"] = None
    tests.append(run_test("R_CANTIDAD_Y_PLAZO_REQUERIDOS (falta plazo)", p, "REQUIERE_DATOS", "R_CANTIDAD_Y_PLAZO_REQUERIDOS"))

    # 7. R_PROPOSITO_REQUERIDO
    p = base_payload(); p["datos_usuario"]["proposito"] = None
    tests.append(run_test("R_PROPOSITO_REQUERIDO (falta propósito)", p, "REQUIERE_DATOS", "R_PROPOSITO_REQUERIDO"))

    # 8. R_GASTOS_FIJOS_REQUERIDOS
    p = base_payload(); p["datos_usuario"]["gastos_fijos_mensuales"] = None
    tests.append(run_test("R_GASTOS_FIJOS_REQUERIDOS (faltan gastos)", p, "REQUIERE_DATOS", "R_GASTOS_FIJOS_REQUERIDOS"))

    # 9. R_DISPARAR_CIRBE
    p = base_payload(); p["datos_bde"]["consultado"] = False
    tests.append(run_test("R_DISPARAR_CIRBE (consultado=False)", p, "REQUIERE_ACCION", "R_DISPARAR_CIRBE"))

    # 10. R_MOROSIDAD_ASNEF
    p = base_payload(); p["datos_bde"]["tiene_impagos_activos"] = True
    tests.append(run_test("R_MOROSIDAD_ASNEF (impagos activos)", p, "DENEGADO", "R_MOROSIDAD_ASNEF"))
    
    p = base_payload(); p["datos_bde"]["importe_morosidad_asnef"] = 150.0
    tests.append(run_test("R_MOROSIDAD_ASNEF (importe > 0)", p, "DENEGADO", "R_MOROSIDAD_ASNEF"))

    # 11. R_ALERTA_QUIEBRA_AVAL
    p = base_payload()
    p["datos_core"]["es_avalista"] = True
    p["datos_bde"]["empresa_avalada_concurso"] = True
    tests.append(run_test("R_ALERTA_QUIEBRA_AVAL", p, "DENEGADO", "R_ALERTA_QUIEBRA_AVAL"))


    # 13. R_DISCREPANCIA_DECLARADA
    p = base_payload()
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 2000.0 # 2000 > 1000 * 1.35 = 1350
    tests.append(run_test("R_DISCREPANCIA_DECLARADA", p, "REQUIERE_SUPERVISION_HUMANA", "R_DISCREPANCIA_DECLARADA"))

    # 14. R_APROBACION_ESTANDAR
    p = base_payload()
    tests.append(run_test("R_APROBACION_ESTANDAR (Todo Perfecto)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    print(f"\nResultados: {sum(tests)}/{len(tests)} pruebas pasadas con exito.")
    if sum(tests) == len(tests):
        print("[EXITO] El motor Drools funciona PERFECTAMENTE segun la especificacion.")
    else:
        print("[ATENCION] Hay errores. Revisa las reglas que han fallado.")

if __name__ == "__main__":
    main()
