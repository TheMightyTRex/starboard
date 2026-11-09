"""Download now, outside download hours (DASH-171): one item downloads, everything else stays paused."""
import tempfile
import time
import unittest
from unittest import mock

from starboard import schedule


class Config:
    def __init__(self, folder):
        self.data_dir = folder
        self.data = {"download_hours": {"enabled": True, "start": 1, "end": 7},
                     "services": [{"id": "qb", "type": "qbittorrent", "name": "qBittorrent", "url": "http://qb", "api_key": "k", "enabled": True}],
                     "performance": {}}


class DownloadNow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.s = schedule.Schedule(Config(self.tmp.name))
        self.s.ensure = lambda: None

    def test_only_the_allowed_torrent_runs(self):
        self.s.allow({"kind": "movie", "id": 7, "title": "Arrival"})
        sent = []
        torrents = [{"hash": "AAA", "progress": 0.2, "state": "downloading"}, {"hash": "BBB", "progress": 0.1, "state": "stoppedDL"}]
        queue = {"items": [{"download_id": "bbb", "media": {"kind": "movie", "id": 7}, "episodes": []}]}
        with mock.patch("starboard.services.qbit", side_effect=lambda c, path, data=None: torrents if path == "torrents/info" else sent.append((path, data))), \
                mock.patch("starboard.services.reelix_native", return_value=[{"url": "http://r/api/v1", "api_key": "k"}]), \
                mock.patch("starboard.services._api", return_value=queue):
            state = self.s.load()
            self.s.apply("pause", state)
        self.assertIn(("torrents/start", {"hashes": "BBB"}), sent)
        self.assertIn(("torrents/stop", {"hashes": "AAA"}), sent)
        self.assertEqual([a["title"] for a in state["now"]], ["Arrival"])

    def test_the_allowance_goes_when_its_download_has_gone(self):
        self.s.allow({"kind": "episode", "id": 41, "title": "Ghosts"})
        state = self.s.load()
        state["now"][0]["seen"] = True
        with mock.patch("starboard.services.reelix_native", return_value=[{"url": "http://r/api/v1", "api_key": "k"}]), \
                mock.patch("starboard.services._api", return_value={"items": []}):
            self.assertEqual(self.s._allowed_downloads(state), set())
        self.assertEqual(state["now"], [])
        state["now"] = [{"kind": "movie", "id": 1, "title": "x", "until": time.time() - 1, "seen": False}]
        self.assertEqual(self.s._allowed_downloads(state), set())  # expired


if __name__ == "__main__":
    unittest.main()
