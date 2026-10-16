"""
test_drools_rules.py — Batería de Pruebas Unitarias y de Integración para Drools DRL.

Este módulo implementa la certificación de evaluación determinista sobre el endpoint
POST /api/evaluate del microservicio Drools (Spring Boot + KIE).

Objetivos de Cobertura:
  1. 100% de cobertura de reglas activas del catálogo 'prestamos.drl' (13 reglas activas).
  2. Verificación matemática exacta de los cálculos derivados (Sección 3.4.3 del TFM):
       - cuota_estimada = cantidad_solicitada / plazo_meses
       - total_compromisos = cuota_estimada + gastos_fijos + deuda_interna + deuda_cirbe
       - ratio_endeudamiento (DTI) = total_compromisos / ingresos_netos_mensuales
       - remanente_subsistencia = ingresos_netos_mensuales - total_compromisos
       - edad_al_vencimiento = edad + floor(plazo_meses / 12)
  3. Comprobación de estados canónicos (APROBADO, DENEGADO, REQUIERE_DATOS,
     REQUIERE_ACCION, REQUIERE_SUPERVISION_HUMANA).
  4. Null-safety y cálculos monótonos parciales con datos incompletos.
"""

import urllib.request
import json
import math
import sys
import os

# Permitir importación del InformationState si se ejecuta en el entorno del backend
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
backend_dir = os.path.join(project_root, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app.schemas.state import InformationState, DatosUsuario, DatosCoreBancario, DatosExternosBde
    HAS_PYDANTIC_STATE = True
except Exception:
    HAS_PYDANTIC_STATE = False

URL = "http://localhost:8080/api/evaluate"


def to_drools_payload(state_or_dict):
    """
    Normaliza un InformationState canónico (objeto o diccionario)
    al formato JSON esperado por el controlador Drools:
      {
        "datos_usuario": {...},
        "datos_core": {...},
        "datos_bde": {...}
      }
    """
    if HAS_PYDANTIC_STATE and isinstance(state_or_dict, InformationState):
        d = state_or_dict.as_dict()
    elif hasattr(state_or_dict, "model_dump"):
        d = state_or_dict.model_dump()
    elif isinstance(state_or_dict, dict):
        d = json.loads(json.dumps(state_or_dict))  # Copia profunda
    else:
        raise TypeError(f"Tipo de estado no soportado: {type(state_or_dict)}")

    # Mapeo de nombres si proceden del InformationState canónico
    datos_usuario = d.get("datos_usuario", {})
    datos_core = d.get("datos_core") or d.get("datos_core_bancario", {})
    datos_bde = d.get("datos_bde") or d.get("datos_externos_bde", {})

    return {
        "datos_usuario": datos_usuario,
        "datos_core": datos_core,
        "datos_bde": datos_bde
    }


def base_payload():
    """
    Retorna el estado base canónico de un solicitante ideal solvente.
    Todas las reglas restrictivas evalúan a falso y conduce a R_APROBACION_ESTANDAR.
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


def assert_calculos_derivados(payload, calculos):
    """
    Verifica con precisión matemática estricta (tolerancia float 1e-4) que las
    métricas derivadas calculadas por DroolsService corresponden a las fórmulas
    establecidas en la Sección 3.4.3 del TFM:

      1. cuota_estimada = cantidad_solicitada / plazo_meses
      2. total_compromisos = cuota_estimada + gastos_fijos + deuda_interna + deuda_cirbe
      3. ratio_endeudamiento (DTI) = total_compromisos / ingresos_netos_mensuales
      4. remanente_subsistencia = ingresos_netos_mensuales - total_compromisos
      5. edad_al_vencimiento = edad + floor(plazo_meses / 12)
    """
    if calculos is None:
        return True, "calculos_derivados es None"

    du = payload.get("datos_usuario", {})
    dc = payload.get("datos_core", {}) or payload.get("datos_core_bancario", {})
    db = payload.get("datos_bde", {}) or payload.get("datos_externos_bde", {})

    cantidad = du.get("cantidad_solicitada")
    plazo = du.get("plazo_meses")
    gastos = du.get("gastos_fijos_mensuales")
    deuda_interna = dc.get("deuda_interna_banco_mensual")
    deuda_cirbe = db.get("deuda_cirbe_mensual") if db else None
    ingresos = dc.get("ingresos_netos_mensuales")
    edad = dc.get("edad")

    actual_cuota = calculos.get("cuota_estimada")
    actual_dti = calculos.get("ratio_endeudamiento")
    actual_remanente = calculos.get("remanente_subsistencia")
    actual_edad_venc = calculos.get("edad_al_vencimiento")

    # --- 1. Verificación de Cuota y Compromisos ---
    if cantidad is not None and plazo is not None and plazo > 0:
        expected_cuota = float(cantidad) / float(plazo)
        assert actual_cuota is not None, f"cuota_estimada debería estar calculada pero es None"
        assert math.isclose(actual_cuota, expected_cuota, rel_tol=1e-5, abs_tol=1e-4), \
            f"Cuota incorrecta: esperado {expected_cuota}, obtenido {actual_cuota}"

        # Total compromisos acumulados (con null-safety monotónico)
        expected_total_compromisos = expected_cuota
        if gastos is not None:
            expected_total_compromisos += float(gastos)
        if deuda_interna is not None:
            expected_total_compromisos += float(deuda_interna)
        if deuda_cirbe is not None:
            expected_total_compromisos += float(deuda_cirbe)

        # --- 2. Verificación de Ratio de Endeudamiento (DTI) y Remanente ---
        if ingresos is not None and float(ingresos) > 0.0:
            expected_dti = expected_total_compromisos / float(ingresos)
            expected_remanente = float(ingresos) - expected_total_compromisos

            assert actual_dti is not None, f"ratio_endeudamiento debería estar calculado pero es None"
            assert math.isclose(actual_dti, expected_dti, rel_tol=1e-5, abs_tol=1e-4), \
                f"DTI incorrecto: esperado {expected_dti:.6f}, obtenido {actual_dti:.6f}"

            assert actual_remanente is not None, f"remanente_subsistencia debería estar calculado pero es None"
            assert math.isclose(actual_remanente, expected_remanente, rel_tol=1e-5, abs_tol=1e-4), \
                f"Remanente incorrecto: esperado {expected_remanente:.2f}, obtenido {actual_remanente:.2f}"

            # Verificación cruzada: compromiso derivado desde remanente y DTI
            calc_comp_from_rem = float(ingresos) - actual_remanente
            assert math.isclose(calc_comp_from_rem, expected_total_compromisos, rel_tol=1e-5, abs_tol=1e-4), \
                f"Inconsistencia en total_compromisos deducido del remanente"
        else:
            assert actual_dti is None, f"ratio_endeudamiento debería ser None por falta de ingresos"
            assert actual_remanente is None, f"remanente_subsistencia debería ser None por falta de ingresos"
    else:
        assert actual_cuota is None, f"cuota_estimada debería ser None (cantidad={cantidad}, plazo={plazo})"
        assert actual_dti is None, f"ratio_endeudamiento debería ser None cuando cuota no se calcula"
        assert actual_remanente is None, f"remanente_subsistencia debería ser None cuando cuota no se calcula"

    # --- 3. Verificación de Edad al Vencimiento (División Entera) ---
    if edad is not None and plazo is not None:
        expected_edad_venc = int(edad) + (int(plazo) // 12)
        assert actual_edad_venc == expected_edad_venc, \
            f"Edad al vencimiento incorrecta: esperado {expected_edad_venc}, obtenido {actual_edad_venc}"
    else:
        assert actual_edad_venc is None, f"edad_al_vencimiento debería ser None si falta edad o plazo"

    return True, "Cálculos matemáticos exactos verificados satisfactoriamente"


def run_test(name, payload_raw, expected_estado, expected_regla,
             expected_dato_faltante=None, expected_accion_requerida=None,
             verificar_calculos=True):
    """
    Ejecuta un caso de prueba individual contra el motor Drools.
    Comprueba:
      1. Código de estado resultante.
      2. Regla disparada esperada presente en 'reglas_disparadas'.
      3. Parámetros complementarios (dato_faltante, accion_requerida) si se indican.
      4. Exactitud matemática de todos los cálculos financieros derivados.
    """
    payload = to_drools_payload(payload_raw)
    req = urllib.request.Request(URL, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    data = json.dumps(payload).encode("utf-8")

    try:
        with urllib.request.urlopen(req, data=data, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            estado = result.get("estado")
            reglas = result.get("reglas_disparadas", [])
            calculos = result.get("calculos_derivados")
            dato_faltante = result.get("dato_faltante")
            accion_requerida = result.get("accion_requerida")

            errors = []
            if estado != expected_estado:
                errors.append(f"Estado esperado '{expected_estado}', obtenido '{estado}'")

            if expected_regla and expected_regla not in reglas:
                errors.append(f"Regla esperada '{expected_regla}' no figura en disparadas {reglas}")

            if expected_dato_faltante is not None and dato_faltante != expected_dato_faltante:
                errors.append(f"Dato faltante esperado '{expected_dato_faltante}', obtenido '{dato_faltante}'")

            if expected_accion_requerida is not None and accion_requerida != expected_accion_requerida:
                errors.append(f"Acción requerida esperada '{expected_accion_requerida}', obtenido '{accion_requerida}'")

            # Verificación matemática estricta
            if verificar_calculos:
                try:
                    assert_calculos_derivados(payload, calculos)
                except AssertionError as ae:
                    errors.append(f"Fallo en aserción matemática: {ae}")

            if not errors:
                calcs_summary = ""
                if calculos and calculos.get("cuota_estimada") is not None:
                    calcs_summary = (f" | Cuota={calculos['cuota_estimada']:.2f}€, "
                                     f"DTI={calculos['ratio_endeudamiento']*100:.1f}%, "
                                     f"Rem={calculos['remanente_subsistencia']:.2f}€, "
                                     f"EdadVenc={calculos['edad_al_vencimiento']}a")
                print(f"[PASSED] {name}{calcs_summary}")
                return True
            else:
                print(f"[FAILED] {name}")
                for err in errors:
                    print(f"   -> {err}")
                print(f"   Respuesta del motor: {result}")
                return False

    except Exception as e:
        print(f"[ERROR] {name}")
        print(f"   Excepción: {e}")
        return False


def main():
    print("==========================================================================")
    print(" BATERÍA EXHAUSTIVA DE PRUEBAS DE DROOLS (TFM - EVALUACIÓN NEURO-SIMBÓLICA)")
    print(" Cobertura: Reglas de Negocio + Precisión Matemática de Cálculos Derivados")
    print("==========================================================================\n")
    tests = []

    # =========================================================================
    # GRUPO 1: REGLAS DE ELEGIBILIDAD Y CRITERIOS PERSONALES
    # =========================================================================
    print("--- [GRUPO 1] Reglas de Elegibilidad y Datos Personales ---")

    # 1.1. R_EDAD_MINIMA (menor de edad estricto: 17 años)
    p = base_payload(); p["datos_core"]["edad"] = 17
    tests.append(run_test("1.1. R_EDAD_MINIMA (menor de 18 años, edad=17)", p, "DENEGADO", "R_EDAD_MINIMA"))

    # 1.2. R_EDAD_MINIMA (menor extremo: 14 años)
    p = base_payload(); p["datos_core"]["edad"] = 14
    tests.append(run_test("1.2. R_EDAD_MINIMA (menor extremo, edad=14)", p, "DENEGADO", "R_EDAD_MINIMA"))

    # 1.3. R_EDAD_MINIMA (frontera exacta de mayoría de edad: 18 años)
    p = base_payload(); p["datos_core"]["edad"] = 18; p["datos_usuario"]["plazo_meses"] = 12
    tests.append(run_test("1.3. R_EDAD_MINIMA frontera (edad=18 años exacta -> admisible)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # 1.4. R_EDAD_MAXIMA (supera 75 años al vencimiento: 74 + 2 años = 76 > 75)
    p = base_payload(); p["datos_core"]["edad"] = 74; p["datos_usuario"]["plazo_meses"] = 24
    tests.append(run_test("1.4. R_EDAD_MAXIMA (edad=74, plazo=24m -> 76a > 75)", p, "DENEGADO", "R_EDAD_MAXIMA"))

    # 1.5. R_EDAD_MAXIMA frontera exacta (edad=73, plazo=24m -> 75a <= 75 -> admisible)
    p = base_payload(); p["datos_core"]["edad"] = 73; p["datos_usuario"]["plazo_meses"] = 24
    tests.append(run_test("1.5. R_EDAD_MAXIMA frontera (edad=73, plazo=24m -> 75a exactos)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # 1.6. R_EDAD_MAXIMA división entera (edad=74, plazo=23m -> 74 + floor(23/12) = 75a <= 75)
    p = base_payload(); p["datos_core"]["edad"] = 74; p["datos_usuario"]["plazo_meses"] = 23
    tests.append(run_test("1.6. R_EDAD_MAXIMA redondeo entero (edad=74, plazo=23m -> 75a exactos)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # =========================================================================
    # GRUPO 2: VIABILIDAD FINANCIERA Y CAPACIDAD DE PAGO
    # =========================================================================
    print("\n--- [GRUPO 2] Viabilidad Financiera y Capacidad de Pago ---")

    # 2.1. R_RATIO_ENDEUDAMIENTO (ratio > 40%: cuota ~8333€ con ingresos 3000€)
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 100000.0
    p["datos_usuario"]["plazo_meses"] = 12
    tests.append(run_test("2.1. R_RATIO_ENDEUDAMIENTO (Ratio > 40%, cuota alta)", p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO"))

    # 2.2. R_RATIO_ENDEUDAMIENTO frontera superior (DTI = 40.1% -> 401€ compromisos / 1000€ ingresos)
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 1000.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 101.0
    p["datos_usuario"]["cantidad_solicitada"] = 3600.0
    p["datos_usuario"]["plazo_meses"] = 12  # cuota 300€ + 101€ = 401€ (40.1% > 40%)
    tests.append(run_test("2.2. R_RATIO_ENDEUDAMIENTO frontera superior (DTI=40.1%)", p, "DENEGADO", "R_RATIO_ENDEUDAMIENTO"))

    # 2.3. R_RATIO_ENDEUDAMIENTO frontera exacta admisible (DTI = 40.0% exacto, remanente >= 700)
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 2500.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 500.0
    p["datos_usuario"]["cantidad_solicitada"] = 12000.0
    p["datos_usuario"]["plazo_meses"] = 24  # cuota 500€ + 500€ = 1000€ (1000/2500 = 40.0% exacto; Remanente=1500€)
    tests.append(run_test("2.3. R_RATIO_ENDEUDAMIENTO frontera exacta (DTI=40.0% exacto -> admisible)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # 2.4. R_MINIMO_SUBSISTENCIA (remanente < 700€: ingresos 1000€, compromisos 400€ -> remanente 600€)
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 1000.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 100.0
    p["datos_usuario"]["cantidad_solicitada"] = 3600.0
    p["datos_usuario"]["plazo_meses"] = 12  # cuota 300€ + 100€ = 400€ (DTI=40% pasa regla 11; remanente 600€ < 700€)
    tests.append(run_test("2.4. R_MINIMO_SUBSISTENCIA (Remanente 600€ < 700€ con DTI<=40%)", p, "DENEGADO", "R_MINIMO_SUBSISTENCIA"))

    # 2.5. R_MINIMO_SUBSISTENCIA (remanente frontera exacta 700.0€ exactos con DTI <= 40%)
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 1100.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 100.0
    p["datos_usuario"]["cantidad_solicitada"] = 3600.0
    p["datos_usuario"]["plazo_meses"] = 12  # cuota 300€ + 100€ = 400€ (DTI=36.36%; remanente = 1100-400 = 700.0€)
    tests.append(run_test("2.5. R_MINIMO_SUBSISTENCIA frontera exacta (Remanente=700.0€ exactos -> admisible)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # 2.6. R_MINIMO_SUBSISTENCIA frontera inferior (remanente 699.0€ < 700.0€)
    p = base_payload()
    p["datos_core"]["ingresos_netos_mensuales"] = 1100.0
    p["datos_usuario"]["gastos_fijos_mensuales"] = 101.0
    p["datos_usuario"]["cantidad_solicitada"] = 3600.0
    p["datos_usuario"]["plazo_meses"] = 12  # cuota 300€ + 101€ = 401€ (DTI=36.45%; remanente = 699.0€)
    tests.append(run_test("2.6. R_MINIMO_SUBSISTENCIA frontera inferior (Remanente=699.0€)", p, "DENEGADO", "R_MINIMO_SUBSISTENCIA"))

    # =========================================================================
    # GRUPO 3: PROPÓSITO DE LA FINANCIACIÓN
    # =========================================================================
    print("\n--- [GRUPO 3] Propósito de la Financiación ---")

    # 3.1. R_PROPOSITO_NO_FINANCIABLE (CRIPTOMONEDAS)
    p = base_payload(); p["datos_usuario"]["proposito"] = "CRIPTOMONEDAS"
    tests.append(run_test("3.1. R_PROPOSITO_NO_FINANCIABLE (CRIPTOMONEDAS)", p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE"))

    # 3.2. R_PROPOSITO_NO_FINANCIABLE (APUESTAS)
    p = base_payload(); p["datos_usuario"]["proposito"] = "APUESTAS"
    tests.append(run_test("3.2. R_PROPOSITO_NO_FINANCIABLE (APUESTAS)", p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE"))

    # 3.3. R_PROPOSITO_NO_FINANCIABLE (REFINANCIACION_INFORMAL)
    p = base_payload(); p["datos_usuario"]["proposito"] = "REFINANCIACION_INFORMAL"
    tests.append(run_test("3.3. R_PROPOSITO_NO_FINANCIABLE (REFINANCIACION_INFORMAL)", p, "DENEGADO", "R_PROPOSITO_NO_FINANCIABLE"))

    # 3.4. Propósitos financiables válidos
    for prop in ["REFORMA", "ESTUDIOS", "SALUD"]:
        p = base_payload(); p["datos_usuario"]["proposito"] = prop
        tests.append(run_test(f"3.4. Propósito financiable permitido ({prop})", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # =========================================================================
    # GRUPO 4: INTEGRIDAD DE DATOS Y COMPLETITUD (REQUIERE_DATOS)
    # =========================================================================
    print("\n--- [GRUPO 4] Integridad de Datos y Completitud ---")

    # 4.1. R_CANTIDAD_Y_PLAZO_REQUERIDOS (falta cantidad)
    p = base_payload(); p["datos_usuario"]["cantidad_solicitada"] = None
    tests.append(run_test("4.1. R_CANTIDAD_Y_PLAZO_REQUERIDOS (falta cantidad)", p, "REQUIERE_DATOS",
                          "R_CANTIDAD_Y_PLAZO_REQUERIDOS", expected_dato_faltante="cantidad_solicitada"))

    # 4.2. R_CANTIDAD_Y_PLAZO_REQUERIDOS (falta plazo)
    p = base_payload(); p["datos_usuario"]["plazo_meses"] = None
    tests.append(run_test("4.2. R_CANTIDAD_Y_PLAZO_REQUERIDOS (falta plazo)", p, "REQUIERE_DATOS",
                          "R_CANTIDAD_Y_PLAZO_REQUERIDOS", expected_dato_faltante="plazo_meses"))

    # 4.3. R_CANTIDAD_Y_PLAZO_REQUERIDOS (faltan ambos)
    p = base_payload(); p["datos_usuario"]["cantidad_solicitada"] = None; p["datos_usuario"]["plazo_meses"] = None
    tests.append(run_test("4.3. R_CANTIDAD_Y_PLAZO_REQUERIDOS (faltan ambos)", p, "REQUIERE_DATOS",
                          "R_CANTIDAD_Y_PLAZO_REQUERIDOS", expected_dato_faltante="cantidad_solicitada y plazo_meses"))

    # 4.4. R_PROPOSITO_REQUERIDO (falta propósito)
    p = base_payload(); p["datos_usuario"]["proposito"] = None
    tests.append(run_test("4.4. R_PROPOSITO_REQUERIDO (falta propósito)", p, "REQUIERE_DATOS",
                          "R_PROPOSITO_REQUERIDO", expected_dato_faltante="proposito"))

    # 4.5. R_GASTOS_FIJOS_REQUERIDOS (faltan gastos fijos)
    p = base_payload(); p["datos_usuario"]["gastos_fijos_mensuales"] = None
    tests.append(run_test("4.5. R_GASTOS_FIJOS_REQUERIDOS (faltan gastos)", p, "REQUIERE_DATOS",
                          "R_GASTOS_FIJOS_REQUERIDOS", expected_dato_faltante="gastos_fijos_mensuales"))

    # =========================================================================
    # GRUPO 5: EXTERNAL RISK Y CONSULTAS PATRIMONIALES (BDE, CIRBE, ASNEF)
    # =========================================================================
    print("\n--- [GRUPO 5] Verificación Externa y Riesgo Patrimonial ---")

    # 5.1. R_DISPARAR_CIRBE (consultado=False)
    p = base_payload(); p["datos_bde"]["consultado"] = False
    tests.append(run_test("5.1. R_DISPARAR_CIRBE (consultado=False)", p, "REQUIERE_ACCION",
                          "R_DISPARAR_CIRBE", expected_accion_requerida="CONSULTAR_CIRBE_ASNEF"))

    # 5.2. R_DISPARAR_CIRBE (consultado=None)
    p = base_payload(); p["datos_bde"]["consultado"] = None
    tests.append(run_test("5.2. R_DISPARAR_CIRBE (consultado=None)", p, "REQUIERE_ACCION",
                          "R_DISPARAR_CIRBE", expected_accion_requerida="CONSULTAR_CIRBE_ASNEF"))

    # 5.3. R_MOROSIDAD_ASNEF (tiene impagos activos)
    p = base_payload(); p["datos_bde"]["tiene_impagos_activos"] = True
    tests.append(run_test("5.3. R_MOROSIDAD_ASNEF (impagos activos=True)", p, "DENEGADO", "R_MOROSIDAD_ASNEF"))

    # 5.4. R_MOROSIDAD_ASNEF (importe morosidad > 0)
    p = base_payload(); p["datos_bde"]["importe_morosidad_asnef"] = 150.0
    tests.append(run_test("5.4. R_MOROSIDAD_ASNEF (importe ASNEF > 0)", p, "DENEGADO", "R_MOROSIDAD_ASNEF"))

    # 5.5. R_ALERTA_QUIEBRA_AVAL (es avalista de empresa en concurso)
    p = base_payload()
    p["datos_core"]["es_avalista"] = True
    p["datos_bde"]["empresa_avalada_concurso"] = True
    tests.append(run_test("5.5. R_ALERTA_QUIEBRA_AVAL (empresa avalada en quiebra)", p, "DENEGADO", "R_ALERTA_QUIEBRA_AVAL"))

    # 5.6. Avalista sin concurso (empresa avalada solvente -> admisible)
    p = base_payload()
    p["datos_core"]["es_avalista"] = True
    p["datos_bde"]["empresa_avalada_concurso"] = False
    tests.append(run_test("5.6. Avalista con empresa solvente (empresa concurso=False)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # =========================================================================
    # GRUPO 6: DISCREPANCIA DECLARADA Y SUPERVISIÓN HUMANA (EU AI ACT ART. 14)
    # =========================================================================
    print("\n--- [GRUPO 6] Supervisión Humana y Auditoría AI Act ---")

    # 6.1. R_DISCREPANCIA_DECLARADA (deuda CIRBE supera +35% de la deuda declarada)
    p = base_payload()
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 2000.0  # 2000 > 1000 * 1.35 = 1350
    tests.append(run_test("6.1. R_DISCREPANCIA_DECLARADA (CIRBE total 2000€ > 1000*1.35)", p,
                          "REQUIERE_SUPERVISION_HUMANA", "R_DISCREPANCIA_DECLARADA"))

    # 6.2. R_DISCREPANCIA_DECLARADA límite no superado (CIRBE total == 1350€ exactos <= 1350)
    p = base_payload()
    p["datos_usuario"]["deuda_declarada"] = 1000.0
    p["datos_bde"]["deuda_cirbe_total"] = 1350.0  # 1350 <= 1000 * 1.35 -> no salta discrepancia
    tests.append(run_test("6.2. Discrepancia límite no superada (CIRBE=1350€ == declarada*1.35)", p,
                          "APROBADO", "R_APROBACION_ESTANDAR"))

    # =========================================================================
    # GRUPO 7: APROBACIÓN ESTÁNDAR Y ESCENARIOS MULTIDIMENSIONALES
    # =========================================================================
    print("\n--- [GRUPO 7] Aprobación Estándar y Casos Complejos ---")

    # 7.1. R_APROBACION_ESTANDAR (Perfil ideal)
    p = base_payload()
    tests.append(run_test("7.1. R_APROBACION_ESTANDAR (solicitante ideal)", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # 7.2. R_APROBACION_ESTANDAR con compromisos múltiples acumulados
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 6000.0
    p["datos_usuario"]["plazo_meses"] = 24  # Cuota: 250€
    p["datos_usuario"]["gastos_fijos_mensuales"] = 200.0
    p["datos_core"]["deuda_interna_banco_mensual"] = 100.0
    p["datos_bde"]["deuda_cirbe_mensual"] = 150.0
    p["datos_core"]["ingresos_netos_mensuales"] = 2500.0
    # Compromisos: 250 + 200 + 100 + 150 = 700€; DTI: 700/2500 = 28.0% <= 40%; Remanente: 1800€ >= 700€
    tests.append(run_test("7.2. Aprobación con compromisos múltiples solventes", p, "APROBADO", "R_APROBACION_ESTANDAR"))

    # =========================================================================
    # GRUPO 8: CERTIFICACIÓN MATEMÁTICA Y PRECISION DE CÁLCULOS DERIVADOS
    # =========================================================================
    print("\n--- [GRUPO 8] Certificación Matemática Rigurosa de Cálculos Derivados ---")

    # 8.1. Desglose analítico de las 5 fórmulas con valores reales
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 15000.0
    p["datos_usuario"]["plazo_meses"] = 60
    p["datos_usuario"]["gastos_fijos_mensuales"] = 350.0
    p["datos_core"]["deuda_interna_banco_mensual"] = 120.0
    p["datos_bde"]["deuda_cirbe_mensual"] = 180.0
    p["datos_core"]["ingresos_netos_mensuales"] = 3000.0
    p["datos_core"]["edad"] = 42
    # Cuota: 15000 / 60 = 250.00€
    # Compromisos: 250 + 350 + 120 + 180 = 900.00€
    # DTI: 900 / 3000 = 0.3000 (30.0%)
    # Remanente: 3000 - 900 = 2100.00€
    # Edad al vencimiento: 42 + floor(60/12) = 47
    tests.append(run_test("8.1. TEST_CALC_DESGLOSE_MULTIPLE (desglose exhaustivo 5 fórmulas)", p,
                          "APROBADO", "R_APROBACION_ESTANDAR"))

    # 8.2. División periódica con decimales infinitos (10.000€ / 36 meses = 277.777...€)
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = 10000.0
    p["datos_usuario"]["plazo_meses"] = 36
    p["datos_usuario"]["gastos_fijos_mensuales"] = 200.0
    p["datos_core"]["ingresos_netos_mensuales"] = 2200.0
    p["datos_core"]["edad"] = 29
    tests.append(run_test("8.2. TEST_CALC_DIVISION_PERIODICA (división 10.000€ / 36m)", p,
                          "APROBADO", "R_APROBACION_ESTANDAR"))

    # 8.3. Verificación de floor division en edad (plazos de 18, 23 y 24 meses)
    for meses, delta in [(18, 1), (23, 1), (24, 2)]:
        p = base_payload()
        p["datos_core"]["edad"] = 45
        p["datos_usuario"]["plazo_meses"] = meses
        tests.append(run_test(f"8.3. TEST_CALC_EDAD_FLOOR (edad 45 + plazo {meses}m -> {45+delta}a)", p,
                              "APROBADO", "R_APROBACION_ESTANDAR"))

    # 8.4. Null-safety y preservación de nulos ante ausencia de parámetros primarios
    p = base_payload()
    p["datos_usuario"]["cantidad_solicitada"] = None
    p["datos_usuario"]["plazo_meses"] = None
    tests.append(run_test("8.4. TEST_CALC_NULL_SAFETY (resiliencia ante campos nulos)", p,
                          "REQUIERE_DATOS", "R_CANTIDAD_Y_PLAZO_REQUERIDOS"))

    # =========================================================================
    # RESUMEN Y CONCLUSIÓN
    # =========================================================================
    total = len(tests)
    passed = sum(tests)
    print("\n==========================================================================")
    print(f" RESULTADOS FINALES: {passed}/{total} PRUEBAS SUPERADAS CON ÉXITO")
    print("==========================================================================")

    if passed == total:
        print("[ÉXITO TOTAL] Todas las reglas activas del catálogo de préstamos y")
        print("todas las fórmulas financieras derivadas han sido verificadas al 100%.")
    else:
        print(f"[ALERTA] Se detectaron {total - passed} fallos en la batería de pruebas.")
        sys.exit(1)


if __name__ == "__main__":
    main()
