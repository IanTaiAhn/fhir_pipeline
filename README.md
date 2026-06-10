# FHIR Pipeline

An ELT pipeline that ingests synthetic FHIR R4 patient data, transforms it with dbt, and serves it via a REST API.

```
Synthea → raw_fhir (Postgres) → dbt (staging → mart) → FastAPI
```

## Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local dbt runs)
- Java 11+ (for Synthea data generation)

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env if you need non-default credentials
```

### 2. Start Postgres

```bash
docker compose up -d postgres
# Wait for healthy: docker compose ps
```

### 3. Generate synthetic data (Synthea)

```bash
mkdir -p data/synthea_output
# Download synthea if needed:
#   wget https://github.com/synthetichealth/synthea/releases/latest/download/synthea-with-dependencies.jar
java -jar synthea-with-dependencies.jar \
  -p 50 \
  --exporter.fhir.export=true \
  --exporter.baseDirectory=data/synthea_output
```

### 4. Run ingestion

```bash
docker compose run --rm --profile ingestion ingestion
# Or locally:
pip install -r requirements.txt
DATABASE_URL=postgresql://fhir:fhir@localhost:5432/fhir_db \
SYNTHEA_OUTPUT_DIR=data/synthea_output \
python -m ingestion.loader
```

### 5. Run dbt transforms

```bash
cd dbt_project
cp profiles.yml.example profiles.yml   # edit DB credentials if needed
pip install dbt-postgres
dbt run
dbt test
```

### 6. Start the API

```bash
docker compose up api
# Or locally:
DATABASE_URL=postgresql://fhir:fhir@localhost:5432/fhir_db \
uvicorn api.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Project Layout

```
ingestion/          Python parsers + loader (raw_fhir schema)
  parsers/          One module per FHIR resource type
  tests/            Parser unit tests (no DB required)
api/                FastAPI query layer (mart schema only)
  routers/          patients, conditions, encounters
dbt_project/        SQL transformation layer
  models/staging/   Deduplicated views (1:1 with raw tables)
  models/mart/      Analytics-ready dim/fact tables
sql/                DDL — raw_fhir tables + schemas
data/               Synthea output (git-ignored)
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/patients` | List patients (paginated) |
| GET | `/patients/{id}` | Single patient |
| GET | `/patients/{id}/conditions` | Patient's conditions |
| GET | `/patients/{id}/encounters` | Patient's encounters |
| GET | `/patients/{id}/observations` | Patient's observations |
| GET | `/conditions?snomed_code=&status=` | Filter conditions |
| GET | `/encounters?encounter_class=&start_after=&start_before=` | Filter encounters |

## Running Tests

```bash
# Parser unit tests (no DB needed)
pytest ingestion/tests/

# dbt schema tests (requires live DB + dbt run first)
cd dbt_project && dbt test
```

## Architecture Notes

- **Raw layer is append-only** — ingestion never updates or deletes. Deduplication (pick latest `ingested_at` per `resource_id`) happens in dbt staging models.
- **`raw_json` column on every table** — full original FHIR JSON retained for debugging and re-parsing.
- **API reads mart only** — consumers never touch raw tables directly.
- **No auth in v1** — API key / OAuth middleware is a planned v2 addition.

## Default Credentials (local dev only)

| Setting | Value |
|---------|-------|
| Postgres host | `localhost:5432` |
| Database | `fhir_db` |
| User / Password | `fhir` / `fhir` |
