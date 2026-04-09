from __future__ import annotations

from verse_archive_toolkit.records import get_lines, get_nested


POEM_MIN_LINES = 4
POEM_MAX_LINES = 24
POEM_MIN_TEXT_LEN = 60
POEM_MAX_TEXT_LEN = 1200

QUOTE_MIN_TEXT_LEN = 35
QUOTE_MAX_TEXT_LEN = 280

SOUP_PHRASES = [
    "believe in yourself",
    "never give up",
    "follow your heart",
    "dream big",
    "live your best life",
    "best version of yourself",
    "happiness is a choice",
    "you can do anything",
    "stay positive",
    "good vibes",
    "shine your light",
    "reach for the stars",
    "manifest your dreams",
    "trust the process",
]

SOUP_WORDS = {
    "success",
    "motivation",
    "motivational",
    "inspiration",
    "inspirational",
    "positive",
    "positivity",
    "mindset",
    "grind",
    "hustle",
    "winner",
    "winners",
    "winning",
    "achieve",
    "achievement",
    "greatness",
    "destiny",
    "abundance",
    "manifest",
    "dream",
    "dreams",
}

PHILOSOPHY_HINTS = {
    "death",
    "time",
    "truth",
    "soul",
    "self",
    "silence",
    "loneliness",
    "suffering",
    "existence",
    "freedom",
    "meaning",
    "void",
    "memory",
    "beauty",
    "love",
    "fear",
    "god",
    "human",
    "life",
    "world",
    "mind",
    "being",
    "nothingness",
    "desire",
    "wisdom",
    "fate",
    "consciousness",
}


def get_poem_review_reason(poem: dict[str, object]) -> str | None:
    lines = get_lines(poem)
    english_text = get_nested(poem, "content", "en").strip()

    if not lines or not english_text:
        return "empty"

    if len(lines) < POEM_MIN_LINES:
        return "too_short"

    if len(lines) > POEM_MAX_LINES:
        return "too_many_lines"

    average_line_length = sum(len(line.strip()) for line in lines) / max(len(lines), 1)
    if average_line_length < 12:
        return "lines_too_short"

    normalized_lines = [line.strip().lower() for line in lines if line.strip()]
    if normalized_lines:
        unique_ratio = len(set(normalized_lines)) / len(normalized_lines)
        if unique_ratio < 0.6:
            return "too_repetitive"

    if len(english_text) < POEM_MIN_TEXT_LEN:
        return "text_too_short"

    if len(english_text) > POEM_MAX_TEXT_LEN:
        return "text_too_long"

    return None


def get_quote_review_reason(text: str) -> str | None:
    normalized_text = text.strip().lower()

    if not normalized_text:
        return "empty"

    if len(normalized_text) < QUOTE_MIN_TEXT_LEN:
        return "too_short"

    if len(normalized_text) > QUOTE_MAX_TEXT_LEN:
        return "too_long"

    for phrase in SOUP_PHRASES:
        if phrase in normalized_text:
            return f"matched_phrase:{phrase}"

    soup_hits = sum(1 for word in SOUP_WORDS if word in normalized_text)
    philosophy_hits = sum(1 for word in PHILOSOPHY_HINTS if word in normalized_text)

    if soup_hits >= 2 and philosophy_hits == 0:
        return f"soup_words:{soup_hits}"

    if normalized_text.count("!") >= 2:
        return "too_many_exclamations"

    return None
