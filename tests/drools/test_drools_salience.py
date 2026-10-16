import urllib.request
import json
import sys

URL = "http://localhost:8080/api/evaluate"

def base_payload():
    """
    Payload base representando un solicitante ideal cuyos datos
    aprobarían directamente (R_APROBACION_ESTANDAR).
    """
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

def run_salience_test(name, payload, expected_estado, winner_rule, loser_rules):
    """
    Evalúa un caso de conflicto donde las condiciones de múltiples reglas se
    cumplen simultáneamente.
    Verifica que:
      1. El estado resultante coincide con expected_estado.
      2. La regla con mayor salience (winner_rule) se ha disparado.
      3. Ninguna regla de menor prioridad (loser_rules) se ha disparado gracias a la guarda anticolisión.
      4. Solamente una regla final ha sido registrada en 'reglas_disparadas'.
    """
    req = urllib.request.Request(URL, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data=data, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            estado = result.get("estado")
            reglas = result.get("reglas_disparadas", [])

            errors = []
            if estado != expected_estado:
                errors.append(f"Estado esperado '{expected_estado}', pero se obtuvo '{estado}'")

            if winner_rule not in reglas:
                errors.append(f"La regla ganadora esperada '{winner_rule}' NO se disparó. Reglas disparadas: {reglas}")

            for loser in loser_rules:
                if loser in reglas:
                    errors.append(f"COLISIÓN NO RESUELTA: La regla de menor prioridad '{loser}' se disparó indebidamente.")

            if len(reglas) > 1:
                errors.append(f"Se dispararon múltiples reglas ({reglas}) cuando solo debía ejecutarse una.")

            if not errors:
                print(f"[PASSED] {name}")
                print(f"         Ganadora: {winner_rule} | Descartadas por salience: {', '.join(loser_rules)}")
                return True
            else:
                print(f"[FAILED] {name}")
                for err in errors:
                    print(f"   -> {err}")
                print(f"   Resultado completo: estado={estado}, reglas={reglas}")
                return False

    except Exception as e:
        print(f"[ERROR] {name}")
        print(f"   Exception: {e}")
        return False

def main():
    print("==================================================================")
    print(" BATERÍA DE PRUEBAS DE SALIENCE Y RESOLUCIÓN DE CONFLICTOS (DROOLS)")
    print("==================================================================\n")
    tests = []

    # -----------------------------------------------------------------
    # 1. R_EDAD_MINIMA (100) vs R_EDAD_MAXIMA (95)
    # -----------------------------------------------------------------
    # Menor de edad (17 años) pero con plazo que excede 75 al vencimiento (17 + 60 = 77)
    p = base_payload()
    p["datos_core"]["edad"] = 17
    p["datos_usuario"]["plazo_meses"] = 720
    tests.append(run_salience_test(
        "SALIENCE 100 vs 95: R_EDAD_MINIMA prevalece sobre R_EDAD_MAXIMA",
        p, "DENEGADO", "R_EDAD_MINIMA", ["R_EDAD_MAXIMA"]
    ))

    # -----------------------------------------------------------------
    # 2. R_EDAD_MINIMA (100) vs R_RATIO_ENDEUDAMIENTO (92)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_core"]["edad"] = 17
    p["datos_usuario"]["cantidad_solicitada"] = 100000.0
    p["datos_usuario"]["plazo_meses"] = 12 # Cuota ~8333, ratio > 40%
    tests.append(run_salience_test(
        "SALIENCE 100 vs 92: R_EDAD_MINIMA prevalece sobre R_RATIO_ENDEUDAMIENTO",
        p, "DENEGADO", "R_EDAD_MINIMA", ["R_RATIO_ENDEUDAMIENTO"]
    ))

    # -----------------------------------------------------------------
    # 3. R_EDAD_MINIMA (100) vs R_PROPOSITO_NO_FINANCIABLE (90)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_core"]["edad"] = 17
    p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    tests.append(run_salience_test(
        "SALIENCE 100 vs 90: R_EDAD_MINIMA prevalece sobre R_PROPOSITO_NO_FINANCIABLE",
        p, "DENEGADO", "R_EDAD_MINIMA", ["R_PROPOSITO_NO_FINANCIABLE"]
    ))

    # -----------------------------------------------------------------
    # 4. R_EDAD_MINIMA (100) vs R_MOROSIDAD_ASNEF (60)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_core"]["edad"] = 17
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 1500.0
    tests.append(run_salience_test(
        "SALIENCE 100 vs 60: R_EDAD_MINIMA prevalece sobre R_MOROSIDAD_ASNEF",
        p, "DENEGADO", "R_EDAD_MINIMA", ["R_MOROSIDAD_ASNEF"]
    ))

    # -----------------------------------------------------------------
    # 5. R_EDAD_MAXIMA (95) vs R_RATIO_ENDEUDAMIENTO (92)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_core"]["edad"] = 74
    p["datos_usuario"]["plazo_meses"] = 24 # 74 + 2 = 76 > 75
    p["datos_usuario"]["cantidad_solicitada"] = 100000.0 # Cuota ~4166 > 40% de 3000
    tests.append(run_salience_test(
        "SALIENCE 95 vs 92: R_EDAD_MAXIMA prevalece sobre R_RATIO_ENDEUDAMIENTO",
        p, "DENEGADO", "R_EDAD_MAXIMA", ["R_RATIO_ENDEUDAMIENTO"]
    ))

    # -----------------------------------------------------------------
    # 6. R_EDAD_MAXIMA (95) vs R_PROPOSITO_NO_FINANCIABLE (90)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_core"]["edad"] = 74
    p["datos_usuario"]["plazo_meses"] = 24
    p["datos_usuario"]["proposito"] = "APUESTAS"
    tests.append(run_salience_test(
        "SALIENCE 95 vs 90: R_EDAD_MAXIMA prevalece sobre R_PROPOSITO_NO_FINANCIABLE",
        p, "DENEGADO", "R_EDAD_MAXIMA", ["R_PROPOSITO_NO_FINANCIABLE"]
    ))

    # -----------------------------------------------------------------
    # 7. R_EDAD_MAXIMA (95) vs R_CANTIDAD_Y_PLAZO_REQUERIDOS (85)
    # -----------------------------------------------------------------
    # Supera edad máxima con plazo conocido, pero falta cantidad solicitada
    p = base_payload()
    p["datos_core"]["edad"] = 74
    p["datos_usuario"]["plazo_meses"] = 24
    p["datos_usuario"]["cantidad_solicitada"] = None
    tests.append(run_salience_test(
        "SALIENCE 95 vs 85: R_EDAD_MAXIMA prevalece sobre R_CANTIDAD_Y_PLAZO_REQUERIDOS (deniega en vez de pedir datos)",
        p, "DENEGADO", "R_EDAD_MAXIMA", ["R_CANTIDAD_Y_PLAZO_REQUERIDOS"]
    ))

    # -----------------------------------------------------------------
    # 8. R_RATIO_ENDEUDAMIENTO (92) vs R_MINIMO_SUBSISTENCIA (91)
    # -----------------------------------------------------------------
    # Saliences contiguas (92 vs 91). Ratio > 40% y Remanente < 700 €
    # Ingresos: 2000, Gastos: 200, Cuota: 2000. Compromisos: 2200.
    # Ratio = 2200/2000 = 1.10 (>0.40). Remanente = 2000 - 2200 = -200 (< 700).
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 2000.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 200.0
    p["datos_usuario"]["cantidad_solicitada"] = 24000.0
    p["datos_usuario"]["plazo_meses"] = 12
    tests.append(run_salience_test(
        "SALIENCE 92 vs 91: R_RATIO_ENDEUDAMIENTO prevalece sobre R_MINIMO_SUBSISTENCIA",
        p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO", ["R_MINIMO_SUBSISTENCIA"]
    ))

    # -----------------------------------------------------------------
    # 9. R_RATIO_ENDEUDAMIENTO (92) vs R_DISPARAR_CIRBE (70)
    # -----------------------------------------------------------------
    # Si la cuota ya excede el ratio con datos declarados y core, deniega sin pedir consulta CIRBE
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 100000.0
    p["datos_usuario"]["plazo_meses"] = 12
    p["datos_bde"]["consultado"] = False
    tests.append(run_salience_test(
        "SALIENCE 92 vs 70: R_RATIO_ENDEUDAMIENTO prevalece sobre R_DISPARAR_CIRBE",
        p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO", ["R_DISPARAR_CIRBE"]
    ))

    # -----------------------------------------------------------------
    # 10. R_RATIO_ENDEUDAMIENTO (92) vs R_MOROSIDAD_ASNEF (60)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 100000.0
    p["datos_usuario"]["plazo_meses"] = 12
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 2000.0
    tests.append(run_salience_test(
        "SALIENCE 92 vs 60: R_RATIO_ENDEUDAMIENTO prevalece sobre R_MOROSIDAD_ASNEF",
        p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO", ["R_MOROSIDAD_ASNEF"]
    ))

    # -----------------------------------------------------------------
    # 11. R_MINIMO_SUBSISTENCIA (91) vs R_PROPOSITO_NO_FINANCIABLE (90)
    # -----------------------------------------------------------------
    # Saliences contiguas (91 vs 90).
    # Ratio <= 40% (no dispara 92): Ingresos=1000, Gastos=100, Cuota=250 -> Ratio = 35%
    # Remanente = 650 < 700 (dispara 91). Propósito = CRIPTOMONEDAS (dispara 90).
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 1000.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 100.0
    p["datos_usuario"]["cantidad_solicitada"] = 3000.0
    p["datos_usuario"]["plazo_meses"] = 12
    p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    tests.append(run_salience_test(
        "SALIENCE 91 vs 90: R_MINIMO_SUBSISTENCIA prevalece sobre R_PROPOSITO_NO_FINANCIABLE",
        p, "DENEGADO", "R_MINIMO_SUBSISTENCIA", ["R_PROPOSITO_NO_FINANCIABLE"]
    ))

    # -----------------------------------------------------------------
    # 12. R_PROPOSITO_NO_FINANCIABLE (90) vs R_CANTIDAD_Y_PLAZO_REQUERIDOS (85)
    # -----------------------------------------------------------------
    # Propósito no financiable y falta cantidad solicitada
    p = base_payload()
    p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    p["datos_usuario"]["cantidad_solicitada"] = None
    tests.append(run_salience_test(
        "SALIENCE 90 vs 85: R_PROPOSITO_NO_FINANCIABLE prevalece sobre R_CANTIDAD_Y_PLAZO_REQUERIDOS",
        p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE", ["R_CANTIDAD_Y_PLAZO_REQUERIDOS"]
    ))

    # -----------------------------------------------------------------
    # 13. R_PROPOSITO_NO_FINANCIABLE (90) vs R_DISPARAR_CIRBE (70)
    # -----------------------------------------------------------------
    # Propósito de criptomonedas y CIRBE no consultado: deniega en vez de pedir consulta
    p = base_payload()
    p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    p["datos_bde"]["consultado"] = False
    tests.append(run_salience_test(
        "SALIENCE 90 vs 70: R_PROPOSITO_NO_FINANCIABLE prevalece sobre R_DISPARAR_CIRBE",
        p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE", ["R_DISPARAR_CIRBE"]
    ))

    # -----------------------------------------------------------------
    # 14. R_PROPOSITO_NO_FINANCIABLE (90) vs R_MOROSIDAD_ASNEF (60)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_usuario"]["proposito"] = "REFINANCIACION_INFORMAL"
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 800.0
    tests.append(run_salience_test(
        "SALIENCE 90 vs 60: R_PROPOSITO_NO_FINANCIABLE prevalece sobre R_MOROSIDAD_ASNEF",
        p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE", ["R_MOROSIDAD_ASNEF"]
    ))

    # -----------------------------------------------------------------
    # 15. R_MOROSIDAD_ASNEF (60) vs R_ALERTA_QUIEBRA_AVAL (50)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 600.0
    p["datos_core"]["es_avalista"] = True
    p["datos_bde"]["empresa_avalada_concurso"] = True
    tests.append(run_salience_test(
        "SALIENCE 60 vs 50: R_MOROSIDAD_ASNEF prevalece sobre R_ALERTA_QUIEBRA_AVAL",
        p, "DENEGADO", "R_MOROSIDAD_ASNEF", ["R_ALERTA_QUIEBRA_AVAL"]
    ))

    # -----------------------------------------------------------------
    # 16. R_ALERTA_QUIEBRA_AVAL (50) vs R_DISCREPANCIA_DECLARADA (40)
    # -----------------------------------------------------------------
    # Denegación directa por quiebra aval prevalece sobre supervisión humana por discrepancia
    p = base_payload()
    p["datos_core"]["es_avalista"] = True
    p["datos_bde"]["empresa_avalada_concurso"] = True
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 2500.0 # 2500 > 1000 * 1.35
    tests.append(run_salience_test(
        "SALIENCE 50 vs 40: R_ALERTA_QUIEBRA_AVAL prevalece sobre R_DISCREPANCIA_DECLARADA",
        p, "DENEGADO", "R_ALERTA_QUIEBRA_AVAL", ["R_DISCREPANCIA_DECLARADA"]
    ))

    # -----------------------------------------------------------------
    # 17. R_MOROSIDAD_ASNEF (60) vs R_DISCREPANCIA_DECLARADA (40)
    # -----------------------------------------------------------------
    p = base_payload()
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 500.0
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 2500.0
    tests.append(run_salience_test(
        "SALIENCE 60 vs 40: R_MOROSIDAD_ASNEF prevalece sobre R_DISCREPANCIA_DECLARADA",
        p, "DENEGADO", "R_MOROSIDAD_ASNEF", ["R_DISCREPANCIA_DECLARADA"]
    ))

    # -----------------------------------------------------------------
    # 18. R_DISCREPANCIA_DECLARADA (40) vs R_APROBACION_ESTANDAR (10)
    # -----------------------------------------------------------------
    # Solicitud totalmente aprobable (solvente, sin morosidad), pero con discrepancia CIRBE
    # Debe pasar a supervisión humana y NO aprobarse directamente
    p = base_payload()
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 2000.0
    tests.append(run_salience_test(
        "SALIENCE 40 vs 10: R_DISCREPANCIA_DECLARADA prevalece sobre R_APROBACION_ESTANDAR",
        p, "REQUIERE_SUPERVISION_HUMANA", "R_DISCREPANCIA_DECLARADA", ["R_APROBACION_ESTANDAR"]
    ))

    # -----------------------------------------------------------------
    # 19. COLISIÓN MÚLTIPLE: Salience 100 vs (90, 60, 50, 40)
    # -----------------------------------------------------------------
    # Menor de edad + cripto + impagos ASNEF + avalista en concurso + discrepancia CIRBE
    p = base_payload()
    p["datos_core"]["edad"] = 16
    p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 1200.0
    p["datos_core"]["es_avalista"] = True
    p["datos_bde"]["empresa_avalada_concurso"] = True
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 3000.0
    tests.append(run_salience_test(
        "COLISIÓN MÚLTIPLE (100 vs 90, 60, 50, 40): R_EDAD_MINIMA absorbe el conflicto",
        p, "DENEGADO", "R_EDAD_MINIMA",
        ["R_PROPOSITO_NO_FINANCIABLE", "R_MOROSIDAD_ASNEF", "R_ALERTA_QUIEBRA_AVAL", "R_DISCREPANCIA_DECLARADA"]
    ))

    # -----------------------------------------------------------------
    # 20. COLISIÓN MÚLTIPLE: Salience 92 vs (91, 90, 60)
    # -----------------------------------------------------------------
    # Adulto: ratio excesivo + remanente bajo + cripto + impagos ASNEF
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 2000.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 200.0
    p["datos_usuario"]["cantidad_solicitada"] = 30000.0
    p["datos_usuario"]["plazo_meses"] = 12 # Cuota: 2500, ratio > 40%, remanente < 700
    p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    p["datos_bde"]["tiene_impagos_activos"] = True
    p["datos_bde"]["importe_morosidad_asnef"] = 900.0
    tests.append(run_salience_test(
        "COLISIÓN MÚLTIPLE (92 vs 91, 90, 60): R_RATIO_ENDEUDAMIENTO absorbe el conflicto",
        p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO",
        ["R_MINIMO_SUBSISTENCIA", "R_PROPOSITO_NO_FINANCIABLE", "R_MOROSIDAD_ASNEF"]
    ))

    # -----------------------------------------------------------------
    # Resumen y veredicto
    # -----------------------------------------------------------------
    total = len(tests)
    passed = sum(tests)
    print("\n==================================================================")
    print(f" RESULTADOS: {passed}/{total} pruebas de salience pasadas con éxito.")
    print("==================================================================")

    if passed == total:
        print("[ÉXITO] La jerarquía de salience y la guarda anticolisión funcionan EXACTAMENTE según el diseño.")
    else:
        print("[FALLO] Hay inconsistencias en la prioridad de reglas o en la guarda anticolisión.")
        sys.exit(1)

if __name__ == "__main__":
    main()
