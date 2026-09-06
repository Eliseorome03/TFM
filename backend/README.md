# Backend — Sistema Neurosimbólico de Evaluación de Préstamos

## 1. Visión General

El servicio `backend/` es el **orquestador central** del sistema neurosimbólico bancario. Implementa el paradigma **Symbolic[Neuro]** (Kautz Nivel 1-2): el componente simbólico (este backend + Drools) gobierna y orquesta; el componente neuronal (Mistral AI) opera como servicio encapsulado para tareas lingüísticas estrictas.

### Stack Tecnológico

| Componente | Tecnología | Propósito |
|---|---|---|
| Framework API | FastAPI 0.115 + Uvicorn | Servidor REST, validación, OpenAPI |
| ORM | SQLAlchemy 2.0 | Acceso a MariaDB |
| Driver BD | PyMySQL 1.1 | Conector MariaDB/MySQL para SQLAlchemy |
| LLM Client | mistralai 1.2 (SDK oficial) | NLU (structured output) y NLG (read-only) |
| HTTP Client | httpx 0.28 | Llamadas al microservicio Drools |
| Validación | Pydantic v2 + pydantic-settings | Schemas y configuración tipada |

---

## 2. Estructura de Carpetas

```
backend/
├── Dockerfile              # Python 3.11-slim + pip install
├── requirements.txt        # Dependencias exactas con versiones fijadas
├── bde.json                # Datos CIRBE/ASNEF simulados (6 perfiles)
├── .env.example            # Plantilla de variables de entorno
└── app/
    ├── __init__.py
    ├── main.py             # FastAPI app: CORS, routers, static, lifespan
    ├── config.py           # Settings (pydantic-settings) desde .env
    ├── database.py         # Engine, SessionLocal, Base, get_db()
    │
    ├── models/             # ORM (tablas MariaDB)
    │   ├── cliente.py      # ClienteModel → tabla 'clientes'
    │   └── traza.py        # TrazaAuditoria → tabla 'trazas_auditoria'
    │
    ├── schemas/            # Contratos Pydantic
    │   ├── nlu.py          # EsquemaNLU + Enums (Intencion, Proposito, Duda)
    │   ├── state.py        # InformationState canónico completo
    │   ├── drools_io.py    # DroolsRequest / DroolsResponse tipados
    │   └── chat.py         # ChatRequest / ChatResponse (endpoint /api/chat)
    │
    ├── clients/            # Conectores externos OOP
    │   ├── mistral_client.py  # MistralClient: extraer_nlu() + generar_nlg()
    │   └── drools_client.py   # DroolsClient: evaluar_reglas() + construir_payload()
    │
    ├── services/           # Lógica de negocio
    │   ├── audit_tracker.py   # AuditTracker: ledger inmutable AI Act
    │   ├── bde_mock_service.py # BdeMockService: CIRBE/ASNEF simulado por DNI
    │   └── orchestrator.py    # PipelineOrchestrator: 6 pasos ISU
    │
    ├── routers/            # Endpoints FastAPI
    │   ├── chat_router.py     # POST /api/chat
    │   ├── clientes_router.py # GET /api/clientes
    │   └── bde_mock_router.py # GET /api/mock/bde/{dni}
    │
    └── static/             # Frontend (index.html, styles.css, app.js — Fase 2)
```

---

## 3. Variables de Entorno

Copiar `.env.example` como `.env` y rellenar los valores:

```bash
cp .env.example .env
```

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | URL de conexión MariaDB (pymysql) | `mysql+pymysql://user:pass@mariadb:3306/db` |
| `MISTRAL_API_KEY` | API Key de Mistral AI | `abc123...` |
| `DROOLS_URL` | URL del endpoint de Drools | `http://drools-engine:8080/api/evaluate` |
| `MISTRAL_MODEL` | Modelo Mistral a usar | `mistral-large-latest` |
| `DROOLS_TIMEOUT` | Timeout HTTP Drools (seg.) | `30` |
| `BDE_JSON_PATH` | Ruta al archivo bde.json | `bde.json` |

---

## 4. Pipeline Conversacional — Los 6 Pasos ISU

Cada mensaje del usuario activa hasta 6 micro-acciones registradas atómicamente en `trazas_auditoria`:

```
Usuario envía mensaje
       │
       ▼
[1] EXTRACT_NLU ─────────────── Mistral.chat.parse() → EsquemaNLU
       │
       ▼
[2] FETCH_CORE_DATA ─────────── SELECT clientes WHERE cliente_id=? (solo turno 1)
       │
       ▼
[3] EVALUATE_PRELIMINARY ────── POST /api/evaluate → Drools → DroolsResponse
       │
       ├─ estado == REQUIERE_ACCION + CONSULTAR_CIRBE_ASNEF?
       │          │
       │          ▼
       │  [4] FETCH_CIRBE_ASNEF ─── BdeMockService.consultar_por_dni()
       │          │
       │          ▼
       │  [5] EVALUATE_FINAL_DECISION ─── POST /api/evaluate (con datos BdE)
       │
       ▼
[6] GENERATE_NATURAL_RESPONSE ── Mistral.chat.complete() ← Read-Only State Dump
       │
       ▼
ChatResponse { respuesta, information_state, turn_id, estado_evaluacion }
```

### Estados de Evaluación Drools

| Estado | Significado |
|---|---|
| `EN_PROCESO` | Evaluación en curso (estado inicial) |
| `REQUIERE_DATOS` | Falta un dato obligatorio (pedir al usuario) |
| `REQUIERE_ACCION` | Backend debe ejecutar acción (consultar CIRBE) |
| `REQUIERE_SUPERVISION_HUMANA` | Anomalía detectada — escalar a especialista |
| `DENEGADO` | Solicitud denegada por regla normativa |
| `APROBADO` | Capacidad de pago comprobada — préstamo aprobado |

---

## 5. Esquema de Auditoría (AI Act)

La tabla `trazas_auditoria` actúa como **ledger inmutable** conforme al EU AI Act:

```sql
CREATE TABLE trazas_auditoria (
    id                BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id        VARCHAR(64) NOT NULL,       -- UUID de sesión
    turn_id           INT NOT NULL,               -- Número de turno
    step_order        INT NOT NULL,               -- 1 a 6
    action_type       VARCHAR(64) NOT NULL,       -- Nombre de la micro-acción
    step_input        JSON,                       -- Input exacto al componente
    step_output       JSON,                       -- Output del componente
    information_state JSON,                       -- Snapshot completo post-paso
    created_at        TIMESTAMP DEFAULT NOW()     -- Marca temporal precisa
);
```

---

## 6. Datos Mock CIRBE/ASNEF (bde.json)

El archivo `bde.json` simula 6 perfiles del Banco de España:

| DNI | Perfil | Comportamiento |
|---|---|---|
| `12345678A` | Cliente solvente | Sin impagos, deuda CIRBE baja |
| `87654321B` | Cliente con morosidad | ASNEF activo → denegación |
| `11223344C` | Avalista en riesgo | Empresa avalada en concurso → denegación |
| `99887766D` | Cliente endeudado | CIRBE mensual alto → ratio excedido |
| `55443322E` | Cliente joven solvente | Sin deudas externas |
| `66778899F` | Cliente autónomo | CIRBE medio, avalista |
| Cualquier otro | Perfil por defecto | Sin impagos, limpio |

---

## 7. API Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Healthcheck del sistema |
| `POST` | `/api/chat` | Pipeline conversacional completo |
| `GET` | `/api/clientes` | Catálogo de clientes (para desplegable UI) |
| `GET` | `/api/mock/bde/{dni}` | Consulta CIRBE/ASNEF simulada por DNI |
| `GET` | `/api/mock/bde` | Lista DNIs catalogados en el mock |
| `GET` | `/docs` | Swagger UI interactivo |
| `GET` | `/redoc` | ReDoc (documentación alternativa) |
| `GET` | `/static/*` | Archivos estáticos del frontend |

### Ejemplo: POST /api/chat

**Request:**
```json
{
  "mensaje": "Quiero pedir 12000 euros a 48 meses para comprarme un coche",
  "cliente_id": "CLI001",
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "respuesta": "Gracias por su solicitud. Necesitamos conocer sus gastos fijos mensuales...",
  "information_state": { ... },
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "turn_id": 1,
  "estado_evaluacion": "REQUIERE_DATOS"
}
```

---

## 8. Ejecución Local (sin Docker)

```bash
# Desde el directorio backend/
cd backend

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
copy .env.example .env
# Editar .env con los valores reales

# Arrancar el servidor
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

El servidor estará disponible en: `http://localhost:8000`
La documentación interactiva en: `http://localhost:8000/docs`

---

## 9. Ejecución con Docker Compose

```bash
# Desde la raíz del proyecto
docker-compose up --build

# Solo el backend
docker-compose up backend
```

---

## 10. Arquitectura de Clases

```
MistralClient
├── extraer_nlu(mensaje) → EsquemaNLU     [chat.parse — structured output]
└── generar_nlg(state, mensaje) → str     [chat.complete — read-only state dump]

DroolsClient
├── evaluar_reglas(payload) → DroolsResponse  [HTTP POST con httpx]
└── construir_payload(state) → dict           [InformationState → DroolsRequest]

BdeMockService
├── consultar_por_dni(dni) → dict    [Lee bde.json, perfil específico o default]
└── listar_dnis_catalogados() → list

AuditTracker
├── registrar_paso(session_id, turn_id, step_order, ...) → TrazaAuditoria
└── obtener_trazas_sesion(session_id) → list[TrazaAuditoria]

PipelineOrchestrator
└── procesar_turno_conversacional(mensaje, cliente_id, session_id, db)
    → tuple[respuesta: str, information_state: dict]
```

---

## 11. Notas de Diseño

### Paradigma Symbolic[Neuro]
El LLM (Mistral) nunca toma decisiones de negocio. Tiene dos roles:
1. **NLU**: Extrae entidades del lenguaje natural → `EsquemaNLU`
2. **NLG**: Redacta el mensaje al usuario leyendo el estado en modo solo lectura

### Mitigación de Prompt Injection
El NLG recibe un "Read-Only State Dump": un volcado estructurado del `information_state` sin herramientas de ejecución. El LLM no puede modificar estados, acceder a BD, ni ejecutar código.

### Information State Update (ISU)
El estado (`information_state`) es acumulativo entre turnos:
- Los datos conocidos se preservan entre turnos
- Los nuevos datos del NLU sobreescriben o complementan (nunca borran)
- Los datos BdE se consultan solo una vez por sesión

### Inmutabilidad del Ledger
La tabla `trazas_auditoria` solo recibe INSERTs, nunca UPDATEs. Cada paso del pipeline genera una fila atómica e irrevocable con el snapshot completo del estado.
