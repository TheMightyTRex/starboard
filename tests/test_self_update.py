"""Update now and automatic Starboard updates (DASH-417): reading update.sh's progress, the quiet hours, when the
automatic update runs or waits, the task dialog's shape, the Update now route, and the setting's default."""
import datetime as dt
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from starboard import config as config_mod, jobs, self_update

ROOT = pathlib.Path(__file__).resolve().parents[1]

UPDATED = """== Preparing the update

== Fetching releases
You have:  v0.17.0
Available: v0.18.0

== Using the update steps from v0.18.0

== Fetching releases
You have:  v0.17.0
Available: v0.18.0

== Backing up your settings
Saved backups/starboard-data-x.tar.gz

== Installing v0.18.0

== Building v0.18.0

== Restarting Starboard

== Checking that Starboard answers

== Updated to v0.18.0
@@ finished 0
"""

WENT_BACK = """== Preparing the update
== Fetching releases
Available: v0.18.0
== Backing up your settings
== Installing v0.18.0
== Building v0.18.0
== Restarting Starboard
== Checking that Starboard answers
== The new version did not start. Going back to v0.17.0
== Building v0.17.0
== Restarting Starboard
== Checking that Starboard answers
Back on v0.17.0 with your settings restored. The failed version's data is in data.failed-update.
@@ finished 1
"""

REFUSED = """== Preparing the update
== Fetching releases
Stopped: files in this folder have been changed. Keep your changes elsewhere, then run: git checkout -- .
@@ finished 1
"""


class Progress(unittest.TestCase):
    def test_an_update_that_worked_has_every_step_done(self):
        p = self_update.parse(UPDATED)
        self.assertEqual(p["outcome"], "updated")
        self.assertEqual(p["to"], "v0.18.0")
        self.assertEqual({s["state"] for s in p["steps"]}, {"done"})

    def test_the_hand_over_to_the_new_update_sh_does_not_go_back_a_step(self):
        p = self_update.parse(UPDATED.split("== Backing up")[0])
        self.assertEqual(p["at"], "checking")
        self.assertIsNone(p["outcome"])

    def test_a_running_update_shows_where_it_is(self):
        p = self_update.parse(UPDATED.split("== Checking that")[0])
        self.assertEqual(p["at"], "restarting")
        states = {s["key"]: s["state"] for s in p["steps"]}
        self.assertEqual(states["building"], "done")
        self.assertEqual(states["restarting"], "now")
        self.assertEqual(states["answering"], "waiting")

    def test_going_back_is_said(self):
        p = self_update.parse(WENT_BACK)
        self.assertEqual(p["outcome"], "went-back")
        self.assertEqual(p["back_to"], "v0.17.0")
        self.assertIn("stopped", {s["state"] for s in p["steps"]})

    def test_a_stop_before_anything_changed_is_refused_with_its_reason(self):
        p = self_update.parse(REFUSED)
        self.assertEqual(p["outcome"], "refused")
        self.assertTrue(p["reason"].startswith("files in this folder have been changed"))
        title, text = self_update.words("refused", {"to": "v0.18.0"}, p)
        self.assertEqual(title, "Starboard was not updated")
        self.assertIn("git checkout -- .", text)


class Rules(unittest.TestCase):
    def test_quiet_hours_are_the_download_hours_or_one_to_six(self):
        at = lambda h: dt.datetime(2026, 11, 14, h, 30)
        self.assertTrue(self_update.in_quiet_hours({}, at(3)))
        self.assertFalse(self_update.in_quiet_hours({}, at(6)))
        hours = {"download_hours": {"enabled": True, "start": 22, "end": 2}}
        self.assertTrue(self_update.in_quiet_hours(hours, at(23)))
        self.assertTrue(self_update.in_quiet_hours(hours, at(1)))
        self.assertFalse(self_update.in_quiet_hours(hours, at(3)))

    def test_the_automatic_update_waits_until_every_rule_allows_it(self):
        night, day = dt.datetime(2026, 11, 14, 2), dt.datetime(2026, 11, 14, 14)
        on = {"starboard_auto_update": True}
        decide = self_update.automatic_decision
        self.assertEqual(decide({}, night, "v0.18.0", "0.17.0", {})[0], "wait")  # deactivated
        self.assertEqual(decide(on, day, "v0.18.0", "0.17.0", {}), ("wait", "Waiting for the quiet hours"))
        self.assertEqual(decide(on, night, "v0.17.0", "0.17.0", {}), ("wait", "Starboard is up to date"))
        self.assertEqual(decide(on, night, "v0.18.0-dev.1", "0.17.0", {})[0], "wait")
        self.assertIn("did not install last time", decide(on, night, "v0.18.0", "0.17.0", {"skip": "v0.18.0"})[1])
        self.assertEqual(decide(on, night, "v0.18.0", "0.17.0", {}), ("update", "v0.18.0"))

    def test_deactivated_by_default_admin_only_and_in_the_backup(self):
        self.assertFalse(config_mod.DEFAULTS["starboard_auto_update"])
        self.assertFalse(config_mod.DEFAULTS["reelix_auto_update"])
        self.assertEqual(config_mod.GENERAL_RIGHTS["starboard_auto_update"], "admin")
        from starboard import backup
        self.assertIn("starboard_auto_update", backup.GENERAL_KEYS)

    def test_the_job_is_listed_and_follows_the_setting(self):
        self.assertIn("starboardupdate", jobs.JOBS)
        app = mock.Mock(config=mock.Mock(data={"starboard_auto_update": False}))
        j = jobs.Jobs.__new__(jobs.Jobs)
        j.app = app
        self.assertFalse(j.enabled("starboardupdate"))
        app.config.data["starboard_auto_update"] = True
        self.assertTrue(j.enabled("starboardupdate"))


class Running(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = mock.Mock(data_dir=self.tmp.name, version="0.17.0", watch=None,
                             config=mock.Mock(data={"starboard_auto_update": True}))
        self.app.latest_release.return_value = "v0.18.0"
        self.native = mock.patch.object(self_update, "plan", return_value={"how": "native", "folder": "/srv/starboard"})
        self.native.start()

    def tearDown(self):
        mock.patch.stopall()
        self.tmp.cleanup()

    def write_log(self, text):
        pathlib.Path(self.tmp.name, self_update.LOG).write_text(text)

    def test_start_refuses_anything_but_a_newer_release(self):
        for to in ("main", "v0.17.0", "v0.16.0", "v0.18.0; rm -rf /"):
            with self.assertRaises(self_update.Refused):
                self_update.start(self.app, to)

    def test_start_records_it_and_launches_once(self):
        with mock.patch.object(self_update, "launch") as launch, mock.patch.object(self_update, "_follow"):
            out = self_update.start(self.app, "v0.18.0")
            launch.assert_called_once_with({"how": "native", "folder": "/srv/starboard"}, "v0.18.0")
            self.assertTrue(out["running"])
            with self.assertRaises(self_update.Refused):
                self_update.start(self.app, "v0.18.0")  # one at a time
        record = self_update.load(self.tmp.name)
        self.assertEqual((record["state"], record["by"], record["to"]), ("running", "you", "v0.18.0"))
        self.assertEqual(os.stat(os.path.join(self.tmp.name, self_update.STATE)).st_mode & 0o077, 0)

    def test_a_failed_update_is_skipped_by_the_automatic_one_until_update_now(self):
        with mock.patch.object(self_update, "launch"), mock.patch.object(self_update, "_follow"):
            self_update.start(self.app, "v0.18.0", by="automatic")
        self.write_log(WENT_BACK)
        record = self_update.finish(self.app)
        self.assertEqual((record["outcome"], record["skip"]), ("went-back", "v0.18.0"))
        night = dt.datetime(2026, 11, 14, 2)
        self.assertIn("did not install last time", self_update.automatic(self.app, night))
        with mock.patch.object(self_update, "launch"), mock.patch.object(self_update, "_follow"):
            self_update.start(self.app, "v0.18.0", by="you")  # Update now tries it again
        self.assertNotIn("skip", self_update.load(self.tmp.name))

    def test_the_task_dialog_follows_the_steps_and_ends_with_the_result(self):
        with mock.patch.object(self_update, "launch"), mock.patch.object(self_update, "_follow"):
            self_update.start(self.app, "v0.18.0")
        self.write_log(UPDATED.split("== Checking that")[0])
        j = self_update.job(self.app)
        self.assertFalse(j["finished"])
        self.assertIn("reconnects by itself", j["now"])
        self.write_log(UPDATED)
        j = self_update.job(self.app)
        self.assertTrue(j["finished"])
        self.assertTrue(j["ok"])
        self.assertEqual(j["title"], "Starboard is updated")

    def test_going_back_ends_with_a_warning_not_a_success(self):
        with mock.patch.object(self_update, "launch"), mock.patch.object(self_update, "_follow"):
            self_update.start(self.app, "v0.18.0")
        self.write_log(WENT_BACK)
        j = self_update.job(self.app)
        self.assertIsNone(j["ok"])
        self.assertEqual(j["tasks"][-1], {"id": "going-back", "label": "Going back to v0.17.0", "state": "done"})

    def test_a_launch_that_fails_says_why_and_records_it(self):
        with mock.patch.object(self_update, "launch", side_effect=OSError("no systemd-run")):
            with self.assertRaises(self_update.Refused):
                self_update.start(self.app, "v0.18.0")
        self.assertEqual(self_update.load(self.tmp.name)["outcome"], "refused")


class HelperContainer(unittest.TestCase):
    def test_the_helper_runs_as_the_folders_owner_never_root_and_takes_the_version_from_its_environment(self):
        body = self_update.helper_body({"how": "docker", "folder": "/srv/starboard", "uid": 1000, "gid": 1000, "socket_gid": 998}, "v0.18.0")
        self.assertEqual(body["User"], "1000:1000")
        self.assertIn("STARBOARD_UPDATE_TO=v0.18.0", body["Env"])
        self.assertNotIn("v0.18.0", body["Cmd"][-1])
        self.assertEqual(body["HostConfig"]["GroupAdd"], ["998"])
        self.assertIn("no-new-privileges:true", body["HostConfig"]["SecurityOpt"])
        self.assertTrue(body["HostConfig"]["AutoRemove"])


class Words(unittest.TestCase):
    def test_both_set_ups_read_the_updates_step_from_the_shared_files(self):
        answers = json.loads((ROOT / "web" / "setup-answers.json").read_text(encoding="utf-8"))["updates"]
        steps = [s["id"] for s in json.loads((ROOT / "web" / "setup-steps.json").read_text(encoding="utf-8"))["steps"]]
        self.assertLess(steps.index("hours"), steps.index("updates"))
        self.assertLess(steps.index("updates"), steps.index("alerts"))
        self.assertIn("deactivated unless you choose it", answers["later"])
        self.assertEqual([p["key"] for p in answers["parts"]], ["starboard_auto_update", "reelix_auto_update", "apps_auto_update",
                                                               "plugins_auto_update", "jellyfin_plugins_auto_update"])
        js = (ROOT / "web" / "js" / "settings.js").read_text(encoding="utf-8")
        self.assertIn('list.push({ id: "updates"', js)
        self.assertLess(js.index('list.push({ id: "hours"'), js.index('list.push({ id: "updates"'))
        self.assertIn('list.push({ id: "alerts"', js[js.index('list.push({ id: "updates"'):])  # the restore branch asks neither
        from starboard import terminal_setup as ts
        self.assertLess(ts.STEP_FUNCTIONS.index(ts.step_hours), ts.STEP_FUNCTIONS.index(ts.step_updates))
        self.assertLess(ts.STEP_FUNCTIONS.index(ts.step_updates), ts.STEP_FUNCTIONS.index(ts.step_alerts))


class TerminalStep(unittest.TestCase):
    def test_enter_keeps_every_part_deactivated_and_reelix_and_jellyfin_are_asked_only_when_installed(self):
        from tests.test_terminal_setup_rules import FakeApi, plain
        from starboard import setup_answers, terminal_setup as ts
        w = setup_answers.WORDS["updates"]
        reelix = next(p for p in w["parts"] if p["key"] == "reelix_auto_update")
        api = FakeApi()
        term, out = plain([""])
        self.assertTrue(ts.step_updates(api, term, {"choice": {"apps": ["sonarr"]}}))
        self.assertEqual(api.calls[-1], ("PUT", "/api/config/general", {"starboard_auto_update": False, "apps_auto_update": False,
                                                                        "plugins_auto_update": False}))
        self.assertIn(w["intro"].split(":")[0], " ".join(out.getvalue().split()))
        self.assertNotIn(reelix["hint"], out.getvalue())
        api, (term, out) = FakeApi(), plain(["1,2,5"])
        state = {"choice": {"apps": ["reelix", "jellyfin"]}}
        self.assertTrue(ts.step_updates(api, term, state))
        self.assertEqual(api.calls[-1][2], {"starboard_auto_update": True, "reelix_auto_update": True, "apps_auto_update": False,
                                            "plugins_auto_update": False, "jellyfin_plugins_auto_update": True})
        self.assertEqual(ts.updates_summary(state["updates_chosen"]), "Starboard, Reelix and Jellyfin's plug-ins")
        self.assertEqual(ts.updates_summary([]), w["summary_none"])
        self.assertEqual(ts.updates_summary(["plugins_auto_update"]), "Plug-ins")
        self.assertFalse(ts.step_updates(FakeApi(), plain()[0], {"start": "restore"}))

    def test_the_browser_set_up_uses_the_same_parts_and_rule(self):
        js = (ROOT / "web" / "js" / "settings.js").read_text(encoding="utf-8")
        self.assertIn('w.parts.filter((p) => p.when === "always" || (step.has || {})[p.when])', js)
        self.assertIn('has: { reelix: coming(["reelix"]), jellyfin: coming(["jellyfin"]) }', js)
        self.assertIn("function updatesSummary(w, cfg)", js)

if __name__ == "__main__":
    unittest.main()
