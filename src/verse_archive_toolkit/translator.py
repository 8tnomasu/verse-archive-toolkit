from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from verse_archive_toolkit.records import get_lines, get_nested
from verse_archive_toolkit.storage import load_json_list, write_json


STANDARD_ARCHIVE_FILES = [
    "english_poems.json",
    "english_poems_review.json",
    "philosophy_quotes.json",
    "philosophy_quotes_review.json",
]


class TranslationRepositoryError(RuntimeError):
    pass


@dataclass(slots=True)
class ArchiveDocument:
    path: Path
    records: list[dict[str, Any]]
    mtime_ns: int


@dataclass(slots=True)
class ArchiveEntry:
    file_path: Path
    index: int
    record: dict[str, Any]
    mtime_ns: int

    @property
    def type_label(self) -> str:
        return str(self.record.get("type", "")).strip()

    @property
    def author_en(self) -> str:
        return get_nested(self.record, "author", "en").strip()

    @property
    def title_en(self) -> str:
        return get_nested(self.record, "title", "en").strip()

    @property
    def content_en(self) -> str:
        content = get_nested(self.record, "content", "en").strip()
        if content:
            return content
        return "\n".join(get_lines(self.record))

    @property
    def signature(self) -> str:
        return "|||".join(
            [
                self.type_label,
                self.author_en,
                self.title_en,
                self.content_en,
            ]
        )

    @property
    def summary(self) -> str:
        text = self.content_en.replace("\n", " ").strip()
        return text[:80] + ("..." if len(text) > 80 else "")


def translation_state(record: dict[str, Any]) -> str:
    title_en = get_nested(record, "title", "en").strip()
    author_en = get_nested(record, "author", "en").strip()
    content_en = get_nested(record, "content", "en").strip()

    title_cn = get_nested(record, "title", "cn").strip()
    author_cn = get_nested(record, "author", "cn").strip()
    content_cn = get_nested(record, "content", "cn").strip()

    required_fields: list[tuple[str, str]] = []

    if title_en:
        required_fields.append((title_en, title_cn))
    if author_en:
        required_fields.append((author_en, author_cn))
    if content_en:
        required_fields.append((content_en, content_cn))

    if not required_fields:
        return "untranslated"

    translated_count = sum(1 for _, cn in required_fields if cn.strip())
    if translated_count == 0:
        return "untranslated"
    if translated_count == len(required_fields):
        return "translated"
    return "partial"


class TranslationRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.documents: list[ArchiveDocument] = []

    def load(self) -> None:
        self.documents.clear()
        if not self.data_dir.exists():
            raise TranslationRepositoryError(f"資料目錄不存在：{self.data_dir}")

        candidate_paths: list[Path] = []
        for filename in STANDARD_ARCHIVE_FILES:
            path = self.data_dir / filename
            if path.exists():
                candidate_paths.append(path)

        if not candidate_paths:
            candidate_paths = sorted(self.data_dir.glob("*.json"))

        for path in candidate_paths:
            records = load_json_list(path)
            if not records:
                continue
            self.documents.append(
                ArchiveDocument(
                    path=path,
                    records=records,
                    mtime_ns=path.stat().st_mtime_ns,
                )
            )

    def all_entries(self) -> list[ArchiveEntry]:
        entries: list[ArchiveEntry] = []
        for document in self.documents:
            for index, record in enumerate(document.records):
                if not isinstance(record, dict):
                    continue
                entries.append(
                    ArchiveEntry(
                        file_path=document.path,
                        index=index,
                        record=record,
                        mtime_ns=document.mtime_ns,
                    )
                )
        return entries

    def search(self, query: str) -> list[ArchiveEntry]:
        normalized_query = query.strip().lower()
        entries = self.all_entries()
        if not normalized_query:
            return entries

        results: list[ArchiveEntry] = []
        for entry in entries:
            haystacks = [
                entry.author_en,
                entry.title_en,
                entry.content_en,
                "\n".join(get_lines(entry.record)),
            ]
            joined = "\n".join(part.lower() for part in haystacks if part)
            if normalized_query in joined:
                results.append(entry)
        return results

    def stats(self) -> dict[str, int]:
        translated = 0
        untranslated = 0
        partial = 0
        entries = self.all_entries()

        for entry in entries:
            state = translation_state(entry.record)
            if state == "translated":
                translated += 1
            elif state == "partial":
                partial += 1
            else:
                untranslated += 1

        return {
            "total": len(entries),
            "translated": translated,
            "partial": partial,
            "untranslated": untranslated,
        }

    def random_entry(self, type_filter: str = "all", translation_filter: str = "all") -> ArchiveEntry | None:
        entries = self.all_entries()
        filtered: list[ArchiveEntry] = []

        for entry in entries:
            if type_filter == "poems" and entry.type_label != "english_poem":
                continue
            if type_filter == "quotes" and entry.type_label != "philosophy":
                continue

            state = translation_state(entry.record)
            if translation_filter == "untranslated" and state != "untranslated":
                continue
            if translation_filter == "partial" and state != "partial":
                continue
            if translation_filter == "translated" and state != "translated":
                continue

            filtered.append(entry)

        if not filtered:
            return None

        return random.choice(filtered)

    def save_translation(
        self,
        entry: ArchiveEntry,
        *,
        title_cn: str,
        author_cn: str,
        content_cn: str,
    ) -> ArchiveEntry:
        target_document = next(
            (document for document in self.documents if document.path == entry.file_path),
            None,
        )
        if target_document is None:
            raise TranslationRepositoryError(f"檔案尚未載入：{entry.file_path}")

        current_mtime_ns = entry.file_path.stat().st_mtime_ns
        if current_mtime_ns != entry.mtime_ns:
            raise TranslationRepositoryError(
                f"檔案已被外部修改，請重新載入後再儲存：{entry.file_path}"
            )

        if entry.index >= len(target_document.records):
            raise TranslationRepositoryError("所選資料索引超出範圍。")

        current_record = target_document.records[entry.index]
        current_signature = ArchiveEntry(
            file_path=entry.file_path,
            index=entry.index,
            record=current_record,
            mtime_ns=current_mtime_ns,
        ).signature
        if current_signature != entry.signature:
            raise TranslationRepositoryError("所選資料已被外部修改，請重新載入後再儲存。")

        updated_record = deepcopy(current_record)
        updated_record.setdefault("title", {})
        updated_record.setdefault("author", {})
        updated_record.setdefault("content", {})
        updated_record["title"]["cn"] = title_cn.strip()
        updated_record["author"]["cn"] = author_cn.strip()
        updated_record["content"]["cn"] = content_cn.strip()

        target_document.records[entry.index] = updated_record
        write_json(entry.file_path, target_document.records)

        reloaded_records = load_json_list(entry.file_path)
        target_document.records = reloaded_records
        target_document.mtime_ns = entry.file_path.stat().st_mtime_ns

        return ArchiveEntry(
            file_path=entry.file_path,
            index=entry.index,
            record=target_document.records[entry.index],
            mtime_ns=target_document.mtime_ns,
        )
