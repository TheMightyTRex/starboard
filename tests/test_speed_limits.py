"""Speed limits for qBittorrent and NZBGet from Starboard (DASH-578): read, set, refuse bad figures, and say so in words."""
import http.client
import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import auth, services, speed_limits
from starboard.server import make_server


class FakeQbit(BaseHTTPRequestHandler):
    prefs = {}
    alt = False
    toggles = 0

    def log_message(self, *a):
        pass

    def reply(self, body, kind="application/json"):
        raw = body if isinstance(body, bytes) else (json.dumps(body) if not isinstance(body, str) else body).encode()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.endswith("app/preferences"):
            return self.reply(FakeQbit.prefs)
        if self.path.endswith("transfer/speedLimitsMode"):
            return self.reply("1" if FakeQbit.alt else "0", "text/plain")
        self.send_error(404)

    def do_POST(self):
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
        if self.path.endswith("app/setPreferences"):
            FakeQbit.prefs.update(json.loads(form["json"][0]))
            return self.reply("")
        if self.path.endswith("transfer/toggleSpeedLimitsMode"):
            FakeQbit.alt = not FakeQbit.alt
            FakeQbit.toggles += 1
            return self.reply("")
        self.send_error(404)


class FakeNzbget(BaseHTTPRequestHandler):
    limit = 0  # bytes a second
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        call = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeNzbget.seen.append(call["method"])
        if call["method"] == "status":
            out = {"result": {"DownloadLimit": FakeNzbget.limit, "DownloadRate": 0}}
        elif call["method"] == "rate":
            FakeNzbget.limit = call["params"][0] * 1024
            out = {"result": True}
        else:
            out = {"error": {"message": "Invalid procedure"}}
        raw = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class SpeedLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = ThreadingHTTPServer(("127.0.0.1", 0), FakeQbit)
        cls.n = ThreadingHTTPServer(("127.0.0.1", 0), FakeNzbget)
        for s in (cls.q, cls.n):
            threading.Thread(target=s.serve_forever, daemon=True).start()
        cls.qb = {"id": "qbittorrent", "name": "qBittorrent", "type": "qbittorrent", "url": f"http://127.0.0.1:{cls.q.server_port}", "api_key": "k"}
        cls.nz = {"id": "nzbget", "name": "NZBGet", "type": "nzbget", "url": f"http://127.0.0.1:{cls.n.server_port}", "api_key": "u:p"}

    @classmethod
    def tearDownClass(cls):
        cls.q.shutdown()
        cls.n.shutdown()

    def setUp(self):
        FakeQbit.prefs = {"dl_limit": -1, "up_limit": 250}
        FakeQbit.alt, FakeQbit.toggles = False, 0
        FakeNzbget.limit, FakeNzbget.seen = 0, []

    def test_the_limits_are_read_in_kilobytes_with_no_limit_as_zero(self):
        self.assertEqual(speed_limits.read(self.qb), {"id": "qbittorrent", "name": "qBittorrent", "kind": "torrent", "down": 0, "up": 250, "alt": False})
        FakeNzbget.limit = 2_048_000
        self.assertEqual(speed_limits.read(self.nz), {"id": "nzbget", "name": "NZBGet", "kind": "usenet", "down": 2000, "up": None, "alt": None})

    def test_qbittorrent_limits_are_set_and_read_back(self):
        row = speed_limits.apply(self.qb, {"down": 1500, "up": 0})
        self.assertEqual((row["down"], row["up"]), (1500, 0))
        self.assertEqual(FakeQbit.prefs["dl_limit"], 1500)

    def test_the_alternative_limits_switch_is_toggled_only_when_it_must_change(self):
        self.assertTrue(speed_limits.apply(self.qb, {"alt": True})["alt"])
        speed_limits.apply(self.qb, {"alt": True})  # already on: nothing to toggle
        self.assertEqual(FakeQbit.toggles, 1)
        self.assertFalse(speed_limits.apply(self.qb, {"alt": False})["alt"])
        self.assertEqual(FakeQbit.toggles, 2)

    def test_nzbget_has_a_download_limit_only(self):
        self.assertEqual(speed_limits.apply(self.nz, {"down": 800})["down"], 800)
        self.assertEqual(FakeNzbget.limit, 800 * 1024)
        for body in ({"up": 5}, {"alt": True}):
            with self.assertRaises(ValueError) as e:
                speed_limits.apply(self.nz, body)
            self.assertIn("download limit only", str(e.exception))

    def test_bad_figures_are_refused_in_words_and_nothing_is_sent(self):
        for bad in (-1, 1.5, "100", True, None, speed_limits.MOST + 1):
            with self.assertRaises(ValueError) as e:
                speed_limits.apply(self.qb, {"down": bad})
            self.assertIn("whole number of kilobytes a second", str(e.exception))
        with self.assertRaises(ValueError):
            speed_limits.apply(self.qb, {})
        with self.assertRaises(ValueError):
            speed_limits.apply(self.qb, {"alt": "yes"})
        self.assertEqual(FakeQbit.prefs, {"dl_limit": -1, "up_limit": 250})
        self.assertEqual(FakeNzbget.seen, [])

    def test_only_apps_with_a_key_that_are_on_are_listed(self):
        rows = [self.qb, {**self.nz, "id": "off", "enabled": False}, {**self.nz, "id": "nokey", "api_key": ""},
                {"id": "sab", "name": "SABnzbd", "type": "sabnzbd", "url": "http://x", "api_key": "k"}]
        self.assertEqual([c["id"] for c in speed_limits.clients(rows)], ["qbittorrent"])

    def test_an_app_that_does_not_answer_is_a_service_error(self):
        gone = {**self.qb, "url": "http://127.0.0.1:1"}
        with self.assertRaises(services.ServiceError):
            speed_limits.read(gone)

    def test_the_log_words(self):
        self.assertEqual(speed_limits.words({"down": 0, "up": 250, "alt": True}), "download no limit, upload 250 KB/s, alternative limits on")
        self.assertEqual(speed_limits.words({"down": 800, "up": None, "alt": None}), "download 800 KB/s")


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        SpeedLimits.setUpClass()
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.app.config.data["services"] = [dict(SpeedLimits.qb), dict(SpeedLimits.nz)]
        resp, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=None)
        cls.cookie = resp.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        SpeedLimits.tearDownClass()
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, body=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = {"Content-Type": "application/json"}
        if method != "GET":
            h["X-Starboard"] = "1"
        if cookie is not None:
            h["Cookie"] = cls.cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        try:
            return r, json.loads(raw)
        except ValueError:
            return r, raw

    def setUp(self):
        SpeedLimits.setUp(self)

    def test_the_page_reads_and_a_change_is_kept_and_logged(self):
        r, d = self.call("GET", "/api/speed-limits")
        self.assertEqual((r.status, [i["id"] for i in d["items"]], d["errors"]), (200, ["qbittorrent", "nzbget"], []))
        r, row = self.call("POST", "/api/speed-limits/qbittorrent", {"down": 900})
        self.assertEqual((r.status, row["down"]), (200, 900))
        r, row = self.call("POST", "/api/speed-limits/nzbget", {"down": 300})
        self.assertEqual((r.status, row["down"]), (200, 300))

    def test_bad_requests_get_words(self):
        r, d = self.call("POST", "/api/speed-limits/qbittorrent", {"down": -5})
        self.assertEqual(r.status, 400)
        self.assertIn("whole number", json.dumps(d))
        r, _ = self.call("POST", "/api/speed-limits/nothing", {"down": 5})
        self.assertEqual(r.status, 404)
        r, _ = self.call("POST", "/api/speed-limits/qbittorrent", {"down": 5}, cookie=None)
        self.assertIn(r.status, (303, 401, 403))

    def test_an_app_that_does_not_answer_is_said_and_the_others_still_show(self):
        self.app.config.data["services"][1] = {**SpeedLimits.nz, "url": "http://127.0.0.1:1"}
        try:
            r, d = self.call("GET", "/api/speed-limits")
            self.assertEqual([i["id"] for i in d["items"]], ["qbittorrent"])
            self.assertEqual(d["errors"][0]["name"], "NZBGet")
            r, _ = self.call("POST", "/api/speed-limits/nzbget", {"down": 5})
            self.assertEqual(r.status, 502)
        finally:
            self.app.config.data["services"][1] = dict(SpeedLimits.nz)


if __name__ == "__main__":
    unittest.main()
