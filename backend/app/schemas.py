from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---- clinical note (this is also the JSON contract the LLM must return) ----

class Symptom(BaseModel):
    name: str
    duration: Optional[str] = None
    severity: Optional[str] = None
    quote: Optional[str] = None


class Vital(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None


class Diagnosis(BaseModel):
    text: str
    status: Literal["suspected", "confirmed", "ruled_out"] = "suspected"


class Medication(BaseModel):
    name: str
    dose: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instruction: Optional[str] = None


class MedInstruction(BaseModel):
    med_name: str
    plain_text: str
    timing: Optional[str] = None
    total_days: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


# the model writes these; med_name is matched back and source is set in code
class MedInstructionDraft(BaseModel):
    med_name: str
    plain_text: str
    timing: Optional[str] = None
    total_days: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class MedInstructionList(BaseModel):
    instructions: list[MedInstructionDraft] = Field(default_factory=list)


class FollowUp(BaseModel):
    when: Optional[str] = None
    reason: Optional[str] = None


class Soap(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: str = ""
    plan: str = ""


class Entities(BaseModel):
    chief_complaint: Optional[str] = None
    symptoms: list[Symptom] = Field(default_factory=list)
    vitals: list[Vital] = Field(default_factory=list)
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    follow_up: Optional[FollowUp] = None


# what the LLM is asked for; med_instructions come from a second pass
class NoteDraft(BaseModel):
    soap: Soap
    entities: Entities


class ClinicalNote(NoteDraft):
    med_instructions: list[MedInstruction] = Field(default_factory=list)


# ---- patient portfolio ----

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)
    dob: Optional[str] = None
    sex: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hospital_phone: Optional[str] = None


class PatientOut(BaseModel):
    id: int
    username: str
    full_name: str
    dob: Optional[str] = None
    sex: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hospital_phone: Optional[str] = None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    token: str
    patient: PatientOut


# the editable shapes: what a patient may change about their own record
class ProfileIn(BaseModel):
    full_name: str = Field(min_length=1)
    dob: Optional[str] = None
    sex: Optional[str] = None
    blood_group: Optional[str] = None
    phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hospital_phone: Optional[str] = None


class ConditionIn(BaseModel):
    name: str = Field(min_length=1)
    since: Optional[str] = None
    status: Literal["active", "resolved"] = "active"
    notes: Optional[str] = None


class AllergyIn(BaseModel):
    substance: str = Field(min_length=1)
    reaction: Optional[str] = None
    severity: Optional[Literal["mild", "moderate", "severe"]] = None


class AppointmentIn(BaseModel):
    scheduled_for: str = Field(min_length=1)
    reason: Optional[str] = None
    status: Literal["scheduled", "completed", "cancelled"] = "scheduled"
    # the doctor is matched by name and created if new, so one call is enough
    doctor_name: Optional[str] = None
    doctor_specialty: Optional[str] = None
    doctor_hospital: Optional[str] = None
    doctor_phone: Optional[str] = None


class ConditionOut(BaseModel):
    id: int
    name: str
    since: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class AllergyOut(BaseModel):
    id: int
    substance: str
    reaction: Optional[str] = None
    severity: Optional[str] = None

    model_config = {"from_attributes": True}


class DoctorOut(BaseModel):
    id: int
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class AppointmentOut(BaseModel):
    id: int
    scheduled_for: str
    reason: Optional[str] = None
    status: Optional[str] = None
    doctor: Optional[DoctorOut] = None

    model_config = {"from_attributes": True}


class Portfolio(BaseModel):
    patient: PatientOut
    conditions: list[ConditionOut] = Field(default_factory=list)
    allergies: list[AllergyOut] = Field(default_factory=list)
    appointments: list[AppointmentOut] = Field(default_factory=list)
    doctors_seen: list[DoctorOut] = Field(default_factory=list)
    current_medications: list[Medication] = Field(default_factory=list)
    encounters: list["EncounterOut"] = Field(default_factory=list)


# deliberately thin: this is the only thing readable without signing in
class EmergencyCard(BaseModel):
    full_name: str
    dob: Optional[str] = None
    sex: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: list[AllergyOut] = Field(default_factory=list)
    conditions: list[ConditionOut] = Field(default_factory=list)
    current_medications: list[Medication] = Field(default_factory=list)
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    hospital_phone: Optional[str] = None


# ---- API shapes ----

class SegmentOut(BaseModel):
    id: int
    idx: int
    start_s: float
    end_s: float
    speaker: Optional[str] = None
    text: str
    edited: int = 0

    model_config = {"from_attributes": True}


# a transcript produced in the browser: the audio itself never reaches the server
class SegmentIn(BaseModel):
    start_s: float
    end_s: float
    text: str = Field(min_length=1)


class BrowserTranscript(BaseModel):
    segments: list[SegmentIn] = Field(min_length=1)
    language: Optional[str] = None
    duration_s: Optional[float] = None
    asr_ms: Optional[int] = None
    asr_model: str = "whisper (browser)"
    patient_label: Optional[str] = None


class SegmentEdit(BaseModel):
    id: int
    speaker: Optional[str] = None
    text: Optional[str] = None


class EncounterOut(BaseModel):
    id: int
    created_at: str
    patient_label: Optional[str] = None
    source: str
    language: Optional[str] = None
    duration_s: Optional[float] = None
    status: str
    asr_ms: Optional[int] = None
    llm_ms: Optional[int] = None
    asr_model: Optional[str] = None
    llm_model: Optional[str] = None

    model_config = {"from_attributes": True}


class EncounterDetail(EncounterOut):
    segments: list[SegmentOut] = Field(default_factory=list)
    note: Optional[ClinicalNote] = None
    reviewed: int = 0
    fhir_bundle: Optional[dict] = None
    fhir_valid: Optional[bool] = None
