"""A lighter server (DASH-79): kept-alive connections, files that are kept for a year once their link carries their
hash, and a connection closed when a request's body was not read."""

import http.client
import os
import re
import tempfile
import threading
import unittest

from starboard.server import make_server


class LighterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        for k in ("STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def conn(self):
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)

    def get(self, c, path, headers=None):
        c.request("GET", path, headers={"Host": f"127.0.0.1:{self.port}", **(headers or {})})
        r = c.getresponse()
        return r, r.read()

    def test_one_connection_carries_several_requests(self):
        c = self.conn()
        r1, _ = self.get(c, "/login.html")
        r2, _ = self.get(c, "/css/tokens.css")
        self.assertEqual((r1.status, r2.status), (200, 200))
        self.assertFalse(r2.will_close)
        self.assertEqual(r2.version, 11)
        c.close()

    def test_a_page_links_its_files_with_their_hash_and_they_are_kept(self):
        c = self.conn()
        _, page = self.get(c, "/login.html")
        link = re.search(rb'href="(/css/tokens\.css\?v=([0-9a-f]+))"', page)
        self.assertIsNotNone(link)
        r, _ = self.get(c, link.group(1).decode())
        self.assertIn("immutable", r.getheader("Cache-Control"))
        self.assertEqual(r.getheader("ETag").strip('"'), link.group(2).decode())
        # Without the hash, or with an old one, the file is checked again each time as before.
        r, _ = self.get(c, "/css/tokens.css?v=0000")
        self.assertEqual(r.getheader("Cache-Control"), "no-cache")
        # The page itself is always checked again, so a new version shows at once.
        r, _ = self.get(c, "/login.html")
        self.assertEqual(r.getheader("Cache-Control"), "no-cache")
        c.close()

    def test_the_font_link_inside_the_styles_carries_its_hash(self):
        c = self.conn()
        _, css = self.get(c, "/css/tokens.css", {"Accept-Encoding": "identity"})
        self.assertRegex(css, rb'url\("\.\./fonts/[\w.-]+\.woff2\?v=[0-9a-f]+"\)')
        c.close()

    def test_a_body_nobody_read_closes_the_connection(self):
        c = self.conn()
        body = b'{"password": "x"}'
        # Refused before its body is read (it did not come from the dashboard): the connection must close.
        c.request("POST", "/api/login", body=body, headers={"Host": f"127.0.0.1:{self.port}", "Origin": "http://elsewhere.example",
                                                           "Content-Type": "application/json", "X-Starboard": "1"})
        r = c.getresponse()
        r.read()
        self.assertTrue(r.will_close)
        c.close()

    def test_a_small_body_nobody_read_is_dropped_and_the_connection_goes_on(self):
        c = self.conn()
        c.request("POST", "/api/logout", body=b'{"unused": true}', headers={"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "X-Starboard": "1"})
        r = c.getresponse()
        r.read()
        r2, _ = self.get(c, "/login.html")
        self.assertEqual(r2.status, 200)
        c.close()

    def test_pythons_own_error_answers_carry_the_security_headers(self):
        c = self.conn()
        c.request("PATCH", "/setup.html", headers={"Host": f"127.0.0.1:{self.port}"})
        r = c.getresponse()
        r.read()
        self.assertEqual(r.status, 501)
        self.assertIn("default-src", r.getheader("Content-Security-Policy") or "")
        self.assertTrue(r.will_close)
        c.close()

    def test_only_slide_out_pages_may_be_framed_and_a_cached_answer_says_so_too(self):
        # Still to set up shows its steps' pages in a slide-out (a frame from Starboard itself); other pages refuse.
        from unittest import mock
        from starboard import server
        with mock.patch.object(server.Handler, "signed_in", return_value=True), \
                mock.patch.object(type(self.app), "needs_setup", new_callable=mock.PropertyMock, return_value=False):
            c = self.conn()
            r, _ = self.get(c, "/settings-reelix.html")
            self.assertEqual(r.getheader("X-Frame-Options"), "SAMEORIGIN")
            self.assertIn("frame-ancestors 'self'", r.getheader("Content-Security-Policy"))
            again, _ = self.get(c, "/settings-reelix.html", {"If-None-Match": r.getheader("ETag")})
            self.assertEqual((again.status, again.getheader("X-Frame-Options")), (304, "SAMEORIGIN"))
            other, _ = self.get(c, "/dashboard.html")
            self.assertEqual(other.getheader("X-Frame-Options"), "DENY")
            c.close()

    def test_make_the_change_now_needs_the_password_and_the_run_first_window(self):
        # The set-up's change to the server (owner, 10 November 2026): a request the Run first window picks up.
        import json as j
        from unittest import mock
        from starboard import server, stack
        folder = stack.folder(self.tmp.name)
        with mock.patch.object(server.Handler, "signed_in", return_value=True), \
                mock.patch.object(type(self.app), "needs_setup", new_callable=mock.PropertyMock, return_value=False), \
                mock.patch.object(server.Handler, "check_password", return_value=None) as pw, \
                mock.patch.object(stack, "starter_waiting", return_value=True):
            c = self.conn()
            post = lambda: (c.request("POST", "/api/setup/host/apply", j.dumps({"password": "made-up"}),  # noqa: E731
                                      {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "X-Starboard": "1",
                                       "Origin": f"http://127.0.0.1:{self.port}"}), c.getresponse())[1]
            r = post()
            r.read()
            self.assertEqual(r.status, 400)  # nothing to change yet
            with open(os.path.join(self.tmp.name, "setup-host.json"), "w") as f:
                j.dump({"args": ["--disk-health"]}, f)
            r = post()
            r.read()
            self.assertEqual(r.status, 200)
            self.assertTrue(pw.called)
            self.assertTrue(os.path.exists(os.path.join(folder, "host-request")))
            r, body = self.get(c, "/api/setup/host/progress")
            self.assertEqual(j.loads(body)["state"], "waiting")
            with open(os.path.join(folder, "host-progress.json"), "w") as f:
                j.dump({"state": "running", "n": 2, "of": 3, "name": "Installing smartmontools"}, f)
            r, body = self.get(c, "/api/setup/host/progress")
            self.assertEqual((j.loads(body)["n"], j.loads(body)["name"]), (2, "Installing smartmontools"))
            c.close()

    def test_a_second_set_up_keeps_the_apps_starboard_installed(self):
        # VM test F4: running apps of Starboard's own install stay in Basics, or the next start would stop them.
        import json as j
        from unittest import mock
        from starboard import server, stack
        overview = {"apps": [{"key": "jellyfin", "installed": True}, {"key": "sonarr", "installed": True}]}
        with mock.patch.object(server.Handler, "signed_in", return_value=True), \
                mock.patch.object(type(self.app), "needs_setup", new_callable=mock.PropertyMock, return_value=False), \
                mock.patch.object(server.Handler, "stack_overview", return_value=overview), \
                mock.patch.object(stack, "chosen_keys", return_value=["jellyfin", "reelix"]):
            c = self.conn()
            c.request("POST", "/api/stack/install", j.dumps({"install": "basics"}),
                      {"Host": f"127.0.0.1:{self.port}", "Content-Type": "application/json", "X-Starboard": "1", "Origin": f"http://127.0.0.1:{self.port}"})
            r = c.getresponse()
            body = j.loads(r.read())
            c.close()
        self.assertEqual(r.status, 200)
        self.assertIn("jellyfin", body["apps"])  # Starboard's own, running: kept


if __name__ == "__main__":
    unittest.main()
