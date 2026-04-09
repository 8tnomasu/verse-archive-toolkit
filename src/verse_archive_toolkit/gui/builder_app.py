from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from verse_archive_toolkit.builder import BuildHooks, BuildProgress, BuildResult, build_selected_sources
from verse_archive_toolkit.settings import (
    AppSettings,
    BuildSettings,
    FilterSettings,
    KeywordActionRule,
    NumericActionRule,
    PoetryFilterSettings,
    QuoteFilterSettings,
    RangeActionRule,
    build_runtime_config,
    mask_secret,
)
from verse_archive_toolkit.settings_store import SettingsStore


def _action_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem("accept", "accept")
    combo.addItem("review", "review")
    combo.addItem("reject", "reject")
    return combo


class RangeRuleEditor(QGroupBox):
    def __init__(self, title: str, *, decimals: int = 0, maximum: float = 999999.0) -> None:
        super().__init__(title)
        self.setCheckable(True)
        self.action_combo = _action_combo()
        if decimals == 0:
            self.min_spin: QSpinBox | QDoubleSpinBox = QSpinBox()
            self.max_spin: QSpinBox | QDoubleSpinBox = QSpinBox()
            self.min_spin.setRange(0, int(maximum))
            self.max_spin.setRange(0, int(maximum))
        else:
            self.min_spin = QDoubleSpinBox()
            self.max_spin = QDoubleSpinBox()
            self.min_spin.setDecimals(decimals)
            self.max_spin.setDecimals(decimals)
            self.min_spin.setRange(0.0, maximum)
            self.max_spin.setRange(0.0, maximum)

        self.min_spin.setSpecialValueText("0 = no limit")
        self.max_spin.setSpecialValueText("0 = no limit")

        layout = QFormLayout(self)
        layout.addRow("Action", self.action_combo)
        layout.addRow("Minimum", self.min_spin)
        layout.addRow("Maximum", self.max_spin)

    def set_rule(self, rule: RangeActionRule) -> None:
        self.setChecked(rule.enabled)
        self.action_combo.setCurrentText(rule.action)
        self.min_spin.setValue(rule.min_value)
        self.max_spin.setValue(rule.max_value)

    def get_rule(self) -> RangeActionRule:
        return RangeActionRule(
            enabled=self.isChecked(),
            action=str(self.action_combo.currentData()),
            min_value=int(self.min_spin.value()),
            max_value=int(self.max_spin.value()),
        )


class NumericRuleEditor(QGroupBox):
    def __init__(
        self,
        title: str,
        *,
        decimals: int = 0,
        maximum: float = 999999.0,
        show_action: bool = True,
    ) -> None:
        super().__init__(title)
        self.setCheckable(True)
        self.show_action = show_action
        self.action_combo = _action_combo()
        self.value_spin = QDoubleSpinBox()
        self.value_spin.setDecimals(decimals)
        self.value_spin.setRange(0.0, maximum)
        self.value_spin.setSingleStep(1.0 if decimals == 0 else 0.05)
        self.value_spin.setSpecialValueText("0 = no limit")

        layout = QFormLayout(self)
        if show_action:
            layout.addRow("Action", self.action_combo)
        layout.addRow("Value", self.value_spin)

    def set_rule(self, rule: NumericActionRule) -> None:
        self.setChecked(rule.enabled)
        self.action_combo.setCurrentText(rule.action)
        self.value_spin.setValue(rule.value)

    def get_rule(self) -> NumericActionRule:
        return NumericActionRule(
            enabled=self.isChecked(),
            action=str(self.action_combo.currentData()),
            value=float(self.value_spin.value()),
        )


class KeywordRuleEditor(QGroupBox):
    def __init__(
        self,
        title: str,
        *,
        show_action: bool = True,
        show_threshold: bool = False,
    ) -> None:
        super().__init__(title)
        self.setCheckable(True)
        self.show_action = show_action
        self.show_threshold = show_threshold
        self.action_combo = _action_combo()
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 9999)
        self.items_edit = QPlainTextEdit()
        self.items_edit.setPlaceholderText("One keyword or phrase per line")

        layout = QFormLayout(self)
        if show_action:
            layout.addRow("Action", self.action_combo)
        if show_threshold:
            layout.addRow("Match threshold", self.threshold_spin)
        layout.addRow("Items", self.items_edit)

    def set_rule(self, rule: KeywordActionRule) -> None:
        self.setChecked(rule.enabled)
        self.action_combo.setCurrentText(rule.action)
        self.threshold_spin.setValue(rule.threshold)
        self.items_edit.setPlainText("\n".join(rule.items))

    def get_rule(self) -> KeywordActionRule:
        return KeywordActionRule(
            enabled=self.isChecked(),
            action=str(self.action_combo.currentData()),
            items=self.items_edit.toPlainText().splitlines(),
            threshold=self.threshold_spin.value(),
        )


class QuoteFilterEditor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("0 means no limit for range-based rules."))

        self.text_length = RangeRuleEditor("Quote text length")
        self.phrase_blacklist = KeywordRuleEditor("Phrase blacklist")
        self.soup_words = KeywordRuleEditor("Soup-word blacklist", show_threshold=True)
        self.philosophy_hints = KeywordRuleEditor(
            "Philosophy hints (used to exempt soup-word hits)",
            show_action=False,
            show_threshold=True,
        )
        self.exclamation_limit = NumericRuleEditor("Exclamation limit")

        for widget in (
            self.text_length,
            self.phrase_blacklist,
            self.soup_words,
            self.philosophy_hints,
            self.exclamation_limit,
        ):
            layout.addWidget(widget)

        layout.addStretch(1)

    def set_settings(self, settings: QuoteFilterSettings) -> None:
        self.text_length.set_rule(settings.text_length)
        self.phrase_blacklist.set_rule(settings.phrase_blacklist)
        self.soup_words.set_rule(settings.soup_words)
        self.philosophy_hints.set_rule(settings.philosophy_hints)
        self.exclamation_limit.set_rule(settings.exclamation_limit)

    def get_settings(self) -> QuoteFilterSettings:
        return QuoteFilterSettings(
            text_length=self.text_length.get_rule(),
            phrase_blacklist=self.phrase_blacklist.get_rule(),
            soup_words=self.soup_words.get_rule(),
            philosophy_hints=self.philosophy_hints.get_rule(),
            exclamation_limit=self.exclamation_limit.get_rule(),
        )


class PoetryFilterEditor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("0 means no limit for range-based rules."))

        self.line_count = RangeRuleEditor("Poem line count")
        self.text_length = RangeRuleEditor("Poem text length")
        self.average_line_length = NumericRuleEditor("Average line length", decimals=1)
        self.unique_line_ratio = NumericRuleEditor("Unique line ratio", decimals=2, maximum=1.0)
        self.keyword_blacklist = KeywordRuleEditor("Title / author / content blacklist")

        for widget in (
            self.line_count,
            self.text_length,
            self.average_line_length,
            self.unique_line_ratio,
            self.keyword_blacklist,
        ):
            layout.addWidget(widget)

        layout.addStretch(1)

    def set_settings(self, settings: PoetryFilterSettings) -> None:
        self.line_count.set_rule(settings.line_count)
        self.text_length.set_rule(settings.text_length)
        self.average_line_length.set_rule(settings.average_line_length)
        self.unique_line_ratio.set_rule(settings.unique_line_ratio)
        self.keyword_blacklist.set_rule(settings.keyword_blacklist)

    def get_settings(self) -> PoetryFilterSettings:
        return PoetryFilterSettings(
            line_count=self.line_count.get_rule(),
            text_length=self.text_length.get_rule(),
            average_line_length=self.average_line_length.get_rule(),
            unique_line_ratio=self.unique_line_ratio.get_rule(),
            keyword_blacklist=self.keyword_blacklist.get_rule(),
        )


class FilterSettingsEditor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        self.quote_editor = QuoteFilterEditor()
        self.poetry_editor = PoetryFilterEditor()
        tabs.addTab(self.quote_editor, "Quotes")
        tabs.addTab(self.poetry_editor, "Poetry")
        layout.addWidget(tabs)

    def set_settings(self, settings: FilterSettings) -> None:
        self.quote_editor.set_settings(settings.quotes)
        self.poetry_editor.set_settings(settings.poetry)

    def get_settings(self) -> FilterSettings:
        return FilterSettings(
            quotes=self.quote_editor.get_settings(),
            poetry=self.poetry_editor.get_settings(),
        )


class BuildWorker(QObject):
    log_message = Signal(str)
    progress_changed = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self._settings = settings.clone()
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        try:
            runtime_config = build_runtime_config(
                self._settings.build,
                self._settings.filters,
                self._settings.zenquotes_api_key,
            )
            results = build_selected_sources(
                config=runtime_config,
                source=self._settings.build.source,
                hooks=BuildHooks(
                    log=self.log_message.emit,
                    progress=self.progress_changed.emit,
                    should_cancel=self._cancel_event.is_set,
                ),
            )
        except Exception as error:
            self.failed.emit(str(error))
            return

        self.finished.emit(results)


@dataclass(slots=True)
class _SummaryTotals:
    accepted: int = 0
    review: int = 0
    rejected: int = 0
    skipped: int = 0
    processed: int = 0
    target: int = 0


class BuilderMainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore | None = None) -> None:
        super().__init__()
        self.settings_store = settings_store or SettingsStore()
        self.settings = self.settings_store.load()
        self._thread: QThread | None = None
        self._worker: BuildWorker | None = None
        self._source_progress: dict[str, BuildProgress] = {}
        self._translator_window: QWidget | None = None

        self.setWindowTitle("Verse Archive Toolkit")
        self.resize(1100, 860)
        self._build_ui()
        self._apply_settings(self.settings)
        self._refresh_api_key_hint()
        self._append_log(f"Settings file: {self.settings_store.path}")

    def _build_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout(central)

        header = QLabel("Desktop archive builder for Verse Archive Toolkit")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        main_layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(self._create_build_tab(), "Build")
        tabs.addTab(self._create_filter_tab(), "Filter Rules")
        main_layout.addWidget(tabs)

        footer = QLabel(
            "Local settings are stored outside the repo. API keys are saved locally and shown masked in the UI."
        )
        footer.setWordWrap(True)
        footer.setStyleSheet("color: #555;")
        main_layout.addWidget(footer)

        self.setCentralWidget(central)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f6f4ef; color: #1f1f1f; }
            QGroupBox {
                border: 1px solid #d1cabd;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
                background: #fffdfa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #6a4e2a;
                font-weight: 600;
            }
            QPushButton {
                background: #244b74;
                color: white;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPushButton:disabled {
                background: #9fabb8;
            }
            QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background: white;
                border: 1px solid #c9c3b7;
                border-radius: 6px;
                padding: 4px 6px;
            }
            QProgressBar {
                border: 1px solid #c9c3b7;
                border-radius: 6px;
                background: white;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #d17a22;
                border-radius: 5px;
            }
            """
        )

    def _create_build_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        config_group = QGroupBox("Build configuration")
        form = QFormLayout(config_group)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.textChanged.connect(self._refresh_api_key_hint)
        self.api_key_hint = QLabel()
        self.api_key_hint.setStyleSheet("color: #666;")
        api_key_box = QWidget()
        api_key_layout = QVBoxLayout(api_key_box)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.addWidget(self.api_key_edit)
        api_key_layout.addWidget(self.api_key_hint)
        form.addRow("ZenQuotes API key", api_key_box)

        self.output_dir_edit = QLineEdit()
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_dir)
        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.output_dir_edit, 1)
        path_layout.addWidget(browse_button)
        form.addRow("Output directory", path_row)

        self.source_combo = QComboBox()
        self.source_combo.addItem("Poems + Quotes", "all")
        self.source_combo.addItem("Poems only", "poems")
        self.source_combo.addItem("Quotes only", "quotes")
        form.addRow("Build source", self.source_combo)

        self.poem_target_spin = QSpinBox()
        self.poem_target_spin.setRange(0, 100000)
        self.quote_target_spin = QSpinBox()
        self.quote_target_spin.setRange(0, 100000)
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 1000)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.0, 3600.0)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setSingleStep(0.25)
        self.save_every_spin = QSpinBox()
        self.save_every_spin.setRange(1, 10000)
        self.request_timeout_spin = QSpinBox()
        self.request_timeout_spin.setRange(1, 600)
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 50)

        form.addRow("Poem target", self.poem_target_spin)
        form.addRow("Quote target", self.quote_target_spin)
        form.addRow("Batch size", self.batch_size_spin)
        form.addRow("Request interval (s)", self.interval_spin)
        form.addRow("Auto save every", self.save_every_spin)
        form.addRow("Request timeout (s)", self.request_timeout_spin)
        form.addRow("Max retries", self.max_retries_spin)
        layout.addWidget(config_group)

        button_row = QHBoxLayout()
        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.clicked.connect(self._save_settings)
        self.start_button = QPushButton("Start Build")
        self.start_button.clicked.connect(self._start_build)
        self.cancel_button = QPushButton("Stop / Cancel")
        self.cancel_button.clicked.connect(self._cancel_build)
        self.cancel_button.setEnabled(False)
        self.open_translator_button = QPushButton("Open Translator")
        self.open_translator_button.clicked.connect(self._open_translator_window)

        button_row.addWidget(self.save_settings_button)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch(1)
        button_row.addWidget(self.open_translator_button)
        layout.addLayout(button_row)

        progress_group = QGroupBox("Build status")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("Idle")
        self.summary_label = QLabel("No build started yet.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #555;")

        stats_grid = QGridLayout()
        self.accepted_label = QLabel("0")
        self.review_label = QLabel("0")
        self.rejected_label = QLabel("0")
        self.skipped_label = QLabel("0")
        self.processed_label = QLabel("0")

        stats_grid.addWidget(QLabel("Accepted"), 0, 0)
        stats_grid.addWidget(self.accepted_label, 0, 1)
        stats_grid.addWidget(QLabel("Review"), 0, 2)
        stats_grid.addWidget(self.review_label, 0, 3)
        stats_grid.addWidget(QLabel("Rejected"), 1, 0)
        stats_grid.addWidget(self.rejected_label, 1, 1)
        stats_grid.addWidget(QLabel("Skipped"), 1, 2)
        stats_grid.addWidget(self.skipped_label, 1, 3)
        stats_grid.addWidget(QLabel("Processed this run"), 2, 0)
        stats_grid.addWidget(self.processed_label, 2, 1)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(260)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_layout.addLayout(stats_grid)
        progress_layout.addWidget(self.summary_label)
        progress_layout.addWidget(QLabel("Log output"))
        progress_layout.addWidget(self.log_output)
        layout.addWidget(progress_group, 1)

        return widget

    def _create_filter_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        description = QLabel(
            "Edit the live filtering rules used by the builder. Each rule can be enabled, disabled, set to accept, review, or reject, and reset to project defaults."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.filter_editor = FilterSettingsEditor()
        scroll_area.setWidget(self.filter_editor)
        layout.addWidget(scroll_area, 1)

        button_row = QHBoxLayout()
        save_button = QPushButton("Save Filter Settings")
        save_button.clicked.connect(self._save_settings)
        reset_button = QPushButton("Restore Filter Defaults")
        reset_button.clicked.connect(self._restore_filter_defaults)
        button_row.addWidget(save_button)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        return widget

    def _apply_settings(self, settings: AppSettings) -> None:
        self.api_key_edit.setText(settings.zenquotes_api_key)
        self.output_dir_edit.setText(settings.build.output_dir)
        self.source_combo.setCurrentIndex(max(0, self.source_combo.findData(settings.build.source)))
        self.poem_target_spin.setValue(settings.build.poem_target)
        self.quote_target_spin.setValue(settings.build.quote_target)
        self.batch_size_spin.setValue(settings.build.poetry_batch_size)
        self.interval_spin.setValue(settings.build.zenquotes_request_interval)
        self.save_every_spin.setValue(settings.build.save_every)
        self.request_timeout_spin.setValue(settings.build.request_timeout)
        self.max_retries_spin.setValue(settings.build.max_retries)
        self.filter_editor.set_settings(settings.filters)

    def _collect_settings(self) -> AppSettings:
        settings = self.settings.clone()
        settings.zenquotes_api_key = self.api_key_edit.text().strip()
        settings.build = BuildSettings(
            output_dir=self.output_dir_edit.text().strip() or "output",
            poem_target=self.poem_target_spin.value(),
            quote_target=self.quote_target_spin.value(),
            poetry_batch_size=self.batch_size_spin.value(),
            zenquotes_request_interval=self.interval_spin.value(),
            save_every=self.save_every_spin.value(),
            request_timeout=self.request_timeout_spin.value(),
            max_retries=self.max_retries_spin.value(),
            source=str(self.source_combo.currentData()),
        )
        settings.translation.data_dir = settings.build.output_dir
        settings.filters = self.filter_editor.get_settings()
        return settings.normalized()

    def _refresh_api_key_hint(self) -> None:
        self.api_key_hint.setText(
            "Displayed masked in the UI and never echoed into the log: "
            f"{mask_secret(self.api_key_edit.text())}"
        )

    def _browse_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choose output directory",
            self.output_dir_edit.text().strip() or str(Path.cwd()),
        )
        if selected:
            self.output_dir_edit.setText(selected)

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)

    def _save_settings(self) -> None:
        self.settings = self._collect_settings()
        saved_path = self.settings_store.save(self.settings)
        self._append_log(f"Saved settings to {saved_path}")
        self.status_label.setText("Settings saved.")

    def _restore_filter_defaults(self) -> None:
        self.filter_editor.set_settings(FilterSettings())
        self.status_label.setText("Filter rules restored to defaults.")
        self._append_log("Filter rules restored to defaults.")

    def _toggle_running_state(self, is_running: bool) -> None:
        self.start_button.setEnabled(not is_running)
        self.cancel_button.setEnabled(is_running)
        self.save_settings_button.setEnabled(not is_running)
        self.open_translator_button.setEnabled(not is_running)

    def _start_build(self) -> None:
        self._save_settings()
        self._source_progress.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting build...")
        self.summary_label.setText("Build is running.")
        self.log_output.clear()
        self._append_log("Build requested.")

        self._toggle_running_state(True)
        self._thread = QThread(self)
        self._worker = BuildWorker(self.settings)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.log_message.connect(self._append_log)
        self._worker.progress_changed.connect(self._handle_progress)
        self._worker.finished.connect(self._handle_finished)
        self._worker.failed.connect(self._handle_failed)
        self._worker.finished.connect(self._cleanup_thread)
        self._worker.failed.connect(self._cleanup_thread)
        self._thread.start()

    def _cancel_build(self) -> None:
        if self._worker is None:
            return
        self._worker.cancel()
        self.status_label.setText("Cancellation requested...")
        self._append_log("Cancellation requested by user.")

    def _handle_progress(self, payload: object) -> None:
        if not isinstance(payload, BuildProgress):
            return
        self._source_progress[payload.source] = payload
        totals = self._summarize_progress()

        self.accepted_label.setText(str(totals.accepted))
        self.review_label.setText(str(totals.review))
        self.rejected_label.setText(str(totals.rejected))
        self.skipped_label.setText(str(totals.skipped))
        self.processed_label.setText(str(totals.processed))

        progress_value = 0
        if totals.target > 0:
            progress_value = min(100, int((totals.accepted / totals.target) * 100))
        self.progress_bar.setValue(progress_value)
        self.status_label.setText(payload.status_text)

    def _summarize_progress(self) -> _SummaryTotals:
        totals = _SummaryTotals()
        for payload in self._source_progress.values():
            totals.accepted += payload.accepted_count
            totals.review += payload.review_count
            totals.rejected += payload.rejected_count
            totals.skipped += payload.skipped_count
            totals.processed += payload.processed_count
            totals.target += payload.target_count
        return totals

    def _handle_finished(self, results: object) -> None:
        if not isinstance(results, dict):
            return

        summary_lines: list[str] = []
        for source_name, result in results.items():
            if not isinstance(result, BuildResult):
                continue
            summary_lines.append(
                f"{source_name}: accepted={result.accepted_count}, review={result.review_count}, "
                f"rejected={result.rejected_count}, skipped={result.skipped_count}"
            )
            if result.reason_counts:
                top_reasons = ", ".join(
                    f"{reason} ({count})"
                    for reason, count in sorted(
                        result.reason_counts.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:5]
                )
                summary_lines.append(f"  top reasons: {top_reasons}")

        self.summary_label.setText("\n".join(summary_lines) if summary_lines else "Build finished.")
        self.status_label.setText("Build completed.")
        self.progress_bar.setValue(100)
        self._append_log("Build completed successfully.")
        self._toggle_running_state(False)

    def _handle_failed(self, message: str) -> None:
        self.status_label.setText("Build failed.")
        self.summary_label.setText(message)
        self._append_log(f"Build failed: {message}")
        self._toggle_running_state(False)
        QMessageBox.critical(self, "Build failed", message)

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = None
        self._thread = None
        self._toggle_running_state(False)

    def _open_translator_window(self) -> None:
        from verse_archive_toolkit.gui.translator_app import TranslationWindow

        self._save_settings()
        if self._translator_window is None:
            self._translator_window = TranslationWindow(self.settings_store)
        self._translator_window.show()
        self._translator_window.raise_()
        self._translator_window.activateWindow()

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        if self._worker is not None:
            response = QMessageBox.question(
                self,
                "Build in progress",
                "A build is still running. Cancel it and close the window?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if response != QMessageBox.Yes:
                event.ignore()
                return
            self._cancel_build()
            if self._thread is not None:
                self._thread.quit()
                self._thread.wait()
        event.accept()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    window = BuilderMainWindow()
    window.show()
    return app.exec()
