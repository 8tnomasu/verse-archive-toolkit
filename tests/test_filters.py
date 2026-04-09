from __future__ import annotations

import unittest
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.filters import get_poem_review_reason, get_quote_review_reason
from verse_archive_toolkit.records import build_poem_record


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

        self.assertIsNone(get_poem_review_reason(poem))

    def test_poem_filter_rejects_repetition(self) -> None:
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

        self.assertEqual(get_poem_review_reason(poem), "too_repetitive")

    def test_quote_filter_rejects_generic_motivation(self) -> None:
        quote = "Believe in yourself and stay positive because you can do anything."
        self.assertEqual(
            get_quote_review_reason(quote),
            "matched_phrase:believe in yourself",
        )

    def test_quote_filter_accepts_philosophical_text(self) -> None:
        quote = "Truth arrives quietly when the mind stops bargaining with fear."
        self.assertIsNone(get_quote_review_reason(quote))


if __name__ == "__main__":
    unittest.main()
