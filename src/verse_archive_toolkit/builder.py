from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from verse_archive_toolkit.config import ToolkitConfig
from verse_archive_toolkit.filters import get_poem_review_reason, get_quote_review_reason
from verse_archive_toolkit.http import make_session, safe_get_json
from verse_archive_toolkit.records import (
    build_poem_record,
    build_quote_record,
    poem_key,
    quote_key,
    review_key,
)
from verse_archive_toolkit.storage import load_json_list, write_json


ProgressCallback = Callable[[str], None]


@dataclass(slots=True)
class BuildResult:
    accepted_count: int
    review_count: int
    accepted_path: Path
    review_path: Path


def _noop(_: str) -> None:
    return


def _save_progress(
    accepted: list[dict[str, object]],
    review_items: list[dict[str, object]],
    accepted_path: Path,
    review_path: Path,
) -> None:
    write_json(accepted_path, accepted)
    write_json(review_path, review_items)


def build_poem_archive(
    config: ToolkitConfig,
    progress: ProgressCallback | None = None,
) -> BuildResult:
    emit = progress or _noop

    poems = load_json_list(config.poems_file)
    review_items = load_json_list(config.poems_review_file)

    seen = {poem_key(item) for item in poems if poem_key(item) != "|||"}
    review_seen = {poem_key(item) for item in review_items if poem_key(item) != "|||"}
    all_seen = seen | review_seen

    emit(f"[poems] loaded {len(poems)} accepted items and {len(review_items)} review items.")

    if len(poems) >= config.poem_target:
        return BuildResult(
            accepted_count=len(poems),
            review_count=len(review_items),
            accepted_path=config.poems_file,
            review_path=config.poems_review_file,
        )

    session = make_session()
    added_since_save = 0

    while len(poems) < config.poem_target:
        take = min(config.poetry_batch_size, config.poem_target - len(poems))
        payload = safe_get_json(
            session=session,
            url=f"https://poetrydb.org/random/{take}/author,title,lines,linecount",
            timeout=config.request_timeout,
            max_retries=config.max_retries,
        )

        if not isinstance(payload, list):
            emit("[poems] unexpected PoetryDB payload, retrying.")
            time.sleep(1)
            continue

        for item in payload:
            author = str(item.get("author", "")).strip()
            title = str(item.get("title", "")).strip()
            lines = item.get("lines", []) or []

            if not author or not title or not isinstance(lines, list):
                continue

            poem = build_poem_record(title=title, author=author, lines=lines)
            unique_key = poem_key(poem)

            if unique_key in all_seen:
                continue

            reason = get_poem_review_reason(poem)
            if reason is None:
                poems.append(poem)
                seen.add(unique_key)
            else:
                review_items.append({**poem, "reason": reason})
                review_seen.add(unique_key)

            all_seen.add(unique_key)
            added_since_save += 1

            if len(poems) >= config.poem_target:
                break

            if added_since_save >= config.save_every:
                _save_progress(
                    accepted=poems,
                    review_items=review_items,
                    accepted_path=config.poems_file,
                    review_path=config.poems_review_file,
                )
                emit(
                    f"[poems] checkpoint saved ({len(poems)} accepted / "
                    f"{len(review_items)} review)."
                )
                added_since_save = 0

        emit(f"[poems] progress: {len(poems)}/{config.poem_target} accepted.")
        time.sleep(0.5)

    _save_progress(
        accepted=poems,
        review_items=review_items,
        accepted_path=config.poems_file,
        review_path=config.poems_review_file,
    )
    emit(f"[poems] completed with {len(poems)} accepted items.")

    return BuildResult(
        accepted_count=len(poems),
        review_count=len(review_items),
        accepted_path=config.poems_file,
        review_path=config.poems_review_file,
    )


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
    progress: ProgressCallback | None = None,
) -> BuildResult:
    emit = progress or _noop

    if not config.zenquotes_api_key:
        raise ValueError(
            "ZENQUOTES_API_KEY is required for the quotes source. "
            "Set it in the environment or pass --zenquotes-api-key."
        )

    quotes = load_json_list(config.quotes_file)
    review_items = load_json_list(config.quotes_review_file)

    seen = {quote_key(item) for item in quotes if quote_key(item) != "|||"}
    review_seen = {review_key(item) for item in review_items if review_key(item) != "|||"}
    all_seen = seen | review_seen

    emit(f"[quotes] loaded {len(quotes)} accepted items and {len(review_items)} review items.")

    if len(quotes) >= config.quote_target:
        return BuildResult(
            accepted_count=len(quotes),
            review_count=len(review_items),
            accepted_path=config.quotes_file,
            review_path=config.quotes_review_file,
        )

    authors = _fetch_zenquotes_authors(config)
    emit(f"[quotes] fetched {len(authors)} author tags from ZenQuotes.")
    added_since_save = 0

    for index, author in enumerate(authors, start=1):
        if len(quotes) >= config.quote_target:
            break

        author_tag = str(author.get("t", "")).strip()
        display_name = str(author.get("a", "")).strip()
        if not author_tag:
            continue

        try:
            payload = _fetch_zenquotes_quotes_by_author(author_tag, config)
        except Exception as error:
            emit(f"[quotes] failed to fetch {display_name or author_tag}: {error}")
            time.sleep(config.zenquotes_request_interval)
            continue

        for item in payload:
            text = str(item.get("q", "")).strip()
            author_name = str(item.get("a", display_name)).strip()

            if not text or not author_name:
                continue

            quote = build_quote_record(author=author_name, text=text)
            unique_key = quote_key(quote)

            if unique_key in all_seen:
                continue

            reason = get_quote_review_reason(text)
            if reason is None:
                quotes.append(quote)
                seen.add(unique_key)
            else:
                review_items.append({**quote, "reason": reason, "source_tag": author_tag})
                review_seen.add(unique_key)

            all_seen.add(unique_key)
            added_since_save += 1

            if len(quotes) >= config.quote_target:
                break

            if added_since_save >= config.save_every:
                _save_progress(
                    accepted=quotes,
                    review_items=review_items,
                    accepted_path=config.quotes_file,
                    review_path=config.quotes_review_file,
                )
                emit(
                    f"[quotes] checkpoint saved ({len(quotes)} accepted / "
                    f"{len(review_items)} review)."
                )
                added_since_save = 0

        emit(f"[quotes] processed {index}/{len(authors)} authors.")
        time.sleep(config.zenquotes_request_interval)

    _save_progress(
        accepted=quotes,
        review_items=review_items,
        accepted_path=config.quotes_file,
        review_path=config.quotes_review_file,
    )
    emit(f"[quotes] completed with {len(quotes)} accepted items.")

    return BuildResult(
        accepted_count=len(quotes),
        review_count=len(review_items),
        accepted_path=config.quotes_file,
        review_path=config.quotes_review_file,
    )


def build_selected_sources(
    config: ToolkitConfig,
    source: str,
    progress: ProgressCallback | None = None,
) -> dict[str, BuildResult]:
    emit = progress or _noop
    tasks = {}

    if source in {"poems", "all"}:
        tasks["poems"] = build_poem_archive
    if source in {"quotes", "all"}:
        tasks["quotes"] = build_quote_archive

    if not tasks:
        raise ValueError(f"Unsupported source selection: {source}")

    if len(tasks) == 1:
        name, func = next(iter(tasks.items()))
        return {name: func(config=config, progress=emit)}

    results: dict[str, BuildResult] = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_map = {
            executor.submit(func, config=config, progress=emit): name
            for name, func in tasks.items()
        }
        for future in as_completed(future_map):
            name = future_map[future]
            results[name] = future.result()

    return results


def collect_output_stats(config: ToolkitConfig) -> dict[str, int]:
    return {
        "accepted_poems": len(load_json_list(config.poems_file)),
        "review_poems": len(load_json_list(config.poems_review_file)),
        "accepted_quotes": len(load_json_list(config.quotes_file)),
        "review_quotes": len(load_json_list(config.quotes_review_file)),
    }
