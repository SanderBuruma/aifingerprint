"""Discourse connective density — however, moreover, furthermore, etc."""

import re

from aifingerprint.patterns import DISCOURSE_CONNECTIVES
from aifingerprint.text import split_sentences

# Per-100-words thresholds (normalizes properly across text lengths)
DENSITY_HIGH = 3.0
DENSITY_MODERATE = 1.5
SCORE_FLOOR = 0.5
SCORE_RANGE = 3.0


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """AI overuses discourse connectives like however, moreover, furthermore."""
    hits = []
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return hits, 0.0

    words = re.findall(r"\b[a-z]+\b", text.lower())
    if not words:
        return hits, 0.0
    count = sum(1 for w in words if w in DISCOURSE_CONNECTIVES)
    density = count / (len(words) / 100)

    if density > DENSITY_HIGH:
        found = [w for w in words if w in DISCOURSE_CONNECTIVES]
        unique_found = list(dict.fromkeys(found))[:5]
        hits.append(
            f"  Connective density: {density:.1f} per 100 words (high) "
            f"— {', '.join(unique_found)}"
        )
    elif density > DENSITY_MODERATE:
        found = [w for w in words if w in DISCOURSE_CONNECTIVES]
        unique_found = list(dict.fromkeys(found))[:5]
        hits.append(
            f"  Connective density: {density:.1f} per 100 words (moderate) "
            f"— {', '.join(unique_found)}"
        )

    raw = max(0.0, min(1.0, (density - SCORE_FLOOR) / SCORE_RANGE))
    return hits, raw
