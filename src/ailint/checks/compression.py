"""LZMA compression similarity — compares text against known AI corpus."""

import lzma
import os

# From corpus testing: AI leave-one-out mean ~0.47, human mean ~0.36
SIMILARITY_HIGH = 0.45
SIMILARITY_MODERATE = 0.38
# Score mapping: similarity 0.30-0.50 → score 0.0-1.0
SCORE_FLOOR = 0.30
SCORE_RANGE = 0.20
MIN_TEXT_BYTES = 100

_seed_bytes: bytes | None = None


def _load_seed() -> bytes:
    global _seed_bytes
    if _seed_bytes is not None:
        return _seed_bytes
    seed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "ai_seed_corpus.txt")
    seed_path = os.path.normpath(seed_path)
    if os.path.exists(seed_path):
        with open(seed_path) as f:
            _seed_bytes = f.read().encode("utf-8")
    else:
        _seed_bytes = b""
    return _seed_bytes


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """Compare how well text compresses when appended to a known AI corpus.
    AI-like text shares patterns with the seed, producing a higher compression ratio."""
    hits = []
    seed = _load_seed()
    if not seed:
        return hits, 0.0

    text_bytes = text.encode("utf-8")
    if len(text_bytes) < MIN_TEXT_BYTES:
        return hits, 0.0

    seed_compressed = len(lzma.compress(seed))
    combined_compressed = len(lzma.compress(seed + text_bytes))
    text_alone = len(lzma.compress(text_bytes))

    if text_alone == 0:
        return hits, 0.0
    overhead = combined_compressed - seed_compressed
    similarity = 1.0 - (overhead / text_alone)

    if similarity > SIMILARITY_HIGH:
        hits.append(
            f"  Compression similarity: {similarity:.3f} (high) "
            f"— text compresses well against AI corpus"
        )
    elif similarity > SIMILARITY_MODERATE:
        hits.append(
            f"  Compression similarity: {similarity:.3f} (moderate) "
            f"— some pattern overlap with AI corpus"
        )

    raw = max(0.0, min(1.0, (similarity - SCORE_FLOOR) / SCORE_RANGE))
    return hits, raw
