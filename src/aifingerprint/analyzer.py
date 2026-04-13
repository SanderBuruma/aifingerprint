"""Core analyzer — orchestrates all checks and produces a weighted score."""

from aifingerprint.checks import CHECKS
from aifingerprint.patterns import CATEGORY_WEIGHTS
from aifingerprint.text import normalize_text


def analyze(text: str) -> tuple[int, dict]:
    """Run all checks on text and return (score 0-100, results dict).

    Results dict maps category name → (hits: list[str], raw_score: float).
    """
    text = normalize_text(text)
    lines = text.splitlines()
    results = {}
    weighted_total = 0.0

    for name, fn in CHECKS.items():
        hits, raw_score = fn(text, lines)
        results[name] = (hits, raw_score)
        weighted_total += raw_score * CATEGORY_WEIGHTS[name]

    final_score = max(0, min(100, int(round(weighted_total * 100))))
    return final_score, results


def score_label(score: int) -> str:
    if score <= 20:
        return "CLEAN"
    if score <= 40:
        return "MILD"
    if score <= 60:
        return "NOTICEABLE"
    if score <= 80:
        return "OBVIOUS"
    return "BLATANT"
