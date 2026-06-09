from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class Patient(BaseModel):
    patient_id: str
    full_name: Optional[str] = None
    birth_date: Optional[date] = None
    age_years: Optional[int] = None
    gender: Optional[str] = None
    marital_status_code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None

    model_config = {"from_attributes": True}


class Condition(BaseModel):
    condition_id: str
    patient_id: str
    code_system: Optional[str] = None
    code_value: Optional[str] = None
    code_display: Optional[str] = None
    clinical_status: Optional[str] = None
    is_active: Optional[bool] = None
    onset_datetime: Optional[datetime] = None
    abatement_datetime: Optional[datetime] = None

    model_config = {"from_attributes": True}


class Encounter(BaseModel):
    encounter_id: str
    patient_id: str
    patient_name: Optional[str] = None
    encounter_class: Optional[str] = None
    encounter_type: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    duration_hours: Optional[float] = None
    reason_display: Optional[str] = None
    status: Optional[str] = None

    model_config = {"from_attributes": True}


class Observation(BaseModel):
    observation_id: str
    patient_id: str
    patient_name: Optional[str] = None
    encounter_id: Optional[str] = None
    code_system: Optional[str] = None
    code_value: Optional[str] = None
    code_display: Optional[str] = None
    effective_datetime: Optional[datetime] = None
    value_quantity: Optional[float] = None
    value_unit: Optional[str] = None
    value_code: Optional[str] = None
    status: Optional[str] = None

    model_config = {"from_attributes": True}
