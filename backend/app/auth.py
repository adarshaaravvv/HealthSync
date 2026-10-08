import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .db import get_db
from .models_db import AuthSession, Patient

ITERATIONS = 200_000


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return digest.hex(), salt


def verify_password(password, password_hash, salt):
    candidate, _ = hash_password(password, salt)
    # constant-time compare so a wrong password cannot be found byte by byte
    return secrets.compare_digest(candidate, password_hash)


def login(db, username, password):
    patient = db.query(Patient).filter(Patient.username == username).first()
    if not patient or not verify_password(password, patient.password_hash, patient.salt):
        return None
    return start_session(db, patient), patient


def start_session(db, patient):
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(patient_id=patient.id, token=token))
    db.commit()
    return token


def logout(db, token):
    session = db.query(AuthSession).filter(AuthSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()


def current_patient(authorization: str = Header(None), db: Session = Depends(get_db)):
    patient = optional_patient(authorization, db)
    if not patient:
        raise HTTPException(401, "not signed in")
    return patient


def optional_patient(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    session = db.query(AuthSession).filter(AuthSession.token == token).first()
    return session.patient if session else None
