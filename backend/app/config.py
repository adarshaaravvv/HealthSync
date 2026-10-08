import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("HEALTHSYNC_DATA_DIR", BASE_DIR / "data"))
AUDIO_DIR = DATA_DIR / "audio"
SAMPLES_DIR = BASE_DIR / "data" / "samples"
DB_PATH = DATA_DIR / "healthsync.db"

for d in (DATA_DIR, AUDIO_DIR, SAMPLES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# postgres://... on a host with a managed database, sqlite on a laptop
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# small leaves VRAM for Ollama; medium fights the LLM for space on an 8GB card
ASR_MODEL = os.getenv("HEALTHSYNC_ASR_MODEL", "small")
ASR_DEVICE = os.getenv("HEALTHSYNC_ASR_DEVICE", "cuda")
ASR_COMPUTE = os.getenv("HEALTHSYNC_ASR_COMPUTE", "float16")

OLLAMA_URL = os.getenv("HEALTHSYNC_OLLAMA_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.getenv("HEALTHSYNC_LLM_MODEL", "llama3.2:3b")
GROQ_API_KEY = os.getenv("HEALTHSYNC_GROQ_API_KEY", "")
LLM_RETRIES = 2

# On a host with no GPU and no Ollama the bundled sample is served from
# precomputed results, so the whole flow still demonstrates. Anything other than
# the sample is refused with an explanation rather than left to hang.
DEMO_MODE = os.getenv("HEALTHSYNC_DEMO_MODE", "").lower() in ("1", "true", "yes")

def use_groq():
    # only ever in demo mode: a local install must not send records outside,
    # whatever key happens to be lying around in the environment
    return DEMO_MODE and bool(GROQ_API_KEY)


def chat_backend():
    """Which model actually answers the assistant, so the interface can say so.

    groq means the patient's record is sent to a third party; browser means a
    model on the visitor's own GPU; ollama means this machine.
    """
    if not DEMO_MODE:
        return "ollama"
    return "groq" if GROQ_API_KEY else "browser"


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("HEALTHSYNC_GROQ_MODEL", "llama-3.1-8b-instant")


FRONTEND_ORIGINS = [
    o.strip()
    for o in os.getenv("HEALTHSYNC_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
