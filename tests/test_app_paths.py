from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.app_paths import (
    get_logs_directory,
    read_log_tail,
    get_settings_directory,
    get_settings_path,
    resolve_output_directory,
    tail_text,
)
from verse_archive_toolkit.settings import APP_NAME


class AppPathTests(unittest.TestCase):
    def test_product_name_based_settings_and_logs_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / APP_NAME
            logs_dir = root / APP_NAME / "Logs"

            with (
                patch("verse_archive_toolkit.app_paths.user_config_dir", return_value=str(config_dir)),
                patch("verse_archive_toolkit.app_paths.user_log_dir", return_value=str(logs_dir)),
            ):
                self.assertEqual(get_settings_directory(), config_dir)
                self.assertEqual(get_settings_path(), config_dir / "settings.json")
                self.assertEqual(get_logs_directory(), logs_dir)
                self.assertNotIn("8tnomasu", str(get_settings_directory()).lower())
                self.assertNotIn("8tnomasu", str(get_logs_directory()).lower())

    def test_resolve_output_directory_returns_absolute_path(self) -> None:
        resolved = resolve_output_directory("output")
        self.assertTrue(resolved.is_absolute())
        self.assertEqual(resolved.name, "output")

    def test_tail_helpers_keep_only_recent_lines(self) -> None:
        text = "\n".join(f"line {index}" for index in range(1, 6))
        self.assertEqual(tail_text(text, max_lines=2), "line 4\nline 5")

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "demo.log"
            log_path.write_text(text, encoding="utf-8")
            self.assertEqual(read_log_tail(log_path, max_lines=3), "line 3\nline 4\nline 5")


if __name__ == "__main__":
    unittest.main()
