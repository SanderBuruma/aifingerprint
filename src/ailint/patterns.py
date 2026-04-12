"""AI writing fingerprint patterns — the complete database."""

import re

# =============================================================================
# BANNED VOCABULARY
# =============================================================================

BANNED_WORDS = {
    "verbs": {
        "delve", "leverage", "utilize", "harness", "streamline", "underscore",
        "foster", "embark", "unlock", "unveil", "elevate", "unleash",
        "revolutionize", "spearhead", "augment", "facilitate", "maximize",
        "capitalize", "bolster", "champion", "cultivate", "empower", "enable",
        "enhance", "illuminate", "optimize", "unpack", "transcend",
        "supercharge",
    },
    "adjectives": {
        "pivotal", "robust", "innovative", "seamless", "cutting-edge",
        "meticulous", "multifaceted", "transformative", "comprehensive",
        "crucial", "essential", "vital", "dynamic", "vibrant", "intricate",
        "daunting", "compelling", "commendable", "exemplary", "invaluable",
        "synergistic", "thought-provoking", "profound", "groundbreaking",
        "renowned", "unprecedented", "whimsical", "indelible", "enduring",
        "enigmatic", "nuanced", "actionable",
    },
    "nouns": {
        "landscape", "realm", "tapestry", "synergy", "testament",
        "underpinnings", "interplay", "labyrinth", "metropolis", "crucible",
        "gossamer", "beacon", "symphony", "virtuoso", "enigma",
        "treasure trove", "nexus", "intersection",
    },
    "adverbs": {
        "meticulously", "effectively", "successfully", "efficiently",
        "fundamentally", "remarkably", "deeply", "arguably", "notably",
        "importantly", "essentially", "promptly",
    },
    "copulative_avoidance": {
        "serves as", "stands as", "marks", "represents", "features",
        "offers", "boasts",
    },
}

# Flatten for quick lookup (single words only)
BANNED_SINGLE_WORDS: set[str] = set()
BANNED_MULTI_WORDS: list[tuple[str, str]] = []
for _cat, _words in BANNED_WORDS.items():
    for w in _words:
        if " " in w:
            BANNED_MULTI_WORDS.append((w.lower(), _cat))
        else:
            BANNED_SINGLE_WORDS.add(w.lower())

# =============================================================================
# BANNED PHRASES
# =============================================================================

BANNED_PHRASES = {
    "opener": [
        "in today's fast-paced world",
        "in today's digital age",
        "in today's landscape",
        "in today's era",
        "in the realm of",
        "in the world of",
        "in a world where",
        "as the landscape continues to evolve",
        "as the industry continues to evolve",
        "now more than ever",
        "whether you're a beginner or an expert",
        "let's dive in",
        "let's break it down",
        "let's face it",
        "without further ado",
    ],
    "hedging": [
        "it's important to note that",
        "it's worth noting that",
        "it's essential to consider",
        "it's worth mentioning that",
        "it is generally considered",
        "one might argue",
        "one could argue",
        "in light of the fact that",
        "given the fact that",
        "it is crucial to understand",
        "there are, of course, important caveats",
        "while this is not an exhaustive treatment",
        "this analysis has certain limitations",
    ],
    "transition": [
        "that being said",
        "as previously mentioned",
        "in light of this",
    ],
    "closing": [
        "in conclusion",
        "in summary",
        "to summarize",
        "to wrap things up",
        "at the end of the day",
        "the key takeaway is",
    ],
    "hype": [
        "unlock the potential",
        "unlock the power",
        "unleash the power",
        "revolutionizing the way",
        "a game-changer for",
        "supercharge your",
        "future-proof your",
        "stay ahead of the curve",
        "that's where",  # "that's where X comes in"
        "at the forefront of",
        "bridging the gap between",
        "push the boundaries of",
        "pave the way for",
    ],
    "faux_conversational": [
        "but here's the thing",
        "here's the kicker",
        "here's the uncomfortable truth",
        "what does this mean for you",
        "not all .* are created equal",
        "it's no secret that",
        "think of it as",
        "imagine a world where",
    ],
    "pleasantries": [
        "i hope this email finds you well",
        "i hope this helps",
        "feel free to reach out",
        "don't hesitate to",
        "great question",
        "i'd be happy to help",
    ],
    "weasel": [
        "industry reports suggest",
        "observers have cited",
        "experts argue",
        "some critics argue",
        "many studies show",
    ],
}

BANNED_SENTENCE_STARTERS = [
    "furthermore", "moreover", "additionally", "consequently",
    "subsequently", "accordingly", "ultimately", "remember that",
]

# =============================================================================
# SENTENCE PATTERNS (compiled regexes)
# =============================================================================

SENTENCE_PATTERNS = {
    "participial_ending": re.compile(
        r",\s+\w+ing\s+[\w\s]+[.!?]$", re.MULTILINE
    ),
    "negative_parallelism": re.compile(
        r"(?:it'?s not .{3,40}(?:,|—|-{1,2})\s*it'?s|"
        r"it'?s less about .{3,40} and more about|"
        r"not just .{3,40},?\s*but also|"
        r"more than just .{3,40}\.\s*it'?s)",
        re.IGNORECASE,
    ),
    "rhetorical_self_answer": re.compile(
        r"(?:^|\. )(?:The|What|Why|How) [^.?]{3,40}\?\s+[A-Z][^.?]{2,40}\.",
        re.MULTILINE,
    ),
    "tricolon": re.compile(
        r"\b(\w+),\s+(\w+),?\s+and\s+(\w+)\b",
        re.IGNORECASE,
    ),
    "both_sides": re.compile(
        r"on\s+(?:the\s+)?one\s+hand\b.*?\bon\s+the\s+other\s+hand\b",
        re.IGNORECASE | re.DOTALL,
    ),
    "analogy_stacking": re.compile(
        r"just\s+as\s+.{10,80}just\s+as\s+",
        re.IGNORECASE,
    ),
    "scope_disclaimer": re.compile(
        r"(?:this\s+is\s+not\s+(?:an?\s+)?exhaustive|"
        r"not\s+(?:an?\s+)?exhaustive\s+(?:list|treatment|analysis|overview)|"
        r"beyond\s+the\s+scope\s+of\s+this|"
        r"space\s+does\s+not\s+permit|"
        r"there\s+are[,\s]+of\s+course[,\s]+(?:important\s+)?(?:caveats|limitations)|"
        r"this\s+analysis\s+has\s+(?:certain\s+)?limitations)",
        re.IGNORECASE,
    ),
}

# =============================================================================
# WORD SETS
# =============================================================================

ENTHUSIASM_WORDS = {
    "exciting", "excited", "thrilled", "thrilling", "fascinating",
    "incredible", "amazing", "wonderful", "remarkable", "extraordinary",
    "fantastic", "tremendous", "awesome", "brilliant", "magnificent",
    "spectacular", "phenomenal", "stunning", "breathtaking",
}

HEDGE_WORDS = {
    "might", "could", "perhaps", "generally", "somewhat", "often",
    "potentially", "possibly", "typically", "arguably", "likely",
    "in many cases", "to some extent", "it seems", "it appears",
}

DISCOURSE_CONNECTIVES = {
    "however", "moreover", "furthermore", "additionally", "consequently",
    "nevertheless", "nonetheless", "subsequently", "accordingly", "therefore",
    "thus", "hence", "meanwhile", "similarly", "likewise", "conversely",
    "alternatively", "specifically", "notably", "importantly", "ultimately",
    "indeed",
}

# =============================================================================
# FORMAT PATTERNS
# =============================================================================

FORMAT_PATTERNS = {
    "em_dash": re.compile(r"—|–|(?<!\w)--(?!\w)"),
    "bold_first_bullet": re.compile(r"^[\s]*[-*]\s+\*\*[^*]+\*\*", re.MULTILINE),
    "header": re.compile(r"^#{1,6}\s+", re.MULTILINE),
    "title_case_header": re.compile(
        r"^#{1,6}\s+(?:[A-Z][a-z]+\s+){2,}[A-Z][a-z]+", re.MULTILINE
    ),
}

# =============================================================================
# SCORING
# =============================================================================

CATEGORY_WEIGHTS = {
    "compression":      0.20,
    "sentence_rhythm":  0.15,
    "tone":             0.15,
    "punctuation":      0.12,
    "connectives":      0.10,
    "burstiness":       0.08,
    "vocabulary":       0.08,
    "structure":        0.07,
    "phrases":          0.05,
    "formatting":       0.00,
}

# Display order (by weight, descending) — single source of truth
CATEGORY_ORDER = [
    "compression", "sentence_rhythm", "tone", "punctuation",
    "connectives", "burstiness", "vocabulary", "structure",
    "phrases", "formatting",
]

SECTION_NAMES = {
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
