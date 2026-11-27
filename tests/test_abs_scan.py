"""Scan Audiobookshelf's libraries from Starboard (DASH-578): one POST to its own scan call for each library."""
import http.client
import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import auth, listening, services
from starboard.server import make_server


class FakeAbs(BaseHTTPRequestHandler):
    scans = []
    refuse = False

    def log_message(self, *a):
        pass

    def reply(self, code, body=b"OK"):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.headers.get("Authorization") != "Bearer admin-key":
            return self.reply(401, {})
        if urllib.parse.urlparse(self.path).path == "/api/libraries":
            return self.reply(200, {"libraries": [{"id": "lib-1", "name": "Audiobooks", "mediaType": "book"},
                                                  {"id": "pods", "name": "Podcasts", "mediaType": "podcast"},
                                                  {"id": "../evil", "name": "Bad id"}]})
        self.reply(404, {})

    def do_POST(self):
        if self.headers.get("Authorization") != "Bearer admin-key" or FakeAbs.refuse:
            return self.reply(403, {})
        FakeAbs.scans.append(urllib.parse.urlparse(self.path).path)
        self.reply(200)


class Scan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abs = ThreadingHTTPServer(("127.0.0.1", 0), FakeAbs)
        threading.Thread(target=cls.abs.serve_forever, daemon=True).start()
        cls.service = {"id": "abs", "name": "Audiobookshelf", "type": "audiobookshelf", "url": f"http://127.0.0.1:{cls.abs.server_port}", "api_key": "admin-key"}

    @classmethod
    def tearDownClass(cls):
        cls.abs.shutdown()

    def setUp(self):
        FakeAbs.scans, FakeAbs.refuse = [], False

    def test_each_library_is_scanned_by_its_own_call_and_a_odd_id_is_skipped(self):
        self.assertEqual(listening.abs_scan(self.service), ["Audiobooks", "Podcasts"])
        self.assertEqual(FakeAbs.scans, ["/api/libraries/lib-1/scan", "/api/libraries/pods/scan"])

    def test_a_refusal_is_said(self):
        FakeAbs.refuse = True
        with self.assertRaises(services.ServiceError) as e:
            listening.abs_scan(self.service)
        self.assertIn("refused the API key", str(e.exception))


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Scan.setUpClass()
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.app.config.data["services"] = [dict(Scan.service)]
        r, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, signed=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        Scan.tearDownClass()
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, body=None, signed=True):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = {"Content-Type": "application/json"}
        if method != "GET":
            h["X-Starboard"] = "1"
        if signed:
            h["Cookie"] = cls.cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        try:
            return r, json.loads(raw)
        except ValueError:
            return r, raw

    def setUp(self):
        Scan.setUp(self)
        self.app.config.data["services"] = [dict(Scan.service)]

    def test_the_button_scans_and_says_what_it_asked(self):
        r, d = self.call("POST", "/api/listening/scan")
        self.assertEqual(r.status, 200)
        self.assertEqual(d["libraries"], ["Audiobooks", "Podcasts"])
        self.assertIn("Audiobookshelf is scanning Audiobooks, Podcasts", d["said"])

    def test_without_a_key_it_says_where_to_add_one(self):
        self.app.config.data["services"] = [{**Scan.service, "api_key": ""}]
        r, d = self.call("POST", "/api/listening/scan")
        self.assertEqual(r.status, 400)
        self.assertIn("Manage apps", json.dumps(d))

    def test_a_refusal_is_a_502_in_words(self):
        FakeAbs.refuse = True
        r, d = self.call("POST", "/api/listening/scan")
        self.assertEqual(r.status, 502)
        self.assertIn("refused the API key", json.dumps(d))

    def test_it_needs_a_sign_in(self):
        r, _ = self.call("POST", "/api/listening/scan", signed=False)
        self.assertIn(r.status, (303, 401, 403))
        self.assertEqual(FakeAbs.scans, [])


if __name__ == "__main__":
    unittest.main()
