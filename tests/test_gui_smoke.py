from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
except Exception:  # pragma: no cover - handled by skip
    Qt = None
    QApplication = None

from verse_archive_toolkit.settings_store import SettingsStore
from verse_archive_toolkit.settings import AppSettings
from verse_archive_toolkit.builder import BuildProgress


@unittest.skipIf(QApplication is None, "PySide6 is not available")
class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_builder_window_starts(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            window = BuilderMainWindow(SettingsStore(Path(tmp_dir)))
            self.assertEqual(window.windowTitle(), "Verse Archive Toolkit 建庫工具")
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
            self.assertEqual(window.windowTitle(), "Verse Archive Toolkit 翻譯輔助工具")
            window.close()

    def test_filter_action_rule_round_trip_uses_combo_data(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            store = SettingsStore(Path(tmp_dir))
            settings = AppSettings()
            settings.filters.quotes.text_length.action = "reject"
            settings.filters.poetry.keyword_blacklist.action = "accept"
            store.save(settings)

            window = BuilderMainWindow(store)
            self.assertEqual(window.filter_editor.quote_editor.text_length.get_rule().action, "reject")
            self.assertEqual(
                window.filter_editor.poetry_editor.keyword_blacklist.get_rule().action,
                "accept",
            )
            window.close()

    def test_builder_window_shows_source_progress_and_path_diagnostics(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            app_root = Path(tmp_dir).resolve()
            with patch.dict(os.environ, {"VERSE_ARCHIVE_TOOLKIT_HOME": str(app_root)}, clear=False):
                window = BuilderMainWindow()
                window.show()
                self.app.processEvents()
                self.assertEqual(window.settings_path_display.text(), str((app_root / "data" / "settings.json")))
                self.assertEqual(window.logs_dir_display.text(), str(app_root / "logs"))
                self.assertEqual(window.output_path_display.text(), str(app_root / "output"))
                self.assertIn("poems", window._source_widgets)
                self.assertIn("quotes", window._source_widgets)
                self.assertTrue(window.build_scroll_area.widgetResizable())
                self.assertEqual(window.build_splitter.orientation(), Qt.Vertical)
                self.assertEqual(window.runtime_splitter.orientation(), Qt.Vertical)
                self.assertFalse(window.build_scroll_area.isAncestorOf(window.save_settings_button))
                self.assertFalse(window.build_scroll_area.isAncestorOf(window.start_button))
                self.assertFalse(window.build_scroll_area.isAncestorOf(window.cancel_button))
                self.assertFalse(window.build_scroll_area.isAncestorOf(window.copy_recent_log_button))
                self.assertFalse(window.build_scroll_area.isAncestorOf(window.open_translator_button))
                self.assertTrue(window.runtime_panel.isAncestorOf(window.open_translator_button))
                build_sizes = window.build_splitter.sizes()
                runtime_sizes = window.runtime_splitter.sizes()
                self.assertGreaterEqual(build_sizes[0], window.build_scroll_area.minimumHeight() - 20)
                self.assertLessEqual(build_sizes[1], window.runtime_panel.minimumHeight() + 20)
                self.assertLessEqual(runtime_sizes[1], window._log_panel_height_for_lines())
                self.assertEqual(window.log_output.minimumHeight(), window._log_output_height_for_lines())

                poems_index = window.source_combo.findData("poems")
                window.source_combo.setCurrentIndex(poems_index)
                self.assertEqual(window._source_widgets["quotes"].status_label.text(), "本次未啟用")

                button_texts = {button.text() for button in window.findChildren(type(window.start_button))}
                self.assertNotIn("複製設定檔路徑", button_texts)
                self.assertNotIn("複製日誌路徑", button_texts)
                self.assertNotIn("複製輸出路徑", button_texts)
                self.assertIn("複製最近日誌內容", button_texts)

                window._handle_progress(
                    BuildProgress(
                        source="poems",
                        status_text="英文詩進度：已通過 3 / 10",
                        accepted_count=3,
                        review_count=1,
                        rejected_count=0,
                        skipped_count=2,
                        processed_count=6,
                        target_count=10,
                        reason_counts={},
                    )
                )
                self.assertEqual(window._source_widgets["poems"].accepted_label.text(), "3")
                self.assertEqual(window._source_widgets["poems"].processed_label.text(), "6")
                self.assertTrue(window.summary_label.text())
                window.close()

    def test_open_translator_button_launches_translation_window(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            app_root = Path(tmp_dir).resolve()
            with patch.dict(os.environ, {"VERSE_ARCHIVE_TOOLKIT_HOME": str(app_root)}, clear=False):
                window = BuilderMainWindow()
                window.show()
                self.app.processEvents()

                window.open_translator_button.click()
                self.app.processEvents()

                self.assertIsNotNone(window._translator_window)
                self.assertEqual(window._translator_window.windowTitle(), "Verse Archive Toolkit 翻譯輔助工具")

                window._translator_window.close()
                window.close()

    def test_start_build_focuses_runtime_panel(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            app_root = Path(tmp_dir).resolve()
            with patch.dict(os.environ, {"VERSE_ARCHIVE_TOOLKIT_HOME": str(app_root)}, clear=False):
                window = BuilderMainWindow()
                window.show()
                self.app.processEvents()
                window.build_splitter.setSizes([780, 120])
                self.app.processEvents()

                with (
                    patch.object(window, "_focus_runtime_panel", wraps=window._focus_runtime_panel) as focus_runtime_panel,
                    patch("verse_archive_toolkit.gui.builder_app.QThread.start", return_value=None),
                ):
                    window._start_build()

                self.app.processEvents()
                focus_runtime_panel.assert_called_once()
                self.assertFalse(window.start_button.isEnabled())
                self.assertTrue(window.cancel_button.isEnabled())
                self.assertIn("已送出建庫工作。", window.log_output.toPlainText())

                window._cleanup_thread()
                window.close()

    def test_copy_recent_log_content_uses_current_session_log(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            window = BuilderMainWindow(SettingsStore(Path(tmp_dir)))
            window.log_output.setPlainText("\n".join(f"log line {index}" for index in range(1, 251)))

            window._copy_recent_log_content()

            clipboard_text = QApplication.clipboard().text()
            clipboard_lines = clipboard_text.splitlines()
            self.assertEqual(clipboard_lines[0], "log line 51")
            self.assertIn("log line 250", clipboard_text)
            self.assertIn("最近 200 行日誌", window.status_label.text())
            window.close()

    def test_copy_recent_log_content_without_available_log_shows_message(self) -> None:
        from verse_archive_toolkit.gui.builder_app import BuilderMainWindow

        with tempfile.TemporaryDirectory() as tmp_dir:
            window = BuilderMainWindow(SettingsStore(Path(tmp_dir)))
            window.log_output.clear()

            with patch("verse_archive_toolkit.gui.builder_app.find_latest_log_path", return_value=None):
                with patch("verse_archive_toolkit.gui.builder_app.QMessageBox.information") as information:
                    window._copy_recent_log_content()

            information.assert_called_once()
            self.assertEqual(window.status_label.text(), "目前沒有可複製的日誌。")
            window.close()


if __name__ == "__main__":
    unittest.main()
