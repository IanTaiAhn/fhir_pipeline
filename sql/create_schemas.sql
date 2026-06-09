-- Raw FHIR staging schema
CREATE SCHEMA IF NOT EXISTS raw_fhir;
CREATE SCHEMA IF NOT EXISTS mart;

-- ─────────────────────────────────────────────────────────────
-- raw_fhir.patient
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_fhir.patient (
    resource_id         TEXT NOT NULL,
    family_name         TEXT,
    given_name          TEXT,
    birth_date          DATE,
    gender              TEXT,
    marital_status_code TEXT,
    city                TEXT,
    state               TEXT,
    postal_code         TEXT,
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);

-- ─────────────────────────────────────────────────────────────
-- raw_fhir.condition
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_fhir.condition (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    code_system         TEXT,
    code_value          TEXT,
    code_display        TEXT,
    clinical_status     TEXT,
    onset_datetime      TIMESTAMPTZ,
    abatement_datetime  TIMESTAMPTZ,
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);

-- ─────────────────────────────────────────────────────────────
-- raw_fhir.observation
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_fhir.observation (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT,
    code_system         TEXT,
    code_value          TEXT,
    code_display        TEXT,
    effective_datetime  TIMESTAMPTZ,
    value_quantity      NUMERIC,
    value_unit          TEXT,
    value_code          TEXT,
    status              TEXT,
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);

-- ─────────────────────────────────────────────────────────────
-- raw_fhir.medication_request
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_fhir.medication_request (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT,
    med_code_system     TEXT,
    med_code_value      TEXT,
    med_display         TEXT,
    authored_on         TIMESTAMPTZ,
    status              TEXT,
    intent              TEXT,
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);

-- ─────────────────────────────────────────────────────────────
-- raw_fhir.claim
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_fhir.claim (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT,
    use                 TEXT,
    billable_start      DATE,
    billable_end        DATE,
    total_value         NUMERIC,
    total_currency      TEXT,
    provider_ref        TEXT,
    status              TEXT,
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);

-- ─────────────────────────────────────────────────────────────
-- raw_fhir.encounter
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS raw_fhir.encounter (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    class_code          TEXT,
    type_code           TEXT,
    type_display        TEXT,
    period_start        TIMESTAMPTZ,
    period_end          TIMESTAMPTZ,
    reason_code         TEXT,
    reason_display      TEXT,
    status              TEXT,
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);
