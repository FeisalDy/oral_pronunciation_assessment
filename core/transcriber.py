"""
core/transcriber.py
────────────────────────────────────────────────────────────────────────────
Thin wrapper around faster-whisper.  The model is initialised once at module
import time so that repeated calls within a session do not reload weights.
"""

from faster_whisper import WhisperModel

print("Initializing Whisper model…")
_model = WhisperModel("tiny", device="cpu", compute_type="int8")


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe a Mandarin audio file and return the raw Chinese character
    string with common trailing punctuation stripped.
    """
    if not audio_path:
        return ""

    segments, _info = _model.transcribe(audio_path, language="zh")
    text = "".join(seg.text for seg in segments)
    return text.strip().replace("。", "").replace("，", "")
