"""Choose the episode (12 November 2026): guesses for files Reelix refused for their episode number, and the import."""
import unittest
from unittest import mock

from starboard import episode_fix as ef, services

EPS = [{"id": 1, "season": 2, "number": 11, "title": "The Burrito", "have": True},
       {"id": 2, "season": 2, "number": 12, "title": "Somewhere Else", "have": True},
       {"id": 3, "season": 0, "number": 32, "title": "Supermarket Special", "have": False}]


class Guess(unittest.TestCase):
    def test_title_in_the_name_is_sure(self):
        self.assertEqual(ef.guess("The.Good.Place.S02E13.Somewhere.Else.1080p.mkv", EPS), (2, True))
        self.assertEqual(ef.guess("Food.Unwrapped.S12E05.Supermarket.Special.mkv", EPS), (3, True))

    def test_number_past_the_season_end_needs_checking(self):
        self.assertEqual(ef.guess("Show.S02E13.mkv", EPS), (2, False))
        self.assertEqual(ef.guess("Show.S02E11.mkv", EPS), (1, False))
        self.assertEqual(ef.guess("no numbers here.mkv", EPS), (None, False))


class Apply(unittest.TestCase):
    def test_only_known_episodes_are_sent(self):
        preview = [{"path": "/d/a.mkv", "relative_path": "a.mkv", "media": {"kind": "series", "id": 50}, "quality": {"q": 1},
                    "languages": ["English"], "release_group": "X"}]
        episodes = [{"id": 2, "season_number": 2, "episode_number": 12, "title": "Somewhere Else", "has_file": True}]
        calls = []

        def api(service, path, params=None, method="GET", body=None, timeout=None):
            calls.append((method, path, body))
            return preview if path.startswith("/manualimport") and method == "GET" else episodes if "/episodes" in path else {}
        with mock.patch.object(services, "_api", side_effect=api):
            out = ef.apply({}, "dl7", [{"path": "/d/a.mkv", "episode_ids": [2, 999]}, {"path": "/elsewhere.mkv", "episode_ids": [2]}])
            self.assertEqual(out, {"sent": 1})
            sent = [c for c in calls if c[0] == "POST"][0][2]["files"]
            self.assertEqual(sent[0]["episode_ids"], [2])
            self.assertEqual(sent[0]["series_id"], 50)
            with self.assertRaises(ValueError):
                ef.apply({}, "dl7", [{"path": "/d/a.mkv", "episode_ids": [999]}])
            with self.assertRaises(ValueError):
                ef.options({}, "../../x")


if __name__ == "__main__":
    unittest.main()
