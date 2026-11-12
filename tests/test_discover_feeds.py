"""Discover by area (12 November 2026): rows, genres and cards from Reelix's own feeds, with what you already have."""
import unittest
from unittest import mock

from starboard import discover_feeds as df, services

ANSWERS = {
    "/discover/genres/movie": [{"id": 28, "name": "Action"}],
    "/discover/trending-movies": {"results": [
        {"tmdb_id": 1, "title": "Dune", "year": 2021, "poster": "https://image.tmdb.org/t/p/w500/a.jpg", "availability": "available"},
        {"tmdb_id": 2, "title": "Heat", "year": 1995, "poster": "https://evil.example/x.jpg", "availability": "monitored"},
        {"tmdb_id": 3, "title": "Ran", "year": 1985, "availability": "unknown"}, {"title": "No id"}]},
    "/discover/content/album/new-releases": {"results": [{"foreign_id": "rg", "title": "Album", "subtitle": "Artist",
                                                           "subtitle_id": "1c26f82c-b35d-4c8e-a1f4-9c20747495c9"}]},
    "/discover/content/book/trending": {"results": [{"foreign_id": "OL1W", "title": "Book", "subtitle": "Author"}]},
    "/discover/genres/radio": {"rows": [{"id": "bbc-popular", "name": "Popular on BBC Sounds", "provider_name": "BBC"}],
                               "categories": [{"id": "bbc-cat-comedy", "name": "Comedy"}]},
    "/discover/content/radio/bbc-popular": {"results": [{"foreign_id": "bbc:b006qpgr", "title": "The Archers",
                                                         "cover": "https://ichef.bbci.co.uk/images/ic/640x640/p.jpg"}]},
}


def fake(service, path, params=None, **kw):
    return ANSWERS[path]


@mock.patch.object(services, "_api", side_effect=fake)
@mock.patch.object(services, "cached", side_effect=lambda key, secs, fn: fn())
class Feeds(unittest.TestCase):
    def test_films(self, *_):
        r = df.rows({}, "films")
        self.assertEqual(r["genres"], [{"id": "genre/movie/28", "title": "Action"}])
        items = df.row({}, "films", "trending-movies")["items"]
        self.assertEqual([(i["key"], i["state"]) for i in items], [("tmdb:1", "have"), ("tmdb:2", "wanted"), ("tmdb:3", "")])
        self.assertTrue(items[0]["image"].startswith("/api/library/lookup-poster?src="))
        self.assertEqual(items[1]["image"], "")  # a picture from anywhere else is not shown

    def test_other_areas(self, *_):
        self.assertEqual(df.row({}, "music", "new-releases")["items"][0]["key"], "mb:1c26f82c-b35d-4c8e-a1f4-9c20747495c9")
        book = df.row({}, "audiobooks", "trending")["items"][0]
        self.assertEqual((book["key"], book["kind"], book["audiobook"]), ("olw:OL1W", "books", True))
        radio = df.row({}, "radio", "bbc-popular")["items"][0]
        self.assertEqual(radio["key"], "radio:bbc:b006qpgr")
        self.assertTrue(radio["image"])

    def test_only_known_rows(self, *_):
        for bad in ("../../users", "trending-movies?x=1", "genre/movie/99"):
            with self.assertRaises(ValueError):
                df.row({}, "films", bad)
        with self.assertRaises(ValueError):
            df.rows({}, "podcasts")


if __name__ == "__main__":
    unittest.main()
