"""Text splitting and comparison utilities."""

import re
import unicodedata

# Zero-width and invisible characters that can be used to evade word matching
_INVISIBLE_CHARS = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f"   # zero-width space/joiners/marks
    "\u00ad"                              # soft hyphen
    "\ufeff"                              # BOM / zero-width no-break space
    "\u2060\u2061\u2062\u2063\u2064"     # word joiner, invisible operators
    "\u180e"                              # Mongolian vowel separator
    "]"
)

# Common Cyrillic/Greek homoglyphs → ASCII equivalents
_HOMOGLYPH_MAP = str.maketrans({
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",
    "\u0441": "c", "\u0443": "y", "\u0445": "x", "\u0456": "i",
    "\u0458": "j", "\u04bb": "h", "\u0455": "s", "\u0432": "b",
    "\u043d": "h", "\u0442": "t", "\u043c": "m",
    "\u0410": "A", "\u0412": "B", "\u0415": "E", "\u041a": "K",
    "\u041c": "M", "\u041d": "H", "\u041e": "O", "\u0420": "P",
    "\u0421": "C", "\u0422": "T", "\u0425": "X",
    # Greek
    "\u03b1": "a", "\u03bf": "o", "\u03c1": "p", "\u03b5": "e",
    "\u0391": "A", "\u0392": "B", "\u0395": "E", "\u039a": "K",
    "\u039c": "M", "\u039d": "N", "\u039f": "O", "\u03a1": "P",
    "\u03a4": "T", "\u03a7": "X",
    # Latin small capitals (survive NFKC)
    "\u1d00": "a", "\u0299": "b", "\u1d04": "c", "\u1d05": "d",
    "\u1d07": "e", "\ua730": "f", "\u0262": "g", "\u029c": "h",
    "\u026a": "i", "\u1d0a": "j", "\u1d0b": "k", "\u029f": "l",
    "\u1d0d": "m", "\u0274": "n", "\u1d0f": "o", "\u1d18": "p",
    "\u0280": "r", "\ua731": "s", "\u1d1b": "t", "\u1d1c": "u",
    "\u1d20": "v", "\u1d21": "w", "\u028f": "y", "\u1d22": "z",
})


def normalize_text(text: str) -> str:
    """Strip invisible characters and normalize Unicode to defeat evasion.

    This prevents trivial evasion of word-matching checks via zero-width
    characters, soft hyphens, Cyrillic/Greek look-alike letters, fullwidth
    Latin characters (U+FF41-FF5A), or mathematical Unicode letters.
    """
    # NFKC folds fullwidth, mathematical, and compatibility forms to ASCII
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE_CHARS.sub("", text)
    text = text.translate(_HOMOGLYPH_MAP)
    return text

# Abbreviations whose trailing period should NOT trigger a sentence split.
_ABBREV_PATTERN = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Rev|Gen|Sgt|Capt|Lt|Col|Maj"
    r"|vs|etc|approx|dept|govt|inc|corp|ltd|est"
    r"|e\.g|i\.e|al"
    r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\.",
    re.IGNORECASE,
)
_PLACEHOLDER = "\ue000\ue001"  # Private-use Unicode sentinel — safe from collisions


def split_sentences(text: str) -> list[str]:
    """Sentence splitter that handles common abbreviations and ellipsis."""
    clean = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    clean = re.sub(r"^[\s]*[-*]\s+", "", clean, flags=re.MULTILINE)
    # Protect abbreviation periods and ellipsis from splitting
    clean = clean.replace("...", "\u2026")
    clean = _ABBREV_PATTERN.sub(lambda m: m.group(0)[:-1] + _PLACEHOLDER, clean)
    # Protect multi-letter abbreviations like "U.S.", "D.C.", "A.M." —
    # only when a capital-period follows another capital-period.
    clean = re.sub(r"(?<=[A-Z]\.)([A-Z])\.", rf"\1{_PLACEHOLDER}", clean)
    # Split on sentence-ending punctuation followed by whitespace + uppercase/quote
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"])', clean)
    # Restore placeholder back to periods
    parts = [p.replace(_PLACEHOLDER, ".") for p in parts]
    return [s.strip() for s in parts if s.strip() and len(s.split()) >= 2]


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines."""
    paras = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paras if p.strip() and len(p.split()) >= 5]


def word_overlap(s1: str, s2: str) -> float:
    """Fraction of shared words between two strings."""
    w1 = set(s1.lower().split())
    w2 = set(s2.lower().split())
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / min(len(w1), len(w2))


def find_line(lines: list[str], snippet: str) -> int | str:
    """Find the line number containing a snippet."""
    snippet_lower = snippet.lower()
    for i, line in enumerate(lines, 1):
        if snippet_lower in line.lower():
            return i
    return "?"
