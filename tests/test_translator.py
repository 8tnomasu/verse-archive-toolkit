from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from verse_archive_toolkit.storage import write_json
from verse_archive_toolkit.translator import TranslationRepository, translation_state


SAMPLE_RECORDS = [
    {
        "type": "english_poem",
        "title": {"en": "Night River", "cn": ""},
        "author": {"en": "Jane Doe", "cn": ""},
        "content": {
            "lines": ["One line", "Two line", "Three line", "Four line"],
            "en": "One line\nTwo line\nThree line\nFour line",
            "cn": "",
        },
    },
    {
        "type": "philosophy",
        "title": {"en": "", "cn": ""},
        "author": {"en": "Laozi", "cn": "老子"},
        "content": {"lines": ["Silence teaches."], "en": "Silence teaches.", "cn": ""},
    },
]


class TranslationRepositoryTests(unittest.TestCase):
    def test_search_stats_and_save(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "english_poems.json"
            write_json(file_path, SAMPLE_RECORDS)

            repository = TranslationRepository(Path(tmp_dir))
            repository.load()

            stats = repository.stats()
            self.assertEqual(stats["total"], 2)
            self.assertEqual(stats["partial"], 1)
            self.assertEqual(stats["untranslated"], 1)

            results = repository.search("jane")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].author_en, "Jane Doe")

            updated = repository.save_translation(
                results[0],
                title_cn="夜河",
                author_cn="珍．杜",
                content_cn="一行\n二行\n三行\n四行",
            )

            self.assertEqual(translation_state(updated.record), "translated")
            self.assertEqual(updated.record["content"]["lines"][0], "One line")


if __name__ == "__main__":
    unittest.main()
