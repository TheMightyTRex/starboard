"""Wanted: Missing and Below the quality wanted, from Reelix (DASH-207)."""
import unittest
from unittest import mock

from starboard import wanted

REELIX = [{"id": "rx", "url": "http://r/api/v1", "api_key": "k", "name": "Reelix"}]


class Wanted(unittest.TestCase):
    def test_rows_link_to_the_library(self):
        page = {"items": [{"kind": "episode", "id": 41, "series_id": 3, "title": "Ghosts", "season_number": 6, "episode_number": 1,
                           "episode_title": "Pilot", "date": "2026-11-01"}], "total": 1, "page": 1}
        with mock.patch("starboard.services.reelix_native", return_value=REELIX), mock.patch("starboard.services._api", return_value=page) as api:
            out = wanted.listing([], "missing", "episode")
        self.assertEqual(out["items"][0]["detail"], "S06E01 · Pilot")
        self.assertEqual(out["items"][0]["href"], "/library-tv-show.html?id=3")
        self.assertEqual(api.call_args[0][1], "/wanted/missing")

    def test_search_the_ticked_or_all(self):
        with mock.patch("starboard.services.reelix_native", return_value=REELIX), mock.patch("starboard.services._api") as api:
            wanted.search([], "cutoff", "movie", [3, "4", "x"])
            self.assertEqual(api.call_args.kwargs["body"], {"kind": "movie", "ids": [3, 4]})
            wanted.search([], "cutoff", "episode", [])
            self.assertEqual(api.call_args.kwargs["body"], {"kind": "cutoff", "ids": [], "media": "episode"})

    def test_without_reelix_or_with_a_wrong_list(self):
        with mock.patch("starboard.services.reelix_native", return_value=[]):
            with self.assertRaisesRegex(ValueError, "Add Reelix"):
                wanted.listing([], "missing", "movie")
        with self.assertRaises(ValueError):
            wanted.listing([], "everything", "movie")


if __name__ == "__main__":
    unittest.main()


class WantedEveryKind(unittest.TestCase):
    """12 November 2026: albums, books and audiobooks have Missing and Below the quality wanted too."""
    def test_books_and_albums(self):
        from unittest import mock
        from starboard import services, wanted
        calls = []

        def api(service, path, params=None, method="GET", body=None, timeout=None):
            calls.append((method, path, params, body))
            if path == "/books/wanted":
                return {"items": [{"id": 7, "title": "Brave New World", "author_name": "Aldous Huxley", "release_date": "1932-01-01"}], "total": 1}
            if path == "/albums/wanted":
                return {"items": [{"id": 9, "title": "An Album", "artist_name": "A Band", "album_type": "album"}], "total": 1}
            return {}
        svc = [{"id": "reelix", "type": "link"}]
        with mock.patch.object(services, "reelix_native", return_value=svc), mock.patch.object(services, "_api", side_effect=api):
            b = wanted.listing(svc, "cutoff", "audiobook")
            self.assertEqual((b["items"][0]["title"], b["items"][0]["year"], b["items"][0]["detail"]), ("Brave New World", "1932", "Aldous Huxley"))
            self.assertEqual(calls[-1][2]["format"], "audiobook")
            self.assertEqual(calls[-1][2]["kind"], "cutoff")
            a = wanted.listing(svc, "missing", "album")
            self.assertEqual(a["items"][0]["detail"], "A Band · album")
            self.assertIn("2 audiobooks", wanted.search(svc, "missing", "audiobook", [1, 2]))
            self.assertEqual(calls[-1][1:], ("/books/search", None, {"kind": "item", "ids": [1, 2], "format": "audiobook"}))
            wanted.search(svc, "cutoff", "album", [])
            self.assertEqual(calls[-1][1:], ("/music/search", None, {"kind": "cutoff", "ids": []}))
