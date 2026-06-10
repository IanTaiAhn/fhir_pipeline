# Verification Steps

Follow these steps to confirm the pipeline is working end to end.

## 1. Start Postgres

```bash
docker compose up -d postgres
docker compose ps   # wait until postgres shows "healthy"
```

## 2. Generate Test Data (Synthea)

Skip this step if you already have data in `data/synthea_output/fhir/`.

```bash
mkdir -p data/synthea_output
java -jar synthea-with-dependencies.jar -p 10 \
  --exporter.fhir.export=true \
  --exporter.baseDirectory=data/synthea_output
```

## 3. Run Ingestion

```bash
docker compose run --rm --profile ingestion ingestion
# Expected: log lines showing bundles processed and resources inserted
```

## 4. Verify Raw Data Landed

```bash
docker compose exec postgres psql -U fhir -d fhir_db \
  -c "SELECT COUNT(*) FROM raw_fhir.patient;"
# Expected: count > 0
```

## 5. Run dbt Transforms and Tests

```bash
cd dbt_project
cp profiles.yml.example profiles.yml   # first time only — edit credentials if needed
dbt run
dbt test
# Expected: all models build and all schema tests pass
```

## 6. Start the API

```bash
docker compose up -d api
curl http://localhost:8000/health
# Expected: {"status":"ok"}

curl http://localhost:8000/patients
# Expected: JSON array of patient records
```

## 7. Run Parser Unit Tests

No database required for this step.

```bash
pip install -r requirements.txt
pytest ingestion/tests/ -v
# Expected: all tests pass
```

---

All 7 steps passing means the full pipeline — ingestion, transformation, and API — is in working order.
