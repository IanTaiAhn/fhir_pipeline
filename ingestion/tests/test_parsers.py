"""Unit tests for FHIR resource parsers.

Tests run against in-memory dicts — no DB required.
"""
import pytest
from ingestion.parsers import patient, condition, observation, medication_request, claim, encounter
from ingestion.utils import extract_ref_id, get_primary_coding


# ─── fixtures ────────────────────────────────────────────────────────────────

PATIENT_RESOURCE = {
    "resourceType": "Patient",
    "id": "pat-001",
    "name": [{"family": "Smith", "given": ["John", "A"]}],
    "birthDate": "1980-05-15",
    "gender": "male",
    "maritalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-MaritalStatus", "code": "M"}]},
    "address": [{"city": "Boston", "state": "MA", "postalCode": "02101"}],
}

CONDITION_RESOURCE = {
    "resourceType": "Condition",
    "id": "cond-001",
    "subject": {"reference": "Patient/pat-001"},
    "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus type 2"}]},
    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
    "onsetDateTime": "2010-03-01T00:00:00+00:00",
}

OBSERVATION_RESOURCE = {
    "resourceType": "Observation",
    "id": "obs-001",
    "subject": {"reference": "Patient/pat-001"},
    "encounter": {"reference": "Encounter/enc-001"},
    "code": {"coding": [{"system": "http://loinc.org", "code": "2339-0", "display": "Glucose [Mass/volume] in Blood"}]},
    "effectiveDateTime": "2022-06-10T08:00:00+00:00",
    "valueQuantity": {"value": 95.0, "unit": "mg/dL"},
    "status": "final",
}

MEDICATION_REQUEST_RESOURCE = {
    "resourceType": "MedicationRequest",
    "id": "med-001",
    "subject": {"reference": "Patient/pat-001"},
    "encounter": {"reference": "Encounter/enc-001"},
    "medicationCodeableConcept": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "860975", "display": "Metformin 500 MG"}]},
    "authoredOn": "2022-06-10",
    "status": "active",
    "intent": "order",
}

CLAIM_RESOURCE = {
    "resourceType": "Claim",
    "id": "claim-001",
    "patient": {"reference": "Patient/pat-001"},
    "use": "claim",
    "billablePeriod": {"start": "2022-06-10", "end": "2022-06-10"},
    "total": {"value": 250.00, "currency": "USD"},
    "provider": {"reference": "Organization/org-001"},
    "status": "active",
}

ENCOUNTER_RESOURCE = {
    "resourceType": "Encounter",
    "id": "enc-001",
    "subject": {"reference": "Patient/pat-001"},
    "class": {"code": "AMB"},
    "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "11429006", "display": "Consultation"}]}],
    "period": {"start": "2022-06-10T08:00:00+00:00", "end": "2022-06-10T09:00:00+00:00"},
    "reasonCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "44054006", "display": "Diabetes mellitus type 2"}]}],
    "status": "finished",
}


# ─── utils ───────────────────────────────────────────────────────────────────

def test_extract_ref_id_with_prefix():
    assert extract_ref_id("Patient/abc-123") == "abc-123"


def test_extract_ref_id_no_prefix():
    assert extract_ref_id("abc-123") == "abc-123"


def test_extract_ref_id_none():
    assert extract_ref_id(None) is None


def test_get_primary_coding_empty():
    assert get_primary_coding({}) == (None, None, None)


def test_get_primary_coding():
    concept = {"coding": [{"system": "http://snomed.info/sct", "code": "123", "display": "Test"}]}
    assert get_primary_coding(concept) == ("http://snomed.info/sct", "123", "Test")


# ─── patient ─────────────────────────────────────────────────────────────────

def test_patient_parse_basic():
    row = patient.parse(PATIENT_RESOURCE)
    assert row["resource_id"] == "pat-001"
    assert row["family_name"] == "Smith"
    assert row["given_name"] == "John A"
    assert row["birth_date"] == "1980-05-15"
    assert row["gender"] == "male"
    assert row["marital_status_code"] == "M"
    assert row["city"] == "Boston"
    assert row["state"] == "MA"
    assert row["postal_code"] == "02101"


def test_patient_parse_missing_optional_fields():
    minimal = {"resourceType": "Patient", "id": "pat-min"}
    row = patient.parse(minimal)
    assert row["resource_id"] == "pat-min"
    assert row["family_name"] is None
    assert row["given_name"] is None


# ─── condition ───────────────────────────────────────────────────────────────

def test_condition_parse():
    row = condition.parse(CONDITION_RESOURCE)
    assert row["resource_id"] == "cond-001"
    assert row["patient_id"] == "pat-001"
    assert row["code_system"] == "http://snomed.info/sct"
    assert row["code_value"] == "44054006"
    assert row["code_display"] == "Diabetes mellitus type 2"
    assert row["clinical_status"] == "active"
    assert row["onset_datetime"] == "2010-03-01T00:00:00+00:00"
    assert row["abatement_datetime"] is None


# ─── observation ─────────────────────────────────────────────────────────────

def test_observation_parse():
    row = observation.parse(OBSERVATION_RESOURCE)
    assert row["resource_id"] == "obs-001"
    assert row["patient_id"] == "pat-001"
    assert row["encounter_id"] == "enc-001"
    assert row["code_value"] == "2339-0"
    assert row["value_quantity"] == 95.0
    assert row["value_unit"] == "mg/dL"
    assert row["status"] == "final"


# ─── medication request ───────────────────────────────────────────────────────

def test_medication_request_parse():
    row = medication_request.parse(MEDICATION_REQUEST_RESOURCE)
    assert row["resource_id"] == "med-001"
    assert row["patient_id"] == "pat-001"
    assert row["encounter_id"] == "enc-001"
    assert row["med_code_value"] == "860975"
    assert row["med_display"] == "Metformin 500 MG"
    assert row["status"] == "active"
    assert row["intent"] == "order"


# ─── claim ───────────────────────────────────────────────────────────────────

def test_claim_parse():
    row = claim.parse(CLAIM_RESOURCE)
    assert row["resource_id"] == "claim-001"
    assert row["patient_id"] == "pat-001"
    assert row["use"] == "claim"
    assert row["billable_start"] == "2022-06-10"
    assert row["total_value"] == 250.00
    assert row["total_currency"] == "USD"
    assert row["status"] == "active"


# ─── encounter ───────────────────────────────────────────────────────────────

def test_encounter_parse():
    row = encounter.parse(ENCOUNTER_RESOURCE)
    assert row["resource_id"] == "enc-001"
    assert row["patient_id"] == "pat-001"
    assert row["class_code"] == "AMB"
    assert row["type_display"] == "Consultation"
    assert row["period_start"] == "2022-06-10T08:00:00+00:00"
    assert row["status"] == "finished"
