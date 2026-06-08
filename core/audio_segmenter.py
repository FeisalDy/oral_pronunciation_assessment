"""
core/audio_segmenter.py
────────────────────────────────────────────────────────────────────────────
Splits a spoken audio file into per-syllable chunks using silence detection.

Design decisions
----------------
* pydub is used for silence detection because it is pure-Python, has no
  native dependencies beyond ffmpeg/libav (already required by Whisper),
  and its split_on_silence API is simple and readable.

* librosa / webrtcvad were considered but add extra complexity (VAD tuning,
  frame-level iteration) that is unnecessary for the ≤ 4-syllable MVP scope.

* Users are instructed to pause 100–300 ms between syllables.  We therefore
  set min_silence_len=150 ms and silence_thresh=-40 dBFS as sensible defaults
  that tolerate realistic microphone noise floors without over-splitting.

* keep_silence=100 ms is appended at each boundary so that the onset and
  offset of each syllable are preserved for accurate F0 estimation.

* Segments shorter than 80 ms are discarded as noise / breath artefacts.

Public API
----------
split_audio_by_silence(audio_path, min_silence_len, silence_thresh, keep_silence)
    → list[pydub.AudioSegment]
"""

import io
from typing import List

from pydub import AudioSegment
from pydub.silence import split_on_silence


# Minimum voiced-segment duration to be counted as a real syllable (ms)
_MIN_SEGMENT_MS = 80


def split_audio_by_silence(
    audio_path: str,
    min_silence_len: int = 150,
    silence_thresh: int = -40,
    keep_silence: int = 100,
) -> List[AudioSegment]:
    """
    Parameters
    ----------
    audio_path      : path to a .wav or .mp3 file
    min_silence_len : minimum gap (ms) treated as a syllable boundary
    silence_thresh  : dBFS level below which audio is considered silence
    keep_silence    : ms of silence retained at each segment boundary

    Returns
    -------
    List of AudioSegment objects, one per detected syllable, in order.
    Returns an empty list if the file contains no voiced content.
    """
    audio = AudioSegment.from_file(audio_path)

    # Normalise to mono so that pitch analysis works on a single channel
    audio = audio.set_channels(1)

    raw_segments = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=silence_thresh,
        keep_silence=keep_silence,
    )

    # Discard very short artefacts
    segments = [s for s in raw_segments if len(s) >= _MIN_SEGMENT_MS]

    return segments


def segment_to_wav_bytes(segment: AudioSegment) -> bytes:
    """
    Helper: export a pydub AudioSegment to raw WAV bytes so that
    parselmouth.Sound can load it from a buffer.
    """
    buf = io.BytesIO()
    segment.export(buf, format="wav")
    buf.seek(0)
    return buf.read()
