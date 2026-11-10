"""End-to-end tests against a real server and a fake Sonarr. Run: python3 -m unittest discover tests"""

import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import auth
from starboard.config import SCHEMA, Config, ConfigError, validate_service
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
        os.environ["STARBOARD_HISTORY"] = "0"
        os.environ["STARBOARD_SCHEDULE"] = "0"
        os.environ["STARBOARD_WATCH"] = "0"
        os.environ["STARBOARD_JOBS"] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
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
        self.assertNotIn("Max-Age", cookie)  # Remember me not ticked: gone when the browser closes
        ServerTest.cookie = cookie.split(";")[0]
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "setup-token")))
        resp, _ = self.request("POST", "/api/setup", {"token": "x", "password": "another long password"}, cookie=False)
        self.assertEqual(resp.status, 409)

    def test_history_answers_with_history_off(self):
        self.sign_in()
        resp, data = self.request("GET", "/api/history?hours=1")
        self.assertEqual(resp.status, 200, data)
        self.assertEqual((data["interval"], data["points"]), (300, []))

    def test_logs_list_report_and_delete(self):
        self.sign_in()
        self.request("PUT", "/api/config/general", {"logs": {"keep_days": 30}}, {"Origin": f"http://127.0.0.1:{self.port}"})
        resp, data = self.request("GET", "/api/logs")
        self.assertEqual(resp.status, 200)
        self.assertTrue(any(e["message"].startswith("Changed: logs") for e in data["entries"]))
        self.assertEqual(data["settings"]["keep_days"], 30)
        resp, text = self.request("GET", "/api/logs/report")
        self.assertIn(b"## About this Starboard", text)
        self.assertNotIn(b"correct horse", text)
        resp, data = self.request("POST", "/api/logs/clear", {}, {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(resp.status, 200)
        resp, data = self.request("GET", "/api/logs")
        self.assertEqual([e["area"] for e in data["entries"]], ["logs"])  # only the line saying they were deleted

    def test_05_security_headers(self):
        resp, _ = self.request("GET", "/login.html", cookie=False)
        self.assertIn("default-src 'self'", resp.getheader("Content-Security-Policy"))
        self.assertEqual(resp.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(resp.getheader("Referrer-Policy"), "no-referrer")
        self.assertEqual(resp.getheader("Cross-Origin-Resource-Policy"), "same-origin")
        self.assertEqual(resp.getheader("Cross-Origin-Opener-Policy"), "same-origin")
        # The password is posted, never put in the address, even if Enter is pressed before the script loads.
        for page in ("login.html", "setup.html"):
            with open(os.path.join(os.path.dirname(__file__), "..", "web", page), encoding="utf-8") as f:
                self.assertRegex(f.read(), r'<form id="login-form"[^>]*method="post"')

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

    def test_08b_remember_me_keeps_the_cookie(self):
        resp, _ = self.request("POST", "/api/login", {"password": "correct horse battery", "remember": True}, cookie=False)
        self.assertEqual(resp.status, 200)
        self.assertIn(f"Max-Age={7 * 86400}", resp.getheader("Set-Cookie"))
        resp, _ = self.request("POST", "/api/login", {"password": "correct horse battery"}, cookie=False)
        self.assertNotIn("Max-Age", resp.getheader("Set-Cookie"))

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


    def test_14_backup_and_restore_settings(self):
        self.sign_in()
        resp, _ = self.request("POST", "/api/backup/settings", {"password": "wrong"})
        self.assertEqual(resp.status, 401)
        self.app.limits.clear("127.0.0.1")
        resp, saved = self.request("POST", "/api/backup/settings", {"password": "correct horse battery"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(saved["format"], "starboard-settings")
        self.assertNotIn("auth", json.dumps(saved["settings"]))
        before = len(saved["services"])
        # Change something, then put the backup back.
        self.request("POST", "/api/services", {"name": "Temporary", "type": "link", "url": "http://127.0.0.1:9"})
        resp, data = self.request("POST", "/api/backup/restore", {"password": "correct horse battery", "backup": saved})
        self.assertEqual(resp.status, 200, data)
        self.assertEqual(len(data["config"]["services"]), before)
        self.assertTrue(self.app.config.data["auth"]["password_hash"])  # the password survives a restore
        resp, data = self.request("POST", "/api/backup/restore", {"password": "correct horse battery", "backup": {"format": "other"}})
        self.assertEqual(resp.status, 400)
        resp, listed = self.request("GET", "/api/backup/saved")
        self.assertTrue(any("before-restore" in i["name"] for i in listed["items"]))
        resp, data = self.request("POST", "/api/backup/restore-saved", {"password": "correct horse battery", "name": "../config.json"})
        self.assertEqual(resp.status, 400)
        resp, data = self.request("GET", "/api/backup/server")
        self.assertFalse(data["configured"])
        with tempfile.TemporaryDirectory() as jobs:
            os.makedirs(os.path.join(jobs, "requests"))
            os.environ["STARBOARD_JOBS_DIR"] = jobs
            try:
                resp, data = self.request("POST", "/api/backup/server", {"with_prompt": True})
                self.assertTrue(os.path.exists(os.path.join(jobs, "requests", "backup-with-prompt")))
                self.assertEqual(data["status"]["status"], "waiting")
            finally:
                del os.environ["STARBOARD_JOBS_DIR"]


    def test_15_access_list_and_privacy_switches(self):
        self.sign_in()
        resp, data = self.request("GET", "/api/access")
        keys = {a["key"]: a for a in data["items"]}
        self.assertFalse(keys["docker"]["on"])
        self.assertEqual(keys["docker"]["on_flag"], "--docker")
        self.request("PUT", "/api/config/general", {"show_posters": False, "fetch_icons": False})
        resp, data = self.request("GET", "/api/access")
        self.assertFalse({a["key"]: a for a in data["items"]}["posters"]["on"])
        resp, data = self.request("GET", "/api/containers")
        self.assertFalse(data["available"])
        self.request("PUT", "/api/config/general", {"show_posters": True, "fetch_icons": True})


    def test_71_a_history_file_over_80_mb_is_refused_before_the_upload(self):
        self.sign_in()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", "/api/import/upload?kind=json")
        for k, v in (("X-Starboard", "1"), ("Cookie", self.cookie), ("Content-Length", str(81 * 1024 * 1024))):
            conn.putheader(k, v)
        conn.endheaders()  # no body sent: the answer comes from the size alone
        resp = conn.getresponse()
        self.assertEqual((resp.status, json.loads(resp.read())["error"]), (400, "That history file is larger than 80 MB"))
        conn.close()
        self.assertFalse(self.app.importing)

    def test_72_a_new_password_signs_out_every_other_browser(self):
        # SEC-18: the browser that changed it stays signed in; every other one is signed out.
        self.sign_in()
        resp, _ = self.request("POST", "/api/login", {"password": "correct horse battery"}, cookie=False)
        other = resp.getheader("Set-Cookie").split(";")[0]
        resp, _ = self.request("GET", "/api/config", headers={"Cookie": other}, cookie=False)
        self.assertEqual(resp.status, 200)
        for old, new in (("correct horse battery", "another long made-up password"), ("another long made-up password", "correct horse battery")):
            resp, _ = self.request("POST", "/api/password", {"current": old, "new": new})
            self.assertEqual(resp.status, 200)
            ServerTest.cookie = resp.getheader("Set-Cookie").split(";")[0]
        resp, _ = self.request("GET", "/api/config", headers={"Cookie": other}, cookie=False)
        self.assertEqual(resp.status, 401)
        resp, _ = self.request("GET", "/api/config")
        self.assertEqual(resp.status, 200)

    def test_995_sign_out_everywhere_needs_the_password(self):
        # DASH-280: a session on its own cannot sign everyone out.
        self.sign_in()
        resp, _ = self.request("POST", "/api/sessions/end-all", {})
        self.assertEqual(resp.status, 401)
        resp, _ = self.request("POST", "/api/sessions/end-all", {"password": "not it"})
        self.assertEqual(resp.status, 401)
        resp, _ = self.request("GET", "/api/config")
        self.assertEqual(resp.status, 200)  # still signed in
        resp, _ = self.request("POST", "/api/sessions/end-all", {"password": "correct horse battery"})
        self.assertEqual(resp.status, 200)
        resp, _ = self.request("GET", "/api/config")
        self.assertEqual(resp.status, 401)
        ServerTest.cookie = None

    def test_73_snaglist_reports_need_the_key_from_a_signed_in_session(self):
        self.sign_in()
        report = {"title": "Apps: the button is hidden", "markdown": "## Hard to use\n\nThe button is hidden.",
                  "report": {"type": "ux", "severity": "major", "page": {"path": "/index.html"}, "element": {"component": "Apps"}}}
        send = lambda key, body=report: self.request("POST", "/api/feedback", body, {"X-Starboard-Feedback": key}, cookie=False)
        resp, _ = self.request("GET", "/api/feedback/key")
        self.assertEqual(resp.status, 404)  # Send feedback is inactive
        self.request("PUT", "/api/config/general", {"ux_notes": True})
        try:
            _, data = self.request("GET", "/api/feedback/key")
            key = data["key"]
            self.assertEqual(send("")[0].status, 401)
            self.assertEqual(send("made-up")[0].status, 401)
            self.assertEqual(send(key, {"title": "x", "markdown": " "})[0].status, 400)
            resp, data = send(key)
            self.assertEqual(resp.status, 200)
            _, listed = self.request("GET", "/api/ux-notes")
            saved = next(n for n in listed["notes"] if n["id"] == data["id"])
            self.assertEqual((saved["source"], saved["type"], saved["page"], saved["part"], saved["status"]),
                             ("snaglist", "ux", "/index.html", "Apps", "open"))
            self.assertEqual(self.request("GET", "/api/feedback/key")[1]["key"], key)  # one key for each session
            # The key ends with the session it was given to.
            other = self.app.sessions.create(1, self.app.session_version)
            other_key = self.app.feedback_key(other)
            self.assertEqual(send(other_key)[0].status, 200)
            self.app.sessions.end(other)
            self.assertEqual(send(other_key)[0].status, 401)
            # The page lets in Snaglist's stylesheet by its hash, and no other inline style.
            resp, _ = self.request("GET", "/login.html", cookie=False)
            self.assertRegex(resp.getheader("Content-Security-Policy"), r"style-src 'self' 'sha256-[A-Za-z0-9+/]{43}='; ")
            self.request("PUT", "/api/config/general", {"ux_notes": False})
            self.assertEqual(send(key)[0].status, 401)
        finally:
            self.request("PUT", "/api/config/general", {"ux_notes": False})
            for n in self.app.uxnotes.list():
                self.app.uxnotes.remove(n["id"])

    def test_70_ux_notes_only_while_turned_on(self):
        self.sign_in()
        resp, _ = self.request("GET", "/api/ux-notes")
        self.assertEqual(resp.status, 404)  # off by default
        self.request("PUT", "/api/config/general", {"ux_notes": True})
        resp, data = self.request("GET", "/api/session")
        self.assertTrue(data["ux_notes"])
        resp, data = self.request("POST", "/api/ux-notes", {"what": "  "})
        self.assertEqual(resp.status, 400)
        resp, note = self.request("POST", "/api/ux-notes", {
            "what": "<script>alert(1)</script>" + "x" * 5000, "kind": "Nonsense", "severity": "stops-me",
            "page": "/index.html", "part": "Button: Check again", "zoom": 1.25, "display": ["contrast", 5], "extra": "dropped"})
        self.assertEqual(resp.status, 200)
        self.assertEqual((note["kind"], note["severity"], note["status"], len(note["what"])), ("Other", "stops-me", "open", 4000))
        self.assertNotIn("extra", note)
        self.assertEqual(note["display"], ["contrast"])
        path = os.path.join(self.tmp.name, "ux-notes.json")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        resp, _ = self.request("POST", "/api/ux-notes/update", {"id": note["id"], "status": "fixed"})
        self.assertEqual(resp.status, 200)
        _, data = self.request("GET", "/api/ux-notes")
        self.assertEqual(data["notes"][0]["status"], "fixed")
        self.request("POST", "/api/ux-notes/remove", {"id": note["id"]})
        _, data = self.request("GET", "/api/ux-notes")
        self.assertEqual(data["notes"], [])
        resp, _ = self.request("GET", "/api/ux-notes", cookie=False)
        self.assertEqual(resp.status, 401)
        self.request("PUT", "/api/config/general", {"ux_notes": False})

    def test_16_static_files_are_compressed_and_cached(self):
        resp, _ = self.request("GET", "/js/common.js", headers={"Accept-Encoding": "gzip"}, cookie=False)
        self.assertEqual(resp.getheader("Content-Encoding"), "gzip")
        tag = resp.getheader("ETag")
        resp, _ = self.request("GET", "/js/common.js", headers={"If-None-Match": tag}, cookie=False)
        self.assertEqual(resp.status, 304)


class ConfigTest(unittest.TestCase):
    def test_rejects_bad_addresses(self):
        for url in ("file:///etc/passwd", "ftp://x", "javascript:alert(1)", ""):
            with self.assertRaises(ConfigError):
                validate_service({"name": "A", "type": "link", "url": url})

    def test_outside_address(self):
        ok = validate_service({"name": "A", "type": "link", "url": "http://127.0.0.1:1", "outside_link": "https://media.example.com/"})
        self.assertEqual(ok["outside_link"], "https://media.example.com")
        for bad in ("media.example.com", "javascript:alert(1)", "https://a b"):
            with self.assertRaises(ConfigError):
                validate_service({"name": "A", "type": "link", "url": "http://127.0.0.1:1", "outside_link": bad})
        with tempfile.TemporaryDirectory() as d:
            public = Config(d).public()
            self.assertTrue(public["show_home_address"])
            self.assertTrue(public["show_outside_address"])

    def test_coming_up_settings(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual((c.public()["upcoming_view"], c.public()["upcoming_days"]), ("list", 14))
            c.update_general({"upcoming_view": "calendar", "upcoming_days": 30})
            self.assertEqual((Config(d).data["upcoming_view"], Config(d).data["upcoming_days"]), ("calendar", 30))
            for bad in ({"upcoming_view": "grid"}, {"upcoming_days": 365}, {"upcoming_days": "x"}):
                with self.assertRaises((ConfigError, ValueError)):
                    c.update_general(bad)

    def test_migration_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"schema": 0, "services": []}, f)
            cfg = Config(d)
            self.assertEqual(cfg.data["schema"], SCHEMA)
            self.assertTrue(os.listdir(os.path.join(d, "backups")))

    def test_removed_design_falls_back_to_health_first(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"schema": 1, "design": "calm", "services": []}, f)
            self.assertEqual(Config(d).data["design"], "health")

    def test_setup_code_survives_a_restart(self):
        from starboard.config import new_setup_token
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(new_setup_token(d), new_setup_token(d))

    def test_ten_characters_is_enough(self):
        self.assertIsNone(auth.password_problem("a" * 10))
        self.assertIsNotNone(auth.password_problem("a" * 9))

    def test_category_is_chosen_for_known_apps(self):
        from starboard.config import DEFAULTS, guess_group
        groups = DEFAULTS["groups"]
        self.assertEqual(guess_group({"name": "Sonarr", "type": "sonarr"}, groups), "Find and organise")
        self.assertEqual(guess_group({"name": "qBittorrent", "type": "link"}, groups), "Search and download")
        self.assertEqual(guess_group({"name": "Jellyfin", "type": "jellyfin"}, groups), "Watch, listen and request")
        self.assertEqual(guess_group({"name": "Something new", "type": "link"}, groups), "Dashboards and tools")
        self.assertEqual(guess_group({"name": "Sonarr", "type": "sonarr"}, ["Watch", "Get", "Fetch", "Other"]), "Get")

    def test_history_records_and_thins_out(self):
        import collections
        import threading
        import time as clock
        from starboard import sysinfo
        with tempfile.TemporaryDirectory() as d:
            h = sysinfo.History.__new__(sysinfo.History)
            h.points, h.lock, h.path = collections.deque(), threading.Lock(), os.path.join(d, "history.json")
            h._previous = sysinfo.monitor()
            h.sample()
            self.assertEqual(len(h.get(1)), 1)
            for key in ("cpu", "mem", "rx", "tx", "read", "write"):
                self.assertIn(key, h.points[0])
            now = clock.time()
            h.points.extend({"t": now - i, "cpu": 1, "mem": 2, "load": 0, "rx": 0, "tx": 0, "read": 0, "write": 0, "temp": None} for i in range(2000))
            self.assertLessEqual(len(h.get(24)), 360)
            h._save()
            self.assertEqual(os.stat(h.path).st_mode & 0o777, 0o600)

    def test_filesystem_is_named(self):
        from starboard import sysinfo
        self.assertTrue(sysinfo.filesystem("/"))

    def test_password_hash(self):
        stored = auth.hash_password("a long password here", iterations=1000)
        self.assertTrue(auth.check_password("a long password here", stored))
        self.assertFalse(auth.check_password("wrong", stored))
        self.assertFalse(auth.check_password("x", "garbage"))


if __name__ == "__main__":
    unittest.main()
