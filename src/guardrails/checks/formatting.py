"""Formatting pattern detection — em dashes, bold bullets, headers."""

from guardrails.patterns import FORMAT_PATTERNS

EM_DASH_PER_500_LIMIT = 2
BOLD_BULLET_MIN = 3
HEADER_PER_500_LIMIT = 4
SHORT_TEXT_HEADER_LIMIT = 3
SHORT_TEXT_WORD_LIMIT = 500


def check(text: str, lines: list[str]) -> tuple[list[str], float]:
    hits = []
    total_words = len(text.split())

    # Em dashes
    em_dashes = FORMAT_PATTERNS["em_dash"].findall(text)
    em_count = len(em_dashes)
    if total_words > 0:
        per_500 = em_count / (total_words / 500)
        if per_500 > EM_DASH_PER_500_LIMIT:
            hits.append(f"  Em dash density: {per_500:.1f} per 500 words (limit: {EM_DASH_PER_500_LIMIT}) — {em_count} total")

    # Bold-first bullets
    bold_bullets = FORMAT_PATTERNS["bold_first_bullet"].findall(text)
    if len(bold_bullets) >= BOLD_BULLET_MIN:
        hits.append(f"  Bold-first bullets: {len(bold_bullets)} instances")

    # Header density
    headers = FORMAT_PATTERNS["header"].findall(text)
    if total_words > 0 and total_words < SHORT_TEXT_WORD_LIMIT and len(headers) > SHORT_TEXT_HEADER_LIMIT:
        hits.append(f"  Header density: {len(headers)} headers in {total_words} words — excessive")
    elif total_words > 0:
        per_500 = len(headers) / (total_words / 500)
        if per_500 > HEADER_PER_500_LIMIT:
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
