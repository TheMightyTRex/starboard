"""The switch wizard's plan (DASH-565, owner, 26 November 2026): what moves, what cannot, what is unaffected, and which
plug-ins and parts of Starboard work or wait after the switch. It asks the new server to answer and changes nothing."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, mediaserver, mediaserver_switch as sw, plugin_systems, server

JF = {"id": "jf", "name": "Jellyfin", "type": "jellyfin", "url": "http://x:8096", "api_key": "k", "enabled": True}
PLEX = {"id": "plex", "name": "Plex", "type": "plex", "url": "http://x:32400", "api_key": "t", "enabled": True}
RX = {"id": "reelix", "name": "Reelix", "type": "link", "icon": "reelix", "url": "http://x:7700", "enabled": True}
DATA = {"services": [JF, PLEX, RX], "extras": {}}


def plug(pid, name, needs):
    return {"id": pid, "name": name, "system": plugin_systems.describe({"requires": needs}) if needs is not None else {}}


LISTED = [plug("direct-play", "Direct play", ["jellyfin"]), plug("either", "Either one", ["plex or emby"]), plug("needs-reelix", "Fetcher", ["reelix"]),
          plug("free", "Free one", []), {**plug("jellyfin", "Jellyfin", ["jellyfin"]), "media_server": True}]


class Plan(unittest.TestCase):
    def fake_check(self, ok=True):
        return mock.patch.object(mediaserver, "check", return_value={"ok": ok, "name": "Plex", "said": "It answered. It has 2 libraries: Films, Series.", "libraries": ["Films", "Series"]})

    def test_plug_ins_that_need_the_old_server_wait_and_the_rest_work(self):
        with self.fake_check():
            p = sw.plan(DATA, "plex", "migrate", LISTED)
        by = {r["id"]: r for r in p["plugins"]}
        self.assertEqual(by["direct-play"]["state"], "waiting")
        self.assertIn("Needs Jellyfin", by["direct-play"]["why"])
        self.assertEqual((by["either"]["state"], by["needs-reelix"]["state"]), ("works", "works"))
        self.assertNotIn("free", by)  # needs nothing named: not a dependant
        self.assertNotIn("jellyfin", by)  # the media server plug-in itself is the slot, not a dependant
        self.assertEqual([r["state"] for r in p["plugins"]][:1], ["waiting"])  # the ones that wait come first

    def test_back_to_jellyfin_everything_works(self):
        data = {**DATA, "extras": {"media_server": "plex"}}
        with self.fake_check():
            p = sw.plan(data, "jellyfin", "fresh", LISTED)
        by = {r["id"]: r["state"] for r in p["plugins"]}
        self.assertEqual((by["direct-play"], by["needs-reelix"], by["either"]), ("works", "works", "waiting"))  # "Plex or Emby" waits for Jellyfin
        feats = {f["name"]: f for f in p["features"]}
        self.assertEqual(feats["Live TV channels and the TV channel plug-in"]["state"], "works")
        self.assertEqual(feats["Play in your media server (Library)"]["state"], "works")

    def test_what_plex_cannot_do_yet_waits_in_words_and_the_apps_with_their_own_link_need_pointing(self):
        with self.fake_check():
            feats = {f["name"]: f for f in sw.plan(DATA, "plex", "own", LISTED)["features"]}
        self.assertEqual(feats["Live TV channels and the TV channel plug-in"]["state"], "waiting")
        self.assertIn("Jellyfin only", feats["Live TV channels and the TV channel plug-in"]["why"])
        self.assertEqual(feats["Dashboard panel, Activity and System"]["state"], "works")
        for name in ("Reelix's own link to the media server", "Seerr (requests)", "On demand", "Remote access forwarding"):
            self.assertEqual(feats[name]["state"], "repoint", name)

    def test_the_three_ways_say_different_things_and_all_say_what_is_unaffected(self):
        with self.fake_check():
            own, mig, fresh = (sw.plan(DATA, "plex", m, LISTED) for m in ("own", "migrate", "fresh"))
        self.assertIn("same media folders", own["moves"][0])
        self.assertTrue(any("cannot be copied into Plex yet" in m for m in mig["moves"]))
        self.assertFalse(mig["import_history"])
        self.assertIn("starts empty", fresh["moves"][0])
        for p in (own, mig, fresh):
            self.assertTrue(any("download apps" in u for u in p["unaffected"]))
            self.assertTrue(any("Collections" in c for c in p["cannot_move"]))
        with self.fake_check():
            self.assertTrue(sw.plan({**DATA, "extras": {"media_server": "plex"}}, "jellyfin", "migrate", LISTED)["import_history"])

    def test_the_new_server_is_asked_first_and_a_server_that_does_not_answer_is_said(self):
        with self.fake_check(ok=False) as c:
            p = sw.plan(DATA, "plex", "own", LISTED)
        c.assert_called_once()
        self.assertFalse(p["check"]["ok"])

    def test_the_same_server_and_none_ask_nothing(self):
        with mock.patch.object(mediaserver, "check") as c:
            same = sw.plan(DATA, "jellyfin", "own", LISTED)
            none = sw.plan(DATA, "", "fresh", LISTED)
        c.assert_not_called()
        self.assertTrue(same["same"])
        self.assertEqual((none["to_name"], none["features"]), ("None", []))
        self.assertTrue(all(r["state"] == "waiting" for r in none["plugins"] if r["id"] != "needs-reelix"))

    def test_a_wrong_way_or_server_is_refused(self):
        with self.assertRaises(ValueError):
            sw.plan(DATA, "plex", "teleport", LISTED)
        with self.assertRaises(LookupError):
            sw.plan(DATA, "kodi", "own", LISTED)


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = server.make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        r, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def call(cls, method, path, body=None, cookie=True):
        c = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            h["Cookie"] = cls.cookie
        c.request(method, path, json.dumps(body) if body is not None else None, h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        return r, json.loads(raw) if raw[:1] in (b"{", b"[") else raw

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_the_plan_changes_nothing_and_needs_a_sign_in(self):
        r, _ = self.call("POST", "/api/media-server/plan", {"id": "plex", "mode": "fresh"}, cookie=False)
        self.assertEqual(r.status, 401)
        before = json.dumps(self.app.config.data["extras"], sort_keys=True)
        r, got = self.call("POST", "/api/media-server/plan", {"id": "plex", "mode": "fresh"})
        self.assertEqual(r.status, 200, got)
        self.assertEqual((got["to"], got["from"], got["mode"]), ("plex", "jellyfin", "fresh"))
        self.assertFalse(got["check"]["ok"])  # no Plex is set up here: said, not raised
        self.assertEqual(json.dumps(self.app.config.data["extras"], sort_keys=True), before)
        self.assertEqual(self.call("POST", "/api/media-server/plan", {"id": "plex", "mode": "x"})[0].status, 400)
        self.assertEqual(self.call("POST", "/api/media-server/plan", {"id": "kodi", "mode": "own"})[0].status, 404)


if __name__ == "__main__":
    unittest.main()
