"""Discourse connective density — however, moreover, furthermore, etc."""

import re

from guardrails.patterns import DISCOURSE_CONNECTIVES
from guardrails.text import split_sentences

DENSITY_HIGH = 0.5  # connectives per sentence
DENSITY_MODERATE = 0.25
SCORE_FLOOR = 0.1
SCORE_RANGE = 0.5


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """AI overuses discourse connectives like however, moreover, furthermore."""
    hits = []
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return hits, 0.0

    words = re.findall(r"\b[a-z]+\b", text.lower())
    count = sum(1 for w in words if w in DISCOURSE_CONNECTIVES)
    density = count / len(sentences)

    if density > DENSITY_HIGH:
        found = [w for w in words if w in DISCOURSE_CONNECTIVES]
        unique_found = list(dict.fromkeys(found))[:5]
        hits.append(
            f"  Connective density: {density:.2f}/sentence (high) "
            f"— {', '.join(unique_found)}"
        )
    elif density > DENSITY_MODERATE:
        found = [w for w in words if w in DISCOURSE_CONNECTIVES]
        unique_found = list(dict.fromkeys(found))[:5]
        hits.append(
            f"  Connective density: {density:.2f}/sentence (moderate) "
            f"— {', '.join(unique_found)}"
        )

    raw = max(0.0, min(1.0, (density - SCORE_FLOOR) / SCORE_RANGE))
    return hits, raw
