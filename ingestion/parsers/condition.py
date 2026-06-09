import json
import logging
from ingestion.utils import extract_ref_id, get_primary_coding

logger = logging.getLogger(__name__)


def parse(resource: dict) -> dict:
    system, code, display = get_primary_coding(resource.get("code", {}))
    clinical_status_concept = resource.get("clinicalStatus", {})
    _, clinical_status, _ = get_primary_coding(clinical_status_concept)

    return {
        "resource_id": resource.get("id"),
        "patient_id": extract_ref_id(resource.get("subject", {}).get("reference")),
        "code_system": system,
        "code_value": code,
        "code_display": display,
        "clinical_status": clinical_status,
        "onset_datetime": resource.get("onsetDateTime"),
        "abatement_datetime": resource.get("abatementDateTime"),
    }


def insert(resource: dict, source_file: str, cur) -> None:
    try:
        row = parse(resource)
        row["source_file"] = source_file
        row["raw_json"] = json.dumps(resource)
        cur.execute(
            """
            INSERT INTO raw_fhir.condition (
                resource_id, patient_id, code_system, code_value, code_display,
                clinical_status, onset_datetime, abatement_datetime,
                source_file, raw_json
            ) VALUES (
                %(resource_id)s, %(patient_id)s, %(code_system)s, %(code_value)s,
                %(code_display)s, %(clinical_status)s, %(onset_datetime)s,
                %(abatement_datetime)s, %(source_file)s, %(raw_json)s
            )
            """,
            row,
        )
    except Exception as exc:
        logger.error("condition insert failed [file=%s id=%s]: %s", source_file, resource.get("id"), exc)
        raise
