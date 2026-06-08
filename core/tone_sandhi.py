"""
core/tone_sandhi.py
────────────────────────────────────────────────────────────────────────────
Applies Mandarin tone-sandhi rules and adds 'spoken_tone' to each metadata
entry.  Works in both input modes:

  Hanzi mode  – entry['char'] contains the character  (e.g. '不')
  Pinyin mode – entry['char'] is None; rules fall back to entry['pinyin']

Rules implemented
-----------------
1. Third-Tone Sandhi  – tone 3 before tone 3 → first syllable becomes tone 2
2. 不 (bù) Sandhi     – 不 / "bu" (T4) before T4 → spoken tone 2
3. 一 (yī) Sandhi     – 一 / "yi" (T1):
                          before T4          → spoken tone 2
                          before T1/2/3/5    → spoken tone 4
4. Neutral Tone       – written_tone 5 propagates unchanged
"""

from typing import Any, Dict, List


def apply_tone_sandhi(metadata: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Input:  list from pinyin_parser (get_pinyin_metadata or parse_pinyin_input)
    Output: same structure, each entry augmented with 'spoken_tone'.

    The input list is NOT mutated; a new list of new dicts is returned.
    """
    result = [dict(entry) for entry in metadata]
    for entry in result:
        entry["spoken_tone"] = entry["written_tone"]   # baseline

    n = len(result)

    for i in range(n):
        char        = result[i].get("char") or ""   # "" when char is None
        py          = result[i]["pinyin"].lower()
        spoken_tone = result[i]["spoken_tone"]
        next_tone   = result[i + 1]["spoken_tone"] if i + 1 < n else None

        # Rule 4: neutral tone is inert
        if spoken_tone == 5:
            continue

        # Rule 1: Third-Tone Sandhi
        if spoken_tone == 3 and next_tone == 3:
            result[i]["spoken_tone"] = 2
            continue

        # Rule 2: 不 sandhi — match by char OR by pinyin "bu" + T4
        is_bu = (char == "不") or (not char and py == "bu")
        if is_bu and spoken_tone == 4 and next_tone == 4:
            result[i]["spoken_tone"] = 2
            continue

        # Rule 3: 一 sandhi — match by char OR by pinyin "yi" + T1
        is_yi = (char == "一") or (not char and py == "yi")
        if is_yi and spoken_tone == 1:
            if next_tone is None:
                pass                                  # standalone 一 → keep T1
            elif next_tone == 4:
                result[i]["spoken_tone"] = 2          # 一个 yi2 ge4
            else:
                result[i]["spoken_tone"] = 4          # 一天 yi4 tian1
            continue

    return result