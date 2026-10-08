import os
import sys
import time
from pathlib import Path

# ctranslate2 needs the CUDA runtime from the nvidia-* pip packages, and Windows
# will not find those DLLs unless their directories are registered before import.
_nvidia = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
if _nvidia.is_dir():
    for _bin in _nvidia.glob("*/bin"):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(str(_bin))
        os.environ["PATH"] = f"{_bin}{os.pathsep}{os.environ['PATH']}"

from faster_whisper import WhisperModel  # noqa: E402

from . import config

_model = None
_device = None


def device():
    return _device or config.ASR_DEVICE


def transcribe(wav_path, language=None):
    try:
        return _run(_get_model(), wav_path, language)
    except Exception as e:
        if device() == "cpu":
            raise
        # a missing CUDA library should slow the demo down, not end it
        print(f"[asr] gpu path failed ({e}); retrying on cpu")
        return _run(_load("cpu", "int8"), wav_path, language)


def _get_model():
    return _model or _load(config.ASR_DEVICE, config.ASR_COMPUTE)


def _load(device_name, compute_type):
    global _model, _device
    _model = WhisperModel(config.ASR_MODEL, device=device_name, compute_type=compute_type)
    _device = device_name
    return _model


def _run(model, wav_path, language):
    start = time.perf_counter()

    segments, info = model.transcribe(
        str(wav_path),
        beam_size=5,
        language=language,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
    )

    # transcribe() is lazy, so the work (and any GPU failure) happens in this loop
    out = [
        {
            "start_s": round(s.start, 2),
            "end_s": round(s.end, 2),
            "text": s.text.strip(),
            "avg_logprob": round(s.avg_logprob, 3),
        }
        for s in segments
        if s.text.strip()
    ]

    return out, info.language, int((time.perf_counter() - start) * 1000)
