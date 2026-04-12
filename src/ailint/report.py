"""Report generation — console and markdown output."""

import math
from datetime import datetime

from ailint.analyzer import score_label
from ailint.patterns import CATEGORY_ORDER, CATEGORY_WEIGHTS, SECTION_NAMES
from ailint.text import split_sentences, split_paragraphs


def _score_color(score: int) -> str:
    if score <= 20:
        return "green"
    if score <= 40:
        return "olive"
    if score <= 60:
        return "orange"
    if score <= 80:
        return "red"
    return "darkred"


def _gauge_bar(score: int) -> str:
    filled = score // 5
    empty = 20 - filled
    return f"`[{'#' * filled}{'.' * empty}]` {score}/100"


SUMMARY_LABELS = {
    "vocabulary": "Vocab",
    "phrases": "Phrases",
    "structure": "Structure",
    "formatting": "Format",
    "tone": "Tone",
    "compression": "Compression",
    "sentence_rhythm": "Rhythm",
    "punctuation": "Punct",
    "connectives": "Connectives",
    "burstiness": "Burstiness",
}


def print_report(score: int, results: dict) -> None:
    label = score_label(score)
    print(f"\nAI Fingerprint Score: {score}/100 [{label}]\n")

    for key in CATEGORY_ORDER:
        hits, raw = results[key]
        name = SECTION_NAMES[key]
        count = len(hits)
        if count == 0:
            print(f"=== {name} — clean ===\n")
            continue
        print(f"=== {name} ({count} {'hit' if count == 1 else 'hits'}) ===")
        for h in hits:
            print(h)
        print()

    summary_parts = []
    for key in CATEGORY_ORDER:
        hits, _ = results[key]
        summary_parts.append(f"{SUMMARY_LABELS[key]}: {len(hits)}")
    print(f"=== Summary: {' | '.join(summary_parts)} ===")


def generate_report(score: int, results: dict, text: str, source_name: str) -> str:
    label = score_label(score)
    lines = []

    lines.append(f"# AI Fingerprint Report: {source_name}")
    lines.append("")
    lines.append(f"**Score: {score}/100 [{label}]**")
    lines.append("")
    lines.append(_gauge_bar(score))
    lines.append("")

    # Score breakdown table
    lines.append("## Score Breakdown")
    lines.append("")
    lines.append("| Category | Hits | Raw Score | Weight | Weighted |")
    lines.append("|----------|------|-----------|--------|----------|")
    for key in CATEGORY_ORDER:
        hits, raw = results[key]
        weight = CATEGORY_WEIGHTS[key]
        weighted = raw * weight
        lines.append(
            f"| {SECTION_NAMES[key]} | {len(hits)} | {raw:.2f} | {weight:.0%} | {weighted:.2f} |"
        )
    lines.append("")

    # Text statistics
    total_words = len(text.split())
    sents = split_sentences(text)
    paras = split_paragraphs(text)
    alpha_words = [w for w in text.split() if w.isalpha()]
    avg_wl = sum(len(w) for w in alpha_words) / len(alpha_words) if alpha_words else 0
    unique_words = set(w.lower() for w in alpha_words)
    ttr = len(unique_words) / len(alpha_words) if alpha_words else 0

    burst_sd = 0
    if len(sents) >= 2:
        lengths = [len(s.split()) for s in sents]
        mean_len = sum(lengths) / len(lengths)
        variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
        burst_sd = math.sqrt(variance)

    lines.append("## Text Statistics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Words | {total_words} |")
    lines.append(f"| Sentences | {len(sents)} |")
    lines.append(f"| Paragraphs | {len(paras)} |")
    lines.append(f"| Avg word length | {avg_wl:.1f} chars |")
    lines.append(f"| Burstiness (sentence length std dev) | {burst_sd:.1f} |")
    lines.append(f"| Lexical diversity (type-token ratio) | {ttr:.2f} |")
    lines.append(f"| Unique words | {len(unique_words)} |")
    lines.append("")

    # Top issues
    all_hits = []
    for key in CATEGORY_ORDER:
        hits, raw = results[key]
        for h in hits:
            all_hits.append((SECTION_NAMES[key], h.strip()))

    if all_hits:
        lines.append("## Top Issues")
        lines.append("")
        for cat, hit in all_hits:
            lines.append(f"- **{cat}**: {hit}")
        lines.append("")

    # Detailed findings per category
    lines.append("## Detailed Findings")
    lines.append("")
    for key in CATEGORY_ORDER:
        hits, raw = results[key]
        name = SECTION_NAMES[key]
        count = len(hits)
        lines.append(f"### {name} ({count} {'hit' if count == 1 else 'hits'})")
        lines.append("")
        if count == 0:
            lines.append("No issues found.")
        else:
            for h in hits:
                lines.append(f"- `{h.strip()}`")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by ailint*")

    return "\n".join(lines)
