from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship

from .db import Base


def now():
    return datetime.now().isoformat(timespec="seconds")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    dob = Column(String)
    sex = Column(String)
    blood_group = Column(String)
    phone = Column(String)
    emergency_contact_name = Column(String)
    emergency_contact_phone = Column(String)
    hospital_phone = Column(String)
    created_at = Column(String, nullable=False, default=now)

    conditions = relationship("MedicalCondition", back_populates="patient",
                              cascade="all, delete-orphan")
    allergies = relationship("Allergy", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient",
                                cascade="all, delete-orphan", order_by="Appointment.scheduled_for")
    encounters = relationship("Encounter", back_populates="patient", order_by="Encounter.id.desc()")


class MedicalCondition(Base):
    __tablename__ = "conditions"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    since = Column(String)
    status = Column(String, default="active")  # active | resolved
    notes = Column(Text)

    patient = relationship("Patient", back_populates="conditions")


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    substance = Column(String, nullable=False)
    reaction = Column(String)
    severity = Column(String)  # mild | moderate | severe

    patient = relationship("Patient", back_populates="allergies")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    specialty = Column(String)
    hospital = Column(String)
    phone = Column(String)


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    scheduled_for = Column(String, nullable=False)
    reason = Column(String)
    status = Column(String, default="scheduled")  # scheduled | completed | cancelled

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor")


class AuthSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False, unique=True)
    created_at = Column(String, nullable=False, default=now)

    patient = relationship("Patient")


class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(Integer, primary_key=True)
    created_at = Column(String, nullable=False, default=now)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="SET NULL"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    patient_label = Column(String)
    source = Column(String, nullable=False)  # mic | upload | sample
    audio_path = Column(String)
    language = Column(String)
    duration_s = Column(Float)
    status = Column(String, nullable=False, default="new")  # new|transcribed|noted|reviewed
    asr_ms = Column(Integer)
    llm_ms = Column(Integer)
    asr_model = Column(String)
    llm_model = Column(String)

    segments = relationship(
        "Segment", back_populates="encounter", cascade="all, delete-orphan",
        order_by="Segment.idx",
    )
    note = relationship("Note", back_populates="encounter", uselist=False,
                        cascade="all, delete-orphan")
    bundle = relationship("FhirBundle", back_populates="encounter", uselist=False,
                          cascade="all, delete-orphan")
    patient = relationship("Patient", back_populates="encounters")
    doctor = relationship("Doctor")


class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    idx = Column(Integer, nullable=False)
    start_s = Column(Float, nullable=False)
    end_s = Column(Float, nullable=False)
    speaker = Column(String)  # doctor | patient | unknown
    text = Column(Text, nullable=False)
    avg_logprob = Column(Float)
    edited = Column(Integer, default=0)

    encounter = relationship("Encounter", back_populates="segments")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    raw_note_json = Column(Text, nullable=False)
    final_note_json = Column(Text)
    reviewed = Column(Integer, default=0)
    created_at = Column(String, nullable=False, default=now)
    updated_at = Column(String)

    encounter = relationship("Encounter", back_populates="note")


class FhirBundle(Base):
    __tablename__ = "fhir_bundles"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False)
    bundle_json = Column(Text, nullable=False)
    valid = Column(Integer, nullable=False)
    error = Column(Text)
    created_at = Column(String, nullable=False, default=now)

    encounter = relationship("Encounter", back_populates="bundle")
