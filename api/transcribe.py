"""
Local speech-to-text via faster-whisper. No API keys, no network.

The model loads lazily on the first call (~5 sec for the `base` model on CPU,
plus a one-time ~145 MB download). Subsequent calls are fast.

Env vars:
    WHISPER_MODEL    - tiny | base | small | medium | large (default: base)
    WHISPER_COMPUTE  - int8 | float16 | float32 (default: int8 — best CPU perf)
"""

from __future__ import annotations

import io
import os
import threading

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            size = os.environ.get("WHISPER_MODEL", "base")
            compute = os.environ.get("WHISPER_COMPUTE", "int8")
            _model = WhisperModel(size, device="cpu", compute_type=compute)
    return _model


def transcribe(audio_bytes: bytes) -> tuple[str, str, float]:
    """Transcribe audio bytes (any format PyAV reads — Telegram voice notes are .ogg/Opus).

    Returns (text, detected_language_iso2, language_probability).
    Empty audio or pure silence returns ("", "", 0.0).
    """
    if not audio_bytes:
        return "", "", 0.0
    model = _get_model()
    buf = io.BytesIO(audio_bytes)
    segments, info = model.transcribe(
        buf,
        beam_size=1,
        vad_filter=True,  # skip leading/trailing silence
    )
    text = "".join(seg.text for seg in segments).strip()
    return text, (info.language or ""), float(info.language_probability or 0.0)
