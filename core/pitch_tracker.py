# """
# core/pitch_tracker.py
# ────────────────────────────────────────────────────────────────────────────
# Analyses the F0 (fundamental frequency) contour of a single syllable and
# returns a Mandarin tone integer (1–4) or 0 for unvoiced / ambiguous audio.
#
# Design decisions
# ----------------
# * parselmouth (Praat bindings) is kept as specified.
# * Two entry points are provided:
#     - analyze_voice_tone(audio_path)  – for a file on disk (backward compat)
#     - analyze_segment_tone(wav_bytes) – for in-memory WAV bytes produced by
#       the segmenter, avoiding temporary file I/O.
# * The heuristic thresholds are intentionally simple and match the original
#   implementation.  Improving them is explicitly out of scope for this MVP.
# """
#
# import io
# import tempfile
# import os
#
# import numpy as np
# import parselmouth
#
#
# # ── Heuristic thresholds ──────────────────────────────────────────────────────
# # variance < _FLAT_VAR  → Tone 1 (flat)
# # pitch_diff > _RISE    → Tone 2 (rising)
# # pitch_diff < -_FALL   → Tone 4 (falling)
# # otherwise             → Tone 3 (dip-rise, catch-all for MVP)
# _FLAT_VAR   = 150
# _RISE_DELTA = 15
# _FALL_DELTA = -15
# _MIN_VOICED = 5        # minimum voiced frames required for a reliable estimate
#
# _MAX_NEUTRAL_DURATION = 0.18  # Neutral tones are short (usually under 150-180ms)
# _MIN_NEUTRAL_DROP    = 8.0    # Decibel drop from peak intensity to the end
#
# def _classify_pitch(voiced_points: np.ndarray) -> int:
#     """Core classification logic shared between both public functions."""
#     if len(voiced_points) < _MIN_VOICED:
#         return 0  # too short / silent
#
#     mid = len(voiced_points) // 2
#     start_avg = np.mean(voiced_points[:mid])
#     end_avg   = np.mean(voiced_points[mid:])
#     pitch_diff = end_avg - start_avg
#     variance   = np.var(voiced_points)
#
#     if variance < _FLAT_VAR:
#         return 1
#     elif pitch_diff > _RISE_DELTA:
#         return 2
#     elif pitch_diff < _FALL_DELTA:
#         return 4
#     else:
#         return 3
#
#
# def _extract_voiced(snd: parselmouth.Sound) -> np.ndarray:
#     pitch = snd.to_pitch()
#     values = pitch.selected_array["frequency"]
#     return values[values > 0]
#
#
# # ── Public API ────────────────────────────────────────────────────────────────
#
# def analyze_voice_tone(audio_path: str) -> int:
#     """Analyse a WAV/MP3 file on disk and return the detected tone (1–4 or 0)."""
#     snd = parselmouth.Sound(audio_path)
#     voiced = _extract_voiced(snd)
#     return _classify_pitch(voiced)
#
#
# def analyze_segment_tone(wav_bytes: bytes) -> int:
#     """
#     Analyse an in-memory WAV byte string and return the detected tone.
#
#     parselmouth.Sound does not support BytesIO directly, so we write to a
#     temporary file.  The file is deleted immediately after reading to avoid
#     leaking disk space during batch processing.
#     """
#     with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
#         tmp.write(wav_bytes)
#         tmp_path = tmp.name
#
#     try:
#         snd = parselmouth.Sound(tmp_path)
#         voiced = _extract_voiced(snd)
#         return _classify_pitch(voiced)
#     finally:
#         os.unlink(tmp_path)
import io
import tempfile
import os

import numpy as np
import parselmouth

# ── Heuristic thresholds ──────────────────────────────────────────────────────
_FLAT_VAR = 150
_RISE_DELTA = 15
_FALL_DELTA = -15
_MIN_VOICED = 5

# ── New Tone 5 Thresholds ────────────────────────────────────────────────────
_MAX_NEUTRAL_DURATION = 0.18  # Neutral tones are short (usually under 150-180ms)
_MIN_NEUTRAL_DROP = 8.0  # Decibel drop from peak intensity to the end


def _classify_pitch(pitch_values: np.ndarray, intensities: np.ndarray, total_duration: float) -> int:
    """Core classification logic updated to detect Tone 5."""
    if len(pitch_values) < _MIN_VOICED:
        return 0  # too short / silent

    # 1. Check for Tone 5 (Neutral) based on Duration and Intensity Drop
    if total_duration < _MAX_NEUTRAL_DURATION and len(intensities) > 0:
        peak_intensity = np.max(intensities)
        end_intensity = np.mean(intensities[-3:]) if len(intensities) >= 3 else intensities[-1]

        # If it's brief AND the volume fades out quickly, it's a neutral tone
        if (peak_intensity - end_intensity) > _MIN_NEUTRAL_DROP:
            return 5

    # 2. Classic Tone 1-4 Shape Rules
    mid = len(pitch_values) // 2
    start_avg = np.mean(pitch_values[:mid])
    end_avg = np.mean(pitch_values[mid:])
    pitch_diff = end_avg - start_avg
    variance = np.var(pitch_values)

    if variance < _FLAT_VAR:
        return 1
    elif pitch_diff > _RISE_DELTA:
        return 2
    elif pitch_diff < _FALL_DELTA:
        return 4
    else:
        return 3


def _extract_features(snd: parselmouth.Sound):
    """Helper to safely extract pitch, intensity, and duration data."""
    pitch = snd.to_pitch()
    frequencies = pitch.selected_array["frequency"]
    voiced_pitch = frequencies[frequencies > 0]

    # Extract intensity values for loudness profile
    intensity = snd.to_intensity()
    intensity_values = intensity.values[0]

    # Calculate absolute duration of the sound file
    duration = snd.duration

    return voiced_pitch, intensity_values, duration


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_voice_tone(audio_path: str) -> int:
    """Analyse a WAV/MP3 file on disk and return the detected tone (0–5)."""
    snd = parselmouth.Sound(audio_path)
    voiced, intensities, duration = _extract_features(snd)
    return _classify_pitch(voiced, intensities, duration)


def analyze_segment_tone(wav_bytes: bytes) -> int:
    """Analyse an in-memory WAV byte string and return the detected tone (0–5)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        snd = parselmouth.Sound(tmp_path)
        voiced, intensities, duration = _extract_features(snd)
        return _classify_pitch(voiced, intensities, duration)
    finally:
        os.unlink(tmp_path)