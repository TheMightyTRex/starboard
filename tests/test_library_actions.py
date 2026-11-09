"""Get it, follow, stop following and delete from the Library (DASH-276, DASH-206)."""
import unittest
from unittest import mock

from starboard import library


class Actions(unittest.TestCase):
    def run_act(self, *args, **kw):
        calls = []

        def fake(service, path, params=None, method="GET", body=None, timeout=None):
            calls.append((method, path, body, params))
            return [{"season_number": 1}, {"season_number": 2}] if path.endswith("/episodes") else {}
        with mock.patch("starboard.services._api", side_effect=fake):
            said = library.act({"url": "x"}, *args, **kw)
        return said, [(m, p, b) for m, p, b, _ in calls], calls

    def test_a_film_is_followed_and_searched(self):
        said, calls, _ = self.run_act("films", 7, "get")
        self.assertEqual(calls, [("PUT", "/movies/7", {"monitored": True}), ("POST", "/search", {"kind": "movie", "ids": [7]})])
        self.assertIn("searching", said)

    def test_an_episode_and_a_season(self):
        _, calls, _ = self.run_act("tv", 3, "get", "episode", episode=41)
        self.assertEqual(calls, [("PUT", "/episodes/monitor", {"episode_ids": [41], "monitored": True}),
                                 ("POST", "/search", {"kind": "episode", "ids": [41]})])
        _, calls, _ = self.run_act("tv", 3, "get", "season", season=2)
        self.assertEqual(calls[-1], ("POST", "/search", {"kind": "season", "ids": [3], "season": 2}))

    def test_stop_following_a_series_stops_every_season(self):
        _, calls, _ = self.run_act("tv", 3, "unfollow")
        self.assertEqual([c for c in calls if c[1] == "/seasons/monitor"],
                         [("PUT", "/seasons/monitor", {"series_id": 3, "season_number": n, "monitored": False}) for n in (1, 2)])

    def test_delete_keeps_files_unless_asked(self):
        said, _, raw = self.run_act("films", 7, "delete")
        self.assertEqual(raw[0][3], {"delete_files": "false"})
        self.assertIn("files stay", said)

    def test_unknown_actions_are_refused(self):
        with self.assertRaises(ValueError):
            self.run_act("films", 7, "launch")


if __name__ == "__main__":
    unittest.main()


class RadioFollow(unittest.TestCase):
    """DASH-158: how Reelix follows a radio show, from Starboard."""

    def test_new_episodes_from_now_on(self):
        calls = []
        with mock.patch("starboard.services._api", side_effect=lambda s, path, params=None, method="GET", body=None, timeout=None: calls.append((method, path, body))):
            said = library.act({}, "radio", 5, "follow", "from_now_on")
            library.act({}, "radio", 5, "unfollow", "none")
        self.assertEqual(calls, [("PUT", "/radio/shows/5", {"follow": "from_now_on", "monitored": True}),
                                 ("PUT", "/radio/shows/5", {"follow": "none", "monitored": False})])
        self.assertIn("new episodes", said)
