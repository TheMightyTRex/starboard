"""Automatic updates for everything (DASH-422): each part deactivated until chosen, only in the update hours and once
a day, the copy first, the way back, What is new afterwards, and an alert when something failed or waits."""
import datetime as dt
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auto_updates as au, backup, config as config_mod, jobs, self_update, update_runs
from tests.jellyfin_stand_in import KEY, StandIn

NIGHT = dt.datetime(2026, 11, 16, 3, 0)
DAY = dt.datetime(2026, 11, 16, 14, 0)


class FakeWatch:
    def __init__(self):
        self.sent = []

    def alert(self, key, title, text, level="problem"):
        self.sent.append((key, title, text, level))


class FakeApp:
    def __init__(self, **settings):
        self.data_dir = tempfile.mkdtemp()
        self.config = mock.Mock(data={"services": [], "download_hours": {"enabled": False, "start": 1, "end": 6}, **settings})
        self.watch = FakeWatch()
        self.version = "0.18.0"


class Rules(unittest.TestCase):
    def test_every_part_is_deactivated_by_default_admin_only_and_in_the_backup(self):
        for p in au.PARTS:
            self.assertIs(config_mod.DEFAULTS[p["key"]], False, p["key"])
            self.assertEqual(config_mod.GENERAL_RIGHTS[p["key"]], "admin")
            self.assertIn(p["key"], backup.GENERAL_KEYS)
            self.assertEqual(jobs.AUTO[p["job"]], p["key"])
        self.assertEqual(config_mod.DEFAULTS["auto_update_hours"], "download")
        self.assertIn("auto_update_hours", backup.GENERAL_KEYS)

    def test_the_hours_are_the_download_hours_or_always_the_quiet_hours(self):
        hours = {"enabled": True, "start": 22, "end": 4}
        self.assertEqual(self_update.update_hours({"download_hours": hours}), (22, 4))
        self.assertEqual(self_update.update_hours({"download_hours": hours, "auto_update_hours": "quiet"}), (1, 6))
        self.assertEqual(self_update.update_hours({"download_hours": {"enabled": False}}), (1, 6))
        self.assertTrue(au.in_hours({"download_hours": hours}, dt.datetime(2026, 11, 16, 23, 0)))
        self.assertFalse(au.in_hours({"download_hours": hours, "auto_update_hours": "quiet"}, dt.datetime(2026, 11, 16, 23, 0)))
        self.assertEqual(au.hours_words({"download_hours": hours}), "your download hours, 22:00 to 04:00")
        self.assertEqual(au.hours_words({}), "the quiet hours, 01:00 to 06:00")

    def test_the_choice_of_hours_is_checked(self):
        cfg = config_mod.Config(tempfile.mkdtemp())
        cfg.update_general({"auto_update_hours": "quiet", "apps_auto_update": True})
        self.assertEqual(cfg.data["auto_update_hours"], "quiet")
        self.assertTrue(cfg.public()["apps_auto_update"])
        with self.assertRaises(config_mod.ConfigError):
            cfg.update_general({"auto_update_hours": "midday"})

    def test_a_part_looks_only_when_activated_in_the_hours_and_once_a_day(self):
        app = FakeApp()
        self.assertEqual(au.due(app, "apps", NIGHT), (False, "Deactivated"))
        app.config.data["apps_auto_update"] = True
        self.assertEqual(au.due(app, "apps", DAY), (False, "Waiting for the update hours"))
        self.assertEqual(au.due(app, "apps", NIGHT), (True, ""))
        au._finish(app, "apps", [], NIGHT)
        self.assertEqual(au.due(app, "apps", NIGHT), (False, "Already looked today"))
        self.assertEqual(au.due(app, "apps", NIGHT + dt.timedelta(days=1)), (True, ""))

    def test_outside_the_hours_nothing_is_asked(self):
        app = FakeApp(apps_auto_update=True, plugins_auto_update=True)
        with mock.patch("starboard.containers.check") as check, mock.patch("starboard.plugins_admin.catalogue") as cat:
            self.assertEqual(au.apps(app, DAY), "Waiting for the update hours")
            self.assertEqual(au.plugins(app, DAY), "Waiting for the update hours")
        check.assert_not_called()
        cat.assert_not_called()


class Apps(unittest.TestCase):
    def rows(self):
        c = {"name": "sonarr", "compose": True, "version": "4.0.10"}
        return {"items": [{"id": "s1", "name": "Sonarr", "update": True, "latest": "4.0.11", "container": c},
                          {"id": "r1", "name": "Reelix", "update": True, "latest": "0.7.2", "container": dict(c, name="reelix")},
                          {"id": "x1", "name": "Pinned", "update": True, "latest": "2", "container": dict(c, name="pinned", compose=False)},
                          {"id": "q1", "name": "Quiet", "update": False, "latest": "", "container": dict(c, name="quiet")}]}

    def run_apps(self, app, state):
        started = []

        def start(a, target, by="you", address=""):
            started.append((target, by))
            return {"id": "r" + str(len(started))}
        got = {"target": "app:s1", "name": "Sonarr", "from": "4.0.10", "to": "4.0.11", "state": state, "said": "said"}
        services = [{"id": "r1", "icon": "reelix", "type": "link"}]
        app.config.data["services"] = services
        with mock.patch("starboard.containers.available", return_value=True), \
                mock.patch("starboard.containers.check", return_value=self.rows()), \
                mock.patch.object(update_runs, "start", side_effect=start), \
                mock.patch.object(update_runs, "get", return_value=got):
            said = au.apps(app, NIGHT)
        return said, started

    def test_each_app_with_a_new_version_updates_by_itself_but_not_reelix_or_one_compose_did_not_start(self):
        app = FakeApp(apps_auto_update=True)
        said, started = self.run_apps(app, "updated")
        self.assertEqual(started, [("app:s1", "automatic")])
        self.assertEqual(said, "Updated Sonarr")
        key, title, text, level = app.watch.sent[-1]
        self.assertEqual((title, level), ("Updated by itself", "info"))
        self.assertIn("Sonarr 4.0.10 to 4.0.11", text)
        self.assertIn("Recent updates", text)

    def test_a_version_that_went_back_waits_until_it_is_updated_by_hand(self):
        app = FakeApp(apps_auto_update=True)
        said, started = self.run_apps(app, "went-back")
        self.assertIn("Not updated: Sonarr", said)
        self.assertTrue(au.skipped(app.data_dir, "app:s1", "4.0.11"))
        _, started = self.run_apps(app, "updated")  # the next night (the day's look is forgotten here)
        self.assertEqual(started, [])
        au.forget_skip(app.data_dir, "app:s1")
        self.assertFalse(au.skipped(app.data_dir, "app:s1", "4.0.11"))

    def test_no_docker_access_says_so(self):
        app = FakeApp(apps_auto_update=True)
        with mock.patch("starboard.containers.available", return_value=False):
            self.assertIn("no Docker access", au.apps(app, NIGHT))

    def test_an_app_update_makes_a_copy_of_its_settings_first_without_its_caches(self):
        c = {"id": "abc", "name": "sonarr", "folder": "/srv/stack"}
        with mock.patch("starboard.containers.docker", return_value={"Mounts": [{"Destination": "/config"}]}), \
                mock.patch("starboard.containers._helper", return_value=(0, "")) as helper:
            state, said = update_runs.save_app_settings(c)
        self.assertEqual(state, "done")
        script = helper.call_args[0][1]
        self.assertIn("--volumes-from sonarr", script)
        self.assertIn("--exclude=config/MediaCover", script)
        self.assertIn("> sonarr-before-update.tgz.new && mv sonarr-before-update.tgz.new sonarr-before-update.tgz", script)
        with mock.patch("starboard.containers.docker", return_value={"Mounts": [{"Destination": "/data"}]}):
            self.assertEqual(update_runs.save_app_settings(c)[0], "skipped")
        self.assertEqual(update_runs.save_app_settings(dict(c, name="bad name; rm"))[0], "skipped")
        with mock.patch("starboard.containers.docker", return_value={"Mounts": [{"Destination": "/config"}]}), \
                mock.patch("starboard.containers._helper", return_value=(1, "no space")):
            self.assertEqual(update_runs.save_app_settings(c)[0], "failed")


class Plugins(unittest.TestCase):
    def setUp(self):
        from starboard import plugins_admin as pa
        self.pa = pa
        self.app = FakeApp(plugins_auto_update=True)
        self.app.config.data["plugin_catalogues"] = []
        for pid, perms in (("line-speed", ["apps:read"]), ("disk-forecast", ["apps:read"])):
            where = pa.folder(self.app.data_dir, pid)
            os.makedirs(where, exist_ok=True)
            pa._write(os.path.join(where, "manifest.json"), {"id": pid, "name": pid.title(), "version": "1.0.0", "permissions": perms})
            pa._write(os.path.join(where, "state.json"), {"state": "enabled"})

    def test_new_permissions_wait_for_the_owner_and_an_address_is_looked_at(self):
        au.remember_address(self.app.data_dir, "disk-forecast", "https://example.invalid/disk-forecast.json")
        listing = [{"id": "line-speed", "name": "Line speed", "version": "1.0.0"}, {"id": "disk-forecast", "name": "Disk forecast", "version": "1.0.0"}]
        known = {"line-speed": {"version": "1.1.0", "manifest": "https://example.invalid/ls.json", "sha256": "", "changelog": ""}}
        manifests = {"https://example.invalid/ls.json": {"id": "line-speed", "version": "1.1.0", "permissions": ["apps:read", "jellyfin:admin"]},
                     "https://example.invalid/disk-forecast.json": {"id": "disk-forecast", "version": "1.2.0", "permissions": ["apps:read"]}}
        started = []
        with mock.patch.object(self.pa, "listing", return_value=listing), mock.patch.object(self.pa, "catalogue"), \
                mock.patch("starboard.plugin_life.updates_known", return_value=known), \
                mock.patch.object(self.pa, "fetch_manifest", side_effect=lambda a, sha256="", opener=None: manifests[a]), \
                mock.patch.object(au, "_run", side_effect=lambda app, target, address="": started.append((target, address)) or
                                  {"target": target, "name": target, "from": "1.0.0", "to": "1.2.0", "state": "updated", "said": ""}):
            said = au.plugins(self.app, NIGHT)
        self.assertEqual(started, [("plugin:disk-forecast", "https://example.invalid/disk-forecast.json")])
        self.assertIn("asks for new permissions, so it waits for you", said)
        self.assertTrue(any(t == "An update waits for you" for _, t, _, _ in self.app.watch.sent))


class JellyfinPlugins(unittest.TestCase):
    def setUp(self):
        self.jf = StandIn(plugins=[{"Name": "Playback Reporting", "Version": "19.0.0.0", "Status": "Active", "Id": "p1"},
                                   {"Name": "Trakt", "Version": "31.0.0.0", "Status": "Active", "Id": "t1"}])
        self.app = FakeApp(jellyfin_plugins_auto_update=True)
        self.app.config.data["services"] = [{"type": "jellyfin", "name": "Jellyfin", "url": "http://jellyfin.invalid", "api_key": KEY}]
        update_runs._runs.clear()
        update_runs._loaded.discard(self.app.data_dir)

        def call(jf, method, path, body=None):
            code, answer = self.jf.handle(method, path, body, {"Authorization": f'MediaBrowser Token="{KEY}"'})
            if code >= 400:
                raise ValueError(f"Jellyfin answered {code}")
            if path == "/System/Restart":
                self.jf.restart()
            return answer
        patcher = mock.patch.object(au, "_jf_call", side_effect=call)
        patcher.start()
        self.addCleanup(patcher.stop)
        for p in ("starboard.containers.available",):
            m = mock.patch(p, return_value=False)
            m.start()
            self.addCleanup(m.stop)

    def run_now(self):
        return au.jellyfin_plugins_run(self.app, sleep=lambda s: None, task_wait=1, restart_wait=1)

    def test_an_update_restarts_jellyfin_and_checks_each_plug_in(self):
        self.jf.updates = {"p1": "20.0.0.0"}
        run = self.run_now()
        self.assertEqual(run["state"], "updated")
        self.assertIn("Playback Reporting 19.0.0.0 to 20.0.0.0", run["said"])
        self.assertEqual({s["id"]: s["state"] for s in run["steps"]}["health"], "done")
        self.assertIn(("POST", "/System/Restart"), self.jf.calls)

    def test_nobody_is_interrupted_while_watching(self):
        self.jf.updates = {"p1": "20.0.0.0"}
        self.jf.sessions = [{"NowPlayingItem": {"Name": "A film"}}]
        run = self.run_now()
        self.assertEqual(run["state"], "updated")
        self.assertIn("Someone is watching", run["said"])
        self.assertNotIn(("POST", "/System/Restart"), self.jf.calls)

    def test_a_plug_in_that_does_not_start_is_said_with_the_copy(self):
        self.jf.updates, self.jf.broken = {"t1": "32.0.0.0"}, {"t1"}
        run = self.run_now()
        self.assertEqual(run["state"], "failed")
        self.assertIn("Trakt did not start", run["said"])
        self.assertIn("jellyfin-plugins-before-update.tgz", run["said"])
        self.assertEqual(self.app.watch.sent[-1][1], "Jellyfin's plug-ins was not updated")

    def test_up_to_date(self):
        self.assertEqual(self.run_now()["state"], "up-to-date")

    def test_jellyfins_own_schedule_moves_aside_once_when_activated(self):
        task = next(t for t in self.jf.tasks if t["Key"] == "PluginUpdates")
        self.assertTrue(task["Triggers"])
        self.assertTrue(au.jellyfin_status(self.app)["own_schedule"])
        self.assertTrue(au.take_over_schedule(self.app))
        self.assertEqual(task["Triggers"], [])
        task["Triggers"] = [{"Type": "DailyTrigger"}]  # the owner schedules it again in Jellyfin: left alone
        self.assertFalse(au.take_over_schedule(self.app))
        self.assertTrue(task["Triggers"])

    def test_the_job_runs_once_a_day_in_the_hours(self):
        self.jf.updates = {"p1": "20.0.0.0"}
        real = au.jellyfin_plugins_run
        with mock.patch.object(au, "jellyfin_plugins_run", side_effect=lambda app: real(app, sleep=lambda s: None, task_wait=1, restart_wait=1)) as run:
            self.assertEqual(au.jellyfin_plugins(self.app, DAY), "Waiting for the update hours")
            self.assertIn("Updated Jellyfin's plug-ins", au.jellyfin_plugins(self.app, NIGHT))
            self.assertEqual(au.jellyfin_plugins(self.app, NIGHT), "Already looked today")
        self.assertEqual(run.call_count, 1)


class Waiting(unittest.TestCase):
    def test_what_waits_comes_from_what_is_known_and_leaves_out_what_updates_by_itself(self):
        app = FakeApp()
        listing = [{"id": "line-speed", "name": "Line speed"}]
        known = {"line-speed": {"version": "1.1.0"}}
        check = {"sonarr": {"update": True, "latest": "4.0.11"}, "reelix": {"update": True, "latest": "0.7.2"}, "quiet": {"update": False}}
        with mock.patch("starboard.plugins_admin.listing", return_value=listing), mock.patch("starboard.plugin_life.updates_known", return_value=known), \
                mock.patch.dict("starboard.containers._state", {"check": check}):
            self.assertEqual(au.waiting(app), [("plugin:line-speed", "Line speed", "1.1.0"), ("app:sonarr", "sonarr", "4.0.11"), ("app:reelix", "Reelix", "0.7.2")])
            app.config.data.update(plugins_auto_update=True, reelix_auto_update=True)
            self.assertEqual(au.waiting(app), [("app:sonarr", "sonarr", "4.0.11")])

    def test_the_alert_is_sent_once_for_each_version(self):
        from starboard import watch
        w = watch.Watch.__new__(watch.Watch)
        w.app, w.state, w.lock = FakeApp(), {"alerted": {}}, threading.Lock()
        w.settings = lambda: {"channel": {}}
        with mock.patch.object(au, "waiting", return_value=[("app:sonarr", "sonarr", "4.0.11")]):
            w._waiting("Harbour")
            w._waiting("Harbour")
        self.assertEqual(list(w.state["alerted"]), ["waiting:app:sonarr:4.0.11"])


class Summary(unittest.TestCase):
    def test_the_page_gets_each_part_with_how_it_is_kept_safe(self):
        app = FakeApp(starboard_auto_update=True)
        s = au.summary(app)
        self.assertEqual([p["id"] for p in s["parts"]], ["starboard", "reelix", "apps", "plugins", "jellyfin_plugins"])
        self.assertTrue(s["parts"][0]["active"])
        self.assertFalse(any(p["active"] for p in s["parts"][1:]))
        for p in s["parts"]:
            self.assertEqual(set(p["safety"]), {"copy", "check", "back"})
        self.assertIn("Not by itself", s["parts"][-1]["safety"]["back"])
        json.dumps(s)


if __name__ == "__main__":
    unittest.main()
