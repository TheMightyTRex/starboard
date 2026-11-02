"""Moving to Jellyfin and Live TV, against a made-up Jellyfin."""

import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import livetv, migrate


class FakeJellyfin(BaseHTTPRequestHandler):
    played, positions, prefs = [], [], {}

    def log_message(self, *a):
        pass

    def reply(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/Users":
            return self.reply([{"Name": "alex", "Id": "u1"}])
        if path == "/Items":
            return self.reply({"Items": [
                {"Id": "m1", "Type": "Movie", "ProviderIds": {"Tmdb": "603"}, "UserData": {}},
                {"Id": "e1", "Type": "Episode", "SeriesId": "s1", "ParentIndexNumber": 1, "IndexNumber": 2, "UserData": {}},
                {"Id": "m2", "Type": "Movie", "ProviderIds": {"Imdb": "tt0000001"}, "UserData": {}}]})
        if path == "/Items/s1":
            return self.reply({"ProviderIds": {"Tvdb": "81189"}})
        if path.startswith("/DisplayPreferences"):
            return self.reply({"CustomPrefs": dict(FakeJellyfin.prefs)})
        return self.reply({})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"null") if n else None
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/UserPlayedItems/"):
            FakeJellyfin.played.append(path.rsplit("/", 1)[1])
        elif path.startswith("/UserItems/"):
            FakeJellyfin.positions.append((path.split("/")[2], body["PlaybackPositionTicks"]))
        elif path.startswith("/DisplayPreferences"):
            FakeJellyfin.prefs = body["CustomPrefs"]
        return self.reply({})


class JellyfinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeJellyfin)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.services = [{"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": f"http://127.0.0.1:{cls.server.server_port}", "api_key": "k"}]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_import_file_then_apply_once(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "old.json")
            with open(src, "w") as f:
                json.dump({"accounts": {"Alex": [
                    {"type": "movie", "watched": True, "last_watched": "2025-01-01T00:00:00+00:00", "ids": {"tmdb": "603"}},
                    {"type": "episode", "watched": False, "position_ms": 60000, "season": 1, "episode": 2, "ids": {"tvdb": "81189"}}]}}, f)
            migrate.save_history(d, "History file", migrate.read_file(src))
            st = migrate.status(d, self.services)
            self.assertEqual(st["accounts"][0]["suggested"], "alex")
            migrate.set_mapping(d, {"Alex": "alex"})
            FakeJellyfin.played, FakeJellyfin.positions = [], []
            self.assertIn("Marked 1", migrate.apply(d, self.services))
            self.assertEqual(FakeJellyfin.played, ["m1"])
            self.assertEqual(FakeJellyfin.positions, [("e1", 600000000)])
            migrate.apply(d, self.services)  # applied once only
            self.assertEqual(FakeJellyfin.played, ["m1"])

    def test_user_defaults_keep_a_users_choice(self):
        FakeJellyfin.prefs = {}
        self.assertIn("alex", migrate.ensure_defaults(self.services))
        self.assertEqual(FakeJellyfin.prefs["landing-livetv"], "guide")
        FakeJellyfin.prefs = {"landing-livetv": "channels"}
        self.assertIn("already", migrate.ensure_defaults(self.services))
        self.assertEqual(FakeJellyfin.prefs["landing-livetv"], "channels")

    def test_numbering_by_category_without_white_logos(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "samsung.m3u"), "w") as f:
                f.write('#EXTM3U\n#EXTINF:-1 tvg-id="a" tvg-logo="https://x/a.png" tvg-chno="5" group-title="Samsung UK · News",Daily News\nhttps://x/a.m3u8\n'
                        '#EXTINF:-1 tvg-id="b" tvg-logo="" tvg-chno="6" group-title="Samsung UK · Movies",Film Four Ever\nhttps://x/b.m3u8\n')
            os.environ["STARBOARD_IPTV_DIR"] = d
            try:
                self.assertIn("Numbered 2", livetv.number_and_logos(d, "http://starboard:8090", white=False))
            finally:
                del os.environ["STARBOARD_IPTV_DIR"]
            with open(os.path.join(d, "samsung.m3u")) as f:
                text = f.read()
            self.assertIn('tvg-chno="701"', text)
            self.assertIn('tvg-chno="451"', text)
            self.assertIn('tvg-logo="https://x/a.png"', text)  # no white logo made: its own logo stays

    def test_pluto_ids_are_checked(self):
        with self.assertRaises(ValueError):
            livetv.pluto_url("../../etc")


if __name__ == "__main__":
    unittest.main()
