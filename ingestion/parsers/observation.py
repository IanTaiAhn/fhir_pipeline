import json
import logging
from ingestion.utils import extract_ref_id, get_primary_coding

logger = logging.getLogger(__name__)


def parse(resource: dict) -> dict:
    system, code, display = get_primary_coding(resource.get("code", {}))

    value_quantity = resource.get("valueQuantity", {})
    value_codeable = resource.get("valueCodeableConcept", {})
    _, value_code, _ = get_primary_coding(value_codeable)

    return {
        "resource_id": resource.get("id"),
        "patient_id": extract_ref_id(resource.get("subject", {}).get("reference")),
        "encounter_id": extract_ref_id(resource.get("encounter", {}).get("reference")),
        "code_system": system,
        "code_value": code,
        "code_display": display,
        "effective_datetime": resource.get("effectiveDateTime"),
        "value_quantity": value_quantity.get("value"),
        "value_unit": value_quantity.get("unit"),
        "value_code": value_code,
        "status": resource.get("status"),
    }


def insert(resource: dict, source_file: str, cur) -> None:
    try:
        row = parse(resource)
        row["source_file"] = source_file
        row["raw_json"] = json.dumps(resource)
        cur.execute(
            """
            INSERT INTO raw_fhir.observation (
                resource_id, patient_id, encounter_id, code_system, code_value,
                code_display, effective_datetime, value_quantity, value_unit,
                value_code, status, source_file, raw_json
            ) VALUES (
                %(resource_id)s, %(patient_id)s, %(encounter_id)s, %(code_system)s,
                %(code_value)s, %(code_display)s, %(effective_datetime)s,
                %(value_quantity)s, %(value_unit)s, %(value_code)s, %(status)s,
                %(source_file)s, %(raw_json)s
            )
            """,
            row,
        )
    except Exception as exc:
        logger.error("observation insert failed [file=%s id=%s]: %s", source_file, resource.get("id"), exc)
        raise
