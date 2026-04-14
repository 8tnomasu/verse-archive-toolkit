from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


APP_NAME = "Verse Archive Toolkit"
SETTINGS_FILENAME = "settings.json"
DEFAULT_OUTPUT_DIRNAME = "output"
DEFAULT_LOG_TAIL_LINES = 200


def get_application_directory() -> Path:
    override = os.getenv("VERSE_ARCHIVE_TOOLKIT_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    module_path = Path(__file__).resolve()
    for candidate in [module_path.parent.parent.parent, Path.cwd().resolve()]:
        candidate = candidate.resolve()
        if (candidate / "pyproject.toml").exists() and (candidate / "src" / "verse_archive_toolkit").exists():
            return candidate

    if sys.argv and sys.argv[0]:
        argv_path = Path(sys.argv[0]).expanduser()
        if argv_path.exists():
            return argv_path.resolve().parent

    return Path.cwd().resolve()


def get_data_directory() -> Path:
    path = get_application_directory() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_settings_directory() -> Path:
    return get_data_directory()


def get_settings_path() -> Path:
    return get_settings_directory() / SETTINGS_FILENAME


def get_logs_directory() -> Path:
    path = get_application_directory() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_output_directory() -> Path:
    path = get_application_directory() / DEFAULT_OUTPUT_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_output_directory(raw_path: str | Path | None) -> Path:
    candidate = str(raw_path or "").strip()
    if not candidate:
        return get_default_output_directory()

    base_path = Path(candidate).expanduser()
    if base_path.is_absolute():
        return base_path.resolve()

    return (get_application_directory() / base_path).resolve()


def serialize_app_relative_path(raw_path: str | Path) -> str:
    candidate = str(raw_path).strip()
    if not candidate:
        return ""

    path = Path(candidate).expanduser()
    if not path.is_absolute():
        return str(path)

    resolved = path.resolve()
    app_root = get_application_directory()
    try:
        relative = resolved.relative_to(app_root)
    except ValueError:
        return str(resolved)

    return str(relative) if str(relative) else "."


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
