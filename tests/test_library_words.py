"""The Library's one vocabulary (owner decisions, 26 November 2026): nine words for what you have and what you want."""
import pathlib
import unittest

from starboard import library

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
OLD = ("Not in library", "Episodes not in library", "Tracks not in library", "Not wanted", "Not requested", "Has episodes",
       "Have it", "Below the quality wanted", "Complete")
NEW = {"In library", "Partly in library", "Wanted", "Downloading", "Below quality", "Not followed", "Not added", "Not released",
       "File missing", "Searching"}


class VocabularyTest(unittest.TestCase):
    def test_status_chips_use_only_the_library_words(self):
        self.assertLessEqual({w for w, _ in library.STATUS.values()}, NEW)

    def test_wanted_is_neutral_and_not_followed_is_muted(self):
        self.assertEqual(library.STATUS["wanted"], ("Wanted", "neutral"))
        self.assertEqual(library.STATUS["not_monitored"], ("Not followed", "muted"))

    def test_every_tab_calls_the_wanted_filter_wanted(self):
        for tab in ("films", "tv", "music", "radio", "books", "audiobooks"):
            labels = [label for key, label in library.CHIPS[tab]]
            self.assertIn("Wanted", labels, tab)
            self.assertFalse([x for x in labels if x in OLD], tab)

    def test_the_old_words_are_gone_from_the_pages(self):
        for name in ("library.js", "library-item.js", "library-search.js", "wanted.js", "search.js"):
            text = (WEB / "js" / name).read_text()
            for old in OLD[:-1]:
                self.assertNotIn(f'"{old}"', text, f"{old} in {name}")

    def test_a_collection_adds_the_rest_not_the_missing(self):
        text = (WEB / "js" / "library.js").read_text()
        self.assertIn("Add the rest (", text)
        self.assertNotIn("Add missing", text)
        self.assertNotIn(" missing ${", text)


if __name__ == "__main__":
    unittest.main()
