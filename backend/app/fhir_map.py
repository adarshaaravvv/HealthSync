import base64
import json
import uuid

from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.codeableconcept import CodeableConcept
from fhir.resources.R4B.coding import Coding
from fhir.resources.R4B.condition import Condition
from fhir.resources.R4B.documentreference import DocumentReference
from fhir.resources.R4B.encounter import Encounter as FhirEncounter
from fhir.resources.R4B.medicationrequest import MedicationRequest
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient

ACT_CODE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
CONDITION_CLINICAL = "http://terminology.hl7.org/CodeSystem/condition-clinical"
CONDITION_VERIFICATION = "http://terminology.hl7.org/CodeSystem/condition-ver-status"
LOINC = "http://loinc.org"

# nothing here is coded against SNOMED or RxNorm: the text carries the meaning,
# which is honest for a prototype and still validates
VERIFICATION = {
    "suspected": "provisional",
    "confirmed": "confirmed",
    "ruled_out": "refuted",
}

VITAL_LOINC = {
    "blood pressure": "85354-9",
    "temperature": "8310-5",
    "pulse": "8867-4",
    "heart rate": "8867-4",
    "oxygen saturation": "59408-5",
    "respiratory rate": "9279-1",
    "weight": "29463-7",
    "height": "8302-2",
}


def build_bundle(encounter, note):
    patient_id = f"patient-{encounter.id}"
    encounter_id = f"encounter-{encounter.id}"
    subject = {"reference": f"Patient/{patient_id}"}
    context = {"reference": f"Encounter/{encounter_id}"}

    resources = [
        Patient(id=patient_id, active=True, name=[{"text": encounter.patient_label or "Unnamed patient"}]),
        FhirEncounter(
            id=encounter_id,
            status="finished",
            class_fhir=Coding(system=ACT_CODE, code="AMB", display="ambulatory"),
            subject=subject,
            period={"start": _instant(encounter.created_at)},
        ),
    ]

    for i, diagnosis in enumerate(note.entities.diagnoses):
        resources.append(Condition(
            id=f"condition-{encounter.id}-{i}",
            subject=subject,
            encounter=context,
            code=CodeableConcept(text=diagnosis.text),
            verificationStatus=CodeableConcept(coding=[Coding(
                system=CONDITION_VERIFICATION,
                code=VERIFICATION.get(diagnosis.status, "unconfirmed"),
            )]),
            clinicalStatus=CodeableConcept(coding=[Coding(
                system=CONDITION_CLINICAL,
                code="resolved" if diagnosis.status == "ruled_out" else "active",
            )]),
        ))

    for i, vital in enumerate(note.entities.vitals):
        resources.append(Observation(
            id=f"observation-{encounter.id}-{i}",
            status="final",
            subject=subject,
            encounter=context,
            code=_vital_code(vital),
            valueString=_vital_text(vital),
        ))

    for i, med in enumerate(note.entities.medications):
        resources.append(MedicationRequest(
            id=f"medicationrequest-{encounter.id}-{i}",
            status="active",
            intent="order",
            subject=subject,
            encounter=context,
            medicationCodeableConcept=CodeableConcept(text=med.name),
            dosageInstruction=[{"text": _dosage_text(med)}],
        ))

    resources.append(DocumentReference(
        id=f"documentreference-{encounter.id}",
        status="current",
        subject=subject,
        context={"encounter": [context]},
        type=CodeableConcept(coding=[Coding(system=LOINC, code="11488-4", display="Consult note")]),
        content=[{"attachment": {
            "contentType": "text/plain",
            "data": base64.b64encode(_soap_text(note).encode()).decode(),
            "title": "SOAP note",
        }}],
    ))

    bundle = Bundle(
        id=f"bundle-{encounter.id}",
        type="collection",
        entry=[{"fullUrl": f"urn:uuid:{uuid.uuid4()}", "resource": r} for r in resources],
    )
    # mode="json" so datetimes come out as strings; by_alias so class_fhir emits "class"
    return bundle.model_dump(mode="json", by_alias=True, exclude_none=True)


def rebuild_bundle(db, enc):
    from .models_db import FhirBundle, now
    from .schemas import ClinicalNote

    if not enc.note:
        return None

    note = ClinicalNote.model_validate_json(enc.note.final_note_json or enc.note.raw_note_json)
    error = None
    try:
        # fhir.resources validates on construction, so a build failure is a spec failure
        bundle_json = json.dumps(build_bundle(enc, note))
        valid = 1
    except Exception as e:
        bundle_json = json.dumps(None)
        valid = 0
        error = str(e)[:600]

    if enc.bundle:
        enc.bundle.bundle_json = bundle_json
        enc.bundle.valid = valid
        enc.bundle.error = error
        enc.bundle.created_at = now()
    else:
        db.add(FhirBundle(encounter_id=enc.id, bundle_json=bundle_json, valid=valid, error=error))

    return valid


def _vital_code(vital):
    # models return "blood pressure" or "blood_pressure" depending on which one ran
    code = VITAL_LOINC.get(vital.name.strip().lower().replace("_", " "))
    if code:
        return CodeableConcept(coding=[Coding(system=LOINC, code=code, display=vital.name)], text=vital.name)
    return CodeableConcept(text=vital.name)


def _vital_text(vital):
    return f"{vital.value} {vital.unit}".strip() if vital.unit else vital.value


def _dosage_text(med):
    parts = [med.dose, med.route, med.frequency, med.duration, med.instruction]
    return ", ".join(p for p in parts if p) or "as directed"


def _soap_text(note):
    soap = note.soap
    return (
        f"SUBJECTIVE\n{soap.subjective}\n\n"
        f"OBJECTIVE\n{soap.objective}\n\n"
        f"ASSESSMENT\n{soap.assessment}\n\n"
        f"PLAN\n{soap.plan}\n"
    )


def _instant(created_at):
    # rows store "2026-07-31T14:18:09"; FHIR wants a timezone
    return created_at if created_at.endswith("Z") or "+" in created_at else f"{created_at}Z"
