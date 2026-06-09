import json
import logging
from ingestion.utils import extract_ref_id, get_primary_coding

logger = logging.getLogger(__name__)


def parse(resource: dict) -> dict:
    system, code, display = get_primary_coding(resource.get("medicationCodeableConcept", {}))

    return {
        "resource_id": resource.get("id"),
        "patient_id": extract_ref_id(resource.get("subject", {}).get("reference")),
        "encounter_id": extract_ref_id(resource.get("encounter", {}).get("reference")),
        "med_code_system": system,
        "med_code_value": code,
        "med_display": display,
        "authored_on": resource.get("authoredOn"),
        "status": resource.get("status"),
        "intent": resource.get("intent"),
    }


def insert(resource: dict, source_file: str, cur) -> None:
    try:
        row = parse(resource)
        row["source_file"] = source_file
        row["raw_json"] = json.dumps(resource)
        cur.execute(
            """
            INSERT INTO raw_fhir.medication_request (
                resource_id, patient_id, encounter_id, med_code_system, med_code_value,
                med_display, authored_on, status, intent, source_file, raw_json
            ) VALUES (
                %(resource_id)s, %(patient_id)s, %(encounter_id)s, %(med_code_system)s,
                %(med_code_value)s, %(med_display)s, %(authored_on)s, %(status)s,
                %(intent)s, %(source_file)s, %(raw_json)s
            )
            """,
            row,
        )
    except Exception as exc:
        logger.error("medication_request insert failed [file=%s id=%s]: %s", source_file, resource.get("id"), exc)
        raise
