"""Moving in from other apps, clearer at every stage (13 November 2026): the task list a long change shows (DASH-252,
254), the takeover's and the move's steps, a step that stopped before it started, qBittorrent's ban (DASH-251), the
titles waiting for a match (DASH-253), clearing away the apps Reelix replaced (DASH-191), the requests route
(DASH-192) and Change your install leaving out apps from the person's own Compose file (DASH-250)."""
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from unittest import mock

from starboard import reelix_move, reelix_waiting, requests_route, stack, takeover, tasklist


class TasksTest(unittest.TestCase):
    def test_start_marks_the_ones_before_done(self):
        t = tasklist.Tasks([("a", "A"), ("b", "B"), ("c", "C")])
        t.start("a")
        t.start("b", now="Doing B")
        got = {x["id"]: x["state"] for x in t.public()["tasks"]}
        self.assertEqual(got, {"a": "done", "b": "working", "c": "waiting"})
        self.assertEqual(t.public()["now"], "Doing B")

    def test_a_stop_says_why_the_rest_did_not_start(self):
        t = tasklist.Tasks([("a", "A"), ("b", "B"), ("c", "C")])
        t.start("a")
        t.stop_rest("Not started, because A did not finish")
        got = t.public()["tasks"]
        self.assertEqual([x["state"] for x in got], ["failed", "skipped", "skipped"])
        self.assertEqual(got[2]["detail"], "Not started, because A did not finish")

    def test_progress_lines_from_a_helper_script(self):
        t = tasklist.Tasks([("stop", "Stop"), ("copy-0", "Copy"), ("start", "Start")])
        tasklist.from_progress(t, ["stop", "copy-0", "copy-0 failed"])
        self.assertEqual([x["state"] for x in t.public()["tasks"]], ["done", "failed", "waiting"])


class TakeoverStepsTest(unittest.TestCase):
    def plan(self, sab=False):
        return {"copies": [("/old/jf", "/new/jellyfin"), ("/old/qb", "/new/qbittorrent")],
                "copy_apps": ["Jellyfin's settings", "qBittorrent's settings"], "sab": sab,
                "choice": {"apps": ["reelix", "jellyfin", "qbittorrent"]}}

    def test_the_dialog_lists_each_copy_by_app(self):
        labels = [label for _, label in takeover.takeover_tasks(self.plan(sab=True))]
        self.assertEqual(labels[:4], ["Save the way back", "Stop your old apps", "Copy Jellyfin's settings", "Copy qBittorrent's settings"])
        self.assertIn("Move the Usenet servers into NZBGet", labels)
        self.assertEqual(labels[-1], "Update your dashboard")

    def test_the_script_writes_each_step_as_it_starts_it(self):
        rec = {"containers": [{"name": "jellyfin", "project": "media", "files": ["/srv/compose.yaml"], "folder": "/srv"}],
               "copies": [("/old/jf", "/new/jellyfin")]}
        script = takeover.takeover_script(rec, "/host/stack", "/new", progress="/host/stack/takeover-progress")
        marks = [line for line in script.splitlines() if "takeover-progress" in line]
        self.assertEqual([m.split()[1].strip("'") for m in marks], ["stop", "copy-0", "remove", "start"])
        self.assertLess(script.index("echo 'stop'"), script.index("docker stop"))

    def test_without_progress_the_script_is_unchanged_in_effect(self):
        rec = {"containers": [{"name": "jellyfin", "project": "media", "files": ["/srv/compose.yaml"], "folder": "/srv"}],
               "copies": []}
        self.assertNotIn("takeover-progress", takeover.takeover_script(rec, "/host/stack", "/new"))

    def test_rollback_steps_name_each_old_project(self):
        rec = {"containers": [{"name": "jellyfin", "project": "media", "service": "jellyfin", "files": ["/srv/c.yaml"], "folder": "/srv"}]}
        self.assertIn(("old-media", "Start your old apps from media"), takeover.rollback_tasks(rec))
        self.assertIn("echo 'old-media'", takeover.rollback_script(rec, "/hs", "/hs/takeover-progress"))


class ClearAwayTest(unittest.TestCase):
    def test_holding_folder_is_beside_the_settings_folders(self):
        self.assertEqual(takeover.holding_for("/srv/apps/config/radarr", "radarr", "s"), "/srv/apps/config/starboard-holding/s/radarr")
        self.assertEqual(takeover.holding_for("/home/o/media/radarr/config", "radarr", "s"),
                         "/home/o/media/starboard-holding/s/radarr-config")
        self.assertIsNone(takeover.holding_for("/srv/radarr", "radarr", "s"))  # too near the top to move safely

    def test_offered_only_after_keep_it(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(takeover, "found", return_value=[]):
            self.assertIsNone(takeover.leftovers(d))
            kept = os.path.join(stack.folder(d), "takeover-kept-20261113")
            os.makedirs(kept)
            with open(os.path.join(kept, "record.json"), "w") as f:
                json.dump({"containers": [{"name": "radarr", "key": "radarr", "settings": ["/srv/apps/config/radarr"]},
                                          {"name": "jellyfin", "key": "jellyfin", "settings": ["/srv/apps/config/jellyfin"]}]}, f)
            with mock.patch.object(takeover.containers, "available", return_value=False):
                left = takeover.leftovers(d)
        self.assertEqual([x["name"] for x in left], ["radarr"])  # Jellyfin is not something Reelix replaced

    def test_the_script_moves_never_deletes_and_one_failure_does_not_stop_the_rest(self):
        items = [{"name": "radarr", "app": "Radarr", "container": True, "settings": ["/srv/apps/config/radarr"]},
                 {"name": "sonarr", "app": "Sonarr", "container": False, "settings": ["/srv/apps/config/sonarr"]}]
        script = takeover.clear_script(items, "s", "/hs/p")
        self.assertNotIn("rm -r", script)
        self.assertIn("mv '/srv/apps/config/radarr' '/srv/apps/config/starboard-holding/s/radarr'", script)
        self.assertIn("echo 'app-0 failed'", script)
        self.assertNotIn("set -e", script)

    def test_the_script_runs_for_real(self):
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "srv", "apps", "config")
            os.makedirs(os.path.join(base, "radarr"))
            open(os.path.join(base, "radarr", "radarr.db"), "w").close()
            bin_ = os.path.join(d, "bin")
            os.makedirs(bin_)
            with open(os.path.join(bin_, "docker"), "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(os.path.join(bin_, "docker"), 0o755)
            items = [{"name": "radarr", "app": "Radarr", "container": True, "settings": [os.path.join(base, "radarr")]}]
            with mock.patch.object(takeover, "_TOP", ("/",)):
                script = takeover.clear_script(items, "s", os.path.join(d, "progress"))
            subprocess.run(["sh", "-c", script], check=True, env={**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}"})
            self.assertTrue(os.path.exists(os.path.join(base, "starboard-holding", "s", "radarr", "radarr.db")))
            self.assertFalse(os.path.exists(os.path.join(base, "radarr")))
            with open(os.path.join(d, "progress")) as f:
                self.assertEqual(f.read().split(), ["app-0"])


class FakeAdmin:
    def __init__(self, runs):
        self.runs = list(runs)

    def call(self, method, path, body=None, timeout=20, ok=(200, 201, 204)):
        if path == "/system/migrate":
            return 200, self.runs.pop(0)
        if path == "/indexers":
            return 200, []
        return 200, {}


class MoveStepsTest(unittest.TestCase):
    def src(self, kind):
        return {"source": kind, "app": reelix_move.LABELS[kind], "container": kind, "url": "http://x:1", "api_key": "k",
                "networks": [], "path_rewrites": []}

    def test_progress_and_results_in_the_task_list(self):
        runs = [{"state": "running", "done": 3, "total": 10, "current": "Harbour Street (2019)"},
                {"state": "finished", "items": [{"action": "create"}, {"action": "skip", "name": "X", "category": "movie"}]}]
        tasks = tasklist.Tasks(reelix_move.move_tasks([self.src("radarr")], hold=True))
        with mock.patch.object(reelix_move, "_admin", return_value=FakeAdmin(runs)), \
                mock.patch.object(reelix_move, "join_networks", return_value=[]):
            reelix_move.run_all("http://127.0.0.1:7700", "pw", [self.src("radarr")], tasks=tasks, sleep=lambda s: None)
        got = {t["id"]: t for t in tasks.public()["tasks"]}
        self.assertEqual(got["app-radarr"]["state"], "done")
        self.assertEqual(got["app-radarr"]["detail"], "1 moved, 1 not moved")
        self.assertEqual(got["hold"]["state"], "done")

    def test_a_move_that_stops_says_the_rest_did_not_start(self):
        class Boom(FakeAdmin):
            def call(self, method, path, body=None, timeout=20, ok=(200, 201, 204)):
                if path == "/system/migrate/run":
                    raise reelix_move.reelix_setup.ReelixError("Reelix stopped answering")
                return super().call(method, path, body)
        tasks = tasklist.Tasks(reelix_move.move_tasks([self.src("prowlarr"), self.src("radarr")]))
        with mock.patch.object(reelix_move, "_admin", return_value=Boom([])), \
                mock.patch.object(reelix_move, "join_networks", return_value=[]), \
                mock.patch.object(reelix_move, "prowlarr_secrets", return_value={}), \
                self.assertRaises(reelix_move.reelix_setup.ReelixError):
            reelix_move.run_all("http://127.0.0.1:7700", "pw", [self.src("prowlarr"), self.src("radarr")], tasks=tasks)
        got = {t["id"]: t for t in tasks.public()["tasks"]}
        self.assertEqual(got["app-prowlarr"]["state"], "failed")
        self.assertEqual(got["app-radarr"]["state"], "skipped")
        self.assertIn("stopped at Prowlarr", got["app-radarr"]["detail"])

    def test_progress_words(self):
        self.assertEqual(reelix_move.progress_words("Radarr", {"done": 120, "total": 340, "current": "Harbour Street (2019)"}),
                         "Radarr: 120 of 340, Harbour Street (2019)")


class QbittorrentTest(unittest.TestCase):
    def opener(self, code=None, body=b"Ok."):
        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n=-1):
                return body

        class Opener:
            def open(self, req, timeout=15):
                if code:
                    raise urllib.error.HTTPError(req.full_url, code, "no", {}, None)
                return Resp()
        return Opener()

    def test_states(self):
        self.assertEqual(reelix_move.qbit_sign_in("pw", opener=self.opener()), "ok")
        self.assertEqual(reelix_move.qbit_sign_in("pw", opener=self.opener(body=b"Fails.")), "wrong")
        self.assertEqual(reelix_move.qbit_sign_in("pw", opener=self.opener(code=403)), "banned")
        self.assertFalse(reelix_move.qbit_check("pw", opener=self.opener(code=403)))

    def test_ban_words_say_how_to_clear_it(self):
        words = reelix_move.qbit_problem("banned", "harbour", 30)
        self.assertIn("after 30 minutes", words)
        self.assertIn("docker restart qbittorrent", words)
        self.assertIn("harbour", reelix_move.qbit_problem("wrong", "harbour"))

    def test_ban_length_from_the_settings_file(self):
        self.assertEqual(reelix_move.conf_ban_minutes("[Preferences]\nWebUI\\BanDuration=1800\n"), 30)
        self.assertEqual(reelix_move.conf_ban_minutes("[Preferences]\n"), 60)


class WaitingTest(unittest.TestCase):
    def test_only_titles_that_did_not_match_wait(self):
        self.assertTrue(reelix_waiting.is_unmatched({"category": "movie", "why": "TMDB isn't configured"}))
        self.assertTrue(reelix_waiting.is_unmatched({"category": "series", "why": "it has no TMDB or TVDB id"}))
        self.assertFalse(reelix_waiting.is_unmatched({"category": "movie", "why": "its root folder wasn't migrated"}))
        self.assertFalse(reelix_waiting.is_unmatched({"category": "indexer", "why": "TMDB"}))

    def test_held_once_tried_and_added_when_it_matches(self):
        with tempfile.TemporaryDirectory() as d:
            film = reelix_waiting.entry("Radarr", {"category": "movie", "name": "A (2001)", "key": "movie:1", "why": "TMDB"}, {"tmdb": 11, "imdb": "tt1"})
            show = reelix_waiting.entry("Sonarr", {"category": "series", "name": "B", "key": "series:2", "why": "TMDB"}, {"tvdb": 22})
            only_imdb = reelix_waiting.entry("Radarr", {"category": "movie", "name": "C", "key": "movie:3", "why": "TMDB"}, {"imdb": "tt3"})
            self.assertEqual(reelix_waiting.hold(d, [film, show, only_imdb]), 3)
            self.assertEqual(reelix_waiting.hold(d, [film]), 0)  # not twice
            added = []

            def add(kind, key):
                if key == "tvdb:22":
                    raise ValueError("TVDB did not know it")
                added.append((kind, key))
            got = reelix_waiting.try_again(d, None, add=add)
            self.assertEqual(got, {"added": 1, "waiting": 2})
            self.assertEqual(added, [("films", "tmdb:11")])
            left = {i["title"]: i for i in reelix_waiting.read(d)}
            self.assertEqual(set(left), {"B", "C"})
            self.assertEqual(left["B"]["tries"], 1)
            self.assertIn("by hand", left["C"]["last_error"])

    def test_no_tmdb_key_stops_the_round_after_one_try(self):
        with tempfile.TemporaryDirectory() as d:
            reelix_waiting.hold(d, [reelix_waiting.entry("Radarr", {"category": "movie", "name": f"F{n}", "key": f"movie:{n}", "why": "TMDB"}, {"tmdb": n + 1})
                                    for n in range(5)])
            calls = []

            def add(kind, key):
                calls.append(key)
                raise ValueError("TMDB isn't configured")
            self.assertEqual(reelix_waiting.try_again(d, None, add=add), {"added": 0, "waiting": 5})
            self.assertEqual(len(calls), 1)

    def test_the_retry_sleeps_while_the_list_is_empty(self):
        waits = []

        class Wake:
            def wait(self, timeout=None):
                waits.append(timeout)
                raise SystemExit  # one look is enough

            def clear(self):
                pass
        with tempfile.TemporaryDirectory() as d, mock.patch.object(reelix_waiting, "_wake", Wake()):
            loop_ran = []
            with mock.patch.object(reelix_waiting.threading, "Thread") as thread:
                reelix_waiting._thread = None
                reelix_waiting.start(d, lambda: None)
                target = thread.call_args.kwargs["target"]
            with self.assertRaises(SystemExit):
                target()
            loop_ran.append(True)
        self.assertEqual(waits, [None])  # no timer at all while nothing waits


class RequestsRouteTest(unittest.TestCase):
    def test_reelix_is_recommended_and_messages_name_the_address(self):
        self.assertEqual(requests_route.RECOMMENDED, "reelix")
        self.assertIn("http://reelix.example", requests_route.message("reelix", "http://reelix.example"))
        self.assertIn("keep asking", requests_route.message("seerr"))

    def test_seerr_is_pointed_at_reelix(self):
        calls = []

        def call(s, path, method="GET", body=None):
            calls.append((method, path, body))
            if path.endswith("/test"):
                return {"profiles": [{"id": 4, "name": "HD"}], "rootFolders": [{"id": 1, "path": "/data/media/films"}]}
            if path == "/settings/radarr":
                return [{"id": 0, "name": "Radarr", "isDefault": True, "is4k": False, "activeProfileName": "HD",
                         "activeDirectory": "/movies", "hostname": "radarr", "port": 7878}]
            if path == "/settings/sonarr":
                return []
            return {}
        notes = requests_route.point_seerr_at_reelix({"name": "Seerr"}, "manager-key", call)
        put = next(c for c in calls if c[0] == "PUT")
        self.assertEqual(put[1], "/settings/radarr/0")
        self.assertEqual((put[2]["hostname"], put[2]["port"], put[2]["baseUrl"], put[2]["apiKey"]), ("reelix", 7700, "/radarr", "manager-key"))
        self.assertEqual(put[2]["activeProfileId"], 4)
        post = next(c for c in calls if c[0] == "POST" and c[1] == "/settings/sonarr")
        self.assertEqual(post[2]["baseUrl"], "/sonarr")
        self.assertEqual(notes, ["Seerr sends films requests to Reelix", "Seerr sends series requests to Reelix"])

    def test_choosing_reelix_makes_seerr_inactive_on_the_dashboard(self):
        saved = []

        class Config:
            data = {"services": [{"id": "s", "type": "seerr", "api_key": "k", "name": "Seerr", "enabled": True}]}

            def upsert_service(self, s):
                saved.append(s)
        with tempfile.TemporaryDirectory() as d:
            applied, notes = requests_route.apply(Config(), d, "reelix")
        self.assertTrue(applied)
        self.assertFalse(saved[0]["enabled"])
        self.assertIn("Seerr stops when Starboard takes over your apps", notes)


class OutsideAppsTest(unittest.TestCase):
    def test_apps_from_the_own_compose_file_are_not_added_again(self):
        with tempfile.TemporaryDirectory() as d:
            basics = stack.install_choice("basics", check=lambda ref: True)
            choice = {"apps": ["reelix", "nzbget"], "config_dir": "/srv/c", "data_dir": "/srv/m", "reelix_edition": "lite",
                      "vpn": {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "x", "wireguard_addresses": "10.0.0.2/32"}}
            stack.write(d, stack.build(choice))
            with mock.patch.object(stack, "can_download", return_value=True):
                plan = stack.plan_change(d, install="basics", outside=["jellyfin", "qbittorrent", "gluetun"])
        self.assertTrue(set(basics["apps"]) >= {"jellyfin", "qbittorrent"})
        self.assertNotIn("jellyfin", plan["add"])
        self.assertNotIn("qbittorrent", plan["add"])
        self.assertEqual(sorted(plan["outside"]), ["gluetun", "jellyfin", "qbittorrent"])


if __name__ == "__main__":
    unittest.main()
