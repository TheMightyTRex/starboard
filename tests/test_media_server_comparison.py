"""The measured comparison of Jellyfin, Plex and Emby (DASH-580): a small file read when asked, never measured by Starboard."""
import json
import os
import unittest
from unittest import mock

from starboard import mediaserver

FILE = os.path.join(os.path.dirname(mediaserver.__file__), "media_server_comparison.json")


class Comparison(unittest.TestCase):
    def test_the_file_holds_the_three_servers_with_every_figure(self):
        got = mediaserver.comparison()
        self.assertEqual([s["id"] for s in got["servers"]], ["jellyfin", "plex", "emby"])
        for s in got["servers"]:
            for key in ("memory_mib", "cpu_pct", "startup_s", "image_mb"):
                self.assertIsInstance(s.get(key), (int, float), (s["id"], key))
            self.assertGreater(s["memory_mib"], 0)
        self.assertRegex(got["measured"], r"^2026-\d\d-\d\d$")
        self.assertIn("idle", got["caveat"], "the page says the figures are idle ones")
        self.assertIn("36 readings", got["method"])

    def test_a_missing_or_broken_file_answers_nothing_instead_of_failing(self):
        for broken in (OSError("gone"), ValueError("bad")):
            with mock.patch("builtins.open", side_effect=broken):
                self.assertEqual(mediaserver.comparison(), {"servers": [], "method": "", "caveat": ""})

    def test_nothing_is_measured_by_starboard(self):
        src = open(mediaserver.__file__).read()  # noqa: SIM115
        body = src.split("def comparison():")[1]
        for word in ("subprocess", "docker", "psutil"):
            self.assertNotIn(word, body)

    def test_the_file_is_plain_json_a_person_can_read(self):
        with open(FILE, encoding="utf-8") as f:
            json.load(f)


if __name__ == "__main__":
    unittest.main()
