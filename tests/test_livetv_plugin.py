"""Live TV as a plug-in (DASH-285): the built-in manifest, its Compose file, its program, and the move from Starboard."""
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from starboard import config as config_mod, livetv_move, livetv_plugin, plugin_cards, plugins, plugins_admin as pa

HOST = {"image": "starboard:local", "user": "1000:1000", "iptv": "/srv/apps/jellyfin/iptv", "tz": "Europe/London"}


class FakeConfig:
    def __init__(self, data_dir, extras):
        self.data_dir = data_dir
        self.lock = threading.Lock()
        self.data = {"extras": {**config_mod.DEFAULTS["extras"], **extras},
                     "services": [{"type": "jellyfin", "url": "http://127.0.0.1:8097", "api_key": "made-up-jf-key"}]}
        self.saved = 0

    def save(self):
        self.saved += 1


class LiveTvPluginTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.manifest = pa.builtins()["livetv"]
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/starboard/data/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)
        livetv_move._active.clear()

    def test_the_manifest_is_built_in_only(self):
        self.assertEqual(plugins.check(self.manifest, builtin=True), [])
        self.assertTrue(any("only plug-ins built into Starboard" in x for x in plugins.check(self.manifest)))
        copy = json.loads(json.dumps(self.manifest))
        copy["version"] = "9.9.9"  # a changed copy from elsewhere is not built in
        with self.assertRaises(ValueError):
            pa.install(self.tmp.name, copy, "/srv/media", builtin=True, host=HOST)

    def test_its_compose_file_runs_starboards_image_on_the_same_folder(self):
        text = plugins.compose(self.manifest, "/srv/p", "/srv/media", HOST)
        for line in ('image: "starboard:local"', 'command: ["python", "-m", "starboard.livetv_plugin"]', 'user: "1000:1000"',
                     '"/srv/apps/jellyfin/iptv:/iptv"', "host.docker.internal:host-gateway", "/srv/p/run:/run/starboard:ro",  # DASH-357: one folder
                     "read_only: true", "- ALL", "mem_limit: 192m", 'TZ: "Europe/London"',
                     '"http://127.0.0.1:8080/health"'):
            self.assertIn(line, text)
        with self.assertRaisesRegex(ValueError, "no Live TV folder"):
            plugins.compose(self.manifest, "/srv/p", "/srv/media", {**HOST, "iptv": None})

    def test_jellyfins_key_reaches_it_through_the_computer(self):
        pa.install(self.tmp.name, self.manifest, "/srv/media", builtin=True, host=HOST)
        cfg = FakeConfig(self.tmp.name, {})
        self.assertTrue(pa.write_jellyfin(self.tmp.name, "livetv", cfg.data["services"]))
        with open(os.path.join(pa.folder(self.tmp.name, "livetv"), "jellyfin.json")) as f:
            self.assertEqual(json.load(f), {"url": "http://host.docker.internal:8097", "api_key": "made-up-jf-key"})

    def test_the_move_keeps_every_setting_and_switches_starboards_job_off(self):
        cfg = FakeConfig(self.tmp.name, {"livetv": True, "white_logos": False, "livetv_address": "http://192.168.1.20:8095",
                                         "livetv_jellyfin_folder": "/config/iptv"})
        runs = []
        with mock.patch.object(livetv_move, "can_run", return_value=""), mock.patch.object(pa, "host_for_builtin", return_value=HOST):
            said = livetv_move.move(cfg, self.tmp.name, "/srv/media", "http://192.168.1.20:8095",
                                    helper=lambda folder, script: (runs.append(script) or (0, "")))
        self.assertIn("Live TV is now a plug-in", said)
        self.assertFalse(cfg.data["extras"]["livetv"])
        self.assertIn("up -d", runs[-1])
        with open(os.path.join(pa.folder(self.tmp.name, "livetv"), "settings.json")) as f:
            self.assertEqual(json.load(f), {"white_logos": False, "address": "http://192.168.1.20:8095", "jellyfin_folder": "/config/iptv"})
        self.assertTrue(livetv_move.plugin_active(self.tmp.name))
        self.assertEqual(livetv_move.move(cfg, self.tmp.name, "/srv/media", ""), "")  # once only

    def test_without_docker_live_tv_stays_in_starboard(self):
        cfg = FakeConfig(self.tmp.name, {"livetv": True})
        with mock.patch.object(livetv_move, "can_run", return_value="Starboard has no access to Docker here"):
            self.assertEqual(livetv_move.move(cfg, self.tmp.name, "/srv/media", "http://x"), "")
        self.assertTrue(cfg.data["extras"]["livetv"])
        self.assertIsNone(livetv_move.plugin_state(self.tmp.name))

    def test_a_failed_start_leaves_live_tv_in_starboard(self):
        cfg = FakeConfig(self.tmp.name, {"livetv": True})
        with mock.patch.object(livetv_move, "can_run", return_value=""), mock.patch.object(pa, "host_for_builtin", return_value=HOST):
            said = livetv_move.move(cfg, self.tmp.name, "/srv/media", "http://x", helper=lambda f, s: (1, "Error: no such image"))
        self.assertEqual(said, "")
        self.assertTrue(cfg.data["extras"]["livetv"])

    def test_the_program_runs_reports_and_answers(self):
        d = self.tmp.name
        settings, jellyfin, status = (os.path.join(d, n) for n in ("settings.json", "jellyfin.json", "status.json"))
        json.dump({"address": "http://192.168.1.20:8095", "white_logos": True, "jellyfin_folder": "/config/iptv"}, open(settings, "w"))
        json.dump({"url": "http://host.docker.internal:8097", "api_key": "made-up-jf-key"}, open(jellyfin, "w"))
        seen = {}
        with mock.patch.multiple(livetv_plugin, SETTINGS=settings, JELLYFIN=jellyfin, STATUS=status):
            said = livetv_plugin.run_once(build=lambda addr, white, force: (seen.update(addr=addr, white=white) or "Guides refreshed"),
                                          connect=lambda services, extras, dd, **k: (seen.update(svc=services, folder=extras) or "Jellyfin: added 2"))
            self.assertEqual(said, "Guides refreshed · Jellyfin: added 2")
            self.assertEqual(seen["svc"][0]["url"], "http://host.docker.internal:8097")
            self.assertEqual(seen["folder"], {"livetv_jellyfin_folder": "/config/iptv"})
            self.assertEqual(livetv_plugin.card()["state"], "warning")  # not run yet
            livetv_plugin._save_status(state="failed", finished=0, summary="no network")
            self.assertEqual(livetv_plugin.card()["state"], "problem")
            plugin_cards.clean("status", livetv_plugin.card())  # the card's shape is what Starboard draws
            srv = ThreadingHTTPServer(("127.0.0.1", 0), livetv_plugin.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self.addCleanup(srv.shutdown)
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            self.assertEqual(urllib.request.urlopen(base + "/health").status, 200)
            r = urllib.request.urlopen(urllib.request.Request(base + "/run", data=b"", method="POST"))
            self.assertEqual(r.status, 202)
            self.assertTrue(livetv_plugin._force["now"])

    def test_a_guide_running_short_is_due_and_new_guides_reach_jellyfin(self):
        # Owner, 10 November 2026: Samsung's guide covers about ten hours, so a daily refresh left it empty by the
        # evening, and Jellyfin kept the morning's guide.
        import time as _t
        from starboard import livetv
        d = self.tmp.name
        guide = os.path.join(d, "guide-samsung.xml")
        end = _t.strftime("%Y%m%d%H%M%S", _t.gmtime(_t.time() + 3 * 3600))
        open(guide, "w").write(f'<tv><programme start="20261110000000 +0000" stop="{end} +0100" channel="a"/></tv>')
        self.assertAlmostEqual(livetv.guide_end(guide), _t.time() + 2 * 3600, delta=5)
        self.assertTrue(livetv._short(guide))  # fresh file, but only two hours left
        later = _t.strftime("%Y%m%d%H%M%S", _t.gmtime(_t.time() + 20 * 3600))
        open(guide, "w").write(f'<tv><programme start="x" stop="{later}" channel="a"/></tv>')
        self.assertFalse(livetv._short(guide))
        self.assertEqual(livetv.guide_end(os.path.join(d, "none.xml")), 0)
        settings, jellyfin, status = (os.path.join(d, n) for n in ("settings.json", "jellyfin.json", "status.json"))
        json.dump({"address": "http://192.168.1.20:8095"}, open(settings, "w"))
        json.dump({"url": "http://jf.example:8096", "api_key": "made-up-jf-key"}, open(jellyfin, "w"))
        asked = []

        def build(*a, **k):
            open(os.path.join(d, "guide-pluto.xml"), "w").write("<tv/>")  # a guide written this run
            return "pluto guide: 10 programmes"
        with mock.patch.multiple(livetv_plugin, SETTINGS=settings, JELLYFIN=jellyfin, STATUS=status), \
                mock.patch.object(livetv, "folder", return_value=d):
            said = livetv_plugin.run_once(build=build, connect=lambda *a, **k: "", refresh=lambda svc: asked.append(svc) or "Jellyfin: reading the new guides")
            self.assertEqual(said, "pluto guide: 10 programmes · Jellyfin: reading the new guides")
            self.assertEqual(asked[0][0]["url"], "http://jf.example:8096")
            asked.clear()
            livetv_plugin.run_once(build=lambda *a, **k: "Nothing due", connect=lambda *a, **k: "", refresh=lambda svc: asked.append(svc))
            self.assertEqual(asked, [])  # no new guide: Jellyfin is not asked

    def test_channels_can_be_turned_off_and_stay_off(self):
        # DASH-313 (owner, 11 November 2026): 330 of 546 channels removed by hand; now a screen in Starboard.
        from starboard import livetv
        d = self.tmp.name
        with open(os.path.join(d, "samsung.m3u"), "w") as f:
            f.write('#EXTM3U\n#EXTINF:-1 tvg-id="A1" tvg-chno="101",Keep\nhttp://a\n#EXTINF:-1 tvg-id="B2" tvg-chno="102",Drop\nhttp://b\n')
        with open(os.path.join(d, livetv.ALL), "w") as f:
            json.dump([{"id": "A1", "name": "Keep", "number": "101", "section": "Entertainment", "list": "samsung.m3u"},
                       {"id": "B2", "name": "Drop", "number": "102", "section": "Entertainment", "list": "samsung.m3u"}], f)
        with mock.patch.object(livetv, "folder", return_value=d), mock.patch.object(livetv_plugin, "DATA", d), \
                mock.patch.object(livetv_plugin, "JELLYFIN", os.path.join(d, "none.json")):
            out = livetv_plugin.channels_act({"action": "toggle", "id": "B2"})
            self.assertIn("Drop deactivated", out["said"])
            self.assertEqual([(r["title"], r["on"]) for r in out["items"]], [("101 Keep", True), ("102 Drop", False)])
            self.assertEqual([c["name"] for c in livetv._parse(os.path.join(d, "samsung.m3u"))], ["Keep"])
            out = livetv_plugin.channels_act({"action": "toggle", "id": "B2"})
            self.assertIn("Drop activated", out["said"])
            self.assertEqual(livetv.hidden_ids(d), set())
            with self.assertRaises(ValueError):
                livetv_plugin.channels_act({"action": "toggle", "id": "nope"})

    def test_whole_sources_regions_and_sections_activate_and_deactivate_at_once(self):
        # DASH-359 (owner, 12 November 2026): switches for each source and group, and for every channel at once.
        from starboard import livetv
        d = self.tmp.name
        chans = [("F1", "BBC One", "101", "Entertainment", "channels.m3u", "UK"), ("S1", "Sky News", "801", "News", "samsung.m3u", "UK"),
                 ("S2", "CBS News", "802", "News", "samsung.m3u", "US"), ("P1", "Pluto Films", "451", "Movies", "pluto.m3u", None)]
        for name in livetv.FILES:
            with open(os.path.join(d, name), "w") as f:
                f.write("#EXTM3U\n" + "".join(f'#EXTINF:-1 tvg-id="{i}" tvg-chno="{n}",{t}\nhttp://{i}\n' for i, t, n, _, lst, _r in chans if lst == name))
        with open(os.path.join(d, livetv.ALL), "w") as f:
            json.dump([{"id": i, "name": t, "number": n, "section": sec, "list": lst, **({"region": r} if r else {})}
                       for i, t, n, sec, lst, r in chans], f)
        refreshed = []
        with mock.patch.object(livetv, "folder", return_value=d), mock.patch.object(livetv_plugin, "DATA", d), \
                mock.patch.object(livetv_plugin, "JELLYFIN", os.path.join(d, "none.json")), \
                mock.patch("starboard.livetv_jellyfin.refresh_guide", side_effect=lambda svc: refreshed.append(svc)):
            screen = livetv_plugin.channels_screen()
            sets = {b["id"]: (b["kind"], b["on"], b["total"]) for b in screen["bulk"]}
            self.assertEqual([b["id"] for b in screen["bulk"][:4]], ["lists:freetv", "lists:samsung", "lists:pluto", "all"])
            self.assertEqual(sets["all"], ("Channels", 4, 4))
            self.assertEqual(sets["lists:samsung"], ("Lists", 2, 2))
            self.assertEqual(sets["regions:UK"], ("Regions", 3, 3))  # Pluto TV, saved before regions were, is UK
            self.assertEqual(sets["regions:US"], ("Regions", 1, 1))
            self.assertEqual(sets["sections:News"], ("Sections", 2, 2))
            self.assertEqual([(b["label"], b["active"]) for b in screen["bulk"] if b["kind"] == "Lists"],
                             [("Free-TV", True), ("Samsung TV Plus", True), ("Pluto TV", True)])
            self.assertIn("Free-TV · UK", [r["detail"] for r in screen["items"]])

            out = livetv_plugin.channels_act({"action": "bulk", "id": "sections:News", "value": "off"})
            self.assertEqual(out["said"], "News: 2 channels deactivated; Jellyfin drops them at its guide refresh, starting now")
            self.assertEqual(livetv.hidden_ids(d), {"S1", "S2"})
            self.assertEqual(livetv._parse(os.path.join(d, "samsung.m3u")), [])
            self.assertEqual(len(refreshed), 1)
            self.assertEqual({b["id"]: b["on"] for b in out["bulk"]}["lists:samsung"], 0)

            out = livetv_plugin.channels_act({"action": "bulk", "id": "regions:US", "value": "on"})
            self.assertIn("US: 1 channel activated", out["said"])
            self.assertEqual(livetv.hidden_ids(d), {"S1"})
            self.assertTrue(livetv_plugin._force["now"])  # the lists are rebuilt with it

            out = livetv_plugin.channels_act({"action": "bulk", "id": "all", "value": "off"})
            self.assertEqual(livetv.hidden_ids(d), {"F1", "S1", "S2", "P1"})
            self.assertEqual({b["id"]: b["on"] for b in out["bulk"]}["all"], 0)
            out = livetv_plugin.channels_act({"action": "bulk", "id": "all", "value": "off"})
            self.assertEqual(out["said"], "Every channel: 4 channels already inactive")
            out = livetv_plugin.channels_act({"action": "bulk", "id": "all", "value": "on"})
            self.assertEqual(livetv.hidden_ids(d), set())

            # A whole list (owner, 12 November 2026: the original list off in full, a switch for each of the others)
            out = livetv_plugin.channels_act({"action": "bulk", "id": "lists:freetv", "value": "off"})
            self.assertIn("Free-TV deactivated: not fetched, and its 1 channel leaves Jellyfin now", out["said"])
            self.assertEqual(livetv.lists_off(d), {"freetv"})
            self.assertEqual(livetv._parse(os.path.join(d, "channels.m3u")), [])
            self.assertNotIn("F1", [c["id"] for c in livetv.all_channels(d)])
            lists = {b["id"]: b for b in out["bulk"] if b["kind"] == "Lists"}
            self.assertFalse(lists["lists:freetv"]["active"])
            self.assertIn("not fetched", lists["lists:freetv"]["hint"])
            self.assertTrue(lists["lists:pluto"]["active"])
            self.assertIn("already inactive", livetv_plugin.channels_act({"action": "bulk", "id": "lists:freetv", "value": "off"})["said"])
            livetv_plugin._force["now"] = False
            out = livetv_plugin.channels_act({"action": "bulk", "id": "lists:freetv", "value": "on"})
            self.assertIn("Free-TV activated", out["said"])
            self.assertEqual(livetv.lists_off(d), set())
            self.assertTrue(livetv_plugin._force["now"])
            with self.assertRaises(ValueError):
                livetv_plugin.channels_act({"action": "bulk", "id": "lists:nope", "value": "on"})

            for bad in ({"id": "sections:Nope", "value": "on"}, {"id": "all", "value": "maybe"}):
                with self.assertRaises(ValueError):
                    livetv_plugin.channels_act({"action": "bulk", **bad})
        livetv_plugin._force["now"] = False

    def test_built_in_plug_ins_follow_starboards_update(self):
        cfg = FakeConfig(self.tmp.name, {"livetv": True})
        runs = []
        helper = lambda folder, script: (runs.append(script) or (0, ""))
        with mock.patch.object(livetv_move, "can_run", return_value=""), mock.patch.object(pa, "host_for_builtin", return_value=HOST):
            livetv_move.move(cfg, self.tmp.name, "/srv/media", "http://192.168.1.20:8095", helper=helper)
        compose = os.path.join(pa.folder(self.tmp.name, "livetv"), "compose.yaml")
        with open(compose, "w") as f:
            f.write("services: {}\n")  # as an older version wrote it
        again = pa.refresh_builtins(self.tmp.name, "/srv/media", cfg.data["services"], helper=helper, host=HOST)
        self.assertEqual(again, ["Live TV"])
        with open(compose) as f:
            self.assertIn("healthcheck:", f.read())
        self.assertIn("chown", runs[-1])
        self.assertIn("up -d", runs[-1])

    def test_an_address_is_needed(self):
        settings = os.path.join(self.tmp.name, "settings.json")
        json.dump({}, open(settings, "w"))
        with mock.patch.object(livetv_plugin, "SETTINGS", settings):
            with self.assertRaisesRegex(ValueError, "address Jellyfin uses"):
                livetv_plugin.run_once(build=lambda *a, **k: "", connect=lambda *a, **k: "")


if __name__ == "__main__":
    unittest.main()


class InactiveListTest(unittest.TestCase):
    def test_an_inactive_list_is_not_fetched_and_is_emptied_once(self):
        # DASH-359 (owner, 12 November 2026): the original list off in full; the others each with a switch.
        from starboard import livetv
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as data:
            with open(os.path.join(d, "freetv-source.m3u"), "w") as f:
                f.write('#EXTM3U\n#EXTINF:-1 tvg-id="F1",BBC One\nhttp://f1\n')
            with open(os.path.join(d, "channels.m3u"), "w") as f:
                f.write('#EXTM3U\n#EXTINF:-1 tvg-id="F1" tvg-chno="101",BBC One\nhttp://f1\n')
            with open(os.path.join(d, livetv.ALL), "w") as f:
                json.dump([{"id": "F1", "name": "BBC One", "number": "101", "section": "Entertainment", "list": "channels.m3u"}], f)
            livetv.save_lists_off(data, {"freetv", "samsung", "pluto", "made-up"})
            self.assertEqual(livetv.lists_off(data), {"freetv", "samsung", "pluto"})
            fetched = []
            with mock.patch.object(livetv, "folder", return_value=d), mock.patch.dict(os.environ, {"STARBOARD_DATA": data}), \
                    mock.patch.object(livetv, "build_guide", side_effect=lambda dd: fetched.append("guide") or "Guide"), \
                    mock.patch.object(livetv, "build_freetv", side_effect=lambda dd: fetched.append("freetv") or "Free-TV"), \
                    mock.patch.object(livetv, "_channels_json", side_effect=lambda s: fetched.append(s)), \
                    mock.patch.object(livetv, "number_and_logos", return_value="Numbered 0 channels"):
                said = livetv.run("http://starboard:8090", False, force=True)
                self.assertEqual(fetched, [])
                self.assertIn("Free-TV: inactive, emptied", said)
                self.assertEqual(livetv._parse(os.path.join(d, "channels.m3u")), [])
                self.assertEqual(livetv.all_channels(d), [])
                with open(os.path.join(d, "guide.xml")) as f:
                    self.assertIn("<tv", f.read())
                self.assertNotIn("inactive", livetv.run("http://starboard:8090", False, force=True))  # once only
                livetv.save_lists_off(data, {"samsung", "pluto"})
                livetv.run("http://starboard:8090", False)
                self.assertEqual(fetched, ["guide", "freetv"])  # activated: built again as new
