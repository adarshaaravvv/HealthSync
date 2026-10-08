import time

import requests
from pydantic import ValidationError

from . import config, prompts
from .schemas import ClinicalNote, MedInstruction, MedInstructionList, NoteDraft


class LLMError(RuntimeError):
    pass


def generate_note(transcript_text, model=None):
    model = model or config.LLM_MODEL
    messages = [
        {"role": "system", "content": prompts.NOTE_SYSTEM},
        {"role": "user", "content": prompts.note_user(transcript_text)},
    ]
    draft, note_ms = _ask_until_valid(messages, NoteDraft, model)

    instructions, instr_ms = _build_instructions(draft.entities.medications, model)

    note = ClinicalNote(soap=draft.soap, entities=draft.entities, med_instructions=instructions)
    return note, note_ms + instr_ms


def free_chat(system_prompt, history, model=None):
    if config.use_groq():
        return _groq_chat(system_prompt, history)

    # no JSON schema here: the reply is prose for a person to read
    model = model or config.LLM_MODEL
    turns = [{"role": "system", "content": system_prompt}] + history

    start = time.perf_counter()
    try:
        response = requests.post(
            f"{config.OLLAMA_URL}/api/chat",
            json={"model": model, "messages": turns, "stream": False,
                  "options": {"temperature": 0.3}},
            timeout=300,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise LLMError(f"cannot reach Ollama at {config.OLLAMA_URL}: {e}")

    reply = response.json()["message"]["content"].strip()
    return reply, int((time.perf_counter() - start) * 1000)


def _groq_chat(system_prompt, history):
    turns = [{"role": "system", "content": system_prompt}] + history
    reply, elapsed_ms = _groq(turns, temperature=0.3)
    return reply.strip(), elapsed_ms


def _groq(messages, temperature=0.0, json_only=False):
    body = {"model": config.GROQ_MODEL, "messages": messages, "temperature": temperature}
    if json_only:
        body["response_format"] = {"type": "json_object"}

    start = time.perf_counter()
    try:
        response = requests.post(
            config.GROQ_URL,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json=body,
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise LLMError(f"cannot reach Groq: {e}")

    return response.json()["choices"][0]["message"]["content"], int((time.perf_counter() - start) * 1000)


def transcript_from_segments(segments):
    return "\n".join(f"{(s.speaker or 'unknown').title()}: {s.text}" for s in segments)


def _build_instructions(medications, model):
    if not medications:
        return [], 0

    messages = [
        {"role": "system", "content": prompts.INSTRUCTIONS_SYSTEM},
        {"role": "user", "content": prompts.instructions_user(medications)},
    ]

    try:
        result, elapsed_ms = _ask_until_valid(messages, MedInstructionList, model)
    except LLMError:
        return [_fallback(med) for med in medications], 0

    # match on name so a reordered or short reply cannot misattribute a dose
    by_name = {d.med_name.strip().lower(): d for d in result.instructions}
    out = []
    for med in medications:
        draft = by_name.get(med.name.strip().lower())
        if draft is None:
            out.append(_fallback(med))
            continue
        out.append(MedInstruction(
            med_name=med.name,
            plain_text=draft.plain_text,
            timing=draft.timing,
            total_days=draft.total_days,
            warnings=draft.warnings,
        ))

    return out, elapsed_ms


def _fallback(med):
    return MedInstruction(
        med_name=med.name,
        plain_text="Instructions could not be generated. Follow the plan in the note above.",
    )


def _ask_until_valid(messages, model_cls, model):
    schema = model_cls.model_json_schema()
    total_ms = 0
    last_error = None

    for _ in range(config.LLM_RETRIES + 1):
        turns = list(messages)
        if last_error:
            turns.append({"role": "user", "content": prompts.retry(last_error)})

        raw, elapsed_ms = _chat(turns, schema, model)
        total_ms += elapsed_ms

        try:
            return model_cls.model_validate_json(_strip_fences(raw)), total_ms
        except (ValidationError, ValueError) as e:
            last_error = str(e)[:800]

    raise LLMError(f"{model_cls.__name__} still invalid after {config.LLM_RETRIES + 1} tries: {last_error}")


def _chat(messages, schema, model):
    # Groq has no schema-guided decoding, so json mode plus the retry loop above
    # does the same job of getting a parseable object back
    if config.use_groq():
        return _groq(messages, temperature=0.0, json_only=True)

    start = time.perf_counter()
    try:
        response = requests.post(
            f"{config.OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "format": schema,
                "options": {"temperature": 0},
            },
            timeout=300,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise LLMError(f"cannot reach Ollama at {config.OLLAMA_URL}: {e}")

    return response.json()["message"]["content"], int((time.perf_counter() - start) * 1000)


def _strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return text.strip()
