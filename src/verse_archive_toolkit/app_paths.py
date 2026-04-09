from __future__ import annotations

import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from platformdirs import user_config_dir, user_log_dir

from verse_archive_toolkit.settings import APP_NAME, DEFAULT_OUTPUT_DIR, SETTINGS_FILENAME


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


def get_program_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    if sys.argv and sys.argv[0]:
        return Path(sys.argv[0]).resolve()
    return Path.cwd()


def get_package_version() -> str:
    try:
        return version("verse-archive-toolkit")
    except PackageNotFoundError:
        return "開發版本"


def find_latest_log_path(app_slug: str | None = None) -> Path | None:
    log_dir = get_logs_directory()
    pattern = f"{app_slug}-*.log" if app_slug else "*.log"
    candidates = [path for path in log_dir.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.stat().st_mtime)


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


def build_diagnostic_report(
    *,
    output_dir: str | Path | None,
    settings_path: Path | None = None,
    app_slug: str | None = None,
) -> str:
    resolved_settings_path = (settings_path or get_settings_path()).resolve()
    resolved_logs_dir = get_logs_directory().resolve()
    resolved_output_dir = resolve_output_directory(output_dir)
    latest_log_path = find_latest_log_path(app_slug)

    lines = [
        f"程式版本：{get_package_version()}",
        f"執行位置：{get_program_path()}",
        f"設定檔位置：{resolved_settings_path}",
        f"日誌資料夾：{resolved_logs_dir}",
        f"輸出資料夾：{resolved_output_dir}",
        f"最近啟動日誌：{latest_log_path if latest_log_path is not None else '尚未找到'}",
    ]
    return "\n".join(lines)
