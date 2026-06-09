import json
import logging
from ingestion.utils import extract_ref_id, get_primary_coding

logger = logging.getLogger(__name__)


def parse(resource: dict) -> dict:
    enc_class = resource.get("class", {})
    types = resource.get("type", [])
    type_system, type_code, type_display = get_primary_coding(types[0] if types else {})
    period = resource.get("period", {})
    reasons = resource.get("reasonCode", [])
    _, reason_code, reason_display = get_primary_coding(reasons[0] if reasons else {})

    return {
        "resource_id": resource.get("id"),
        "patient_id": extract_ref_id(resource.get("subject", {}).get("reference")),
        "class_code": enc_class.get("code"),
        "type_code": type_code,
        "type_display": type_display,
        "period_start": period.get("start"),
        "period_end": period.get("end"),
        "reason_code": reason_code,
        "reason_display": reason_display,
        "status": resource.get("status"),
    }


def insert(resource: dict, source_file: str, cur) -> None:
    try:
        row = parse(resource)
        row["source_file"] = source_file
        row["raw_json"] = json.dumps(resource)
        cur.execute(
            """
            INSERT INTO raw_fhir.encounter (
                resource_id, patient_id, class_code, type_code, type_display,
                period_start, period_end, reason_code, reason_display,
                status, source_file, raw_json
            ) VALUES (
                %(resource_id)s, %(patient_id)s, %(class_code)s, %(type_code)s,
                %(type_display)s, %(period_start)s, %(period_end)s,
                %(reason_code)s, %(reason_display)s, %(status)s,
                %(source_file)s, %(raw_json)s
            )
            """,
            row,
        )
    except Exception as exc:
        logger.error("encounter insert failed [file=%s id=%s]: %s", source_file, resource.get("id"), exc)
        raise
