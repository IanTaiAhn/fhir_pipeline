def extract_ref_id(reference_str: str) -> str:
    """'Patient/abc-123' → 'abc-123'"""
    if not reference_str:
        return None
    return reference_str.split("/")[-1] if "/" in reference_str else reference_str


def get_primary_coding(codeable_concept: dict) -> tuple[str, str, str]:
    """Return (system, code, display) from the first coding in a CodeableConcept."""
    if not codeable_concept:
        return None, None, None
    codings = codeable_concept.get("coding", [])
    if not codings:
        return None, None, None
    first = codings[0]
    return first.get("system"), first.get("code"), first.get("display")
