"""Install all updates (DASH-454): one batch, one update at a time in a safe order, held back items, one failure
going back by itself while the rest carry on, Jellyfin restarted once (never while someone is watching), and
Starboard last, with its end read after Starboard restarted."""
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from starboard import auto_updates, plugin_life, update_batch, update_runs
from starboard import plugins_admin as pa


class Config:
    def __init__(self, data):
        self.data = data


class App:
    def __init__(self, data_dir, services=None):
        self.data_dir = data_dir
        self.config = Config({"services": services or []})
        self.version = "0.19.1"
        self.watch = None


def target(tid, kind, name, current, latest, can=True, why="", big=False):
    return {"id": tid, "kind": kind, "name": name, "current": current, "latest": latest, "update_available": True,
            "can_update": can, "why": why, "can_roll_back": False, "roll_back_to": "", "note": "", "big_change": big}


class FakeJellyfin:
    """Jellyfin's API as auto_updates uses it: its Update plugins task changes two plug-ins' versions."""
    def __init__(self, watching=0):
        self.plugins = [{"Id": "a", "Name": "Playback Reporting", "Version": "19.0.0.0", "Status": "Active"},
                        {"Id": "b", "Name": "Open Subtitles", "Version": "20.0.0.0", "Status": "Active"}]
        self.watching = watching  # how many looks at /Sessions still see someone watching
        self.restarts = 0
        self.calls = []

    def __call__(self, jf, method, path, body=None):
        self.calls.append((method, path))
        if path == "/Plugins":
            return json.loads(json.dumps(self.plugins))
        if path == "/ScheduledTasks":
            return [{"Key": auto_updates.JF_TASK, "Id": "t1", "Triggers": []}]
        if path.startswith("/ScheduledTasks/Running/"):
            for p in self.plugins:
                p["Version"] = p["Version"].replace(".0.0.0", ".1.0.0")
            return None
        if path.startswith("/ScheduledTasks/"):
            return {"State": "Idle"}
        if path == "/Sessions":
            if self.watching:
                self.watching -= 1
                return [{"NowPlayingItem": {"Name": "A film"}}]
            return [{}]
        if path == "/System/Restart":
            self.restarts += 1
            return None
        if path == "/System/Info":
            return {"HasPendingRestart": False}
        raise AssertionError(f"Not expected: {method} {path}")


class BatchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = App(self.tmp.name, services=[{"id": "jf", "type": "jellyfin", "name": "Jellyfin"}])
        update_runs._runs.clear()
        update_runs._loaded.discard(self.tmp.name)
        update_batch._manifests.clear()
        self.order = []
        self.outcomes = {}
        self.targets = [
            target("starboard", "starboard", "Starboard", "0.19.1", "0.20.0"),
            target("reelix", "reelix", "Reelix", "0.8.7", "0.8.8"),
            target("app:sonarr", "app", "Sonarr", "4.0.10", "4.0.11"),
            target("app:radarr", "app", "Radarr", "5.1.0", "5.2.0"),
            target("plugin:picture-shrinker", "plugin", "Picture shrinker", "1.0.0", "1.1.0"),
            target("plugin:watch-stats", "plugin", "Watch statistics", "1.0.0", "1.2.0"),
        ]
        self.jelly = FakeJellyfin()
        self.manifests = {"picture-shrinker": {"id": "picture-shrinker", "version": "1.1.0", "permissions": ["media:read"]},
                          "watch-stats": {"id": "watch-stats", "version": "1.2.0", "permissions": ["jellyfin:read"]}}
        for pid, perms in (("picture-shrinker", ["media:read"]), ("watch-stats", ["jellyfin:read"])):
            os.makedirs(pa.folder(self.tmp.name, pid), exist_ok=True)
            with open(os.path.join(pa.folder(self.tmp.name, pid), "manifest.json"), "w") as f:
                json.dump({"id": pid, "version": "1.0.0", "permissions": perms}, f)
        patches = [
            mock.patch.object(update_runs, "targets", lambda app: [dict(t) for t in self.targets]),
            mock.patch.object(update_runs, "_starboard_running", lambda app: False),
            mock.patch.object(update_runs, "start", self.fake_start),
            mock.patch.object(plugin_life, "updates_known", lambda d: {pid: {"version": m["version"], "manifest": f"https://example.invalid/{pid}", "sha256": ""}
                                                                       for pid, m in self.manifests.items()}),
            mock.patch.object(update_batch, "_manifest", lambda address, sha256="": self.manifests[address.rsplit("/", 1)[1]]),
            mock.patch.object(auto_updates, "_jf", lambda services: {"url": "http://jellyfin.example", "api_key": "made-up"}),
            mock.patch.object(auto_updates, "_jf_call", self.jelly),
            mock.patch.object(auto_updates, "_save_jellyfin_copy", lambda app: ("skipped", "No Docker in the test")),
            mock.patch.object(update_batch, "_sleep", lambda s: time.sleep(0.01)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def fake_start(self, app, target, by="you", address="", note=None, batch=None):
        """Each update as its own run, ending as self.outcomes says (updated by default), in its own thread."""
        if (not batch and update_runs._busy()):
            raise update_runs.Busy("An update is already running. Wait for it to finish")
        self.assertIn(batch, update_runs._active, "an update of the batch starts only while the batch runs")
        # One at a time: nothing else of the batch is running when the next starts.
        running = [r for r in update_runs._runs.values() if r["state"] == "running" and r.get("kind") != "batch" and r["id"] in update_runs._active
                   and r["target"] != "jellyfin-plugins"]
        self.assertEqual(running, [], f"{target} started while {[r['target'] for r in running]} ran")
        self.order.append(target)
        t = next(x for x in self.targets if x["id"] == target)
        run = update_runs._new(app.data_dir, target, t["kind"], t["name"], "update", t["current"], t["latest"], by, [("install", "Installing")])
        state, said = self.outcomes.get(target, ("updated", f"{t['name']} is updated"))

        def work():
            time.sleep(0.05)
            update_runs._end(app.data_dir, run, state, said)
        update_runs._go(app.data_dir, run, work)
        return run

    def run_batch(self, **k):
        with mock.patch.object(update_batch, "WATCH_LOOK", 0):
            run = update_batch.start(self.app, **k)
            for _ in range(200):
                if update_runs.get(self.app, run["id"])["state"] != "running":
                    break
                time.sleep(0.05)
        return update_batch.view(self.app, run["id"])

    # The plan ----------------------------------------------------------------------------------------------------

    def test_the_order_is_apps_jellyfin_plugins_starboard_plugins_reelix_then_starboard(self):
        p = update_batch.plan(self.app)
        self.assertEqual([i["target"] for i in p["items"]],
                         ["app:radarr", "app:sonarr", "jellyfin-plugins", "plugin:picture-shrinker", "plugin:watch-stats", "reelix", "starboard"])
        self.assertEqual((p["count"], p["held"]), (6, []))

    def test_new_permissions_big_changes_zips_and_what_cannot_update_are_held_back(self):
        self.manifests["watch-stats"]["permissions"] = ["jellyfin:read", "jellyfin:write"]
        self.manifests["picture-shrinker"]["containers"] = [{"name": "main", "build": True}]
        self.targets[3]["big_change"] = True  # Radarr 5 to 6, as the registry look says
        self.targets[1].update(can_update=False, why="It was not started by Docker Compose")
        p = update_batch.plan(self.app)
        held = {h["target"]: h["why"] for h in p["held"]}
        self.assertIn("new permissions (jellyfin:write)", held["plugin:watch-stats"])
        self.assertIn("zip file", held["plugin:picture-shrinker"])
        self.assertIn("big change", held["app:radarr"])
        self.assertIn("Docker Compose", held["reelix"])
        self.assertEqual([i["target"] for i in p["items"]], ["app:sonarr", "jellyfin-plugins", "starboard"])
        self.assertEqual(p["count"], 2)

    def test_a_new_major_version_of_a_plugin_or_starboard_is_held_back(self):
        self.manifests["picture-shrinker"]["version"] = "2.0.0"
        self.targets[0]["latest"] = "1.0.0"
        held = {h["target"] for h in update_batch.plan(self.app)["held"]}
        self.assertEqual(held, {"plugin:picture-shrinker", "starboard"})
        self.assertFalse(update_batch.big_change("0.19.1", "0.20.0"))
        self.assertTrue(update_batch.big_change("4.2.0", "v5.0.0"))

    # The run -----------------------------------------------------------------------------------------------------

    def test_everything_runs_one_at_a_time_in_order_with_starboard_last(self):
        v = self.run_batch()
        self.assertEqual(self.order, ["app:radarr", "app:sonarr", "plugin:picture-shrinker", "plugin:watch-stats", "reelix", "starboard"])
        self.assertEqual(v["state"], "updated", v)
        self.assertEqual({i["state"] for i in v["items"]}, {"done"})
        self.assertEqual((v["count"], v["ended"]), (7, 7))
        self.assertIn("7 of 7 updated", v["said"])

    def test_one_failing_goes_back_by_itself_and_the_rest_carry_on(self):
        self.outcomes["app:radarr"] = ("went-back", "Radarr did not start on the new version, so it went back")
        self.outcomes["plugin:watch-stats"] = ("failed", "It stopped")
        v = self.run_batch()
        self.assertEqual(self.order[-1], "starboard")
        self.assertEqual(len(self.order), 6, "the rest carried on")
        states = {i["target"]: i["state"] for i in v["items"]}
        self.assertEqual((states["app:radarr"], states["plugin:watch-stats"], states["app:sonarr"]), ("went-back", "failed", "done"))
        self.assertEqual(v["state"], "some-updated")
        self.assertIn("Went back by itself: Radarr", v["said"])
        self.assertIn("Not updated: Watch statistics", v["said"])

    def test_held_back_items_are_listed_in_the_batch_and_never_run(self):
        self.manifests["watch-stats"]["permissions"] = ["jellyfin:read", "jellyfin:write"]
        v = self.run_batch()
        self.assertNotIn("plugin:watch-stats", self.order)
        held = [i for i in v["items"] if i["state"] == "held"]
        self.assertEqual([i["target"] for i in held], ["plugin:watch-stats"])
        self.assertIn("Held back for you: Watch statistics", v["said"])
        self.assertEqual(v["state"], "updated")  # everything that could update did

    def test_only_the_updates_the_person_confirmed_run(self):
        v = self.run_batch(targets=["app:sonarr", "reelix"])
        self.assertEqual(self.order, ["app:sonarr", "reelix"])
        self.assertEqual([i["target"] for i in v["items"]], ["app:sonarr", "reelix"])
        self.assertEqual(self.jelly.restarts, 0)

    def test_jellyfin_is_restarted_once_after_reelix_and_before_starboard(self):
        restarted_before = []
        real = self.fake_start

        def start(app, target, **k):
            if target == "starboard":
                restarted_before.append(self.jelly.restarts)
            if target == "reelix":
                self.assertEqual(self.jelly.restarts, 0, "Jellyfin waits for the other updates")
            return real(app, target, **k)
        with mock.patch.object(update_runs, "start", start):
            v = self.run_batch()
        self.assertEqual(self.jelly.restarts, 1)
        self.assertEqual(restarted_before, [1])
        jf = next(i for i in v["items"] if i["target"] == "jellyfin-plugins")
        self.assertEqual(jf["state"], "done", jf)
        jr = next(r for r in update_runs.recent(self.app) if r["target"] == "jellyfin-plugins")
        self.assertEqual(jr["state"], "updated")
        self.assertIn("Playback Reporting 19.0.0.0 to 19.1.0.0", jr["said"])

    def test_jellyfin_waits_while_someone_is_watching_and_says_so(self):
        self.jelly.watching = 3
        said = []
        real = update_batch._say
        with mock.patch.object(update_batch, "_say", lambda app, run, words: (said.append(words), real(app, run, words))):
            v = self.run_batch()
        self.assertEqual(self.jelly.restarts, 1)
        self.assertTrue(any("1 person is watching" in w for w in said), said)
        self.assertEqual(v["state"], "updated")

    def test_jellyfin_never_restarts_while_someone_still_watches(self):
        self.jelly.watching = 10 ** 6
        with mock.patch.object(update_batch, "WATCH_WAIT", 0):
            v = self.run_batch()
        self.assertEqual(self.jelly.restarts, 0)
        jr = next(r for r in update_runs.recent(self.app) if r["target"] == "jellyfin-plugins")
        self.assertIn("next restarts", jr["said"])
        self.assertEqual(self.order[-1], "starboard")
        self.assertEqual(v["state"], "updated")

    def test_nothing_else_starts_while_the_batch_runs(self):
        gate = threading.Event()
        real = self.fake_start

        def slow(app, target, **k):
            gate.wait(5)
            return real(app, target, **k)
        with mock.patch.object(update_runs, "start", slow):
            run = update_batch.start(self.app)
            with self.assertRaises(update_runs.Busy):
                update_batch.start(self.app)
            self.assertTrue(update_runs._busy())
            gate.set()
            for _ in range(200):
                if update_runs.get(self.app, run["id"])["state"] != "running":
                    break
                time.sleep(0.05)

    def test_nothing_to_install_says_so(self):
        self.targets = [t for t in self.targets if t["kind"] == "plugin"]
        for m in self.manifests.values():
            m["permissions"] = ["everything"]
        with self.assertRaises(update_runs.Refused) as e:
            update_batch.start(self.app)
        self.assertIn("held back", str(e.exception))

    # Starboard restarts at the end ----------------------------------------------------------------------------------

    def test_after_starboard_restarts_the_batch_ends_with_starboards_own_run(self):
        """The batch's thread ends with the old Starboard; the new one reads Starboard's run to end the batch."""
        stop = threading.Event()
        real, real_wait = self.fake_start, update_batch._wait

        def start(app, target, **k):
            if target != "starboard":
                return real(app, target, **k)
            self.order.append(target)
            return update_runs._new(app.data_dir, "starboard", "starboard", "Starboard", "update", "0.19.1", "0.20.0", "you",
                                    [("install", "Installing")], extra={"delegate": "self-update"})

        def wait(app, rid, sleep, **k):
            if update_runs._runs[rid]["target"] == "starboard":
                stop.set()
                raise SystemExit  # Starboard restarting: the batch's thread goes with it
            return real_wait(app, rid, sleep, **k)
        with mock.patch.object(update_runs, "start", start), mock.patch.object(update_batch, "_wait", wait):
            run = update_batch.start(self.app)
            self.assertTrue(stop.wait(10))
            time.sleep(0.2)
        with update_runs._lock:
            update_runs._active.clear()  # a new Starboard: nothing is followed
            saved = dict(update_runs._runs[run["id"]])
        self.assertEqual(saved["state"], "running")
        sb = next(r for r in update_runs._runs.values() if r["target"] == "starboard")
        sb_live = {"state": "running"}
        with mock.patch.object(update_runs, "get", lambda app, rid: dict(update_runs._runs[rid], **sb_live) if rid == sb["id"]
                               else update_runs._live(app, json.loads(json.dumps(update_runs._runs[rid])))):
            self.assertEqual(update_batch.view(self.app, run["id"])["state"], "running")
            sb_live.update(state="updated", said="Starboard is updated to 0.20.0")
            v = update_batch.view(self.app, run["id"])
        self.assertEqual(v["state"], "updated", v)
        self.assertEqual(next(i for i in v["items"] if i["target"] == "starboard")["state"], "done")
        self.assertEqual(update_runs._runs[run["id"]]["state"], "updated", "written once")
        with open(os.path.join(self.tmp.name, update_runs.RUNS)) as f:
            self.assertEqual(next(r for r in json.load(f) if r["id"] == run["id"])["state"], "updated")

    def test_a_batch_left_running_without_starboard_updating_stopped(self):
        run = update_runs._new(self.tmp.name, "all", "batch", "All updates", "update", "", "2 updates", "you",
                               [("app:sonarr", "Sonarr"), ("reelix", "Reelix")], extra={"items": []})
        update_runs._step(self.tmp.name, run, "app:sonarr", "done")
        v = update_batch.view(self.app, run["id"])
        self.assertEqual(v["state"], "failed")
        self.assertIn("Starboard restarted while it ran", v["said"])

    def test_a_running_batch_is_never_pushed_out_of_recent_updates(self):
        run = update_runs._new(self.tmp.name, "all", "batch", "All updates", "update", "", "30 updates", "you", [("a", "A")])
        with update_runs._lock:
            update_runs._active[run["id"]] = threading.current_thread()
        try:
            for n in range(update_runs.KEEP + 5):
                update_runs._new(self.tmp.name, f"app:a{n}", "app", f"A{n}", "update", "1", "2", "you", [])
            self.assertIn(run["id"], update_runs._runs)
            self.assertEqual(len(update_runs._runs), update_runs.KEEP)
        finally:
            update_runs._active.pop(run["id"], None)


if __name__ == "__main__":
    unittest.main()
