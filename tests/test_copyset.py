"""Copying settings between two Sonarrs: ids matched again by name, hidden passwords, nothing overwritten."""

import json
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import copyset


class FakeSonarr(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def part(self):
        u = urllib.parse.urlparse(self.path)
        return u.path.removeprefix("/api/v3/"), urllib.parse.parse_qs(u.query)

    def do_GET(self):
        if self.headers.get("X-Api-Key") != "key":
            return self.reply(401, {})
        part, _ = self.part()
        if part == "system/status":
            return self.reply(200, {"version": self.server.version})
        self.reply(200, self.server.state.get(part, []))

    def do_POST(self):
        part, query = self.part()
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if part == "rootfolder" and body["path"].startswith("/missing"):
            return self.reply(400, [{"errorMessage": "Folder does not exist"}])
        self.server.posts.append((part, body, query))
        items = self.server.state.setdefault(part, [])
        body["id"] = max([i["id"] for i in items] + [100]) + 1
        items.append(body)
        self.reply(201, body)

    def do_PUT(self):
        part, _ = self.part()
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.state[part.rsplit("/", 1)[0]] = body
        self.reply(202, body)


def serve(state, version="4.0.16"):
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSonarr)
    server.state, server.posts, server.version = state, [], version
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, {"id": f"s{server.server_address[1]}", "name": f"Sonarr {server.server_address[1]}", "type": "sonarr",
                    "url": f"http://127.0.0.1:{server.server_address[1]}", "api_key": "key"}


OLD = {
    "tag": [{"id": 1, "label": "kids"}, {"id": 2, "label": "4k"}],
    "customformat": [{"id": 5, "name": "x265", "specifications": []}, {"id": 6, "name": "Remux", "specifications": []}],
    "qualityprofile": [{"id": 3, "name": "HD", "items": [], "formatItems": [{"format": 5, "name": "x265", "score": 50}]},
                       {"id": 4, "name": "Any", "items": [], "formatItems": []}],
    "rootfolder": [{"id": 1, "path": "/tv"}, {"id": 2, "path": "/missing/anime"}],
    "downloadclient": [{"id": 1, "name": "qBittorrent", "implementation": "QBittorrent", "enable": True, "tags": [1],
                        "fields": [{"name": "host", "value": "qbit"}, {"name": "password", "label": "Password", "value": "********"}]},
                       {"id": 2, "name": "SABnzbd", "implementation": "Sabnzbd", "enable": True, "tags": [],
                        "fields": [{"name": "apiKey", "label": "API Key", "value": "********"}]}],
    "remotepathmapping": [{"id": 1, "host": "qbit", "remotePath": "/downloads/", "localPath": "/data/downloads/"}],
    "config/naming": {"id": 1, "renameEpisodes": True, "standardEpisodeFormat": "{Series Title} - S{season:00}E{episode:00}"},
    "config/mediamanagement": {"id": 1, "copyUsingHardlinks": True},
}


class CopyTest(unittest.TestCase):
    def setUp(self):
        self.old, self.source = serve(json.loads(json.dumps(OLD)))
        self.new, self.target = serve({"tag": [{"id": 7, "label": "Kids"}], "qualityprofile": [{"id": 9, "name": "Any", "items": [], "formatItems": []}],
                                       "config/naming": {"id": 1, "renameEpisodes": False}, "config/mediamanagement": {"id": 1}})

    def tearDown(self):
        for s in (self.old, self.new):
            s.shutdown()
            s.server_close()

    def test_preview_says_what_happens(self):
        p = copyset.preview(self.source, self.target, list(copyset.PARTS))
        by = {part["part"]: part["items"] for part in p["parts"]}
        self.assertEqual([(i["name"], i["state"]) for i in by["tags"]], [("kids", "there"), ("4k", "add")])
        self.assertEqual(by["clients"][0]["needs"], [{"field": "password", "label": "Password"}])
        self.assertEqual(by["naming"], [{"name": "Naming", "state": "replace"}])

    def test_copy_matches_ids_and_keeps_what_is_there(self):
        r = copyset.apply(self.source, self.target, list(copyset.PARTS), {"qBittorrent": {"password": "secret"}})
        state = self.new.state
        self.assertEqual(sorted(t["label"] for t in state["tag"]), ["4k", "Kids"])  # kids matched Kids, not added twice
        self.assertEqual({p["name"] for p in state["qualityprofile"]}, {"Any", "HD"})
        hd = next(p for p in state["qualityprofile"] if p["name"] == "HD")
        new_x265 = next(f["id"] for f in state["customformat"] if f["name"] == "x265")
        self.assertIn({"format": new_x265, "name": "x265", "score": 50}, hd["formatItems"])
        qbit = next(c for c in state["downloadclient"] if c["name"] == "qBittorrent")
        self.assertEqual(qbit["tags"], [7])
        self.assertIn({"name": "password", "label": "Password", "value": "secret"}, qbit["fields"])
        self.assertTrue(qbit["enable"])
        sab = next(c for c in state["downloadclient"] if c["name"] == "SABnzbd")
        self.assertFalse(sab["enable"])  # no key given: added switched off
        self.assertTrue(all(q.get("forceSave") == ["true"] for part, _, q in self.new.posts if part == "downloadclient"))
        self.assertEqual(state["config/naming"]["standardEpisodeFormat"], OLD["config/naming"]["standardEpisodeFormat"])
        self.assertEqual([f["path"] for f in state["rootfolder"]], ["/tv"])
        self.assertEqual(len(r["problems"]), 1)
        self.assertIn("/missing/anime", r["problems"][0])
        self.assertIn("1 switched off until you add the password", " ".join(r["lines"]))

        # A second copy adds nothing more
        before = len(self.new.posts)
        copyset.apply(self.source, self.target, ["tags", "formats", "profiles", "clients"])
        self.assertEqual(len(self.new.posts), before)

    def test_refuses_different_versions_and_kinds(self):
        self.new.version = "3.0.10"
        with self.assertRaisesRegex(ValueError, "same major version"):
            copyset.preview(self.source, self.target, ["tags"])
        with self.assertRaisesRegex(ValueError, "same kind"):
            copyset.check(self.source, dict(self.target, type="radarr"))


if __name__ == "__main__":
    unittest.main()
