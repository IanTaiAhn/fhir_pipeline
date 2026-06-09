import json
import logging
from ingestion.utils import extract_ref_id

logger = logging.getLogger(__name__)


def parse(resource: dict) -> dict:
    billable = resource.get("billablePeriod", {})
    total = resource.get("total", {})
    items = resource.get("item", [])
    encounter_ref = None
    if items:
        encounter_ref = extract_ref_id(items[0].get("encounter", [{}])[0].get("reference") if items[0].get("encounter") else None)

    return {
        "resource_id": resource.get("id"),
        "patient_id": extract_ref_id(resource.get("patient", {}).get("reference")),
        "encounter_id": encounter_ref,
        "use": resource.get("use"),
        "billable_start": billable.get("start", "")[:10] or None,
        "billable_end": billable.get("end", "")[:10] or None,
        "total_value": total.get("value"),
        "total_currency": total.get("currency"),
        "provider_ref": extract_ref_id(resource.get("provider", {}).get("reference")),
        "status": resource.get("status"),
    }


def insert(resource: dict, source_file: str, cur) -> None:
    try:
        row = parse(resource)
        row["source_file"] = source_file
        row["raw_json"] = json.dumps(resource)
        cur.execute(
            """
            INSERT INTO raw_fhir.claim (
                resource_id, patient_id, encounter_id, use, billable_start,
                billable_end, total_value, total_currency, provider_ref,
                status, source_file, raw_json
            ) VALUES (
                %(resource_id)s, %(patient_id)s, %(encounter_id)s, %(use)s,
                %(billable_start)s, %(billable_end)s, %(total_value)s,
                %(total_currency)s, %(provider_ref)s, %(status)s,
                %(source_file)s, %(raw_json)s
            )
            """,
            row,
        )
    except Exception as exc:
        logger.error("claim insert failed [file=%s id=%s]: %s", source_file, resource.get("id"), exc)
        raise
