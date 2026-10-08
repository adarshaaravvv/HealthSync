import json

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import auth
from .db import get_db
from .models_db import Allergy, Appointment, Doctor, MedicalCondition, Patient
from .schemas import (
    AllergyIn, AllergyOut, AppointmentIn, AppointmentOut, ConditionIn, ConditionOut,
    DoctorOut, EmergencyCard, EncounterOut, LoginRequest, LoginResponse, PatientOut,
    Portfolio, ProfileIn, RegisterRequest,
)

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.post("/auth/login", response_model=LoginResponse)
def sign_in(body: LoginRequest, db: Session = Depends(get_db)):
    result = auth.login(db, body.username, body.password)
    if not result:
        raise HTTPException(401, "wrong username or password")
    token, patient = result
    return LoginResponse(token=token, patient=PatientOut.model_validate(patient))


@router.post("/auth/register", response_model=LoginResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    taken = db.query(Patient).filter(Patient.username == body.username).first()
    if taken:
        raise HTTPException(409, "that username is already taken")

    password_hash, salt = auth.hash_password(body.password)
    patient = Patient(
        password_hash=password_hash,
        salt=salt,
        **body.model_dump(exclude={"password"}),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    # sign the new account in straight away rather than bouncing back to the form
    token = auth.start_session(db, patient)
    return LoginResponse(token=token, patient=PatientOut.model_validate(patient))


@router.post("/auth/logout")
def sign_out(authorization: str = Header(None), db: Session = Depends(get_db)):
    if authorization and authorization.startswith("Bearer "):
        auth.logout(db, authorization.split(" ", 1)[1])
    return {"ok": True}


@router.get("/portfolio", response_model=Portfolio)
def my_portfolio(patient: Patient = Depends(auth.current_patient)):
    doctors = {}
    for appointment in patient.appointments:
        if appointment.doctor:
            doctors[appointment.doctor.id] = appointment.doctor
    for enc in patient.encounters:
        if enc.doctor:
            doctors[enc.doctor.id] = enc.doctor

    return Portfolio(
        patient=PatientOut.model_validate(patient),
        conditions=[ConditionOut.model_validate(c) for c in patient.conditions],
        allergies=[AllergyOut.model_validate(a) for a in patient.allergies],
        appointments=[AppointmentOut.model_validate(a) for a in patient.appointments],
        doctors_seen=[DoctorOut.model_validate(d) for d in doctors.values()],
        current_medications=current_medications(patient),
        encounters=[EncounterOut.model_validate(e) for e in patient.encounters],
    )


@router.put("/portfolio/profile", response_model=PatientOut)
def save_profile(body: ProfileIn, patient: Patient = Depends(auth.current_patient),
                 db: Session = Depends(get_db)):
    for field, value in body.model_dump().items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return PatientOut.model_validate(patient)


# conditions and allergies are saved as whole lists rather than row at a time:
# the editor hands back what the list should now be, which keeps deletes simple
@router.put("/portfolio/conditions", response_model=list[ConditionOut])
def save_conditions(body: list[ConditionIn], patient: Patient = Depends(auth.current_patient),
                    db: Session = Depends(get_db)):
    for existing in patient.conditions:
        db.delete(existing)
    db.flush()

    for item in body:
        db.add(MedicalCondition(patient_id=patient.id, **item.model_dump()))

    db.commit()
    db.refresh(patient)
    return [ConditionOut.model_validate(c) for c in patient.conditions]


@router.put("/portfolio/allergies", response_model=list[AllergyOut])
def save_allergies(body: list[AllergyIn], patient: Patient = Depends(auth.current_patient),
                   db: Session = Depends(get_db)):
    for existing in patient.allergies:
        db.delete(existing)
    db.flush()

    for item in body:
        db.add(Allergy(patient_id=patient.id, **item.model_dump()))

    db.commit()
    db.refresh(patient)
    return [AllergyOut.model_validate(a) for a in patient.allergies]


@router.put("/portfolio/appointments", response_model=list[AppointmentOut])
def save_appointments(body: list[AppointmentIn],
                      patient: Patient = Depends(auth.current_patient),
                      db: Session = Depends(get_db)):
    for existing in patient.appointments:
        db.delete(existing)
    db.flush()

    for item in body:
        db.add(Appointment(
            patient_id=patient.id,
            doctor_id=_find_or_add_doctor(db, item),
            scheduled_for=item.scheduled_for,
            reason=item.reason,
            status=item.status,
        ))

    db.commit()
    db.refresh(patient)
    return [AppointmentOut.model_validate(a) for a in patient.appointments]


def _find_or_add_doctor(db, item):
    if not item.doctor_name:
        return None

    doctor = db.query(Doctor).filter(Doctor.name == item.doctor_name).first()
    if not doctor:
        doctor = Doctor(
            name=item.doctor_name,
            specialty=item.doctor_specialty,
            hospital=item.doctor_hospital,
            phone=item.doctor_phone,
        )
        db.add(doctor)
        db.flush()
    return doctor.id


@router.get("/emergency/{patient_id}", response_model=EmergencyCard)
def emergency_card(patient_id: int, db: Session = Depends(get_db)):
    # intentionally unauthenticated: an unconscious patient cannot sign in.
    # only the minimum a responder needs, never notes or transcripts.
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "patient not found")

    return EmergencyCard(
        full_name=patient.full_name,
        dob=patient.dob,
        sex=patient.sex,
        blood_group=patient.blood_group,
        allergies=[AllergyOut.model_validate(a) for a in patient.allergies],
        conditions=[ConditionOut.model_validate(c) for c in patient.conditions
                    if c.status == "active"],
        current_medications=current_medications(patient),
        emergency_contact_name=patient.emergency_contact_name,
        emergency_contact_phone=patient.emergency_contact_phone,
        hospital_phone=patient.hospital_phone,
    )


def current_medications(patient):
    # whatever the most recent encounter with a note prescribed
    for enc in patient.encounters:
        if not enc.note:
            continue
        note = json.loads(enc.note.final_note_json or enc.note.raw_note_json)
        return note.get("entities", {}).get("medications", [])
    return []
