import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import auth, config, llm, prompts
from .models_db import Patient

router = APIRouter(prefix="/api", tags=["chat"])

MAX_HISTORY = 10

# a hosted demo has no model attached. Say so plainly rather than failing with a
# 503 the user reads as the whole app being broken.
DEMO_REPLY = (
    "This hosted demo cannot answer questions. The assistant runs a language model on "
    "the clinician's own machine, and this server has no model attached to it.\n\n"
    "Everything else you can see is real: your record, the consultation note and the "
    "emergency card are all live data.\n\n"
    "To try the assistant, run HealthSync on your own machine:\n"
    "https://github.com/your-username/healthsync\n\n"
    "There it answers only from your own record, and it will not recommend or change "
    "any medicine."
)


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatTurn] = []


class ChatReply(BaseModel):
    reply: str
    llm_ms: int


@router.get("/prompts")
def prompt_templates(patient: Patient = Depends(auth.current_patient)):
    # a model running in the visitor's browser still uses the prompts from
    # prompts.py, so there is only ever one copy of the wording to tune
    from .schemas import NoteDraft

    return {
        "note_system": prompts.NOTE_SYSTEM,
        "note_user": prompts.NOTE_USER,
        "note_schema": NoteDraft.model_json_schema(),
        "chat_system": prompts.CHAT_SYSTEM,
        "retry": prompts.RETRY,
    }


@router.get("/chat/context")
def chat_context(patient: Patient = Depends(auth.current_patient)):
    return {"record": record_text(patient)}


@router.post("/chat", response_model=ChatReply)
def ask(body: ChatRequest, patient: Patient = Depends(auth.current_patient)):
    # with a Groq key set, the record below is sent to a third party. config
    # reports that as chat_backend so the interface can say so on screen.
    if config.chat_backend() == "browser":
        return ChatReply(reply=DEMO_REPLY, llm_ms=0)

    history = [t.model_dump() for t in body.history[-MAX_HISTORY:]]
    history.append({"role": "user", "content": body.message})

    try:
        reply, llm_ms = llm.free_chat(prompts.chat_system(record_text(patient)), history)
    except llm.LLMError as e:
        raise HTTPException(503, str(e))

    return ChatReply(reply=reply, llm_ms=llm_ms)


def record_text(patient):
    lines = [
        f"Name: {patient.full_name}",
        f"Date of birth: {patient.dob or 'not recorded'}",
        f"Blood group: {patient.blood_group or 'not recorded'}",
        f"Emergency contact: {patient.emergency_contact_name or 'not recorded'} "
        f"{patient.emergency_contact_phone or ''}".strip(),
        f"Hospital number: {patient.hospital_phone or 'not recorded'}",
        "",
        "Known conditions:",
    ]
    lines += [f"  - {c.name} (since {c.since or 'unknown'}, {c.status})" for c in patient.conditions] or ["  none recorded"]

    lines.append("")
    lines.append("Allergies:")
    lines += [f"  - {a.substance}: {a.reaction or 'reaction not recorded'} ({a.severity or 'severity not recorded'})"
              for a in patient.allergies] or ["  none recorded"]

    lines.append("")
    lines.append("Appointments:")
    lines += [f"  - {a.scheduled_for} with {a.doctor.name if a.doctor else 'unknown doctor'}"
              f" for {a.reason or 'unspecified'} ({a.status})" for a in patient.appointments] or ["  none recorded"]

    latest = next((e for e in patient.encounters if e.note), None)
    if latest:
        note = json.loads(latest.note.final_note_json or latest.note.raw_note_json)
        soap = note.get("soap", {})
        lines += [
            "",
            f"Most recent consultation ({latest.created_at}):",
            f"  What the patient reported: {soap.get('subjective', '')}",
            f"  Examination findings: {soap.get('objective', '')}",
            f"  Doctor's impression: {soap.get('assessment', '')}",
            f"  Plan: {soap.get('plan', '')}",
            "",
            "  Medicines prescribed at that visit:",
        ]
        meds = note.get("entities", {}).get("medications", [])
        lines += [
            f"    - {m.get('name')}: {m.get('dose') or 'dose not recorded'},"
            f" {m.get('frequency') or 'frequency not recorded'},"
            f" {m.get('duration') or 'duration not recorded'}"
            f"{', ' + m['instruction'] if m.get('instruction') else ''}"
            for m in meds
        ] or ["    none recorded"]

        for instruction in note.get("med_instructions", []):
            lines.append(f"    how to take {instruction['med_name']}: {instruction['plain_text']}")
    else:
        lines += ["", "No consultation notes recorded yet."]

    return "\n".join(lines)
