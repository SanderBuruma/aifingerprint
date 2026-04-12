#!/usr/bin/env python3
"""AI writing fingerprint analyzer — lints text for AI writing patterns."""

import argparse
import lzma
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

from collections import Counter

from patterns import (
    BANNED_MULTI_WORDS,
    BANNED_PHRASES,
    BANNED_SENTENCE_STARTERS,
    BANNED_SINGLE_WORDS,
    CATEGORY_WEIGHTS,
    DISCOURSE_CONNECTIVES,
    ENTHUSIASM_WORDS,
    FORMAT_PATTERNS,
    HEDGE_WORDS,
    SENTENCE_PATTERNS,
)


def parse_args():
    parser = argparse.ArgumentParser(description="AI writing fingerprint analyzer")
    parser.add_argument("file", nargs="?", help="Text file to analyze (reads stdin if omitted)")
    parser.add_argument("--clipboard", action="store_true", help="Read from clipboard")
    parser.add_argument("--report", nargs="?", const=True, default=False,
                        metavar="PATH", help="Generate markdown report (optionally specify output path)")
    return parser.parse_args()


def read_input(args):
    if args.clipboard:
        import subprocess
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["xsel", "--clipboard", "--output"],
                capture_output=True, text=True,
            )
        return result.stdout
    if args.file:
        with open(args.file) as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Usage: python analyze.py [file.txt | --clipboard] [--report [PATH]]")
    print("       echo 'text' | python analyze.py")
    sys.exit(1)


def split_sentences(text):
    """Rough sentence splitter. Good enough for heuristics."""
    # Strip markdown headers and bullets for sentence analysis
    clean = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    clean = re.sub(r"^[\s]*[-*]\s+", "", clean, flags=re.MULTILINE)
    # Split on sentence-ending punctuation followed by space or newline
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", clean)
    return [s.strip() for s in parts if s.strip() and len(s.split()) >= 2]


def split_paragraphs(text):
    """Split on blank lines."""
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip() and len(p.split()) >= 5]


def word_overlap(s1, s2):
    """Fraction of shared words between two strings."""
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / min(len(w1), len(w2))


# ─────────────────────────────────────────────────────────────────────────────
# CHECK FUNCTIONS — each returns (hits: list[str], raw_score: float 0-1)
# ─────────────────────────────────────────────────────────────────────────────

def check_vocabulary(text, lines):
    hits = []
    text_lower = text.lower()
    total_words = len(text.split())

    # Single-word matches
    for i, line in enumerate(lines, 1):
        words_in_line = re.findall(r"\b[a-z][\w'-]*\b", line.lower())
        for j, word in enumerate(words_in_line):
            if word in BANNED_SINGLE_WORDS:
                # Context: ±5 words
                start = max(0, j - 5)
                end = min(len(words_in_line), j + 6)
                raw_words = line.split()
                # Find the word in the raw line for highlighting
                ctx_start = max(0, j - 5)
                ctx_end = min(len(raw_words), j + 6)
                context = " ".join(raw_words[ctx_start:ctx_end])
                # Uppercase the match in context
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

    # Score: hits per 100 words, capped at 1.0
    if total_words == 0:
        return hits, 0.0
    density = len(hits) / (total_words / 100)
    return hits, min(1.0, density / 5.0)  # 5+ hits per 100 words = max


def check_phrases(text, lines):
    hits = []
    text_lower = text.lower()

    for category, phrases in BANNED_PHRASES.items():
        for phrase in phrases:
            for i, line in enumerate(lines, 1):
                if phrase.lower() in line.lower():
                    # Show the matching portion
                    idx = line.lower().index(phrase.lower())
                    matched = line[idx:idx + len(phrase) + 20].rstrip()
                    hits.append(f"  Line {i}: \"{matched}...\" [{category}]")

    # Sentence starters
    sentences = split_sentences(text)
    for sent in sentences:
        first_word = sent.split()[0].lower().rstrip(",") if sent.split() else ""
        for starter in BANNED_SENTENCE_STARTERS:
            if sent.lower().startswith(starter):
                line_num = _find_line(lines, sent[:30])
                hits.append(f"  Line {line_num}: starts with \"{starter}\" [transition]")

    total_words = len(text.split())
    if total_words == 0:
        return hits, 0.0
    density = len(hits) / (total_words / 100)
    return hits, min(1.0, density / 3.0)  # 3+ per 100 words = max


def check_structure(text, lines):
    hits = []
    flags = 0

    sentences = split_sentences(text)
    if len(sentences) < 3:
        return hits, 0.0

    # --- Burstiness (sentence length variance) ---
    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)

    if std_dev < 4.0:
        hits.append(f"  Burstiness: LOW (std dev {std_dev:.1f} words) — sentences are too uniform")
        flags += 1
    elif std_dev < 6.0:
        hits.append(f"  Burstiness: MODERATE (std dev {std_dev:.1f} words)")

    # --- Consecutive similar-length sentences ---
    streak = 1
    streak_start = 0
    for i in range(1, len(lengths)):
        if abs(lengths[i] - lengths[i - 1]) <= 3:
            streak += 1
        else:
            if streak >= 3:
                avg = sum(lengths[streak_start:streak_start + streak]) / streak
                hits.append(
                    f"  Sentences {streak_start + 1}-{streak_start + streak}: "
                    f"{streak} consecutive sentences of ~{avg:.0f} words"
                )
                flags += 1
            streak = 1
            streak_start = i
    if streak >= 3:
        avg = sum(lengths[streak_start:streak_start + streak]) / streak
        hits.append(
            f"  Sentences {streak_start + 1}-{streak_start + streak}: "
            f"{streak} consecutive sentences of ~{avg:.0f} words"
        )
        flags += 1

    # --- Participial endings ---
    for sent in sentences:
        if SENTENCE_PATTERNS["participial_ending"].search(sent):
            snippet = sent[-60:] if len(sent) > 60 else sent
            line_num = _find_line(lines, sent[:30])
            hits.append(f"  Line {line_num}: participial ending \"...{snippet}\"")
            flags += 1

    # --- Negative parallelism ---
    for m in SENTENCE_PATTERNS["negative_parallelism"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = _find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: negative parallelism \"{snippet}\"")
        flags += 1

    # --- Rhetorical self-answers ---
    for m in SENTENCE_PATTERNS["rhetorical_self_answer"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = _find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: rhetorical self-answer \"{snippet}\"")
        flags += 1

    # --- Paragraph uniformity ---
    paragraphs = split_paragraphs(text)
    if len(paragraphs) >= 3:
        para_sent_counts = []
        for p in paragraphs:
            p_sents = split_sentences(p)
            para_sent_counts.append(len(p_sents))
        if para_sent_counts:
            p_mean = sum(para_sent_counts) / len(para_sent_counts)
            p_var = sum((c - p_mean) ** 2 for c in para_sent_counts) / len(para_sent_counts)
            p_std = math.sqrt(p_var)
            if p_std < 1.0 and p_mean > 2:
                hits.append(
                    f"  Paragraph uniformity: avg {p_mean:.1f} sentences, "
                    f"std dev {p_std:.1f} — too uniform"
                )
                flags += 1

    # --- Fractal summaries (first/last sentence overlap) ---
    for idx, p in enumerate(paragraphs):
        p_sents = split_sentences(p)
        if len(p_sents) >= 3:
            overlap = word_overlap(p_sents[0], p_sents[-1])
            if overlap > 0.5:
                hits.append(
                    f"  Paragraph {idx + 1}: first/last sentence overlap "
                    f"{overlap:.0%} — possible fractal summary"
                )
                flags += 1

    # --- Conclusion recycling (first paragraph vs last paragraph overlap) ---
    if len(paragraphs) >= 4:
        first_p = paragraphs[0]
        last_p = paragraphs[-1]
        overlap = word_overlap(first_p, last_p)
        if overlap > 0.4:
            hits.append(
                f"  Conclusion recycling: first/last paragraph overlap "
                f"{overlap:.0%} — conclusion restates introduction"
            )
            flags += 1

    # --- Anaphora (3+ sentences starting with the same word) ---
    # Common words that naturally repeat at sentence starts
    _anaphora_skip = {"i", "the", "a", "an", "it", "he", "she", "we", "they",
                      "this", "that", "but", "and", "so", "if", "or", "my"}
    if len(sentences) >= 3:
        all_starters = []
        for s in sentences:
            first = s.split()[0].lower() if s.split() else ""
            all_starters.append(first)
        # Scan for runs, but only report each run once
        i = 0
        while i < len(all_starters) - 2:
            if all_starters[i] in _anaphora_skip:
                i += 1
                continue
            run = 1
            while i + run < len(all_starters) and all_starters[i + run] == all_starters[i]:
                run += 1
            if run >= 3:
                hits.append(
                    f"  Sentences {i + 1}-{i + run}: anaphora — "
                    f"{run} sentences starting with \"{all_starters[i]}\""
                )
                flags += 1
                i += run  # Skip past this run
            else:
                i += 1

    # --- Rule of three / tricolon ---
    tricolons = list(SENTENCE_PATTERNS["tricolon"].finditer(text))
    # Only flag if there are many tricolons relative to text length
    tricolon_threshold = max(2, len(sentences) // 10)
    if len(tricolons) >= tricolon_threshold:
        examples = [m.group(0) for m in tricolons[:3]]
        hits.append(
            f"  Tricolon density: {len(tricolons)} instances of \"X, Y, and Z\" — "
            f"e.g. \"{examples[0]}\""
        )
        flags += 1

    # --- Both-sides / balanced counterargument ---
    for m in SENTENCE_PATTERNS["both_sides"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = _find_line(lines, "on one hand")
        hits.append(f"  Line {line_num}: balanced counterargument \"{snippet}...\"")
        flags += 1

    # --- Historical analogy stacking ---
    for m in SENTENCE_PATTERNS["analogy_stacking"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = _find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: analogy stacking \"{snippet}...\"")
        flags += 1

    # --- Scope disclaimers ---
    for m in SENTENCE_PATTERNS["scope_disclaimer"].finditer(text):
        snippet = m.group(0)[:60]
        line_num = _find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: scope disclaimer \"{snippet}\"")
        flags += 1

    # --- Five-paragraph essay detection ---
    if 4 <= len(paragraphs) <= 6:
        first_p_lower = paragraphs[0].lower()
        last_p_lower = paragraphs[-1].lower()
        has_intro_signals = any(
            w in first_p_lower
            for w in ["will explore", "will discuss", "will examine",
                       "this article", "this essay", "this guide",
                       "in this post", "we'll look at", "we will"]
        )
        has_closing_signals = any(
            w in last_p_lower
            for w in ["in conclusion", "in summary", "to summarize",
                       "key takeaway", "to wrap up", "in closing"]
        )
        if has_intro_signals and has_closing_signals:
            hits.append(
                f"  Five-paragraph essay: {len(paragraphs)} paragraphs with "
                f"intro preview + conclusion formula"
            )
            flags += 1

    # Score based on flags relative to text length
    max_expected = max(3, len(sentences) // 5)
    return hits, min(1.0, flags / max_expected)


def check_formatting(text, lines):
    hits = []
    total_words = len(text.split())

    # Em dashes
    em_dashes = FORMAT_PATTERNS["em_dash"].findall(text)
    em_count = len(em_dashes)
    if total_words > 0:
        per_500 = em_count / (total_words / 500)
        if per_500 > 2:
            hits.append(f"  Em dash density: {per_500:.1f} per 500 words (limit: 2) — {em_count} total")

    # Bold-first bullets
    bold_bullets = FORMAT_PATTERNS["bold_first_bullet"].findall(text)
    if len(bold_bullets) >= 3:
        hits.append(f"  Bold-first bullets: {len(bold_bullets)} instances")

    # Header density
    headers = FORMAT_PATTERNS["header"].findall(text)
    if total_words > 0 and total_words < 500 and len(headers) > 3:
        hits.append(f"  Header density: {len(headers)} headers in {total_words} words — excessive")
    elif total_words > 0:
        per_500 = len(headers) / (total_words / 500)
        if per_500 > 4:
            hits.append(f"  Header density: {per_500:.1f} per 500 words — excessive")

    # Title case headers
    title_case = FORMAT_PATTERNS["title_case_header"].findall(text)
    if title_case:
        hits.append(f"  Title Case headers: {len(title_case)} instances (prefer sentence case)")

    score_parts = []
    if em_count > 0 and total_words > 0:
        score_parts.append(min(1.0, (em_count / (total_words / 500)) / 6))
    if bold_bullets:
        score_parts.append(min(1.0, len(bold_bullets) / 8))
    if headers and total_words > 0:
        score_parts.append(min(1.0, (len(headers) / (total_words / 500)) / 8))

    return hits, (sum(score_parts) / max(1, len(score_parts))) if score_parts else 0.0


def check_tone(text, lines):
    hits = []
    total_words = len(text.split())
    text_lower = text.lower()

    # Hedge word density
    hedge_count = 0
    for hw in HEDGE_WORDS:
        hedge_count += len(re.findall(rf"\b{re.escape(hw)}\b", text_lower))
    if total_words > 0:
        hedge_per_100 = hedge_count / (total_words / 100)
        if hedge_per_100 > 2.0:
            hits.append(f"  Hedging density: {hedge_per_100:.1f} per 100 words (high)")
        elif hedge_per_100 > 1.0:
            hits.append(f"  Hedging density: {hedge_per_100:.1f} per 100 words (moderate)")

    # Exclamation marks
    excl_count = text.count("!")
    if total_words > 0:
        excl_per_500 = excl_count / (total_words / 500)
        if excl_per_500 > 3:
            hits.append(f"  Exclamation marks: {excl_count} total ({excl_per_500:.1f} per 500 words)")

    # False enthusiasm
    enthusiasm_count = 0
    enthusiasm_found = []
    for ew in ENTHUSIASM_WORDS:
        matches = re.findall(rf"\b{re.escape(ew)}\b", text_lower)
        if matches:
            enthusiasm_count += len(matches)
            enthusiasm_found.append(ew)
    if total_words > 0:
        enth_per_500 = enthusiasm_count / (total_words / 500)
        if enth_per_500 > 2:
            hits.append(
                f"  False enthusiasm: {enthusiasm_count} hype words "
                f"({enth_per_500:.1f} per 500 words) — {', '.join(enthusiasm_found[:5])}"
            )
        elif enthusiasm_count >= 3:
            hits.append(
                f"  Enthusiasm: {enthusiasm_count} instances — {', '.join(enthusiasm_found[:5])}"
            )

    # Contraction rate (low contractions = overly formal / AI-like)
    contraction_pattern = re.compile(r"\b\w+'(?:t|re|ve|ll|s|d|m)\b", re.IGNORECASE)
    contractions = contraction_pattern.findall(text)
    if total_words > 100:
        contr_per_100 = len(contractions) / (total_words / 100)
        if contr_per_100 < 0.3:
            hits.append(
                f"  Low contraction rate: {len(contractions)} contractions in "
                f"{total_words} words ({contr_per_100:.2f}/100) — overly formal"
            )

    # Register consistency (sentence-level formality variance)
    # Heuristic: measure avg word length per sentence as a rough formality proxy
    sentences = split_sentences(text)
    if len(sentences) >= 5:
        sent_formality = []
        for s in sentences:
            words = s.split()
            if words:
                avg_wl = sum(len(w) for w in words) / len(words)
                sent_formality.append(avg_wl)
        if sent_formality:
            f_mean = sum(sent_formality) / len(sent_formality)
            f_var = sum((f - f_mean) ** 2 for f in sent_formality) / len(sent_formality)
            f_std = math.sqrt(f_var)
            if f_std < 0.5:
                hits.append(
                    f"  Register consistency: formality std dev {f_std:.2f} — "
                    f"tone is unnaturally uniform (human writing varies more)"
                )

    # Abstract noun density (-tion, -ment, -ness, -ity words)
    wds = [w.lower().strip(".,!?;:\"'()") for w in text.split()]
    abstract_count = sum(
        1 for w in wds
        if re.match(r".*(?:tion|ment|ness|ity)$", w) and len(w) > 5
    )
    if total_words > 0:
        abstract_per_100 = abstract_count / (total_words / 100)
        if abstract_per_100 > 3.0:
            hits.append(
                f"  Abstract noun density: {abstract_per_100:.1f} per 100 words (high) "
                f"— overuse of -tion/-ment/-ness/-ity words"
            )
        elif abstract_per_100 > 1.5:
            hits.append(
                f"  Abstract noun density: {abstract_per_100:.1f} per 100 words (moderate)"
            )

    # Average word length (AI uses longer words)
    alpha_words = [w for w in text.split() if w.isalpha()]
    if alpha_words:
        avg_wl = sum(len(w) for w in alpha_words) / len(alpha_words)
        if avg_wl > 5.2:
            hits.append(
                f"  Average word length: {avg_wl:.1f} chars (high) "
                f"— AI averages 5.3-5.8, humans 4.0-4.5"
            )

    # Long word ratio (>8 chars)
    if alpha_words:
        long_ratio = sum(1 for w in alpha_words if len(w) > 8) / len(alpha_words)
        if long_ratio > 0.12:
            hits.append(
                f"  Long word ratio: {long_ratio:.0%} of words >8 chars "
                f"(AI typical: 18-24%, human: 3-7%)"
            )

    # Intensifier density (truly, extremely, remarkably, etc.)
    intensifiers = {
        "very", "highly", "extremely", "incredibly", "truly",
        "absolutely", "remarkably", "significantly", "particularly",
        "exceptionally", "tremendously", "profoundly",
    }
    intensifier_count = sum(1 for w in wds if w in intensifiers)
    if total_words > 0 and intensifier_count > 0:
        intens_per_500 = intensifier_count / (total_words / 500)
        if intens_per_500 > 1.0:
            found = [w for w in wds if w in intensifiers][:5]
            hits.append(
                f"  Intensifier density: {intens_per_500:.1f} per 500 words "
                f"— {', '.join(set(found))}"
            )

    # Conversational marker absence
    conv_markers = [
        "honestly", "actually", "basically", "literally", "obviously",
        "look,", "i mean", "right?", "you know", "kind of", "sort of",
        "pretty much", "turns out", "ended up", "wound up",
    ]
    conv_count = sum(text_lower.count(m) for m in conv_markers)
    if total_words > 200 and conv_count == 0:
        hits.append(
            f"  No conversational markers found in {total_words} words "
            f"— natural writing uses 'actually', 'honestly', 'turns out', etc."
        )

    # Conjunction starters absence (And/But/So at sentence start = human)
    conj_starters = {"and", "but", "so", "or", "yet"}
    sents_for_conj = split_sentences(text)
    if len(sents_for_conj) >= 5:
        conj_start_count = sum(
            1 for s in sents_for_conj if s.split()[0].lower() in conj_starters
        )
        conj_ratio = conj_start_count / len(sents_for_conj)
        if conj_ratio < 0.02:
            hits.append(
                f"  No conjunction starters: 0/{len(sents_for_conj)} sentences start "
                f"with And/But/So — human writing does this naturally"
            )

    # Abstract-to-concrete ratio
    if alpha_words:
        concrete_count = sum(1 for w in alpha_words if len(w) <= 5)
        if concrete_count > 0:
            abs_conc_ratio = abstract_count / concrete_count
            if abs_conc_ratio > 0.04:
                hits.append(
                    f"  Abstract/concrete ratio: {abs_conc_ratio:.2f} "
                    f"({abstract_count} abstract vs {concrete_count} concrete words)"
                )

    score_parts = []
    if total_words > 0:
        score_parts.append(min(1.0, (hedge_count / (total_words / 100)) / 4.0))
        score_parts.append(min(1.0, enthusiasm_count / 6.0))
        # New signals
        score_parts.append(min(1.0, abstract_count / (total_words / 100) / 6.0))
        if alpha_words:
            score_parts.append(min(1.0, max(0, (avg_wl - 4.5)) / 1.5))
            score_parts.append(min(1.0, max(0, long_ratio - 0.08) / 0.15) if alpha_words else 0)
        score_parts.append(min(1.0, intensifier_count / 3.0))
        if total_words > 200:
            score_parts.append(1.0 if conv_count == 0 else 0.0)
    return hits, (sum(score_parts) / max(1, len(score_parts))) if score_parts else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# SENTENCE RHYTHM (sentence length coefficient of variation)
# ─────────────────────────────────────────────────────────────────────────────

def check_sentence_rhythm(text, lines):
    """AI produces sentences of uniform length. Measure coefficient of variation."""
    hits = []
    sentences = split_sentences(text)
    if len(sentences) < 5:
        return hits, 0.0

    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return hits, 0.0
    std_len = math.sqrt(sum((ln - mean_len) ** 2 for ln in lengths) / len(lengths))
    cv = std_len / mean_len

    # From corpus testing: AI mean CV ~0.45, human ~0.72
    if cv < 0.35:
        hits.append(
            f"  Sentence rhythm: CV={cv:.2f} (very low) "
            f"— sentence lengths are unnaturally uniform"
        )
    elif cv < 0.50:
        hits.append(
            f"  Sentence rhythm: CV={cv:.2f} (low) "
            f"— sentence lengths lack natural variation"
        )

    # Map CV 0.30-0.70 to score 1.0-0.0 (lower CV = higher score)
    raw = max(0.0, min(1.0, (0.70 - cv) / 0.40))
    return hits, raw


# ─────────────────────────────────────────────────────────────────────────────
# PUNCTUATION DIVERSITY (Shannon entropy of punctuation distribution)
# ─────────────────────────────────────────────────────────────────────────────

_PUNCT_CHARS = set('.,;:!?\u2014\u2013-()"\u201c\u201d\'\u2018\u2019')


def check_punctuation_diversity(text, lines):
    """AI uses a narrow range of punctuation. Measure entropy of punct distribution."""
    hits = []
    punct = [ch for ch in text if ch in _PUNCT_CHARS]
    if len(punct) < 10:
        return hits, 0.0

    freqs = Counter(punct)
    total = len(punct)
    entropy = -sum((c / total) * math.log2(c / total) for c in freqs.values())
    max_entropy = math.log2(len(_PUNCT_CHARS))
    normalized = entropy / max_entropy if max_entropy > 0 else 0

    # Lower entropy = narrower punctuation = more AI-like
    if normalized < 0.30:
        hits.append(
            f"  Punctuation diversity: entropy={entropy:.2f} (very low) "
            f"— almost only commas and periods"
        )
    elif normalized < 0.45:
        hits.append(
            f"  Punctuation diversity: entropy={entropy:.2f} (low) "
            f"— limited punctuation variety"
        )

    # Map normalized entropy 0.20-0.60 to score 1.0-0.0
    raw = max(0.0, min(1.0, (0.60 - normalized) / 0.40))
    return hits, raw


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTIVE DENSITY (discourse connectives per sentence)
# ─────────────────────────────────────────────────────────────────────────────

def check_connective_density(text, lines):
    """AI overuses discourse connectives like however, moreover, furthermore."""
    hits = []
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return hits, 0.0

    words = re.findall(r"\b[a-z]+\b", text.lower())
    count = sum(1 for w in words if w in DISCOURSE_CONNECTIVES)
    density = count / len(sentences)

    if density > 0.5:
        found = [w for w in words if w in DISCOURSE_CONNECTIVES]
        unique_found = list(dict.fromkeys(found))[:5]
        hits.append(
            f"  Connective density: {density:.2f}/sentence (high) "
            f"— {', '.join(unique_found)}"
        )
    elif density > 0.25:
        found = [w for w in words if w in DISCOURSE_CONNECTIVES]
        unique_found = list(dict.fromkeys(found))[:5]
        hits.append(
            f"  Connective density: {density:.2f}/sentence (moderate) "
            f"— {', '.join(unique_found)}"
        )

    # Map density 0.1-0.6 to score 0.0-1.0
    raw = max(0.0, min(1.0, (density - 0.1) / 0.5))
    return hits, raw


# ─────────────────────────────────────────────────────────────────────────────
# BURSTINESS (word distribution uniformity)
# ─────────────────────────────────────────────────────────────────────────────

_BURSTINESS_STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "been", "were",
    "they", "their", "there", "which", "would", "could", "should", "about",
    "into", "than", "then", "them", "these", "those", "other", "after",
    "before", "being", "between", "does", "doing", "during", "each",
    "every", "under", "over", "again", "further", "where", "when", "while",
    "also", "just", "more", "most", "some", "such", "only", "very",
    "will", "what", "your", "still",
}


def check_burstiness(text, lines):
    """Human writing clusters topic words; AI distributes them evenly.
    Measure CV of inter-occurrence gaps for content words."""
    hits = []
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if len(words) < 50:
        return hits, 0.0

    positions = {}
    for i, w in enumerate(words):
        if len(w) > 4 and w not in _BURSTINESS_STOPWORDS:
            positions.setdefault(w, []).append(i)

    burstiness_values = []
    for w, pos_list in positions.items():
        if len(pos_list) < 3:
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

    # Lower burstiness = more uniform = more AI-like
    if avg_burstiness < 0.5:
        hits.append(
            f"  Word burstiness: {avg_burstiness:.2f} (very low) "
            f"— content words are distributed too evenly"
        )
    elif avg_burstiness < 0.7:
        hits.append(
            f"  Word burstiness: {avg_burstiness:.2f} (low) "
            f"— content words lack natural clustering"
        )

    # Map burstiness 0.3-1.0 to score 1.0-0.0 (lower = more AI-like)
    raw = max(0.0, min(1.0, (1.0 - avg_burstiness) / 0.7))
    return hits, raw


# ─────────────────────────────────────────────────────────────────────────────
# COMPRESSION CHECK (ZipPy-style LZMA compression ratio)
# ─────────────────────────────────────────────────────────────────────────────

_SEED_BYTES = None


def _load_seed():
    global _SEED_BYTES
    if _SEED_BYTES is not None:
        return _SEED_BYTES
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_seed_corpus.txt")
    if os.path.exists(seed_path):
        with open(seed_path) as f:
            _SEED_BYTES = f.read().encode("utf-8")
    else:
        _SEED_BYTES = b""
    return _SEED_BYTES


def check_compression(text, lines):
    """Compare how well text compresses when appended to a known AI corpus.
    AI-like text shares patterns with the seed, producing a higher compression ratio."""
    hits = []
    seed = _load_seed()
    if not seed:
        return hits, 0.0

    text_bytes = text.encode("utf-8")
    if len(text_bytes) < 100:
        return hits, 0.0

    seed_compressed = len(lzma.compress(seed))
    combined_compressed = len(lzma.compress(seed + text_bytes))
    text_alone = len(lzma.compress(text_bytes))

    # Overhead: how many extra bytes the text adds to the compressed seed
    overhead = combined_compressed - seed_compressed
    # Ratio: lower overhead relative to standalone = more similar to AI seed
    if text_alone == 0:
        return hits, 0.0
    similarity = 1.0 - (overhead / text_alone)

    # Based on corpus testing:
    #   AI leave-one-out mean: ~0.47, human mean: ~0.36
    #   Threshold zone: 0.36-0.47
    if similarity > 0.45:
        hits.append(
            f"  Compression similarity: {similarity:.3f} (high) "
            f"— text compresses well against AI corpus"
        )
    elif similarity > 0.38:
        hits.append(
            f"  Compression similarity: {similarity:.3f} (moderate) "
            f"— some pattern overlap with AI corpus"
        )

    # Score: map 0.30-0.50 range to 0.0-1.0
    raw = max(0.0, min(1.0, (similarity - 0.30) / 0.20))
    return hits, raw


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _find_line(lines, snippet):
    """Find the line number containing a snippet."""
    snippet_lower = snippet.lower()
    for i, line in enumerate(lines, 1):
        if snippet_lower in line.lower():
            return i
    return "?"


def score_label(score):
    if score <= 20:
        return "CLEAN"
    if score <= 40:
        return "MILD"
    if score <= 60:
        return "NOTICEABLE"
    if score <= 80:
        return "OBVIOUS"
    return "BLATANT"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def analyze(text):
    lines = text.splitlines()
    results = {}

    checks = {
        "vocabulary": check_vocabulary,
        "phrases": check_phrases,
        "structure": check_structure,
        "formatting": check_formatting,
        "tone": check_tone,
        "compression": check_compression,
        "sentence_rhythm": check_sentence_rhythm,
        "punctuation": check_punctuation_diversity,
        "connectives": check_connective_density,
        "burstiness": check_burstiness,
    }

    weighted_total = 0.0
    for name, fn in checks.items():
        hits, raw_score = fn(text, lines)
        results[name] = (hits, raw_score)
        weighted_total += raw_score * CATEGORY_WEIGHTS[name]

    final_score = int(round(weighted_total * 100))
    final_score = max(0, min(100, final_score))
    return final_score, results


def print_report(score, results):
    label = score_label(score)
    print(f"\nAI Fingerprint Score: {score}/100 [{label}]\n")

    section_names = {
        "vocabulary": "Banned Vocabulary",
        "phrases": "Banned Phrases",
        "structure": "Sentence & Paragraph Structure",
        "formatting": "Formatting",
        "tone": "Tone",
        "compression": "Compression Analysis",
        "sentence_rhythm": "Sentence Rhythm",
        "punctuation": "Punctuation Diversity",
        "connectives": "Connective Density",
        "burstiness": "Word Burstiness",
    }

    _all_keys = [
        "compression", "sentence_rhythm", "tone", "punctuation",
        "connectives", "burstiness", "vocabulary", "structure",
        "phrases", "formatting",
    ]
    for key in _all_keys:
        hits, raw = results[key]
        name = section_names[key]
        count = len(hits)
        if count == 0:
            print(f"=== {name} — clean ===\n")
            continue
        print(f"=== {name} ({count} {'hit' if count == 1 else 'hits'}) ===")
        for h in hits:
            print(h)
        print()

    # Summary line
    summary_parts = []
    summary_labels = {
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
    for key in _all_keys:
        hits, _ = results[key]
        count = len(hits)
        summary_parts.append(f"{summary_labels[key]}: {count}")
    print(f"=== Summary: {' | '.join(summary_parts)} ===")


def _score_color(score):
    if score <= 20:
        return "green"
    if score <= 40:
        return "olive"
    if score <= 60:
        return "orange"
    if score <= 80:
        return "red"
    return "darkred"


def _gauge_bar(score):
    filled = score // 5
    empty = 20 - filled
    return f"`[{'#' * filled}{'.' * empty}]` {score}/100"


def generate_report(score, results, text, source_name):
    label = score_label(score)
    lines = []

    lines.append(f"# AI Fingerprint Report: {source_name}")
    lines.append("")
    lines.append(f"**Score: {score}/100 [{label}]**")
    lines.append("")
    lines.append(_gauge_bar(score))
    lines.append("")

    # Summary table
    section_names = {
        "vocabulary": "Banned Vocabulary",
        "phrases": "Banned Phrases",
        "structure": "Structure",
        "formatting": "Formatting",
        "tone": "Tone",
        "compression": "Compression",
        "sentence_rhythm": "Sentence Rhythm",
        "punctuation": "Punctuation Diversity",
        "connectives": "Connective Density",
        "burstiness": "Word Burstiness",
    }
    _all_keys = [
        "compression", "sentence_rhythm", "tone", "punctuation",
        "connectives", "burstiness", "vocabulary", "structure",
        "phrases", "formatting",
    ]
    lines.append("## Score Breakdown")
    lines.append("")
    lines.append("| Category | Hits | Raw Score | Weight | Weighted |")
    lines.append("|----------|------|-----------|--------|----------|")
    for key in _all_keys:
        hits, raw = results[key]
        weight = CATEGORY_WEIGHTS[key]
        weighted = raw * weight
        lines.append(
            f"| {section_names[key]} | {len(hits)} | {raw:.2f} | {weight:.0%} | {weighted:.2f} |"
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
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
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
    for key in _all_keys:
        hits, raw = results[key]
        for h in hits:
            all_hits.append((section_names[key], h.strip()))

    if all_hits:
        lines.append("## Top Issues")
        lines.append("")
        for cat, hit in all_hits:
            lines.append(f"- **{cat}**: {hit}")
        lines.append("")

    # Detailed findings per category
    lines.append("## Detailed Findings")
    lines.append("")
    for key in _all_keys:
        hits, raw = results[key]
        name = section_names[key]
        count = len(hits)
        lines.append(f"### {name} ({count} {'hit' if count == 1 else 'hits'})")
        lines.append("")
        if count == 0:
            lines.append("No issues found.")
        else:
            for h in hits:
                lines.append(f"- `{h.strip()}`")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by ai-writing-guardrails*")

    return "\n".join(lines)


def main():
    args = parse_args()
    text = read_input(args)
    if not text or not text.strip():
        print("No text provided.")
        sys.exit(1)

    score, results = analyze(text)

    if args.report is not False:
        # Determine source name
        if args.file:
            source_name = os.path.basename(args.file)
        elif args.clipboard:
            source_name = "clipboard"
        else:
            source_name = "stdin"

        # Determine output path
        if args.report is True:
            if args.file:
                base = os.path.splitext(args.file)[0]
                report_path = f"{base}.report.md"
            else:
                report_path = "report.md"
        else:
            report_path = args.report

        md = generate_report(score, results, text, source_name)
        with open(report_path, "w") as f:
            f.write(md)
        print(f"Report written to {report_path}")
    else:
        print_report(score, results)


if __name__ == "__main__":
    main()
