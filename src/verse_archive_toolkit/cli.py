from __future__ import annotations

import argparse
import json
from pathlib import Path

from verse_archive_toolkit.builder import BuildHooks, build_selected_sources, collect_output_stats
from verse_archive_toolkit.config import load_dotenv_file, load_zenquotes_api_key
from verse_archive_toolkit.settings import AppSettings, build_runtime_config
from verse_archive_toolkit.settings_store import SettingsStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verse-archive",
        description="Build curated poetry archives, launch desktop tools, and inspect output stats.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Fetch and curate archive data.")
    build_parser.add_argument("--source", choices=("all", "poems", "quotes"), default=None)
    build_parser.add_argument("--output-dir", type=Path, default=None)
    build_parser.add_argument("--poem-target", type=int, default=None)
    build_parser.add_argument("--quote-target", type=int, default=None)
    build_parser.add_argument("--poetry-batch-size", type=int, default=None)
    build_parser.add_argument("--zenquotes-api-key", type=str, default="")
    build_parser.add_argument("--zenquotes-interval", type=float, default=None)
    build_parser.add_argument("--save-every", type=int, default=None)
    build_parser.add_argument("--request-timeout", type=int, default=None)
    build_parser.add_argument("--max-retries", type=int, default=None)

    stats_parser = subparsers.add_parser("stats", help="Inspect the current output directory.")
    stats_parser.add_argument("--output-dir", type=Path, default=None)

    subparsers.add_parser("gui", help="Launch the main desktop build GUI.")
    subparsers.add_parser("translator", help="Launch the translation assistant GUI.")
    subparsers.add_parser("settings-path", help="Print the local settings file path.")

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
        output_dir = args.output_dir if args.output_dir is not None else Path(settings.build.output_dir)
        runtime_config = build_runtime_config(settings.build, settings.filters, settings.zenquotes_api_key)
        runtime_config.output_dir = output_dir
        print(json.dumps(collect_output_stats(runtime_config), indent=2))
        return 0

    if args.command == "settings-path":
        print(store.path)
        return 0

    if args.command == "gui":
        from verse_archive_toolkit.gui.builder_app import main as gui_main

        return gui_main()

    if args.command == "translator":
        from verse_archive_toolkit.gui.translator_app import main as translator_main

        return translator_main()

    parser.error(f"Unsupported command: {args.command}")
    return 2
