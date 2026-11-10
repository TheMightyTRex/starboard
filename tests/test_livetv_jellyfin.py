"""Live TV added to Jellyfin over its API (DASH-229), against a stand-in that answers like Jellyfin 10.11."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import livetv_jellyfin as lj

ENV = {"CONFIG_DIR": "/srv/apps", "DATA_DIR": "/srv/data"}


class Jellyfin(BaseHTTPRequestHandler):
    state = None

    def log_message(self, *a):
        pass

    def answer(self, code, body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        s = self.state
        if self.headers.get("Authorization") != 'MediaBrowser Token="jf-key"':  # as Jellyfin 10.11 and later
            return self.answer(401)
        if self.path == "/System/Configuration/livetv":
            return self.answer(200, {"TunerHosts": s["tuners"], "ListingProviders": s["guides"]})
        if self.path.startswith("/ScheduledTasks"):
            return self.answer(200, [{"Id": "t9", "Key": "RefreshGuide"}])
        return self.answer(404)

    def do_POST(self):
        s = self.state
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n)) if n else None
        if self.path == "/LiveTv/TunerHosts":
            s["tuners"].append(body)
        elif self.path.startswith("/LiveTv/ListingProviders"):
            s["guides"].append(body)
        elif self.path == "/ScheduledTasks/Running/t9":
            s["refreshed"] += 1
        else:
            return self.answer(404)
        return self.answer(200, {})


class LiveTvJellyfinTest(unittest.TestCase):
    def setUp(self):
        self.state = {"tuners": [{"Type": "m3u", "Url": "/config/iptv/channels.m3u"}], "guides": [], "refreshed": 0}
        Jellyfin.state = self.state
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Jellyfin)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.services = [{"type": "jellyfin", "url": f"http://127.0.0.1:{srv.server_address[1]}", "api_key": "jf-key"}]
        self.dir = tempfile.mkdtemp()
        for name in ("channels.m3u", "samsung.m3u", "guide.xml", "guide-samsung.xml"):
            open(os.path.join(self.dir, name), "w").close()

    def connect(self, extras=None):
        return lj.connect(self.services, extras or {}, "/unused", local_folder=self.dir, host_path="/srv/apps/jellyfin/iptv", env=ENV)

    def test_where_jellyfin_sees_the_folder(self):
        self.assertEqual(lj.jellyfin_folder({}, "", host_path="/srv/apps/jellyfin/iptv", env=ENV), "/config/iptv")
        self.assertEqual(lj.jellyfin_folder({}, "", host_path="/srv/data/media/tv-guide", env=ENV), "/data/media/tv-guide")
        self.assertIsNone(lj.jellyfin_folder({}, "", host_path="/elsewhere/iptv", env=ENV))
        self.assertEqual(lj.jellyfin_folder({"livetv_jellyfin_folder": "/tv/"}, "", host_path="/elsewhere", env=ENV), "/tv")

    def test_adds_what_is_missing_once_and_keeps_the_rest(self):
        line = self.connect()
        self.assertIn("added 3", line)
        self.assertEqual([t["Url"] for t in self.state["tuners"]], ["/config/iptv/channels.m3u", "/config/iptv/samsung.m3u"])
        self.assertEqual([g["Path"] for g in self.state["guides"]], ["/config/iptv/guide.xml", "/config/iptv/guide-samsung.xml"])
        self.assertEqual(self.state["refreshed"], 1)
        self.assertEqual(self.connect(), "")
        self.assertEqual(self.state["refreshed"], 1)

    def test_the_folder_comes_from_jellyfins_own_tuners(self):
        self.assertEqual(lj.folder_from_jellyfin(self.services), "/config/iptv")
        self.assertIsNone(lj.folder_from_jellyfin([]))

    def test_says_what_is_missing(self):
        self.assertIn("API key", lj.connect([], {}, "", local_folder=self.dir, host_path="", env=ENV))
        self.assertIn("as Jellyfin sees it", lj.connect(self.services, {}, "", local_folder=self.dir, host_path="/elsewhere", env=ENV))


if __name__ == "__main__":
    unittest.main()
