# aifingerprint

[![PyPI](https://img.shields.io/pypi/v/aifingerprint)](https://pypi.org/project/aifingerprint/)

Scores text 0–100 for AI writing fingerprints. Catches the stuff LLMs can't help doing — flat rhythm, hedge words, compression patterns, that weird punctuation sameness. No API keys, no model downloads, just stdlib Python.

## Installation

```bash
pip install aifingerprint
```

## Usage

```bash
# Analyze a file
aifingerprint input.txt

# Read from clipboard
aifingerprint --clipboard

# Read from stdin
echo "text to analyze" | aifingerprint

# Generate a markdown report
aifingerprint input.txt --report
aifingerprint input.txt --report output.md
```

## Score interpretation

| Score | Label | Meaning |
|-------|-------|---------|
| 0–20 | CLEAN | Looks human |
| 21–40 | MILD | A few AI-ish traits, probably human |
| 41–60 | NOTICEABLE | Smells like AI |
| 61–80 | OBVIOUS | Yeah, that's AI |
| 81–100 | BLATANT | Copy-pasted straight from ChatGPT |

## What it checks

Ten weighted checks, each scoring 0.0–1.0:

| Check | Weight | What it measures |
|-------|--------|-----------------|
| Compression | 20% | How much the text resembles known AI writing when compressed (uses LZMA, a zip-like algorithm — similar text compresses well together) |
| Sentence rhythm | 15% | Whether sentences are all roughly the same length (humans vary more) |
| Tone | 15% | Hedging, enthusiasm, formality, word length |
| Punctuation | 12% | Whether punctuation is suspiciously samey (humans use messier, more varied punctuation) |
| Connectives | 10% | Overuse of transition words like "however", "moreover", "furthermore" |
| Burstiness | 8% | Whether key words are spread too evenly (humans tend to clump related words together) |
| Vocabulary | 8% | Known AI-favorite words (delve, leverage, utilize...) |
| Structure | 7% | Cookie-cutter paragraph shapes, repetitive sentence patterns, five-paragraph essay format |
| Phrases | 5% | Cliches, hedges, stock openers and closers |
| Formatting | 0% | Em dashes, bold bullets, header density (disabled) |

## HTML reports

Generate a markdown report, then convert to styled HTML:

```bash
aifingerprint input.txt --report
python -m aifingerprint.html report.md
```

## How it compares

We tested against **RoBERTa** (a machine-learning model OpenAI released in 2019 to detect AI writing, available as `openai-community/roberta-base-openai-detector` on HuggingFace) — the only other pip-installable detector that runs offline on prose. 27 samples, 8 AI-generated, 19 human-written:

| | aifingerprint | RoBERTa |
|---|---|---|
| AI samples (avg) | **53%** | 97% |
| Human samples (avg) | **15%** | 97% |
| Separation | **38 percentage points** | ~0 — labels everything as AI |

RoBERTa was trained on GPT-2 output back in 2019. It thinks Paul Graham, Reddit posts, and Seth Godin are all 100% AI. Basically useless on anything written after 2022. aifingerprint uses pattern-matching rules instead of a trained model, so it doesn't go stale when the next GPT drops.

Other packages in this space:

| Package | Why it doesn't work |
|---------|-------------------|
| [gptzero](https://github.com/Haste171/gptzero/) | API wrapper — requires paid GPTZero API key |
| [openai-detector](https://github.com/promptslab/openai-detector) | Thin wrapper around the same broken RoBERTa model |
| [sloppylint](https://github.com/rsionnach/sloppylint) | Detects AI patterns in code, not prose |
| [finbert-ai-detector](https://huggingface.co/msperlin/finbert-ai-detector) | Fine-tuned for financial documents only |
| [ai-slop-detector](https://github.com/flamehaven/ai-slop-detector) | Browser-based, requires Gemma 270M model download |
| [textstat](https://github.com/textstat/textstat) | Readability metrics (Flesch, SMOG, etc.) — doesn't attempt detection |

## No dependencies

Runs on Python 3.10+ using only the standard library.
