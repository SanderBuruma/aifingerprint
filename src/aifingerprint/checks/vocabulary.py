"""Banned vocabulary detection — flags known AI-favored words."""

import re

from aifingerprint.patterns import BANNED_SINGLE_WORDS, BANNED_MULTI_WORDS

HITS_PER_100_MAX = 5.0  # 5+ hits per 100 words = max score

# Suffixes to strip, longest first. Each entry is tried and if the resulting
# stem (or stem+"e") is in BANNED_SINGLE_WORDS, it's a match.
_SUFFIXES = [
    "izing", "ising", "ating", "ening", "ling", "ring",
    "ized", "ised", "ated", "ened",
    "izes", "ises", "ates",
    "ings", "ment", "ness",
    "ing", "ize", "ise", "ate",
    "ful", "ous", "ive", "ial",
    "ed", "es", "er", "ly",
    "s",
]


def _stem(word: str) -> str:
    """Reduce an inflected word to a rough stem for banned-word matching."""
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            stem = word[:-len(suffix)]
            if stem in BANNED_SINGLE_WORDS:
                return stem
            if stem + "e" in BANNED_SINGLE_WORDS:
                return stem + "e"
    return word


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    hits = []
    total_words = len(text.split())

    # Single-word matches (exact + stemmed)
    for i, line in enumerate(lines, 1):
        raw_words = line.split()
        for j, raw_word in enumerate(raw_words):
            word = re.sub(r"[^\w'-]", "", raw_word).lower()
            matched = word if word in BANNED_SINGLE_WORDS else _stem(word)
            if matched in BANNED_SINGLE_WORDS:
                ctx_start = max(0, j - 5)
                ctx_end = min(len(raw_words), j + 6)
                context = " ".join(raw_words[ctx_start:ctx_end])
                context_highlighted = re.sub(
                    rf"\b({re.escape(raw_word)})\b",
                    lambda m: m.group(1).upper(),
                    context,
                    flags=re.IGNORECASE,
                    count=1,
                )
                hits.append(f"  Line {i}: \"...{context_highlighted}...\" [{matched}]")

    # Multi-word matches — count every occurrence, not just once per line
    for phrase, cat in BANNED_MULTI_WORDS:
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            start = 0
            while True:
                idx = line_lower.find(phrase, start)
                if idx == -1:
                    break
                hits.append(f"  Line {i}: \"{phrase}\" [{cat}]")
                start = idx + len(phrase)

    if total_words == 0:
        return hits, 0.0
    density = len(hits) / (total_words / 100)
    return hits, min(1.0, density / HITS_PER_100_MAX)
