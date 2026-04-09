from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from verse_archive_toolkit.app_paths import get_settings_directory
from verse_archive_toolkit.settings import AppSettings, SETTINGS_FILENAME


class SettingsStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir if base_dir is not None else get_settings_directory()
        self._path = self._base_dir / SETTINGS_FILENAME

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppSettings:
        self._base_dir.mkdir(parents=True, exist_ok=True)

        if not self._path.exists():
            return AppSettings()

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            backup = self._path.with_suffix(
                f".corrupt-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
            )
            try:
                shutil.move(str(self._path), str(backup))
            except OSError:
                pass
            return AppSettings()

        return AppSettings.from_dict(payload)

    def save(self, settings: AppSettings) -> Path:
        normalized = settings.normalized()
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(normalized.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self._path
