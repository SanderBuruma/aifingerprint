"""LZMA compression similarity — compares text against known AI corpus."""

import lzma
import sys
from importlib.resources import files

# From corpus testing: AI leave-one-out mean ~0.47, human mean ~0.36
SIMILARITY_HIGH = 0.45
SIMILARITY_MODERATE = 0.38
# Score mapping: similarity 0.30-0.50 → score 0.0-1.0
SCORE_FLOOR = 0.30
SCORE_RANGE = 0.20
MIN_TEXT_BYTES = 100
MAX_TEXT_BYTES = 1_000_000  # 1 MB — prevents CPU/memory exhaustion

_seed_bytes: bytes | None = None
_seed_compressed_len: int | None = None


def _load_seed() -> tuple[bytes, int]:
    global _seed_bytes, _seed_compressed_len
    if _seed_bytes is not None:
        return _seed_bytes, _seed_compressed_len
    try:
        _seed_bytes = (
            files("aifingerprint").joinpath("data", "ai_seed_corpus.txt")
            .read_text(encoding="utf-8")
            .encode("utf-8")
        )
        _seed_compressed_len = len(lzma.compress(_seed_bytes))
    except (FileNotFoundError, ModuleNotFoundError):
        print("warning: ai_seed_corpus.txt not found — compression check disabled", file=sys.stderr)
        _seed_bytes = b""
        _seed_compressed_len = 0
    return _seed_bytes, _seed_compressed_len


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    """Compare how well text compresses when appended to a known AI corpus.
    AI-like text shares patterns with the seed, producing a higher compression ratio."""
    hits = []
    seed, seed_compressed = _load_seed()
    if not seed:
        return hits, 0.0

    text_bytes = text.encode("utf-8")
    if len(text_bytes) < MIN_TEXT_BYTES:
        return hits, 0.0
    if len(text_bytes) > MAX_TEXT_BYTES:
        text_bytes = text_bytes[:MAX_TEXT_BYTES]
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
