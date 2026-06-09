import json
import logging
from ingestion.utils import get_primary_coding

logger = logging.getLogger(__name__)


def parse(resource: dict) -> dict:
    name = {}
    names = resource.get("name", [])
    if names:
        name = names[0]

    address = {}
    addresses = resource.get("address", [])
    if addresses:
        address = addresses[0]

    marital = resource.get("maritalStatus", {})
    _, marital_code, _ = get_primary_coding(marital)

    return {
        "resource_id": resource.get("id"),
        "family_name": name.get("family"),
        "given_name": " ".join(name.get("given", [])) or None,
        "birth_date": resource.get("birthDate"),
        "gender": resource.get("gender"),
        "marital_status_code": marital_code,
        "city": address.get("city"),
        "state": address.get("state"),
        "postal_code": address.get("postalCode"),
    }


def insert(resource: dict, source_file: str, cur) -> None:
    try:
        row = parse(resource)
        row["source_file"] = source_file
        row["raw_json"] = json.dumps(resource)
        cur.execute(
            """
            INSERT INTO raw_fhir.patient (
                resource_id, family_name, given_name, birth_date, gender,
                marital_status_code, city, state, postal_code,
                source_file, raw_json
            ) VALUES (
                %(resource_id)s, %(family_name)s, %(given_name)s, %(birth_date)s,
                %(gender)s, %(marital_status_code)s, %(city)s, %(state)s,
                %(postal_code)s, %(source_file)s, %(raw_json)s
            )
            """,
            row,
        )
    except Exception as exc:
        logger.error("patient insert failed [file=%s id=%s]: %s", source_file, resource.get("id"), exc)
        raise
