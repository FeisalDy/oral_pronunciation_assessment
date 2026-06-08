# Mandarin Pronunciation Evaluator

A fully local Mandarin pronunciation assessment tool built with Gradio, Faster-Whisper, and Parselmouth.

The application evaluates:

* Text accuracy (what Whisper hears)
* Tone accuracy (per syllable)
* Basic Mandarin tone sandhi rules
* Hanzi and Pinyin input

## Features

* Supports **1–4 syllables**
* Accepts **Hanzi** input
* Accepts **Pinyin with tone numbers**
* Accepts **Pinyin with tone marks**
* Per-syllable tone evaluation
* Local speech transcription using Faster-Whisper
* Local pitch analysis using Parselmouth
* No cloud APIs

## Supported Input Formats

### Hanzi

```text
你好
谢谢
中国人
```

### Pinyin (Tone Numbers)

```text
ni3 hao3
xie4 xie5
zhong1 guo2 ren2
```

### Pinyin (Tone Marks)

```text
nǐ hǎo
xiè xie
zhōng guó rén
```

## Tone Sandhi Support

The evaluator applies common Mandarin pronunciation rules before scoring.

### Third Tone + Third Tone

```text
你好

Written:
ni3 hao3

Spoken:
ni2 hao3
```

### 不 Tone Sandhi

```text
不用

Written:
bu4 yong4

Spoken:
bu2 yong4
```

### 一 Tone Sandhi

```text
一个

Written:
yi1 ge4

Spoken:
yi2 ge4
```

### Neutral Tone

```text
妈妈

ma1 ma5
```

## How To Speak

For best results, insert a short pause between syllables.

Example:

```text
你 ... 好
谢 ... 谢
中 ... 国 ... 人
```

Recommended pause:

```text
100–300 ms
```

This helps the evaluator separate syllables for individual tone analysis.

## Example Output

```text
🎯 TARGET │ Hanzi: 你好 │ Pinyin: ni3 hao3

🗣️ WHISPER │ Hanzi: 你好 │ Pinyin: ni3 hao3

🔤 TEXT MATCH │ Similarity: 100%

── PER-SYLLABLE RESULTS ──────────────────────

你 (ni)
Expected: Tone 2
Detected: Tone 2
PASS

好 (hao)
Expected: Tone 3
Detected: Tone 3
PASS

── SCORES ────────────────────────────────────

Tone Accuracy │ 100%
Overall Score │ 100 / 100
```

## Limitations

This project is intentionally lightweight and does not perform:

* Forced alignment
* Phoneme-level scoring
* Initial/final pronunciation scoring
* Native-speaker pronunciation grading
* Long sentence evaluation

Maximum supported length is currently:

```text
4 syllables
```

## Installation

```bash
git clone https://github.com/FeisalDy/oral_pronunciation_assessment
cd oral_pronunciation_assessment

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open the local Gradio URL in your browser.

## Technology Stack

* Gradio
* Faster-Whisper
* Parselmouth (Praat)
* PyPinyin****
* RapidFuzz

## Project Goal

This project focuses on providing a simple local Mandarin pronunciation evaluator for learners, emphasizing tone accuracy rather than full phonetic assessment.
****