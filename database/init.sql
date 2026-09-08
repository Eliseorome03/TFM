-- =============================================================================
-- init.sql — Script de Inicialización DDL para MariaDB 11.2
--
-- Sistema Neurosimbólico de Evaluación de Préstamos
-- Conformidad: EU AI Act (Art. 14 supervisión humana) + Directiva 2014/17/UE
--
-- Crea la base de datos `banca_db`, las tablas `clientes` y `trazas_auditoria`
-- e inserta 4 perfiles de cliente mock para validación del sistema completo.
--
-- ORDEN DE EJECUCIÓN:
--   1. Creación de base de datos y selección
--   2. Tabla `clientes` (datos de core bancario — solo lectura en runtime)
--   3. Tabla `trazas_auditoria` (ledger inmutable de auditoría AI Act)
--   4. INSERT de 4 perfiles mock para demostración
-- =============================================================================

-- ── 1. BASE DE DATOS ──────────────────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS banca_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE banca_db;

-- =============================================================================
-- TABLA: clientes
-- Mapea el perfil bancario core de cada cliente (DatosCoreBancario del ISU).
-- Tabla de SOLO LECTURA durante el pipeline conversacional en runtime.
-- Se alimenta exclusivamente mediante este script SQL de inicialización.
-- =============================================================================

CREATE TABLE IF NOT EXISTS clientes (
    -- Identificador único del cliente (PK)
    cliente_id                  VARCHAR(64)     NOT NULL,

    -- Documento Nacional de Identidad (único, indexado para búsquedas BdE)
    dni                         VARCHAR(20)     NOT NULL,

    -- Datos demográficos y financieros core
    edad                        INT             NOT NULL
                                    COMMENT 'Edad en años del titular en la fecha de alta',

    ingresos_netos_mensuales    DOUBLE          NOT NULL
                                    COMMENT 'Ingresos netos tras impuestos (EUR/mes)',

    antiguedad_meses            INT             NOT NULL DEFAULT 0
                                    COMMENT 'Antigüedad como cliente del banco (en meses)',

    deuda_interna_banco_mensual DOUBLE          NOT NULL DEFAULT 0.0
                                    COMMENT 'Cuota mensual de deudas activas con este banco (EUR/mes)',

    -- Datos de aval (críticos para la regla R_ALERTA_QUIEBRA_AVAL)
    es_avalista                 BOOLEAN         NOT NULL DEFAULT FALSE
                                    COMMENT 'TRUE si el cliente actúa como avalista de terceros',

    empresa_avalada_cif         VARCHAR(20)     NULL DEFAULT NULL
                                    COMMENT 'CIF de la empresa avalada (solo cuando es_avalista=TRUE)',

    -- Claves e índices
    PRIMARY KEY (cliente_id),
    UNIQUE KEY uq_clientes_dni (dni),
    KEY idx_clientes_dni (dni)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Perfil bancario core de clientes — Alineado con DatosCoreBancario del ISU (SYSTEM_SPEC.md §2)';


-- =============================================================================
-- TABLA: trazas_auditoria
-- Ledger inmutable de auditoría por micro-acción.
-- Requerido por EU AI Act Art. 14 (supervisión humana de sistemas de alto riesgo)
-- y Art. 12 (registro de logs para sistemas de alto riesgo).
--
-- Cada registro = 1 micro-acción atómica del pipeline de 6 pasos:
--   EXTRACT_NLU | FETCH_CORE_DATA | EVALUATE_PRELIMINARY |
--   FETCH_CIRBE_ASNEF | EVALUATE_FINAL_DECISION | GENERATE_NATURAL_RESPONSE
-- =============================================================================

CREATE TABLE IF NOT EXISTS trazas_auditoria (
    -- Identificador único de la traza (BIGINT para soportar alto volumen)
    id                  BIGINT          NOT NULL AUTO_INCREMENT,

    -- Identificadores de correlación conversacional
    session_id          VARCHAR(64)     NOT NULL
                            COMMENT 'UUID de la sesión conversacional (generado en frontend)',
    turn_id             INT             NOT NULL
                            COMMENT 'Número de turno conversacional (1, 2, 3...)',
    step_order          INT             NOT NULL
                            COMMENT 'Secuencia cronológica dentro del turno (1 a 6)',

    -- Tipo de micro-acción registrada
    action_type         VARCHAR(64)     NOT NULL
                            COMMENT 'Nombre formal de la micro-acción ejecutada',

    -- Snapshots de entrada/salida del componente (JSON — auditoría técnica)
    step_input          JSON            NULL
                            COMMENT 'Datos exactos entregados al componente en este paso',
    step_output         JSON            NULL
                            COMMENT 'Respuesta devuelta por el componente tras ejecutar el paso',

    -- Estado completo del sistema tras completar el paso (ISU snapshot)
    information_state   JSON            NULL
                            COMMENT 'Snapshot consolidado del information_state (SYSTEM_SPEC.md §2)',

    -- Marca temporal precisa (UTC) — inmutable por diseño
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                            COMMENT 'Marca de tiempo UTC precisa para auditoría temporal (EU AI Act Art. 12)',

    -- Claves e índices
    PRIMARY KEY (id),
    KEY idx_trazas_session_id    (session_id),
    KEY idx_trazas_session_turn  (session_id, turn_id),
    KEY idx_trazas_action_type   (action_type),
    KEY idx_trazas_created_at    (created_at)

) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  COMMENT='Ledger inmutable de auditoría AI Act — Micro-acciones del pipeline neurosimbólico';


-- =============================================================================
-- INSERT: 4 Perfiles Mock de Clientes
--
-- Diseñados para cubrir los 4 escenarios de decisión del motor Drools:
--
--   CLI-001 (Laura Martínez Gil)     → Aprobación estándar (sin incidencias en BdE)
--   CLI-002 (María Blanco Torres)    → R_ALERTA_QUIEBRA_AVAL (empresa en concurso)
--   CLI-003 (Carlos Ruiz Fernández)  → R_MOROSIDAD_ASNEF (impagos activos en BdE)
--   CLI-004 (Pedro Sánchez Moreno)   → R_EDAD_MAXIMA (supera 75 años al vencimiento)
--
-- Los DNIs coinciden exactamente con las entradas del archivo `bde.json` (Fase 2).
-- =============================================================================

INSERT INTO clientes (
    cliente_id,
    dni,
    edad,
    ingresos_netos_mensuales,
    antiguedad_meses,
    deuda_interna_banco_mensual,
    es_avalista,
    empresa_avalada_cif
) VALUES

-- ─────────────────────────────────────────────────────────────────────────────
-- CLI-001: Laura Martínez Gil
-- Escenario: APROBACIÓN ESTÁNDAR
--
-- Perfil: Cliente solvente sin incidencias. Al consultar BdE (bde.json),
-- su DNI 55443322E devuelve tiene_impagos_activos=false, sin deuda CIRBE.
-- Con ingresos altos y deuda interna nula, la evaluación Drools debería
-- alcanzar R_APROBACION_ESTANDAR para solicitudes razonables.
-- ─────────────────────────────────────────────────────────────────────────────
(
    'CLI-001',
    '55443322E',
    35,
    3200.00,
    48,
    0.00,
    FALSE,
    NULL
),

-- ─────────────────────────────────────────────────────────────────────────────
-- CLI-002: María Blanco Torres
-- Escenario: R_ALERTA_QUIEBRA_AVAL (Salience 50)
--
-- Perfil: Avalista activa de la empresa con CIF B9999999. Al consultar BdE
-- (bde.json, DNI 11223344C), devuelve empresa_avalada_concurso=TRUE.
-- Drools dispara R_ALERTA_QUIEBRA_AVAL → DENEGADO por riesgo concursal
-- indirecto (Criterios EBA).
-- Ingresos medios; la deuda la asume el riesgo del aval, no financiero propio.
-- ─────────────────────────────────────────────────────────────────────────────
(
    'CLI-002',
    '11223344C',
    29,
    2100.00,
    24,
    0.00,
    TRUE,
    'B9999999'
),

-- ─────────────────────────────────────────────────────────────────────────────
-- CLI-003: Carlos Ruiz Fernández
-- Escenario: R_MOROSIDAD_ASNEF (Salience 60)
--
-- Perfil: Cliente con morosidad activa registrada en ASNEF/CIRBE.
-- Al consultar BdE (bde.json, DNI 87654321B), devuelve:
--   tiene_impagos_activos=TRUE, importe_morosidad_asnef=2300.50€
-- Drools dispara R_MOROSIDAD_ASNEF → DENEGADO por criterios prudenciales.
-- Ingresos bajos pero suficientes para detectar la regla de morosidad
-- antes de que el ratio de endeudamiento sea relevante.
-- ─────────────────────────────────────────────────────────────────────────────
(
    'CLI-003',
    '87654321B',
    45,
    1100.00,
    12,
    120.00,
    FALSE,
    NULL
),

-- ─────────────────────────────────────────────────────────────────────────────
-- CLI-004: Pedro Sánchez Moreno
-- Escenario: R_EDAD_MAXIMA (Salience 98)
--
-- Perfil: Cliente mayor. Con 74 años, cualquier préstamo con plazo >= 13 meses
-- haría que la edad al vencimiento (74 + plazo/12) supere los 75 años,
-- disparando R_EDAD_MAXIMA → DENEGADO independientemente del estado BdE.
-- DNI 99887766D en bde.json tiene deuda_cirbe_mensual=850€ (relevante si
-- la regla de edad no bloqueara antes). Ingresos medios.
-- ─────────────────────────────────────────────────────────────────────────────
(
    'CLI-004',
    '99887766D',
    74,
    1800.00,
    96,
    200.00,
    FALSE,
    NULL
);


-- =============================================================================
-- VERIFICACIÓN POST-INSERT
-- Consulta de confirmación (visible en logs de inicialización de MariaDB)
-- =============================================================================

SELECT
    cliente_id,
    dni,
    edad,
    FORMAT(ingresos_netos_mensuales, 2) AS ingresos_eur,
    antiguedad_meses,
    FORMAT(deuda_interna_banco_mensual, 2) AS deuda_interna_eur,
    IF(es_avalista, 'SÍ', 'NO') AS es_avalista,
    IFNULL(empresa_avalada_cif, '—') AS empresa_avalada_cif
FROM clientes
ORDER BY cliente_id;

-- =============================================================================
-- FIN DEL SCRIPT
-- Tablas creadas: clientes, trazas_auditoria
-- Registros insertados: 4 perfiles mock (CLI-001 a CLI-004)
-- Base de datos: banca_db
-- =============================================================================
