from __future__ import annotations

from dataclasses import dataclass

from verse_archive_toolkit.records import get_lines, get_nested
from verse_archive_toolkit.settings import FilterSettings, PoetryFilterSettings, QuoteFilterSettings


@dataclass(slots=True)
class FilterDecision:
    matched: bool = False
    action: str = "accept"
    reason: str | None = None
    detail: str | None = None


def _accept() -> FilterDecision:
    return FilterDecision()


def _decision(action: str, reason: str, detail: str) -> FilterDecision:
    return FilterDecision(matched=True, action=action, reason=reason, detail=detail)


def _matches_range(value: int, min_value: int, max_value: int) -> tuple[bool, str]:
    if min_value > 0 and value < min_value:
        return True, "below_min"
    if max_value > 0 and value > max_value:
        return True, "above_max"
    return False, ""


def evaluate_poem_filters(
    poem: dict[str, object],
    settings: PoetryFilterSettings,
) -> FilterDecision:
    lines = get_lines(poem)
    english_text = get_nested(poem, "content", "en").strip()
    normalized_lines = [line.strip().lower() for line in lines if line.strip()]
    combined = " ".join(
        [
            get_nested(poem, "author", "en"),
            get_nested(poem, "title", "en"),
            english_text,
        ]
    ).lower()

    if settings.line_count.enabled:
        matched, reason = _matches_range(
            len(lines),
            settings.line_count.min_value,
            settings.line_count.max_value,
        )
        if matched:
            return _decision(
                settings.line_count.action,
                f"poetry.line_count.{reason}",
                f"line_count={len(lines)}",
            )

    if settings.keyword_blacklist.enabled and settings.keyword_blacklist.items:
        for term in settings.keyword_blacklist.items:
            if term.lower() in combined:
                return _decision(
                    settings.keyword_blacklist.action,
                    "poetry.keyword_blacklist.match",
                    term,
                )

    if settings.average_line_length.enabled and lines:
        threshold = settings.average_line_length.value
        average_line_length = sum(len(line.strip()) for line in lines) / max(len(lines), 1)
        if threshold > 0 and average_line_length < threshold:
            return _decision(
                settings.average_line_length.action,
                "poetry.average_line_length.below_min",
                f"average={average_line_length:.2f}",
            )

    if settings.unique_line_ratio.enabled and normalized_lines:
        threshold = settings.unique_line_ratio.value
        unique_ratio = len(set(normalized_lines)) / len(normalized_lines)
        if threshold > 0 and unique_ratio < threshold:
            return _decision(
                settings.unique_line_ratio.action,
                "poetry.unique_line_ratio.below_min",
                f"ratio={unique_ratio:.2f}",
            )

    if settings.text_length.enabled:
        matched, reason = _matches_range(
            len(english_text),
            settings.text_length.min_value,
            settings.text_length.max_value,
        )
        if matched:
            return _decision(
                settings.text_length.action,
                f"poetry.text_length.{reason}",
                f"length={len(english_text)}",
            )

    return _accept()


def evaluate_quote_filters(
    text: str,
    settings: QuoteFilterSettings,
) -> FilterDecision:
    normalized_text = text.strip().lower()

    if settings.text_length.enabled:
        matched, reason = _matches_range(
            len(normalized_text),
            settings.text_length.min_value,
            settings.text_length.max_value,
        )
        if matched:
            return _decision(
                settings.text_length.action,
                f"quotes.text_length.{reason}",
                f"length={len(normalized_text)}",
            )

    if settings.phrase_blacklist.enabled and settings.phrase_blacklist.items:
        for phrase in settings.phrase_blacklist.items:
            if phrase.lower() in normalized_text:
                return _decision(
                    settings.phrase_blacklist.action,
                    "quotes.phrase_blacklist.match",
                    phrase,
                )

    if settings.soup_words.enabled and settings.soup_words.items:
        soup_hits = sum(1 for word in settings.soup_words.items if word.lower() in normalized_text)
        hint_hits = 0
        if settings.philosophy_hints.enabled and settings.philosophy_hints.items:
            hint_hits = sum(
                1 for word in settings.philosophy_hints.items if word.lower() in normalized_text
            )

        if soup_hits >= settings.soup_words.threshold:
            hint_threshold = settings.philosophy_hints.threshold
            if not settings.philosophy_hints.enabled or hint_hits < hint_threshold:
                return _decision(
                    settings.soup_words.action,
                    "quotes.soup_words.threshold",
                    f"soup_hits={soup_hits}, hint_hits={hint_hits}",
                )

    if settings.exclamation_limit.enabled:
        limit = settings.exclamation_limit.value
        exclamation_count = normalized_text.count("!")
        if limit > 0 and exclamation_count > limit:
            return _decision(
                settings.exclamation_limit.action,
                "quotes.exclamation_limit.above_max",
                f"count={exclamation_count}",
            )

    return _accept()


def get_poem_review_reason(poem: dict[str, object]) -> str | None:
    decision = evaluate_poem_filters(poem, FilterSettings().poetry)
    if decision.matched and decision.action != "accept":
        return decision.reason
    return None


def get_quote_review_reason(text: str) -> str | None:
    decision = evaluate_quote_filters(text, FilterSettings().quotes)
    if decision.matched and decision.action != "accept":
        return decision.reason
    return None
