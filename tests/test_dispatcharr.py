"""Dispatcharr set up from Starboard (DASH-228), against a made-up Dispatcharr and Jellyfin (tests/dispatcharr_stand_in.py):
its admin and key, the IPTV playlist and guide, channels from the playlist, and the tuner and guide in Jellyfin."""
import os
import tempfile
import unittest

from starboard import app_setup, dispatcharr, setup_left, stack
from tests.dispatcharr_stand_in import StandIn

COMPOSE = ('services:\n  dispatcharr:\n    container_name: dispatcharr\n    ports:\n      - "9191:9191"\n'
           '  jellyfin:\n    container_name: jellyfin\n    ports:\n      - "8096:8096"\n')


class Cfg:
    def __init__(self, *services):
        self.data = {"services": [dict(s) for s in services]}

    def upsert_service(self, s):
        s = dict(s)
        for i, have in enumerate(self.data["services"]):
            if have is s or (s.get("id") and have.get("id") == s.get("id")):
                self.data["services"][i] = s
                return
        s.setdefault("id", f"s{len(self.data['services']) + 1}")
        self.data["services"].append(s)


JELLYFIN = {"id": "jf", "name": "Jellyfin", "type": "jellyfin", "url": "http://jellyfin.example:8096", "api_key": "jf-key"}


class DispatcharrTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        os.makedirs(stack.folder(self.dir))
        with open(os.path.join(stack.folder(self.dir), "compose.yaml"), "w") as f:
            f.write(COMPOSE)
        setup_left.forget()

    def connected(self, streams=0, **more):
        fake = StandIn(admin_password="pw", streams=streams, **more)
        fake.key = "made-up-dispatcharr-key"
        cfg = Cfg(JELLYFIN, {"id": "d", "name": "Dispatcharr", "type": "link", "icon": "dispatcharr",
                             "url": "http://127.0.0.1:9191", "api_key": fake.key})
        return fake, cfg

    # first run ----------------------------------------------------------------------------------------------------
    def test_first_run_makes_the_admin_and_a_key_and_runs_again_safely(self):
        fake = StandIn()
        key, done, _ = dispatcharr.first_run("http://127.0.0.1:9191", "pw", opener=fake)
        self.assertEqual((fake.admin, key), (("admin", "pw"), "made-up-dispatcharr-key"))
        self.assertIn("Set up Dispatcharr with the account admin", done[0])
        again, done, _ = dispatcharr.first_run("http://127.0.0.1:9191", "pw", opener=fake)
        self.assertEqual((again, done), (key, []))
        self.assertEqual(sum(1 for m, p, _ in fake.calls if p == "/api/accounts/api-keys/generate/"), 1)

    def test_an_admin_made_before_with_another_password_says_what_to_do(self):
        with self.assertRaisesRegex(app_setup.AppSetupError, "set up before with another account"):
            dispatcharr.first_run("http://d", "pw", opener=StandIn(admin_password="other"))

    def test_setup_refused_from_starboards_address_says_what_to_do(self):
        with self.assertRaisesRegex(app_setup.AppSetupError, "only from some addresses"):
            dispatcharr.first_run("http://d", "pw", opener=StandIn(allow_setup=False))

    def test_connect_keeps_the_key_on_its_link(self):
        fake = StandIn()
        cfg = Cfg({"id": "d", "name": "Dispatcharr", "type": "link", "icon": "dispatcharr", "url": "http://127.0.0.1:9191"})
        dispatcharr.connect(cfg, self.dir, "pw", opener=fake)
        self.assertEqual(cfg.data["services"][0]["api_key"], "made-up-dispatcharr-key")
        self.assertEqual(cfg.data["services"][0]["type"], "link")

    def test_the_first_runs_set_up_dispatcharr_when_install_apps_added_it(self):
        fake = StandIn()
        cfg = Cfg()
        lines = app_setup.dispatcharr_first_run(cfg, self.dir, "pw", opener=fake, wait=0)
        self.assertIn("Add your IPTV source in Settings, Apps, Dispatcharr", lines)
        s = dispatcharr.service(cfg)
        self.assertEqual((s["url"], s["icon"], s["api_key"]), ("http://127.0.0.1:9191", "dispatcharr", "made-up-dispatcharr-key"))

    # state ------------------------------------------------------------------------------------------------------
    def test_state_says_when_dispatcharr_is_not_installed_or_not_connected(self):
        empty = tempfile.mkdtemp(dir=self.dir)
        self.assertEqual(dispatcharr.state(Cfg(), empty), {"installed": False, "connected": False})
        self.assertEqual(dispatcharr.state(Cfg(), self.dir)["connected"], False)

    # the IPTV source --------------------------------------------------------------------------------------------
    def test_saving_a_playlist_and_guide_adds_them_and_the_tuner_in_jellyfin(self):
        fake, cfg = self.connected(streams=3)
        out = dispatcharr.save(cfg, self.dir, {"kind": "m3u", "url": "https://iptv.example/get.php?type=m3u_plus",
                                               "guide": "https://iptv.example/xmltv.php", "max_streams": 2}, opener=fake)
        self.assertEqual([(p["name"], p["account_type"], p["max_streams"]) for p in fake.playlists], [("Starboard playlist", "STD", 2)])
        self.assertEqual([(g["source_type"], g["url"]) for g in fake.guides], [("xmltv", "https://iptv.example/xmltv.php")])
        self.assertEqual([(t["Type"], t["Url"], t["TunerCount"]) for t in fake.tuners], [("hdhomerun", "http://dispatcharr:9191/hdhr", 2)])
        self.assertEqual([(g["Path"], g["EnabledTuners"]) for g in fake.listings], [("http://dispatcharr:9191/output/epg", ["tuner1"])])
        self.assertTrue(any(p == "/ScheduledTasks/Running/refresh-guide" for _, p, _ in fake.calls))
        self.assertIn("Jellyfin: added Dispatcharr as a tuner, with its guide, and started its guide refresh", out["done"])
        self.assertTrue(out["state"]["jellyfin"]["connected"])
        self.assertEqual(out["state"]["streams"], 3)
        self.assertTrue(setup_left.recorded(self.dir)["dispatcharr"])
        # Again: updated in place, nothing added twice.
        again = dispatcharr.save(cfg, self.dir, {"kind": "m3u", "url": "https://iptv.example/new.m3u"}, opener=fake)
        self.assertEqual((len(fake.playlists), len(fake.guides), len(fake.tuners), len(fake.listings)), (1, 1, 1, 1))
        self.assertEqual(fake.playlists[0]["server_url"], "https://iptv.example/new.m3u")
        self.assertEqual(again["done"], ["Updated your IPTV playlist in Dispatcharr"])

    def test_xtream_codes_keeps_the_password_when_left_empty(self):
        fake, cfg = self.connected()
        dispatcharr.save(cfg, self.dir, {"kind": "xc", "url": "http://iptv.example:8080", "username": "sam", "password": "secret"}, opener=fake)
        dispatcharr.save(cfg, self.dir, {"kind": "xc", "url": "http://iptv.example:8080", "username": "sam", "password": ""}, opener=fake)
        sent = [b for m, p, b in fake.calls if p.startswith("/api/m3u/accounts/") and m in ("POST", "PATCH")]
        self.assertEqual((sent[0]["account_type"], sent[0]["password"]), ("XC", "secret"))
        self.assertNotIn("password", sent[1])

    def test_a_source_is_checked_before_anything_is_sent(self):
        for choice, words in (({"kind": "m3u", "url": "iptv.example/list.m3u"}, "full address"),
                              ({"kind": "m3u", "url": ""}, "playlist address"),
                              ({"kind": "xc", "url": "http://iptv.example"}, "user name"),
                              ({"kind": "m3u", "url": "http://a.example/x.m3u", "guide": "ftp://g"}, "guide address"),
                              ({"kind": "m3u", "url": "http://a.example/x.m3u", "max_streams": 99}, "0 to 50"),
                              ({"kind": "other", "url": "http://a.example"}, "Playlist address or Xtream Codes")):
            with self.subTest(choice=choice), self.assertRaisesRegex(ValueError, words):
                dispatcharr.check_choice(choice)

    def test_without_jellyfin_the_source_is_still_saved_and_says_why(self):
        fake, cfg = self.connected()
        cfg.data["services"] = [s for s in cfg.data["services"] if s["type"] != "jellyfin"]
        out = dispatcharr.save(cfg, self.dir, {"kind": "m3u", "url": "http://a.example/x.m3u"}, opener=fake)
        self.assertEqual(len(fake.playlists), 1)
        self.assertIn("add its API key", out["done"][-1])
        self.assertIsNone(out["state"]["jellyfin"]["connected"])

    # channels -----------------------------------------------------------------------------------------------------
    def test_make_channels_takes_at_most_the_first_thousand_streams_once(self):
        fake, cfg = self.connected(streams=1500)
        dispatcharr.save(cfg, self.dir, {"kind": "m3u", "url": "http://a.example/x.m3u"}, opener=fake)
        out = dispatcharr.make_channels(cfg, self.dir, opener=fake)
        bulk = [b for m, p, b in fake.calls if p == "/api/channels/channels/from-stream/bulk/"]
        self.assertEqual(len(bulk[0]["stream_ids"]), dispatcharr.MOST_CHANNELS)
        self.assertIn("the first 1000 of 1500 streams", out["done"][0])
        with self.assertRaisesRegex(ValueError, "has channels already"):
            dispatcharr.make_channels(cfg, self.dir, opener=fake)

    def test_make_channels_waits_for_the_playlist_to_be_read(self):
        fake, cfg = self.connected(streams=0)
        with self.assertRaisesRegex(ValueError, "Add your IPTV source first"):
            dispatcharr.make_channels(cfg, self.dir, opener=fake)
        dispatcharr.save(cfg, self.dir, {"kind": "m3u", "url": "http://a.example/x.m3u"}, opener=fake)
        with self.assertRaisesRegex(ValueError, "has not read your playlist yet"):
            dispatcharr.make_channels(cfg, self.dir, opener=fake)

    # Jellyfin -------------------------------------------------------------------------------------------------------
    def test_a_guide_linked_to_every_tuner_is_linked_to_dispatcharrs_own(self):
        fake, cfg = self.connected()
        fake.tuners.append({"Id": "t9", "Type": "hdhomerun", "Url": "http://dispatcharr:9191/hdhr"})
        fake.listings.append({"Id": "g9", "Type": "xmltv", "Path": "http://dispatcharr:9191/output/epg", "EnableAllTuners": True})
        line = dispatcharr.connect_jellyfin(cfg, self.dir, opener=fake)
        self.assertEqual(line, "Jellyfin: linked Dispatcharr's guide to its tuner, and started its guide refresh")
        self.assertEqual(fake.listings[0]["EnabledTuners"], ["t9"])
        self.assertEqual(dispatcharr.connect_jellyfin(cfg, self.dir, opener=fake), "")

    def test_an_app_installed_by_hand_is_reached_at_its_own_address(self):
        with open(os.path.join(stack.folder(self.dir), "compose.yaml"), "w") as f:
            f.write("services:\n")
        fake, cfg = self.connected()
        dispatcharr.connect_jellyfin(cfg, self.dir, opener=fake)
        self.assertEqual(fake.tuners[0]["Url"], "http://127.0.0.1:9191/hdhr")

    # Still to set up ------------------------------------------------------------------------------------------------
    def test_still_to_set_up_points_at_the_page_and_goes_when_saved(self):
        from unittest import mock
        with mock.patch.object(setup_left, "_reelix_health", return_value=None), \
                mock.patch.object(setup_left, "_usenet_server", return_value=None):
            item = next(i for i in setup_left.items(Cfg(), self.dir) if i["key"] == "dispatcharr")
            self.assertEqual((item["href"], item["done"], item.get("guided")), ("/settings-dispatcharr.html#dp-source-h", False, None))
            setup_left.record(self.dir, guided_done=["dispatcharr"])  # Done on the old guided step still counts
            self.assertTrue(next(i for i in setup_left.items(Cfg(), self.dir) if i["key"] == "dispatcharr")["done"])
        self.assertIn("/settings-dispatcharr.html", setup_left.PANEL_PAGES)
        self.assertNotIn("dispatcharr", {k for k, _, _ in setup_left.GUIDED})


if __name__ == "__main__":
    unittest.main()
