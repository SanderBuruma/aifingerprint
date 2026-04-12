"""Text splitting and comparison utilities."""

import re


def split_sentences(text: str) -> list[str]:
    """Rough sentence splitter. Good enough for heuristics."""
    clean = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    clean = re.sub(r"^[\s]*[-*]\s+", "", clean, flags=re.MULTILINE)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", clean)
    return [s.strip() for s in parts if s.strip() and len(s.split()) >= 2]


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines."""
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip() and len(p.split()) >= 5]


def word_overlap(s1: str, s2: str) -> float:
    """Fraction of shared words between two strings."""
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / min(len(w1), len(w2))


def find_line(lines: list[str], snippet: str) -> int | str:
    """Find the line number containing a snippet."""
    snippet_lower = snippet.lower()
    for i, line in enumerate(lines, 1):
        if snippet_lower in line.lower():
            return i
    return "?"
