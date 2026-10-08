import os
import shutil
import subprocess
from pathlib import Path

# winget puts ffmpeg on PATH, but that change never reaches an already-running
# shell, so fall back to the install location before giving up.
_LINKS = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links"


def _find(name):
    found = shutil.which(name)
    if found:
        return found
    fallback = _LINKS / f"{name}.exe"
    return str(fallback) if fallback.is_file() else None


FFMPEG = _find("ffmpeg")
FFPROBE = _find("ffprobe")


def have_ffmpeg():
    return FFMPEG is not None


def to_wav16k(src, dst):
    # whisper wants 16 kHz mono; browsers hand us webm/opus, which it cannot read
    if not FFMPEG:
        raise RuntimeError("ffmpeg not found")

    result = subprocess.run(
        [FFMPEG, "-y", "-loglevel", "error", "-i", str(src),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(dst)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[:400]}")
    return dst


def duration_of(path):
    if not FFPROBE:
        return None

    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None

    try:
        return round(float(result.stdout.strip()), 2)
    except ValueError:
        return None
