"""Banned phrase detection — cliches, hedges, openers, closers."""

from aifingerprint.patterns import BANNED_PHRASES, BANNED_SENTENCE_STARTERS
from aifingerprint.text import split_sentences, find_line

HITS_PER_100_MAX = 3.0  # 3+ per 100 words = max score


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    hits = []

    for category, phrases in BANNED_PHRASES.items():
        for phrase in phrases:
            phrase_lower = phrase.lower()
            for i, line in enumerate(lines, 1):
                line_lower = line.lower()
                start = 0
                while True:
                    idx = line_lower.find(phrase_lower, start)
                    if idx == -1:
                        break
                    matched = line[idx:idx + len(phrase) + 20].rstrip()
                    hits.append(f"  Line {i}: \"{matched}...\" [{category}]")
                    start = idx + len(phrase)

    sentences = split_sentences(text)
    for sent in sentences:
        for starter in BANNED_SENTENCE_STARTERS:
            if sent.lower().startswith(starter):
                line_num = find_line(lines, sent[:30])
                hits.append(f"  Line {line_num}: starts with \"{starter}\" [transition]")

    total_words = len(text.split())
    if total_words == 0:
        return hits, 0.0
    density = len(hits) / (total_words / 100)
    return hits, min(1.0, density / HITS_PER_100_MAX)
