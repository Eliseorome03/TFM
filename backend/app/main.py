"""
main.py — Entrypoint principal de la aplicación FastAPI.

Configura la instancia FastAPI con:
  - Metadatos OpenAPI (título, descripción, versión)
  - Middleware CORS para el frontend local
  - Inclusión de todos los routers de la aplicación
  - Montaje de archivos estáticos en /static
  - Evento de startup para crear tablas si no existen
  - Healthcheck en la raíz

Arquitectura: Symbolic[Neuro] — el backend es el componente simbólico
que gobierna el pipeline; Mistral opera como servicio lingüístico encapsulado.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path

from app.database import engine, Base
from app.routers.chat_router import router as chat_router
from app.routers.clientes_router import router as clientes_router
from app.routers.bde_mock_router import router as bde_mock_router

# Importar modelos para que Base los registre antes del create_all
from app.models import ClienteModel, TrazaAuditoria  # noqa: F401

# Configuración del sistema de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Contexto de ciclo de vida de la aplicación.

    Startup: Crea las tablas de base de datos si no existen.
    Shutdown: Registra el apagado graceful.
    """
    logger.info("═══ Iniciando Sistema Neurosimbólico Bancario ═══")
    logger.info("Verificando/creando tablas en MariaDB...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tablas verificadas: 'clientes', 'trazas_auditoria'")
    except Exception as exc:
        logger.warning(
            "No se pudieron crear las tablas automáticamente: %s "
            "(normal si MariaDB aún no está disponible al arrancar)",
            str(exc),
        )
    logger.info("═══ Backend listo en http://0.0.0.0:8000 ═══")
    yield
    logger.info("═══ Apagando Sistema Neurosimbólico Bancario ═══")


# ── Instancia FastAPI ─────────────────────────────────────────────────────────

app = FastAPI(
    title="Sistema Neurosimbólico de Evaluación de Préstamos",
    description=(
        "API de orquestación para el sistema neurosimbólico bancario de evaluación "
        "de préstamos personales. Combina Mistral AI (NLU/NLG) con Drools KIE "
        "(motor de reglas normativas) bajo el paradigma Symbolic[Neuro] conforme "
        "al EU AI Act y la Directiva 2014/17/UE.\n\n"
        "**Componentes:**\n"
        "- `POST /api/chat`: Pipeline conversacional de 6 pasos con auditoría completa\n"
        "- `GET /api/clientes`: Catálogo de clientes para el selector del frontend\n"
        "- `GET /api/mock/bde/{dni}`: Simulación CIRBE/ASNEF del Banco de España\n"
    ),
    version="1.0.0",
    contact={
        "name": "TFM Neurosimbólico Bancario",
        "email": "tfm@universidad.es",
    },
    license_info={
        "name": "Proyecto TFM — Uso Académico",
    },
    lifespan=lifespan,
)


# ── Middleware CORS ───────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Inclusión de routers ──────────────────────────────────────────────────────

app.include_router(chat_router)
app.include_router(clientes_router)
app.include_router(bde_mock_router)


# ── Archivos estáticos (Frontend) ─────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app.mount(
    "/static",
    StaticFiles(directory=str(static_dir)),
    name="static",
)


# ── Healthcheck ───────────────────────────────────────────────────────────────

@app.get(
    "/",
    tags=["Sistema"],
    summary="Healthcheck del sistema",
    description="Verifica que el backend está operativo.",
    include_in_schema=True,
)
def healthcheck() -> JSONResponse:
    """
    Endpoint de healthcheck.

    Devuelve el estado del sistema y los endpoints disponibles.
    Útil para Docker healthcheck y monitorización.
    """
    return JSONResponse(
        content={
            "status": "ok",
            "sistema": "Sistema Neurosimbólico Bancario",
            "version": "1.0.0",
            "paradigma": "Symbolic[Neuro] — EU AI Act compliant",
            "endpoints": {
                "chat": "POST /api/chat",
                "clientes": "GET /api/clientes",
                "bde_mock": "GET /api/mock/bde/{dni}",
                "docs": "GET /docs",
                "redoc": "GET /redoc",
                "static": "GET /static/*",
            },
        }
    )
