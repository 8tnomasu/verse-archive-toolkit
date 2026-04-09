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
    get_settings_directory,
    get_settings_path,
    resolve_output_directory,
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


if __name__ == "__main__":
    unittest.main()
