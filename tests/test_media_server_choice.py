"""Choosing the media server, checking it and the way back (DASH-565, PR D): a new one is asked to answer first, nothing
is switched by itself, the one before stays and the way back lasts 24 hours."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, mediaserver, services

JF = {"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "made-up-key-7731", "enabled": True}


class Fake(mediaserver.MediaServer):
    """A second media server that answers or does not, as a test says."""
    id, name, service_type, page = "plex", "Plex", "plex", "/settings-plex.html"
    answers = {"ok": True, "why": "", "name": "Den", "version": "1.41"}
    shelves = [{"name": "Films"}, {"name": "Series"}]

    def sign_in_check(self, services_list):
        return dict(self.answers)

    def libraries(self, services_list):
        return list(self.shelves)


class Cfg:
    """The bit of the settings object the choice uses."""
    def __init__(self, extras=None):
        self.data = {"extras": dict(extras or {}), "services": [JF]}
        self.lock = threading.RLock()
        self.saved = 0

    def save(self):
        self.saved += 1


class Choice(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(mediaserver.ADAPTERS, {"plex": Fake})
        p.start()
        self.addCleanup(p.stop)
        Fake.answers = {"ok": True, "why": "", "name": "Den", "version": "1.41"}

    def test_a_new_one_is_asked_first_then_chosen_with_a_way_back(self):
        cfg = Cfg()
        got = mediaserver.choose(cfg, "plex", ["jellyfin", "plex"], now=1000)
        self.assertTrue(got["changed"])
        self.assertIn("Plex answered and is now your media server", got["said"])
        self.assertIn("Jellyfin stays added", got["said"])
        self.assertEqual(cfg.data["extras"]["media_server"], "plex")
        self.assertEqual(cfg.data["extras"]["media_server_back"], {"id": "jellyfin", "at": 1000})
        self.assertEqual(cfg.saved, 1)  # one write

    def test_one_that_does_not_answer_changes_nothing(self):
        Fake.answers = {"ok": False, "why": "Plex is not set up yet."}
        cfg = Cfg()
        with self.assertRaises(ValueError) as e:
            mediaserver.choose(cfg, "plex", ["jellyfin", "plex"])
        self.assertIn("Plex did not answer: Plex is not set up yet.", str(e.exception))
        self.assertIn("Nothing changed: Jellyfin stays in use", str(e.exception))
        self.assertEqual(cfg.data["extras"], {})
        self.assertEqual(cfg.saved, 0)

    def test_one_that_is_not_added_is_not_chosen(self):
        cfg = Cfg()
        with self.assertRaises(ValueError) as e:
            mediaserver.choose(cfg, "plex", ["jellyfin"])
        self.assertIn("not added as a plug-in yet", str(e.exception))
        self.assertEqual(cfg.saved, 0)

    def test_an_unknown_one_is_not_found(self):
        with self.assertRaises(LookupError):
            mediaserver.choose(Cfg(), "kodi", ["jellyfin"])

    def test_the_one_in_use_is_a_no_op(self):
        cfg = Cfg()
        got = mediaserver.choose(cfg, "jellyfin", ["jellyfin"])
        self.assertEqual((got["changed"], cfg.saved), (False, 0))

    def test_none_needs_no_check_and_keeps_the_old_one(self):
        cfg = Cfg()
        got = mediaserver.choose(cfg, "", [])
        self.assertTrue(got["changed"])
        self.assertEqual(mediaserver.active_id(cfg.data), "")
        self.assertIn("Jellyfin stays added", got["said"])
        self.assertEqual(cfg.data["extras"]["media_server_back"]["id"], "jellyfin")

    def test_the_way_back_lasts_24_hours(self):
        cfg = Cfg()
        mediaserver.choose(cfg, "plex", ["plex"], now=1000)
        self.assertEqual(mediaserver.back_info(cfg.data, now=1000 + 23 * 3600)["name"], "Jellyfin")
        self.assertIsNone(mediaserver.back_info(cfg.data, now=1000 + 24 * 3600))
        with self.assertRaises(ValueError):
            mediaserver.go_back(cfg, now=1000 + 25 * 3600)
        got = mediaserver.go_back(cfg, now=1000 + 3600)
        self.assertEqual(got["said"], "Jellyfin is your media server again")
        self.assertEqual(mediaserver.active_id(cfg.data), "jellyfin")
        self.assertEqual(cfg.data["extras"]["media_server_back"]["id"], "plex")  # and back again, if wanted
        self.assertEqual(mediaserver.back_info(cfg.data, now=1000 + 3600)["id"], "plex")

    def test_back_does_not_ask_the_old_one_first(self):
        cfg = Cfg()
        mediaserver.choose(cfg, "plex", ["plex"], now=10)
        with mock.patch.object(services, "_fetch", side_effect=AssertionError("asked")):
            self.assertTrue(mediaserver.go_back(cfg, now=20)["changed"])

    def test_back_to_none(self):
        cfg = Cfg({"media_server": "plex", "media_server_back": {"id": "", "at": 5}})
        self.assertEqual(mediaserver.back_info(cfg.data, now=6), {"id": "", "name": "", "until": 5 + 24 * 3600})
        self.assertEqual(mediaserver.go_back(cfg, now=6)["said"], "No media server is in use now")
        self.assertEqual(mediaserver.active_id(cfg.data), "")

    def test_bad_back_records_are_ignored(self):
        for bad in (None, "x", {"id": 5, "at": 1}, {"id": "jellyfin"}, {"id": "kodi", "at": 1}, {"id": "jellyfin", "at": 1}):
            self.assertIsNone(mediaserver.back_info({"extras": {"media_server": "jellyfin", "media_server_back": bad}}, now=2), bad)

    def test_the_state_says_which_are_added_and_the_way_back(self):
        got = mediaserver.state({"extras": {"media_server": "plex", "media_server_back": {"id": "jellyfin", "at": 1}}, "services": []}, ["plex"], now=2)
        self.assertEqual((got["active"], got["added"], got["back"]["name"]), ("plex", ["plex"], "Jellyfin"))
        self.assertEqual(mediaserver.state({}, None)["added"], ["jellyfin", "plex"])


class Check(unittest.TestCase):
    def test_what_it_found_in_words(self):
        with mock.patch.dict(mediaserver.ADAPTERS, {"plex": Fake}):
            got = mediaserver.check({"services": []}, "plex")
        self.assertEqual((got["ok"], got["name"], got["libraries"]), (True, "Den", ["Films", "Series"]))
        self.assertEqual(got["said"], "It answered (version 1.41). It has 2 libraries: Films, Series.")

    def test_one_library_and_none(self):
        with mock.patch.dict(mediaserver.ADAPTERS, {"plex": Fake}), mock.patch.object(Fake, "shelves", [{"name": "Films"}]):
            self.assertIn("It has 1 library: Films.", mediaserver.check({}, "plex")["said"])
        with mock.patch.dict(mediaserver.ADAPTERS, {"plex": Fake}), mock.patch.object(Fake, "shelves", []):
            self.assertIn("It lists no libraries yet.", mediaserver.check({}, "plex")["said"])

    def test_a_server_that_does_not_answer_is_said_not_raised(self):
        with mock.patch.dict(mediaserver.ADAPTERS, {"plex": Fake}), mock.patch.object(Fake, "answers", {"ok": False, "why": "No answer from 192.168.1.9"}):
            got = mediaserver.check({}, "plex")
        self.assertEqual((got["ok"], got["said"]), (False, "No answer from 192.168.1.9"))

    def test_jellyfin_answers_through_the_check(self):
        from tests.test_mediaserver import fake
        with mock.patch.object(services, "_fetch", side_effect=fake):
            got = mediaserver.check({"services": [JF]}, "jellyfin")
        self.assertTrue(got["ok"])
        self.assertIn("It answered (version 12.4.0). It has 2 libraries: Films, Mixed.", got["said"])

    def test_jellyfin_not_set_up_says_so(self):
        got = mediaserver.check({"services": []}, "jellyfin")
        self.assertFalse(got["ok"])
        self.assertIn("not set up yet", got["said"])

    def test_an_unknown_server(self):
        with self.assertRaises(LookupError):
            mediaserver.check({}, "kodi")


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
        r, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def call(cls, method, path, body=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        headers = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            headers["Cookie"] = cls.cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r, json.loads(raw) if raw[:1] in (b"{", b"[") else raw

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        p = mock.patch.dict(mediaserver.ADAPTERS, {"plex": Fake})
        p.start()
        self.addCleanup(p.stop)
        Fake.answers = {"ok": True, "why": "", "name": "Den", "version": "1.41"}
        self.app.config.data["extras"].pop("media_server", None)
        self.app.config.data["extras"].pop("media_server_back", None)
        self.call("GET", "/api/plugins")  # Jellyfin's record is added
        import shutil
        shutil.rmtree(os.path.join(self.app.data_dir, "plugins", "plex"), ignore_errors=True)

    def add_plex(self, state="enabled"):
        d = os.path.join(self.app.data_dir, "plugins", "plex")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "manifest.json"), "w") as f:
            json.dump({"id": "plex", "name": "Plex", "version": "1.0.0"}, f)
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump({"state": state, "builtin": True}, f)

    def test_every_route_needs_a_signed_in_person(self):
        for method, path in (("GET", "/api/media-server"), ("POST", "/api/media-server/check"), ("POST", "/api/media-server/choose"),
                             ("POST", "/api/media-server/back")):
            r, _ = self.call(method, path, {}, cookie=False)
            self.assertIn(r.status, (401, 403), path)

    def test_the_state_lists_what_is_added(self):
        r, got = self.call("GET", "/api/media-server")
        self.assertEqual((r.status, got["added"], got["back"]), (200, ["jellyfin"], None))
        self.add_plex()
        self.assertEqual(self.call("GET", "/api/media-server")[1]["added"], ["jellyfin", "plex"])
        self.add_plex("installed")  # added but not active: not chosen yet
        self.assertEqual(self.call("GET", "/api/media-server")[1]["added"], ["jellyfin"])

    def test_check_says_what_it_found_and_changes_nothing(self):
        self.add_plex()
        r, got = self.call("POST", "/api/media-server/check", {"id": "plex"})
        self.assertEqual((r.status, got["ok"]), (200, True))
        self.assertNotIn("media_server", self.app.config.data["extras"])
        self.assertEqual(self.call("POST", "/api/media-server/check", {"id": "kodi"})[0].status, 404)

    def test_choose_then_back(self):
        self.add_plex()
        r, got = self.call("POST", "/api/media-server/choose", {"id": "plex"})
        self.assertEqual((r.status, got["changed"], got["active"]), (200, True, "plex"))
        self.assertEqual(got["back"]["id"], "jellyfin")
        self.assertEqual(self.call("GET", "/api/media-server")[1]["name"], "Plex")
        r, got = self.call("POST", "/api/media-server/back")
        self.assertEqual((r.status, got["active"]), (200, "jellyfin"))

    def test_choose_one_that_does_not_answer(self):
        self.add_plex()
        Fake.answers = {"ok": False, "why": "No answer."}
        r, got = self.call("POST", "/api/media-server/choose", {"id": "plex"})
        self.assertEqual(r.status, 409)
        self.assertIn("Nothing changed", got["error"])
        self.assertEqual(self.call("GET", "/api/media-server")[1]["active"], "jellyfin")

    def test_choose_one_not_added_or_unknown(self):
        self.assertEqual(self.call("POST", "/api/media-server/choose", {"id": "plex"})[0].status, 409)
        self.assertEqual(self.call("POST", "/api/media-server/choose", {"id": "kodi"})[0].status, 404)
        self.assertEqual(self.call("POST", "/api/media-server/back")[0].status, 409)

    def test_none_then_jellyfin_may_be_removed_in_use_may_not(self):
        r, _ = self.call("POST", "/api/plugins/jellyfin/disable", {})
        self.assertEqual(r.status, 409)
        self.assertIn("Settings, Media server", self.call("POST", "/api/plugins/jellyfin/disable", {})[1]["error"])
        self.assertEqual(self.call("POST", "/api/media-server/choose", {"id": ""})[0].status, 200)
        self.assertEqual(self.call("POST", "/api/plugins/jellyfin/disable", {})[0].status, 200)
        self.assertEqual(self.call("POST", "/api/plugins/jellyfin/enable", {})[0].status, 200)

    def test_the_choice_is_kept_in_the_saved_settings(self):
        self.add_plex()
        self.call("POST", "/api/media-server/choose", {"id": "plex"})
        with open(os.path.join(self.app.data_dir, "config.json")) as f:
            saved = json.load(f)
        self.assertEqual(saved["extras"]["media_server"], "plex")


if __name__ == "__main__":
    unittest.main()
