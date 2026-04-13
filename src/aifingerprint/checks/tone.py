"""Tone analysis — hedging, enthusiasm, formality, word length, intensifiers."""

import math
import re

from aifingerprint.patterns import HEDGE_WORDS, ENTHUSIASM_WORDS
from aifingerprint.text import split_sentences

HEDGE_HIGH_PER_100 = 2.0
HEDGE_MODERATE_PER_100 = 1.0
EXCL_PER_500_LIMIT = 3
ENTHUSIASM_PER_500_LIMIT = 2
ENTHUSIASM_MIN_COUNT = 3
LOW_CONTRACTION_PER_100 = 0.3
MIN_WORDS_FOR_CONTRACTION = 100
FORMALITY_STD_THRESHOLD = 0.5
ABSTRACT_HIGH_PER_100 = 3.0
ABSTRACT_MODERATE_PER_100 = 1.5
AVG_WORD_LENGTH_THRESHOLD = 5.2
LONG_WORD_RATIO_THRESHOLD = 0.12
INTENSIFIER_PER_500_LIMIT = 1.0
MIN_WORDS_FOR_CONV_MARKERS = 200
CONJ_START_RATIO_THRESHOLD = 0.02

# Words ending in -tion/-ment/-ness/-ity that are NOT abstract AI-style nouns.
# These are concrete, institutional, or common enough to cause false positives.
_ABSTRACT_EXCLUSIONS = {
    # -ity: concrete/institutional
    "university", "community", "authority", "majority", "minority", "priority",
    "quality", "quantity", "charity", "clarity", "gravity", "electricity",
    "city", "entity", "identity", "facility", "ability", "utility",
    "nationality", "personality", "municipality", "celebrity", "security",
    "commodity", "capacity", "activity", "reality", "society", "variety",
    "density", "velocity", "publicity", "property", "liberty", "dignity",
    # -tion: concrete/common
    "nation", "station", "position", "question", "section", "election",
    "collection", "education", "population", "generation", "location",
    "condition", "direction", "function", "mention", "attention",
    "tradition", "competition", "motion", "action", "fraction",
    "construction", "production", "infection", "reaction", "portion",
    "addition", "ammunition", "caution", "fiction", "edition",
    # -ment: concrete/common
    "apartment", "government", "department", "moment", "comment",
    "document", "element", "basement", "equipment", "instrument",
    "tournament", "payment", "treatment", "segment", "garment",
    "cement", "pavement",
    # -ness: concrete/common
    "business", "fitness", "illness", "witness", "darkness", "wilderness",
}

INTENSIFIERS = {
    "very", "highly", "extremely", "incredibly", "truly",
    "absolutely", "remarkably", "significantly", "particularly",
    "exceptionally", "tremendously", "profoundly",
}

CONVERSATIONAL_MARKERS = [
    "honestly", "actually", "basically", "literally", "obviously",
    "look,", "i mean", "right?", "you know", "kind of", "sort of",
    "pretty much", "turns out", "ended up", "wound up",
]

_CONV_MARKER_PATTERNS = [
    re.compile(rf"\b{re.escape(m)}")
    for m in CONVERSATIONAL_MARKERS
]

CONJUNCTION_STARTERS = {"and", "but", "so", "or", "yet"}


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    hits = []
    total_words = len(text.split())
    text_lower = text.lower()

    # Hedge word density
    hedge_count = 0
    for hw in HEDGE_WORDS:
        hedge_count += len(re.findall(rf"\b{re.escape(hw)}\b", text_lower))
    if total_words > 0:
        hedge_per_100 = hedge_count / (total_words / 100)
        if hedge_per_100 > HEDGE_HIGH_PER_100:
            hits.append(f"  Hedging density: {hedge_per_100:.1f} per 100 words (high)")
        elif hedge_per_100 > HEDGE_MODERATE_PER_100:
            hits.append(f"  Hedging density: {hedge_per_100:.1f} per 100 words (moderate)")

    # Exclamation marks
    excl_count = text.count("!")
    if total_words > 0:
        excl_per_500 = excl_count / (total_words / 500)
        if excl_per_500 > EXCL_PER_500_LIMIT:
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
        if enth_per_500 > ENTHUSIASM_PER_500_LIMIT:
            hits.append(
                f"  False enthusiasm: {enthusiasm_count} hype words "
                f"({enth_per_500:.1f} per 500 words) — {', '.join(enthusiasm_found[:5])}"
            )
        elif enthusiasm_count >= ENTHUSIASM_MIN_COUNT:
            hits.append(
                f"  Enthusiasm: {enthusiasm_count} instances — {', '.join(enthusiasm_found[:5])}"
            )

    # Contraction rate (low contractions = overly formal / AI-like)
    # Match n't, 're, 've, 'll, 'd, 'm unconditionally; 's only after pronouns
    contraction_pattern = re.compile(
        r"\b\w+'(?:t|re|ve|ll|d|m)\b"   # all except 's
        r"|\b(?:it|he|she|that|what|there|here|let|who|how|where|when)'s\b",
        re.IGNORECASE,
    )
    contractions = contraction_pattern.findall(text)
    if total_words > MIN_WORDS_FOR_CONTRACTION:
        contr_per_100 = len(contractions) / (total_words / 100)
        if contr_per_100 < LOW_CONTRACTION_PER_100:
            hits.append(
                f"  Low contraction rate: {len(contractions)} contractions in "
                f"{total_words} words ({contr_per_100:.2f}/100) — overly formal"
            )

    # Register consistency (sentence-level formality variance)
    sentences = split_sentences(text)
    sent_formality: list[float] = []
    f_std = float("inf")
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
            if f_std < FORMALITY_STD_THRESHOLD:
                hits.append(
                    f"  Register consistency: formality std dev {f_std:.2f} — "
                    f"tone is unnaturally uniform (human writing varies more)"
                )

    # Abstract noun density (-tion, -ment, -ness, -ity words)
    wds = [w.lower().strip(".,!?;:\"'()") for w in text.split()]
    abstract_count = sum(
        1 for w in wds
        if re.match(r".*(?:tion|ment|ness|ity)$", w) and len(w) > 5
        and w not in _ABSTRACT_EXCLUSIONS
    )
    if total_words > 0:
        abstract_per_100 = abstract_count / (total_words / 100)
        if abstract_per_100 > ABSTRACT_HIGH_PER_100:
            hits.append(
                f"  Abstract noun density: {abstract_per_100:.1f} per 100 words (high) "
                f"— overuse of -tion/-ment/-ness/-ity words"
            )
        elif abstract_per_100 > ABSTRACT_MODERATE_PER_100:
            hits.append(
                f"  Abstract noun density: {abstract_per_100:.1f} per 100 words (moderate)"
            )

    # Average word length (AI uses longer words)
    alpha_words = [w for w in text.split() if w.isalpha()]
    avg_wl = 0.0
    if alpha_words:
        avg_wl = sum(len(w) for w in alpha_words) / len(alpha_words)
        if avg_wl > AVG_WORD_LENGTH_THRESHOLD:
            hits.append(
                f"  Average word length: {avg_wl:.1f} chars (high) "
                f"— AI averages 5.3-5.8, humans 4.0-4.5"
            )

    # Long word ratio (>8 chars)
    long_ratio = 0.0
    if alpha_words:
        long_ratio = sum(1 for w in alpha_words if len(w) > 8) / len(alpha_words)
        if long_ratio > LONG_WORD_RATIO_THRESHOLD:
            hits.append(
                f"  Long word ratio: {long_ratio:.0%} of words >8 chars "
                f"(AI typical: 18-24%, human: 3-7%)"
            )

    # Intensifier density
    intensifier_count = sum(1 for w in wds if w in INTENSIFIERS)
    if total_words > 0 and intensifier_count > 0:
        intens_per_500 = intensifier_count / (total_words / 500)
        if intens_per_500 > INTENSIFIER_PER_500_LIMIT:
            found = [w for w in wds if w in INTENSIFIERS][:5]
            hits.append(
                f"  Intensifier density: {intens_per_500:.1f} per 500 words "
                f"— {', '.join(set(found))}"
            )

    # Conversational marker absence (word-boundary matching)
    conv_count = sum(
        len(pat.findall(text_lower)) for pat in _CONV_MARKER_PATTERNS
    )
    if total_words > MIN_WORDS_FOR_CONV_MARKERS and conv_count == 0:
        hits.append(
            f"  No conversational markers found in {total_words} words "
            f"— natural writing uses 'actually', 'honestly', 'turns out', etc."
        )

    # Conjunction starters absence (And/But/So at sentence start = human)
    conj_ratio = 1.0  # default: assume present (no flag)
    if len(sentences) >= 5:
        conj_start_count = sum(
            1 for s in sentences if s.split()[0].lower() in CONJUNCTION_STARTERS
        )
        conj_ratio = conj_start_count / len(sentences)
        if conj_ratio < CONJ_START_RATIO_THRESHOLD:
            hits.append(
                f"  No conjunction starters: 0/{len(sentences)} sentences start "
                f"with And/But/So — human writing does this naturally"
            )

    # Composite score — fixed-weight signals, normalized by evaluated weight.
    # Each signal has a predetermined weight. When insufficient text prevents
    # evaluation, the signal is skipped and its weight excluded from the total.
    signals: list[tuple[float, float]] = []  # (weight, score)
    if total_words > 0:
        signals.append((0.15, min(1.0, (hedge_count / (total_words / 100)) / 4.0)))
        signals.append((0.10, min(1.0, enthusiasm_count / 6.0)))
        signals.append((0.10, min(1.0, abstract_count / (total_words / 100) / 6.0)))
        if alpha_words:
            signals.append((0.10, min(1.0, max(0, (avg_wl - 4.5)) / 1.5)))
            signals.append((0.08, min(1.0, max(0, long_ratio - 0.08) / 0.15)))
        signals.append((0.08, min(1.0, intensifier_count / 3.0)))
        if total_words > MIN_WORDS_FOR_CONV_MARKERS:
            signals.append((0.10, 0.5 if conv_count == 0 else 0.0))
        if total_words > MIN_WORDS_FOR_CONTRACTION:
            signals.append((0.10, 0.75 if contr_per_100 < LOW_CONTRACTION_PER_100 else 0.0))
        if len(sentences) >= 5 and sent_formality:
            signals.append((0.10, 1.0 if f_std < FORMALITY_STD_THRESHOLD else 0.0))
        if len(sentences) >= 5:
            signals.append((0.09, 1.0 if conj_ratio < CONJ_START_RATIO_THRESHOLD else 0.0))

    if not signals:
        return hits, 0.0
    total_weight = sum(w for w, _ in signals)
    score = sum(w * s for w, s in signals) / total_weight
    return hits, score
