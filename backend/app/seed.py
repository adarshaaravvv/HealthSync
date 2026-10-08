"""Fills the database with invented demo data. Every person here is fictional.

Run from the backend directory:  .venv\\Scripts\\python.exe -m app.seed
This drops and recreates all tables.
"""
from . import auth, config
from .db import Base, SessionLocal, engine
from .models_db import Allergy, Appointment, Doctor, MedicalCondition, Patient

DEMO_PASSWORD = "healthsync123"

DOCTORS = [
    {"name": "Dr. Priya Raghavan", "specialty": "Pulmonology", "hospital": "Patna General Hospital", "phone": "+91-612-555-0111"},
    {"name": "Dr. Sanjay Mehta", "specialty": "General Medicine", "hospital": "Patna General Hospital", "phone": "+91-612-555-0112"},
    {"name": "Dr. Kavita Iyer", "specialty": "Neurology", "hospital": "Ganga Care Clinic", "phone": "+91-612-555-0113"},
]

PATIENTS = [
    {
        "username": "ananya",
        "full_name": "Ananya Sharma",
        "dob": "1998-04-12",
        "sex": "female",
        "blood_group": "B+",
        "phone": "+91-99000-11223",
        "emergency_contact_name": "Rakesh Sharma (father)",
        "emergency_contact_phone": "+91-99000-11224",
        "hospital_phone": "+91-612-555-0100",
        "conditions": [
            {"name": "Asthma", "since": "2012", "status": "active", "notes": "Inhaler used during winter months"},
            {"name": "Iron deficiency anaemia", "since": "2021", "status": "resolved", "notes": None},
        ],
        "allergies": [
            {"substance": "Penicillin", "reaction": "Rash and swelling", "severity": "severe"},
            {"substance": "Dust mites", "reaction": "Sneezing, wheeze", "severity": "moderate"},
        ],
        "appointments": [
            {"doctor": 0, "scheduled_for": "2026-08-07 10:30", "reason": "Chest X-ray review", "status": "scheduled"},
            {"doctor": 1, "scheduled_for": "2026-06-19 09:00", "reason": "Fever and cough", "status": "completed"},
        ],
    },
    {
        "username": "rohit",
        "full_name": "Rohit Verma",
        "dob": "1979-11-30",
        "sex": "male",
        "blood_group": "O+",
        "phone": "+91-99000-33445",
        "emergency_contact_name": "Sunita Verma (wife)",
        "emergency_contact_phone": "+91-99000-33446",
        "hospital_phone": "+91-612-555-0100",
        "conditions": [
            {"name": "Type 2 diabetes mellitus", "since": "2016", "status": "active", "notes": "On metformin, HbA1c 7.4 at last check"},
            {"name": "Hypertension", "since": "2019", "status": "active", "notes": "Controlled on amlodipine"},
        ],
        "allergies": [
            {"substance": "Sulfa drugs", "reaction": "Hives", "severity": "moderate"},
        ],
        "appointments": [
            {"doctor": 1, "scheduled_for": "2026-08-14 11:15", "reason": "Quarterly diabetes review", "status": "scheduled"},
        ],
    },
    {
        "username": "meera",
        "full_name": "Meera Nair",
        "dob": "2003-02-08",
        "sex": "female",
        "blood_group": "A-",
        "phone": "+91-99000-55667",
        "emergency_contact_name": "Latha Nair (mother)",
        "emergency_contact_phone": "+91-99000-55668",
        "hospital_phone": "+91-612-555-0100",
        "conditions": [
            {"name": "Migraine with aura", "since": "2020", "status": "active", "notes": "Triggered by lack of sleep"},
        ],
        "allergies": [],
        "appointments": [
            {"doctor": 2, "scheduled_for": "2026-09-02 16:00", "reason": "Migraine follow up", "status": "scheduled"},
        ],
    },
]


def run():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    # dropping the tables orphans every recording, so clear the audio too
    removed = 0
    for wav in config.AUDIO_DIR.glob("*.wav"):
        wav.unlink()
        removed += 1
    if removed:
        print(f"removed {removed} orphaned recording(s)")

    db = SessionLocal()
    doctors = [Doctor(**d) for d in DOCTORS]
    db.add_all(doctors)
    db.flush()

    for spec in PATIENTS:
        password_hash, salt = auth.hash_password(DEMO_PASSWORD)
        patient = Patient(
            username=spec["username"],
            password_hash=password_hash,
            salt=salt,
            full_name=spec["full_name"],
            dob=spec["dob"],
            sex=spec["sex"],
            blood_group=spec["blood_group"],
            phone=spec["phone"],
            emergency_contact_name=spec["emergency_contact_name"],
            emergency_contact_phone=spec["emergency_contact_phone"],
            hospital_phone=spec["hospital_phone"],
        )
        db.add(patient)
        db.flush()

        for c in spec["conditions"]:
            db.add(MedicalCondition(patient_id=patient.id, **c))
        for a in spec["allergies"]:
            db.add(Allergy(patient_id=patient.id, **a))
        for appt in spec["appointments"]:
            db.add(Appointment(
                patient_id=patient.id,
                doctor_id=doctors[appt["doctor"]].id,
                scheduled_for=appt["scheduled_for"],
                reason=appt["reason"],
                status=appt["status"],
            ))

    db.commit()

    print("seeded demo data (all fictional)")
    for spec in PATIENTS:
        print(f"  {spec['username']} / {DEMO_PASSWORD}   {spec['full_name']}")
    db.close()


if __name__ == "__main__":
    run()
