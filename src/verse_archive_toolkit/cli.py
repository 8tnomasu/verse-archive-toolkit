from __future__ import annotations

import argparse
import json
from pathlib import Path

from verse_archive_toolkit.app_paths import (
    find_latest_log_path,
    get_logs_directory,
    resolve_output_directory,
)
from verse_archive_toolkit.builder import BuildHooks, build_selected_sources, collect_output_stats
from verse_archive_toolkit.config import load_dotenv_file, load_zenquotes_api_key
from verse_archive_toolkit.settings import AppSettings, build_runtime_config
from verse_archive_toolkit.settings_store import SettingsStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verse-archive",
        description="VerseArchiveToolkit CLI，用於操作 VerseArchiveCurator 建庫流程與共用路徑診斷。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="執行 VerseArchiveCurator 的 archive 建庫流程。")
    build_parser.add_argument(
        "--source",
        choices=("all", "poems", "quotes"),
        default=None,
        help="建庫來源：all=英文詩與哲思語錄，poems=只抓英文詩，quotes=只抓哲思語錄。",
    )
    build_parser.add_argument("--output-dir", type=Path, default=None, help="指定 archive JSON 輸出目錄。")
    build_parser.add_argument("--poem-target", type=int, default=None, help="英文詩目標筆數。")
    build_parser.add_argument("--quote-target", type=int, default=None, help="哲思語錄目標筆數。")
    build_parser.add_argument(
        "--poetry-batch-size",
        type=int,
        default=None,
        help="每批向 PoetryDB 抓取的筆數。",
    )
    build_parser.add_argument(
        "--zenquotes-api-key",
        type=str,
        default="",
        help="ZenQuotes API key；若未提供，會優先使用本機設定或環境設定。",
    )
    build_parser.add_argument(
        "--zenquotes-interval",
        type=float,
        default=None,
        help="ZenQuotes 請求間隔秒數。",
    )
    build_parser.add_argument("--save-every", type=int, default=None, help="每處理幾筆資料就寫回一次。")
    build_parser.add_argument("--request-timeout", type=int, default=None, help="HTTP timeout 秒數。")
    build_parser.add_argument("--max-retries", type=int, default=None, help="HTTP 最大重試次數。")

    stats_parser = subparsers.add_parser("stats", help="輸出目前 archive JSON 的統計資訊。")
    stats_parser.add_argument("--output-dir", type=Path, default=None, help="改用指定輸出目錄讀取統計。")

    subparsers.add_parser("gui", help="啟動 VerseArchiveCurator 桌面 GUI。")
    subparsers.add_parser("translator", help="啟動 VerseArchiveTranslator Desktop GUI。")
    subparsers.add_parser("settings-path", help="輸出本機 settings.json 路徑。")
    subparsers.add_parser("logs-path", help="輸出桌面應用程式 log 資料夾路徑。")
    paths_parser = subparsers.add_parser("paths", help="一次輸出 settings、logs、output 等診斷路徑。")
    paths_parser.add_argument("--output-dir", type=Path, default=None, help="指定要解析的 output 目錄。")

    return parser


def _print_progress(message: str) -> None:
    print(message)


def _load_app_settings() -> tuple[SettingsStore, AppSettings]:
    store = SettingsStore()
    return store, store.load()


def _apply_build_overrides(settings: AppSettings, args: argparse.Namespace) -> AppSettings:
    updated = settings.clone()

    if args.source is not None:
        updated.build.source = args.source
    if args.output_dir is not None:
        updated.build.output_dir = str(args.output_dir)
    if args.poem_target is not None:
        updated.build.poem_target = args.poem_target
    if args.quote_target is not None:
        updated.build.quote_target = args.quote_target
    if args.poetry_batch_size is not None:
        updated.build.poetry_batch_size = args.poetry_batch_size
    if args.zenquotes_interval is not None:
        updated.build.zenquotes_request_interval = args.zenquotes_interval
    if args.save_every is not None:
        updated.build.save_every = args.save_every
    if args.request_timeout is not None:
        updated.build.request_timeout = args.request_timeout
    if args.max_retries is not None:
        updated.build.max_retries = args.max_retries

    explicit_key = load_zenquotes_api_key(args.zenquotes_api_key)
    if explicit_key:
        updated.zenquotes_api_key = explicit_key

    return updated


def _collect_path_payload(
    store: SettingsStore,
    settings: AppSettings,
    output_dir: Path | None = None,
) -> dict[str, str]:
    resolved_output = resolve_output_directory(
        output_dir if output_dir is not None else settings.build.output_dir
    )
    latest_log = find_latest_log_path("builder-gui")
    return {
        "settings_path": str(store.path.resolve()),
        "logs_dir": str(get_logs_directory().resolve()),
        "output_dir": str(resolved_output),
        "latest_builder_log": str(latest_log.resolve()) if latest_log is not None else "",
    }


def main(argv: list[str] | None = None) -> int:
    load_dotenv_file()
    parser = build_parser()
    args = parser.parse_args(argv)
    store, settings = _load_app_settings()

    if args.command == "build":
        active_settings = _apply_build_overrides(settings, args)
        runtime_config = build_runtime_config(
            active_settings.build,
            active_settings.filters,
            active_settings.zenquotes_api_key,
        )
        results = build_selected_sources(
            config=runtime_config,
            source=active_settings.build.source,
            hooks=BuildHooks(log=_print_progress),
        )
        print(
            json.dumps(
                {
                    name: {
                        "accepted_count": result.accepted_count,
                        "review_count": result.review_count,
                        "rejected_count": result.rejected_count,
                        "skipped_count": result.skipped_count,
                        "processed_count": result.processed_count,
                        "accepted_path": str(result.accepted_path),
                        "review_path": str(result.review_path),
                        "reason_counts": result.reason_counts,
                        "cancelled": result.cancelled,
                    }
                    for name, result in results.items()
                },
                indent=2,
            )
        )
        return 0

    if args.command == "stats":
        output_dir = resolve_output_directory(
            args.output_dir if args.output_dir is not None else settings.build.output_dir
        )
        runtime_config = build_runtime_config(
            settings.build,
            settings.filters,
            settings.zenquotes_api_key,
        )
        runtime_config.output_dir = output_dir
        print(json.dumps(collect_output_stats(runtime_config), indent=2))
        return 0

    if args.command == "settings-path":
        print(store.path)
        return 0

    if args.command == "logs-path":
        print(get_logs_directory())
        return 0

    if args.command == "paths":
        print(
            json.dumps(
                _collect_path_payload(store, settings, args.output_dir),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "gui":
        from verse_archive_toolkit.builder_gui_entry import main as gui_main

        return gui_main()

    if args.command == "translator":
        from verse_archive_toolkit.translator_gui_entry import main as translator_main

        return translator_main()

    parser.error(f"未知命令：{args.command}")
    return 2
