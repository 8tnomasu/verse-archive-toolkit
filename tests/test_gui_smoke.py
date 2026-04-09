from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - handled by skip
    QApplication = None

from verse_archive_toolkit.settings_store import SettingsStore


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_builder_window_starts(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            window = BuilderMainWindow(SettingsStore(Path(tmp_dir)))
            self.assertEqual(window.windowTitle(), "Verse Archive Toolkit")
            window.close()

    def test_translation_window_starts(self) -> None:
        from verse_archive_toolkit.gui.translator_app import TranslationWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir) / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            store = SettingsStore(Path(tmp_dir))
            settings = store.load()
            settings.translation.data_dir = str(output_dir)
            store.save(settings)
            window = TranslationWindow(store)
            self.assertEqual(window.windowTitle(), "Verse Archive Toolkit Translator")
            window.close()


if __name__ == "__main__":
    unittest.main()
