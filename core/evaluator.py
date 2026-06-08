"""
core/evaluator.py
────────────────────────────────────────────────────────────────────────────
Central evaluation service.  app.py calls only this module.

Supports two input modes
------------------------
Hanzi mode  – target_text contains Hanzi (e.g. "你好")
Pinyin mode – target_text contains pinyin  (e.g. "ni3 hao3" or "nǐ hǎo")

Text-similarity comparison
--------------------------
Hanzi mode  → compare Whisper output (hanzi) against target hanzi string
Pinyin mode → convert Whisper output to tone3 pinyin, compare against
              normalised target pinyin string.
              This avoids the need for a lossy pinyin→hanzi reverse lookup.

Return value
------------
{
    "input_mode":        "hanzi" | "pinyin",
    "target_hanzi":      str | None,     # None in pinyin mode
    "target_pinyin":     str,            # always set; space-separated tone3
    "transcription":     str,            # Whisper raw output (hanzi)
    "transcription_pinyin": str,         # Whisper output converted to pinyin
    "similarity_score":  int,            # 0–100
    "character_results": list,
    "tone_accuracy":     float,
    "overall_score":     float,
    "error":             str | None,
}
"""

from __future__ import annotations

from typing import Any, Dict, List

from rapidfuzz import fuzz

from core.pinyin_parser   import (get_metadata, hanzi_to_pinyin_str,
                                   is_hanzi_input)
from core.tone_sandhi     import apply_tone_sandhi
from core.transcriber     import transcribe_audio
from core.audio_segmenter import split_audio_by_silence, segment_to_wav_bytes
from core.pitch_tracker   import analyze_segment_tone


_TEXT_WEIGHT       = 0.4
_TONE_WEIGHT       = 0.6
_TEXT_PASS_THRESHOLD = 80


def evaluate_pronunciation(
    target_text: str,
    audio_path: str,
) -> Dict[str, Any]:
    """Evaluate pronunciation and return a structured result dict."""

    # ── Step 1 & 2: Parse + Sandhi ────────────────────────────────────────────
    raw_metadata, input_mode = get_metadata(target_text)
    if not raw_metadata:
        return _error_result("Could not parse the input text.")

    metadata   = apply_tone_sandhi(raw_metadata)
    n_chars    = len(metadata)

    # Compute canonical pinyin string for the target (always available)
    target_pinyin = " ".join(
        f"{e['pinyin']}{e['written_tone']}" for e in raw_metadata
    )
    target_hanzi = target_text.strip() if input_mode == "hanzi" else None

    # ── Step 3: Whisper transcription ─────────────────────────────────────────
    whisper_hanzi   = transcribe_audio(audio_path)
    whisper_pinyin  = hanzi_to_pinyin_str(whisper_hanzi) if whisper_hanzi else ""

    # Similarity: compare in the same domain as the input
    if input_mode == "hanzi":
        similarity_score = int(fuzz.ratio(whisper_hanzi, target_text.strip()))
    else:
        # Normalize target pinyin (lowercase, single spaces) then compare
        target_py_norm = " ".join(target_pinyin.lower().split())
        similarity_score = int(fuzz.ratio(whisper_pinyin, target_py_norm))

    # ── Step 4: Segmentation ──────────────────────────────────────────────────
    try:
        segments = split_audio_by_silence(audio_path)
    except Exception as exc:
        return _error_result(f"Audio segmentation failed: {exc}")

    # ── Step 5: Segment count validation ─────────────────────────────────────
    if len(segments) != n_chars:
        msg = (
            f"Expected {n_chars} syllable(s) but detected {len(segments)} "
            f"speech segment(s).\n\n"
            f"Please pause briefly between each character when speaking."
        )
        return _error_result(msg)

    # ── Step 6 & 7: Per-segment tone detection + evaluation ───────────────────
    character_results: List[Dict[str, Any]] = []
    correct_tones = 0

    for entry, segment in zip(metadata, segments):
        wav_bytes     = segment_to_wav_bytes(segment)
        detected_tone = analyze_segment_tone(wav_bytes)
        expected_tone = entry["spoken_tone"]
        passed        = detected_tone == expected_tone
        if passed:
            correct_tones += 1

        character_results.append({
            "char":          entry["char"],          # None in pinyin mode
            "pinyin":        entry["pinyin"],
            "written_tone":  entry["written_tone"],
            "spoken_tone":   expected_tone,
            "detected_tone": detected_tone,
            "passed":        passed,
        })

    # ── Step 8: Scores ────────────────────────────────────────────────────────
    tone_accuracy = (correct_tones / n_chars) * 100 if n_chars else 0.0
    overall_score = round(
        _TEXT_WEIGHT * similarity_score + _TONE_WEIGHT * tone_accuracy, 1
    )

    return {
        "input_mode":           input_mode,
        "target_hanzi":         target_hanzi,
        "target_pinyin":        target_pinyin,
        "transcription":        whisper_hanzi,
        "transcription_pinyin": whisper_pinyin,
        "similarity_score":     similarity_score,
        "character_results":    character_results,
        "tone_accuracy":        round(tone_accuracy, 1),
        "overall_score":        overall_score,
        "error":                None,
    }


def _error_result(message: str) -> Dict[str, Any]:
    return {
        "input_mode":           "unknown",
        "target_hanzi":         None,
        "target_pinyin":        "",
        "transcription":        "",
        "transcription_pinyin": "",
        "similarity_score":     0,
        "character_results":    [],
        "tone_accuracy":        0.0,
        "overall_score":        0.0,
        "error":                message,
    }