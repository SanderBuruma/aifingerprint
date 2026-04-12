#!/usr/bin/env python3
"""Test new heuristics 1-by-1 against the full corpus to measure AI/human separation."""

import lzma
import math
import os
import re
import zlib
from collections import Counter

SAMPLE_DIRS = {
    "ai": ["samples/ai", "samples/ai_corpus"],
    "human": ["samples/human", "samples/human_corpus"],
}


def load_corpus():
    """Load all sample texts, return dict of {label: [(text, filename), ...]}."""
    corpus = {"ai": [], "human": []}
    for label, dirs in SAMPLE_DIRS.items():
        for d in dirs:
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if not f.endswith(".txt"):
                    continue
                path = os.path.join(d, f)
                with open(path) as fh:
                    text = fh.read()
                if text.strip():
                    corpus[label].append((text, f))
    return corpus


def build_ai_seed():
    """Build a compression seed from all AI samples for ZipPy-style detection."""
    texts = []
    for d in SAMPLE_DIRS["ai"]:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".txt"):
                with open(os.path.join(d, f)) as fh:
                    texts.append(fh.read())
    return "\n\n".join(texts)


# ─────────────────────────────────────────────────────────────────────────────
# HEURISTIC FUNCTIONS — each returns a float score (higher = more AI-like)
# ─────────────────────────────────────────────────────────────────────────────

def h_compression_ratio(text, ai_seed_bytes):
    """ZipPy-style: how well does the text compress when appended to AI seed corpus?
    Higher ratio = more similar to AI text = more AI-like."""
    text_bytes = text.encode("utf-8")
    seed_compressed = len(lzma.compress(ai_seed_bytes))
    combined_compressed = len(lzma.compress(ai_seed_bytes + text_bytes))
    text_alone = len(lzma.compress(text_bytes))
    # How much extra compression the seed provides for this text
    # If text is AI-like, the combined compresses better (less overhead)
    overhead = combined_compressed - seed_compressed
    if text_alone == 0:
        return 0.0
    # Ratio: lower overhead relative to standalone = more AI-like
    # Invert so higher = more AI-like
    return 1.0 - (overhead / text_alone)


def h_compression_ratio_zlib(text, ai_seed_bytes):
    """Same as above but with zlib (faster, different characteristics)."""
    text_bytes = text.encode("utf-8")
    seed_compressed = len(zlib.compress(ai_seed_bytes))
    combined_compressed = len(zlib.compress(ai_seed_bytes + text_bytes))
    text_alone = len(zlib.compress(text_bytes))
    if text_alone == 0:
        return 0.0
    overhead = combined_compressed - seed_compressed
    return 1.0 - (overhead / text_alone)


def h_shannon_entropy(text):
    """Shannon entropy of word distribution. Lower = more predictable = more AI-like.
    Returns inverted so higher = more AI-like."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if not words:
        return 0.0
    freqs = Counter(words)
    total = len(words)
    entropy = -sum((c / total) * math.log2(c / total) for c in freqs.values())
    # Invert: lower entropy = more AI-like, so return negative
    # Normalize roughly to 0-1 range (typical entropy is 6-10 for text)
    return max(0.0, 10.0 - entropy) / 10.0


def h_sentence_start_diversity(text):
    """How diverse are sentence openings? Lower diversity = more AI-like.
    Returns inverted so higher = more AI-like."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z\"])", text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.split()) >= 3]
    if len(sentences) < 5:
        return 0.0
    # Get first 2 words (bigram) of each sentence
    bigrams = []
    for s in sentences:
        words = s.split()[:2]
        bigrams.append(" ".join(w.lower() for w in words))
    unique_ratio = len(set(bigrams)) / len(bigrams)
    # Lower unique ratio = more repetitive = more AI-like
    return 1.0 - unique_ratio


def h_zipf_deviation(text):
    """How well does word frequency follow Zipf's law?
    AI text deviates more from Zipf's distribution.
    Returns R-squared deviation (higher = worse fit = more AI-like)."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if len(words) < 50:
        return 0.0
    freqs = Counter(words)
    ranked = sorted(freqs.values(), reverse=True)
    n = len(ranked)
    if n < 10:
        return 0.0
    # Expected Zipf: freq(rank r) = freq(1) / r
    max_freq = ranked[0]
    expected = [max_freq / (r + 1) for r in range(n)]
    # R-squared
    ss_res = sum((a - e) ** 2 for a, e in zip(ranked, expected))
    mean_actual = sum(ranked) / n
    ss_tot = sum((a - mean_actual) ** 2 for a in ranked)
    if ss_tot == 0:
        return 0.0
    r_squared = 1.0 - (ss_res / ss_tot)
    # Higher R-squared = better Zipf fit = more human-like
    # Invert: lower fit = more AI-like
    return max(0.0, 1.0 - r_squared)


def h_hapax_ratio(text):
    """Ratio of words appearing exactly once. Lower = more AI-like (less unique vocab).
    Returns inverted so higher = more AI-like."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if not words:
        return 0.0
    freqs = Counter(words)
    hapax = sum(1 for c in freqs.values() if c == 1)
    ratio = hapax / len(freqs)
    # Lower hapax ratio = more AI-like
    return 1.0 - ratio


def evaluate_heuristic(name, score_fn, corpus):
    """Evaluate a heuristic and print separation stats."""
    ai_scores = [score_fn(text) for text, _ in corpus["ai"]]
    hu_scores = [score_fn(text) for text, _ in corpus["human"]]

    ai_mean = sum(ai_scores) / len(ai_scores)
    hu_mean = sum(hu_scores) / len(hu_scores)
    ai_med = sorted(ai_scores)[len(ai_scores) // 2]
    hu_med = sorted(hu_scores)[len(hu_scores) // 2]

    gap = ai_mean - hu_mean
    # Cohen's d (effect size)
    ai_std = math.sqrt(sum((s - ai_mean) ** 2 for s in ai_scores) / len(ai_scores))
    hu_std = math.sqrt(sum((s - hu_mean) ** 2 for s in hu_scores) / len(hu_scores))
    pooled_std = math.sqrt((ai_std ** 2 + hu_std ** 2) / 2)
    cohens_d = gap / pooled_std if pooled_std > 0 else 0

    # AUC approximation (Mann-Whitney U)
    correct = 0
    total = 0
    for a in ai_scores:
        for h in hu_scores:
            total += 1
            if a > h:
                correct += 1
            elif a == h:
                correct += 0.5
    auc = correct / total if total > 0 else 0.5

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    print(f"  AI  ({len(ai_scores):3d}): mean={ai_mean:.4f}  median={ai_med:.4f}  std={ai_std:.4f}")
    print(f"  Human({len(hu_scores):3d}): mean={hu_mean:.4f}  median={hu_med:.4f}  std={hu_std:.4f}")
    print(f"  Gap: {gap:+.4f}  Cohen's d: {cohens_d:.3f}  AUC: {auc:.3f}")
    verdict = "GOOD" if auc > 0.65 else "WEAK" if auc > 0.55 else "NO SIGNAL"
    print(f"  Verdict: {verdict}")
    return {"name": name, "gap": gap, "cohens_d": cohens_d, "auc": auc}


def main():
    corpus = load_corpus()
    print(f"Corpus: {len(corpus['ai'])} AI, {len(corpus['human'])} human samples")

    # Build AI seed for compression tests
    ai_seed = build_ai_seed()
    ai_seed_bytes = ai_seed.encode("utf-8")
    print(f"AI seed corpus: {len(ai_seed_bytes)} bytes")

    results = []

    # 1. Compression ratio (LZMA)
    r = evaluate_heuristic(
        "1. Compression Ratio (LZMA / ZipPy-style)",
        lambda text: h_compression_ratio(text, ai_seed_bytes),
        corpus,
    )
    results.append(r)

    # 2. Compression ratio (zlib)
    r = evaluate_heuristic(
        "2. Compression Ratio (zlib)",
        lambda text: h_compression_ratio_zlib(text, ai_seed_bytes),
        corpus,
    )
    results.append(r)

    # 3. Shannon entropy
    r = evaluate_heuristic("3. Shannon Entropy (inverted)", h_shannon_entropy, corpus)
    results.append(r)

    # 4. Sentence-start diversity
    r = evaluate_heuristic("4. Sentence-Start Bigram Repetition", h_sentence_start_diversity, corpus)
    results.append(r)

    # 5. Zipf's law deviation
    r = evaluate_heuristic("5. Zipf's Law Deviation", h_zipf_deviation, corpus)
    results.append(r)

    # 6. Hapax legomena ratio
    r = evaluate_heuristic("6. Hapax Legomena Ratio (inverted)", h_hapax_ratio, corpus)
    results.append(r)

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY — sorted by AUC")
    print(f"{'='*60}")
    for r in sorted(results, key=lambda x: x["auc"], reverse=True):
        star = "*" if r["auc"] > 0.65 else " "
        print(f"  {star} AUC={r['auc']:.3f}  d={r['cohens_d']:+.3f}  {r['name']}")


if __name__ == "__main__":
    main()
