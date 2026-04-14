from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from verse_archive_toolkit.app_paths import resolve_output_directory, serialize_app_relative_path
from verse_archive_toolkit.settings_store import SettingsStore
from verse_archive_toolkit.translator import (
    ArchiveEntry,
    TranslationRepository,
    TranslationRepositoryError,
    translation_state,
)

TYPE_LABELS = {
    "english_poem": "英文詩",
    "philosophy": "哲思語錄",
}

STATE_LABELS = {
    "translated": "已完成翻譯",
    "partial": "部分翻譯",
    "untranslated": "未翻譯",
}


def _humanize_type_label(type_label: str) -> str:
    return TYPE_LABELS.get(type_label, type_label or "未分類")


def _humanize_translation_state(state: str) -> str:
    return STATE_LABELS.get(state, state)


class TranslationWindow(QMainWindow):
    def __init__(self, settings_store: SettingsStore | None = None) -> None:
        super().__init__()
        self.settings_store = settings_store or SettingsStore()
        self.settings = self.settings_store.load()
        self.repository: TranslationRepository | None = None
        self.current_results: list[ArchiveEntry] = []
        self.current_entry: ArchiveEntry | None = None
        self._dirty = False
        self._selection_guard = False

        self.setWindowTitle("Verse Archive Toolkit 翻譯輔助工具")
        self.resize(1180, 780)
        self._build_ui()
        self._load_directory(resolve_output_directory(self.settings.translation.data_dir), show_message=False)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #f7f6f2; color: #1e1e1e; }
            QPushButton {
                background: #3b5b3a;
                color: white;
                border-radius: 6px;
                padding: 7px 14px;
            }
            QPlainTextEdit, QLineEdit, QListWidget, QComboBox {
                background: white;
                border: 1px solid #c6c8c0;
                border-radius: 6px;
                padding: 4px 6px;
            }
            """
        )

    def _build_ui(self) -> None:
        central = QWidget()
        layout = QVBoxLayout(central)

        path_row = QHBoxLayout()
        self.data_dir_edit = QLineEdit()
        browse_button = QPushButton("選擇資料夾...")
        browse_button.clicked.connect(self._browse_directory)
        reload_button = QPushButton("重新載入")
        reload_button.clicked.connect(self._reload_repository)
        path_row.addWidget(QLabel("資料來源目錄"))
        path_row.addWidget(self.data_dir_edit, 1)
        path_row.addWidget(browse_button)
        path_row.addWidget(reload_button)
        layout.addLayout(path_row)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜尋 author.en、title.en、content.en 或 content.lines")
        self.search_edit.textChanged.connect(self._refresh_results)
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItem("全部類型", "all")
        self.type_filter_combo.addItem("只看英文詩", "poems")
        self.type_filter_combo.addItem("只看哲思語錄", "quotes")
        self.type_filter_combo.currentIndexChanged.connect(self._refresh_results)
        self.random_state_combo = QComboBox()
        self.random_state_combo.addItem("不限翻譯狀態", "all")
        self.random_state_combo.addItem("完全未翻譯", "untranslated")
        self.random_state_combo.addItem("部分已翻譯", "partial")
        self.random_state_combo.addItem("已完成翻譯", "translated")
        random_button = QPushButton("隨機抽取")
        random_button.clicked.connect(self._random_pick)
        filter_row.addWidget(self.search_edit, 1)
        filter_row.addWidget(self.type_filter_combo)
        filter_row.addWidget(self.random_state_combo)
        filter_row.addWidget(random_button)
        layout.addLayout(filter_row)

        stats_grid = QGridLayout()
        self.total_label = QLabel("0")
        self.translated_label = QLabel("0")
        self.partial_label = QLabel("0")
        self.untranslated_label = QLabel("0")
        stats_grid.addWidget(QLabel("總筆數"), 0, 0)
        stats_grid.addWidget(self.total_label, 0, 1)
        stats_grid.addWidget(QLabel("已完成翻譯"), 0, 2)
        stats_grid.addWidget(self.translated_label, 0, 3)
        stats_grid.addWidget(QLabel("部分翻譯"), 1, 0)
        stats_grid.addWidget(self.partial_label, 1, 1)
        stats_grid.addWidget(QLabel("未翻譯"), 1, 2)
        stats_grid.addWidget(self.untranslated_label, 1, 3)
        layout.addLayout(stats_grid)

        splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("搜尋結果"))
        self.results_list = QListWidget()
        self.results_list.currentItemChanged.connect(self._on_result_changed)
        left_layout.addWidget(self.results_list)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        meta_group = QWidget()
        meta_form = QFormLayout(meta_group)
        self.file_label = QLabel("-")
        self.type_label = QLabel("-")
        self.state_label = QLabel("-")
        meta_form.addRow("檔案", self.file_label)
        meta_form.addRow("類型", self.type_label)
        meta_form.addRow("翻譯狀態", self.state_label)
        right_layout.addWidget(meta_group)

        self.title_en_view = QLineEdit()
        self.title_en_view.setReadOnly(True)
        self.author_en_view = QLineEdit()
        self.author_en_view.setReadOnly(True)
        self.content_en_view = QPlainTextEdit()
        self.content_en_view.setReadOnly(True)

        source_group = QWidget()
        source_form = QFormLayout(source_group)
        source_form.addRow("標題（英文）", self.title_en_view)
        source_form.addRow("作者（英文）", self.author_en_view)
        source_form.addRow("內容（英文）", self.content_en_view)
        right_layout.addWidget(source_group)

        self.title_cn_edit = QLineEdit()
        self.author_cn_edit = QLineEdit()
        self.content_cn_edit = QPlainTextEdit()
        self.title_cn_edit.textChanged.connect(self._mark_dirty_from_ui)
        self.author_cn_edit.textChanged.connect(self._mark_dirty_from_ui)
        self.content_cn_edit.textChanged.connect(self._mark_dirty_from_ui)

        translation_group = QWidget()
        translation_form = QFormLayout(translation_group)
        translation_form.addRow("標題（中文）", self.title_cn_edit)
        translation_form.addRow("作者（中文）", self.author_cn_edit)
        translation_form.addRow("內容（中文）", self.content_cn_edit)
        right_layout.addWidget(translation_group, 1)

        button_row = QHBoxLayout()
        self.prev_button = QPushButton("上一筆")
        self.prev_button.clicked.connect(lambda: self._move_selection(-1))
        self.next_button = QPushButton("下一筆")
        self.next_button.clicked.connect(lambda: self._move_selection(1))
        self.save_button = QPushButton("儲存翻譯")
        self.save_button.clicked.connect(self._save_current_entry)
        button_row.addWidget(self.prev_button)
        button_row.addWidget(self.next_button)
        button_row.addStretch(1)
        button_row.addWidget(self.save_button)
        right_layout.addLayout(button_row)

        self.status_note = QLabel("就緒")
        right_layout.addWidget(self.status_note)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        layout.addWidget(splitter, 1)

        self.setCentralWidget(central)

    def _browse_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "選擇資料來源目錄",
            str(resolve_output_directory(self.data_dir_edit.text().strip() or "output")),
        )
        if not selected:
            return
        self._load_directory(Path(selected))

    def _reload_repository(self) -> None:
        self._load_directory(resolve_output_directory(self.data_dir_edit.text().strip() or "output"))

    def _load_directory(self, directory: Path, *, show_message: bool = True) -> None:
        resolved_directory = resolve_output_directory(directory)
        self.data_dir_edit.setText(serialize_app_relative_path(resolved_directory))
        self.repository = TranslationRepository(resolved_directory)
        try:
            self.repository.load()
        except TranslationRepositoryError as error:
            if show_message:
                QMessageBox.warning(self, "無法載入資料", str(error))
            self.results_list.clear()
            self.current_results = []
            self.repository = None
            self._update_stats()
            self.status_note.setText("找不到可用資料來源，請先選擇資料夾。")
            return

        self.settings.translation.data_dir = serialize_app_relative_path(resolved_directory)
        self.settings_store.save(self.settings)
        self._refresh_results()
        self.status_note.setText(f"已載入資料來源目錄：{resolved_directory}")

    def _update_stats(self) -> None:
        if self.repository is None:
            stats = {"total": 0, "translated": 0, "partial": 0, "untranslated": 0}
        else:
            stats = self.repository.stats()
        self.total_label.setText(str(stats["total"]))
        self.translated_label.setText(str(stats["translated"]))
        self.partial_label.setText(str(stats["partial"]))
        self.untranslated_label.setText(str(stats["untranslated"]))

    def _filtered_entries(self) -> list[ArchiveEntry]:
        if self.repository is None:
            return []

        entries = self.repository.search(self.search_edit.text())
        type_filter = str(self.type_filter_combo.currentData())
        filtered: list[ArchiveEntry] = []
        for entry in entries:
            if type_filter == "poems" and entry.type_label != "english_poem":
                continue
            if type_filter == "quotes" and entry.type_label != "philosophy":
                continue
            filtered.append(entry)
        return filtered

    def _refresh_results(self) -> None:
        preserve_signature = self.current_entry.signature if self.current_entry else None
        self.current_results = self._filtered_entries()
        self.results_list.clear()

        for entry in self.current_results:
            state = translation_state(entry.record)
            title = entry.title_en or "（無標題）"
            author = entry.author_en or "（作者未填）"
            item = QListWidgetItem(
                f"[{_humanize_type_label(entry.type_label)}] {title} | {author}\n"
                f"{entry.summary}\n翻譯狀態：{_humanize_translation_state(state)}"
            )
            item.setData(Qt.UserRole, entry)
            self.results_list.addItem(item)

        self._update_stats()
        if self.current_results:
            self.status_note.setText(f"共有 {len(self.current_results)} 筆符合條件。")
        else:
            self.status_note.setText("目前沒有符合條件的資料。")

        if preserve_signature:
            for row in range(self.results_list.count()):
                candidate = self.results_list.item(row).data(Qt.UserRole)
                if isinstance(candidate, ArchiveEntry) and candidate.signature == preserve_signature:
                    self.results_list.setCurrentRow(row)
                    return

        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
        else:
            self._populate_entry(None)
            self.status_note.setText("目前沒有符合條件的資料。")

    def _populate_entry(self, entry: ArchiveEntry | None) -> None:
        self.current_entry = entry
        self._selection_guard = True
        try:
            if entry is None:
                self.file_label.setText("-")
                self.type_label.setText("-")
                self.state_label.setText("-")
                self.title_en_view.clear()
                self.author_en_view.clear()
                self.content_en_view.clear()
                self.title_cn_edit.clear()
                self.author_cn_edit.clear()
                self.content_cn_edit.clear()
                self._dirty = False
                self.status_note.setText("尚未選取資料。")
                return

            self.file_label.setText(entry.file_path.name)
            self.type_label.setText(_humanize_type_label(entry.type_label))
            self.state_label.setText(_humanize_translation_state(translation_state(entry.record)))
            self.title_en_view.setText(entry.title_en)
            self.author_en_view.setText(entry.author_en)
            self.content_en_view.setPlainText(entry.content_en)
            self.title_cn_edit.setText(entry.record.get("title", {}).get("cn", ""))
            self.author_cn_edit.setText(entry.record.get("author", {}).get("cn", ""))
            self.content_cn_edit.setPlainText(entry.record.get("content", {}).get("cn", ""))
            self._dirty = False
            self.status_note.setText("資料已載入。")
        finally:
            self._selection_guard = False

    def _mark_dirty_from_ui(self) -> None:
        if self._selection_guard or self.current_entry is None:
            return
        title_cn = self.title_cn_edit.text().strip()
        author_cn = self.author_cn_edit.text().strip()
        content_cn = self.content_cn_edit.toPlainText().strip()
        record = self.current_entry.record
        self._dirty = (
            title_cn != str(record.get("title", {}).get("cn", "")).strip()
            or author_cn != str(record.get("author", {}).get("cn", "")).strip()
            or content_cn != str(record.get("content", {}).get("cn", "")).strip()
        )
        self.status_note.setText("有未保存變更。" if self._dirty else "目前內容已儲存。")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Warning)
        message_box.setWindowTitle("未保存變更")
        message_box.setText("目前翻譯內容尚未保存。")
        save_button = message_box.addButton("儲存", QMessageBox.AcceptRole)
        discard_button = message_box.addButton("放棄變更", QMessageBox.DestructiveRole)
        cancel_button = message_box.addButton("取消", QMessageBox.RejectRole)
        message_box.exec()

        clicked = message_box.clickedButton()
        if clicked == save_button:
            return self._save_current_entry(show_message=False)
        if clicked == discard_button:
            self._dirty = False
            return True
        if clicked == cancel_button:
            return False
        return False

    def _on_result_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._selection_guard:
            return

        if not self._confirm_discard():
            self._selection_guard = True
            try:
                if previous is not None:
                    self.results_list.setCurrentItem(previous)
                else:
                    self.results_list.clearSelection()
            finally:
                self._selection_guard = False
            return

        entry = current.data(Qt.UserRole) if current is not None else None
        if isinstance(entry, ArchiveEntry):
            self._populate_entry(entry)
        else:
            self._populate_entry(None)

    def _move_selection(self, offset: int) -> None:
        if self.results_list.count() == 0:
            return
        current_row = self.results_list.currentRow()
        next_row = max(0, min(self.results_list.count() - 1, current_row + offset))
        self.results_list.setCurrentRow(next_row)

    def _save_current_entry(self, *, show_message: bool = True) -> bool:
        if self.repository is None or self.current_entry is None:
            return False

        try:
            updated_entry = self.repository.save_translation(
                self.current_entry,
                title_cn=self.title_cn_edit.text(),
                author_cn=self.author_cn_edit.text(),
                content_cn=self.content_cn_edit.toPlainText(),
            )
        except TranslationRepositoryError as error:
            QMessageBox.warning(self, "無法儲存翻譯", str(error))
            return False

        self._dirty = False
        self._populate_entry(updated_entry)
        self._refresh_results()
        self.status_note.setText("翻譯已儲存。")
        if show_message:
            QMessageBox.information(self, "已儲存", "翻譯已成功儲存。")
        return True

    def _random_pick(self) -> None:
        if self.repository is None:
            return

        entry = self.repository.random_entry(
            type_filter=str(self.type_filter_combo.currentData()),
            translation_filter=str(self.random_state_combo.currentData()),
        )
        if entry is None:
            QMessageBox.information(
                self,
                "沒有符合條件的資料",
                "目前隨機抽取條件下沒有可用資料。",
            )
            return

        self.search_edit.clear()
        self._refresh_results()
        for row in range(self.results_list.count()):
            candidate = self.results_list.item(row).data(Qt.UserRole)
            if isinstance(candidate, ArchiveEntry) and candidate.signature == entry.signature:
                self.results_list.setCurrentRow(row)
                self.results_list.scrollToItem(self.results_list.item(row))
                self.status_note.setText("已隨機選取一筆資料。")
                return

    def closeEvent(self, event: Any) -> None:  # noqa: N802
        if not self._confirm_discard():
            event.ignore()
            return
        event.accept()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    window = TranslationWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
