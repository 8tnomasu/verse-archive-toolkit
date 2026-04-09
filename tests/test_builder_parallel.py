from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path
from typing import Callable
from unittest.mock import patch
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.builder import BuildResult, build_selected_sources
from verse_archive_toolkit.settings import ToolkitConfig


class ParallelBuilderTests(unittest.TestCase):
    def test_build_selected_sources_runs_poems_and_quotes_in_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            config = ToolkitConfig(output_dir=output_dir, zenquotes_api_key="demo-key")
            barrier = threading.Barrier(2, timeout=1.0)
            barrier_results: list[tuple[str, str]] = []
            lock = threading.Lock()

            def make_stub(source: str) -> Callable[..., BuildResult]:
                def _stub(*_args, **_kwargs) -> BuildResult:
                    try:
                        barrier.wait()
                        status = "passed"
                    except threading.BrokenBarrierError:
                        status = "broken"
                    with lock:
                        barrier_results.append((source, status))
                    return BuildResult(
                        source=source,
                        accepted_count=1,
                        review_count=0,
                        rejected_count=0,
                        skipped_count=0,
                        processed_count=1,
                        reason_counts={},
                        accepted_path=output_dir / f"{source}.json",
                        review_path=output_dir / f"{source}_review.json",
                        cancelled=False,
                    )

                return _stub

            with (
                patch("verse_archive_toolkit.builder.build_poem_archive", new=make_stub("poems")),
                patch("verse_archive_toolkit.builder.build_quote_archive", new=make_stub("quotes")),
            ):
                results = build_selected_sources(config=config, source="all")

        self.assertEqual(set(results), {"poems", "quotes"})
        self.assertEqual(sorted(barrier_results), [("poems", "passed"), ("quotes", "passed")])


if __name__ == "__main__":
    unittest.main()
