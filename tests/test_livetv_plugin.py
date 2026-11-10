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
                     '"/srv/apps/jellyfin/iptv:/iptv"', "host.docker.internal:host-gateway", "jellyfin.json:/run/starboard/jellyfin.json:ro",
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
