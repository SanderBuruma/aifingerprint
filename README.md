# ailint

Scores text 0–100 for AI writing fingerprints. Analyzes vocabulary, sentence rhythm, tone, compression similarity, punctuation diversity, and more to detect machine-generated prose.

## Installation

```bash
pip install .
# or for development:
pip install -e .
```

## Usage

```bash
# Analyze a file
ailint input.txt

# Read from clipboard
ailint --clipboard

# Read from stdin
echo "text to analyze" | ailint

# Generate a markdown report
ailint input.txt --report
ailint input.txt --report output.md
```

## Score interpretation

| Score | Label | Meaning |
|-------|-------|---------|
| 0–20 | CLEAN | No significant AI patterns detected |
| 21–40 | MILD | Minor AI-like traits, likely human |
| 41–60 | NOTICEABLE | Clear AI patterns present |
| 61–80 | OBVIOUS | Strong AI fingerprint |
| 81–100 | BLATANT | Almost certainly AI-generated |

## What it checks

Ten weighted checks, each scoring 0.0–1.0:

| Check | Weight | What it measures |
|-------|--------|-----------------|
| Compression | 20% | LZMA similarity to a known AI corpus |
| Sentence rhythm | 15% | Coefficient of variation in sentence lengths |
| Tone | 15% | Hedging, enthusiasm, formality, word length |
| Punctuation | 12% | Shannon entropy of punctuation distribution |
| Connectives | 10% | Density of discourse markers (however, moreover...) |
| Burstiness | 8% | Whether content words cluster or distribute evenly |
| Vocabulary | 8% | Known AI-favored words (delve, leverage, utilize...) |
| Structure | 7% | Paragraph uniformity, parallelism, five-paragraph essay |
| Phrases | 5% | Cliches, hedges, openers, closers |
| Formatting | 0% | Em dashes, bold bullets, header density (disabled) |

## HTML reports

Generate a markdown report, then convert to styled HTML:

```bash
ailint input.txt --report
python -m ailint.html report.md
```

## No dependencies

Runs on Python 3.10+ using only the standard library.
