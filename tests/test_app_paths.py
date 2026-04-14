from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.app_paths import (
    get_application_directory,
    get_logs_directory,
    get_settings_directory,
    get_settings_path,
    read_log_tail,
    resolve_output_directory,
    serialize_app_relative_path,
    tail_text,
)


class AppPathTests(unittest.TestCase):
    def test_portable_paths_live_under_application_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_root = Path(tmp_dir).resolve()
            with patch.dict(os.environ, {"VERSE_ARCHIVE_TOOLKIT_HOME": str(app_root)}, clear=False):
                self.assertEqual(get_application_directory(), app_root)
                self.assertEqual(get_settings_directory(), app_root / "data")
                self.assertEqual(get_settings_path(), app_root / "data" / "settings.json")
                self.assertEqual(get_logs_directory(), app_root / "logs")
                self.assertEqual(resolve_output_directory(None), app_root / "output")
                self.assertEqual(
                    resolve_output_directory(Path("output") / "review"),
                    app_root / "output" / "review",
                )
                self.assertTrue(get_settings_path().resolve().is_relative_to(app_root))
                self.assertTrue(get_logs_directory().resolve().is_relative_to(app_root))

    def test_serialize_app_relative_path_prefers_relative_paths_inside_tool_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_root = Path(tmp_dir).resolve()
            external_dir = app_root.parent / "external-output"
            with patch.dict(os.environ, {"VERSE_ARCHIVE_TOOLKIT_HOME": str(app_root)}, clear=False):
                stored_output = serialize_app_relative_path(app_root / "output")
                stored_nested = serialize_app_relative_path(app_root / "output" / "translated")
                stored_external = serialize_app_relative_path(external_dir)

        self.assertEqual(stored_output, "output")
        self.assertEqual(Path(stored_nested).parts, ("output", "translated"))
        self.assertEqual(stored_external, str(external_dir.resolve()))

    def test_tail_helpers_keep_only_recent_lines(self) -> None:
        text = "\n".join(f"line {index}" for index in range(1, 6))
        self.assertEqual(tail_text(text, max_lines=2), "line 4\nline 5")

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "demo.log"
            log_path.write_text(text, encoding="utf-8")
            self.assertEqual(read_log_tail(log_path, max_lines=3), "line 3\nline 4\nline 5")


if __name__ == "__main__":
    unittest.main()
