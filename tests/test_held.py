"""Held downloads (DASH-210): Reelix's /pending, Get it now and Remove, with the manager key."""
import http.server
import json
import threading
import unittest

from starboard import held


class Reelix(http.server.BaseHTTPRequestHandler):
    seen = []
    rows = []

    def _send(self, body, code=200):
        raw = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        assert self.headers["X-Api-Key"] == "manager-key"
        if self.path == "/api/v1/pending":
            return self._send(Reelix.rows)
        self._send({"message": "no"}, 404)

    def do_POST(self):
        Reelix.seen.append(("POST", self.path))
        if self.path == "/api/v1/pending/7/grab":
            return self._send({"queue_id": 3, "download_client": "qBittorrent", "download_id": "abc"})
        self._send({"message": "pending release not found"}, 404)

    def do_DELETE(self):
        Reelix.seen.append(("DELETE", self.path))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


class Held(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Reelix)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        self.addCleanup(self.srv.server_close)
        self.svcs = [{"id": "r", "name": "Reelix", "type": "link", "icon": "reelix", "api_key": "manager-key",
                      "url": f"http://127.0.0.1:{self.srv.server_address[1]}"}]
        Reelix.seen = []
        Reelix.rows = [
            {"id": 8, "title": "Later.Film.2019.1080p", "media": {"kind": "movie", "id": 1, "title": "Later Film", "year": 2019},
             "episodes": [], "quality": {"quality": "WEBDL-1080p"}, "indexer": "Example", "protocol": "torrent",
             "reason": "preferred_protocol", "added": "2026-11-13T01:00:00Z", "release_at": "2026-11-13T09:00:00Z"},
            {"id": 7, "title": "Harbour.Lights.S02E03.720p", "media": {"kind": "series", "id": 2, "title": "Harbour Lights", "year": 2018},
             "episodes": [{"id": 1, "season_number": 2, "episode_number": 3}], "quality": {"quality": "HDTV-720p"},
             "indexer": "Example Usenet", "protocol": "usenet", "reason": "delay", "added": "2026-11-13T02:00:00Z",
             "release_at": "2026-11-13T05:00:00Z"}]

    def test_listing_in_words_soonest_first(self):
        out = held.listing(self.svcs)
        self.assertTrue(out["available"])
        first = out["items"][0]
        self.assertEqual((first["id"], first["what"], first["quality"], first["site"], first["reason"]),
                         (7, "Harbour Lights (2018), S02E03", "HDTV-720p", "Example Usenet", "Waiting for the delay to pass"))
        self.assertEqual(out["items"][1]["reason"], "Waiting for the preferred kind of download")

    def test_get_it_now_and_remove(self):
        self.assertEqual(held.grab(self.svcs, 7), {"said": "Sent to qBittorrent", "client": "qBittorrent"})
        held.remove(self.svcs, 8)
        self.assertEqual(Reelix.seen, [("POST", "/api/v1/pending/7/grab"), ("DELETE", "/api/v1/pending/8")])

    def test_no_reelix_says_so(self):
        self.assertEqual(held.listing([]), {"available": False, "items": []})
        with self.assertRaisesRegex(ValueError, "Reelix is not on your dashboard"):
            held.grab([], 7)


if __name__ == "__main__":
    unittest.main()
