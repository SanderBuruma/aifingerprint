"""Punctuation diversity — Shannon entropy of punctuation distribution."""

import math
from collections import Counter

_PUNCT_CHARS = set('.,;:!?\u2014\u2013-()"\u201c\u201d\'\u2018\u2019')

ENTROPY_VERY_LOW = 0.30
ENTROPY_LOW = 0.45
NORM_FLOOR = 0.20  # Below this → max score
NORM_CEILING = 0.60  # Above this → zero score


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """AI uses a narrow range of punctuation. Measure entropy of punct distribution."""
    hits = []
    punct = [ch for ch in text if ch in _PUNCT_CHARS]
    if len(punct) < 10:
        return hits, 0.0

    freqs = Counter(punct)
    total = len(punct)
    entropy = -sum((c / total) * math.log2(c / total) for c in freqs.values())
    # Normalize against a reasonable baseline (6 types = typical human diversity),
    # not the full 15-char set which no text ever fully uses.
    baseline_types = min(len(_PUNCT_CHARS), max(len(freqs) + 2, 6))
    max_entropy = math.log2(baseline_types)
    normalized = entropy / max_entropy if max_entropy > 0 else 0

    if normalized < ENTROPY_VERY_LOW:
        hits.append(
            f"  Punctuation diversity: entropy={entropy:.2f} (very low) "
            f"— almost only commas and periods"
        )
    elif normalized < ENTROPY_LOW:
        hits.append(
            f"  Punctuation diversity: entropy={entropy:.2f} (low) "
            f"— limited punctuation variety"
        )

    raw = max(0.0, min(1.0, (NORM_CEILING - normalized) / (NORM_CEILING - NORM_FLOOR)))
    return hits, raw
