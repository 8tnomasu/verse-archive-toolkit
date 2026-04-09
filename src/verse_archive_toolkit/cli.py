from __future__ import annotations

import argparse
import json
from pathlib import Path

from verse_archive_toolkit.builder import build_selected_sources, collect_output_stats
from verse_archive_toolkit.config import ToolkitConfig, load_dotenv_file, load_zenquotes_api_key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verse-archive",
        description="Build curated poetry and philosophy quote archives.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Fetch and curate archive data.")
    build_parser.add_argument(
        "--source",
        choices=("all", "poems", "quotes"),
        default="all",
        help="Which source set to build.",
    )
    build_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for generated JSON files.",
    )
    build_parser.add_argument(
        "--poem-target",
        type=int,
        default=500,
        help="Target number of accepted poem records.",
    )
    build_parser.add_argument(
        "--quote-target",
        type=int,
        default=500,
        help="Target number of accepted quote records.",
    )
    build_parser.add_argument(
        "--poetry-batch-size",
        type=int,
        default=20,
        help="PoetryDB random batch size per request.",
    )
    build_parser.add_argument(
        "--zenquotes-api-key",
        type=str,
        default="",
        help="ZenQuotes API key. Falls back to ZENQUOTES_API_KEY.",
    )
    build_parser.add_argument(
        "--zenquotes-interval",
        type=float,
        default=1.5,
        help="Delay between ZenQuotes author requests in seconds.",
    )
    build_parser.add_argument(
        "--save-every",
        type=int,
        default=50,
        help="Persist checkpoints after this many accepted or review additions.",
    )
    build_parser.add_argument(
        "--request-timeout",
        type=int,
        default=30,
        help="HTTP timeout per request in seconds.",
    )
    build_parser.add_argument(
        "--max-retries",
        type=int,
        default=6,
        help="Maximum retry count per HTTP request.",
    )

    stats_parser = subparsers.add_parser("stats", help="Inspect the current output directory.")
    stats_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory containing generated JSON files.",
    )

    return parser


def _print_progress(message: str) -> None:
    print(message)


def main(argv: list[str] | None = None) -> int:
    load_dotenv_file()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "build":
        config = ToolkitConfig(
            output_dir=args.output_dir,
            poem_target=args.poem_target,
            quote_target=args.quote_target,
            poetry_batch_size=args.poetry_batch_size,
            zenquotes_request_interval=args.zenquotes_interval,
            save_every=args.save_every,
            request_timeout=args.request_timeout,
            max_retries=args.max_retries,
            zenquotes_api_key=load_zenquotes_api_key(args.zenquotes_api_key),
        )
        results = build_selected_sources(config=config, source=args.source, progress=_print_progress)
        print(
            json.dumps(
                {
                    name: {
                        "accepted_count": result.accepted_count,
                        "review_count": result.review_count,
                        "accepted_path": str(result.accepted_path),
                        "review_path": str(result.review_path),
                    }
                    for name, result in results.items()
                },
                indent=2,
            )
        )
        return 0

    if args.command == "stats":
        config = ToolkitConfig(output_dir=args.output_dir)
        print(json.dumps(collect_output_stats(config), indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2
