import wave

import numpy as np

MIN_HZ = 70
MAX_HZ = 300
FRAME_S = 0.04
PAUSE_S = 0.7


def assign(segments, wav_path):
    if not segments:
        return segments

    try:
        signal, rate = _read_wav(wav_path)
    except Exception:
        return alternate(segments)

    pitches = [_pitch_of(signal, rate, s["start_s"], s["end_s"]) for s in segments]
    voiced = [p for p in pitches if p is not None]
    if len(voiced) < 2:
        return alternate(segments)

    boundary = _split_point(voiced)
    low_is_doctor = voiced[0] < boundary

    speaker = "doctor"
    for seg, pitch in zip(segments, pitches):
        if pitch is not None:
            speaker = "doctor" if (pitch < boundary) == low_is_doctor else "patient"
        seg["speaker"] = speaker
    return segments


def _read_wav(path):
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0, rate


def _pitch_of(signal, rate, start_s, end_s):
    clip = signal[int(start_s * rate):int(end_s * rate)]
    step = int(FRAME_S * rate)
    if clip.size < step:
        return None

    pitches = [_frame_pitch(clip[i:i + step], rate) for i in range(0, clip.size - step, step)]
    voiced = [p for p in pitches if p is not None]
    return float(np.median(voiced)) if voiced else None


def _frame_pitch(frame, rate):
    frame = frame - frame.mean()
    if np.sqrt((frame ** 2).mean()) < 0.01:
        return None

    corr = np.correlate(frame, frame, mode="full")[frame.size - 1:]
    lo, hi = rate // MAX_HZ, rate // MIN_HZ
    if hi >= corr.size:
        return None

    window = corr[lo:hi]
    if window.size == 0 or window.max() <= 0:
        return None
    return rate / (int(np.argmax(window)) + lo)


def _split_point(values):
    # 1-D k-means with k=2, seeded at the extremes
    c0, c1 = min(values), max(values)
    for _ in range(20):
        low = [v for v in values if abs(v - c0) <= abs(v - c1)]
        high = [v for v in values if abs(v - c0) > abs(v - c1)]
        if not low or not high:
            break
        moved0, moved1 = sum(low) / len(low), sum(high) / len(high)
        if abs(moved0 - c0) < 1e-6 and abs(moved1 - c1) < 1e-6:
            break
        c0, c1 = moved0, moved1
    return (c0 + c1) / 2


def alternate(segments):
    # used when there is no audio to analyse: flip speaker on every long pause
    speaker = "doctor"
    prev_end = None
    for seg in segments:
        if prev_end is not None and seg["start_s"] - prev_end > PAUSE_S:
            speaker = "patient" if speaker == "doctor" else "doctor"
        seg["speaker"] = speaker
        prev_end = seg["end_s"]
    return segments
