"""A feature that is going says so on every answer, and one that is gone answers 410 (DASH-603)."""
import http.client
import json
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, deprecations
from starboard.server import make_server

GOING = {"method": "GET", "path": "/api/v1/status", "deprecated": "2027-01-15", "sunset": "2028-01-15",
         "replacement": "Use /api/v1/apps", "link": "https://example.org/change", "removed": False}


class Headers(unittest.TestCase):
    def test_deprecation_is_a_unix_time_and_sunset_an_http_date(self):
        h = deprecations.headers(GOING)
        self.assertEqual(h["Deprecation"], "@1799971200")
        self.assertEqual(h["Sunset"], "Sat, 15 Jan 2028 00:00:00 GMT")
        self.assertEqual(h["Link"], '<https://example.org/change>; rel="deprecation"')

    def test_a_link_that_is_not_https_is_left_out(self):
        self.assertNotIn("Link", deprecations.headers({**GOING, "link": "http://example.org"}))

    def test_a_broken_entry_is_ignored_not_fatal(self):
        with mock.patch.object(deprecations, "_items", None), mock.patch("builtins.open", mock.mock_open(read_data="not json")):
            self.assertEqual(deprecations.items(), [])
        deprecations._items = None

    def test_the_list_that_ships_is_empty(self):
        deprecations._items = None
        self.assertEqual(deprecations.items(), [])
        self.assertEqual(deprecations.public(), [])


class OnTheServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.key, _ = api_v1.create_key(cls.tmp.name, "Test", "read", [], 30)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def get(self, path, key=True):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", path, headers={"Authorization": f"Bearer {self.key}"} if key else {})
        r = c.getresponse()
        body = r.read()
        out = (r.status, dict(r.getheaders()), body)
        c.close()
        return out

    def test_the_root_lists_what_is_going(self):
        with mock.patch.object(deprecations, "_items", [GOING]):
            status, headers, body = self.get("/api/v1/")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["deprecations"][0]["path"], "/api/v1/status")
        status, headers, body = self.get("/api/v1/")
        self.assertEqual(json.loads(body)["deprecations"], [])

    def test_a_route_that_is_going_still_answers_with_the_headers(self):
        with mock.patch.object(deprecations, "_items", [GOING]):
            status, headers, _ = self.get("/api/v1/status")
            self.assertEqual(status, 200)
            self.assertEqual(headers["Deprecation"], "@1799971200")
            self.assertIn("Sunset", headers)
            self.assertNotIn("Deprecation", self.get("/api/v1/me")[1])  # another route is not marked
            self.assertIn("Deprecation", self.get("/api/v1/status", key=False)[1])  # even a refused call is told

    def test_a_removed_route_answers_410_with_what_replaces_it(self):
        with mock.patch.object(deprecations, "_items", [{**GOING, "removed": True}]):
            status, headers, body = self.get("/api/v1/status")
        self.assertEqual(status, 410)
        self.assertEqual(json.loads(body)["code"], "gone")
        self.assertIn("/api/v1/apps", json.loads(body)["detail"])
        self.assertIn("rel=\"deprecation\"", headers["Link"])


if __name__ == "__main__":
    unittest.main()
