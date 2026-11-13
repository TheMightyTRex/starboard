"""Bring in a folder with your own details (DASH-322), behind a check for Reelix RFX-90's route."""
import base64
import http.server
import json
import threading
import unittest
from unittest import mock

from starboard import own_details


class Reelix(http.server.BaseHTTPRequestHandler):
    has_route = True
    asked = 0
    seen = []

    def _send(self, body, code=200):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/api/v1/openapi.json":
            Reelix.asked += 1
            return self._send({"paths": {"/api/v1/customitems": {"post": {}}} if Reelix.has_route else {"/api/v1/movies": {"post": {}}}})
        self._send({"message": "no"}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Reelix.seen.append((self.path, body))
        if self.path == "/api/v1/customitems":
            if str(body.get("path")).endswith("/taken"):
                return self._send({"message": "that folder already belongs to an item"}, 409)
            return self._send({"id": 5, "kind": body["kind"], "title": body["title"]}, 201)
        self._send({"message": "no"}, 404)

    def log_message(self, *a):
        pass


class OwnDetails(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Reelix)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        self.addCleanup(self.srv.server_close)
        self.cfg = mock.Mock(data={"services": [{"type": "link", "icon": "reelix", "api_key": "k",
                                                 "url": f"http://127.0.0.1:{self.srv.server_address[1]}"}]})
        own_details.forget()
        self.addCleanup(own_details.forget)
        Reelix.has_route, Reelix.asked, Reelix.seen = True, 0, []

    def test_shown_only_when_reelix_lists_the_route_and_asked_once_in_ten_minutes(self):
        Reelix.has_route = False
        self.assertFalse(own_details.available(self.cfg, now=1000))
        Reelix.has_route = True
        self.assertFalse(own_details.available(self.cfg, now=1500))  # remembered
        self.assertTrue(own_details.available(self.cfg, now=1700))  # asked again after ten minutes
        self.assertEqual(Reelix.asked, 2)
        self.assertFalse(own_details.available(mock.Mock(data={"services": []})))

    def test_the_details_are_checked(self):
        self.assertEqual(own_details.clean("radio", {"title": "  The  Night Shed ", "year": "2004", "station": "Example FM"}),
                         {"title": "The Night Shed", "year": 2004, "station": "Example FM"})
        self.assertNotIn("station", own_details.clean("films", {"title": "Home movies", "station": "x"}))
        for bad, said in (({}, "Type a title"), ({"title": "A", "year": "04"}, "four numbers"),
                          ({"title": "A", "image_url": "javascript:alert(1)"}, "https://"),
                          ({"title": "A", "image_data": "data:image/svg+xml;base64,PHN2Zz4="}, "PNG, JPEG or WebP")):
            with self.assertRaisesRegex(ValueError, said):
                own_details.clean("films", bad)
        big = "data:image/png;base64," + base64.b64encode(b"x" * (own_details.PICTURE_MAX + 1)).decode()
        with self.assertRaisesRegex(ValueError, "larger than 5 MB"):
            own_details.clean("films", {"title": "A", "image_data": big})
        with self.assertRaisesRegex(ValueError, "work for films"):
            own_details.clean("wanted", {"title": "A"})

    def test_run_sends_own_details_to_reelix_and_the_rest_to_the_import(self):
        matched = mock.Mock(return_value={"added": 1, "errors": []})
        items = [{"path": "/data/media/movies/Arrival (2016)", "tmdb_id": 329865},
                 {"path": "/data/media/movies/home movies", "own": {"title": "Home movies", "year": "2004", "image_url": "https://example.com/a.jpg"}},
                 {"path": "/data/media/movies/taken", "own": {"title": "Taken"}}]
        out = own_details.run(self.cfg, "films", 1, items, matched)
        matched.assert_called_once_with([items[0]])
        self.assertEqual(out["added"], 2)
        self.assertEqual(out["errors"], [{"path": "/data/media/movies/taken", "title": "/data/media/movies/taken",
                                          "message": "that folder already belongs to an item"}])
        self.assertEqual(Reelix.seen[0], ("/api/v1/customitems", {"kind": "movie", "title": "Home movies", "year": 2004,
                                                                   "image_url": "https://example.com/a.jpg", "monitored": False,
                                                                   "root_folder_id": 1, "path": "/data/media/movies/home movies"}))

    def test_radio_sends_the_audiobookshelf_item(self):
        own_details.run(self.cfg, "radio", None, [{"key": "li_x", "title": "The Night Shed", "own": {"title": "The Night Shed", "station": "Example FM"}}],
                        mock.Mock())
        self.assertEqual(Reelix.seen[-1][1], {"kind": "radio_show", "title": "The Night Shed", "station": "Example FM", "monitored": False,
                                              "abs_item_id": "li_x"})

    def test_own_details_are_refused_when_reelix_has_no_route(self):
        Reelix.has_route = False
        with self.assertRaisesRegex(ValueError, "cannot bring in a folder with your own details yet"):
            own_details.run(self.cfg, "music", 5, [{"path": "/m/x", "own": {"title": "X"}}], mock.Mock())


if __name__ == "__main__":
    unittest.main()
