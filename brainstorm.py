#!/usr/bin/env python3
"""
Brainstorm 100 heuristic ideas and test each one's ability to
discriminate between AI and human writing samples.

For each idea, we compute a signal value on every sample, then check
if AI samples score higher than human samples (= good discriminator).
"""

import math
import os
import re
from collections import Counter

# ─────────────────────────────────────────────────────────────────────────────
# Load samples
# ─────────────────────────────────────────────────────────────────────────────

def load_samples(directory, label):
    samples = []
    for fname in sorted(os.listdir(directory)):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(directory, fname)) as f:
            text = f.read()
        samples.append({"name": fname, "label": label, "text": text})
    return samples

HUMAN = load_samples("samples/human", "human")
AI = load_samples("samples/ai", "ai")
ALL = HUMAN + AI

# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def words(text):
    return text.split()

def word_count(text):
    return len(words(text))

def sentences(text):
    clean = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    clean = re.sub(r"^[\s]*[-*]\s+", "", clean, flags=re.MULTILINE)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", clean)
    return [s.strip() for s in parts if s.strip() and len(s.split()) >= 2]

def paragraphs(text):
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip() and len(p.split()) >= 5]

def count_pattern(text, pattern, flags=0):
    return len(re.findall(pattern, text, flags))

def density(count, total, per=100):
    if total == 0:
        return 0.0
    return count / (total / per)

def std_dev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)

def unique_ratio(items):
    if not items:
        return 0.0
    return len(set(items)) / len(items)

# ─────────────────────────────────────────────────────────────────────────────
# 100 heuristic ideas — each returns a float (higher = more AI-like)
# ─────────────────────────────────────────────────────────────────────────────

HEURISTICS = {}

def h(name):
    """Decorator to register a heuristic."""
    def decorator(fn):
        HEURISTICS[name] = fn
        return fn
    return decorator

# === VOCABULARY (1-20) ===

@h("01_banned_verb_density")
def _(t):
    banned = {"delve","leverage","utilize","harness","streamline","underscore","foster",
              "embark","unlock","unveil","elevate","unleash","revolutionize","spearhead",
              "augment","facilitate","maximize","capitalize","bolster","champion",
              "cultivate","empower","enable","enhance","illuminate","optimize","unpack",
              "transcend","supercharge"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in banned)
    return density(hits, len(wds))

@h("02_banned_adj_density")
def _(t):
    banned = {"pivotal","robust","innovative","seamless","cutting-edge","meticulous",
              "multifaceted","transformative","comprehensive","crucial","essential",
              "vital","dynamic","vibrant","intricate","daunting","compelling",
              "commendable","exemplary","invaluable","synergistic","thought-provoking",
              "profound","groundbreaking","renowned","unprecedented","whimsical",
              "indelible","enduring","enigmatic","nuanced","actionable"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in banned)
    return density(hits, len(wds))

@h("03_banned_noun_density")
def _(t):
    banned = {"landscape","realm","tapestry","synergy","testament","underpinnings",
              "interplay","labyrinth","metropolis","crucible","gossamer","beacon",
              "symphony","virtuoso","enigma","nexus"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in banned)
    return density(hits, len(wds))

@h("04_avg_word_length")
def _(t):
    wds = [w for w in words(t) if w.isalpha()]
    if not wds:
        return 0
    return sum(len(w) for w in wds) / len(wds)

@h("05_long_word_ratio")
def _(t):
    wds = [w for w in words(t) if w.isalpha()]
    if not wds:
        return 0
    return sum(1 for w in wds if len(w) > 8) / len(wds)

@h("06_unique_word_ratio_inverse")
def _(t):
    """Lower lexical diversity = more AI-like. Return inverse so higher = worse."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    if not wds:
        return 0
    return 1.0 - (len(set(wds)) / len(wds))

@h("07_adverb_ly_density")
def _(t):
    """AI overuses -ly adverbs."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w.endswith("ly") and len(w) > 4)
    return density(hits, len(wds))

@h("08_abstract_noun_density")
def _(t):
    """Words ending in -tion, -ment, -ness, -ity — abstract/nominalized."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if re.match(r".*(?:tion|ment|ness|ity)$", w) and len(w) > 5)
    return density(hits, len(wds))

@h("09_gerund_density")
def _(t):
    """Words ending in -ing — AI overuses present participles."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w.endswith("ing") and len(w) > 4)
    return density(hits, len(wds))

@h("10_that_which_density")
def _(t):
    """AI uses 'that' and 'which' for relative clauses more than humans."""
    hits = count_pattern(t.lower(), r"\bthat\b|\bwhich\b")
    return density(hits, word_count(t))

@h("11_passive_voice_density")
def _(t):
    """Rough passive detection: 'is/are/was/were/been/being + past participle'."""
    hits = count_pattern(t, r"\b(?:is|are|was|were|been|being)\s+\w+(?:ed|en)\b", re.IGNORECASE)
    return density(hits, word_count(t))

@h("12_first_person_density")
def _(t):
    """Less first person = more AI-like. Return inverse."""
    hits = count_pattern(t.lower(), r"\b(?:i|me|my|mine|myself|we|us|our)\b")
    d = density(hits, word_count(t))
    return max(0, 3.0 - d)  # Invert: low first-person → high score

@h("13_second_person_density")
def _(t):
    """AI often addresses 'you' excessively."""
    hits = count_pattern(t.lower(), r"\byou(?:r|rs|rself)?\b")
    return density(hits, word_count(t))

@h("14_weasel_word_density")
def _(t):
    weasels = ["generally", "typically", "often", "usually", "commonly",
               "widely", "broadly", "largely", "mostly", "primarily"]
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in weasels)
    return density(hits, len(wds))

@h("15_hedging_phrase_density")
def _(t):
    hedges = ["it's worth", "it's important to", "it's essential",
              "one might", "one could", "it is generally"]
    tl = t.lower()
    hits = sum(tl.count(h) for h in hedges)
    return density(hits, word_count(t))

@h("16_intensifier_density")
def _(t):
    """Words like 'very', 'highly', 'extremely', 'incredibly', 'truly'."""
    intensifiers = {"very", "highly", "extremely", "incredibly", "truly",
                    "absolutely", "remarkably", "significantly", "particularly",
                    "exceptionally", "tremendously", "profoundly"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in intensifiers)
    return density(hits, len(wds))

@h("17_comparative_superlative_density")
def _(t):
    """More/most + adjective patterns."""
    hits = count_pattern(t, r"\b(?:more|most)\s+\w+(?:ly)?\b", re.IGNORECASE)
    return density(hits, word_count(t))

@h("18_contraction_rate_inverse")
def _(t):
    """Low contractions = overly formal."""
    contractions = count_pattern(t, r"\b\w+'(?:t|re|ve|ll|s|d|m)\b", re.IGNORECASE)
    d = density(contractions, word_count(t))
    return max(0, 2.0 - d)

@h("19_determiner_density")
def _(t):
    """AI uses more determiners (the, a, an, this, these, those)."""
    dets = {"the", "a", "an", "this", "that", "these", "those", "each", "every"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in dets)
    return density(hits, len(wds))

@h("20_conjunction_starter_density")
def _(t):
    """Sentences starting with And/But/So/Or — human-like. Inverse."""
    sents = sentences(t)
    if not sents:
        return 0
    conj = {"and", "but", "so", "or", "yet"}
    hits = sum(1 for s in sents if s.split()[0].lower() in conj)
    d = hits / len(sents)
    return max(0, 0.3 - d)  # More conjunctions = more human = lower score

# === SENTENCE STRUCTURE (21-40) ===

@h("21_sentence_length_std_dev_inverse")
def _(t):
    """Low burstiness (uniform sentence length) = AI-like."""
    sents = sentences(t)
    if len(sents) < 3:
        return 0
    lengths = [len(s.split()) for s in sents]
    sd = std_dev(lengths)
    return max(0, 10 - sd)  # Low std dev = high score

@h("22_avg_sentence_length")
def _(t):
    """AI tends toward medium-length sentences (15-20 words)."""
    sents = sentences(t)
    if not sents:
        return 0
    avg = sum(len(s.split()) for s in sents) / len(sents)
    # Distance from the "AI sweet spot" of 17 words
    return max(0, 5 - abs(avg - 17))

@h("23_short_sentence_ratio_inverse")
def _(t):
    """Fewer short sentences (<8 words) = more AI-like."""
    sents = sentences(t)
    if not sents:
        return 0
    short = sum(1 for s in sents if len(s.split()) < 8)
    ratio = short / len(sents)
    return max(0, 0.3 - ratio)

@h("24_long_sentence_ratio")
def _(t):
    """More uniformly long sentences = AI-like."""
    sents = sentences(t)
    if not sents:
        return 0
    long_s = sum(1 for s in sents if len(s.split()) > 25)
    return long_s / len(sents)

@h("25_sentence_fragment_ratio_inverse")
def _(t):
    """Fewer fragments = more AI-like."""
    clean = re.sub(r"^#{1,6}\s+", "", t, flags=re.MULTILINE)
    parts = re.split(r"(?<=[.!?])\s+", clean)
    fragments = [p for p in parts if p.strip() and 1 <= len(p.split()) < 3]
    total = len([p for p in parts if p.strip()])
    if total == 0:
        return 0
    ratio = len(fragments) / total
    return max(0, 0.1 - ratio)

@h("26_participial_ending_density")
def _(t):
    hits = count_pattern(t, r",\s+\w+ing\s+[\w\s]+[.!?]$", re.MULTILINE)
    sents = sentences(t)
    return density(hits, max(1, len(sents)), per=10)

@h("27_negative_parallelism_count")
def _(t):
    pat = (r"(?:it'?s not .{3,40}(?:,|—|-{1,2})\s*it'?s|"
           r"it'?s less about .{3,40} and more about|"
           r"not just .{3,40},?\s*but also|"
           r"more than just .{3,40}\.\s*it'?s)")
    return count_pattern(t, pat, re.IGNORECASE)

@h("28_rhetorical_question_density")
def _(t):
    """AI poses questions then immediately answers them."""
    hits = count_pattern(t, r"(?:^|\. )(?:The|What|Why|How) [^.?]{3,40}\?\s+[A-Z]", re.MULTILINE)
    return density(hits, word_count(t), per=500)

@h("29_semicolon_density")
def _(t):
    """AI uses semicolons at higher rates."""
    hits = t.count(";")
    return density(hits, word_count(t), per=500)

@h("30_colon_density")
def _(t):
    """Colons for introducing lists/explanations."""
    hits = t.count(":")
    return density(hits, word_count(t), per=500)

@h("31_parenthetical_density")
def _(t):
    hits = t.count("(")
    return density(hits, word_count(t), per=500)

@h("32_em_dash_density")
def _(t):
    hits = len(re.findall(r"—|–|(?<!\w)--(?!\w)", t))
    return density(hits, word_count(t), per=500)

@h("33_comma_density")
def _(t):
    hits = t.count(",")
    return density(hits, word_count(t))

@h("34_consecutive_similar_length")
def _(t):
    """Count streaks of 3+ similar-length sentences."""
    sents = sentences(t)
    if len(sents) < 3:
        return 0
    lengths = [len(s.split()) for s in sents]
    streaks = 0
    run = 1
    for i in range(1, len(lengths)):
        if abs(lengths[i] - lengths[i-1]) <= 3:
            run += 1
        else:
            if run >= 3:
                streaks += 1
            run = 1
    if run >= 3:
        streaks += 1
    return streaks

@h("35_sentence_start_variety")
def _(t):
    """How many unique first words / total sentences. Less variety = more AI."""
    sents = sentences(t)
    if len(sents) < 3:
        return 0
    starters = [s.split()[0].lower() for s in sents if s.split()]
    variety = len(set(starters)) / len(starters)
    return max(0, 1.0 - variety)

@h("36_questions_per_paragraph")
def _(t):
    """AI rarely asks genuine questions."""
    paras = paragraphs(t)
    if not paras:
        return 0
    total_q = t.count("?")
    return max(0, 0.5 - total_q / max(1, len(paras)))

@h("37_exclamation_absence")
def _(t):
    """Some AI avoids exclamations; some overuses. Measure presence."""
    return density(t.count("!"), word_count(t), per=500)

@h("38_sentence_ending_variety")
def _(t):
    """If every sentence ends with period (no ? or !), less variety."""
    sents = sentences(t)
    if not sents:
        return 0
    endings = [s[-1] if s else "." for s in sents]
    unique = len(set(endings))
    return max(0, 3 - unique)  # Only . = score 2; . and ? = score 1

@h("39_appositive_density")
def _(t):
    """Comma-enclosed appositives: ', which ..., ' or ', a ... ,'"""
    hits = count_pattern(t, r",\s+(?:which|who|where|a\s+\w+)\s+[^,]{5,40},", re.IGNORECASE)
    return density(hits, word_count(t), per=500)

@h("40_coordinating_conjunction_mid_sentence")
def _(t):
    """Count 'and' and 'but' mid-sentence (not at start). Higher = AI padding."""
    hits = count_pattern(t, r"(?<!^)\b(?:and|but)\b", re.IGNORECASE | re.MULTILINE)
    return density(hits, word_count(t))

# === PARAGRAPH / DOCUMENT STRUCTURE (41-60) ===

@h("41_paragraph_count_near_five")
def _(t):
    """Five-paragraph essay signal."""
    n = len(paragraphs(t))
    return max(0, 3 - abs(n - 5))

@h("42_paragraph_length_uniformity")
def _(t):
    paras = paragraphs(t)
    if len(paras) < 3:
        return 0
    lengths = [len(p.split()) for p in paras]
    sd = std_dev(lengths)
    return max(0, 30 - sd)  # Low variance = high score

@h("43_paragraph_sentence_count_uniformity")
def _(t):
    paras = paragraphs(t)
    if len(paras) < 3:
        return 0
    counts = [len(sentences(p)) for p in paras]
    sd = std_dev(counts)
    return max(0, 2 - sd)

@h("44_intro_conclusion_overlap")
def _(t):
    """Word overlap between first and last paragraph."""
    paras = paragraphs(t)
    if len(paras) < 3:
        return 0
    w1 = set(paras[0].lower().split())
    w2 = set(paras[-1].lower().split())
    if not w1 or not w2:
        return 0
    return len(w1 & w2) / min(len(w1), len(w2))

@h("45_topic_sentence_ratio")
def _(t):
    """How many paragraphs start with a sentence that previews content.
    Heuristic: first sentence contains 'is', 'are', 'has', 'have' (definitional)."""
    paras = paragraphs(t)
    if not paras:
        return 0
    topic_starters = 0
    for p in paras:
        first_sent = sentences(p)
        if first_sent:
            fl = first_sent[0].lower()
            if any(w in fl for w in [" is ", " are ", " has ", " have ", " was ", " were "]):
                topic_starters += 1
    return topic_starters / len(paras)

@h("46_list_density")
def _(t):
    """Bullet points and numbered lists per 500 words."""
    hits = count_pattern(t, r"^[\s]*(?:[-*]|\d+\.)\s+", re.MULTILINE)
    return density(hits, word_count(t), per=500)

@h("47_bold_text_density")
def _(t):
    hits = count_pattern(t, r"\*\*[^*]+\*\*")
    return density(hits, word_count(t), per=500)

@h("48_header_density")
def _(t):
    hits = count_pattern(t, r"^#{1,6}\s+", re.MULTILINE)
    return density(hits, word_count(t), per=500)

@h("49_single_sentence_paragraph_ratio_inverse")
def _(t):
    """Fewer single-sentence paragraphs = more AI-like."""
    paras = paragraphs(t)
    if not paras:
        return 0
    singles = sum(1 for p in paras if len(sentences(p)) <= 1)
    ratio = singles / len(paras)
    return max(0, 0.2 - ratio)

@h("50_section_word_count_uniformity")
def _(t):
    """If text has headers, check uniformity of section lengths."""
    sections = re.split(r"^#{1,6}\s+.*$", t, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip() and len(s.split()) > 10]
    if len(sections) < 2:
        return 0
    lengths = [len(s.split()) for s in sections]
    sd = std_dev(lengths)
    return max(0, 40 - sd)

@h("51_transition_word_density")
def _(t):
    transitions = ["furthermore", "moreover", "additionally", "consequently",
                   "subsequently", "accordingly", "nevertheless", "nonetheless",
                   "however", "therefore", "thus", "hence", "meanwhile",
                   "conversely", "alternatively", "specifically", "notably"]
    tl = t.lower()
    wds = [w.strip(".,!?;:\"'()") for w in tl.split()]
    hits = sum(1 for w in wds if w in transitions)
    return density(hits, len(wds))

@h("52_signpost_phrase_density")
def _(t):
    """'First...Second...Third', 'On one hand...on the other'."""
    signposts = [r"\bfirst(?:ly)?\b", r"\bsecond(?:ly)?\b", r"\bthird(?:ly)?\b",
                 r"\bon one hand\b", r"\bon the other hand\b",
                 r"\bin addition\b", r"\bfor example\b", r"\bfor instance\b"]
    tl = t.lower()
    hits = sum(len(re.findall(p, tl)) for p in signposts)
    return density(hits, word_count(t), per=500)

@h("53_scope_disclaimer_present")
def _(t):
    pat = (r"(?:not\s+(?:an?\s+)?exhaustive|beyond\s+the\s+scope|"
           r"there\s+are[,\s]+of\s+course[,\s]+(?:important\s+)?caveats|"
           r"this\s+analysis\s+has\s+(?:certain\s+)?limitations)")
    return count_pattern(t, pat, re.IGNORECASE)

@h("54_numbered_list_density")
def _(t):
    hits = count_pattern(t, r"^\s*\d+\.\s+", re.MULTILINE)
    return density(hits, word_count(t), per=500)

@h("55_tricolon_density")
def _(t):
    """X, Y, and Z patterns per 500 words."""
    hits = count_pattern(t, r"\b\w+,\s+\w+,?\s+and\s+\w+\b", re.IGNORECASE)
    return density(hits, word_count(t), per=500)

@h("56_analogy_stacking")
def _(t):
    return count_pattern(t, r"just\s+as\s+.{10,80}just\s+as\s+", re.IGNORECASE)

@h("57_both_sides_pattern")
def _(t):
    return count_pattern(t, r"on\s+(?:the\s+)?one\s+hand\b", re.IGNORECASE)

@h("58_conclusion_keyword_present")
def _(t):
    """'In conclusion', 'To summarize', 'Key takeaway' etc."""
    closers = ["in conclusion", "to summarize", "in summary", "key takeaway",
               "to wrap up", "to wrap things up", "in closing"]
    tl = t.lower()
    return sum(1 for c in closers if c in tl)

@h("59_preview_intro_present")
def _(t):
    """Intro paragraph that previews structure: 'we'll explore', 'this article'."""
    paras = paragraphs(t)
    if not paras:
        return 0
    fl = paras[0].lower()
    previews = ["will explore", "will discuss", "will examine", "this article",
                "this essay", "this guide", "in this post", "we'll look at",
                "let's explore", "let's dive", "we will"]
    return sum(1 for p in previews if p in fl)

@h("60_fractal_summary_density")
def _(t):
    """Paragraphs where first and last sentence overlap significantly."""
    paras = paragraphs(t)
    hits = 0
    for p in paras:
        sents = sentences(p)
        if len(sents) >= 3:
            w1 = set(sents[0].lower().split())
            w2 = set(sents[-1].lower().split())
            if w1 and w2:
                overlap = len(w1 & w2) / min(len(w1), len(w2))
                if overlap > 0.5:
                    hits += 1
    return hits

# === TONE / STYLE (61-80) ===

@h("61_enthusiasm_word_density")
def _(t):
    enth = {"exciting","excited","thrilled","thrilling","fascinating","incredible",
            "amazing","wonderful","remarkable","extraordinary","fantastic",
            "tremendous","awesome","brilliant","magnificent","spectacular",
            "phenomenal","stunning","breathtaking"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in enth)
    return density(hits, len(wds))

@h("62_formality_avg_word_length")
def _(t):
    """Higher average word length = more formal/AI-like."""
    wds = [w for w in words(t) if w.isalpha()]
    if not wds:
        return 0
    return sum(len(w) for w in wds) / len(wds)

@h("63_formality_variance")
def _(t):
    """Low variance in per-sentence avg word length = uniform register = AI."""
    sents = sentences(t)
    if len(sents) < 5:
        return 0
    avgs = []
    for s in sents:
        wds = [w for w in s.split() if w.isalpha()]
        if wds:
            avgs.append(sum(len(w) for w in wds) / len(wds))
    if not avgs:
        return 0
    sd = std_dev(avgs)
    return max(0, 1.5 - sd)

@h("64_polite_phrase_density")
def _(t):
    polite = ["please", "thank you", "appreciate", "grateful", "kind regards",
              "warm regards", "best regards", "sincerely", "respectfully"]
    tl = t.lower()
    return sum(tl.count(p) for p in polite)

@h("65_confident_vs_hedged")
def _(t):
    """Ratio of hedging words to total. Higher = more AI-like."""
    hedges = {"might","could","perhaps","generally","somewhat","often","potentially",
              "possibly","typically","arguably","likely","maybe","probably"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in hedges)
    return density(hits, len(wds))

@h("66_emotional_word_density")
def _(t):
    """AI uses emotion words less naturally (either absent or formulaic)."""
    emotions = {"angry","sad","happy","afraid","love","hate","frustrated","anxious",
                "excited","nervous","proud","ashamed","guilty","jealous","confused",
                "surprised","disgusted","hopeful","desperate","grateful","annoyed",
                "miserable","thrilled","terrified","furious"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in emotions)
    # Very low or very high = suspicious. Mid is human.
    d = density(hits, len(wds))
    return max(0, 0.3 - d) if d < 0.5 else 0

@h("67_impersonal_construction_density")
def _(t):
    """'It is...', 'There are...' — impersonal constructions."""
    hits = count_pattern(t, r"\b(?:it is|it's|there (?:is|are|was|were))\b", re.IGNORECASE)
    return density(hits, word_count(t))

@h("68_modal_verb_density")
def _(t):
    """can, could, should, would, may, might — AI hedges with modals."""
    modals = {"can", "could", "should", "would", "may", "might", "shall", "must"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in modals)
    return density(hits, len(wds))

@h("69_cliche_density")
def _(t):
    cliches = ["at the end of the day", "it goes without saying",
               "needless to say", "few and far between", "the fact of the matter",
               "when all is said and done", "in this day and age",
               "it is what it is", "only time will tell",
               "last but not least", "tip of the iceberg"]
    tl = t.lower()
    return sum(tl.count(c) for c in cliches)

@h("70_corporate_jargon_density")
def _(t):
    jargon = {"stakeholder", "synergize", "bandwidth", "deliverable", "scalable",
              "paradigm", "ecosystem", "value-add", "best-in-class", "end-to-end",
              "cross-functional", "alignment", "visibility", "cadence", "touchpoint"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in jargon)
    return density(hits, len(wds))

@h("71_certainty_marker_absence")
def _(t):
    """Words like 'clearly', 'obviously', 'definitely', 'certainly'. AI avoids these."""
    certain = {"clearly", "obviously", "definitely", "certainly", "undoubtedly",
               "absolutely", "plainly", "undeniably"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    hits = sum(1 for w in wds if w in certain)
    return max(0, 0.5 - density(hits, len(wds)))

@h("72_qualifer_stacking")
def _(t):
    """Multiple qualifiers in same sentence: 'quite potentially rather significant'."""
    quals = {"quite", "rather", "fairly", "somewhat", "relatively", "comparatively",
             "potentially", "arguably", "perhaps"}
    sents = sentences(t)
    stacked = 0
    for s in sents:
        wds = [w.lower().strip(".,!?;:\"'()") for w in s.split()]
        count = sum(1 for w in wds if w in quals)
        if count >= 2:
            stacked += 1
    return stacked

@h("73_filler_phrase_density")
def _(t):
    fillers = ["in terms of", "with regard to", "with respect to", "in order to",
               "for the purpose of", "on the basis of", "in the context of",
               "by means of", "as a matter of fact", "as a result of"]
    tl = t.lower()
    hits = sum(tl.count(f) for f in fillers)
    return density(hits, word_count(t), per=500)

@h("74_direct_address_ratio")
def _(t):
    """Imperative sentences or direct instructions."""
    sents = sentences(t)
    if not sents:
        return 0
    imperative_starts = {"don't", "do", "make", "try", "use", "start",
                         "stop", "keep", "let", "remember", "consider",
                         "ensure", "avoid", "think", "check"}
    hits = sum(1 for s in sents if s.split()[0].lower() in imperative_starts)
    return hits / len(sents)

@h("75_said_synonym_cycling")
def _(t):
    """AI avoids repeating 'said', cycles through synonyms."""
    said_syns = {"stated", "mentioned", "noted", "remarked", "observed",
                 "explained", "emphasized", "highlighted", "pointed out",
                 "acknowledged", "argued", "suggested", "indicated"}
    tl = t.lower()
    hits = sum(tl.count(s) for s in said_syns)
    return hits

@h("76_anaphora_score")
def _(t):
    skip = {"i", "the", "a", "an", "it", "he", "she", "we", "they",
            "this", "that", "but", "and", "so", "if", "or", "my"}
    sents = sentences(t)
    if len(sents) < 3:
        return 0
    starters = [s.split()[0].lower() for s in sents if s.split()]
    runs = 0
    i = 0
    while i < len(starters) - 2:
        if starters[i] in skip:
            i += 1
            continue
        run = 1
        while i + run < len(starters) and starters[i + run] == starters[i]:
            run += 1
        if run >= 3:
            runs += 1
            i += run
        else:
            i += 1
    return runs

@h("77_clause_chain_density")
def _(t):
    """Sentences with 3+ commas — long clause chains."""
    sents = sentences(t)
    if not sents:
        return 0
    hits = sum(1 for s in sents if s.count(",") >= 3)
    return hits / len(sents)

@h("78_abstract_to_concrete_ratio")
def _(t):
    """Abstract words (ending -tion/-ment/-ness/-ity) vs concrete (short, common)."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    abstract = sum(1 for w in wds if re.match(r".*(?:tion|ment|ness|ity)$", w) and len(w) > 5)
    concrete = sum(1 for w in wds if len(w) <= 5)
    if concrete == 0:
        return 0
    return abstract / concrete

@h("79_noun_phrase_length")
def _(t):
    """Longer noun phrases (adj adj adj noun) = more AI-like."""
    # Rough: count sequences of 3+ capitalized/lowercase words before a common verb
    hits = count_pattern(t, r"(?:\b[a-z]+\s+){3,}\b(?:is|are|was|were|has|have)\b", re.IGNORECASE)
    return density(hits, word_count(t), per=500)

@h("80_sentence_ending_preposition_inverse")
def _(t):
    """Sentences ending with prepositions = human-like. Fewer = more AI."""
    preps = {"to", "for", "with", "from", "about", "at", "in", "on", "of", "by", "up"}
    sents = sentences(t)
    if not sents:
        return 0
    hits = 0
    for s in sents:
        last_word = re.sub(r"[.!?]$", "", s).split()[-1].lower() if s.split() else ""
        if last_word in preps:
            hits += 1
    ratio = hits / len(sents)
    return max(0, 0.05 - ratio)

# === STATISTICAL / INFORMATION-THEORETIC (81-100) ===

@h("81_type_token_ratio_inverse")
def _(t):
    """Lower TTR = less lexical diversity = more AI."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    if len(wds) < 50:
        return 0
    ttr = len(set(wds)) / len(wds)
    return max(0, 0.8 - ttr)

@h("82_hapax_ratio_inverse")
def _(t):
    """Hapax legomena (words used exactly once) / total. Lower = more AI."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    if len(wds) < 50:
        return 0
    freq = Counter(wds)
    hapax = sum(1 for w, c in freq.items() if c == 1)
    ratio = hapax / len(wds)
    return max(0, 0.5 - ratio)

@h("83_word_frequency_uniformity")
def _(t):
    """AI text has more uniform word frequency distribution."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    if len(wds) < 50:
        return 0
    freq = Counter(wds)
    counts = sorted(freq.values(), reverse=True)
    # Ratio of top-10 word frequency to median
    if len(counts) < 10:
        return 0
    top10_avg = sum(counts[:10]) / 10
    median = counts[len(counts) // 2]
    if median == 0:
        return 0
    return max(0, 5 - (top10_avg / median))

@h("84_readability_flesch_kincaid")
def _(t):
    """Rough Flesch-Kincaid grade level. AI tends toward consistent 10-12."""
    wds = [w for w in words(t) if w.isalpha()]
    sents = sentences(t)
    if not sents or not wds:
        return 0
    # Rough syllable count
    def syllables(word):
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for i in range(1, len(word)):
            if word[i] in vowels and word[i-1] not in vowels:
                count += 1
        if word.endswith("e"):
            count -= 1
        return max(1, count)
    total_syl = sum(syllables(w) for w in wds)
    grade = 0.39 * (len(wds)/len(sents)) + 11.8 * (total_syl/len(wds)) - 15.59
    # Distance from AI sweet spot (grade 10-12)
    return max(0, 3 - abs(grade - 11))

@h("85_readability_consistency")
def _(t):
    """Low variance in per-paragraph readability = AI-like."""
    paras = paragraphs(t)
    if len(paras) < 3:
        return 0
    def para_avg_word_len(p):
        wds = [w for w in p.split() if w.isalpha()]
        return sum(len(w) for w in wds) / max(1, len(wds))
    scores = [para_avg_word_len(p) for p in paras]
    sd = std_dev(scores)
    return max(0, 1.0 - sd)

@h("86_bigram_repetition")
def _(t):
    """Repeated 2-word combinations — AI recycles phrases."""
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    if len(wds) < 20:
        return 0
    bigrams = [f"{wds[i]} {wds[i+1]}" for i in range(len(wds)-1)]
    freq = Counter(bigrams)
    repeated = sum(1 for bg, c in freq.items() if c >= 3)
    return repeated

@h("87_trigram_repetition")
def _(t):
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    if len(wds) < 30:
        return 0
    trigrams = [f"{wds[i]} {wds[i+1]} {wds[i+2]}" for i in range(len(wds)-2)]
    freq = Counter(trigrams)
    repeated = sum(1 for tg, c in freq.items() if c >= 2)
    return repeated

@h("88_stop_word_ratio")
def _(t):
    """AI uses more function/stop words."""
    stops = {"the","a","an","is","are","was","were","be","been","being","have","has",
             "had","do","does","did","will","would","shall","should","may","might",
             "can","could","must","of","in","to","for","with","on","at","by","from",
             "as","into","about","between","through","during","before","after"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    if not wds:
        return 0
    hits = sum(1 for w in wds if w in stops)
    return hits / len(wds)

@h("89_sentence_length_range")
def _(t):
    """Range between shortest and longest sentence. Narrow range = AI."""
    sents = sentences(t)
    if len(sents) < 3:
        return 0
    lengths = [len(s.split()) for s in sents]
    rng = max(lengths) - min(lengths)
    return max(0, 30 - rng)

@h("90_paragraph_length_range")
def _(t):
    paras = paragraphs(t)
    if len(paras) < 3:
        return 0
    lengths = [len(p.split()) for p in paras]
    rng = max(lengths) - min(lengths)
    return max(0, 80 - rng)

@h("91_opening_word_entropy")
def _(t):
    """Low entropy of sentence-starting words = repetitive/AI."""
    sents = sentences(t)
    if len(sents) < 5:
        return 0
    starters = [s.split()[0].lower() for s in sents if s.split()]
    freq = Counter(starters)
    total = len(starters)
    entropy = -sum((c/total) * math.log2(c/total) for c in freq.values() if c > 0)
    max_entropy = math.log2(total) if total > 0 else 1
    return max(0, 1.0 - (entropy / max_entropy if max_entropy > 0 else 0))

@h("92_punctuation_diversity")
def _(t):
    """Fewer punctuation types = more AI-like."""
    punct_types = set()
    for ch in t:
        if ch in ".,;:!?-—–()[]{}\"'...":
            punct_types.add(ch)
    return max(0, 8 - len(punct_types))

@h("93_avg_paragraph_sentences")
def _(t):
    """AI tends toward 3-4 sentences per paragraph."""
    paras = paragraphs(t)
    if not paras:
        return 0
    avg = sum(len(sentences(p)) for p in paras) / len(paras)
    return max(0, 3 - abs(avg - 3.5))

@h("94_semantic_density")
def _(t):
    """Content words / total words. AI tends toward lower semantic density (more filler)."""
    stops = {"the","a","an","is","are","was","were","be","been","being","have","has",
             "had","do","does","did","will","would","shall","should","may","might",
             "can","could","must","of","in","to","for","with","on","at","by","from",
             "as","into","about","between","through","it","its","and","but","or",
             "not","no","this","that","these","those","so","if","then","than"}
    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t)]
    if not wds:
        return 0
    content = sum(1 for w in wds if w not in stops and len(w) > 2)
    ratio = content / len(wds)
    return max(0, 0.6 - ratio)

@h("95_repetitive_structure_score")
def _(t):
    """Sentences with identical POS-like structure (same length, same starter pattern)."""
    sents = sentences(t)
    if len(sents) < 5:
        return 0
    # Rough fingerprint: (first_word, word_count, last_word)
    prints = [(s.split()[0].lower(), len(s.split()), s.split()[-1].lower().rstrip(".!?"))
              for s in sents if s.split()]
    freq = Counter(prints)
    dupes = sum(c - 1 for c in freq.values() if c > 1)
    return density(dupes, len(sents), per=10)

@h("96_paragraph_starter_variety")
def _(t):
    """Low variety in paragraph-starting words = AI template."""
    paras = paragraphs(t)
    if len(paras) < 3:
        return 0
    starters = [p.split()[0].lower() for p in paras if p.split()]
    variety = len(set(starters)) / len(starters)
    return max(0, 1.0 - variety)

@h("97_numeric_data_presence_inverse")
def _(t):
    """Specific numbers/data = more human. Absence = more AI."""
    nums = count_pattern(t, r"\b\d+(?:\.\d+)?%?\b")
    d = density(nums, word_count(t), per=500)
    return max(0, 1.0 - d)

@h("98_quote_or_citation_presence_inverse")
def _(t):
    """Direct quotes or citations = more human. Absence = AI."""
    quotes = count_pattern(t, r'"[^"]{10,}"')
    names = count_pattern(t, r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
    return max(0, 2 - (quotes + names * 0.5))

@h("99_conversational_markers_inverse")
def _(t):
    """Informal markers: interjections, slang, hedging humor. Absence = AI."""
    markers = ["honestly", "actually", "basically", "literally", "obviously",
               "look,", "i mean", "right?", "you know", "kind of", "sort of",
               "pretty much", "turns out", "ended up", "wound up"]
    tl = t.lower()
    hits = sum(tl.count(m) for m in markers)
    return max(0, 3 - hits)

@h("100_overall_predictability")
def _(t):
    """Combine: low burstiness + uniform paragraphs + formal vocab = predictable AI."""
    sents = sentences(t)
    if len(sents) < 5:
        return 0
    lengths = [len(s.split()) for s in sents]
    burst = std_dev(lengths)

    wds = [w.lower().strip(".,!?;:\"'()") for w in words(t) if w.isalpha()]
    avg_wl = sum(len(w) for w in wds) / max(1, len(wds))

    paras = paragraphs(t)
    para_uniformity = 0
    if len(paras) >= 3:
        para_lens = [len(p.split()) for p in paras]
        para_uniformity = max(0, 30 - std_dev(para_lens))

    # Combine signals
    score = max(0, 10 - burst) + (avg_wl - 4) * 2 + para_uniformity / 10
    return score

# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────

def evaluate():
    results = []

    for name, fn in sorted(HEURISTICS.items()):
        human_scores = []
        ai_scores = []

        for sample in HUMAN:
            try:
                val = fn(sample["text"])
                human_scores.append(val)
            except Exception:
                human_scores.append(0)

        for sample in AI:
            try:
                val = fn(sample["text"])
                ai_scores.append(val)
            except Exception:
                ai_scores.append(0)

        human_avg = sum(human_scores) / len(human_scores) if human_scores else 0
        ai_avg = sum(ai_scores) / len(ai_scores) if ai_scores else 0
        gap = ai_avg - human_avg

        # Normalized gap: how many standard deviations apart
        all_scores = human_scores + ai_scores
        overall_sd = std_dev(all_scores) if len(all_scores) >= 2 else 1
        normalized_gap = gap / overall_sd if overall_sd > 0 else 0

        # Check for any overlap (does any human score >= lowest AI score?)
        overlap = False
        if human_scores and ai_scores:
            overlap = max(human_scores) >= min(ai_scores)

        results.append({
            "name": name,
            "human_avg": human_avg,
            "ai_avg": ai_avg,
            "gap": gap,
            "normalized_gap": normalized_gap,
            "overlap": overlap,
            "human_scores": human_scores,
            "ai_scores": ai_scores,
        })

    # Sort by normalized gap (best discriminators first)
    results.sort(key=lambda r: r["normalized_gap"], reverse=True)

    print(f"{'#':<4} {'Heuristic':<45} {'H avg':>7} {'AI avg':>7} {'Gap':>7} {'Norm':>6} {'Sep':>4}")
    print("─" * 90)

    winners = []
    for i, r in enumerate(results):
        sep = "YES" if not r["overlap"] else "no"
        marker = " ***" if r["normalized_gap"] > 0.8 and not r["overlap"] else \
                 " **" if r["normalized_gap"] > 0.8 else \
                 " *" if r["normalized_gap"] > 0.5 else ""
        print(f"{i+1:<4} {r['name']:<45} {r['human_avg']:>7.2f} {r['ai_avg']:>7.2f} "
              f"{r['gap']:>7.2f} {r['normalized_gap']:>6.2f} {sep:>4}{marker}")
        if r["normalized_gap"] > 0.5:
            winners.append(r)

    print(f"\n{'─' * 90}")
    print(f"Total heuristics: {len(results)}")
    print(f"Strong discriminators (norm gap > 0.5): {len(winners)}")
    print(f"Perfect separation (no overlap): {sum(1 for r in results if not r['overlap'])}")

    # Show top 20 detail
    print(f"\n{'═' * 90}")
    print("TOP 20 — Detailed scores")
    print(f"{'═' * 90}")
    for r in results[:20]:
        h_str = ", ".join(f"{s:.2f}" for s in r["human_scores"])
        a_str = ", ".join(f"{s:.2f}" for s in r["ai_scores"])
        sep = "CLEAN SEP" if not r["overlap"] else "overlap"
        print(f"\n{r['name']} (norm gap: {r['normalized_gap']:.2f}, {sep})")
        print(f"  Human: [{h_str}]")
        print(f"  AI:    [{a_str}]")


if __name__ == "__main__":
    evaluate()
