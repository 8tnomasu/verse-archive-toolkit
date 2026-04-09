from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


APP_AUTHOR = "8tnomasu"
APP_NAME = "Verse Archive Toolkit"
SETTINGS_FILENAME = "settings.json"
SETTINGS_SCHEMA_VERSION = 2

FilterAction = Literal["accept", "review", "reject"]
FILTER_ACTIONS: tuple[FilterAction, ...] = ("accept", "review", "reject")

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_POEM_TARGET = 500
DEFAULT_QUOTE_TARGET = 500
DEFAULT_POETRY_BATCH_SIZE = 20
DEFAULT_ZENQUOTES_INTERVAL = 1.5
DEFAULT_SAVE_EVERY = 50
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 6

DEFAULT_SOUP_PHRASES = [
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

DEFAULT_SOUP_WORDS = [
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
]

DEFAULT_PHILOSOPHY_HINTS = [
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
]


def _coerce_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _coerce_int(value: Any, default: int, minimum: int = 0) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, coerced)


def _coerce_float(value: Any, default: float, minimum: float = 0.0) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, coerced)


def _coerce_action(value: Any, default: FilterAction) -> FilterAction:
    return value if value in FILTER_ACTIONS else default


def normalize_text_list(values: Any) -> list[str]:
    if isinstance(values, str):
        raw_values = values.splitlines()
    elif isinstance(values, list):
        raw_values = values
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for item in raw_values:
        text = str(item).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        normalized.append(text)
        seen.add(lowered)

    return normalized


def mask_secret(secret: str, unmasked: int = 4) -> str:
    clean = secret.strip()
    if not clean:
        return "(not set)"
    if len(clean) <= unmasked * 2:
        return "*" * len(clean)
    return f"{clean[:unmasked]}{'*' * (len(clean) - (unmasked * 2))}{clean[-unmasked:]}"


@dataclass(slots=True)
class RangeActionRule:
    enabled: bool = True
    action: FilterAction = "review"
    min_value: int = 0
    max_value: int = 0

    @classmethod
    def from_dict(cls, payload: Any, default: RangeActionRule | None = None) -> RangeActionRule:
        base = default or cls()
        data = payload if isinstance(payload, dict) else {}
        return cls(
            enabled=_coerce_bool(data.get("enabled"), base.enabled),
            action=_coerce_action(data.get("action"), base.action),
            min_value=_coerce_int(data.get("min_value"), base.min_value),
            max_value=_coerce_int(data.get("max_value"), base.max_value),
        )


@dataclass(slots=True)
class NumericActionRule:
    enabled: bool = True
    action: FilterAction = "review"
    value: float = 0.0

    @classmethod
    def from_dict(
        cls,
        payload: Any,
        default: NumericActionRule | None = None,
    ) -> NumericActionRule:
        base = default or cls()
        data = payload if isinstance(payload, dict) else {}
        return cls(
            enabled=_coerce_bool(data.get("enabled"), base.enabled),
            action=_coerce_action(data.get("action"), base.action),
            value=_coerce_float(data.get("value"), base.value),
        )


@dataclass(slots=True)
class KeywordActionRule:
    enabled: bool = True
    action: FilterAction = "review"
    items: list[str] = field(default_factory=list)
    threshold: int = 1

    @classmethod
    def from_dict(
        cls,
        payload: Any,
        default: KeywordActionRule | None = None,
    ) -> KeywordActionRule:
        base = default or cls()
        data = payload if isinstance(payload, dict) else {}
        return cls(
            enabled=_coerce_bool(data.get("enabled"), base.enabled),
            action=_coerce_action(data.get("action"), base.action),
            items=normalize_text_list(data.get("items", base.items)),
            threshold=_coerce_int(data.get("threshold"), base.threshold, minimum=1),
        )


@dataclass(slots=True)
class QuoteFilterSettings:
    text_length: RangeActionRule = field(
        default_factory=lambda: RangeActionRule(min_value=35, max_value=280)
    )
    phrase_blacklist: KeywordActionRule = field(
        default_factory=lambda: KeywordActionRule(
            items=list(DEFAULT_SOUP_PHRASES),
            threshold=1,
        )
    )
    soup_words: KeywordActionRule = field(
        default_factory=lambda: KeywordActionRule(
            items=list(DEFAULT_SOUP_WORDS),
            threshold=2,
        )
    )
    philosophy_hints: KeywordActionRule = field(
        default_factory=lambda: KeywordActionRule(
            action="accept",
            items=list(DEFAULT_PHILOSOPHY_HINTS),
            threshold=1,
        )
    )
    exclamation_limit: NumericActionRule = field(
        default_factory=lambda: NumericActionRule(value=2)
    )

    @classmethod
    def from_dict(cls, payload: Any) -> QuoteFilterSettings:
        base = cls()
        data = payload if isinstance(payload, dict) else {}
        return cls(
            text_length=RangeActionRule.from_dict(data.get("text_length"), base.text_length),
            phrase_blacklist=KeywordActionRule.from_dict(
                data.get("phrase_blacklist"), base.phrase_blacklist
            ),
            soup_words=KeywordActionRule.from_dict(data.get("soup_words"), base.soup_words),
            philosophy_hints=KeywordActionRule.from_dict(
                data.get("philosophy_hints"), base.philosophy_hints
            ),
            exclamation_limit=NumericActionRule.from_dict(
                data.get("exclamation_limit"), base.exclamation_limit
            ),
        )


@dataclass(slots=True)
class PoetryFilterSettings:
    line_count: RangeActionRule = field(
        default_factory=lambda: RangeActionRule(min_value=4, max_value=24)
    )
    text_length: RangeActionRule = field(
        default_factory=lambda: RangeActionRule(min_value=60, max_value=1200)
    )
    average_line_length: NumericActionRule = field(
        default_factory=lambda: NumericActionRule(value=12)
    )
    unique_line_ratio: NumericActionRule = field(
        default_factory=lambda: NumericActionRule(value=0.6)
    )
    keyword_blacklist: KeywordActionRule = field(
        default_factory=lambda: KeywordActionRule(enabled=False, items=[], threshold=1)
    )

    @classmethod
    def from_dict(cls, payload: Any) -> PoetryFilterSettings:
        base = cls()
        data = payload if isinstance(payload, dict) else {}
        return cls(
            line_count=RangeActionRule.from_dict(data.get("line_count"), base.line_count),
            text_length=RangeActionRule.from_dict(data.get("text_length"), base.text_length),
            average_line_length=NumericActionRule.from_dict(
                data.get("average_line_length"), base.average_line_length
            ),
            unique_line_ratio=NumericActionRule.from_dict(
                data.get("unique_line_ratio"), base.unique_line_ratio
            ),
            keyword_blacklist=KeywordActionRule.from_dict(
                data.get("keyword_blacklist"), base.keyword_blacklist
            ),
        )


@dataclass(slots=True)
class FilterSettings:
    quotes: QuoteFilterSettings = field(default_factory=QuoteFilterSettings)
    poetry: PoetryFilterSettings = field(default_factory=PoetryFilterSettings)

    @classmethod
    def from_dict(cls, payload: Any) -> FilterSettings:
        data = payload if isinstance(payload, dict) else {}
        return cls(
            quotes=QuoteFilterSettings.from_dict(data.get("quotes")),
            poetry=PoetryFilterSettings.from_dict(data.get("poetry")),
        )


@dataclass(slots=True)
class BuildSettings:
    output_dir: str = DEFAULT_OUTPUT_DIR
    poem_target: int = DEFAULT_POEM_TARGET
    quote_target: int = DEFAULT_QUOTE_TARGET
    poetry_batch_size: int = DEFAULT_POETRY_BATCH_SIZE
    zenquotes_request_interval: float = DEFAULT_ZENQUOTES_INTERVAL
    save_every: int = DEFAULT_SAVE_EVERY
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    source: str = "all"

    @classmethod
    def from_dict(cls, payload: Any) -> BuildSettings:
        base = cls()
        data = payload if isinstance(payload, dict) else {}
        source = data.get("source", base.source)
        if source not in {"all", "poems", "quotes"}:
            source = base.source

        return cls(
            output_dir=str(data.get("output_dir", base.output_dir) or base.output_dir),
            poem_target=_coerce_int(data.get("poem_target"), base.poem_target, minimum=0),
            quote_target=_coerce_int(data.get("quote_target"), base.quote_target, minimum=0),
            poetry_batch_size=_coerce_int(
                data.get("poetry_batch_size"), base.poetry_batch_size, minimum=1
            ),
            zenquotes_request_interval=_coerce_float(
                data.get("zenquotes_request_interval"),
                base.zenquotes_request_interval,
                minimum=0.0,
            ),
            save_every=_coerce_int(data.get("save_every"), base.save_every, minimum=1),
            request_timeout=_coerce_int(
                data.get("request_timeout"), base.request_timeout, minimum=1
            ),
            max_retries=_coerce_int(data.get("max_retries"), base.max_retries, minimum=1),
            source=source,
        )


@dataclass(slots=True)
class TranslationSettings:
    data_dir: str = DEFAULT_OUTPUT_DIR

    @classmethod
    def from_dict(cls, payload: Any) -> TranslationSettings:
        data = payload if isinstance(payload, dict) else {}
        base = cls()
        return cls(data_dir=str(data.get("data_dir", base.data_dir) or base.data_dir))


@dataclass(slots=True)
class AppSettings:
    schema_version: int = SETTINGS_SCHEMA_VERSION
    zenquotes_api_key: str = ""
    build: BuildSettings = field(default_factory=BuildSettings)
    filters: FilterSettings = field(default_factory=FilterSettings)
    translation: TranslationSettings = field(default_factory=TranslationSettings)

    @classmethod
    def from_dict(cls, payload: Any) -> AppSettings:
        data = payload if isinstance(payload, dict) else {}
        return cls(
            schema_version=_coerce_int(
                data.get("schema_version"), SETTINGS_SCHEMA_VERSION, minimum=1
            ),
            zenquotes_api_key=str(data.get("zenquotes_api_key", "") or "").strip(),
            build=BuildSettings.from_dict(data.get("build")),
            filters=FilterSettings.from_dict(data.get("filters")),
            translation=TranslationSettings.from_dict(data.get("translation")),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = SETTINGS_SCHEMA_VERSION
        return payload

    def normalized(self) -> AppSettings:
        return AppSettings.from_dict(self.to_dict())

    def clone(self) -> AppSettings:
        return self.normalized()


@dataclass(slots=True)
class ToolkitConfig:
    output_dir: Path = Path(DEFAULT_OUTPUT_DIR)
    poem_target: int = DEFAULT_POEM_TARGET
    quote_target: int = DEFAULT_QUOTE_TARGET
    poetry_batch_size: int = DEFAULT_POETRY_BATCH_SIZE
    zenquotes_request_interval: float = DEFAULT_ZENQUOTES_INTERVAL
    save_every: int = DEFAULT_SAVE_EVERY
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    zenquotes_api_key: str = ""
    filter_settings: FilterSettings = field(default_factory=FilterSettings)

    @property
    def poems_file(self) -> Path:
        return self.output_dir / "english_poems.json"

    @property
    def poems_review_file(self) -> Path:
        return self.output_dir / "english_poems_review.json"

    @property
    def quotes_file(self) -> Path:
        return self.output_dir / "philosophy_quotes.json"

    @property
    def quotes_review_file(self) -> Path:
        return self.output_dir / "philosophy_quotes_review.json"


def build_runtime_config(
    build_settings: BuildSettings,
    filter_settings: FilterSettings | None = None,
    zenquotes_api_key: str = "",
) -> ToolkitConfig:
    return ToolkitConfig(
        output_dir=Path(build_settings.output_dir),
        poem_target=build_settings.poem_target,
        quote_target=build_settings.quote_target,
        poetry_batch_size=build_settings.poetry_batch_size,
        zenquotes_request_interval=build_settings.zenquotes_request_interval,
        save_every=build_settings.save_every,
        request_timeout=build_settings.request_timeout,
        max_retries=build_settings.max_retries,
        zenquotes_api_key=zenquotes_api_key.strip(),
        filter_settings=(filter_settings or FilterSettings()),
    )
