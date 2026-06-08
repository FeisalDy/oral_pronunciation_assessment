"""
core/pinyin_parser.py
────────────────────────────────────────────────────────────────────────────
Handles both Hanzi and pinyin text input.

Input modes
-----------
Hanzi mode  – "你好"         (any text containing CJK characters)
Pinyin mode – "ni3 hao3"    (numeric tone: ni3, hao3)
              "nǐ hǎo"      (diacritic tone: auto-converted via to_tone3)
              Tokens are space-separated; one token per syllable.

Public API
----------
is_hanzi_input(text) → bool
get_pinyin_metadata(text) → list   # Hanzi mode (original behaviour)
parse_pinyin_input(text) → list    # Pinyin mode
hanzi_to_pinyin_str(text) → str    # "你好" → "ni3 hao3"  (for display)
get_metadata(text) → (list, str)   # auto-routes; returns (metadata, mode)
                                   # mode ∈ {"hanzi", "pinyin"}
"""

import re

from pypinyin import pinyin, lazy_pinyin, Style
from pypinyin.contrib.tone_convert import to_tone3


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_hanzi_input(text: str) -> bool:
    """Return True if text contains at least one CJK character."""
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def hanzi_to_pinyin_str(text: str) -> str:
    """
    Convert a Hanzi string to a space-separated tone3 pinyin string.
    "你好" → "ni3 hao3"
    Used for display and for converting Whisper output during comparison.
    """
    parts = lazy_pinyin(text.strip(), style=Style.TONE3, neutral_tone_with_five=True)
    return " ".join(parts)


# ── Hanzi mode ────────────────────────────────────────────────────────────────

def get_pinyin_metadata(text: str) -> list:
    """
    Converts Hanzi to pinyin metadata.

    Input:  "你好"
    Output: [
        {'char': '你', 'pinyin': 'ni',  'written_tone': 3},
        {'char': '好', 'pinyin': 'hao', 'written_tone': 3},
    ]
    """
    clean_text = text.strip()
    pinyin_tones = pinyin(clean_text, style=Style.TONE3, neutral_tone_with_five=True)

    metadata = []
    for char, py_list in zip(clean_text, pinyin_tones):
        py_raw = py_list[0]
        if py_raw == char:          # punctuation / space echoed back
            continue
        if py_raw[-1].isdigit():
            tone     = int(py_raw[-1])
            py_alpha = py_raw[:-1]
        else:
            tone     = 5
            py_alpha = py_raw
        metadata.append({"char": char, "pinyin": py_alpha, "written_tone": tone})

    return metadata


# ── Pinyin mode ───────────────────────────────────────────────────────────────

_TONE3_RE = re.compile(r"^([a-züÜ]+)([1-5]?)$", re.IGNORECASE)


def parse_pinyin_input(text: str) -> list:
    """
    Parse a space-separated pinyin string into metadata.

    Accepts:
        "ni3 hao3"   – numeric tones
        "nǐ hǎo"     – diacritic tones (converted via pypinyin)
        Mixed is not supported; prefer numeric for clarity.

    Output: [
        {'char': None, 'pinyin': 'ni',  'written_tone': 3},
        {'char': None, 'pinyin': 'hao', 'written_tone': 3},
    ]

    'char' is None because there is no unambiguous single Hanzi for a given
    pinyin syllable — the Whisper output will provide the hanzi form.
    """
    tokens = text.strip().lower().split()
    metadata = []

    for raw_token in tokens:
        # Convert diacritics → numeric if needed  (nǐ → ni3)
        token = to_tone3(raw_token)

        m = _TONE3_RE.match(token)
        if not m:
            # Skip unparseable tokens (punctuation etc.)
            continue

        py_alpha = m.group(1).lower()
        tone_str = m.group(2)
        tone     = int(tone_str) if tone_str else 5   # no digit → neutral

        metadata.append({"char": None, "pinyin": py_alpha, "written_tone": tone})

    return metadata


# ── Auto-routing entry point ──────────────────────────────────────────────────

def get_metadata(text: str):
    """
    Detect input type and return (metadata_list, mode_str).

    mode_str ∈ {"hanzi", "pinyin"}
    """
    if is_hanzi_input(text):
        return get_pinyin_metadata(text), "hanzi"
    else:
        return parse_pinyin_input(text), "pinyin"