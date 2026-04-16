from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
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
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from verse_archive_toolkit.app_paths import (
    DEFAULT_LOG_TAIL_LINES,
    find_latest_log_path,
    get_logs_directory,
    open_path_location,
    read_log_tail,
    resolve_output_directory,
    serialize_app_relative_path,
    tail_text,
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


ACTION_LABELS = {
    "accept": "通過",
    "review": "待審",
    "reject": "拒絕",
}

REASON_LABELS = {
    "poems.invalid_payload": "詩作來源回應格式異常",
    "poems.invalid_item": "詩作資料欄位不完整",
    "poems.duplicate": "重複詩作",
    "poems.review": "進入待審",
    "poems.reject": "直接拒絕",
    "poetry.line_count.below_min": "行數不足",
    "poetry.line_count.above_max": "行數過多",
    "poetry.keyword_blacklist.match": "命中詩作關鍵字排除",
    "poetry.average_line_length.below_min": "平均每行字數不足",
    "poetry.unique_line_ratio.below_min": "重複率過高",
    "poetry.text_length.below_min": "全文字數不足",
    "poetry.text_length.above_max": "全文字數過長",
    "quotes.invalid_author_tag": "作者標籤無效",
    "quotes.author_fetch_error": "抓取作者語錄失敗",
    "quotes.invalid_item": "語錄資料欄位不完整",
    "quotes.duplicate": "重複語錄",
    "quotes.review": "進入待審",
    "quotes.reject": "直接拒絕",
    "quotes.text_length.below_min": "語錄字數不足",
    "quotes.text_length.above_max": "語錄字數過長",
    "quotes.phrase_blacklist.match": "命中黑名單片語",
    "quotes.soup_words.threshold": "命中心靈雞湯關鍵字",
    "quotes.exclamation_limit.above_max": "驚嘆號過多",
}

SOURCE_LABELS = {
    "poems": "英文詩",
    "quotes": "哲思語錄",
}


def _humanize_reason(reason: str) -> str:
    return REASON_LABELS.get(reason, reason)


def _humanize_source(source: str) -> str:
    return SOURCE_LABELS.get(source, source)


def _set_combo_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


def _action_combo() -> QComboBox:
    combo = QComboBox()
    combo.addItem(ACTION_LABELS["accept"], "accept")
    combo.addItem(ACTION_LABELS["review"], "review")
    combo.addItem(ACTION_LABELS["reject"], "reject")
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

        self.min_spin.setSpecialValueText("0 = 不設限")
        self.max_spin.setSpecialValueText("0 = 不設限")

        layout = QFormLayout(self)
        layout.addRow("處理方式", self.action_combo)
        layout.addRow("最小值", self.min_spin)
        layout.addRow("最大值", self.max_spin)

    def set_rule(self, rule: RangeActionRule) -> None:
        self.setChecked(rule.enabled)
        _set_combo_data(self.action_combo, rule.action)
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
        self.value_spin.setSpecialValueText("0 = 不設限")

        layout = QFormLayout(self)
        if show_action:
            layout.addRow("處理方式", self.action_combo)
        layout.addRow("數值", self.value_spin)

    def set_rule(self, rule: NumericActionRule) -> None:
        self.setChecked(rule.enabled)
        _set_combo_data(self.action_combo, rule.action)
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
        self.items_edit.setPlaceholderText("每行一個關鍵字或片語")

        layout = QFormLayout(self)
        if show_action:
            layout.addRow("處理方式", self.action_combo)
        if show_threshold:
            layout.addRow("命中門檻", self.threshold_spin)
        layout.addRow("清單內容", self.items_edit)

    def set_rule(self, rule: KeywordActionRule) -> None:
        self.setChecked(rule.enabled)
        _set_combo_data(self.action_combo, rule.action)
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
        layout.addWidget(QLabel("數值型規則中，0 代表不設限。"))

        self.text_length = RangeRuleEditor("語錄字數範圍")
        self.phrase_blacklist = KeywordRuleEditor("黑名單片語")
        self.soup_words = KeywordRuleEditor("心靈雞湯關鍵字", show_threshold=True)
        self.philosophy_hints = KeywordRuleEditor(
            "哲思提示詞（用來豁免雞湯詞命中）",
            show_action=False,
            show_threshold=True,
        )
        self.exclamation_limit = NumericRuleEditor("驚嘆號上限")

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
        layout.addWidget(QLabel("數值型規則中，0 代表不設限。"))

        self.line_count = RangeRuleEditor("詩作行數範圍")
        self.text_length = RangeRuleEditor("詩作全文字數範圍")
        self.average_line_length = NumericRuleEditor("平均每行字數下限", decimals=1)
        self.unique_line_ratio = NumericRuleEditor("唯一行比例下限", decimals=2, maximum=1.0)
        self.keyword_blacklist = KeywordRuleEditor("標題 / 作者 / 內容排除關鍵字")

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
        tabs.addTab(self.quote_editor, "哲思語錄規則")
        tabs.addTab(self.poetry_editor, "英文詩規則")
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


@dataclass(slots=True)
class _SourceWidgets:
    progress_bar: QProgressBar
    status_label: QLabel
    accepted_label: QLabel
    review_label: QLabel
    rejected_label: QLabel
    skipped_label: QLabel
    processed_label: QLabel


class BuilderMainWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore | None = None) -> None:
        super().__init__()
        self.settings_store = settings_store or SettingsStore()
        self.settings = self.settings_store.load()
        self._thread: QThread | None = None
        self._worker: BuildWorker | None = None
        self._source_progress: dict[str, BuildProgress] = {}
        self._source_widgets: dict[str, _SourceWidgets] = {}
        self._translator_window: QWidget | None = None
        self._initial_runtime_layout_applied = False

        self.setWindowTitle("VerseArchiveCurator")
        self.resize(1100, 860)
        self._build_ui()
        self._apply_settings(self.settings)
        self._refresh_api_key_hint()
        self._refresh_path_views()
        self._append_log(f"設定檔位置：{self.settings_store.path.resolve()}")
        self._append_log(f"日誌資料夾：{get_logs_directory().resolve()}")

    def _build_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout(central)

        header = QLabel("VerseArchiveCurator")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        main_layout.addWidget(header)

        tabs = QTabWidget()
        tabs.addTab(self._create_build_tab(), "建庫")
        tabs.addTab(self._create_filter_tab(), "過濾規則")
        main_layout.addWidget(tabs)

        footer = QLabel(
            "本機設定檔、日誌與預設輸出會放在工具資料夾內的 data / logs / output，不會寫回 Git 倉庫；路徑與診斷區可直接開啟相關位置，並一鍵複製最近日誌內容。API key 只在本機保存，介面中只顯示遮罩後內容。"
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
        layout.setContentsMargins(0, 0, 0, 0)
        self.build_splitter = QSplitter(Qt.Vertical)
        self.build_splitter.setChildrenCollapsible(False)

        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setChildrenCollapsible(False)

        self.log_panel = QGroupBox("建庫日誌")
        log_layout = QVBoxLayout(self.log_panel)
        log_layout.setContentsMargins(10, 12, 10, 10)
        log_layout.setSpacing(6)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.log_output.setPlaceholderText("建庫開始後，這裡會顯示即時日誌。")
        log_layout.addWidget(self.log_output, 1)

        self.build_scroll_area = QScrollArea()
        self.build_scroll_area.setWidgetResizable(True)
        self.build_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.build_scroll_area.setMinimumWidth(360)
        self.build_scroll_area.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        top_content = QWidget()
        top_layout = QVBoxLayout(top_content)
        top_layout.setContentsMargins(0, 0, 0, 0)

        config_group = QGroupBox("建庫設定")
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
        form.addRow("ZenQuotes API 金鑰", api_key_box)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.textChanged.connect(self._refresh_path_views)
        browse_button = QPushButton("瀏覽...")
        browse_button.clicked.connect(self._browse_output_dir)
        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.addWidget(self.output_dir_edit, 1)
        path_layout.addWidget(browse_button)
        form.addRow("輸出資料夾", path_row)

        self.source_combo = QComboBox()
        self.source_combo.addItem("英文詩 + 哲思語錄", "all")
        self.source_combo.addItem("只抓英文詩", "poems")
        self.source_combo.addItem("只抓哲思語錄", "quotes")
        self.source_combo.currentIndexChanged.connect(self._sync_source_panels_for_selection)
        form.addRow("建庫來源", self.source_combo)

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

        form.addRow("英文詩目標數量", self.poem_target_spin)
        form.addRow("哲思句目標數量", self.quote_target_spin)
        form.addRow("每批抓取筆數", self.batch_size_spin)
        form.addRow("請求間隔（秒）", self.interval_spin)
        form.addRow("每幾筆自動儲存", self.save_every_spin)
        form.addRow("請求逾時（秒）", self.request_timeout_spin)
        form.addRow("最大重試次數", self.max_retries_spin)
        top_layout.addWidget(config_group)

        top_layout.addWidget(self._create_paths_group())
        top_layout.addStretch(1)

        self.build_scroll_area.setWidget(top_content)
        self.top_splitter.addWidget(self.log_panel)
        self.top_splitter.addWidget(self.build_scroll_area)
        self.top_splitter.setStretchFactor(0, 3)
        self.top_splitter.setStretchFactor(1, 2)

        self.runtime_panel = QWidget()
        self.runtime_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Minimum,
        )
        runtime_layout = QVBoxLayout(self.runtime_panel)
        runtime_layout.setContentsMargins(0, 0, 0, 0)
        runtime_layout.setSpacing(8)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.save_settings_button = QPushButton("儲存設定")
        self.save_settings_button.clicked.connect(self._save_settings)
        self.start_button = QPushButton("開始建庫")
        self.start_button.clicked.connect(self._start_build)
        self.cancel_button = QPushButton("停止 / 取消")
        self.cancel_button.clicked.connect(self._cancel_build)
        self.cancel_button.setEnabled(False)
        self.copy_recent_log_button = QPushButton("複製最近日誌內容")
        self.copy_recent_log_button.clicked.connect(self._copy_recent_log_content)
        self.open_translator_button = QPushButton("開啟 VerseArchiveTranslator")
        self.open_translator_button.clicked.connect(self._open_translator_window)

        action_row.addWidget(self.save_settings_button)
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addStretch(1)
        action_row.addWidget(self.copy_recent_log_button)
        action_row.addWidget(self.open_translator_button)
        runtime_layout.addLayout(action_row)

        self.runtime_status_group = QGroupBox("執行狀態")
        self.runtime_status_group.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        progress_layout = QVBoxLayout(self.runtime_status_group)
        progress_layout.setContentsMargins(10, 12, 10, 10)
        progress_layout.setSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("待命中")

        stats_grid = QGridLayout()
        self.accepted_label = QLabel("0")
        self.review_label = QLabel("0")
        self.rejected_label = QLabel("0")
        self.skipped_label = QLabel("0")
        self.processed_label = QLabel("0")

        stats_grid.addWidget(QLabel("已通過"), 0, 0)
        stats_grid.addWidget(self.accepted_label, 0, 1)
        stats_grid.addWidget(QLabel("待審"), 0, 2)
        stats_grid.addWidget(self.review_label, 0, 3)
        stats_grid.addWidget(QLabel("已拒絕"), 1, 0)
        stats_grid.addWidget(self.rejected_label, 1, 1)
        stats_grid.addWidget(QLabel("已略過"), 1, 2)
        stats_grid.addWidget(self.skipped_label, 1, 3)
        stats_grid.addWidget(QLabel("本次已處理"), 2, 0)
        stats_grid.addWidget(self.processed_label, 2, 1)

        source_panel = QWidget()
        source_grid = QGridLayout(source_panel)
        source_grid.setContentsMargins(0, 0, 0, 0)
        source_grid.setHorizontalSpacing(8)
        source_grid.setVerticalSpacing(8)
        source_grid.addWidget(self._create_source_progress_group("poems", "英文詩"), 0, 0)
        source_grid.addWidget(self._create_source_progress_group("quotes", "哲思語錄"), 0, 1)
        source_grid.setColumnStretch(0, 1)
        source_grid.setColumnStretch(1, 1)

        self.summary_group = QGroupBox("全域摘要")
        summary_layout = QVBoxLayout(self.summary_group)
        summary_layout.setContentsMargins(10, 12, 10, 10)
        summary_layout.setSpacing(6)
        summary_layout.addLayout(stats_grid)
        self.summary_label = QLabel("尚未開始建庫。")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color: #555;")
        summary_layout.addWidget(self.summary_label)

        details_row = QHBoxLayout()
        details_row.setSpacing(8)
        details_row.addWidget(source_panel, 3)
        details_row.addWidget(self.summary_group, 2)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        progress_layout.addLayout(details_row)
        runtime_layout.addWidget(self.runtime_status_group, 1)
        self.runtime_panel.setMinimumHeight(280)

        self.build_splitter.addWidget(self.top_splitter)
        self.build_splitter.addWidget(self.runtime_panel)
        self.build_splitter.setStretchFactor(0, 4)
        self.build_splitter.setStretchFactor(1, 2)
        self.build_splitter.setSizes([580, 280])

        layout.addWidget(self.build_splitter, 1)

        return widget

    def _create_filter_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        description = QLabel(
            "這裡的規則會直接套用到目前建庫流程。每條規則都可啟用或停用，並設定命中後要通過、進待審，或直接拒絕。"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.filter_editor = FilterSettingsEditor()
        scroll_area.setWidget(self.filter_editor)
        layout.addWidget(scroll_area, 1)

        button_row = QHBoxLayout()
        self.filter_save_button = QPushButton("儲存過濾設定")
        self.filter_save_button.clicked.connect(self._save_settings)
        self.filter_reset_button = QPushButton("還原預設值")
        self.filter_reset_button.clicked.connect(self._restore_filter_defaults)
        button_row.addWidget(self.filter_save_button)
        button_row.addWidget(self.filter_reset_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        return widget

    def _create_path_display(self) -> QLineEdit:
        field = QLineEdit()
        field.setReadOnly(True)
        return field

    def _create_paths_group(self) -> QGroupBox:
        group = QGroupBox("路徑與診斷")
        layout = QGridLayout(group)
        layout.setColumnStretch(1, 1)

        self.settings_path_display = self._create_path_display()
        self.logs_dir_display = self._create_path_display()
        self.latest_log_display = self._create_path_display()
        self.output_path_display = self._create_path_display()

        settings_open_button = QPushButton("開啟設定檔位置")
        settings_open_button.clicked.connect(self._open_settings_location)

        logs_open_button = QPushButton("開啟日誌資料夾")
        logs_open_button.clicked.connect(self._open_logs_directory)

        latest_log_open_button = QPushButton("開啟最近日誌位置")
        latest_log_open_button.clicked.connect(self._open_latest_log_location)

        output_open_button = QPushButton("開啟輸出資料夾")
        output_open_button.clicked.connect(self._open_output_directory)

        layout.addWidget(QLabel("設定檔位置"), 0, 0)
        layout.addWidget(self.settings_path_display, 0, 1)
        layout.addWidget(settings_open_button, 0, 2)

        layout.addWidget(QLabel("日誌資料夾"), 1, 0)
        layout.addWidget(self.logs_dir_display, 1, 1)
        layout.addWidget(logs_open_button, 1, 2)

        layout.addWidget(QLabel("最近啟動日誌"), 2, 0)
        layout.addWidget(self.latest_log_display, 2, 1)
        layout.addWidget(latest_log_open_button, 2, 2)

        layout.addWidget(QLabel("目前輸出資料夾"), 3, 0)
        layout.addWidget(self.output_path_display, 3, 1)
        layout.addWidget(output_open_button, 3, 2)
        return group

    def _create_source_progress_group(self, source: str, title: str) -> QGroupBox:
        group = QGroupBox(f"{title}進度")
        layout = QVBoxLayout(group)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        status_label = QLabel("待命中")
        status_label.setWordWrap(True)

        stats_grid = QGridLayout()
        accepted_label = QLabel("0")
        review_label = QLabel("0")
        rejected_label = QLabel("0")
        skipped_label = QLabel("0")
        processed_label = QLabel("0")

        stats_grid.addWidget(QLabel("已通過"), 0, 0)
        stats_grid.addWidget(accepted_label, 0, 1)
        stats_grid.addWidget(QLabel("待審"), 0, 2)
        stats_grid.addWidget(review_label, 0, 3)
        stats_grid.addWidget(QLabel("已拒絕"), 1, 0)
        stats_grid.addWidget(rejected_label, 1, 1)
        stats_grid.addWidget(QLabel("已略過"), 1, 2)
        stats_grid.addWidget(skipped_label, 1, 3)
        stats_grid.addWidget(QLabel("本次已處理"), 2, 0)
        stats_grid.addWidget(processed_label, 2, 1)

        layout.addWidget(progress_bar)
        layout.addWidget(status_label)
        layout.addLayout(stats_grid)

        self._source_widgets[source] = _SourceWidgets(
            progress_bar=progress_bar,
            status_label=status_label,
            accepted_label=accepted_label,
            review_label=review_label,
            rejected_label=rejected_label,
            skipped_label=skipped_label,
            processed_label=processed_label,
        )
        return group

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
        self._refresh_path_views()
        self._sync_source_panels_for_selection()

    def _current_output_directory(self) -> Path:
        return resolve_output_directory(self.output_dir_edit.text().strip())

    def _target_for_source(self, source: str) -> int:
        if source == "poems":
            return self.poem_target_spin.value()
        if source == "quotes":
            return self.quote_target_spin.value()
        return 0

    def _refresh_path_views(self, *_: object) -> None:
        if not hasattr(self, "settings_path_display"):
            return
        self.settings_path_display.setText(str(self.settings_store.path.resolve()))
        self.logs_dir_display.setText(str(get_logs_directory().resolve()))
        latest_log = find_latest_log_path("builder-gui")
        self.latest_log_display.setText(str(latest_log.resolve()) if latest_log is not None else "尚未找到")
        self.output_path_display.setText(str(self._current_output_directory()))

    def _current_session_log_excerpt(self) -> str:
        if not hasattr(self, "log_output"):
            return ""
        content = self.log_output.toPlainText().strip()
        if not content:
            return ""
        lines = content.splitlines()
        if len(lines) <= 2:
            return ""
        return tail_text(content, max_lines=DEFAULT_LOG_TAIL_LINES)

    def _copy_recent_log_content(self) -> None:
        clipboard_text = self._current_session_log_excerpt()
        copied_label = f"目前畫面中的最近 {DEFAULT_LOG_TAIL_LINES} 行日誌"

        if not clipboard_text:
            latest_log = find_latest_log_path("builder-gui")
            if latest_log is None:
                self.status_label.setText("目前沒有可複製的日誌。")
                QMessageBox.information(self, "尚未找到日誌", "目前沒有可複製的 VerseArchiveCurator 日誌。")
                return
            try:
                clipboard_text = read_log_tail(latest_log, max_lines=DEFAULT_LOG_TAIL_LINES)
            except OSError as error:
                QMessageBox.critical(self, "無法讀取日誌", str(error))
                return
            if not clipboard_text:
                self.status_label.setText("最近日誌內容為空白。")
                QMessageBox.information(self, "日誌內容為空", "已找到最近日誌，但內容為空白。")
                return
            copied_label = f"最近啟動日誌的最後 {DEFAULT_LOG_TAIL_LINES} 行"

        QApplication.clipboard().setText(clipboard_text)
        self.status_label.setText(f"已複製{copied_label}。")
        self._append_log(f"已複製{copied_label}。")

    def _open_directory(self, path: Path, *, ensure_exists: bool = False) -> None:
        try:
            opened = open_path_location(path, ensure_exists=ensure_exists)
        except FileNotFoundError:
            QMessageBox.warning(self, "找不到路徑", f"找不到指定路徑：\n{path}")
            return
        except Exception as error:
            QMessageBox.critical(self, "無法開啟路徑", str(error))
            return

        self.status_label.setText(f"已開啟：{opened}")
        self._append_log(f"已開啟路徑：{opened}")

    def _open_settings_location(self) -> None:
        self.settings_store.base_dir.mkdir(parents=True, exist_ok=True)
        self._open_directory(self.settings_store.path, ensure_exists=True)

    def _open_logs_directory(self) -> None:
        self._open_directory(get_logs_directory(), ensure_exists=True)

    def _open_latest_log_location(self) -> None:
        latest_log = find_latest_log_path("builder-gui")
        if latest_log is None:
            QMessageBox.information(self, "尚未找到日誌", "目前尚未找到 VerseArchiveCurator 的啟動日誌。")
            return
        self._open_directory(latest_log)

    def _open_output_directory(self) -> None:
        self._open_directory(self._current_output_directory(), ensure_exists=True)

    def _set_source_panel_state(self, source: str, *, status: str, active: bool) -> None:
        widgets = self._source_widgets.get(source)
        if widgets is None:
            return
        widgets.progress_bar.setValue(0)
        widgets.status_label.setText(status)
        widgets.accepted_label.setText("0")
        widgets.review_label.setText("0")
        widgets.rejected_label.setText("0")
        widgets.skipped_label.setText("0")
        widgets.processed_label.setText("0")
        widgets.progress_bar.setEnabled(active)

    def _sync_source_panels_for_selection(self, *_: object) -> None:
        selected = str(self.source_combo.currentData() or "all")
        enabled_sources = {"poems", "quotes"} if selected == "all" else {selected}
        for source in SOURCE_LABELS:
            if source in self._source_progress:
                self._update_source_panel(self._source_progress[source])
                continue
            if source in enabled_sources:
                self._set_source_panel_state(source, status="待命中", active=True)
            else:
                self._set_source_panel_state(source, status="本次未啟用", active=False)

    def _update_source_panel(self, payload: BuildProgress) -> None:
        widgets = self._source_widgets.get(payload.source)
        if widgets is None:
            return

        widgets.accepted_label.setText(str(payload.accepted_count))
        widgets.review_label.setText(str(payload.review_count))
        widgets.rejected_label.setText(str(payload.rejected_count))
        widgets.skipped_label.setText(str(payload.skipped_count))
        widgets.processed_label.setText(str(payload.processed_count))
        widgets.status_label.setText(payload.status_text)
        widgets.progress_bar.setEnabled(True)

        if payload.target_count <= 0:
            progress_value = 100 if payload.done else 0
        else:
            progress_value = min(100, int((payload.accepted_count / payload.target_count) * 100))
        widgets.progress_bar.setValue(progress_value)

    def _collect_settings(self) -> AppSettings:
        settings = self.settings.clone()
        stored_output_dir = serialize_app_relative_path(self._current_output_directory()) or "output"
        settings.zenquotes_api_key = self.api_key_edit.text().strip()
        settings.build = BuildSettings(
            output_dir=stored_output_dir,
            poem_target=self.poem_target_spin.value(),
            quote_target=self.quote_target_spin.value(),
            poetry_batch_size=self.batch_size_spin.value(),
            zenquotes_request_interval=self.interval_spin.value(),
            save_every=self.save_every_spin.value(),
            request_timeout=self.request_timeout_spin.value(),
            max_retries=self.max_retries_spin.value(),
            source=str(self.source_combo.currentData()),
        )
        settings.translation.data_dir = stored_output_dir
        settings.filters = self.filter_editor.get_settings()
        return settings.normalized()

    def _refresh_api_key_hint(self) -> None:
        self.api_key_hint.setText(
            "介面僅顯示遮罩後的內容，且不會寫入日誌："
            f"{mask_secret(self.api_key_edit.text())}"
        )

    def _browse_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "選擇輸出資料夾",
            str(self._current_output_directory()),
        )
        if selected:
            self.output_dir_edit.setText(serialize_app_relative_path(selected))
            self._refresh_path_views()

    def _apply_initial_workspace_layout(self) -> None:
        if not hasattr(self, "build_splitter"):
            return

        total_height = self.build_splitter.size().height()
        if total_height <= 0:
            total_height = max(self.height() - 120, 680)

        bottom_height = min(max(int(total_height * 0.34), 280), 340)
        top_height = max(total_height - bottom_height, 320)
        self.build_splitter.setSizes([top_height, bottom_height])

        if not hasattr(self, "top_splitter"):
            return

        total_width = self.top_splitter.size().width()
        if total_width <= 0:
            total_width = max(self.width() - 80, 980)
        settings_width = min(max(int(total_width * 0.34), 360), 440)
        log_width = max(total_width - settings_width, 520)
        self.top_splitter.setSizes([log_width, settings_width])

    def _focus_runtime_panel(self) -> None:
        QApplication.processEvents()
        sizes = self.build_splitter.sizes()
        total_height = sum(size for size in sizes if size > 0)
        if total_height <= 0:
            total_height = max(self.height() - 80, 720)

        minimum_top = 240
        maximum_bottom = max(total_height - minimum_top, 280)
        preferred_bottom = max(int(total_height * 0.42), 300)
        bottom_height = min(preferred_bottom, maximum_bottom)
        top_height = max(total_height - bottom_height, minimum_top)
        self.build_splitter.setSizes([top_height, bottom_height])
        self.cancel_button.setFocus(Qt.OtherFocusReason)

    def _append_log(self, message: str) -> None:
        self.log_output.appendPlainText(message)
        self.log_output.ensureCursorVisible()

    def _save_settings(self) -> None:
        self.settings = self._collect_settings()
        saved_path = self.settings_store.save(self.settings)
        self._refresh_path_views()
        self._append_log(f"設定已儲存至 {saved_path}")
        self.status_label.setText("設定已儲存。")

    def _restore_filter_defaults(self) -> None:
        self.filter_editor.set_settings(FilterSettings())
        self.status_label.setText("過濾規則已還原為預設值。")
        self._append_log("過濾規則已還原為預設值。")

    def _toggle_running_state(self, is_running: bool) -> None:
        self.start_button.setEnabled(not is_running)
        self.cancel_button.setEnabled(is_running)
        self.save_settings_button.setEnabled(not is_running)
        self.open_translator_button.setEnabled(not is_running)
        self.filter_save_button.setEnabled(not is_running)
        self.filter_reset_button.setEnabled(not is_running)

    def _start_build(self) -> None:
        self._save_settings()
        self._source_progress.clear()
        self._sync_source_panels_for_selection()
        self.progress_bar.setValue(0)
        self.status_label.setText("準備開始建庫...")
        self.summary_label.setText("建庫執行中。")
        self.log_output.clear()
        self._append_log("已送出建庫工作。")
        self._append_log(f"輸出資料夾：{self._current_output_directory()}")
        self._append_log("建庫來源已啟動；若選擇全部來源，英文詩與哲思語錄會並行抓取。")
        self._focus_runtime_panel()

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
        self.status_label.setText("已送出取消要求...")
        self._append_log("使用者要求取消建庫。")

    def _handle_progress(self, payload: object) -> None:
        if not isinstance(payload, BuildProgress):
            return
        self._source_progress[payload.source] = payload
        self._update_source_panel(payload)
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
        self.status_label.setText(f"{_humanize_source(payload.source)}：{payload.status_text}")

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

        cancelled = False
        summary_lines: list[str] = []
        for source_name, result in results.items():
            if not isinstance(result, BuildResult):
                continue
            cancelled = cancelled or result.cancelled
            final_status = (
                f"{_humanize_source(source_name)}建庫已取消。"
                if result.cancelled
                else f"{_humanize_source(source_name)}建庫已完成。"
            )
            final_progress = BuildProgress(
                source=source_name,
                status_text=final_status,
                accepted_count=result.accepted_count,
                review_count=result.review_count,
                rejected_count=result.rejected_count,
                skipped_count=result.skipped_count,
                processed_count=result.processed_count,
                target_count=self._target_for_source(source_name),
                reason_counts=result.reason_counts,
                done=not result.cancelled,
                cancelled=result.cancelled,
            )
            self._source_progress[source_name] = final_progress
            self._update_source_panel(final_progress)
            summary_lines.append(
                f"{_humanize_source(source_name)}：已處理 {result.processed_count} 筆，"
                f"已通過 {result.accepted_count} 筆，待審 {result.review_count} 筆，"
                f"已拒絕 {result.rejected_count} 筆，已略過 {result.skipped_count} 筆"
            )
            if result.reason_counts:
                top_reasons = ", ".join(
                    f"{_humanize_reason(reason)}（{count}）"
                    for reason, count in sorted(
                        result.reason_counts.items(),
                        key=lambda item: item[1],
                        reverse=True,
                    )[:5]
                )
                summary_lines.append(f"主要命中原因：{top_reasons}")

        totals = self._summarize_progress()
        self.accepted_label.setText(str(totals.accepted))
        self.review_label.setText(str(totals.review))
        self.rejected_label.setText(str(totals.rejected))
        self.skipped_label.setText(str(totals.skipped))
        self.processed_label.setText(str(totals.processed))
        if totals.target > 0 and not cancelled:
            self.progress_bar.setValue(100)

        self.summary_label.setText("\n".join(summary_lines) if summary_lines else "建庫已完成。")
        self.status_label.setText("建庫已取消。" if cancelled else "建庫已完成。")
        self._append_log("建庫已結束。" if cancelled else "建庫已成功完成。")
        self._toggle_running_state(False)

    def _handle_failed(self, message: str) -> None:
        self.status_label.setText("建庫失敗。")
        self.summary_label.setText(message)
        self._append_log(f"建庫失敗：{message}")
        self._toggle_running_state(False)
        QMessageBox.critical(self, "建庫失敗", message)

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

    def showEvent(self, event: Any) -> None:  # noqa: N802
        super().showEvent(event)
        if self._initial_runtime_layout_applied:
            return
        self._initial_runtime_layout_applied = True
        QTimer.singleShot(0, self._apply_initial_workspace_layout)

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        if self._worker is not None:
            response = QMessageBox.question(
                self,
                "建庫仍在執行",
                "目前仍有建庫工作在執行中。要先取消並關閉視窗嗎？",
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


if __name__ == "__main__":
    raise SystemExit(main())
