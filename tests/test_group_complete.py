"""Complete collections and series (12 November 2026): films from Reelix's collections, audiobook series from
Audiobookshelf with Audible's missing books, and Add missing."""
import unittest
from unittest import mock

from starboard import group_complete as gc, services

COLS = [{"id": 1, "title": "Harbour Films", "quality_profile_id": 4, "root_folder_id": 2, "movies": [
    {"tmdb_id": 10, "title": "Harbour", "year": 2011, "movie_id": 5, "has_file": True},
    {"tmdb_id": 11, "title": "Harbour II", "year": 2014, "movie_id": 6, "has_file": False},
    {"tmdb_id": 12, "title": "Harbour III", "year": 2019, "movie_id": None, "has_file": False}]}]
SERIES = {"rivers": {"name": "Rivers", "books": [{"title": "One", "author": "A", "seq": "1", "key": "one|a"},
                                                 {"title": "Two", "author": "A", "seq": "2", "key": "two|a"}]}}
AUDIBLE = [{"title": "One", "seq": "1", "asin": "B1", "author": "A"}, {"title": "Two", "seq": "2", "asin": "B2", "author": "A"},
           {"title": "Three", "seq": "3", "asin": "B3", "author": "A"}]


@mock.patch.object(services, "cached", side_effect=lambda key, secs, fn: fn())
class Complete(unittest.TestCase):
    @mock.patch.object(services, "_api", return_value=COLS)
    def test_films(self, *_):
        d = gc.detail({}, [], "films", "harbour films")
        self.assertEqual((d["total"], d["have"], d["missing"]), (3, 1, 1))  # Harbour II is wanted, not missing
        with mock.patch("starboard.library.add") as add:
            out = gc.add_missing("/tmp", {}, [], "films", "Harbour Films")
        self.assertEqual(out["added"], ["Harbour III"])
        self.assertEqual(add.call_args[0][2:4], ("films", "tmdb:12"))
        self.assertEqual(add.call_args[0][4]["profile_id"], 4)

    @mock.patch.object(gc, "abs_series", return_value=SERIES)
    @mock.patch.object(gc, "audible_series", return_value=AUDIBLE)
    def test_audiobooks(self, *_):
        d = gc.detail({}, [], "audiobooks", "Rivers")
        self.assertEqual((d["total"], d["have"], d["missing"]), (3, 2, 1))
        self.assertEqual([i["title"] for i in d["items"]], ["One", "Two", "Three"])
        with mock.patch.object(services, "_api", return_value=[{"openlibrary_work_id": "OL9W", "title": "Three"}]), \
                mock.patch("starboard.library.add") as add:
            out = gc.add_missing("/tmp", {}, [], "audiobooks", "Rivers")
        self.assertEqual(out["added"], ["Three"])
        self.assertEqual(add.call_args[0][3], "olw:OL9W")
        self.assertEqual(add.call_args[0][4]["formats"], ["audiobook"])

    @mock.patch.object(gc, "abs_series", return_value=SERIES)
    def test_tagging(self, *_):
        idx = {"items": [{"t": "Two", "au": "A", "g": []}, {"t": "Other", "au": "B"}]}
        out = gc.tag_audiobooks(idx, [])
        self.assertEqual(out["items"][0]["g"], ["Rivers"])
        self.assertNotIn("g", out["items"][1])

    def test_unknown(self, *_):
        with mock.patch.object(services, "_api", return_value=[]):
            self.assertIsNone(gc.detail({}, [], "films", "Nope"))
            with self.assertRaises(LookupError):
                gc.add_missing("/tmp", {}, [], "films", "Nope")


if __name__ == "__main__":
    unittest.main()
