"""Scheduled backups (DASH-17) and the saved settings copies kept per version (DASH-109)."""
import json
import os
import tempfile
import types
import unittest
from datetime import datetime
from unittest import mock

from starboard import backup, backup_schedule as bs, full_backup
from starboard.config import Config, ConfigError, prune_saved, saved_versions


class Times(unittest.TestCase):
    def test_nightly_is_the_next_three_oclock(self):
        self.assertEqual(bs.next_run("nightly", datetime(2026, 11, 13, 2, 59)), datetime(2026, 11, 13, 3, 0))
        self.assertEqual(bs.next_run("nightly", datetime(2026, 11, 13, 3, 0)), datetime(2026, 11, 14, 3, 0))

    def test_weekly_is_sunday_at_three(self):
        # 13 November 2026 is a Friday; the Sunday after is the 15th.
        self.assertEqual(bs.next_run("weekly", datetime(2026, 11, 13, 12, 0)), datetime(2026, 11, 15, 3, 0))
        self.assertEqual(bs.next_run("weekly", datetime(2026, 11, 15, 2, 0)), datetime(2026, 11, 15, 3, 0))
        self.assertEqual(bs.next_run("weekly", datetime(2026, 11, 15, 4, 0)), datetime(2026, 11, 22, 3, 0))
        self.assertEqual(bs.previous_run("weekly", datetime(2026, 11, 15, 4, 0)), datetime(2026, 11, 15, 3, 0))

    def test_monthly_is_the_first_at_three(self):
        self.assertEqual(bs.next_run("monthly", datetime(2026, 11, 13, 12, 0)), datetime(2026, 12, 1, 3, 0))
        self.assertEqual(bs.next_run("monthly", datetime(2026, 12, 1, 2, 59)), datetime(2026, 12, 1, 3, 0))
        self.assertEqual(bs.next_run("monthly", datetime(2026, 12, 1, 3, 0)), datetime(2027, 1, 1, 3, 0))
        self.assertEqual(bs.previous_run("monthly", datetime(2026, 12, 1, 3, 0)), datetime(2026, 12, 1, 3, 0))
        self.assertEqual(bs.previous_run("monthly", datetime(2026, 11, 30, 23, 0)), datetime(2026, 11, 1, 3, 0))

    def test_monthly_in_months_shorter_than_31_days(self):
        # 30 November, 28 February and a leap-year 29 February: never a 31st that is not there.
        self.assertEqual(bs.next_run("monthly", datetime(2026, 11, 30, 4, 0)), datetime(2026, 12, 1, 3, 0))
        self.assertEqual(bs.next_run("monthly", datetime(2027, 2, 28, 4, 0)), datetime(2027, 3, 1, 3, 0))
        self.assertEqual(bs.next_run("monthly", datetime(2028, 2, 29, 4, 0)), datetime(2028, 3, 1, 3, 0))
        self.assertEqual(bs.next_run("monthly", datetime(2027, 1, 31, 4, 0)), datetime(2027, 2, 1, 3, 0))
        self.assertEqual(bs.previous_run("monthly", datetime(2027, 3, 15)), datetime(2027, 3, 1, 3, 0))
        self.assertEqual(bs.previous_run("monthly", datetime(2027, 3, 1, 1, 0)), datetime(2027, 2, 1, 3, 0))
        self.assertEqual(bs.next_run("monthly", datetime(2026, 12, 31, 23, 59)), datetime(2027, 1, 1, 3, 0))

    def test_off_and_manual_have_no_run(self):
        self.assertIsNone(bs.next_run("off", datetime(2026, 11, 13)))
        self.assertIsNone(bs.next_run("manual", datetime(2026, 11, 13)))

    def test_how_many_are_kept(self):
        self.assertEqual((bs.keep_for("monthly"), bs.keep_for("weekly"), bs.keep_for("nightly"), bs.keep_for("manual"), bs.keep_for("off")),
                         (6, 4, 7, 5, 5))

    def test_the_choices_go_from_least_to_most_often(self):
        from starboard.config import BACKUP_SCHEDULES
        self.assertEqual(bs.MODES, ("off", "manual", "monthly", "weekly", "nightly"))
        self.assertEqual(BACKUP_SCHEDULES, bs.MODES)


class Setting(unittest.TestCase):
    def test_choices_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual(c.data["backup_schedule"], "off")
            c.update_general({"backup_schedule": "weekly", "backup_keep_versions": 10})
            self.assertEqual((c.data["backup_schedule"], c.data["backup_keep_versions"]), ("weekly", 10))
            c.update_general({"backup_schedule": "monthly"})
            self.assertEqual(c.data["backup_schedule"], "monthly")
            with self.assertRaises(ConfigError):
                c.update_general({"backup_schedule": "hourly"})
            with self.assertRaises(ConfigError):
                c.update_general({"backup_keep_versions": 3})

    def test_the_schedule_goes_in_a_settings_backup(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            one = Config(a)
            one.update_general({"backup_schedule": "nightly", "backup_keep_versions": 20})
            two = Config(b)
            backup.restore(two, backup.export(one, "0.16.6"))
            self.assertEqual((two.data["backup_schedule"], two.data["backup_keep_versions"]), ("nightly", 20))


class SavedCopies(unittest.TestCase):
    def make(self, folder, names_versions):
        os.makedirs(folder, exist_ok=True)
        for name, _ in names_versions:
            with open(os.path.join(folder, name), "w") as f:
                f.write("{}")
        with open(os.path.join(folder, "versions.json"), "w") as f:
            json.dump({n: v for n, v in names_versions if v}, f)

    def test_keeps_every_copy_of_the_newest_five_versions(self):
        with tempfile.TemporaryDirectory() as d:
            folder = os.path.join(d, "backups")
            rows = [(f"config-2026-11-{day:02d}-000000-before-migration.json", v) for day, v in
                    [(9, "0.7"), (8, "0.7"), (7, "0.6"), (6, "0.5"), (5, "0.4"), (4, "0.3"), (3, "0.2"), (2, "0.1"), (1, "")]]
            self.make(folder, rows)
            gone = prune_saved(folder, 5)
            self.assertEqual(sorted(gone), sorted(n for n, _ in rows[-3:]))  # 0.2, 0.1 and the one with no version
            self.assertNotIn(rows[-1][0], saved_versions(folder))
            self.assertTrue(os.path.exists(os.path.join(folder, rows[1][0])))  # the second copy of 0.7 stays

    def test_unrecorded_copies_count_as_one_old_version(self):
        with tempfile.TemporaryDirectory() as d:
            folder = os.path.join(d, "backups")
            self.make(folder, [(f"config-2026-10-{day:02d}-000000-before-restore.json", "") for day in range(1, 20)])
            self.assertEqual(prune_saved(folder, 5), [])

    def test_a_new_copy_records_its_version_and_removes_the_oldest(self):
        with tempfile.TemporaryDirectory() as d:
            folder = os.path.join(d, "backups")
            self.make(folder, [(f"config-2026-11-0{i}-000000-before-migration.json", f"0.{i}") for i in range(1, 6)])
            c = Config(d)
            c.version = "0.9.0"
            c.backup("before-restore")
            versions = saved_versions(folder)
            self.assertIn("0.9.0", versions.values())
            self.assertNotIn("config-2026-11-01-000000-before-migration.json", os.listdir(folder))
            self.assertEqual(len([n for n in os.listdir(folder) if n.startswith("config-")]), 5)
            listed = backup.saved_copies(c)
            self.assertEqual(listed[0]["version"], "0.9.0")

    def test_lowering_the_setting_removes_at_once(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            c.update_general({"backup_keep_versions": 20})
            folder = os.path.join(d, "backups")
            self.make(folder, [(f"config-2026-11-{i:02d}-000000-before-migration.json", f"0.{i}") for i in range(1, 13)])
            c.update_general({"backup_keep_versions": 5})
            self.assertEqual(len([n for n in os.listdir(folder) if n.startswith("config-")]), 5)


class Key(unittest.TestCase):
    @unittest.skipUnless(hasattr(full_backup.hashlib, "scrypt"), "no scrypt here")
    def test_key_is_kept_never_the_password_and_never_backed_up(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(full_backup, "_place", return_value=("/mnt", "/mnt/backups")):
                full_backup.save_key(d, "a long backup password", "/mnt/backups", True)
            with open(os.path.join(d, full_backup.KEY_FILE)) as f:
                self.assertNotIn("a long backup password", f.read())
            self.assertEqual(os.stat(os.path.join(d, full_backup.KEY_FILE)).st_mode & 0o777, 0o600)
            kept = full_backup.saved_key(d)
            self.assertEqual(kept["key"], full_backup.key_of("a long backup password", kept["salt"]))
            self.assertTrue(kept["pictures"])
            self.assertNotIn(full_backup.KEY_FILE, [rel for _, rel in full_backup._starboard_files(d, True)])
            full_backup.forget_key(d)
            self.assertIsNone(full_backup.saved_key(d))

    def test_short_password_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(full_backup, "_place", return_value=("/mnt", "/mnt/backups")):
                with self.assertRaises(full_backup.BackupError):
                    full_backup.save_key(d, "short", "/mnt/backups", False)


class Run(unittest.TestCase):
    def app(self, d, mode):
        c = Config(d)
        c.update_general({"backup_schedule": mode})
        return types.SimpleNamespace(data_dir=d, config=c, version="0.16.6")

    def test_asks_the_server_job_with_how_many_to_keep(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as jobs:
            os.makedirs(os.path.join(jobs, "requests"))
            with mock.patch.dict(os.environ, {"STARBOARD_JOBS_DIR": jobs}):
                s = bs.Scheduler(self.app(d, "nightly"))
                said = s.run()
                self.assertIn("server's backup job", said)
                with open(os.path.join(jobs, "requests", "backup")) as f:
                    self.assertEqual(json.load(f), {"keep": 7, "scheduled": True})
                st = s.status()
                self.assertEqual(st["mode"], "nightly")
                self.assertTrue(st["server_job"])
                self.assertIsNotNone(st["next"])
                self.assertEqual(st["last_result"], said)

    def test_nothing_to_back_up_says_so(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"STARBOARD_JOBS_DIR": ""}):
            s = bs.Scheduler(self.app(d, "weekly"))
            self.assertTrue(s.run().startswith("Nothing was backed up"))

    def test_manual_reminds_when_there_is_no_recent_backup(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"STARBOARD_JOBS_DIR": ""}):
            self.assertTrue(bs.Scheduler(self.app(d, "manual")).status()["remind"])
            self.assertFalse(bs.Scheduler(self.app(d, "off")).status()["remind"])

    def test_no_thread_unless_scheduled(self):
        with tempfile.TemporaryDirectory() as d:
            s = bs.Scheduler(self.app(d, "manual"))
            s.ensure()
            self.assertIsNone(s.thread)

    def test_a_new_choice_does_not_count_as_missed(self):
        with tempfile.TemporaryDirectory() as d:
            s = bs.Scheduler(self.app(d, "nightly"))
            s.save({"mode": "nightly", "since": 0})
            self.assertFalse(s._missed() and bs.previous_run("nightly", datetime.now()).timestamp() < 0)
            s.save({"mode": "nightly", "since": datetime.now().timestamp()})
            self.assertFalse(s._missed())


    def test_a_server_off_on_the_first_catches_up_once(self):
        with tempfile.TemporaryDirectory() as d:
            s = bs.Scheduler(self.app(d, "monthly"))
            chosen = datetime(2026, 10, 20).timestamp()
            s.save({"mode": "monthly", "since": chosen})
            # Off from 30 November to the 4th: the 1 December run is made once when it starts again.
            self.assertTrue(s._missed(now=datetime(2026, 12, 4, 9, 0)))
            s.save({"mode": "monthly", "since": chosen, "last_run": datetime(2026, 12, 4, 9, 0).timestamp()})
            self.assertFalse(s._missed(now=datetime(2026, 12, 4, 9, 5)))
            self.assertFalse(s._missed(now=datetime(2026, 12, 20, 9, 0)))
        with tempfile.TemporaryDirectory() as d:
            # A weekly run more than a day late is not made (the next one is soon); a monthly one still is.
            w = bs.Scheduler(self.app(d, "weekly"))
            w.save({"mode": "weekly", "since": datetime(2026, 10, 20).timestamp()})
            self.assertTrue(w._missed(now=datetime(2026, 11, 15, 9, 0)))   # Sunday the 15th, 6 hours late
            self.assertFalse(w._missed(now=datetime(2026, 11, 17, 9, 0)))  # 2 days late

    def test_monthly_keeps_six(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as jobs:
            os.makedirs(os.path.join(jobs, "requests"))
            with mock.patch.dict(os.environ, {"STARBOARD_JOBS_DIR": jobs}):
                s = bs.Scheduler(self.app(d, "monthly"))
                s.run()
                with open(os.path.join(jobs, "requests", "backup")) as f:
                    self.assertEqual(json.load(f), {"keep": 6, "scheduled": True})
                self.assertEqual(s.status()["keep"], 6)

    def test_monthly_asks_the_full_backup_to_keep_six(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"STARBOARD_JOBS_DIR": ""}):
            s = bs.Scheduler(self.app(d, "monthly"))
            saved = {"folder": "/mnt/backups", "pictures": False, "saved": 1}
            with mock.patch.object(full_backup, "saved_key", return_value=saved), \
                    mock.patch.object(full_backup, "start") as start, mock.patch.object(s, "_wait_full", return_value="Made a full backup"):
                s.run()
            self.assertEqual(start.call_args.kwargs["keep"], 6)

    def test_monthly_prunes_to_the_newest_six(self):
        # Nine monthly backups at the other place: the three oldest go, by the date in their names; nothing else is touched.
        import subprocess
        from starboard import backup_copies
        with tempfile.TemporaryDirectory() as folder:
            names = [f"starboard-full-2026-{m:02d}-01-030000.starboard" for m in range(1, 10)]
            for n in names + ["notes.txt"]:
                open(os.path.join(folder, n), "w").close()
            subprocess.run(["sh", "-c", backup_copies._prune_script(folder, bs.keep_for("monthly"))], check=True)
            self.assertEqual(sorted(os.listdir(folder)), sorted(names[3:] + ["notes.txt"]))


if __name__ == "__main__":
    unittest.main()
