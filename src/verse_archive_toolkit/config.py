from __future__ import annotations

import os
from pathlib import Path

from verse_archive_toolkit.settings import ToolkitConfig


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


__all__ = ["ToolkitConfig", "load_dotenv_file", "load_zenquotes_api_key"]
