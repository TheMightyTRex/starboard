"""Discover by area (12 November 2026): rows, genres and cards from Reelix's own feeds, with what you already have."""
import unittest
from unittest import mock

from starboard import discover_feeds as df, services

ANSWERS = {
    "/discover/genres/movie": [{"id": 28, "name": "Action"}],
    "/discover/genres/tv": [{"id": 10765, "name": "Sci-Fi & Fantasy"}, {"id": 35, "name": "Comedy"}, {"id": "x", "name": "Bad"},
                            {"id": 10770, "name": "TV Movie"}, {"id": 99}],
    "/discover/genre/tv/35": {"results": [{"tmdb_id": 9, "title": "A Comedy", "year": 2020}]},
    "/discover/trending-movies": {"results": [
        {"tmdb_id": 1, "title": "Dune", "year": 2021, "poster": "https://image.tmdb.org/t/p/w500/a.jpg", "availability": "available"},
        {"tmdb_id": 2, "title": "Heat", "year": 1995, "poster": "https://evil.example/x.jpg", "availability": "monitored"},
        {"tmdb_id": 3, "title": "Ran", "year": 1985, "availability": "unknown"}, {"title": "No id"}]},
    "/discover/content/album/new-releases": {"results": [{"foreign_id": "rg", "title": "Album", "subtitle": "Artist",
                                                           "subtitle_id": "1c26f82c-b35d-4c8e-a1f4-9c20747495c9"}]},
    "/discover/content/book/trending": {"results": [{"foreign_id": "OL1W", "title": "Book", "subtitle": "Author"}]},
    "/discover/genres/radio": {"rows": [{"id": "bbc-popular", "name": "Popular on BBC Sounds", "provider_name": "BBC"}],
                               "categories": [{"id": "all-genre-comedy", "name": "Comedy", "provider_name": "Every source", "group": "Genres"},
                                              {"id": "bbc-network-bbc_radio_kent", "name": "BBC Radio Kent", "provider_name": "BBC", "group": "BBC stations: local"},
                                              {"id": "bbc-category-comedy", "name": "All comedy", "provider_name": "BBC", "group": "Comedy"}]},
    "/radio/search": [{"provider": "bbc", "external_id": "b1", "title": "In Our Time", "broadcaster": "BBC"},
                      {"provider": "apple", "external_id": "2", "title": "A Podcast", "feed_url": "https://f.example/x.xml"},
                      {"provider": "apple", "title": "No id"}],
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

    def test_genre_rows(self, *_):
        """DASH-395: every TMDB genre is also a row, marked so it starts hidden, in sentence case and A to Z."""
        r = df.rows({}, "tv")
        self.assertEqual([(g["id"], g["title"]) for g in r["genres"]],
                         [("genre/tv/35", "Comedy"), ("genre/tv/10765", "Sci-fi and fantasy"), ("genre/tv/10770", "TV movie")])
        self.assertEqual([x["id"] for x in r["rows"] if x.get("genre")], [g["id"] for g in r["genres"]])
        self.assertFalse(any(x.get("genre") for x in r["rows"][:5]))
        self.assertEqual(df.row({}, "tv", "genre/tv/35")["items"][0]["key"], "tmdb:9")
        self.assertEqual(df.tidy("Science Fiction"), "Science fiction")
        self.assertEqual(df.tidy("War & Politics"), "War and politics")

    def test_other_areas(self, *_):
        self.assertEqual(df.row({}, "music", "new-releases")["items"][0]["key"], "mb:1c26f82c-b35d-4c8e-a1f4-9c20747495c9")
        book = df.row({}, "audiobooks", "trending")["items"][0]
        self.assertEqual((book["key"], book["kind"], book["audiobook"]), ("olw:OL1W", "books", True))
        radio = df.row({}, "radio", "bbc-popular")["items"][0]
        self.assertEqual(radio["key"], "radio:bbc:b006qpgr")
        self.assertTrue(radio["image"])

    def test_books_offer_every_subject_reelix_allows(self, *_):
        """DASH-396: Reelix allows only its own nine Open Library subjects (BOOK_DISCOVER_ROWS, checked against
        content_discovery.rs), all standard rows, so books and audiobooks have no genre rows; music has no genre source."""
        for tab in ("books", "audiobooks"):
            r = df.rows({}, tab)
            subjects = [x["id"] for x in r["rows"] if x["id"].startswith("subject-")]
            self.assertEqual(len(subjects), 9, tab)
            self.assertFalse(any(x.get("genre") for x in r["rows"]), tab)
            self.assertEqual(df.arrange(r["rows"], None), r["rows"], f"{tab}: every standard row shows")
        self.assertEqual(df.rows({}, "music")["genres"], [])

    def test_only_known_rows(self, *_):
        for bad in ("../../users", "trending-movies?x=1", "genre/movie/99"):
            with self.assertRaises(ValueError):
                df.row({}, "films", bad)
        with self.assertRaises(ValueError):
            df.rows({}, "podcasts")


if __name__ == "__main__":
    unittest.main()


@mock.patch.object(services, "_api", side_effect=fake)
@mock.patch.object(services, "cached", side_effect=lambda key, secs, fn: fn())
class Radio(unittest.TestCase):
    """DASH-339: shared genres as chips, BBC stations in their own picker, each source's categories under More."""

    def test_rows_split(self, *_):
        r = df.rows({}, "radio")
        self.assertEqual([g["id"] for g in r["genres"]], ["all-genre-comedy"])
        self.assertEqual([s["id"] for s in r["stations"]], ["bbc-network-bbc_radio_kent"])
        self.assertEqual([m["id"] for m in r["more"]], ["bbc-category-comedy"])
        # Every one of them can be opened as a row.
        self.assertEqual(df.row.__name__, "row")

    def test_shared_genres_are_rows_too(self, *_):
        """DASH-396: each shared genre is a row as well, marked as a genre so it starts unticked; a source's own
        categories and the stations are not rows."""
        r = df.rows({}, "radio")
        self.assertEqual([(x["id"], x.get("genre", False)) for x in r["rows"]], [("bbc-popular", False), ("all-genre-comedy", True)])
        self.assertEqual(df.arrange(r["rows"], None), [r["rows"][0]], "a genre row is hidden until ticked")
        with mock.patch.dict(ANSWERS, {"/discover/content/radio/all-genre-comedy": {"results": [{"foreign_id": "bbc:x1", "title": "Funny Show"}]}}):
            self.assertEqual([c["key"] for c in df.row({}, "radio", "all-genre-comedy")["items"]], ["radio:bbc:x1"])

    def test_search_cards_and_feeds_only(self, *_):
        items = df.radio_search({}, "time")["items"]
        self.assertEqual([i["key"] for i in items], ["radio:bbc:b1", "radio:apple:2"])
        self.assertTrue(items[0]["detail"].startswith("BBC"))
        self.assertEqual([i["key"] for i in df.radio_search({}, "time", feeds_only=True)["items"]], ["radio:apple:2"])
        with self.assertRaises(ValueError):
            df.radio_search({}, "a")

    def test_from_stations_is_asked_of_reelix(self, *_):
        with mock.patch.object(services, "_api", return_value=[]) as call:
            df.radio_search({}, "time", from_stations=True)
        self.assertEqual(call.call_args[0][2], {"q": "time", "from_stations": "true"})

    def test_older_reelix_says_it_cannot_filter(self, *_):
        with mock.patch.object(services, "_api", return_value=[{"provider": "apple", "external_id": "1", "title": "A show"}]):
            got = df.radio_search({}, "time", from_stations=True)
        self.assertEqual(got["items"], [])
        self.assertIn("Update Reelix", got["note"])

