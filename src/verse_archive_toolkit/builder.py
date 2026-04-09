from __future__ import annotations

import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from verse_archive_toolkit.filters import evaluate_poem_filters, evaluate_quote_filters
from verse_archive_toolkit.http import make_session, safe_get_json
from verse_archive_toolkit.records import (
    build_poem_record,
    build_quote_record,
    poem_key,
    quote_key,
    review_key,
)
from verse_archive_toolkit.settings import ToolkitConfig
from verse_archive_toolkit.storage import load_json_list, write_json


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[object], None]


@dataclass(slots=True)
class BuildProgress:
    source: str
    status_text: str
    accepted_count: int
    review_count: int
    rejected_count: int
    skipped_count: int
    processed_count: int
    target_count: int
    reason_counts: dict[str, int]
    done: bool = False
    cancelled: bool = False


@dataclass(slots=True)
class BuildHooks:
    log: LogCallback | None = None
    progress: ProgressCallback | None = None
    should_cancel: Callable[[], bool] | None = None


@dataclass(slots=True)
class BuildResult:
    source: str
    accepted_count: int
    review_count: int
    rejected_count: int
    skipped_count: int
    processed_count: int
    reason_counts: dict[str, int]
    accepted_path: Path
    review_path: Path
    cancelled: bool = False


@dataclass(slots=True)
class _BuildState:
    source: str
    accepted_count: int
    review_count: int
    rejected_count: int = 0
    skipped_count: int = 0
    processed_count: int = 0
    reason_counts: Counter[str] = field(default_factory=Counter)
    target_count: int = 0


def _noop_log(_: str) -> None:
    return


def _noop_progress(_: object) -> None:
    return


def _should_continue(hooks: BuildHooks) -> bool:
    if hooks.should_cancel is None:
        return True
    return not hooks.should_cancel()


def _emit_progress(hooks: BuildHooks, state: _BuildState, status_text: str, *, done: bool = False, cancelled: bool = False) -> None:
    callback = hooks.progress or _noop_progress
    callback(
        BuildProgress(
            source=state.source,
            status_text=status_text,
            accepted_count=state.accepted_count,
            review_count=state.review_count,
            rejected_count=state.rejected_count,
            skipped_count=state.skipped_count,
            processed_count=state.processed_count,
            target_count=state.target_count,
            reason_counts=dict(state.reason_counts),
            done=done,
            cancelled=cancelled,
        )
    )


def _log(hooks: BuildHooks, message: str) -> None:
    callback = hooks.log or _noop_log
    callback(message)


def _interruptible_sleep(seconds: float, hooks: BuildHooks) -> bool:
    remaining = max(0.0, seconds)
    while remaining > 0:
        if not _should_continue(hooks):
            return False
        step = min(0.2, remaining)
        time.sleep(step)
        remaining -= step
    return True


def _save_progress(
    accepted: list[dict[str, object]],
    review_items: list[dict[str, object]],
    accepted_path: Path,
    review_path: Path,
) -> None:
    write_json(accepted_path, accepted)
    write_json(review_path, review_items)


def _finalize_result(
    state: _BuildState,
    accepted_path: Path,
    review_path: Path,
    *,
    cancelled: bool = False,
) -> BuildResult:
    return BuildResult(
        source=state.source,
        accepted_count=state.accepted_count,
        review_count=state.review_count,
        rejected_count=state.rejected_count,
        skipped_count=state.skipped_count,
        processed_count=state.processed_count,
        reason_counts=dict(state.reason_counts),
        accepted_path=accepted_path,
        review_path=review_path,
        cancelled=cancelled,
    )


def build_poem_archive(
    config: ToolkitConfig,
    hooks: BuildHooks | None = None,
) -> BuildResult:
    hooks = hooks or BuildHooks()
    poems = load_json_list(config.poems_file)
    review_items = load_json_list(config.poems_review_file)

    seen = {poem_key(item) for item in poems if poem_key(item) != "|||"}
    review_seen = {poem_key(item) for item in review_items if poem_key(item) != "|||"}
    all_seen = seen | review_seen

    state = _BuildState(
        source="poems",
        accepted_count=len(poems),
        review_count=len(review_items),
        target_count=config.poem_target,
    )

    _log(
        hooks,
        f"[英文詩] 已載入 {len(poems)} 筆通過資料與 {len(review_items)} 筆待審資料。",
    )
    _emit_progress(hooks, state, "英文詩資料庫已就緒。")

    if config.poem_target <= 0 or len(poems) >= config.poem_target:
        return _finalize_result(state, config.poems_file, config.poems_review_file)

    session = make_session()
    added_since_save = 0

    while len(poems) < config.poem_target:
        if not _should_continue(hooks):
            _save_progress(poems, review_items, config.poems_file, config.poems_review_file)
            _log(hooks, "[英文詩] 已收到取消要求。")
            _emit_progress(hooks, state, "英文詩建庫已取消。", done=True, cancelled=True)
            return _finalize_result(
                state,
                config.poems_file,
                config.poems_review_file,
                cancelled=True,
            )

        take = min(config.poetry_batch_size, config.poem_target - len(poems))
        payload = safe_get_json(
            session=session,
            url=f"https://poetrydb.org/random/{take}/author,title,lines,linecount",
            timeout=config.request_timeout,
            max_retries=config.max_retries,
        )

        if not isinstance(payload, list):
            state.reason_counts["poems.invalid_payload"] += 1
            _log(hooks, "[英文詩] PoetryDB 回傳格式異常，準備重試。")
            if not _interruptible_sleep(1, hooks):
                continue
            continue

        for item in payload:
            if not _should_continue(hooks):
                break

            state.processed_count += 1
            author = str(item.get("author", "")).strip()
            title = str(item.get("title", "")).strip()
            lines = item.get("lines", []) or []

            if not author or not title or not isinstance(lines, list):
                state.skipped_count += 1
                state.reason_counts["poems.invalid_item"] += 1
                continue

            poem = build_poem_record(title=title, author=author, lines=lines)
            unique_key = poem_key(poem)

            if unique_key in all_seen:
                state.skipped_count += 1
                state.reason_counts["poems.duplicate"] += 1
                continue

            decision = evaluate_poem_filters(poem, config.filter_settings.poetry)
            all_seen.add(unique_key)

            if not decision.matched or decision.action == "accept":
                poems.append(poem)
                seen.add(unique_key)
                state.accepted_count = len(poems)
            elif decision.action == "review":
                review_items.append(
                    {
                        **poem,
                        "reason": decision.reason,
                        "filter_detail": decision.detail or "",
                    }
                )
                review_seen.add(unique_key)
                state.review_count = len(review_items)
                state.reason_counts[decision.reason or "poems.review"] += 1
            else:
                state.rejected_count += 1
                state.reason_counts[decision.reason or "poems.reject"] += 1

            added_since_save += 1

            if len(poems) >= config.poem_target:
                break

            if added_since_save >= config.save_every:
                _save_progress(poems, review_items, config.poems_file, config.poems_review_file)
                _log(
                    hooks,
                    f"[英文詩] 已儲存檢查點（通過 {len(poems)} / "
                    f"待審 {len(review_items)} / 拒絕 {state.rejected_count}）。",
                )
                added_since_save = 0

            _emit_progress(
                hooks,
                state,
                f"英文詩進度：已通過 {len(poems)} / {config.poem_target}",
            )

        _emit_progress(
            hooks,
            state,
            f"英文詩進度：已通過 {len(poems)} / {config.poem_target}",
        )
        if not _interruptible_sleep(0.5, hooks):
            continue

    _save_progress(poems, review_items, config.poems_file, config.poems_review_file)
    _log(
        hooks,
        f"[英文詩] 已完成，通過 {len(poems)} / 待審 {len(review_items)} / "
        f"拒絕 {state.rejected_count}。",
    )
    _emit_progress(hooks, state, "英文詩建庫已完成。", done=True)
    return _finalize_result(state, config.poems_file, config.poems_review_file)


def _fetch_zenquotes_authors(config: ToolkitConfig) -> list[dict[str, object]]:
    session = make_session()
    payload = safe_get_json(
        session=session,
        url=f"https://zenquotes.io/api/authors/{config.zenquotes_api_key}",
        timeout=config.request_timeout,
        max_retries=config.max_retries,
    )
    return payload if isinstance(payload, list) else []


def _fetch_zenquotes_quotes_by_author(
    author_tag: str,
    config: ToolkitConfig,
) -> list[dict[str, object]]:
    session = make_session()
    payload = safe_get_json(
        session=session,
        url=f"https://zenquotes.io/api/quotes/author/{author_tag}/{config.zenquotes_api_key}",
        timeout=config.request_timeout,
        max_retries=config.max_retries,
    )
    return payload if isinstance(payload, list) else []


def build_quote_archive(
    config: ToolkitConfig,
    hooks: BuildHooks | None = None,
) -> BuildResult:
    hooks = hooks or BuildHooks()

    quotes = load_json_list(config.quotes_file)
    review_items = load_json_list(config.quotes_review_file)

    seen = {quote_key(item) for item in quotes if quote_key(item) != "|||"}
    review_seen = {review_key(item) for item in review_items if review_key(item) != "|||"}
    all_seen = seen | review_seen

    state = _BuildState(
        source="quotes",
        accepted_count=len(quotes),
        review_count=len(review_items),
        target_count=config.quote_target,
    )

    _log(
        hooks,
        f"[哲思語錄] 已載入 {len(quotes)} 筆通過資料與 {len(review_items)} 筆待審資料。",
    )
    _emit_progress(hooks, state, "哲思語錄資料庫已就緒。")

    if config.quote_target <= 0 or len(quotes) >= config.quote_target:
        return _finalize_result(state, config.quotes_file, config.quotes_review_file)

    if not config.zenquotes_api_key:
        raise ValueError(
            "抓取哲思語錄時需要 ZenQuotes API 金鑰。"
            "請在環境變數、本機設定，或 CLI 的 --zenquotes-api-key 中提供。"
        )

    authors = _fetch_zenquotes_authors(config)
    _log(hooks, f"[哲思語錄] 已從 ZenQuotes 取得 {len(authors)} 組作者標籤。")
    added_since_save = 0

    for index, author in enumerate(authors, start=1):
        if len(quotes) >= config.quote_target:
            break

        if not _should_continue(hooks):
            _save_progress(quotes, review_items, config.quotes_file, config.quotes_review_file)
            _log(hooks, "[哲思語錄] 已收到取消要求。")
            _emit_progress(hooks, state, "哲思語錄建庫已取消。", done=True, cancelled=True)
            return _finalize_result(
                state,
                config.quotes_file,
                config.quotes_review_file,
                cancelled=True,
            )

        author_tag = str(author.get("t", "")).strip()
        display_name = str(author.get("a", "")).strip()
        if not author_tag:
            state.skipped_count += 1
            state.reason_counts["quotes.invalid_author_tag"] += 1
            continue

        try:
            payload = _fetch_zenquotes_quotes_by_author(author_tag, config)
        except Exception as error:
            state.reason_counts["quotes.author_fetch_error"] += 1
            _log(hooks, f"[哲思語錄] 抓取 {display_name or author_tag} 失敗：{error}")
            if not _interruptible_sleep(config.zenquotes_request_interval, hooks):
                continue
            continue

        for item in payload:
            if not _should_continue(hooks):
                break

            state.processed_count += 1
            text = str(item.get("q", "")).strip()
            author_name = str(item.get("a", display_name)).strip()

            if not text or not author_name:
                state.skipped_count += 1
                state.reason_counts["quotes.invalid_item"] += 1
                continue

            quote = build_quote_record(author=author_name, text=text)
            unique_key = quote_key(quote)

            if unique_key in all_seen:
                state.skipped_count += 1
                state.reason_counts["quotes.duplicate"] += 1
                continue

            decision = evaluate_quote_filters(text, config.filter_settings.quotes)
            all_seen.add(unique_key)

            if not decision.matched or decision.action == "accept":
                quotes.append(quote)
                seen.add(unique_key)
                state.accepted_count = len(quotes)
            elif decision.action == "review":
                review_items.append(
                    {
                        **quote,
                        "reason": decision.reason,
                        "filter_detail": decision.detail or "",
                        "source_tag": author_tag,
                    }
                )
                review_seen.add(unique_key)
                state.review_count = len(review_items)
                state.reason_counts[decision.reason or "quotes.review"] += 1
            else:
                state.rejected_count += 1
                state.reason_counts[decision.reason or "quotes.reject"] += 1

            added_since_save += 1

            if len(quotes) >= config.quote_target:
                break

            if added_since_save >= config.save_every:
                _save_progress(quotes, review_items, config.quotes_file, config.quotes_review_file)
                _log(
                    hooks,
                    f"[哲思語錄] 已儲存檢查點（通過 {len(quotes)} / "
                    f"待審 {len(review_items)} / 拒絕 {state.rejected_count}）。",
                )
                added_since_save = 0

            _emit_progress(
                hooks,
                state,
                f"哲思語錄進度：已通過 {len(quotes)} / {config.quote_target} "
                f"（作者 {index} / {len(authors)}）",
            )

        _emit_progress(
            hooks,
            state,
            f"哲思語錄進度：已通過 {len(quotes)} / {config.quote_target} "
            f"（作者 {index} / {len(authors)}）",
        )
        if not _interruptible_sleep(config.zenquotes_request_interval, hooks):
            continue

    _save_progress(quotes, review_items, config.quotes_file, config.quotes_review_file)
    _log(
        hooks,
        f"[哲思語錄] 已完成，通過 {len(quotes)} / 待審 {len(review_items)} / "
        f"拒絕 {state.rejected_count}。",
    )
    _emit_progress(hooks, state, "哲思語錄建庫已完成。", done=True)
    return _finalize_result(state, config.quotes_file, config.quotes_review_file)


def build_selected_sources(
    config: ToolkitConfig,
    source: str,
    hooks: BuildHooks | None = None,
) -> dict[str, BuildResult]:
    hooks = hooks or BuildHooks()
    if source == "poems":
        return {"poems": build_poem_archive(config=config, hooks=hooks)}

    if source == "quotes":
        return {"quotes": build_quote_archive(config=config, hooks=hooks)}

    if source != "all":
        raise ValueError(f"不支援的建庫來源：{source}")

    results: dict[str, BuildResult] = {}
    future_map: dict[Future[BuildResult], str] = {}
    parallel_cancelled = False

    def should_cancel_parallel() -> bool:
        if parallel_cancelled:
            return True
        if hooks.should_cancel is None:
            return False
        return hooks.should_cancel()

    parallel_hooks = BuildHooks(
        log=hooks.log,
        progress=hooks.progress,
        should_cancel=should_cancel_parallel,
    )
    _log(hooks, "[系統] 已同時啟動英文詩與哲思語錄建庫工作。")

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="verse-archive-build") as executor:
        future_map[executor.submit(build_poem_archive, config, parallel_hooks)] = "poems"
        future_map[executor.submit(build_quote_archive, config, parallel_hooks)] = "quotes"

        first_error: Exception | None = None
        for future in as_completed(future_map):
            source_name = future_map[future]
            source_label = "英文詩" if source_name == "poems" else "哲思語錄"
            try:
                results[source_name] = future.result()
            except Exception as error:
                parallel_cancelled = True
                if first_error is None:
                    first_error = error
                _log(hooks, f"[系統] {source_label}建庫工作失敗，已要求其他來源停止。")

        if first_error is not None:
            raise first_error

    return {name: results[name] for name in ("poems", "quotes") if name in results}


def collect_output_stats(config: ToolkitConfig) -> dict[str, int]:
    return {
        "accepted_poems": len(load_json_list(config.poems_file)),
        "review_poems": len(load_json_list(config.poems_review_file)),
        "accepted_quotes": len(load_json_list(config.quotes_file)),
        "review_quotes": len(load_json_list(config.quotes_review_file)),
    }
