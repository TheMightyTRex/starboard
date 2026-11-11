"""Discover, On demand history (DASH-324): the plug-in's history with library state, Add to wanted and filters."""
import unittest
from unittest import mock

from starboard import ondemand_history as oh, services


class OnDemandHistoryTest(unittest.TestCase):
    def setUp(self):
        services._cache.clear()
        history = {"items": [{"id": "tt1", "type": "movie", "name": "A Film", "year": "2020", "poster": "https://x/p.jpg", "last_played": "2026-11-11 10:00"},
                             {"id": "tt2", "type": "series", "name": "A Series", "last_episode": "S01E02", "poster": "javascript:alert(1)"}]}
        self.p = mock.patch.object(oh, "_plugin", return_value=history)
        self.p.start()
        self.addCleanup(self.p.stop)

    def lookup(self, reelix, path, *a, **k):
        return [{"tmdb_id": 10, "in_library": True, "library_id": 4}] if "movies" in path else [{"tmdb_id": 20, "in_library": False}]

    def test_listing_marks_what_you_have_and_filters(self):
        with mock.patch.object(services, "_api", side_effect=self.lookup):
            out = oh.listing("/tmp", {"url": "x"})
            self.assertEqual([(i["id"], i["in_library"], i["key"]) for i in out["items"]], [("tt1", True, "tmdb:10"), ("tt2", False, "tmdb:20")])
            self.assertEqual(out["items"][0]["href"], "/library-film.html?id=4")
            self.assertEqual(out["items"][1]["poster"], "")  # only https pictures
            self.assertEqual([i["id"] for i in oh.listing("/tmp", {"url": "x"}, "series")["items"]], ["tt2"])

    def test_want_adds_and_searches_or_says_it_is_there(self):
        from starboard import library
        with mock.patch.object(services, "_api", side_effect=self.lookup), \
                mock.patch.object(library, "add", return_value={"title": "A Series"}) as add:
            self.assertEqual(oh.want("/tmp", {"url": "x"}, "movie", "tt1")["said"], "It is already in your library")
            self.assertIn("Added A Series", oh.want("/tmp", {"url": "x"}, "series", "tt2")["said"])
            add.assert_called_once_with("/tmp", {"url": "x"}, "tv", "tmdb:20", {"search": True})
        with self.assertRaises(ValueError):
            oh.want("/tmp", {"url": "x"}, "music", "tt2")


if __name__ == "__main__":
    unittest.main()
