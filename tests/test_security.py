"""The findings of the 2 November 2026 security check, each kept fixed by a test."""

import http.client
import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import auth, containers, livetv, services
from starboard.config import Config, ConfigError
from starboard.server import make_server


class SecurityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent"
        auth.ITERATIONS = 1000
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        r = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "a long enough password"})
        cls.cookie = r[1].get("Set-Cookie", "").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, body=None, headers=None, cookie=None):
        c = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = {"X-Starboard": "1", "Origin": f"http://127.0.0.1:{cls.port}", "Content-Type": "application/json"}
        if cookie:
            h["Cookie"] = cookie
        h.update(headers or {})
        c.request(method, path, json.dumps(body).encode() if body is not None else None, h)
        r = c.getresponse()
        data = r.read()
        return r.status, dict(r.getheaders()), data

    def test_forwarded_address_is_believed_only_from_the_proxy(self):
        # SEC-04: X-Forwarded-For from anyone but the proxy cannot pick the address that sign-in limits count.
        from types import SimpleNamespace
        from starboard.server import Handler
        app = SimpleNamespace(trust_proxy=True, proxy_addresses={"127.0.0.1"})
        ask = lambda sender: Handler.client_address_text(SimpleNamespace(app=app, client_address=(sender, 5000),
                                                                         headers={"X-Forwarded-For": "203.0.113.9, 127.0.0.1"}))
        self.assertEqual(ask("127.0.0.1"), "203.0.113.9")  # the proxy passes on who is really asking
        self.assertEqual(ask("192.168.1.21"), "192.168.1.21")  # anyone else: their own address
        app.trust_proxy = False
        self.assertEqual(ask("127.0.0.1"), "127.0.0.1")  # proxy trust off: never believed

    def test_negative_content_length_is_refused(self):
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(b"POST /api/login HTTP/1.1\r\nHost: 127.0.0.1\r\nX-Starboard: 1\r\nContent-Length: -1\r\n\r\n")
        self.assertIn(b" 400 ", s.recv(200))
        s.close()

    def test_dot_dot_paths_do_not_skip_sign_in(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.putrequest("GET", "/css/../settings.html", skip_accept_encoding=True)
        c.endheaders()
        self.assertEqual(c.getresponse().status, 404)

    def test_unknown_host_names_are_refused(self):
        status, _, _ = self.call("GET", "/api/session", headers={"Host": "attacker.example"})
        self.assertEqual(status, 421)
        status, _, _ = self.call("GET", "/api/session", headers={"Host": f"localhost:{self.port}"})
        self.assertEqual(status, 200)

    def test_parallel_guesses_stay_within_the_limit(self):
        limits = auth.RateLimit(limit=5)
        with ThreadPoolExecutor(30) as pool:
            allowed = sum(pool.map(lambda _: limits.attempt("10.0.0.9"), range(30)))
        self.assertEqual(allowed, 5)

    def test_saved_key_is_not_sent_to_a_new_server(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            sid = c.upsert_service({"name": "Sonarr", "type": "sonarr", "url": "http://127.0.0.1:8989", "api_key": "secret"})
            with self.assertRaises(ConfigError):
                c.upsert_service({"id": sid, "name": "Sonarr", "type": "sonarr", "url": "http://attacker.example:8989"})
            c.upsert_service({"id": sid, "name": "Sonarr", "type": "sonarr", "url": "http://127.0.0.1:8989/"})  # same server
            self.assertEqual(c.service(sid)["api_key"], "secret")
            c.update_general({"watch": {"channel": {"kind": "ntfy", "url": "https://ntfy.sh/t", "token": "tok"}}})
            c.update_general({"watch": {"channel": {"url": "https://attacker.example/t"}}})
            self.assertEqual(c.data["watch"]["channel"]["token"], "")

    def test_redirects_do_not_carry_keys_to_another_server(self):
        seen = {}

        class Other(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                seen["auth"] = self.headers.get("X-Api-Key")
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

        other = ThreadingHTTPServer(("127.0.0.1", 0), Other)
        threading.Thread(target=other.serve_forever, daemon=True).start()

        class Bounce(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{other.server_port}/x")
                self.end_headers()

        bounce = ThreadingHTTPServer(("127.0.0.1", 0), Bounce)
        threading.Thread(target=bounce.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{bounce.server_port}/", headers={"X-Api-Key": "secret"})
            urllib.request.urlopen(req, timeout=5).read()
            self.assertIsNone(seen.get("auth"))
        finally:
            other.shutdown()
            bounce.shutdown()
        self.assertTrue(services.TIMEOUT)  # the opener is installed when services is imported

    def test_container_labels_cannot_run_commands(self):
        self.assertEqual(containers._compose("x; rm -rf /", "stack", "/home/a/b", "/home/a/b/c.yml")["service"], "")
        self.assertEqual(containers._compose("svc", "p", "/", "/c.yml")["folder"], "")
        self.assertEqual(containers._compose("svc", "p", "/home/a/b", "/etc/c.yml")["files"], [])
        self.assertEqual(containers._compose("svc", "p", "/home/a/b", "/home/a/b/c.yml")["service"], "svc")

    def test_channel_data_cannot_add_playlist_lines(self):
        line = livetv._entry('a"\nhttp://evil', {"name": 'Bad\n#EXTINF:-1,Evil\nhttp://evil', "logo": "file:///etc/passwd"}, 1, "News\n", "http://x/y.m3u8")
        self.assertEqual(line.count("\n"), 1)
        self.assertIn('tvg-logo=""', line)
        with self.assertRaises(ValueError):
            livetv.fetch("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
