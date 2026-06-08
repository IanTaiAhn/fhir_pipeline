# FHIR R4 Ingestion & Clinical Data Pipeline — Design Document

> **Status:** Draft — Pre-Implementation  
> **Stack:** Python · Synthea · PostgreSQL/Snowflake · dbt · FastAPI · Docker  
> **Audience:** Solo implementer; reference this doc while coding each phase.

---

## Table of Contents

1. [Project Goals & Non-Goals](#1-project-goals--non-goals)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository Layout](#3-repository-layout)
4. [Phase 1 — Synthetic Data Generation (Synthea)](#4-phase-1--synthetic-data-generation-synthea)
5. [Phase 2 — FHIR Ingestion Layer (Python)](#5-phase-2--fhir-ingestion-layer-python)
6. [Phase 3 — Raw Storage Schema (PostgreSQL / Snowflake)](#6-phase-3--raw-storage-schema-postgresql--snowflake)
7. [Phase 4 — dbt Transformation Layer](#7-phase-4--dbt-transformation-layer)
8. [Phase 5 — FastAPI Query Layer](#8-phase-5--fastapi-query-layer)
9. [Docker & Local Dev Setup](#9-docker--local-dev-setup)
10. [Testing Strategy](#10-testing-strategy)
11. [Open Questions & Decision Log](#11-open-questions--decision-log)

---

## 1. Project Goals & Non-Goals

### Goals
- Generate a realistic synthetic patient population using Synthea (FHIR R4 output).
- Ingest and parse six FHIR resource types: `Patient`, `Condition`, `Observation`, `MedicationRequest`, `Claim`, `Encounter`.
- Land raw FHIR JSON in a staging layer with full lineage (bundle source file, ingest timestamp, resource version).
- Build a clean, analytics-ready mart layer via dbt with documented models and column-level tests.
- Expose a FastAPI service so queries can be run against the mart layer without direct DB access.
- Keep the whole stack runnable locally with Docker Compose.

### Non-Goals (for v1)
- Real patient data or PHI of any kind.
- Authentication / authorization on the API (stub only; noted as a future concern).
- FHIR server (HAPI, Azure, etc.) — we are ingesting bundles directly, not implementing a FHIR endpoint.
- Streaming / real-time ingestion — batch only.

---

## 2. Architecture Overview

```
┌─────────────┐     FHIR R4       ┌──────────────────┐
│   Synthea   │ ───bundles (JSON)─▶│  Ingestion Layer │
│  (Java CLI) │                   │  (Python scripts) │
└─────────────┘                   └────────┬─────────┘
                                           │ normalized rows
                                           ▼
                                  ┌─────────────────┐
                                  │  raw_fhir schema │  ← append-only staging
                                  │  (PG / Snowflake)│
                                  └────────┬────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │   dbt project    │
                                  │  staging → mart  │
                                  └────────┬────────┘
                                           │
                                           ▼
                                  ┌─────────────────┐
                                  │    FastAPI       │
                                  │  (query layer)   │
                                  └─────────────────┘
```

**Data flow summary:**
1. Synthea generates one or more FHIR R4 `Bundle` JSON files per patient.
2. Python ingestion script reads each bundle, extracts resources by type, and inserts rows into `raw_fhir.*` tables.
3. dbt reads `raw_fhir.*`, applies staging models (type casting, deduplication, null handling), then builds mart models (dimensional and fact tables).
4. FastAPI reads from the mart schema and exposes REST endpoints.

---

## 3. Repository Layout

```
fhir-pipeline/
│
├── data/
│   └── synthea_output/          # .gitignored; populated by Synthea
│
├── ingestion/
│   ├── __init__.py
│   ├── config.py                # DB connection, env vars
│   ├── loader.py                # Entry point: walk synthea_output/, call parsers
│   ├── parsers/
│   │   ├── patient.py
│   │   ├── condition.py
│   │   ├── observation.py
│   │   ├── medication_request.py
│   │   ├── claim.py
│   │   └── encounter.py
│   └── tests/
│       └── test_parsers.py
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_patients.sql
│   │   │   ├── stg_conditions.sql
│   │   │   ├── stg_observations.sql
│   │   │   ├── stg_medication_requests.sql
│   │   │   ├── stg_claims.sql
│   │   │   └── stg_encounters.sql
│   │   └── mart/
│   │       ├── dim_patients.sql
│   │       ├── dim_conditions.sql
│   │       ├── fct_encounters.sql
│   │       ├── fct_observations.sql
│   │       └── fct_claims.sql
│   ├── tests/
│   └── macros/
│
├── api/
│   ├── main.py
│   ├── routers/
│   │   ├── patients.py
│   │   ├── conditions.py
│   │   └── encounters.py
│   ├── schemas.py               # Pydantic response models
│   └── db.py                    # SQLAlchemy session / connection
│
├── docker-compose.yml
├── Dockerfile.ingestion
├── Dockerfile.api
├── requirements.txt
└── README.md
```

---

## 4. Phase 1 — Synthetic Data Generation (Synthea)

### What Synthea produces
Synthea outputs one `Bundle` JSON file per patient. Each bundle is a FHIR R4 `transaction` or `collection` bundle containing multiple resource entries. A typical patient bundle includes: Patient, Encounter(s), Condition(s), Observation(s), MedicationRequest(s), Claim(s), and more.

### Running Synthea

```bash
# Download
wget https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar

# Generate 500 patients in Massachusetts
java -jar synthea-with-dependencies.jar \
  -p 500 \
  --exporter.fhir.export true \
  --exporter.baseDirectory ./data/synthea_output \
  Massachusetts
```

**Key flags to know:**
| Flag | Purpose |
|------|---------|
| `-p N` | Number of patients to generate |
| `--exporter.fhir.export true` | Enable FHIR R4 output |
| `--exporter.fhir.bulk_data false` | One file per patient (default) |
| `--exporter.baseDirectory` | Output path |

### Output structure
```
synthea_output/
└── fhir/
    ├── Abe123_Patient.json
    ├── Beth456_Patient.json
    └── ...
```

Each JSON file is a FHIR R4 `Bundle`. The ingestion layer iterates these files.

---

## 5. Phase 2 — FHIR Ingestion Layer (Python)

### Design principles
- **Idempotent:** Re-running ingestion on the same file should not create duplicate rows. Use `(source_file, resource_id)` as a natural dedup key.
- **Append-only raw layer:** Never update or delete from `raw_fhir.*`. New runs insert new rows with a new `ingested_at` timestamp. Deduplication happens in dbt.
- **Fail loud:** If a resource is malformed, log the error with file name + resource ID and continue. Do not silently drop data.

### loader.py — main entry point

```python
# Pseudocode outline
def load_all_bundles(synthea_dir: str):
    for filepath in glob(f"{synthea_dir}/fhir/*.json"):
        bundle = json.load(filepath)
        for entry in bundle["entry"]:
            resource = entry["resource"]
            resource_type = resource["resourceType"]
            parser = PARSER_REGISTRY.get(resource_type)
            if parser:
                parser.insert(resource, source_file=filepath)
```

### Parser interface

Each parser module exposes a single `insert(resource: dict, source_file: str, conn)` function. It extracts relevant fields and does an upsert/insert into the corresponding `raw_fhir` table.

### Resource-to-table mapping

| FHIR Resource | Raw Table | Key Fields to Extract |
|---|---|---|
| Patient | `raw_fhir.patient` | id, name, birthDate, gender, address, maritalStatus |
| Condition | `raw_fhir.condition` | id, subject (patient ref), code (SNOMED), onsetDateTime, clinicalStatus |
| Observation | `raw_fhir.observation` | id, subject, code (LOINC), effectiveDateTime, valueQuantity, valueCodeableConcept |
| MedicationRequest | `raw_fhir.medication_request` | id, subject, medicationCodeableConcept (RxNorm), authoredOn, status |
| Claim | `raw_fhir.claim` | id, patient, use, billablePeriod, total.value, provider |
| Encounter | `raw_fhir.encounter` | id, subject, class, type, period.start, period.end, reasonCode |

### Reference resolution
FHIR references are relative (e.g., `"reference": "Patient/abc-123"`). Strip the resource type prefix when storing: store `abc-123` as the foreign key, not `Patient/abc-123`.

```python
def extract_ref_id(reference_str: str) -> str:
    """'Patient/abc-123' → 'abc-123'"""
    return reference_str.split("/")[-1] if "/" in reference_str else reference_str
```

### Coding systems to be aware of
| System | Used in |
|---|---|
| SNOMED CT | Condition.code |
| LOINC | Observation.code |
| RxNorm | MedicationRequest.medicationCodeableConcept |
| ICD-10-CM | Claim diagnosis codes |
| CPT / HCPCS | Claim procedure codes |

Store **both** the `system` URI and `code` value. Don't normalize to a single coding system in the raw layer.

---

## 6. Phase 3 — Raw Storage Schema (PostgreSQL / Snowflake)

### Schema: `raw_fhir`
All tables in this schema are append-only landing tables. They store semi-structured or lightly parsed data and include pipeline metadata columns.

### Common metadata columns (on every raw table)
```sql
source_file      TEXT NOT NULL,       -- original Synthea filename
ingested_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
bundle_id        TEXT,                -- FHIR Bundle.id if present
raw_json         JSONB / VARIANT      -- full resource JSON for recovery
```

### Table: `raw_fhir.patient`
```sql
CREATE TABLE raw_fhir.patient (
    resource_id         TEXT NOT NULL,
    family_name         TEXT,
    given_name          TEXT,
    birth_date          DATE,
    gender              TEXT,
    marital_status_code TEXT,
    city                TEXT,
    state               TEXT,
    postal_code         TEXT,
    -- metadata
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);
```

### Table: `raw_fhir.condition`
```sql
CREATE TABLE raw_fhir.condition (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,   -- extracted ref
    code_system         TEXT,
    code_value          TEXT,
    code_display        TEXT,
    clinical_status     TEXT,
    onset_datetime      TIMESTAMPTZ,
    abatement_datetime  TIMESTAMPTZ,
    -- metadata
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);
```

### Table: `raw_fhir.observation`
```sql
CREATE TABLE raw_fhir.observation (
    resource_id             TEXT NOT NULL,
    patient_id              TEXT NOT NULL,
    encounter_id            TEXT,
    code_system             TEXT,
    code_value              TEXT,             -- LOINC code
    code_display            TEXT,
    effective_datetime      TIMESTAMPTZ,
    value_quantity          NUMERIC,
    value_unit              TEXT,
    value_code              TEXT,             -- for coded results
    status                  TEXT,
    -- metadata
    source_file             TEXT NOT NULL,
    ingested_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json                JSONB
);
```

### Table: `raw_fhir.medication_request`
```sql
CREATE TABLE raw_fhir.medication_request (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT,
    med_code_system     TEXT,
    med_code_value      TEXT,             -- RxNorm code
    med_display         TEXT,
    authored_on         TIMESTAMPTZ,
    status              TEXT,
    intent              TEXT,
    -- metadata
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);
```

### Table: `raw_fhir.claim`
```sql
CREATE TABLE raw_fhir.claim (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    encounter_id        TEXT,
    use                 TEXT,             -- 'claim' | 'preauthorization' | 'predetermination'
    billable_start      DATE,
    billable_end        DATE,
    total_value         NUMERIC,
    total_currency      TEXT,
    provider_ref        TEXT,
    status              TEXT,
    -- metadata
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);
```

### Table: `raw_fhir.encounter`
```sql
CREATE TABLE raw_fhir.encounter (
    resource_id         TEXT NOT NULL,
    patient_id          TEXT NOT NULL,
    class_code          TEXT,             -- e.g. 'AMB', 'IMP', 'EMER'
    type_code           TEXT,
    type_display        TEXT,
    period_start        TIMESTAMPTZ,
    period_end          TIMESTAMPTZ,
    reason_code         TEXT,
    reason_display      TEXT,
    status              TEXT,
    -- metadata
    source_file         TEXT NOT NULL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json            JSONB
);
```

> **Snowflake note:** Replace `JSONB` with `VARIANT`. Replace `TIMESTAMPTZ` with `TIMESTAMP_TZ`. Replace `NUMERIC` with `NUMBER`.

---

## 7. Phase 4 — dbt Transformation Layer

### Model layers

```
raw_fhir.*  →  staging (stg_*)  →  mart (dim_* / fct_*)
```

- **staging:** 1:1 with raw tables. Apply type casts, null coalescing, deduplication (pick latest `ingested_at` per `resource_id`), rename columns to snake_case conventions, and add surrogate keys.
- **mart:** dimensional models for patients and conditions; fact tables for encounters, observations, and claims. Apply business logic here (e.g., flag active vs. resolved conditions, compute encounter duration).

### Staging model pattern

```sql
-- models/staging/stg_patients.sql
with source as (
    select * from {{ source('raw_fhir', 'patient') }}
),
deduped as (
    select *,
        row_number() over (
            partition by resource_id
            order by ingested_at desc
        ) as row_num
    from source
),
final as (
    select
        resource_id                         as patient_id,
        trim(given_name || ' ' || family_name) as full_name,
        birth_date,
        lower(gender)                       as gender,
        marital_status_code,
        city,
        upper(state)                        as state,
        postal_code,
        ingested_at
    from deduped
    where row_num = 1
)
select * from final
```

### Mart model: `dim_patients`

```sql
-- models/mart/dim_patients.sql
select
    patient_id,
    full_name,
    birth_date,
    date_part('year', age(current_date, birth_date))  as age_years,
    gender,
    marital_status_code,
    city,
    state,
    postal_code
from {{ ref('stg_patients') }}
```

### Mart model: `fct_encounters`

```sql
-- models/mart/fct_encounters.sql
select
    e.resource_id                           as encounter_id,
    e.patient_id,
    p.full_name                             as patient_name,
    e.class_code                            as encounter_class,
    e.type_display                          as encounter_type,
    e.period_start,
    e.period_end,
    extract(epoch from (e.period_end - e.period_start)) / 3600
                                            as duration_hours,
    e.reason_display,
    e.status
from {{ ref('stg_encounters') }} e
left join {{ ref('stg_patients') }} p
    on e.patient_id = p.patient_id
```

### dbt tests to implement

```yaml
# schema.yml excerpt
models:
  - name: stg_patients
    columns:
      - name: patient_id
        tests: [unique, not_null]
      - name: gender
        tests:
          - accepted_values:
              values: ['male', 'female', 'other', 'unknown']

  - name: fct_encounters
    columns:
      - name: encounter_id
        tests: [unique, not_null]
      - name: patient_id
        tests:
          - not_null
          - relationships:
              to: ref('stg_patients')
              field: patient_id
```

### dbt macros to write
- `generate_surrogate_key(fields)` — if not using `dbt_utils`
- `extract_coding(json_col, system_uri)` — useful for Snowflake VARIANT columns

---

## 8. Phase 5 — FastAPI Query Layer

### Design principles
- Read-only; all writes happen through the ingestion layer, not the API.
- Query the **mart** schema only, never raw.
- Pydantic response models for every endpoint — no raw DB row dicts leaking to clients.
- Use async SQLAlchemy or psycopg3 for async support.

### Endpoints (v1)

| Method | Path | Description |
|---|---|---|
| GET | `/patients` | List patients with pagination |
| GET | `/patients/{patient_id}` | Get single patient record |
| GET | `/patients/{patient_id}/conditions` | All conditions for a patient |
| GET | `/patients/{patient_id}/encounters` | All encounters for a patient |
| GET | `/patients/{patient_id}/observations` | Lab/vital observations |
| GET | `/encounters` | List encounters with filters (date range, class) |
| GET | `/conditions` | List conditions with filters (SNOMED code, status) |
| GET | `/health` | Health check |

### Example router: `routers/patients.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.db import get_db
from api import schemas

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/{patient_id}", response_model=schemas.Patient)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        "SELECT * FROM mart.dim_patients WHERE patient_id = :pid",
        {"pid": patient_id}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return schemas.Patient(**row._mapping)
```

### Pydantic schemas (`schemas.py`)

```python
from pydantic import BaseModel
from datetime import date
from typing import Optional

class Patient(BaseModel):
    patient_id: str
    full_name: Optional[str]
    birth_date: Optional[date]
    age_years: Optional[int]
    gender: Optional[str]
    state: Optional[str]

    class Config:
        from_attributes = True

class Encounter(BaseModel):
    encounter_id: str
    patient_id: str
    encounter_class: Optional[str]
    encounter_type: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    duration_hours: Optional[float]
    reason_display: Optional[str]
    status: Optional[str]
```

### Pagination pattern

Use `limit` / `offset` for all list endpoints. Default `limit=50`, max `limit=200`.

```python
@router.get("/", response_model=list[schemas.Patient])
async def list_patients(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    ...
```

---

## 9. Docker & Local Dev Setup

### `docker-compose.yml` services

```yaml
services:

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: fhir
      POSTGRES_PASSWORD: fhir
      POSTGRES_DB: fhir_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  ingestion:
    build:
      context: .
      dockerfile: Dockerfile.ingestion
    depends_on: [postgres]
    environment:
      DATABASE_URL: postgresql://fhir:fhir@postgres:5432/fhir_db
    volumes:
      - ./data/synthea_output:/app/data/synthea_output

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    depends_on: [postgres]
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://fhir:fhir@postgres:5432/fhir_db

volumes:
  pgdata:
```

### Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Full SQLAlchemy-compatible connection string |
| `SYNTHEA_OUTPUT_DIR` | Path to Synthea output directory |
| `LOG_LEVEL` | `INFO` (default) or `DEBUG` |

### Local dev quickstart (without Docker)

```bash
# 1. Generate data
java -jar synthea.jar -p 100 Massachusetts

# 2. Create DB schema
psql $DATABASE_URL -f sql/create_schemas.sql

# 3. Run ingestion
python -m ingestion.loader

# 4. Run dbt
cd dbt_project && dbt deps && dbt run && dbt test

# 5. Start API
uvicorn api.main:app --reload --port 8000
```

---

## 10. Testing Strategy

### Unit tests (ingestion parsers)
- One test file per parser in `ingestion/tests/`.
- Fixture: load a real sample Synthea bundle JSON and assert extracted field values.
- Test edge cases: missing optional fields, multiple codings per concept, null references.

### dbt tests
- `unique` and `not_null` on all primary key columns.
- `relationships` tests to enforce FK integrity between staging models.
- `accepted_values` for coded fields (gender, encounter class, condition status).
- Custom test: assert no patient has age < 0 or > 130.

### API tests
- Use FastAPI's `TestClient` with a test database or fixture data.
- Test each endpoint for 200, 404, and invalid param cases.
- Assert response shapes match Pydantic schemas exactly.

### Integration test
- Full pipeline smoke test: generate 10 patients → ingest → dbt run → hit API → assert non-zero results.

---

## 11. Open Questions & Decision Log

| # | Question | Decision | Date |
|---|---|---|---|
| 1 | PostgreSQL vs. Snowflake? | Start with Postgres locally; abstract with SQLAlchemy so Snowflake swap is viable | TBD |
| 2 | How to handle multi-coding arrays on Condition.code? | Store primary coding only in flat columns; preserve full array in `raw_json` | TBD |
| 3 | dbt-core vs. dbt Cloud? | dbt-core locally; can point to dbt Cloud later | TBD |
| 4 | Async vs. sync SQLAlchemy in FastAPI? | Async (asyncpg driver) — better fit for FastAPI's async model | TBD |
| 5 | Include `raw_json` JSONB column on all raw tables? | Yes — recovery mechanism; drop if storage is a concern | TBD |
| 6 | API auth? | Out of scope for v1; add API key middleware in v2 | TBD |
| 7 | Which Synthea population size for demos? | 500 patients — large enough to be interesting, fast to generate | TBD |

---

*Last updated: pre-implementation draft*
