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
