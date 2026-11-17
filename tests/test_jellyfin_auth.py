"""Jellyfin 12 with legacy authorisation off (DASH-458): the key in X-Emby-Token alone is refused with 401, so every
call Starboard makes to Jellyfin sends it in Authorization too. A stand-in that refuses X-Emby-Token alone still
answers the plug-in libraries and poster checks."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import jellyfin_metadata, plugin_libraries

KEY = "jf-key"


class Jellyfin12(BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.seen.append(dict(self.headers))
        if self.headers.get("Authorization") != f'MediaBrowser Token="{KEY}"':  # EnableLegacyAuthorization off
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path.startswith("/Items?"):
            raw = json.dumps({"Items": [{"Id": "a1"}, {"Id": "b2"}]}).encode()
        elif "/Images/Primary" in self.path:
            raw = b"\x89PNG"
        else:
            raw = json.dumps([{"Name": "Films", "Locations": ["/media/films"]}]).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class LegacyAuthorisationOff(unittest.TestCase):
    def setUp(self):
        Jellyfin12.seen = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Jellyfin12)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.service = {"type": "jellyfin", "url": self.url, "api_key": KEY}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_plugin_libraries_call_is_answered(self):
        got = plugin_libraries._call(self.service, "GET", "/Library/VirtualFolders")
        self.assertEqual(got[0]["Name"], "Films")
        self.assertEqual(Jellyfin12.seen[0].get("X-Emby-Token"), KEY)  # kept for older Jellyfin and Emby

    def test_poster_check_is_answered(self):
        self.assertEqual(jellyfin_metadata.check_posters([self.service]), "2 of 2 sampled posters load")

    def test_stand_in_refuses_the_legacy_header_alone(self):
        from starboard import app_setup
        with self.assertRaises(app_setup.AppSetupError):
            app_setup._call(self.url, "GET", "/Library/VirtualFolders", headers={"X-Emby-Token": KEY})


if __name__ == "__main__":
    unittest.main()
