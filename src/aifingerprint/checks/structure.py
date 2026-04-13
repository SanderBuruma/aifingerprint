"""Sentence and paragraph structure analysis."""

import math

from aifingerprint.patterns import SENTENCE_PATTERNS
from aifingerprint.text import split_sentences, split_paragraphs, word_overlap, find_line

LOW_BURSTINESS_THRESHOLD = 4.0
MODERATE_BURSTINESS_THRESHOLD = 6.0
CONSECUTIVE_LENGTH_TOLERANCE = 3  # words
MIN_CONSECUTIVE_STREAK = 3
PARA_UNIFORMITY_STD_THRESHOLD = 1.0
FRACTAL_OVERLAP_THRESHOLD = 0.5
CONCLUSION_OVERLAP_THRESHOLD = 0.4
MIN_ANAPHORA_RUN = 3
# Common words that naturally repeat at sentence starts
_ANAPHORA_SKIP = {
    "i", "the", "a", "an", "it", "he", "she", "we", "they",
    "this", "that", "but", "and", "so", "if", "or", "my",
}


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    hits = []
    flags = 0

    sentences = split_sentences(text)
    if len(sentences) < 3:
        return hits, 0.0

    # Burstiness (sentence length variance)
    lengths = [len(s.split()) for s in sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / (len(lengths) - 1)
    std_dev = math.sqrt(variance)

    if std_dev < LOW_BURSTINESS_THRESHOLD:
        hits.append(f"  Burstiness: LOW (std dev {std_dev:.1f} words) — sentences are too uniform")
        flags += 1
    elif std_dev < MODERATE_BURSTINESS_THRESHOLD:
        hits.append(f"  Burstiness: MODERATE (std dev {std_dev:.1f} words)")

    # Consecutive similar-length sentences
    streak = 1
    streak_start = 0
    for i in range(1, len(lengths)):
        if abs(lengths[i] - lengths[i - 1]) <= CONSECUTIVE_LENGTH_TOLERANCE:
            streak += 1
        else:
            if streak >= MIN_CONSECUTIVE_STREAK:
                avg = sum(lengths[streak_start:streak_start + streak]) / streak
                hits.append(
                    f"  Sentences {streak_start + 1}-{streak_start + streak}: "
                    f"{streak} consecutive sentences of ~{avg:.0f} words"
                )
                flags += 1
            streak = 1
            streak_start = i
    if streak >= MIN_CONSECUTIVE_STREAK:
        avg = sum(lengths[streak_start:streak_start + streak]) / streak
        hits.append(
            f"  Sentences {streak_start + 1}-{streak_start + streak}: "
            f"{streak} consecutive sentences of ~{avg:.0f} words"
        )
        flags += 1

    # Participial endings
    for sent in sentences:
        if SENTENCE_PATTERNS["participial_ending"].search(sent):
            snippet = sent[-60:] if len(sent) > 60 else sent
            line_num = find_line(lines, sent[:30])
            hits.append(f"  Line {line_num}: participial ending \"...{snippet}\"")
            flags += 1

    # Negative parallelism
    for m in SENTENCE_PATTERNS["negative_parallelism"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: negative parallelism \"{snippet}\"")
        flags += 1

    # Rhetorical self-answers
    for m in SENTENCE_PATTERNS["rhetorical_self_answer"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: rhetorical self-answer \"{snippet}\"")
        flags += 1

    # Paragraph uniformity
    paragraphs = split_paragraphs(text)
    if len(paragraphs) >= 3:
        para_sent_counts = [len(split_sentences(p)) for p in paragraphs]
        if para_sent_counts:
            p_mean = sum(para_sent_counts) / len(para_sent_counts)
            p_var = sum((c - p_mean) ** 2 for c in para_sent_counts) / max(1, len(para_sent_counts) - 1)
            p_std = math.sqrt(p_var)
            if p_std < PARA_UNIFORMITY_STD_THRESHOLD and p_mean > 2:
                hits.append(
                    f"  Paragraph uniformity: avg {p_mean:.1f} sentences, "
                    f"std dev {p_std:.1f} — too uniform"
                )
                flags += 1

    # Fractal summaries (first/last sentence overlap)
    for idx, p in enumerate(paragraphs):
        p_sents = split_sentences(p)
        if len(p_sents) >= 3:
            overlap = word_overlap(p_sents[0], p_sents[-1])
            if overlap > FRACTAL_OVERLAP_THRESHOLD:
                hits.append(
                    f"  Paragraph {idx + 1}: first/last sentence overlap "
                    f"{overlap:.0%} — possible fractal summary"
                )
                flags += 1

    # Conclusion recycling (first paragraph vs last paragraph)
    if len(paragraphs) >= 4:
        overlap = word_overlap(paragraphs[0], paragraphs[-1])
        if overlap > CONCLUSION_OVERLAP_THRESHOLD:
            hits.append(
                f"  Conclusion recycling: first/last paragraph overlap "
                f"{overlap:.0%} — conclusion restates introduction"
            )
            flags += 1

    # Anaphora (3+ sentences starting with the same word)
    if len(sentences) >= 3:
        all_starters = [s.split()[0].lower() if s.split() else "" for s in sentences]
        i = 0
        while i < len(all_starters) - 2:
            if all_starters[i] in _ANAPHORA_SKIP:
                i += 1
                continue
            run = 1
            while i + run < len(all_starters) and all_starters[i + run] == all_starters[i]:
                run += 1
            if run >= MIN_ANAPHORA_RUN:
                hits.append(
                    f"  Sentences {i + 1}-{i + run}: anaphora — "
                    f"{run} sentences starting with \"{all_starters[i]}\""
                )
                flags += 1
                i += run
            else:
                i += 1

    # Rule of three / tricolon
    tricolons = list(SENTENCE_PATTERNS["tricolon"].finditer(text))
    tricolon_threshold = max(3, len(sentences) // 8)
    if len(tricolons) >= tricolon_threshold:
        examples = [m.group(0) for m in tricolons[:3]]
        hits.append(
            f"  Tricolon density: {len(tricolons)} instances of \"X, Y, and Z\" — "
            f"e.g. \"{examples[0]}\""
        )
        flags += 1

    # Both-sides / balanced counterargument
    for m in SENTENCE_PATTERNS["both_sides"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: balanced counterargument \"{snippet}...\"")
        flags += 1

    # Historical analogy stacking
    for m in SENTENCE_PATTERNS["analogy_stacking"].finditer(text):
        snippet = m.group(0)[:80]
        line_num = find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: analogy stacking \"{snippet}...\"")
        flags += 1

    # Scope disclaimers
    for m in SENTENCE_PATTERNS["scope_disclaimer"].finditer(text):
        snippet = m.group(0)[:60]
        line_num = find_line(lines, snippet[:30])
        hits.append(f"  Line {line_num}: scope disclaimer \"{snippet}\"")
        flags += 1

    # Five-paragraph essay detection (intro/conclusion formula in any essay)
    if len(paragraphs) >= 4:
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

    max_expected = max(3, len(sentences) / 5)
    return hits, min(1.0, flags / max_expected)
