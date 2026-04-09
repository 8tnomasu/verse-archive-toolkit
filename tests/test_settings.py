from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.settings import AppSettings
from verse_archive_toolkit.settings_store import SettingsStore


class SettingsStoreTests(unittest.TestCase):
    def test_save_and_reload_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SettingsStore(Path(tmp_dir))
            settings = AppSettings()
            settings.zenquotes_api_key = "secret-1234"
            settings.build.output_dir = "demo-output"
            settings.filters.quotes.soup_words.threshold = 5
            store.save(settings)

            loaded = store.load()
            self.assertEqual(loaded.zenquotes_api_key, "secret-1234")
            self.assertEqual(loaded.build.output_dir, "demo-output")
            self.assertEqual(loaded.filters.quotes.soup_words.threshold, 5)

    def test_corrupt_settings_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            store = SettingsStore(base_dir)
            store.path.write_text("{not-json", encoding="utf-8")

            loaded = store.load()

            self.assertEqual(loaded.zenquotes_api_key, "")
            corrupt_files = list(base_dir.glob("*.corrupt-*.json"))
            self.assertTrue(corrupt_files)


if __name__ == "__main__":
    unittest.main()
