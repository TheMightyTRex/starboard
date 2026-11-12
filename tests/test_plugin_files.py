"""DASH-357: what a plug-in's containers read reaches them as one folder (run/), readable by any container user and
current at once; buttons without an id run; health is asked by Starboard; the main container rests when idle."""
import copy
import json
import os
import stat
import tempfile
import time
import unittest
from unittest import mock

from starboard import plugin_cards, plugin_tester, plugin_watch, plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND

OLD_COMPOSE = '''services:
  plugin-on-demand-main:
    image: "x"
    volumes:
      - "/srv/data/plugins/on-demand/data/main:/data"
      - "/srv/data/plugins/on-demand/settings.json:/run/starboard/settings.json:ro"
      - "/srv/data/plugins/on-demand/key:/run/starboard/key:ro"
      - "/srv/data/plugins/on-demand/jellyfin.json:/run/starboard/jellyfin.json:ro"
    environment:
      TZ: "Europe/London"
  plugin-on-demand-engine:
    volumes:
      - "/srv/data/plugins/on-demand/settings.json:/run/starboard/settings.json:ro"
      - "/srv/data/plugins/on-demand/key:/run/starboard/key:ro"
'''


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (("host_path", lambda d, pid: f"/srv/data/plugins/{pid}"),):
            p = mock.patch.object(pa, name, side_effect=value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(pa, "_compose_run", return_value=(True, ""))
        self.compose = p.start()
        self.addCleanup(p.stop)
        self.where = os.path.join(self.tmp.name, "plugins", "on-demand")

    def add(self, manifest=ON_DEMAND):
        pa.install(self.tmp.name, manifest, "/srv/media")
        return self.where


class Files(Base):
    def test_compose_mounts_one_folder(self):
        text = plugins.compose(ON_DEMAND, "/srv/data/plugins/on-demand", "/srv/media")
        self.assertIn('"/srv/data/plugins/on-demand/run:/run/starboard:ro"', text)
        self.assertNotIn("settings.json:/run", text)
        self.assertNotIn("key:/run", text)

    def test_run_folder_is_readable_inside_an_owner_only_folder(self):
        where = self.add()
        run = os.path.join(where, "run")
        self.assertEqual(mode(where), 0o700)
        self.assertEqual(mode(run), 0o755)
        for name in ("settings.json", "key"):
            self.assertEqual(mode(os.path.join(run, name)), 0o644, name)
            self.assertEqual(mode(os.path.join(where, name)), 0o600, name)  # Starboard's own copy stays owner-only

    def test_a_saved_setting_reaches_run_at_once(self):
        where = self.add()
        pa.save_settings(self.tmp.name, "on-demand", {"quality": "720p"})
        with open(os.path.join(where, "run", "settings.json")) as f:
            self.assertEqual(json.load(f)["quality"], "720p")

    def test_jellyfin_details_follow_and_go(self):
        where = self.add()
        pa.write_jellyfin(self.tmp.name, "on-demand", [{"type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "made-up"}])
        with open(os.path.join(where, "run", "jellyfin.json")) as f:
            self.assertEqual(json.load(f)["url"], "http://host.docker.internal:8096")
        os.remove(os.path.join(where, "jellyfin.json"))
        pa.share(where)
        self.assertFalse(os.path.exists(os.path.join(where, "run", "jellyfin.json")))

    def test_old_compose_files_are_upgraded_once(self):
        where = self.add()
        with open(os.path.join(where, "compose.yaml"), "w") as f:
            f.write(OLD_COMPOSE)
        self.assertTrue(pa.upgrade_mounts(where))
        with open(os.path.join(where, "compose.yaml")) as f:
            text = f.read()
        self.assertEqual(text.count('"/srv/data/plugins/on-demand/run:/run/starboard:ro"'), 2)
        self.assertNotIn("settings.json:/run", text)
        self.assertIn('"/srv/data/plugins/on-demand/data/main:/data"', text)
        self.assertIn('TZ: "Europe/London"', text)
        self.assertFalse(pa.upgrade_mounts(where))

    def test_upgrade_all_restarts_only_active_plugins_that_changed(self):
        where = self.add()
        with open(os.path.join(where, "compose.yaml"), "w") as f:
            f.write(OLD_COMPOSE)
        pa.set_state(self.tmp.name, "on-demand", "enabled")
        self.assertEqual(pa.upgrade_all(self.tmp.name, []), [ON_DEMAND["name"]])
        self.assertEqual(pa.upgrade_all(self.tmp.name, []), [])

    def test_roll_back_shares_the_files_it_moved(self):
        from starboard import plugin_life
        where = self.add()
        newer = {**copy.deepcopy(ON_DEMAND), "version": "9.9.9"}
        plugin_life.update(self.tmp.name, "on-demand", newer, "/srv/media")
        pa.save_settings(self.tmp.name, "on-demand", {"quality": "720p"})
        pa.set_state(self.tmp.name, "on-demand", "enabled")
        plugin_life.rollback(self.tmp.name, "on-demand", "/srv/media")
        with open(os.path.join(where, "settings.json")) as a, open(os.path.join(where, "run", "settings.json")) as b:
            self.assertEqual(a.read(), b.read())


class Buttons(Base):
    def test_a_button_without_an_id_runs_by_its_place(self):
        m = copy.deepcopy(ON_DEMAND)
        m["actions"] = [{"label": "Update now", "path": "/api/sync"}]
        self.add(m)
        seen = {}

        class Opener:
            def open(self, req, timeout=None):
                seen["url"] = req.full_url
                return mock.MagicMock(**{"__enter__.return_value.read.return_value": b'{"said": "Done"}'})

        listed = next(p for p in pa.listing(self.tmp.name) if p["id"] == "on-demand")
        with mock.patch.object(plugin_cards, "_host", return_value="plugin-on-demand-main"):
            out = plugin_cards.action(self.tmp.name, "on-demand", listed["actions"][0]["id"], opener=Opener())
        self.assertEqual(out["said"], "Done")
        self.assertTrue(seen["url"].endswith("/api/sync"))


class Health(Base):
    def setUp(self):
        super().setUp()
        plugin_watch._health.clear()

    def test_health_is_asked_once_a_minute_and_says_why_not(self):
        self.add()
        pa.set_state(self.tmp.name, "on-demand", "enabled")
        with mock.patch.object(plugin_watch, "_ask", return_value="Its health check answered 500") as ask:
            out = plugin_watch.health(self.tmp.name, pa.listing(self.tmp.name))
            plugin_watch.health(self.tmp.name, pa.listing(self.tmp.name))
        self.assertEqual(out, {"on-demand": "Its health check answered 500"})
        self.assertEqual(ask.call_count, 1)

    def test_inactive_plugins_are_not_asked(self):
        self.add()
        with mock.patch.object(plugin_watch, "_ask") as ask:
            self.assertEqual(plugin_watch.health(self.tmp.name, pa.listing(self.tmp.name)), {})
        ask.assert_not_called()


class Idle(Base):
    def setUp(self):
        super().setUp()
        self.m = copy.deepcopy(ON_DEMAND)
        self.m["containers"][0].update(start="when_needed", idle_stop_minutes=15)
        self.add(self.m)
        pa.set_state(self.tmp.name, "on-demand", "enabled")
        plugin_watch._last_used.pop("on-demand", None)
        p = mock.patch.object(plugin_watch, "DATA_DIR", self.tmp.name)
        p.start()
        self.addCleanup(p.stop)

    def later(self, minutes):
        return plugin_watch._started + minutes * 60

    def test_rests_only_when_starboard_and_the_network_are_both_quiet(self):
        busy = lambda pid, main, now: now  # noqa: E731 - traffic right now
        self.assertEqual(plugin_watch.rest_idle(self.tmp.name, self.later(20), moved=busy), [])
        quiet = lambda pid, main, now: plugin_watch._started  # noqa: E731
        plugin_watch._last_used["on-demand"] = self.later(10)
        self.assertEqual(plugin_watch.rest_idle(self.tmp.name, self.later(20), moved=quiet), [])
        self.assertEqual(plugin_watch.rest_idle(self.tmp.name, self.later(26), moved=quiet), ["on-demand"])
        self.assertEqual(plugin_watch.resting(self.tmp.name, "on-demand"), ["main"])
        self.assertIn("stop plugin-on-demand-main", self.compose.call_args[0][2])

    def test_only_the_main_container_rests(self):
        self.m["containers"][0].pop("start")
        with open(os.path.join(self.where, "manifest.json"), "w") as f:
            json.dump(self.m, f)
        self.assertFalse(plugin_watch.wanted(self.tmp.name))
        quiet = lambda pid, main, now: 0  # noqa: E731
        self.assertEqual(plugin_watch.rest_idle(self.tmp.name, self.later(60), moved=quiet), [])
        issues = plugin_tester.run(ON_DEMAND)
        self.assertTrue(any(i["where"] == "containers[1]" and "first container" in i["what"] for i in issues))

    def test_a_call_wakes_it_and_activate_clears_resting(self):
        plugin_watch._set_resting(self.tmp.name, "on-demand", ["main"])
        with mock.patch("socket.create_connection"), mock.patch.object(plugin_cards, "_host", wraps=lambda pid, main, wake=True: "x"):
            plugin_watch.used("on-demand", self.m["containers"][0])
        self.assertIn("up -d plugin-on-demand-main", self.compose.call_args[0][2])
        self.assertEqual(plugin_watch.resting(self.tmp.name, "on-demand"), [])
        plugin_watch._set_resting(self.tmp.name, "on-demand", ["main"])
        pa.enable(self.tmp.name, "on-demand")
        self.assertEqual(plugin_watch.resting(self.tmp.name, "on-demand"), [])


if __name__ == "__main__":
    unittest.main()
