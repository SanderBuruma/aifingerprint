"""Sentence rhythm analysis — coefficient of variation in sentence lengths."""

import math

from aifingerprint.text import split_sentences

# From corpus testing: AI mean CV ~0.45, human ~0.72
CV_VERY_LOW = 0.35
CV_LOW = 0.50
CV_FLOOR = 0.30  # Below this → max score
CV_CEILING = 0.70  # Above this → zero score


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """AI produces sentences of uniform length. Measure coefficient of variation."""
    hits = []
    sentences = split_sentences(text)
    if len(sentences) < 5:
        return hits, 0.0

    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return hits, 0.0
    std_len = math.sqrt(sum((ln - mean_len) ** 2 for ln in lengths) / len(lengths))
    cv = std_len / mean_len

    if cv < CV_VERY_LOW:
        hits.append(
            f"  Sentence rhythm: CV={cv:.2f} (very low) "
            f"— sentence lengths are unnaturally uniform"
        )
    elif cv < CV_LOW:
        hits.append(
            f"  Sentence rhythm: CV={cv:.2f} (low) "
            f"— sentence lengths lack natural variation"
        )

    raw = max(0.0, min(1.0, (CV_CEILING - cv) / (CV_CEILING - CV_FLOOR)))
    return hits, raw
