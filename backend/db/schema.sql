-- ============================================================
-- VEDISA CRM - Schema PostgreSQL
-- Ejecutar desde la raiz del repo clonado:
--   psql -U postgres -d vedisa_crm -f backend/db/schema.sql
-- ============================================================

-- PASO 0: Crear la base de datos (ejecutar UNA VEZ aparte si no existe)
-- psql -U postgres -c "CREATE DATABASE vedisa_crm;"

-- Extensión para UUIDs
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABLAS MAESTRAS
-- ============================================================

CREATE TABLE IF NOT EXISTS comerciales (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      VARCHAR(120) NOT NULL,
    email       VARCHAR(200) UNIQUE,
    telefono    VARCHAR(20),
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tecnicos_estudios (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre      VARCHAR(120) NOT NULL,
    email       VARCHAR(200) UNIQUE,
    telefono    VARCHAR(20),
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SOLICITUDES (tabla central del CRM)
-- ============================================================

CREATE TABLE IF NOT EXISTS solicitudes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo              VARCHAR(50) NOT NULL UNIQUE,
    nombre_corto        VARCHAR(200) NOT NULL,
    estudio_direccion   TEXT,
    poblacion           VARCHAR(120),

    -- Estado kanban
    estado              VARCHAR(60) NOT NULL DEFAULT 'Pte. Aprobacion',
    kanban_column       VARCHAR(60) NOT NULL DEFAULT 'Pte. Aprobacion',
    color_estado        VARCHAR(10) NOT NULL DEFAULT '#94a3b8',
    prioridad           VARCHAR(20) NOT NULL DEFAULT 'media'
                        CHECK (prioridad IN ('alta', 'media', 'baja')),

    -- Relaciones
    comercial_id        UUID REFERENCES comerciales(id) ON DELETE SET NULL,
    tecnico_estudios_id UUID REFERENCES tecnicos_estudios(id) ON DELETE SET NULL,

    -- Fechas
    fecha_solicitud     TIMESTAMPTZ,
    fecha_limite        TIMESTAMPTZ,
    fecha_visita        TIMESTAMPTZ,
    fecha_envio         TIMESTAMPTZ,
    fecha_adjudicacion  TIMESTAMPTZ,
    fecha_cierre        TIMESTAMPTZ,

    -- Datos economicos
    oferta              NUMERIC(14, 2),
    presupuesto_coste   NUMERIC(14, 2),
    margen_estimado     NUMERIC(5, 2),

    -- Texto libre
    observaciones       TEXT,

    -- Auditoria
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_solicitudes_estado    ON solicitudes(estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_comercial ON solicitudes(comercial_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_tecnico   ON solicitudes(tecnico_estudios_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_fecha     ON solicitudes(fecha_solicitud DESC);

-- ============================================================
-- CONTACTOS DE UNA SOLICITUD
-- ============================================================

CREATE TABLE IF NOT EXISTS contactos_solicitud (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    solicitud_id    UUID NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    nombre          VARCHAR(120) NOT NULL,
    rol             VARCHAR(80),
    telefono        VARCHAR(20),
    email           VARCHAR(200),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contactos_solicitud ON contactos_solicitud(solicitud_id);

-- ============================================================
-- HISTORIAL / ACTUACIONES
-- ============================================================

CREATE TABLE IF NOT EXISTS actuaciones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    solicitud_id    UUID NOT NULL REFERENCES solicitudes(id) ON DELETE CASCADE,
    tipo            VARCHAR(60) NOT NULL DEFAULT 'nota'
                    CHECK (tipo IN ('nota', 'llamada', 'email', 'visita', 'cambio_estado', 'otro')),
    descripcion     TEXT NOT NULL,
    estado_anterior VARCHAR(60),
    estado_nuevo    VARCHAR(60),
    usuario         VARCHAR(120),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actuaciones_solicitud ON actuaciones(solicitud_id);
CREATE INDEX IF NOT EXISTS idx_actuaciones_fecha     ON actuaciones(created_at DESC);

-- ============================================================
-- TRIGGER: updated_at automatico en solicitudes
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_solicitudes_updated_at ON solicitudes;
CREATE TRIGGER trg_solicitudes_updated_at
    BEFORE UPDATE ON solicitudes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================
-- VISTA: dashboard KPIs  -> GET /crm/dashboard
-- ============================================================

CREATE OR REPLACE VIEW v_dashboard_kpis AS
SELECT
    COUNT(*)                                                        AS total_solicitudes,
    COUNT(*) FILTER (WHERE estado = 'En Estudio')                   AS en_estudio,
    COUNT(*) FILTER (WHERE estado IN ('Enviada','Pte. Cierre'))     AS ofertadas,
    COUNT(*) FILTER (WHERE estado = 'Adjudicada')                   AS ganadas,
    COUNT(*) FILTER (WHERE estado IN ('Rechazado','Descartada'))    AS perdidas,
    COALESCE(
        AVG(EXTRACT(EPOCH FROM (NOW() - fecha_solicitud)) / 86400)
        FILTER (WHERE fecha_solicitud IS NOT NULL),
    0)::NUMERIC(8,1)                                                AS aging_promedio,
    CASE
        WHEN COUNT(*) FILTER (WHERE estado != 'Pte. Aprobacion') = 0 THEN 0
        ELSE ROUND(
            COUNT(*) FILTER (WHERE estado = 'Adjudicada')::NUMERIC /
            NULLIF(COUNT(*) FILTER (WHERE estado != 'Pte. Aprobacion'), 0),
        4)
    END                                                             AS tasa_conversion,
    COALESCE(SUM(oferta) FILTER (WHERE oferta IS NOT NULL), 0)     AS oferta_total
FROM solicitudes;

-- ============================================================
-- VISTA: pipeline por estado  -> GET /crm/pipeline
-- ============================================================

CREATE OR REPLACE VIEW v_pipeline AS
SELECT
    s.estado,
    s.kanban_column,
    s.color_estado,
    COUNT(*)         AS total,
    SUM(s.oferta)    AS oferta_total,
    COALESCE(
        AVG(EXTRACT(EPOCH FROM (NOW() - s.fecha_solicitud)) / 86400)
        FILTER (WHERE s.fecha_solicitud IS NOT NULL),
    0)::INT          AS aging_medio_dias
FROM solicitudes s
GROUP BY s.estado, s.kanban_column, s.color_estado;

-- ============================================================
-- SEED: datos de ejemplo para desarrollo
-- ============================================================

INSERT INTO comerciales (nombre, email) VALUES
    ('Ana Garcia',   'ana.garcia@vedisa.com'),
    ('Pedro Lopez',  'pedro.lopez@vedisa.com')
ON CONFLICT DO NOTHING;

INSERT INTO tecnicos_estudios (nombre, email) VALUES
    ('Carlos Ruiz',   'carlos.ruiz@vedisa.com'),
    ('Marta Sanchez', 'marta.sanchez@vedisa.com')
ON CONFLICT DO NOTHING;

INSERT INTO solicitudes (
    codigo, nombre_corto, poblacion, estado, kanban_column, color_estado,
    prioridad, fecha_solicitud, oferta
) VALUES
    ('SOL-2026-001', 'Instalacion Solar Nave A',    'Mao',       'En Estudio',  'En Estudio',  '#3b82f6', 'alta',  NOW() - INTERVAL '15 days', 48000),
    ('SOL-2026-002', 'Reforma Cubierta Edificio B', 'Ciutadella','Enviada',     'Enviada',     '#8b5cf6', 'media', NOW() - INTERVAL '30 days', 120000),
    ('SOL-2026-003', 'Mantenimiento Anual PV',      'Mahon',     'Adjudicada',  'Adjudicada',  '#10b981', 'baja',  NOW() - INTERVAL '60 days', 22000),
    ('SOL-2026-004', 'Auditoria Energetica',        'Alaior',    'Pte. Cierre', 'Pte. Cierre', '#f97316', 'alta',  NOW() - INTERVAL '10 days', 8500),
    ('SOL-2026-005', 'Instalacion Aerotermia',      'Es Castell','Rechazado',   'Rechazado',   '#ef4444', 'media', NOW() - INTERVAL '45 days', NULL)
ON CONFLICT DO NOTHING;

-- Verificacion final
SELECT 'Tablas creadas OK' AS status;
SELECT * FROM v_dashboard_kpis;
