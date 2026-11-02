# Sistema Conversacional Neuro-Simbólico para la Evaluación de Crédito Bancario

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Java](https://img.shields.io/badge/Java-17-ED8B00?style=flat&logo=openjdk&logoColor=white)](https://openjdk.org/)
[![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.2-6DB33F?style=flat&logo=springboot&logoColor=white)](https://spring.io/projects/spring-boot)
[![Drools](https://img.shields.io/badge/Drools_KIE-8.44-BA3925?style=flat&logo=redhat&logoColor=white)](https://www.drools.org/)
[![MariaDB](https://img.shields.io/badge/MariaDB-11.2-003545?style=flat&logo=mariadb&logoColor=white)](https://mariadb.org/)
[![Mistral AI](https://img.shields.io/badge/Mistral_AI-ministral--8b-FF7000?style=flat)](https://mistral.ai/)
[![Docker](https://img.shields.io/badge/Docker_Compose-Multi--Container-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

> **Trabajo Fin de Máster (TFM)**
> **Autor:** Eliseo Romero Marín  
> **Repositorio Oficial:** [https://github.com/Eliseorome03/TFM](https://github.com/Eliseorome03/TFM)  
> **Documento Completo:** [`TFM_Eliseo_Romero/build/tfm.pdf`](TFM_Eliseo_Romero/build/tfm.pdf)

---

## Tabla de Contenidos

1. [Visión General del Proyecto](#-visión-general-del-proyecto)
2. [Principios Arquitectónicos](#-principios-arquitectónicos)
3. [Stack Tecnológico](#-stack-tecnológico)
4. [Estructura del Repositorio](#-estructura-del-repositorio)
5. [Guía Rápida de Despliegue](#-guía-rápida-de-despliegue)
   - [Requisitos Previos](#requisitos-previos)
   - [Paso 1: Clonar el Repositorio](#paso-1-clonar-el-repositorio)
   - [Paso 2: Configurar Variables de Entorno (.env)](#paso-2-configurar-variables-de-entorno-env)
   - [Paso 3: Obtener API Key Gratuita de Mistral AI](#paso-3-obtener-api-key-gratuita-de-mistral-ai)
   - [Paso 4: Despliegue con Docker Compose](#paso-4-despliegue-con-docker-compose-recomendado)
   - [Despliegue Alternativo en Local (sin Docker)](#despliegue-alternativo-en-local-sin-docker)
6. [Acceso e Interacción con el Prototipo](#-acceso-e-interacción-con-el-prototipo)
   - [Interfaz Web y Consola de Auditoría](#interfaz-web-y-consola-de-auditoría)
   - [Perfiles de Prueba Simulados](#perfiles-de-prueba-simulados)
   - [Documentación Interactiva Swagger UI](#documentación-interactiva-swagger-ui)
7. [Batería de Pruebas y Evaluación](#-batería-de-pruebas-y-evaluación)
8. [Resolución de Problemas](#-resolución-de-problemas)
9. [Cita del Trabajo](#-cita-del-trabajo)

---

## Visión General del Proyecto

En sectores críticos y fuertemente regulados, como la originación de crédito bancario, los modelos de lenguaje masivo (LLMs) puros presentan deficiencias estructurales: carecen de un razonamiento deductivo verificable, sufren de alucinaciones y son vulnerables a ataques adversariales (*prompt injection*). Además, sus explicaciones *post-hoc* son meras racionalizaciones estadísticas que no garantizan la causalidad real de sus decisiones, entrando en conflicto con el **EU AI Act (Reglamento UE 2024/1689)** y la **Directiva 2014/17/UE**.

Este proyecto diseña, implementa y evalúa una **arquitectura conversacional neuro-simbólica** orientada a la **accountability**, separando estrictamente la comprensión probabilística del lenguaje natural del gobierno determinista de la lógica de negocio y concesión crediticia.

---

## Principios Arquitectónicos

* **Paradigma Symbolic[Neuro] (Kautz Nivel 1-2):** El componente simbólico (orquestador FastAPI + motor de reglas Drools) ostenta la máxima autoridad del flujo. El componente neuronal (Mistral AI) actúa exclusivamente como un servicio periférico para tareas lingüísticas acotadas: extracción estructurada de entidades (NLU) y redacción empática de respuestas (NLG).
* **Information State Update (ISU):** El contexto conversacional y de negocio no reside en la ventana de tokens estocástica del LLM, sino en una estructura de datos canónica y persistente (`InformationState`), gestionada de forma acumulativa turno a turno.
* **Explicabilidad Constitutiva:** La justificación legal de una denegación o aprobación no la genera el LLM; la explicación es la traza inmutable de las reglas de negocio (*facts* y *salience*) disparadas por Drools, vinculadas formalmente al marco normativo aplicable.
* **Mitigación de Prompt Injection (Read-Only State Dump):** El modelo generador (NLG) carece de acceso a herramientas de ejecución o bases de datos; solo recibe un volcado en modo solo lectura del dictamen formal emitido por Drools.
* **Trazabilidad Inmutable (AI Act - Art. 12):** La base de datos registra en la tabla `trazas_auditoria` cada micro-acción del flujo bajo un patrón *append-only*, permitiendo reconstruir retrospectivamente cualquier interacción.

```
Usuario envía mensaje
       │
       ▼
[1] EXTRACT_NLU ─────────────── Mistral (chat.parse) ──► EsquemaNLU
       │
       ▼
[2] FETCH_CORE_DATA ─────────── SELECT MariaDB (clientes) [solo turno 1]
       │
       ▼
[3] EVALUATE_DROOLS ─────────── POST /api/evaluate ──► Spring Boot Drools
       │     ▲
       │     │ (Reevaluación post-consulta)
       │     │
       ├─ ¿Estado == REQUIERE_ACCION (CONSULTAR_CIRBE_ASNEF)?
       │     │
       │     ▼
       │  [4] FETCH_CIRBE_ASNEF ─── BdeMockService (bde.json)
       │
       ▼
[5] GENERATE_NATURAL_RESPONSE ── Mistral (chat.complete) [Read-Only State Dump]
       │
       ▼
ChatResponse { respuesta, information_state, reglas_disparadas, estado }
```

---

## Stack Tecnológico

| Capa | Tecnología | Versión | Función |
|---|---|---|---|
| **Orquestador Backend** | FastAPI / Uvicorn | 0.115 / 0.32 | API REST asíncrona, validación Pydantic v2, orquestación ISU |
| **Componente Neuronal** | Mistral AI SDK | 2.9.4 | NLU con Structured Output (`ministral-8b-latest`) y NLG controlado |
| **Motor Simbólico** | Drools / KIE | 8.44 | Ejecución de reglas declarativas DRL (`prestamos.drl`), resolución por *salience* |
| **Servicio de Reglas** | Spring Boot | 3.2 (Java 17) | Microservicio REST desacoplado (`POST /api/evaluate`) |
| **Persistencia Relacional**| MariaDB | 11.2 | Ledger de auditoría (`trazas_auditoria`) y datos core (`clientes`) |
| **Frontend** | HTML5 / CSS3 / Vanilla JS | Nativo | Interfaz de chat y consola de inspección síncrona en tiempo real |
| **Contenedores** | Docker & Docker Compose | 20.10+ / v2+ | Aislamiento y orquestación multi-servicio en red privada |

---

## Estructura del Repositorio

```
.
├── docker-compose.yml           # Orquestación de MariaDB, Drools y Backend FastAPI
├── .env_aux                     # Plantilla auxiliar de variables de entorno
├── .gitignore                   # Exclusiones de control de versiones
├── bde.json                     # Simulación de ficheros CIRBE y ASNEF por DNI
├── backend/                     # Microservicio backend Python FastAPI
│   ├── Dockerfile
│   ├── requirements.txt         # Dependencias Python fijadas
│   └── app/
│       ├── main.py              # Punto de entrada de la API y rutas
│       ├── clients/             # Clientes OOP: mistral_client.py, drools_client.py
│       ├── models/              # Modelos ORM SQLAlchemy (cliente.py, traza.py)
│       ├── schemas/             # Contratos Pydantic (state.py, nlu.py, drools_io.py)
│       ├── services/            # Orquestador ISU, AuditTracker y Mock de solvencia
│       ├── routers/             # Endpoints /api/chat, /api/clientes, /api/mock
│       └── static/              # Frontend web (index.html, styles.css, app.js)
├── drools-app/                  # Microservicio Java Spring Boot con motor Drools
│   ├── Dockerfile               # Multi-stage build (Maven -> Eclipse Temurin JRE 17)
│   ├── pom.xml                  # Dependencias Maven (KIE / Drools)
│   └── src/main/
│       ├── java/es/banca/drools # Controladores REST y servicios Drools
│       └── resources/rules/
│           └── prestamos.drl    # Catálogo de 14 reglas DRL de negocio y salience
├── database/                    # Capa de base de datos relacional
│   └── init.sql                 # DDL de tablas y perfiles sintéticos de prueba
├── tests/                       # Baterías de evaluación y reproducibilidad
│   ├── drools/                  # Pruebas unitarias de reglas y salience
│   ├── NLU/                     # Métricas de extracción NLU contra Ground Truth
│   ├── NLG/                     # Evaluación de fidelidad NLG con LLM-as-a-Judge
│   └── end-to-end/              # 22 escenarios E2E (lingüísticos, Drools y seguridad)
├── TFM_Eliseo_Romero/           # Fuentes completas en LaTeX del Trabajo Fin de Máster
│   ├── tfm.tex                  # Documento principal
│   ├── anexo.tex                # Anexo A: Guía técnica de reproducción
│   ├── bibliografia.tex         # Referencias bibliográficas formales
│   └── build/tfm.pdf            # PDF compilado final del TFM
└── README.md                    # Documentación principal del repositorio
```

---

## Guía Rápida de Despliegue

### Requisitos Previos

* **Git** ($\ge$ 2.30)
* **Docker** ($\ge$ 20.10) y **Docker Compose** ($\ge$ v2.0) — *Vía recomendada*
* Opcional (solo si se ejecuta en local sin Docker): **Python 3.11**, **JDK 17**, **Maven 3.9+** y **MariaDB 11.2**.

---

### Paso 1: Clonar el Repositorio

```bash
git clone https://github.com/Eliseorome03/TFM.git
cd TFM
```

---

### Paso 2: Configurar Variables de Entorno (`.env`)

Por motivos de seguridad, el archivo `.env` que contiene credenciales y claves privadas está excluido de Git en `.gitignore`. En la raíz del repositorio se incluye un archivo auxiliar de plantilla denominado **`.env_aux`**.

Copia o renombra este archivo como `.env`:

* **Linux / macOS:**
  ```bash
  cp .env_aux .env
  ```
* **Windows (PowerShell):**
  ```powershell
  Copy-Item .env_aux .env
  ```
* **Windows (CMD):**
  ```cmd
  copy .env_aux .env
  ```

El archivo `.env` contiene:

```env
# .env - Variables de entorno del sistema
# Configuración leída por docker-compose.yml

# -- MISTRAL AI ------------------------------
MISTRAL_API_KEY=
MISTRAL_MODEL=ministral-8b-latest

# -- BASE DE DATOS MariaDB -------------------
MARIADB_ROOT_PASSWORD=root_secret_2024
MARIADB_DATABASE=banca_db
MARIADB_USER=banca_user
MARIADB_PASSWORD=banca_password_2024
MARIADB_PORT=3306

# -- MOTOR DE REGLAS DROOLS ------------------
DROOLS_PORT=8080
DROOLS_TIMEOUT=30

# -- BACKEND FastAPI -------------------------
BACKEND_PORT=8000
```

---

### Paso 3: Obtener API Key Gratuita de Mistral AI

El componente de procesamiento del lenguaje natural requiere una clave de API de Mistral AI. Para obtener una clave gratuita sin necesidad de introducir tarjeta de crédito:

1. Accede a la consola: https://console.mistral.ai/
2. Regístrate o inicia sesión (puedes usar tu cuenta de Google; no requiere verificación adicional). Tu cuenta se inicia en el plan **Free / Experiment Plan** (sin datos bancarios).
3. Si el botón **Nueva clave** de **Claves API** está bloqueado, usa la ruta alternativa:
   - Desde https://console.mistral.ai/home, localiza el apartado **Crea**.
   - Selecciona crear una clave de API.
   - Rellena el formulario: nombre (ej. `clave-tfm`), vencimiento por defecto (*Sin fecha de caducidad*) y ámbito por defecto (*Conectores y conexiones privados y compartidos*).
   - Pulsa **Nueva clave** para generar el token.
4. Copia la clave (se muestra una única vez) y pégala en el archivo `.env` en la raíz del repositorio:

```env
MISTRAL_API_KEY=tu_clave_obtenida_aqui
```

---

### Paso 4: Despliegue con Docker Compose (Recomendado)

Con Docker en ejecución, levanta todos los servicios con una sola instrucción:

```bash
docker compose up --build
```

Docker Compose orquestará automáticamente:
1. `banca_mariadb`: Inicializa la base de datos y ejecuta `database/init.sql`.
2. `banca_drools`: Compila y arranca el microservicio Drools en Spring Boot (puerto 8080), esperando a que MariaDB esté lista.
3. `banca_backend`: Instala dependencias y lanza FastAPI (puerto 8000), esperando a que MariaDB y Drools estén operativos.

Para detener los servicios:
```bash
docker compose down
```

Para reiniciar la base de datos a su estado original (borrando volúmenes persistentes):
```bash
docker compose down -v
```

---

### Despliegue Alternativo en Local (sin Docker)

Si deseas ejecutar cada servicio de forma nativa para depuración:

1. **Base de Datos:** Inicia MariaDB en el puerto 3306 y carga el esquema:
   ```bash
   mysql -u root -p < database/init.sql
   ```
2. **Motor Drools:** Compila y arranca la aplicación Java Spring Boot:
   ```bash
   cd drools-app
   mvn clean spring-boot:run
   ```
3. **Backend FastAPI:** En un entorno virtual de Python 3.11:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate       # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cp ../.env .env
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## Acceso e Interacción con el Prototipo

Una vez que los servicios están activos, se puede interactuar con el sistema a través de las siguientes interfaces:

### Interfaz Web y Consola de Auditoría

Abre tu navegador en:
**[http://localhost:8000/static/index.html](http://localhost:8000/static/index.html)**

La interfaz experimental cuenta con pantalla dividida:
* **Panel Izquierdo (Conversacional):** Chat interactivo con el asistente bancario. Incluye un selector de clientes predefinidos para simular solicitudes con diferentes perfiles de riesgo y solvencia.
* **Panel Derecho (Consola de Inspección):** Muestra en tiempo real la traza auditable de cada turno:
  - Micro-acciones ejecutadas en el turno (`EXTRACT_NLU`, `FETCH_CORE_DATA`, `EVALUATE_DROOLS`, etc.).
  - Dictamen formal de Drools (`APROBADO`, `DENEGADO`, `REQUIERE_DATOS`, `REQUIERE_SUPERVISION_HUMANA`).
  - Identificador de la regla DRL activada y justificación normativa asociada (Art. 18 Directiva 2014/17/UE).
  - Snapshot completo del contrato de datos `InformationState`.

### Perfiles de Prueba Simulados

El sistema carga cuatro perfiles sintéticos en la base de datos para verificar las distintas ramas decisorias:

| ID Cliente | Nombre | Características del Perfil | Veredicto Esperado |
|---|---|---|---|
| `CLI-001` | Juan Pérez | Ingresos solventes, sin deudas ni impagos | `APROBADO` (tras aportar datos) |
| `CLI-002` | María Gómez | Avalista de empresa en concurso de acreedores | `DENEGADO` (`R_ALERTA_QUIEBRA_AVAL`) |
| `CLI-003` | Carlos Ruiz | Morosidad activa registrada en ficheros ASNEF | `DENEGADO` (`R_MOROSIDAD_ASNEF`) |
| `CLI-004` | Ana Fernández | Solicitante cercana al límite de edad de amortización | `DENEGADO` (`R_EDAD_MAXIMA`) |

### Documentación Interactiva Swagger UI

La API REST del backend puede inspeccionarse directamente en:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

Permite enviar peticiones `POST /api/chat`, consultar clientes con `GET /api/clientes` o examinar los datos simulados de CIRBE/ASNEF mediante `GET /api/mock/bde/{dni}`.

---

## Resolución de Problemas

* **Error `HTTP 401 Unauthorized` al comunicarse con Mistral AI:**  
  Verifica que `MISTRAL_API_KEY` en tu archivo `.env` contenga el token generado sin comillas ni espacios adicionales.
* **Error `HTTP 429 Too Many Requests`:**  
  El plan gratuito de Mistral impone límites de peticiones por minuto. Si ejecutas scripts de pruebas automatizados masivos, introduce pausas breves de 1 segundo entre turnos.
* **Puerto en uso (`Port 8000, 8080 or 3306 already allocated`):**  
  Modifica los puertos en el archivo `.env` (`BACKEND_PORT`, `DROOLS_PORT`, `MARIADB_PORT`) a puertos libres en tu máquina anfitriona sin necesidad de modificar el código.
* **Restaurar base de datos limpia:**  
  Si deseas reiniciar la base de datos y borrar los registros de auditoría generados durante las pruebas:
  ```bash
  docker compose down -v
  docker compose up --build
  ```

---

## Cita del Trabajo

Si utilizas este trabajo o parte de su código en investigaciones académicas o proyectos profesionales, por favor cítalo como:

```bibtex
@misc{tfmGitHub,
  author       = {Romero Mar{\'\i}n, Eliseo},
  title        = {Repositorio de c{\'o}digo del Trabajo Fin de M{\'a}ster: Sistema Conversacional Neuro-Simb{\'o}lico para la Evaluaci{\'o}n Crediticia},
  year         = {2026},
  howpublished = {\url{https://github.com/Eliseorome03/TFM}}
}
```
