from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.filters import evaluate_poem_filters, evaluate_quote_filters
from verse_archive_toolkit.records import build_poem_record
from verse_archive_toolkit.settings import FilterSettings


class FilterTests(unittest.TestCase):
    def test_poem_filter_accepts_balanced_poem(self) -> None:
        poem = build_poem_record(
            title="Evening Bells",
            author="Jane Doe",
            lines=[
                "The bell remembers every passing cloud.",
                "Its bronze throat gathers weather into song.",
                "Night leans close and listens from the field.",
                "I answer with the patience of the dark.",
            ],
        )

        decision = evaluate_poem_filters(poem, FilterSettings().poetry)
        self.assertFalse(decision.matched)
        self.assertEqual(decision.action, "accept")

    def test_poem_filter_rejects_repetition_with_reason(self) -> None:
        poem = build_poem_record(
            title="Echo",
            author="Jane Doe",
            lines=[
                "The river keeps repeating the same cold word.",
                "The river keeps repeating the same cold word.",
                "The river keeps repeating the same cold word.",
                "The river keeps repeating the same cold word.",
            ],
        )

        decision = evaluate_poem_filters(poem, FilterSettings().poetry)
        self.assertTrue(decision.matched)
        self.assertEqual(decision.reason, "poetry.unique_line_ratio.below_min")

    def test_quote_filter_rejects_generic_motivation(self) -> None:
        quote = "Believe in yourself and stay positive because you can do anything."
        decision = evaluate_quote_filters(quote, FilterSettings().quotes)
        self.assertTrue(decision.matched)
        self.assertEqual(decision.reason, "quotes.phrase_blacklist.match")

    def test_quote_filter_accepts_philosophical_text(self) -> None:
        quote = "Truth arrives quietly when the mind stops bargaining with fear."
        decision = evaluate_quote_filters(quote, FilterSettings().quotes)
        self.assertFalse(decision.matched)
        self.assertEqual(decision.action, "accept")

    def test_zero_range_values_disable_length_limits(self) -> None:
        poem = build_poem_record(
            title="Short",
            author="Jane Doe",
            lines=["A long enough line.", "Another long enough line.", "Third one is here.", "Fourth arrives too."],
        )
        settings = FilterSettings()
        settings.poetry.text_length.min_value = 0
        settings.poetry.text_length.max_value = 0
        settings.poetry.line_count.min_value = 0
        settings.poetry.line_count.max_value = 0
        settings.poetry.average_line_length.value = 0
        settings.poetry.unique_line_ratio.value = 0
        decision = evaluate_poem_filters(poem, settings.poetry)
        self.assertFalse(decision.matched)


if __name__ == "__main__":
    unittest.main()
