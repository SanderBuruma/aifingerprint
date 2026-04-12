"""Banned vocabulary detection — flags known AI-favored words."""

import re

from aifingerprint.patterns import BANNED_SINGLE_WORDS, BANNED_MULTI_WORDS

HITS_PER_100_MAX = 5.0  # 5+ hits per 100 words = max score


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    hits = []
    total_words = len(text.split())

    # Single-word matches
    for i, line in enumerate(lines, 1):
        words_in_line = re.findall(r"\b[a-z][\w'-]*\b", line.lower())
        for j, word in enumerate(words_in_line):
            if word in BANNED_SINGLE_WORDS:
                raw_words = line.split()
                ctx_start = max(0, j - 5)
                ctx_end = min(len(raw_words), j + 6)
                context = " ".join(raw_words[ctx_start:ctx_end])
                context_highlighted = re.sub(
                    rf"\b({re.escape(word)})\b",
                    lambda m: m.group(1).upper(),
                    context,
                    flags=re.IGNORECASE,
                    count=1,
                )
                hits.append(f"  Line {i}: \"...{context_highlighted}...\" [{word}]")

    # Multi-word matches
    for phrase, cat in BANNED_MULTI_WORDS:
        for i, line in enumerate(lines, 1):
            if phrase in line.lower():
                hits.append(f"  Line {i}: \"{phrase}\" [{cat}]")

    if total_words == 0:
        return hits, 0.0
    density = len(hits) / (total_words / 100)
    return hits, min(1.0, density / HITS_PER_100_MAX)
