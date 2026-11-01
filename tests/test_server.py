"""End-to-end tests against a real server and a fake Sonarr. Run: python3 -m unittest discover tests"""

import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import auth
from starboard.config import Config, ConfigError, validate_service
from starboard.server import make_server

API_KEY = "test-key-not-real"


class FakeSonarr(BaseHTTPRequestHandler):
    added = []

    def log_message(self, *args):
        pass

    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("X-Api-Key") != API_KEY:
            return self._send(401, {"message": "Unauthorized"})
        if self.path.startswith("/api/v3/system/status"):
            return self._send(200, {"version": "4.0.0"})
        if self.path.startswith("/api/v3/series/lookup"):
            return self._send(200, [
                {"title": "Example Show", "tvdbId": 101, "year": 2020, "images": [{"coverType": "poster", "remoteUrl": "https://example.org/p.jpg"}]},
                {"title": "Owned Show", "tvdbId": 102, "id": 7},
            ])
        if self.path.startswith("/api/v3/qualityprofile"):
            return self._send(200, [{"id": 4, "name": "HD"}])
        if self.path.startswith("/api/v3/rootfolder"):
            return self._send(200, [{"path": "/tv", "freeSpace": 10}])
        if self.path.startswith("/api/v3/queue"):
            return self._send(200, {"records": [{"title": "Example.S01E01", "size": 100, "sizeleft": 25, "trackedDownloadState": "downloading"}]})
        return self._send(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeSonarr.added.append(body)
        return self._send(201, dict(body, id=99))


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeSonarr)
        threading.Thread(target=cls.fake.serve_forever, daemon=True).start()
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000  # fast tests
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.cookie = None

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.fake.shutdown()
        cls.tmp.cleanup()

    def request(self, method, path, body=None, headers=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Content-Type": "application/json"}
        if method != "GET":
            h["X-Starboard"] = "1"
        if cookie and self.cookie:
            h["Cookie"] = self.cookie
        h.update(headers or {})
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        resp = conn.getresponse()
        raw = resp.read()
        try:
            data = json.loads(raw)
        except ValueError:
            data = raw
        return resp, data

    def sign_in(self):
        if ServerTest.cookie:
            return
        if self.app.needs_setup:
            resp, _ = self.request("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"})
        else:
            resp, _ = self.request("POST", "/api/login", {"password": "correct horse battery"})
        self.assertEqual(resp.status, 200)
        ServerTest.cookie = resp.getheader("Set-Cookie").split(";")[0]

    # Security --------------------------------------------------------

    def test_01_pages_need_setup_then_sign_in(self):
        resp, _ = self.request("GET", "/index.html", cookie=False)
        self.assertEqual(resp.status, 303)
        self.assertEqual(resp.getheader("Location"), "/setup.html")

    def test_02_setup_needs_the_code(self):
        resp, data = self.request("POST", "/api/setup", {"token": "wrong", "password": "correct horse battery"}, cookie=False)
        self.assertEqual(resp.status, 403)
        self.app.limits.clear("127.0.0.1")

    def test_03_setup_rejects_short_password(self):
        resp, _ = self.request("POST", "/api/setup", {"token": self.app.setup_token, "password": "short"}, cookie=False)
        self.assertEqual(resp.status, 400)

    def test_04_setup_then_cookie_flags(self):
        resp, _ = self.request("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"}, cookie=False)
        self.assertEqual(resp.status, 200)
        cookie = resp.getheader("Set-Cookie")
        for flag in ("HttpOnly", "SameSite=Strict", "Path=/"):
            self.assertIn(flag, cookie)
        ServerTest.cookie = cookie.split(";")[0]
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "setup-token")))
        resp, _ = self.request("POST", "/api/setup", {"token": "x", "password": "another long password"}, cookie=False)
        self.assertEqual(resp.status, 409)

    def test_05_security_headers(self):
        resp, _ = self.request("GET", "/login.html", cookie=False)
        self.assertIn("default-src 'self'", resp.getheader("Content-Security-Policy"))
        self.assertEqual(resp.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(resp.getheader("Referrer-Policy"), "no-referrer")

    def test_06_changes_need_the_dashboard_header(self):
        self.sign_in()
        resp, _ = self.request("PUT", "/api/config/general", {"site_name": "X"}, headers={"X-Starboard": "0"})
        self.assertEqual(resp.status, 403)
        resp, _ = self.request("PUT", "/api/config/general", {"site_name": "X"}, headers={"Origin": "http://evil.example"})
        self.assertEqual(resp.status, 403)

    def test_07_no_path_traversal(self):
        self.sign_in()
        for path in ("/../starboard/config.py", "/%2e%2e/VERSION", "/css/../../VERSION"):
            resp, _ = self.request("GET", path)
            self.assertIn(resp.status, (303, 404), path)

    def test_08_wrong_password_is_rate_limited(self):
        for _ in range(5):
            resp, _ = self.request("POST", "/api/login", {"password": "nope"}, cookie=False)
            self.assertEqual(resp.status, 401)
        resp, _ = self.request("POST", "/api/login", {"password": "correct horse battery"}, cookie=False)
        self.assertEqual(resp.status, 429)
        self.app.limits.clear("127.0.0.1")

    def test_09_api_needs_sign_in(self):
        resp, _ = self.request("GET", "/api/config", cookie=False)
        self.assertEqual(resp.status, 401)

    # Apps, search and add -----------------------------------------------

    def test_10_api_key_never_leaves_the_server(self):
        self.sign_in()
        resp, data = self.request("POST", "/api/services", {
            "name": "Sonarr", "type": "sonarr", "url": f"http://127.0.0.1:{self.fake.server_address[1]}",
            "api_key": API_KEY, "group": "Downloads",
        })
        self.assertEqual(resp.status, 200, data)
        resp, raw = self.request("GET", "/api/config")
        self.assertNotIn(API_KEY, json.dumps(raw))
        self.assertTrue(raw["services"][0]["has_api_key"])
        # Saving again without a key keeps the stored one.
        svc = dict(raw["services"][0], api_key="")
        self.request("POST", "/api/services", svc)
        self.assertEqual(self.app.config.service("sonarr")["api_key"], API_KEY)
        mode = os.stat(os.path.join(self.tmp.name, "config.json")).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_11_status_search_add_queue(self):
        self.sign_in()
        if not self.app.config.service("sonarr"):
            self.test_10_api_key_never_leaves_the_server()
        resp, data = self.request("GET", "/api/status")
        self.assertEqual(data["items"][0]["state"], "up")
        resp, data = self.request("GET", "/api/search?q=example")
        self.assertEqual(resp.status, 200)
        titles = {r["title"]: r for r in data["results"]}
        self.assertFalse(titles["Example Show"]["in_library"])
        self.assertTrue(titles["Owned Show"]["in_library"])
        resp, data = self.request("POST", "/api/add", {"service": "sonarr", "key": "tvdb:101", "options": {"search": False}})
        self.assertEqual(resp.status, 200, data)
        sent = FakeSonarr.added[-1]
        self.assertEqual(sent["qualityProfileId"], 4)
        self.assertEqual(sent["rootFolderPath"], "/tv")
        self.assertFalse(sent["addOptions"]["searchForMissingEpisodes"])
        resp, data = self.request("POST", "/api/add", {"service": "sonarr", "key": "tvdb:102"})
        self.assertEqual(resp.status, 502)
        resp, data = self.request("POST", "/api/add", {"service": "sonarr", "key": "javascript:alert(1)"})
        self.assertEqual(resp.status, 400)
        resp, data = self.request("GET", "/api/queue")
        self.assertEqual(data["items"][0]["progress"], 75.0)

    def test_12_wrong_key_is_reported(self):
        self.sign_in()
        resp, data = self.request("POST", "/api/services/test", {
            "name": "Bad", "type": "sonarr", "url": f"http://127.0.0.1:{self.fake.server_address[1]}", "api_key": "wrong"})
        self.assertEqual(data["state"], "down")
        self.assertIn("refused the API key", data["message"])


    def test_13_network_switch(self):
        self.sign_in()
        resp, data = self.request("GET", "/api/network")
        self.assertTrue(data["network_access"])
        self.assertTrue(data["you_are_on_this_computer"])
        called = []
        self.app.on_network_change = lambda: called.append(True)
        resp, data = self.request("PUT", "/api/config/general", {"network_access": False})
        self.assertFalse(data["network_access"])
        self.assertEqual(self.app.listen_host(), "127.0.0.1")
        # This computer still gets in; any other address is refused.
        resp, _ = self.request("GET", "/api/network")
        self.assertEqual(resp.status, 200)
        from starboard import server as srv
        original = srv.is_loopback
        srv.is_loopback = lambda address: False
        try:
            resp, _ = self.request("GET", "/api/config")
            self.assertEqual(resp.status, 403)
        finally:
            srv.is_loopback = original
        self.request("PUT", "/api/config/general", {"network_access": True})
        self.assertEqual(self.app.listen_host(), "0.0.0.0")
        import time
        time.sleep(0.8)
        self.assertEqual(len(called), 2)


class ConfigTest(unittest.TestCase):
    def test_rejects_bad_addresses(self):
        for url in ("file:///etc/passwd", "ftp://x", "javascript:alert(1)", ""):
            with self.assertRaises(ConfigError):
                validate_service({"name": "A", "type": "link", "url": url})

    def test_migration_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"schema": 0, "services": []}, f)
            cfg = Config(d)
            self.assertEqual(cfg.data["schema"], 1)
            self.assertTrue(os.listdir(os.path.join(d, "backups")))

    def test_removed_design_falls_back_to_health_first(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"schema": 1, "design": "calm", "services": []}, f)
            self.assertEqual(Config(d).data["design"], "health")

    def test_password_hash(self):
        stored = auth.hash_password("a long password here", iterations=1000)
        self.assertTrue(auth.check_password("a long password here", stored))
        self.assertFalse(auth.check_password("wrong", stored))
        self.assertFalse(auth.check_password("x", "garbage"))


if __name__ == "__main__":
    unittest.main()
