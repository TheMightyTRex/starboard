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


if __name__ == "__main__":
    unittest.main()
