"""The media server contract (DASH-565, 25 November 2026): what Starboard asks of a media server, the slot that the
active one fills, and Jellyfin as the first and default one, so nothing a person sees changes."""
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, mediaserver, services

JF = {"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "made-up-key-7731", "enabled": True}
INFO = {"Version": "12.4.0", "ServerName": "Harbour", "HasUpdateAvailable": False, "HasPendingRestart": True, "CanSelfRestart": True}
SESSIONS = [{"UserName": "Sam", "DeviceName": "Lounge TV", "Client": "Android TV", "NowPlayingItem": {"Name": "Dune", "Type": "Movie", "RunTimeTicks": 1000},
             "PlayState": {"PositionTicks": 250, "IsPaused": False}, "TranscodingInfo": {"IsVideoDirect": False, "TranscodeReasons": ["VideoCodecNotSupported"]}}]
ADDED = {"Items": [{"Name": "Dune", "Type": "Movie", "DateCreated": "2026-11-20T10:00:00Z", "ProductionYear": 2021}] * 3}


def fake(service, req, timeout):
    path = req.full_url.split("8096", 1)[1]
    if path.startswith("/System/Info"):
        return INFO
    if path.startswith("/Sessions"):
        return SESSIONS
    if path.startswith("/Items"):
        return ADDED
    if path.startswith("/LiveTv/Channels"):
        raise services.ServiceError("no Live TV")
    if path.startswith("/ScheduledTasks"):
        return []
    if path == "/Library/VirtualFolders":
        return [{"Name": "Films", "ItemId": "a1", "CollectionType": "movies"}, {"Name": "Mixed"}, "junk"]
    if path == "/Users":
        return [{"Id": "u1", "Name": "Sam", "Policy": {"IsAdministrator": True}}, {"Id": "u2", "Name": "Alex"}]
    if path == "/Library/Refresh":
        return ""
    raise AssertionError(path)


class Contract(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(services, "_fetch", side_effect=fake)
        self.fetch = p.start()
        self.addCleanup(p.stop)
        self.jf = mediaserver.Jellyfin()

    def test_every_required_call_is_there_and_capabilities_are_named(self):
        for call in mediaserver.REQUIRED:
            self.assertTrue(callable(getattr(self.jf, call)), call)
        self.assertEqual(set(self.jf.capabilities) - set(mediaserver.CAPABILITIES), set())
        d = self.jf.describe()
        self.assertEqual((d["id"], d["name"], d["kind"], d["page"]), ("jellyfin", "Jellyfin", "media-server", "/settings-jellyfin.html"))

    def test_the_base_class_asks_for_every_call(self):
        base = mediaserver.MediaServer()
        for call, args in (("status", ([],)), ("libraries", ([],)), ("playing", ([],)), ("recent", ([],)), ("refresh", ([],)),
                           ("users", ([],)), ("sign_in_check", ([],)), ("keys_needed", ())):
            with self.assertRaises(NotImplementedError, msg=call):
                getattr(base, call)(*args)

    def test_status(self):
        got = self.jf.status([JF])
        self.assertEqual(got, {"configured": True, "up": True, "name": "Jellyfin", "version": "12.4.0", "update_available": False,
                               "restart_needed": True, "playing": 1, "why": ""})

    def test_status_when_not_set_up_or_not_answering(self):
        self.assertEqual(self.jf.status([])["configured"], False)
        self.assertEqual(self.jf.status([{**JF, "api_key": ""}])["configured"], False)
        self.assertEqual(self.jf.status([{**JF, "enabled": False}])["configured"], False)
        self.fetch.side_effect = services.ServiceError("Cannot reach Jellyfin")
        got = self.jf.status([JF])
        self.assertEqual((got["configured"], got["up"], got["why"]), (True, False, "Cannot reach Jellyfin"))

    def test_libraries_users_playing_recent(self):
        self.assertEqual(self.jf.libraries([JF]), [{"id": "a1", "name": "Films", "type": "movies", "count": None},
                                                    {"id": "Mixed", "name": "Mixed", "type": "mixed", "count": None}])
        self.assertEqual(self.jf.users([JF]), [{"id": "u1", "name": "Sam", "admin": True}, {"id": "u2", "name": "Alex", "admin": False}])
        self.assertEqual(self.jf.playing([JF]), [{"user": "Sam", "title": "Dune", "kind": "Movie", "device": "Lounge TV", "converting": True, "progress": 25}])
        self.assertEqual(len(self.jf.recent([JF])), 3)
        self.assertEqual(len(self.jf.recent([JF], 2)), 2)
        self.assertEqual(self.jf.recent([JF], 0), [])
        self.assertEqual(self.jf.recent([JF])[0], {"title": "Dune", "kind": "Movie", "added": "2026-11-20T10:00:00Z", "link": None})

    def test_refresh_posts_and_names_the_server_in_the_log_path_only(self):
        self.assertEqual(self.jf.refresh([JF]), {"asked": True})
        req = self.fetch.call_args[0][1]
        self.assertEqual((req.get_method(), req.full_url), ("POST", "http://127.0.0.1:8096/Library/Refresh"))

    def test_sign_in_check(self):
        self.assertEqual(self.jf.sign_in_check([JF]), {"ok": True, "why": "", "name": "Harbour", "version": "12.4.0"})
        got = self.jf.sign_in_check([])
        self.assertEqual((got["ok"], "not set up" in got["why"]), (False, True))
        self.fetch.side_effect = services.ServiceError("Jellyfin refused the API key")
        self.assertEqual(self.jf.sign_in_check([JF]), {"ok": False, "why": "Jellyfin refused the API key"})

    def test_a_call_without_the_server_set_up_says_so_in_words(self):
        for call in (self.jf.libraries, self.jf.users, self.jf.refresh):
            with self.assertRaises(services.ServiceError) as e:
                call([])
            self.assertIn("not set up yet", str(e.exception))

    def test_keys_needed_is_what_settings_has_always_said(self):
        self.assertEqual(self.jf.keys_needed(), [{"what": "API key", "where": "Dashboard, API keys", "kept": "Settings, Apps"}])

    def test_no_key_is_in_any_answer(self):
        blob = json.dumps([self.jf.status([JF]), self.jf.libraries([JF]), self.jf.users([JF]), self.jf.playing([JF]),
                           self.jf.recent([JF]), self.jf.sign_in_check([JF]), self.jf.describe(), self.jf.keys_needed()])
        self.assertNotIn(JF["api_key"], blob)
        self.assertNotIn("MediaBrowser", blob)


class Slot(unittest.TestCase):
    def test_jellyfin_is_the_default_so_nothing_needs_migrating(self):
        for data in (None, {}, {"extras": {}}, {"extras": {"media_server": None}}, {"extras": "x"}):
            self.assertEqual(mediaserver.active_id(data), "jellyfin", data)
        self.assertEqual(mediaserver.active({"extras": {}}).id, "jellyfin")

    def test_none_and_unknown_are_no_media_server_never_an_error(self):
        for chosen in ("", "kodi", "Jellyfin", 5, ["jellyfin"]):
            self.assertEqual(mediaserver.active_id({"extras": {"media_server": chosen}}), "", chosen)
            self.assertIsNone(mediaserver.active({"extras": {"media_server": chosen}}))
        self.assertEqual(mediaserver.active_id({"extras": {"media_server": "jellyfin"}}), "jellyfin")

    def test_state_reads_settings_alone(self):
        with mock.patch.object(services, "_fetch", side_effect=AssertionError("nothing is asked of the server")):
            got = mediaserver.state({"services": [JF], "extras": {}})
            self.assertEqual((got["active"], got["name"], got["configured"], got["page"]), ("jellyfin", "Jellyfin", True, "/settings-jellyfin.html"))
            self.assertEqual([a["id"] for a in got["available"]], ["jellyfin", "emby", "plex"])
            self.assertEqual(got["available"][0], {"id": "jellyfin", "name": "Jellyfin", "page": "/settings-jellyfin.html"})
            self.assertIn("restart", got["capabilities"])
            self.assertFalse(mediaserver.state({"services": [], "extras": {}})["configured"])
            none = mediaserver.state({"services": [JF], "extras": {"media_server": ""}})
            self.assertEqual((none["active"], none["name"], none["configured"], none["capabilities"]), ("", "", False, []))

    def test_the_old_answer_is_the_same_as_before(self):
        with mock.patch.object(services, "_fetch", side_effect=fake):
            before = services.jellyfin([JF])
            self.assertEqual(mediaserver.status_for_pages({"services": [JF], "extras": {}}), before)
            self.assertEqual(mediaserver.status_for_pages({"services": [], "extras": {}}), {"configured": False})
            self.assertEqual(mediaserver.status_for_pages({"services": [JF], "extras": {"media_server": ""}}), {"configured": False})

    def test_nothing_is_imported_until_asked_for(self):
        code = ("import sys\nimport starboard.server\n"
                "assert 'starboard.mediaserver' not in sys.modules, 'the slot is loaded at start'\n")
        import subprocess
        r = subprocess.run([sys.executable, "-c", code], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from starboard.server import make_server
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        conn.request("POST", "/api/setup", json.dumps({"token": cls.app.setup_token, "password": "correct horse battery"}),
                     {"Content-Type": "application/json", "X-Starboard": "1"})
        r = conn.getresponse()
        r.read()
        conn.close()
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, None, {"Cookie": self.cookie} if cookie else {})
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, json.loads(raw) if raw[:1] in (b"{", b"[") else raw

    def test_both_routes_need_a_signed_in_person(self):
        for path in ("/api/media-server", "/api/jellyfin"):
            self.assertIn(self.get(path, cookie=False)[0], (401, 403), path)

    def test_the_slot_and_the_old_status_answer(self):
        self.app.config.data["services"] = []
        self.app.config.data["extras"].pop("media_server", None)
        services.forget("jellyfin")
        status, got = self.get("/api/media-server")
        self.assertEqual((status, got["active"], got["configured"]), (200, "jellyfin", False))
        self.assertEqual(self.get("/api/jellyfin"), (200, {"configured": False}))
        self.app.config.data["extras"]["media_server"] = ""
        status, got = self.get("/api/media-server")
        self.assertEqual((got["active"], got["capabilities"]), ("", []))
        self.app.config.data["extras"].pop("media_server")
        services.forget("jellyfin")

    def test_jellyfin_status_is_the_same_through_the_slot(self):
        self.app.config.data["services"] = [JF]
        services.forget("jellyfin")
        with mock.patch.object(services, "_fetch", side_effect=fake):
            status, got = self.get("/api/jellyfin")
            self.assertEqual(status, 200)
            self.assertEqual(got, services.jellyfin([JF]))
        self.app.config.data["services"] = []
        services.forget("jellyfin")


if __name__ == "__main__":
    unittest.main()
