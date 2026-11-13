"""Starboard sets Reelix up over HTTP (reelix_setup), against a small stand-in for Reelix's API that answers the way the
real one does: the set-up token once, then sign-in with a cookie and the cross-site header, a manager role, a key that
is shown once, folders and download apps."""
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import reelix_setup

MANAGER_BITS = 4145150


class FakeReelix:
    def __init__(self):
        self.users = []
        self.keys = {}
        self.folders = {"/rootfolders": [], "/bookrootfolders": [], "/musicrootfolders": []}
        self.clients = []
        self.profiles = [{"id": 1, "tags": [], "preferred_protocol": "usenet"}]
        self.sessions = {}
        self.calls = []


def handler_for(fake):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def reply(self, code, body=None, cookie=None):
            raw = json.dumps(body).encode() if body is not None else b""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            if cookie:
                self.send_header("Set-Cookie", f"reelix_session={cookie}; Path=/")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def who(self):
            key = self.headers.get("X-Api-Key")
            if key:
                return fake.keys.get(key)
            cookie = (self.headers.get("Cookie") or "").replace("reelix_session=", "")
            return fake.sessions.get(cookie)

        def handle_any(self, method):
            path = self.path.replace("/api/v1", "", 1)
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length)) if length else None
            fake.calls.append((method, path))
            user = self.who()
            if method != "GET" and not self.headers.get("X-Api-Key") and path not in ("/setup", "/auth/login") \
                    and not self.headers.get("x-reelix-request"):
                return self.reply(403, {"message": "csrf"})
            if path == "/system/health":
                return self.reply(200, {"ok": True})
            if path == "/setup" and method == "GET":
                return self.reply(200, {"needs_setup": not fake.users, "setup_token_required": True})
            if path == "/setup":
                if fake.users:
                    return self.reply(409, {"message": "set up already"})
                if body.get("setup_token") != "TOKEN123":
                    return self.reply(401, {"message": "bad token"})
                fake.users.append({"id": 1, "username": body["username"], "password": body["password"], "admin": True})
                fake.sessions["s1"] = fake.users[0]
                return self.reply(201, {"id": 1}, cookie="s1")
            if path == "/auth/login":
                u = next((u for u in fake.users if u["username"] == body["username"] and u["password"] == body["password"]), None)
                if not u:
                    return self.reply(401, {"message": "wrong"})
                sid = f"s{len(fake.sessions) + 1}"
                fake.sessions[sid] = u
                return self.reply(200, {"id": u["id"]}, cookie=sid)
            if not user:
                return self.reply(401, {"message": "sign in"})
            if path == "/users/roles":
                # As Reelix 0.8.6 answers: presets with an id, and the permission catalogue.
                return self.reply(200, {"roles": [{"id": "admin", "name": "Admin", "permissions": 1},
                                                  {"id": "manager", "name": "Manager", "permissions": MANAGER_BITS}],
                                        "permissions": [{"bit": 1, "key": "ADMIN", "label": "Admin", "description": ""}]})
            if path == "/users" and method == "GET":
                return self.reply(200, [{"id": u["id"], "username": u["username"]} for u in fake.users])
            if path == "/users":
                fake.users.append({"id": len(fake.users) + 1, "username": body["username"], "password": body["password"],
                                   "permissions": body["permissions"], "admin": False})
                return self.reply(201, {"id": len(fake.users)})
            if path == "/auth/apikeys":
                key = f"key-{user['username']}"
                fake.keys[key] = user
                return self.reply(201, {"api_key": {"id": 1, "name": body["name"], "prefix": key[:4]}, "key": key})  # as Reelix 0.8.6
            if not user.get("admin"):
                return self.reply(403, {"message": "admin only"})
            if path in fake.folders and method == "GET":
                return self.reply(200, fake.folders[path])
            if path in fake.folders:
                fake.folders[path].append(body)
                return self.reply(201, body)
            if path == "/downloadclients" and method == "GET":
                return self.reply(200, fake.clients)
            if path == "/downloadclients":
                fake.clients.append(body)
                return self.reply(201, body)
            if path == "/delayprofiles":
                return self.reply(200, fake.profiles)
            if path.startswith("/delayprofiles/"):
                fake.profiles[0] = body
                return self.reply(200, body)
            return self.reply(404, {"message": path})

        def do_GET(self):
            self.handle_any("GET")

        def do_POST(self):
            self.handle_any("POST")

        def do_PUT(self):
            self.handle_any("PUT")
    return H


class Services:
    def __init__(self):
        self.data = {"services": []}

    def upsert_service(self, s):
        self.data["services"] = [x for x in self.data["services"] if x["name"] != s["name"]] + [s]


class ReelixSetupTest(unittest.TestCase):
    def setUp(self):
        self.fake = FakeReelix()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(self.fake))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, "stack"))
        self.write({"url": self.base, "token": "TOKEN123", "groups": ["movies", "tv", "audiobooks"],
                    "qbittorrent_password": "temp", "qbittorrent_host": "gluetun", "sabnzbd": False})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def write(self, info):
        with open(reelix_setup.setup_file(self.tmp.name), "w") as f:
            json.dump(info, f)

    def test_a_new_reelix_is_set_up_with_a_manager_key(self):
        cfg = Services()
        done = reelix_setup.set_up(cfg, self.tmp.name, "correct horse battery", qbit=lambda temporary: "lasting-pw")
        admin, manager = self.fake.users[0], self.fake.users[1]
        self.assertEqual((admin["username"], admin["password"]), ("admin", "correct horse battery"))
        self.assertEqual(manager["permissions"], MANAGER_BITS)
        self.assertNotEqual(manager["password"], "correct horse battery")
        keys = {s.get("api_key") for s in cfg.data["services"] if s.get("api_key")}
        self.assertEqual(keys, {"key-starboard"})  # the manager's key, never the admin's
        self.assertEqual(sorted(f["path"] for f in self.fake.folders["/rootfolders"]), ["/data/media/movies", "/data/media/tv"])
        self.assertEqual([f["path"] for f in self.fake.folders["/bookrootfolders"]], ["/data/media/audiobooks"])
        self.assertEqual(self.fake.folders["/musicrootfolders"], [])  # music was not chosen
        self.assertEqual(self.fake.clients[0]["settings"]["host"], "gluetun")
        self.assertEqual(self.fake.clients[0]["settings"]["password"], "lasting-pw")
        self.assertEqual(self.fake.profiles[0]["preferred_protocol"], "torrent")
        types = sorted(s["type"] for s in cfg.data["services"])
        self.assertEqual(types, ["link", "radarr", "readarr", "sonarr"])
        self.assertTrue(any(s["url"] == self.base + "/radarr" for s in cfg.data["services"]))
        self.assertFalse(os.path.exists(reelix_setup.setup_file(self.tmp.name)))  # the token file is gone
        self.assertTrue(done)

    def test_nzbget_is_connected_with_the_made_up_sign_in(self):
        self.write({"url": self.base, "token": "TOKEN123", "groups": ["movies"], "usenet": "nzbget",
                    "usenet_host": "gluetun"})
        cfg = Services()
        done = reelix_setup.set_up(cfg, self.tmp.name, "correct horse battery", nzbget=lambda d: ("starboard", "made-up"))
        nz = next(c for c in self.fake.clients if c["implementation"] == "nzbget")
        self.assertEqual((nz["settings"]["host"], nz["settings"]["port"]), ("gluetun", 6789))
        self.assertEqual((nz["settings"]["username"], nz["settings"]["password"]), ("starboard", "made-up"))
        self.assertEqual(self.fake.profiles[0]["preferred_protocol"], "usenet")
        self.assertIn("Connected Reelix to NZBGet", done)

    def test_sabnzbd_is_connected_on_8085_with_the_made_up_key(self):
        os.makedirs(os.path.join(self.tmp.name, "stack"), exist_ok=True)
        with open(os.path.join(self.tmp.name, "stack", ".env"), "a") as f:
            f.write("SABNZBD_API_KEY=" + "a" * 32 + "\n")
        self.write({"url": self.base, "token": "TOKEN123", "groups": ["movies"], "usenet": "sabnzbd",
                    "usenet_host": "gluetun"})
        done = reelix_setup.set_up(Services(), self.tmp.name, "correct horse battery")
        sab = next(c for c in self.fake.clients if c["implementation"] == "sabnzbd")
        self.assertEqual((sab["settings"]["host"], sab["settings"]["port"], sab["settings"]["api_key"]), ("gluetun", 8085, "a" * 32))
        self.assertIn("Connected Reelix to SABnzbd", done)

    def test_running_it_again_changes_nothing_twice(self):
        cfg = Services()
        reelix_setup.set_up(cfg, self.tmp.name, "correct horse battery", qbit=lambda t: "lasting-pw")
        self.write({"url": self.base, "groups": ["movies", "tv", "audiobooks"]})
        reelix_setup.set_up(cfg, self.tmp.name, "correct horse battery")
        self.assertEqual(len(self.fake.users), 2)  # no second manager: Starboard has its key
        self.assertEqual(len(self.fake.folders["/rootfolders"]), 2)
        self.assertEqual(len(self.fake.clients), 1)

    def test_a_wrong_token_says_so(self):
        self.write({"url": self.base, "token": "WRONG", "groups": ["movies"]})
        with self.assertRaises(reelix_setup.ReelixError) as e:
            reelix_setup.set_up(Services(), self.tmp.name, "correct horse battery")
        self.assertIn("401", str(e.exception))

    def test_nothing_to_do_without_the_installers_file(self):
        os.remove(reelix_setup.setup_file(self.tmp.name))
        with self.assertRaises(reelix_setup.ReelixError):
            reelix_setup.set_up(Services(), self.tmp.name, "x")

class NzbgetOptionsTest(unittest.TestCase):
    """NZBGet as linuxserver's image writes it (fixed /downloads folders, a "Series" category) made ready for Reelix."""
    LSIO = [{"Name": "MainDir", "Value": "/data/downloads/usenet"}, {"Name": "DestDir", "Value": "/downloads/completed"},
            {"Name": "InterDir", "Value": "/downloads/intermediate"}, {"Name": "Category1.Name", "Value": "Movies"},
            {"Name": "Category2.Name", "Value": "Series"}, {"Name": "Category3.Name", "Value": "Music"}]

    def test_folders_go_in_the_media_folder_and_series_becomes_tv(self):
        from starboard.reelix_setup import nzbget_options
        got = {o["Name"]: o["Value"] for o in nzbget_options(self.LSIO)}
        self.assertEqual(got["DestDir"], "/data/downloads/usenet/completed")
        self.assertEqual(got["InterDir"], "/data/downloads/usenet/intermediate")
        self.assertEqual(got["Category2.Name"], "tv")
        self.assertEqual(got["Category1.Name"], "Movies")  # Reelix matches names without regard to capitals

    def test_nothing_changes_the_second_time_and_missing_categories_are_added(self):
        from starboard.reelix_setup import nzbget_options
        self.assertIsNone(nzbget_options(nzbget_options(self.LSIO)))
        bare = [o for o in self.LSIO if not o["Name"].startswith("Category")]
        names = {o["Value"] for o in nzbget_options(bare) if o["Name"].endswith(".Name")}
        self.assertEqual(names, {"tv", "movies"})


if __name__ == "__main__":
    unittest.main()


class TokenFromLogTest(unittest.TestCase):
    """A start from the browser does not run the installer, so Starboard reads Reelix's token itself (8 November 2026)."""

    @staticmethod
    def stream(text):
        data = text.encode()
        return b"\x01\x00\x00\x00" + len(data).to_bytes(4, "big") + data

    def test_reads_the_token_from_either_line_and_saves_it(self):
        import tempfile, json as _json
        from unittest import mock
        from starboard import reelix_setup, stack
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "stack"))
            with open(os.path.join(d, "stack", "reelix-setup.json"), "w") as f:
                _json.dump({"url": "http://127.0.0.1:7700"}, f)
            logs = {"reelix": self.stream("\x1b[33m WARN\x1b[0m no users yet \x1b[3msetup_token\x1b[0m\x1b[2m=\x1b[0mabcDEF123_-xyz\n")}
            docker = lambda method, path, **k: logs[path.split("/")[2]]
            with mock.patch.object(stack, "chosen_keys", return_value=["reelix"]):
                info = reelix_setup.tokens_from_docker(d, reelix_setup.read_setup(d), docker=docker, available=lambda: True)
            self.assertEqual(info["token"], "abcDEF123_-xyz")
            self.assertEqual(reelix_setup.read_setup(d)["token"], "abcDEF123_-xyz")
            self.assertNotIn("qbittorrent_password", info)  # qBittorrent is not Starboard's here: its log is not read

    def test_the_banner_and_qbittorrent_when_starboard_installed_it(self):
        import tempfile, json as _json
        from unittest import mock
        from starboard import reelix_setup, stack
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "stack"))
            with open(os.path.join(d, "stack", "reelix-setup.json"), "w") as f:
                _json.dump({"url": "http://127.0.0.1:7700"}, f)
            logs = {"reelix": self.stream("  Reelix first-run setup token: Tok_123456789\n"),
                    "qbittorrent": self.stream("A temporary password is provided for this session: QbTemp99\n")}
            docker = lambda method, path, **k: logs[path.split("/")[2]]
            with mock.patch.object(stack, "chosen_keys", return_value=["reelix", "qbittorrent"]):
                info = reelix_setup.tokens_from_docker(d, reelix_setup.read_setup(d), docker=docker, available=lambda: True)
            self.assertEqual((info["token"], info["qbittorrent_password"]), ("Tok_123456789", "QbTemp99"))

    def test_a_token_already_there_is_kept_and_docker_is_not_asked(self):
        from starboard import reelix_setup
        info = reelix_setup.tokens_from_docker("/nowhere", {"url": "x", "token": "have"}, docker=None, available=lambda: True)
        self.assertEqual(info["token"], "have")


class WaitUntilUpTest(unittest.TestCase):
    """An unhealthy Reelix (503) is running: the wait must not hold back the step that fixes it (8 November 2026)."""

    def test_an_unhealthy_answer_counts_as_up(self):
        class Unhealthy(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b'{"status": "error", "checks": []}'
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Unhealthy)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            reelix_setup.wait_until_up(f"http://127.0.0.1:{server.server_port}", seconds=1)  # returns, does not raise
        finally:
            server.shutdown()
            server.server_close()


class InstallerTokenTest(unittest.TestCase):
    """DASH-96: the installer reads Reelix's one-time token in both of Reelix's ways of writing it, as Starboard does,
    so the person never sees a second code. Reelix never counts Starboard as "the server itself" (a request from
    Docker's network always needs the token), so it must be read."""

    def test_both_lines_give_the_token(self):
        import pathlib
        import subprocess
        import tempfile
        script = (pathlib.Path(__file__).resolve().parent.parent / "install.sh").read_text()
        line = next(x for x in script.splitlines() if x.strip().startswith('token="$(docker logs reelix'))
        for text, want in (("x \x1b[3msetup_token\x1b[0m\x1b[2m=\x1b[0mabcDEF123_-xyz\n", "abcDEF123_-xyz"),
                           ("  Reelix first-run setup token: Tok_123456789\n", "Tok_123456789")):
            with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
                f.write(text)
            body = line.replace("docker logs reelix 2>&1", f"cat {f.name}") + '\nprintf "%s" "$token"'
            out = subprocess.run(["bash", "-c", body], capture_output=True, text=True, timeout=10).stdout
            pathlib.Path(f.name).unlink()
            self.assertEqual(out, want)
            self.assertEqual(reelix_setup._TOKEN.findall(reelix_setup._ANSI.sub("", text)), [want])
