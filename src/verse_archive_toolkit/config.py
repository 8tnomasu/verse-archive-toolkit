from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("output")
DEFAULT_POEM_TARGET = 500
DEFAULT_QUOTE_TARGET = 500
DEFAULT_POETRY_BATCH_SIZE = 20
DEFAULT_ZENQUOTES_INTERVAL = 1.5
DEFAULT_SAVE_EVERY = 50
DEFAULT_REQUEST_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 6


@dataclass(slots=True)
class ToolkitConfig:
    output_dir: Path = DEFAULT_OUTPUT_DIR
    poem_target: int = DEFAULT_POEM_TARGET
    quote_target: int = DEFAULT_QUOTE_TARGET
    poetry_batch_size: int = DEFAULT_POETRY_BATCH_SIZE
    zenquotes_request_interval: float = DEFAULT_ZENQUOTES_INTERVAL
    save_every: int = DEFAULT_SAVE_EVERY
    request_timeout: int = DEFAULT_REQUEST_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    zenquotes_api_key: str = ""

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


def load_dotenv_file(path: Path | None = None) -> None:
    dotenv_path = path or Path(".env")
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        clean_key = key.strip()
        clean_value = value.strip().strip('"').strip("'")

        if clean_key and clean_key not in os.environ:
            os.environ[clean_key] = clean_value


def load_zenquotes_api_key(explicit_value: str | None = None) -> str:
    if explicit_value and explicit_value.strip():
        return explicit_value.strip()

    return os.getenv("ZENQUOTES_API_KEY", "").strip()
