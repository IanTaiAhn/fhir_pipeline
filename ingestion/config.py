import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://fhir:fhir@localhost:5432/fhir_db",
)
SYNTHEA_OUTPUT_DIR = os.environ.get("SYNTHEA_OUTPUT_DIR", "./data/synthea_output")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
