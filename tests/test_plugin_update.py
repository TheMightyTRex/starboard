"""Plug-ins that update safely (plug-in API 1.14, DASH-424): the update object's check, settings migration and Roll
back, the before and after steps, the health check with the automatic way back, What is new before an update, the
tester's checks, and an update run followed to its end."""
import copy
import os
import tempfile
import time
import unittest
from unittest import mock

from starboard import plugin_life, plugin_tester, plugin_update, plugins, plugins_admin as pa, update_runs
from tests.test_plugins import ON_DEMAND


def v1():
    m = copy.deepcopy(ON_DEMAND)
    m["version"] = "1.0.0"
    m["settings"] = [{"key": "minutes", "label": "Check every", "type": "number", "default": 15},
                     {"key": "old_mode", "label": "Old mode", "type": "text", "default": "fast"},
                     {"key": "quality", "label": "Picture quality", "type": "choice", "choices": ["4K", "1080p"], "default": "1080p"}]
    m["update"] = {"before": {"path": "/update/before", "time_limit_seconds": 30}, "after": {"path": "/update/after"}}
    m["changes"] = [{"version": "1.0.0", "added": ["The first version"]}]
    return m


def v2():
    m = v1()
    m["version"] = "2.0.0"
    m["settings"] = [{"key": "every_minutes", "label": "Check every", "type": "number", "default": 15},
                     {"key": "quality", "label": "Picture quality", "type": "choice", "choices": ["4K", "1080p", "720p"], "default": "720p"}]
    m["update"] = {"before": {"path": "/update/before"}, "after": {"path": "/update/after"}, "health_wait_seconds": 10,
                   "migrations": [{"version": "1.5.0", "rename": {"minutes": "every_minutes"}},
                                  {"version": "2.0.0", "remove": ["old_mode"], "defaults": {"quality": "720p", "every_minutes": 30}}]}
    m["changes"] = [{"version": "2.0.0", "changed": ["Checks every 30 minutes unless you chose otherwise"], "removed": ["Old mode"]},
                    {"version": "1.5.0", "fixed": ["A card that said nothing"]}, {"version": "1.0.0", "added": ["The first version"]}]
    return m


class Check(unittest.TestCase):
    def test_a_good_update_object_passes(self):
        self.assertEqual(plugins.check(v2()), [])
        self.assertEqual(plugins.check(v1()), [])

    def test_each_mistake_is_said(self):
        cases = [
            ({"update": "yes"}, "must be an object"),
            ({"update": {"before": {"path": "update"}}}, "update.before: needs a path"),
            ({"update": {"after": {"path": "/a", "time_limit_seconds": 900}}}, "time_limit_seconds must be a whole number from 5 to 300"),
            ({"update": {"health_wait_seconds": 5}}, "health_wait_seconds must be"),
            ({"update": {"sideways": 1}}, "update: unknown field sideways"),
            ({"update": {"migrations": [{"version": "9.0.0", "remove": ["x"]}]}}, "newer than this plug-in's version"),
            ({"update": {"migrations": [{"version": "0.1.0"}]}}, "needs at least one of rename, remove or defaults"),
            ({"update": {"migrations": [{"version": "0.1.0", "rename": {"a": "nowhere"}}]}}, "which is not one of this version's settings"),
            ({"update": {"migrations": [{"version": "0.1.0", "remove": ["quality"]}]}}, "still one of this version's settings"),
            ({"update": {"migrations": [{"version": "0.1.0", "defaults": {"nowhere": 1}}]}}, "defaults sets nowhere"),
            ({"update": {"migrations": [{"version": "0.1.0", "remove": ["x"]}, {"version": "0.1.0", "remove": ["y"]}]}}, "needs its own version"),
        ]
        for change, words in cases:
            problems = plugins.check({**copy.deepcopy(ON_DEMAND), **change})
            self.assertTrue(any(words in p for p in problems), f"{change}: {problems}")
        no_health = {**copy.deepcopy(ON_DEMAND), "update": {"health_wait_seconds": 30}}
        del no_health["health"]
        self.assertTrue(any("needs a health path" in p for p in plugins.check(no_health)))

    def test_the_schema_knows_the_update_object(self):
        import json
        with open(os.path.join(os.path.dirname(plugins.__file__), "plugin-manifest.schema.json")) as f:
            schema = json.load(f)
        self.assertIn("update", schema["properties"])
        self.assertIn("update_step", schema["$defs"])


class Migrate(unittest.TestCase):
    def test_renames_removes_and_new_defaults_in_order(self):
        values, said = plugin_update.migrate(v1(), v2(), {"minutes": 15, "old_mode": "fast", "quality": "1080p"})
        # 15 was 1.0.0's default, so it takes 2.0.0's new 30; the quality was still the old default, so 720p.
        self.assertEqual(values, {"every_minutes": 30, "quality": "720p"})
        self.assertIn("minutes is now every_minutes", said)
        self.assertIn("old_mode was removed", said)

    def test_a_value_the_person_chose_is_kept(self):
        values, _ = plugin_update.migrate(v1(), v2(), {"minutes": 5, "quality": "4K"})
        self.assertEqual(values, {"every_minutes": 5, "quality": "4K"})

    def test_only_the_steps_between_the_two_versions(self):
        old = {**v1(), "version": "1.5.0"}
        values, said = plugin_update.migrate(old, v2(), {"minutes": 7})  # 1.5.0 already had the rename
        self.assertEqual(values, {"minutes": 7, "every_minutes": 30, "quality": "720p"})
        self.assertNotIn("minutes is now every_minutes", said)

    def test_going_to_an_older_version_moves_nothing(self):
        self.assertEqual(plugin_update.migrate(v2(), v1(), {"every_minutes": 5}), ({"every_minutes": 5}, []))


class Life(unittest.TestCase):
    """The update, step by step, with the plug-in's calls answered here."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, name, kw in ((pa, "host_path", {"side_effect": lambda d, pid: f"/srv/starboard/data/plugins/{pid}"}),
                                 (pa, "_compose_run", {"return_value": (True, "")})):
            p = mock.patch.object(target, name, **kw)
            p.start()
            self.addCleanup(p.stop)
        self.calls, self.answers, self.health = [], {}, ["ok"]

        def post(pid, main, path, body, timeout):
            self.calls.append((path, body, timeout))
            return self.answers.get(path, (True, "Ready"))
        for name, fn in (("_post", post), ("_ask", lambda pid, main, path: self.health[0])):
            p = mock.patch.object(plugin_update, name, side_effect=fn)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(plugin_update.time, "sleep")
        p.start()
        self.addCleanup(p.stop)
        self.d = self.tmp.name
        pa.install(self.d, v1(), "/srv/media")
        pa.save_settings(self.d, "on-demand", {"minutes": 15, "old_mode": "fast", "quality": "4K"})
        pa.enable(self.d, "on-demand")
        self.where = pa.folder(self.d, "on-demand")

    def settings(self):
        return pa._read(os.path.join(self.where, "settings.json"))

    def test_a_healthy_update_runs_each_step_and_moves_the_settings(self):
        steps = []
        r = plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media", progress=lambda *a: steps.append(a[:2]))
        self.assertEqual(r["outcome"], "updated")
        self.assertEqual([c[0] for c in self.calls], ["/update/before", "/update/after"])
        self.assertEqual(self.calls[0][1], {"from": "1.0.0", "to": "2.0.0"})
        self.assertEqual(self.calls[0][2], 30)  # the installed version's own time limit
        self.assertEqual(self.calls[1][1]["outcome"], "updated")
        self.assertEqual(self.settings(), {"every_minutes": 30, "quality": "4K"})
        self.assertIn(("health", "done"), steps)
        # Roll back puts the settings back as they were, with the old keys.
        plugin_life.rollback(self.d, "on-demand", "/srv/media")
        self.assertEqual(self.settings(), {"minutes": 15, "old_mode": "fast", "quality": "4K"})

    def test_a_failing_before_step_stops_the_update_and_changes_nothing(self):
        self.answers["/update/before"] = (False, "A job is half way through a film")
        r = plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media")
        self.assertEqual(r["outcome"], "refused")
        self.assertIn("A job is half way", r["said"])
        self.assertEqual(pa._read(os.path.join(self.where, "manifest.json"))["version"], "1.0.0")
        self.assertEqual(self.settings()["minutes"], 15)
        self.assertFalse(os.path.exists(os.path.join(self.where, "previous", "manifest.json")))

    def test_a_failing_health_check_goes_back_by_itself(self):
        self.health[0] = "Its health check answered 500"
        steps = []
        r = plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media", progress=lambda *a: steps.append(a[:2]))
        self.assertEqual(r["outcome"], "went-back")
        self.assertIn("within 10 seconds", r["said"])
        self.assertEqual(pa._read(os.path.join(self.where, "manifest.json"))["version"], "1.0.0")
        self.assertEqual(self.settings(), {"minutes": 15, "old_mode": "fast", "quality": "4K"})
        self.assertEqual(self.calls[-1][1]["outcome"], "rolled_back")  # the old version hears it can start again
        self.assertIn(("going-back", "done"), steps)
        st = pa._read(os.path.join(self.where, "state.json"))
        self.assertIn("rolled back by itself", st["message"])
        self.assertIsNone(plugin_life.whats_new(self.d, "on-demand"))  # nothing changed for them
        with open(os.path.join(self.d, "logs", "audit.jsonl")) as f:
            self.assertIn("plugin_update_rolled_back", f.read())

    def test_a_version_that_does_not_start_goes_back_too(self):
        with mock.patch.object(pa, "_compose_run", side_effect=[(False, "no such image"), (True, "")]):
            r = plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media")
        self.assertEqual(r["outcome"], "went-back")
        self.assertIn("did not start", r["said"])

    def test_an_inactive_plugin_is_updated_without_its_steps(self):
        pa.disable(self.d, "on-demand")
        r = plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media")
        self.assertEqual((r["outcome"], self.calls), ("updated", []))
        self.assertEqual(self.settings()["every_minutes"], 30)

    def test_a_failing_after_step_keeps_the_update_and_says_so(self):
        self.answers["/update/after"] = (False, "Could not tidy the cache")
        r = plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media")
        self.assertEqual(r["outcome"], "updated")
        self.assertIn("Could not tidy the cache", r["said"])

    def test_roll_back_with_its_steps(self):
        plugin_update.update_safely(self.d, "on-demand", v2(), "/srv/media")
        self.calls.clear()
        r = plugin_update.rollback_safely(self.d, "on-demand", "/srv/media")
        self.assertEqual((r["outcome"], r["to"]), ("rolled-back", "1.0.0"))
        self.assertEqual([c[0] for c in self.calls], ["/update/before", "/update/after"])
        self.assertEqual(self.calls[-1][1]["outcome"], "rolled_back")

    def test_what_is_new_before_the_update(self):
        p = plugin_update.preview(v1(), v2())
        self.assertEqual([v["version"] for v in p["whats_new"]], ["2.0.0", "1.5.0"])
        self.assertIn("minutes is now every_minutes", p["settings_move"])
        self.assertTrue(p["before_step"] and p["after_step"])
        self.assertEqual(p["health_wait_seconds"], 10)

    def test_the_plain_update_migrates_too(self):  # Update from the Python API or an old caller
        plugin_life.update(self.d, "on-demand", v2(), "/srv/media")
        self.assertEqual(self.settings()["every_minutes"], 30)
        self.assertIn("old_mode was removed", pa._read(os.path.join(self.where, "state.json"))["migrated"])


class Tester(unittest.TestCase):
    def issues(self, m):
        return {(i["where"], i["severity"]): i["what"] for i in plugin_tester.run(m, dev=True)}

    def test_changes_must_list_this_version(self):
        m = v2()
        m["changes"] = m["changes"][1:]
        self.assertIn(("changes", "warning"), self.issues(m))
        self.assertNotIn(("changes", "warning"), self.issues(v2()))

    def test_jobs_without_a_before_step_get_a_tip(self):
        m = copy.deepcopy(ON_DEMAND)
        m["jobs"] = [{"id": "scan", "label": "Scan", "path": "/scan", "daily": "03:00"}]
        self.assertIn(("update", "info"), self.issues(m))
        m["update"] = {"before": {"path": "/update/before"}}
        self.assertNotIn(("update", "info"), self.issues(m))

    def test_update_mistakes_are_errors(self):
        m = {**copy.deepcopy(ON_DEMAND), "update": {"before": {"path": "no-slash"}}}
        self.assertIn(("update.before", "error"), self.issues(m))


class Runs(unittest.TestCase):
    """An update run, as the plug-in's page and the API start it, followed to its end."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = mock.Mock(data_dir=self.tmp.name, version="0.17.0", watch=None, plugin_clock=None, plugin_idle=None)
        self.app.config.data = {"services": []}
        for target, name, kw in ((pa, "host_path", {"side_effect": lambda d, pid: f"/srv/starboard/data/plugins/{pid}"}),
                                 (pa, "_compose_run", {"return_value": (True, "")}),
                                 (plugin_update, "_post", {"return_value": (True, "")}),
                                 (plugin_update, "_ask", {"return_value": "ok"}),
                                 (pa, "fetch_manifest", {"side_effect": lambda *a, **k: v2()}),
                                 (pa, "fetch_logo", {"return_value": (None, "")}),
                                 (__import__("starboard.containers", fromlist=["x"]), "available", {"return_value": False}),
                                 (plugin_life, "updates_known", {"return_value": {"on-demand": {"version": "2.0.0", "changelog": "Faster",
                                                                                                "manifest": "https://example.invalid/m.json", "sha256": ""}}})):
            p = mock.patch.object(target, name, **kw)
            p.start()
            self.addCleanup(p.stop)
        pa.install(self.tmp.name, v1(), "/srv/media")
        pa.enable(self.tmp.name, "on-demand")

    def wait(self, run):
        for _ in range(200):
            j = update_runs.job(self.app, run["id"])
            if j["finished"]:
                return j
            time.sleep(0.02)
        self.fail("the run did not finish")

    def test_an_update_and_a_roll_back_as_runs(self):
        targets = {t["id"]: t for t in update_runs.targets(self.app) if t["kind"] == "plugin"}
        self.assertTrue(targets["plugin:on-demand"]["update_available"])
        run = update_runs.start(self.app, "plugin:on-demand", by="api:Home Assistant")
        j = self.wait(run)
        self.assertEqual((j["ok"], j["state"]), (True, "updated"))
        self.assertNotIn("not-needed", [t["state"] for t in j["tasks"]])
        self.assertEqual(update_runs.recent(self.app)[0]["by"], "api:Home Assistant")
        run = update_runs.rollback(self.app, "plugin:on-demand")
        j = self.wait(run)
        self.assertEqual((j["state"], j["to"]), ("rolled-back", "1.0.0"))
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            text = f.read()
        for what in ("update_started", "update_finished", "rollback_started"):
            self.assertIn(what, text)

    def test_one_update_at_a_time(self):
        gate = __import__("threading").Event()
        with mock.patch.object(plugin_update, "_post", side_effect=lambda *a: (gate.wait(5), (True, ""))[1]):
            run = update_runs.start(self.app, "plugin:on-demand")
            with self.assertRaises(update_runs.Busy):
                update_runs.start(self.app, "plugin:on-demand")
            gate.set()
            self.wait(run)

    def test_a_run_left_running_by_a_restart_says_so(self):
        run = update_runs._new(self.tmp.name, "plugin:on-demand", "plugin", "On demand", "update", "1.0.0", "2.0.0", "you",
                               plugin_update.STEPS)
        self.assertEqual(update_runs.get(self.app, run["id"])["state"], "failed")


if __name__ == "__main__":
    unittest.main()
