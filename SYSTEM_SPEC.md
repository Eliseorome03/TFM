# Especificación del Sistema Neurosimbólico Bancario

## 1. Visión General del Proyecto y Principios Arquitectónicos

El objetivo de este sistema es evaluar solicitudes de préstamos personales combinando la flexibilidad conversacional de un modelo neuronal (**Mistral**) con el determinismo, trazabilidad y gobernanza de un motor de reglas simbólico (**Drools**). Todo el diseño responde a las exigencias regulatorias de la **Directiva 2014/17/UE** y del **EU AI Act** para sistemas de alto riesgo.

* **Paradigma Arquitectónico (Kautz Nivel 1-2: Symbolic[Neuro]):** El componente simbólico (código backend + Drools) gobierna y orquesta. El componente neuronal (Mistral) opera como servicio encapsulado para dos tareas lingüísticas estrictas: extracción estructurada (NLU) y redacción fiel (NLG).
* **Information State Update (ISU):** El contexto conversacional y de negocio no reside en la ventana de tokens del LLM, sino en una estructura formal inmutable (`information_state`) gestionada paso a paso.
* **Explicabilidad Constitutiva:** La justificación legal y fáctica de una decisión no se genera post-hoc como una racionalización del LLM. La traza literal de las reglas disparadas en Drools constituye la explicación auditable por construcción.
* **RAG Simbólico Gobernado:** Se prescinde de búsqueda vectorial heurística. Las referencias legales (Directiva 2014/17/UE, Código Civil, etc.) están indexadas formalmente por Drools y se devuelven asociadas a la regla que las detona.
* **Mitigación de Prompt Injection (Read-Only State Dump):** El LLM de salida (NLG) carece de herramientas de ejecución. Recibe el volcado del estado emitido por Drools en modo solo lectura, neutralizando el impacto transaccional de ataques de inyección.

---

## 2. Contrato Canónico de Datos: `information_state`

Este esquema JSON define la verdad del sistema en cualquier instante del diálogo.

```json
{
  "session_id": "string (UUID)",
  "turn_id": "integer",
  "datos_usuario": {
    "intencion_principal": "string (SOLICITAR_PRESTAMO | CONSULTAR_DUDA | SALUDAR | OTRA)",
    "cantidad_solicitada": "float | null",
    "plazo_meses": "integer | null",
    "proposito": "string (VEHICULO | REFORMA | ESTUDIOS | SALUD | OTRO | CRIPTOMONEDAS | APUESTAS | REFINANCIACION_INFORMAL | null)",
    "gastos_fijos_mensuales": "float | null", 
    "deuda_declarada": "float | null",
    "duda_catch_all": "string (NINGUNA | REQUISITOS_APROBACION | CONDICIONES_CANCELACION | NORMATIVA_SOLVENCIA | FUERA_DE_DOMINIO)"
  },
  "datos_core_bancario": {
    "cliente_id": "string",
    "nombre": "string",
    "dni": "string",
    "edad": "integer",
    "ingresos_netos_mensuales": "float",
    "antiguedad_meses": "integer",
    "deuda_interna_banco_mensual": "float",
    "es_avalista": "boolean",
    "empresa_avalada_cif": "string | null"
  },
  "datos_externos_bde": {
    "consultado": "boolean",
    "tiene_impagos_activos": "boolean",
    "importe_morosidad_asnef": "float",
    "empresa_avalada_concurso": "boolean | null",
    "deuda_cirbe_mensual": "float",
    "deuda_cirbe_total": "float"
  },
  "calculos_derivados": {
    "cuota_estimada": "float",
    "ratio_endeudamiento": "float",
    "remanente_subsistencia": "float",
    "edad_al_vencimiento": "integer"
  },
  "evaluacion_drools": {
    "estado": "string (EN_PROCESO | REQUIERE_DATOS | REQUIERE_ACCION | REQUIERE_SUPERVISION_HUMANA | DENEGADO | APROBADO)",
    "reglas_disparadas": ["string"],
    "accion_requerida": "string | null",
    "dato_faltante": "string | null",
    "articulo_normativo": "string | null",
    "texto_legal": "string | null"
  }
}
```

---

## 3. Esquemas de Intercambio

### 3.1. Entrada a Drools (`POST /evaluar`)

Drools recibe una versión aplanada o anidada de los datos consolidados:
* Campos numéricos y descriptivos de `datos_usuario` y `datos_core_bancario`.
* Campos de `datos_externos_bde`.

### 3.2. Salida de Drools

```json
{
  "estado": "DENEGADO",
  "reglas_disparadas": ["R_RATIO_ENDEUDAMIENTO"],
  "accion_requerida": null,
  "dato_faltante": null,
  "calculos_derivados": {
    "cuota_estimada": 250.0,
    "ratio_endeudamiento": 0.45,
    "remanente_subsistencia": 1050.0,
    "edad_al_vencimiento": 36
  },
  "articulo_normativo": "Art. 18 Directiva 2014/17/UE",
  "texto_legal": "El ratio máximo de endeudamiento no debe exceder el 40% de los ingresos netos mensuales del solicitante, salvo excepciones justificadas.",
  "tono_mensaje": "firme, claro y respetuoso"
}
```

### 3.3. Salida de NLU Mistral (`EsquemaNLU`)

Input: texto del usuario ('Quiero pedir 12 mil euros para devolver en 48 meses para comprarme un coche')

Output:

```json
{
  "intencion_principal": "SOLICITAR_PRESTAMO",
  "cantidad_solicitada": 12000.0,
  "plazo_meses": 48,
  "proposito": "VEHICULO",
  "gastos_fijos_mensuales": null,
  "deuda_declarada": null,
  "duda_catch_all": "NINGUNA"
}
```

---

## 4. Catálogo de Reglas en Drools DRL

<!-- quiero añadir en las reglas el tono que debe tener el mensaje que se envía al usuario según la regla que se active, lo quiero añadir como un campo más de la salida de drools -->

| Regla | Prioridad (*Salience*) | Condición Lógica | Estado Resultante / Acción | Justificación Normativa | Tono |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `R_EDAD_MINIMA` | 100 | `edad < 18` | `DENEGADO` | Criterios de capacidad legal y riesgo actuarial por edad (préstamos a menores de edad no permitidos) | `firme, claro y respetuoso` |
| `R_EDAD_MAXIMA` | 95 | `(edad + (plazo_meses / 12)) > 75` | `DENEGADO` | Criterios de capacidad legal y riesgo actuarial por edad (al vencimiento del prestamo el cliente no debe superar los 75 años) | `claro, respetuoso y transparente` |
| `R_RATIO_ENDEUDAMIENTO` | 92 | `ratio_endeudamiento > 0.40` | `DENEGADO` | Directiva 2014/17/UE y Banco de España (Límite máximo del 40% de endeudamiento) |`firme, claro y respetuoso`|
| `R_MINIMO_SUBSISTENCIA` | 91 | `remanente_subsistencia < 700.0` | `DENEGADO` | Art. 607 LEC (Mínimo vital inembargable derivado del SMI) |`serio, prudente y respetuoso`|
| `R_PROPOSITO_NO_FINANCIABLE` | 90 | `proposito in ("CRIPTOMONEDAS", "APUESTAS", "REFINANCIACION_INFORMAL")` | `DENEGADO` | Ley 10/2010 PBC y directrices EBA sobre originación de crédito prudencial | `firme, profesional y no acusatorio` |
<!-- regla para asegurar que hayan puesto la cantidad y el plazo (o lo haya inferido el LLM con los dicho por el cliente) -->
| `R_CANTIDAD_Y_PLAZO_REQUERIDOS` | 85 | `cantidad_solicitada == null \|\| plazo_meses == null` | `REQUIERE_DATOS`<br>`dato_faltante: "cantidad_solicitada" o "plazo_meses"` | Debe conocerse la cantidad y el plazo del prestamo para evaluar el riesgo | `amable, orientativo y conciso` |
<!-- regla para pedir un proposito del prestamo -->
| `R_PROPOSITO_REQUERIDO` | 80 | `proposito == null`   | `REQUIERE_DATOS`<br>`dato_faltante: "proposito"` | Debe conocerse el proposito del prestamo para evaluar el riesgo | `amable, cercano y orientativo` |
<!-- pedir gastos fijos (donde se incluyen cosas como alquiler, gastos de suministros, etc) estimados No incluye deudas ya se recogen por otro lado -->
| `R_GASTOS_FIJOS_REQUERIDOS` | 75 | `gastos_fijos_mensuales == null`   | `REQUIERE_DATOS`<br>`dato_faltante: "gastos_fijos_mensuales"` | Art. 18 Directiva 2014/17/UE (Obligación de computar los compromisos periódicos ineludibles para evaluar la solvencia real) | `amable, sencillo y orientativo (explicar que no se refiere a deudas, sino a gastos fijos como por ej alquiler, gastos de suministros, etc.)`|
| `R_DISPARAR_CIRBE` | 70 | `datos_externos_bde.consultado == false` | `REQUIERE_ACCION`<br>`accion_requerida: "CONSULTAR_CIRBE_ASNEF"` | Obligación regulatoria de consulta previa a ficheros de solvencia patrimonial |  |
| `R_MOROSIDAD_ASNEF` | 60 | `datos_externos_bde.tiene_impagos_activos == true \|\| datos_externos_bde.importe_morosidad_asnef > 0` | `DENEGADO` | Criterios prudenciales de morosidad crediticia | `firme, profesional y especialmente cuidadoso`|
| `R_ALERTA_QUIEBRA_AVAL` | 50 | `es_avalista == true && datos_externos_bde.empresa_avalada_concurso == true` | `DENEGADO` | Riesgo concursal indirecto exigible a corto plazo (Criterios EBA) | `serio, prudente y respetuoso`|
| `R_DEUDA_DECLARADA_REQUERIDA` | 45 | `deuda_declarada == null`   | `REQUIERE_DATOS`<br>`dato_faltante: "deuda_declarada"` | Obligación de computar los compromisos ineludibles para evaluar la solvencia real |`amable, claro y orientativo`|
| `R_DISCREPANCIA_DECLARADA` | 40 | `datos_externos_bde.deuda_cirbe_total > (deuda_declarada * 1.35)` | `REQUIERE_SUPERVISION_HUMANA` | Art. 14 EU AI Act (Supervisión humana ante anomalías no resueltas) |`neutral, prudente y no acusatorio`|
| `R_APROBACION_ESTANDAR` | 10 | Sin alertas morosas, `ratio <= 0.35`, `remanente >= 700` | `APROBADO` | Art. 18.1 Directiva 2014/17/UE (Capacidad positiva comprobada) |`positivo, claro y profesional`|

### Fórmulas de derivación ejecutadas previamente en Drools o en el motor de cálculo:

$$
\text{cuota\_estimada} = \frac{\text{cantidad\_solicitada}}{\text{plazo\_meses}}
$$

$$
\text{ratio\_endeudamiento} = \frac{\text{cuota\_estimada} + \text{gastos\_fijos\_mensuales (as 0 if null)} + \text{deuda\_banco} + \text{deuda\_cirbe (as 0 if null)}}{\text{ingresos\_netos\_mensuales}}
$$

$$
\text{remanente\_subsistencia} = \text{ingresos\_netos\_mensuales} - (\text{cuota\_estimada} + \text{gastos\_fijos\_mensuales (as 0 if null)} + \text{deuda\_banco} + \text{deuda\_cirbe (as 0 if null)})
$$

$$
\text{edad\_al\_vencimiento} = \text{edad} + \frac{\text{plazo\_meses}}{12}
$$

---

## 5. El Flujo de Ejecución por Acciones Dinámicas (Auditoría AI Act)

Cada turno conversacional ejecuta acciones dinámicamente que quedan registradas individualmente en `trazas_auditoria`:

1. **`EXTRACT_NLU`**: Mistral procesa el mensaje del usuario y devuelve `EsquemaNLU`.
2. **`FETCH_CORE_DATA`**: FastAPI extrae el registro de la tabla `clientes` para el cliente seleccionado (solo en el primer turno, en los sucesivos se guarda en el estado de la sesión y no es necesario volver a consultarlo a la base de datos).
3. **`EVALUATE_DROOLS`**: Drools evalúa los datos reunidos. Puede ejecutarse varias veces en un mismo turno si solicita datos externos.
4. **`FETCH_CIRBE_ASNEF`** *(Condicional)*: Si Drools devuelve `REQUIERE_ACCION`, FastAPI consulta el mock del Banco de España (CIRBE / ASNEF). Tras esto, se re-evalúa el motor (`EVALUATE_DROOLS`).
5. **`GENERATE_NATURAL_RESPONSE`**: Mistral recibe el `information_state` final en modo solo lectura y genera la respuesta textual ayudandose del information_state para informar al usuario de la falta de datos, o decisión obtenida.


## 6. Estructura de Carpetas sugerida:

  mi-tfm-neurosimbolico/
├── docker-compose.yml
├── .env
├── .env.example
├── SYSTEM_SPEC.md
│
├── database/
│   └── init.sql                         # DDL de MariaDB (tablas clientes y trazas) + 4 perfiles mock
│
├── drools-app/                          # Microservicio Java (Spring Boot + Drools KIE)
│   ├── Dockerfile                       # Multi-stage build Maven + Eclipse Temurin / OpenJDK 17
│   ├── pom.xml                          # Dependencias de Spring Boot y drools-core/drools-compiler
│   └── src/
│       └── main/
│           ├── java/com/example/demo/
│           │   ├── DemoApplication.java # Entrypoint de la aplicación Spring Boot
│           │   ├── config/
│           │   │   └── DroolsConfig.java # Bean configuration (KieServices, KieContainer)
│           │   ├── controller/
│           │   │   └── RuleController.java # POST /evaluar (SolicitudEvaluacion -> ResultadoEvaluacion)
│           │   ├── model/               # POJOs con getters/setters y tipos Wrapper para admitir nulls
│           │   │   ├── DatosUsuario.java
│           │   │   ├── DatosCore.java
│           │   │   ├── DatosBde.java
│           │   │   ├── CalculosDerivados.java
│           │   │   ├── SolicitudEvaluacion.java # Agregador de entrada
│           │   │   └── ResultadoEvaluacion.java # DTO de salida con estado, reglas y textos legales
│           │   └── service/
│           │       └── DroolsService.java # Cálculo de fórmulas, KieSession stateless y fireAllRules()
│           └── resources/
│               ├── META-INF/
│               │   └── kmodule.xml      # Descriptivo KIE estándar
│               └── rules/
│                   └── prestamos.drl    # Las 14 reglas auditables con salience exacto
│
└── backend/                             # Orquestador Python (FastAPI + OOP + SDK nativo mistralai)
    ├── Dockerfile                       # Python 3.11/3.12-slim + pip install requirements.txt
    ├── requirements.txt                 # fastapi, uvicorn, sqlalchemy, pymysql, mistralai, pydantic, httpx
    └── app/
        ├── __init__.py
        ├── main.py                      # Instancia FastAPI, CORS, inclusión de routers y mount /static
        ├── config.py                    # Class Settings (pydantic-settings) para variables de entorno
        ├── database.py                  # Engine SQLAlchemy, SessionLocal y dependencia get_db
        │
        ├── models/                      # Entidades ORM (Tablas de MariaDB)
        │   ├── __init__.py
        │   ├── cliente.py               # class ClienteModel(Base) mapeado a datos_core_bancario
        │   └── traza.py                 # class TrazaAuditoria(Base) para el ledger inmutable AI Act
        │
        ├── schemas/                     # Contratos de datos y validación Pydantic
        │   ├── __init__.py
        │   ├── nlu.py                   # Enums (Intencion, Proposito, Duda) y class EsquemaNLU
        │   ├── state.py                 # Esquema canónico completo de information_state
        │   ├── drools_io.py             # DTOs tipados de entrada/salida para el microservicio Drools
        │   └── chat.py                  # Request/Response del endpoint conversacional del frontend
        │
        ├── clients/                     # Conectores externos orientados a objetos
        │   ├── __init__.py
        │   ├── mistral_client.py        # class MistralClient (chat.parse para NLU y chat.complete para NLG)
        │   └── drools_client.py         # class DroolsClient (HTTP POST con httpx hacia drools-app:8080)
        │
        ├── services/                    # Lógica de negocio y orquestación
        │   ├── __init__.py
        │   ├── audit_tracker.py         # class AuditTracker (persiste snapshots inmutables por micro-acción)
        │   ├── bde_mock_service.py      # class BdeMockService (simulación CIRBE/ASNEF por DNI)
        │   └── orchestrator.py          # class PipelineOrchestrator (orquestador de los 6 pasos del ciclo)
        │
        ├── routers/                     # Capa de transporte y endpoints
        │   ├── __init__.py
        │   ├── chat_router.py           # POST /api/chat (invoca PipelineOrchestrator)
        │   ├── clientes_router.py       # GET /api/clientes (alimenta el selector de clientes del UI)
        │   └── bde_mock_router.py       # GET /api/mock/bde/{dni} (simulación HTTP externa)
        │
        └── static/                      # Frontend web nativo
            ├── index.html               # Chat, selector de usuario, tarjeta core y panel debug JSON
            ├── styles.css               # Estilos visuales banking
            └── app.js                   # Gestión de session_id, llamadas fetch y actualización reactiva