"""Word burstiness — measures how evenly content words are distributed."""

import math
import re

STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "been", "were",
    "they", "their", "there", "which", "would", "could", "should", "about",
    "into", "than", "then", "them", "these", "those", "other", "after",
    "before", "being", "between", "does", "doing", "during", "each",
    "every", "under", "over", "again", "further", "where", "when", "while",
    "also", "just", "more", "most", "some", "such", "only", "very",
    "will", "what", "your", "still",
}

MIN_WORD_LENGTH = 4  # Only track content words longer than this
MIN_OCCURRENCES = 3  # Need 3+ occurrences to measure gaps
MIN_TOTAL_WORDS = 50

BURSTINESS_VERY_LOW = 0.5
BURSTINESS_LOW = 0.7
# Score mapping: burstiness 0.3-1.0 → score 1.0-0.0
SCORE_CEILING = 1.0
SCORE_RANGE = 0.7


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """Human writing clusters topic words; AI distributes them evenly.
    Measure CV of inter-occurrence gaps for content words."""
    hits = []
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if len(words) < MIN_TOTAL_WORDS:
        return hits, 0.0

    positions: dict[str, list[int]] = {}
    for i, w in enumerate(words):
        if len(w) > MIN_WORD_LENGTH and w not in STOPWORDS:
            positions.setdefault(w, []).append(i)

    burstiness_values = []
    for w, pos_list in positions.items():
        if len(pos_list) < MIN_OCCURRENCES:
            continue
        gaps = [pos_list[i + 1] - pos_list[i] for i in range(len(pos_list) - 1)]
        mean_gap = sum(gaps) / len(gaps)
        if mean_gap == 0:
            continue
        std_gap = math.sqrt(sum((g - mean_gap) ** 2 for g in gaps) / len(gaps))
        burstiness_values.append(std_gap / mean_gap)

    if not burstiness_values:
        return hits, 0.0

    avg_burstiness = sum(burstiness_values) / len(burstiness_values)

    if avg_burstiness < BURSTINESS_VERY_LOW:
        hits.append(
            f"  Word burstiness: {avg_burstiness:.2f} (very low) "
            f"— content words are distributed too evenly"
        )
    elif avg_burstiness < BURSTINESS_LOW:
        hits.append(
            f"  Word burstiness: {avg_burstiness:.2f} (low) "
            f"— content words lack natural clustering"
        )

    raw = max(0.0, min(1.0, (SCORE_CEILING - avg_burstiness) / SCORE_RANGE))
    return hits, raw
