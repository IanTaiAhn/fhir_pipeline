import json
import logging
import sys
from glob import glob

from ingestion.config import SYNTHEA_OUTPUT_DIR, LOG_LEVEL
from ingestion.db import get_cursor
from ingestion.parsers import patient, condition, observation, medication_request, claim, encounter

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

PARSER_REGISTRY = {
    "Patient": patient,
    "Condition": condition,
    "Observation": observation,
    "MedicationRequest": medication_request,
    "Claim": claim,
    "Encounter": encounter,
}


def load_bundle(filepath: str, cur) -> tuple[int, int]:
    """Load a single FHIR bundle file. Returns (inserted, skipped) counts."""
    inserted = 0
    skipped = 0
    with open(filepath) as f:
        bundle = json.load(f)

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")
        parser = PARSER_REGISTRY.get(resource_type)
        if parser is None:
            skipped += 1
            continue
        try:
            parser.insert(resource, source_file=filepath, cur=cur)
            inserted += 1
        except Exception as exc:
            logger.error("Skipping resource [type=%s file=%s]: %s", resource_type, filepath, exc)
            skipped += 1

    return inserted, skipped


def load_all_bundles(synthea_dir: str = SYNTHEA_OUTPUT_DIR) -> None:
    pattern = f"{synthea_dir}/fhir/*.json"
    files = sorted(glob(pattern))
    if not files:
        logger.warning("No bundle files found at %s", pattern)
        return

    total_inserted = 0
    total_skipped = 0
    with get_cursor() as cur:
        for filepath in files:
            logger.info("Processing %s", filepath)
            ins, skip = load_bundle(filepath, cur)
            total_inserted += ins
            total_skipped += skip
            logger.debug("  inserted=%d skipped=%d", ins, skip)

    logger.info("Done. total_inserted=%d total_skipped=%d", total_inserted, total_skipped)


if __name__ == "__main__":
    synthea_dir = sys.argv[1] if len(sys.argv) > 1 else SYNTHEA_OUTPUT_DIR
    load_all_bundles(synthea_dir)
