from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from platformdirs import user_config_dir, user_log_dir

from verse_archive_toolkit.settings import APP_NAME, DEFAULT_OUTPUT_DIR, SETTINGS_FILENAME

DEFAULT_LOG_TAIL_LINES = 200


def get_settings_directory() -> Path:
    path = Path(user_config_dir(APP_NAME, appauthor=False, roaming=True))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_path() -> Path:
    return get_settings_directory() / SETTINGS_FILENAME


def get_logs_directory() -> Path:
    path = Path(user_log_dir(APP_NAME, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_output_directory(raw_path: str | Path | None) -> Path:
    candidate = str(raw_path or "").strip()
    base_path = Path(candidate) if candidate else Path(DEFAULT_OUTPUT_DIR)
    return base_path.expanduser().resolve()


def find_latest_log_path(app_slug: str | None = None) -> Path | None:
    log_dir = get_logs_directory()
    pattern = f"{app_slug}-*.log" if app_slug else "*.log"
    candidates = [path for path in log_dir.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


def tail_text(text: str, *, max_lines: int = DEFAULT_LOG_TAIL_LINES) -> str:
    lines = text.splitlines()
    excerpt = lines[-max_lines:] if max_lines > 0 else lines
    return "\n".join(excerpt).strip()


def read_log_tail(path: Path, *, max_lines: int = DEFAULT_LOG_TAIL_LINES) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    return tail_text(content, max_lines=max_lines)


def open_path_location(path: Path, *, ensure_exists: bool = False) -> Path:
    target = Path(path)
    if target.suffix:
        target = target.parent

    if ensure_exists:
        target.mkdir(parents=True, exist_ok=True)

    if not target.exists():
        raise FileNotFoundError(target)

    if sys.platform.startswith("win"):
        os.startfile(str(target))  # type: ignore[attr-defined]
        return target

    if sys.platform == "darwin":
        subprocess.Popen(["open", str(target)])
        return target

    subprocess.Popen(["xdg-open", str(target)])
    return target
