"""Check functions — each scores text on a specific AI writing dimension."""

from aifingerprint.checks.vocabulary import check as check_vocabulary
from aifingerprint.checks.phrases import check as check_phrases
from aifingerprint.checks.structure import check as check_structure
from aifingerprint.checks.formatting import check as check_formatting
from aifingerprint.checks.tone import check as check_tone
from aifingerprint.checks.rhythm import check as check_sentence_rhythm
from aifingerprint.checks.punctuation import check as check_punctuation
from aifingerprint.checks.connectives import check as check_connectives
from aifingerprint.checks.burstiness import check as check_burstiness
from aifingerprint.checks.compression import check as check_compression

CheckResult = tuple[list[str], float]

CHECKS: dict[str, callable] = {
    "vocabulary": check_vocabulary,
    "phrases": check_phrases,
    "structure": check_structure,
    "formatting": check_formatting,
    "tone": check_tone,
    "sentence_rhythm": check_sentence_rhythm,
    "punctuation": check_punctuation,
    "connectives": check_connectives,
    "burstiness": check_burstiness,
    "compression": check_compression,
}
