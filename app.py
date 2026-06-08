"""
app.py
────────────────────────────────────────────────────────────────────────────
Gradio front-end for the Mandarin Pronunciation Evaluator.

Input accepts either Hanzi (你好) or pinyin (ni3 hao3 / nǐ hǎo).
Output always shows both the Hanzi and pinyin representations.
"""

import gradio as gr

from core.evaluator  import evaluate_pronunciation
from core.pinyin_parser import is_hanzi_input


# ── Tone display labels ───────────────────────────────────────────────────────
_TONE_LABEL = {
    1: "1 ─ (flat)",
    2: "2 ╱ (rising)",
    3: "3 ╰╮ (dip-rise)",
    4: "4 ╲ (falling)",
    5: "5 · (neutral)",
    0: "? (undetected)",
}


def _count_syllables(text: str) -> int:
    """
    Count expected syllables regardless of input mode.
    Hanzi:  count CJK characters.
    Pinyin: count space-separated tokens.
    """
    if is_hanzi_input(text):
        return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    else:
        return len(text.strip().split())


def process(target_text: str, audio_path: str) -> str:
    # ── Input validation ──────────────────────────────────────────────────────
    if not target_text or not target_text.strip():
        return "⚠️  Please enter a target word in Hanzi (你好) or pinyin (ni3 hao3)."

    if not audio_path:
        return "⚠️  Please upload or record an audio file."

    n = _count_syllables(target_text)
    if n == 0:
        return "⚠️  Could not detect any syllables. Use Hanzi or space-separated pinyin."
    if n > 4:
        return "⚠️  Maximum supported length is 4 syllables."

    # ── Evaluate ──────────────────────────────────────────────────────────────
    result = evaluate_pronunciation(target_text, audio_path)
    if result["error"]:
        return f"⚠️  {result['error']}"

    # ── Build report ──────────────────────────────────────────────────────────
    mode = result["input_mode"]
    lines = []

    # ── Target representation ─────────────────────────────────────────────────
    if mode == "hanzi":
        lines.append(f"🎯  TARGET  │  Hanzi: {result['target_hanzi']}  │  Pinyin: {result['target_pinyin']}")
    else:
        lines.append(f"🎯  TARGET  │  Pinyin: {result['target_pinyin']}  (pinyin input mode)")

    # ── Whisper output ────────────────────────────────────────────────────────
    w_hanzi  = result["transcription"]        or "(nothing heard)"
    w_pinyin = result["transcription_pinyin"] or "—"
    lines.append(f"🗣️  WHISPER  │  Hanzi: {w_hanzi}  │  Pinyin: {w_pinyin}")
    lines.append(f"🔤  TEXT MATCH  │  Similarity: {result['similarity_score']}%")
    lines.append("")

    # ── Per-character results ─────────────────────────────────────────────────
    lines.append("── PER-SYLLABLE RESULTS ───────────────────────────────────────")
    for r in result["character_results"]:
        # Label: show hanzi + pinyin if available, else just pinyin
        if r["char"]:
            label = f"{r['char']} ({r['pinyin']})"
        else:
            label = f"({r['pinyin']})"

        sandhi = ""
        if r["written_tone"] != r["spoken_tone"]:
            sandhi = f"  [sandhi: written T{r['written_tone']} → spoken T{r['spoken_tone']}]"

        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        lines.append(
            f"  {label:<14} "
            f"Expected: Tone {_TONE_LABEL[r['spoken_tone']]}{sandhi}  │  "
            f"Detected: Tone {_TONE_LABEL[r['detected_tone']]}  │  {status}"
        )

    # ── Summary scores ────────────────────────────────────────────────────────
    lines.append("")
    lines.append("── SCORES ─────────────────────────────────────────────────────")
    lines.append(f"  Tone Accuracy  │  {result['tone_accuracy']}%")
    lines.append(f"  Overall Score  │  {result['overall_score']} / 100")

    return "\n".join(lines)


# ── Gradio layout ─────────────────────────────────────────────────────────────
_INSTRUCTIONS = """
## 🇨🇳 Mandarin Pronunciation Evaluator

**Supports 1–4 syllables.  Input can be Hanzi or pinyin.**

| Input mode | Example |
|---|---|
| Hanzi | `你好` |
| Pinyin (numeric tones) | `ni3 hao3` |
| Pinyin (diacritic tones) | `nǐ hǎo` |

**How to speak:** insert a short pause (~200 ms) between each syllable.
> 你 … 好 &emsp; ni3 … hao3 &emsp; 谢 … 谢

*Fully local — no cloud APIs.*
"""

with gr.Blocks(title="Mandarin Evaluator") as demo:
    gr.Markdown(_INSTRUCTIONS)

    with gr.Row():
        text_input = gr.Textbox(
            label="Target (Hanzi or pinyin)",
            placeholder="e.g.  你好   or   ni3 hao3",
            value="你好",
            max_lines=1,
        )
        audio_input = gr.Audio(
            label="Your Pronunciation (.wav / .mp3)",
            sources=["upload", "microphone"],
            type="filepath",
        )

    submit_btn = gr.Button("Evaluate", variant="primary")
    output_display = gr.Textbox(label="Evaluation Report", lines=16)

    submit_btn.click(
        fn=process,
        inputs=[text_input, audio_input],
        outputs=output_display,
    )

if __name__ == "__main__":
    demo.launch()