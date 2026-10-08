# HealthSync

Edge-first ambient clinical scribe. It records a doctor-patient consultation,
transcribes it locally, and turns it into a structured clinical note plus FHIR R4B
resources. All inference runs on the machine — audio never leaves it.

It also keeps a medical portfolio for each patient: conditions, allergies,
medications, doctors seen and appointments, behind a sign-in, with an emergency
card that a responder can read without one.


## Requirements

- Python 3.10+, Node 20+
- ffmpeg on PATH
- Ollama running locally
- NVIDIA GPU for the fast path (falls back to CPU automatically)

## Setup

```
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```
cd frontend
npm install
```

Pull the models once, then everything works offline:

```
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
```

Seed the demo data (drops and recreates all tables):

```
cd backend
.venv\Scripts\python.exe -m app.seed
```

## Run

Backend:

```
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --port 8000
```

Frontend:

```
npm --prefix frontend run dev
```

Open http://localhost:5173 and sign in with `ananya` / `healthsync123`.

## Accounts

Anyone can create one from the sign-in screen. Usernames are 3+ characters,
passwords 8+. The optional profile fields (blood group, phone, emergency
contact) are what populate the emergency card, so the form says so rather than
collecting them silently.

Each patient sees only their own encounters. Another patient's consultation
returns 404 rather than 403, so a signed-in account cannot probe for what exists.

### Seeded demo accounts

All fictional. Password for each is `healthsync123`.

| Username | Name | Notes |
|---|---|---|
| ananya | Ananya Sharma | Asthma, severe penicillin allergy |
| rohit | Rohit Verma | Type 2 diabetes, hypertension |
| meera | Meera Nair | Migraine with aura |

## The four tabs

- **Consultation** — record, upload or load the bundled sample, transcribe, label
  speakers, generate the note, edit every field, inspect the FHIR bundle.
- **My record** — the patient's portfolio. "Edit record" makes the profile,
  medical conditions and allergies editable: add rows, remove rows, change any
  field, save. Current medications are not editable here; they come from the
  most recent consultation note and are corrected on the note itself.
- **Ask HealthSync** — a chatbot grounded in that patient's record. It explains the
  note, repeats what the doctor prescribed, and refuses to recommend or change
  any medication. Emergency symptoms trigger an escalation message.
- **Emergency card** — blood group, allergies, active conditions, current
  medications and contacts.

The emergency card is also reachable at `#emergency/<patient id>` **without
signing in**, the way a phone lock screen shows a medical ID. It exposes only
that minimal set; notes and transcripts stay behind the login.

## Demo safety

`data/samples/sample_consult_01.wav` is a bundled consultation, so a broken
microphone cannot kill a demo. Regenerate it with
`backend/scripts/make_sample.ps1` (Windows TTS, no network).

## Model choice

The note generator is switchable per request from the Consultation tab.

| | llama3.2:3b | qwen2.5:7b |
|---|---|---|
| Speed | ~8 s | ~35 s |
| Medication capture | misses drugs never named outright | catches them |
| Symptom durations | captured | often missed |
| Invented durations | occasionally | none observed |

llama3.2:3b is the default because the demo needs to stay quick. qwen2.5:7b is
the better clinical read.

## Deployment

The backend cannot run on a serverless host. faster-whisper plus its CUDA
runtime is roughly 2 GB against Vercel's 250 MB function limit, Ollama is a
persistent process with gigabyte weights, a note takes 8 to 35 seconds against a
10 second function timeout, and the filesystem has to persist between requests.
So the two halves deploy to different places.

**Frontend to Vercel.** Root directory `frontend`, framework Vite. Set one
environment variable:

```
VITE_API_URL=https://<your-backend-host>
```

**Backend to any container host with a disk** (Render, Railway, Fly). A
`Dockerfile` and a `render.yaml` blueprint are included. Set:

```
HEALTHSYNC_DEMO_MODE=true
HEALTHSYNC_ORIGINS=https://<your-vercel-domain>
DATABASE_URL=postgresql://...      # optional; falls back to sqlite on the disk
HEALTHSYNC_GROQ_API_KEY=gsk_...        # optional; see "Which model answers" below
```

### Hosted database

Set `DATABASE_URL` and nothing is written to a local file. Any managed Postgres
works; Neon and Supabase both have a free tier that needs no card.

1. Create a Postgres database on the provider.
2. Copy the connection string. If it begins `postgres://`, change that prefix to
   `postgresql://` — SQLAlchemy needs the longer form.
3. Set it as `DATABASE_URL` on the backend host, and locally in `backend/.env`
   if you want to point your laptop at the same database.
4. Create the tables and demo patients:

```
cd backend
set DATABASE_URL=postgresql://...
.venv\Scripts\python.exe -m app.seed
```

The schema compiles cleanly for Postgres — `SERIAL` keys, cascading foreign
keys — and the same code runs on either engine. Only the SQLite foreign-key
pragma is conditional.

One caveat: uploaded recordings still go to `HEALTHSYNC_DATA_DIR` on the host's
filesystem, not into the database. On a host without a persistent disk they
disappear when the container restarts. In demo mode no audio is uploaded at all,
so it does not arise; if you want real uploads in the cloud, they need object
storage.

### Which model answers

There are three possibilities and the app never guesses. `/api/health` reports
`chat_backend`, and the status bar and the note and chat screens all render from
it, so what is on screen matches where the work actually happens.

| Setting | `chat_backend` | Where notes and answers come from |
|---|---|---|
| no demo mode | `ollama` | this machine, nothing leaves it |
| demo mode | `browser` | a small model on the visitor's own GPU |
| demo mode + `HEALTHSYNC_GROQ_API_KEY` | `groq` | Groq's API |

The Groq path sends the transcript, and for chat the patient's whole record, to
a third party. That contradicts the claim the rest of the project rests on, so
the interface says so in red on both screens rather than leaving it to be
discovered. It is a deliberate trade for a hosted demo that works in any
browser; the honest demo is still a local install.

`use_groq()` is false whenever demo mode is off, so a key left in the
environment cannot redirect a real install.

Speech never goes to Groq. Recordings and uploaded files are transcribed in the
browser in every hosted configuration, so the audio itself stays on the device
even when the text does not.

### Speech in the browser

The hosted site has no speech model, but recording and file upload both still
work there: whisper tiny runs inside the visitor's browser through
transformers.js, and only the resulting text is sent to the server. The audio
itself never leaves the device, so that part of the privacy claim holds on the
web as well as on a laptop.

The model is about 150 MB at fp32 and downloads once, then the browser caches
it. Int8 builds are smaller but the whisper decoder ones currently fail to load
under onnxruntime-web, which is why full precision is pinned in `browserAsr.js`.

Measured on a desktop browser: 16 seconds of audio transcribed in 5.8 seconds,
roughly 3x realtime, with usable timestamps.

Locally the server does the transcription instead, because whisper `small` on
the GPU is both faster and more accurate than tiny in a browser.

### The language model in the browser

No free container host has enough memory for Ollama — `llama3.2:3b` wants about
3 GB and a free instance gives you around 512 MB — so without a Groq key the
hosted site runs the note generator and the assistant on the visitor's own GPU
through WebGPU, using `@mlc-ai/web-llm`. Nothing they type or record leaves
their machine, which is the same reason speech runs there too.

With `HEALTHSYNC_GROQ_API_KEY` set this path is not used; see "Which model answers".

The prompts still come from `prompts.py`: the browser fetches them from
`/api/prompts`, so there is one copy of the wording to tune, not two. A note
written this way is posted to `/api/encounters/{id}/note/import`, where the
server validates it against the same Pydantic model and builds the FHIR bundle.

What it costs:

- about 1 GB downloaded once, then cached by the browser
- Chrome or Edge on a desktop, with `shader-f16`. Safari and default Firefox
  cannot run it, and the app says so plainly instead of failing
- a 1.5B model writes weaker notes than the 3B you run locally, and much weaker
  than qwen2.5:7b

Locally none of this is used: the server talks to Ollama as before.

Not yet verified: how long a note takes on this path. The pipeline was tested up to
and including loading the model into the GPU, but generation could not be timed
in the test environment, where the browser tab was hidden and therefore throttled
to zero frames, and WebGPU had bound to an Intel integrated GPU rather than the
discrete card. Browsers often pick the integrated GPU by default, which is why
`support()` now asks for a high-performance adapter. **Time this on the machine
you plan to demo from before relying on it.**

### Demo mode

A cloud host has no GPU and no Ollama, so `HEALTHSYNC_DEMO_MODE=true` tells the
backend not to reach for models it does not have. The bundled sample is served
from precomputed results, so the whole flow still demonstrates — transcript,
speaker labels, note, editing, FHIR bundle — without any inference on the host.

The precomputed files are `data/samples/sample_consult_01.segments.json` and
`.note.json`, generated on a GPU machine with qwen2.5:7b.

Audio the visitor supplies never reaches the server: recordings and uploads are
transcribed in the browser and posted as text to `/api/audio/browser`. The
server's own `/transcribe` route is only used by the bundled sample in demo
mode, and refuses anything else with an explanation rather than hanging.

Notes follow whichever backend is configured, per "Which model answers".

Test both configurations locally before deploying:

```
cd backend
.venv\Scripts\python.exe -m uvicorn app.main:app --env-file .env.demo --port 8001
.venv\Scripts\python.exe -m uvicorn app.main:app --env-file .env.groq --port 8002
```

`.env.groq` carries a placeholder key, which is enough to check that requests
are routed to Groq rather than replayed. Put a real key in it to check the
answers themselves, and do not commit that.

### Deploying does change the privacy story

The whole pitch is that audio and inference stay on the device. A deployed copy
holds patient records on someone else's server, so it is a showcase of the
interface, not the product. The honest live demo is still the laptop: full local
inference, network adapter off. Say which one you are showing.

## What this is not

Prototype-grade authentication: salted PBKDF2 and random session tokens, but no
rate limiting, no password reset, no expiry. Do not put real patient data behind
it. Nothing here is a medical device and no output should be acted on without a
clinician.
