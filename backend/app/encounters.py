import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from . import auth, config, fhir_map
from .db import get_db
from .models_db import Encounter, Patient, now
from .schemas import ClinicalNote, EncounterOut, EncounterDetail, SegmentOut, SegmentEdit

router = APIRouter(prefix="/api/encounters", tags=["encounters"])


def owned(encounter_id, patient, db):
    """An encounter belonging to someone else must look like it does not exist,
    so a signed-in patient cannot probe for other people's consultations."""
    enc = db.get(Encounter, encounter_id)
    if not enc or enc.patient_id != patient.id:
        raise HTTPException(404, "encounter not found")
    return enc


@router.get("", response_model=list[EncounterOut])
def list_encounters(patient: Patient = Depends(auth.current_patient),
                    db: Session = Depends(get_db)):
    return (
        db.query(Encounter)
        .filter(Encounter.patient_id == patient.id)
        .order_by(Encounter.id.desc())
        .all()
    )


def build_detail(enc):
    # built from EncounterOut, not from the ORM row: the row's "note" is a Note
    # record, while the schema's "note" is the parsed ClinicalNote
    detail = EncounterDetail(**EncounterOut.model_validate(enc).model_dump())
    detail.segments = [SegmentOut.model_validate(s) for s in enc.segments]

    if enc.note:
        note_json = enc.note.final_note_json or enc.note.raw_note_json
        detail.note = json.loads(note_json)
        detail.reviewed = enc.note.reviewed
    if enc.bundle:
        detail.fhir_bundle = json.loads(enc.bundle.bundle_json)
        detail.fhir_valid = bool(enc.bundle.valid)

    return detail


@router.get("/{encounter_id}", response_model=EncounterDetail)
def get_encounter(encounter_id: int, patient: Patient = Depends(auth.current_patient),
                  db: Session = Depends(get_db)):
    return build_detail(owned(encounter_id, patient, db))


@router.put("/{encounter_id}/note", response_model=EncounterDetail)
def save_note(encounter_id: int, note: ClinicalNote,
              patient: Patient = Depends(auth.current_patient),
              db: Session = Depends(get_db)):
    enc = owned(encounter_id, patient, db)
    if not enc.note:
        raise HTTPException(400, "generate a note before saving edits")

    # the raw draft is never overwritten, so the model's original stays auditable
    enc.note.final_note_json = note.model_dump_json()
    enc.note.reviewed = 1
    enc.note.updated_at = now()
    enc.status = "reviewed"

    fhir_map.rebuild_bundle(db, enc)

    db.commit()
    db.refresh(enc)
    return build_detail(enc)


@router.delete("/{encounter_id}")
def delete_encounter(encounter_id: int, patient: Patient = Depends(auth.current_patient),
                     db: Session = Depends(get_db)):
    enc = owned(encounter_id, patient, db)

    # the recording is the most sensitive thing here, so deleting an encounter
    # has to take the audio with it, not just the rows that point at it
    audio_path = config.AUDIO_DIR / enc.audio_path if enc.audio_path else None

    db.delete(enc)
    db.commit()

    if audio_path:
        audio_path.unlink(missing_ok=True)
    return {"deleted": encounter_id, "audio_removed": bool(audio_path)}


@router.patch("/{encounter_id}/segments", response_model=list[SegmentOut])
def edit_segments(encounter_id: int, edits: list[SegmentEdit],
                  patient: Patient = Depends(auth.current_patient),
                  db: Session = Depends(get_db)):
    enc = owned(encounter_id, patient, db)

    by_id = {s.id: s for s in enc.segments}
    for e in edits:
        seg = by_id.get(e.id)
        if not seg:
            continue
        if e.speaker is not None:
            seg.speaker = e.speaker
        if e.text is not None:
            seg.text = e.text
        seg.edited = 1

    db.commit()
    return [SegmentOut.model_validate(s) for s in enc.segments]
