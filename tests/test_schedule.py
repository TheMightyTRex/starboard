"""Download hours against a made-up qBittorrent and SABnzbd."""

import json
import tempfile
import threading
import unittest
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard.config import Config
from starboard.schedule import Schedule, in_hours


class FakeClients(BaseHTTPRequestHandler):
    torrents = {}
    sab_paused = False

    def log_message(self, *a):
        pass

    def reply(self, payload):
        body = json.dumps(payload).encode() if not isinstance(payload, str) else payload.encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/v2/torrents/info"):
            return self.reply([{"hash": h, "progress": p, "state": st} for h, (p, st) in FakeClients.torrents.items()])
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        mode = q["mode"][0]
        if mode == "queue":
            return self.reply({"queue": {"paused": FakeClients.sab_paused, "slots": []}})
        FakeClients.sab_paused = mode == "pause"
        return self.reply({"status": True})

    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        hashes = urllib.parse.parse_qs(self.rfile.read(size).decode())["hashes"][0].split("|")
        for h in hashes:
            p, _ = FakeClients.torrents[h]
            FakeClients.torrents[h] = (p, "stoppedDL" if self.path.endswith("/stop") else "downloading")
        return self.reply("Ok.")


class ScheduleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeClients)
        threading.Thread(target=cls.fake.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.fake.shutdown()

    def test_hours(self):
        at = lambda h: datetime(2026, 11, 2, h)
        self.assertTrue(in_hours(1, 6, at(3)))
        self.assertFalse(in_hours(1, 6, at(6)))
        self.assertTrue(in_hours(22, 6, at(23)))
        self.assertTrue(in_hours(22, 6, at(2)))
        self.assertFalse(in_hours(22, 6, at(12)))

    def test_pause_outside_hours_then_resume_only_ours(self):
        url = f"http://127.0.0.1:{self.fake.server_port}"
        FakeClients.torrents = {"a": (0.5, "downloading"), "b": (0.2, "stoppedDL"), "seed": (1, "uploading")}
        FakeClients.sab_paused = False
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            c.data["services"] = [
                {"id": "qbittorrent", "name": "qBittorrent", "type": "qbittorrent", "url": url, "api_key": "k"},
                {"id": "sabnzbd", "name": "SABnzbd", "type": "sabnzbd", "url": url, "api_key": "k"}]
            now = datetime.now().hour
            c.update_general({"download_hours": {"enabled": True, "start": (now + 1) % 24, "end": (now + 2) % 24}})
            s = Schedule(c)
            s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "stoppedDL")
            self.assertEqual(FakeClients.torrents["seed"][1], "uploading")
            self.assertTrue(FakeClients.sab_paused)
            self.assertEqual(s.status()["mode"], "pause")
            # Someone starts "a" by hand while paused: the next check leaves it running.
            FakeClients.torrents["a"] = (0.5, "downloading")
            s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "downloading")
            # Resume now runs everything, including "b" that was stopped before Starboard.
            status = s.act("resume")
            self.assertEqual((status["mode"], status["reason"], status["errors"]), ("run", "manual", []))
            self.assertEqual(FakeClients.torrents["b"][1], "downloading")
            self.assertFalse(FakeClients.sab_paused)
            s.act("follow")
            self.assertEqual(FakeClients.torrents["a"][1], "stoppedDL")
            # Turning the hours off starts again what Starboard stopped.
            c.update_general({"download_hours": {"enabled": False}})
            s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "downloading")
            self.assertFalse(FakeClients.sab_paused)
            with self.assertRaises(ValueError):
                s.act("resume")


if __name__ == "__main__":
    unittest.main()
