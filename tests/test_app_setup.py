"""Jellyfin's and Audiobookshelf's first runs over their own APIs (DASH-179, DASH-180, DASH-181), against small
stand-ins that answer like the real apps did on 9 November 2026 (Jellyfin 10.12, Audiobookshelf 2.37)."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import app_setup

PASSWORD = "made-up-test-password-42"


class Stand(BaseHTTPRequestHandler):
    state = None

    def log_message(self, *a):
        pass

    def answer(self, code, body=None):
        raw = json.dumps(body).encode() if body is not None else b""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"null") if n else None

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")


class Jellyfin(Stand):
    def route(self, method):
        s, path = self.state, self.path
        body = self.body() if method == "POST" else None
        if path == "/System/Info/Public":
            return self.answer(200, {"StartupWizardCompleted": s["done"]})
        if path.startswith("/Startup/"):
            if s["done"]:
                return self.answer(401)
            if path == "/Startup/User" and method == "POST":
                s["user"] = (body["Name"], body["Password"])
            if path == "/Startup/Complete":
                s["done"] = True
            return self.answer(204)
        if path == "/Users/AuthenticateByName":
            return self.answer(200, {"AccessToken": "jf-token"}) if s.get("user") == (body["Username"], body["Pw"]) else self.answer(401)
        if 'Token="jf-token"' not in (self.headers.get("Authorization") or ""):
            return self.answer(401)
        if path == "/Library/VirtualFolders" and method == "GET":
            return self.answer(200, [{"Name": n, "Locations": [p]} for n, p in s["libraries"]])
        if path.startswith("/Library/VirtualFolders?"):
            name = path.split("name=")[1].split("&")[0]
            s["libraries"].append((name, body["LibraryOptions"]["PathInfos"][0]["Path"]))
            return self.answer(204)
        if path == "/Auth/Keys" and method == "GET":
            return self.answer(200, {"Items": [{"AppName": "Starboard", "AccessToken": "jf-key"}] if s.get("key") else []})
        if path.startswith("/Auth/Keys?"):
            s["key"] = True
            return self.answer(204)
        return self.answer(404)


class Audiobookshelf(Stand):
    def route(self, method):
        s, path = self.state, self.path
        body = self.body() if method == "POST" else None
        if path == "/status":
            return self.answer(200, {"isInit": s["init"]})
        if path == "/init":
            s["init"], s["user"] = True, (body["newRoot"]["username"], body["newRoot"]["password"])
            return self.answer(200, {})
        if path == "/login":
            ok = s.get("user") == (body["username"], body["password"])
            return self.answer(200, {"user": {"id": "root", "accessToken": "abs-token"}}) if ok else self.answer(401)
        if self.headers.get("Authorization") != "Bearer abs-token":
            return self.answer(401)
        if path == "/api/libraries" and method == "GET":
            return self.answer(200, {"libraries": [{"id": f"lib{i}", "name": n, "mediaType": t, "folders": [{"fullPath": p}]}
                                                   for i, (n, t, p) in enumerate(s["libraries"])]})
        if path == "/api/libraries":
            s["libraries"].append((body["name"], body["mediaType"], body["folders"][0]["fullPath"]))
            return self.answer(200, {})
        if path == "/api/api-keys":
            return self.answer(200, {"apiKey": {"id": "k1", "apiKey": "abs-key"}})
        return self.answer(404)


def serve(handler, state):
    handler.state = state
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


class FirstRuns(unittest.TestCase):
    def test_jellyfin_from_new_to_libraries_and_a_key_and_again_changes_nothing(self):
        state = {"done": False, "libraries": []}
        srv, base = serve(Jellyfin, state)
        self.addCleanup(srv.shutdown)
        key, done, _ = app_setup.jellyfin_first_run(base, PASSWORD, {"movies", "tv"})
        self.assertEqual(key, "jf-key")
        self.assertEqual(state["user"], ("admin", PASSWORD))
        self.assertEqual(state["libraries"], [("Films", "/data/media/movies"), ("Series", "/data/media/tv")])
        self.assertEqual(len(done), 3)
        _, again, _ = app_setup.jellyfin_first_run(base, PASSWORD, {"movies", "tv"})
        self.assertEqual(again, [])

    def test_jellyfin_set_up_by_someone_else_says_what_to_do(self):
        state = {"done": True, "libraries": [], "user": ("someone", "other")}
        srv, base = serve(Jellyfin, state)
        self.addCleanup(srv.shutdown)
        with self.assertRaisesRegex(app_setup.AppSetupError, "Manage apps"):
            app_setup.jellyfin_first_run(base, PASSWORD, {"movies"})

    def test_audiobookshelf_libraries_key_and_the_radio_library(self):
        state = {"init": False, "libraries": []}
        srv, base = serve(Audiobookshelf, state)
        self.addCleanup(srv.shutdown)
        key, done, found = app_setup.audiobookshelf_first_run(base, PASSWORD, {"audiobooks", "radio"})
        self.assertEqual(key, "abs-key")
        self.assertEqual(state["libraries"], [("Audiobooks", "book", "/media/audiobooks"), ("Radio", "podcast", "/media/radio")])
        self.assertEqual(found["radio_library"], "lib1")
        self.assertEqual(len(done), 3)

    def test_radio_settings_point_reelix_at_the_library(self):
        class FakeReelix:
            def __init__(self):
                self.put = None

            def call(self, method, path, body=None):
                if method == "GET":
                    return 200, {"country": None, "language": None, "max_lookups_per_refresh": 20}
                self.put = body
                return 200, body
        r = FakeReelix()
        app_setup.radio_settings(r, {"radio_library": "lib1"})
        self.assertEqual(r.put["abs_library_id"], "lib1")
        self.assertEqual(r.put["library_folder"], "/data/media/radio")
        self.assertEqual(r.put["max_lookups_per_refresh"], 20)
        self.assertEqual(app_setup.radio_settings(r, {}), [])


if __name__ == "__main__":
    unittest.main()
