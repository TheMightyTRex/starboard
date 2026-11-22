"""Activity, History, Across apps (DASH-68): the capped file, what writes to it, and what it costs at rest."""
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import activity_log, services


class File(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(activity_log.start, None)

    def lines(self):
        with open(os.path.join(self.d, activity_log.FILE), encoding="utf-8") as f:
            return f.readlines()

    def test_newest_first_filters_and_pages(self):
        for i in range(60):
            activity_log.record(self.d, activity_log.KINDS[i % 3], "Reelix", f"Thing {i}", when=1000 + i)
        out = activity_log.listing(self.d)
        self.assertEqual((out["total"], len(out["items"]), out["cap"]), (60, 50, 500))
        self.assertEqual(out["items"][0]["what"], "Thing 59")
        self.assertEqual(out["counts"], {"added": 20, "failed": 20, "upgraded": 20})
        self.assertEqual(len(activity_log.listing(self.d, "all", 2)["items"]), 10)
        failed = activity_log.listing(self.d, "failed")
        self.assertEqual((failed["total"], {i["event"] for i in failed["items"]}, failed["items"][0]["tone"]), (20, {"Failed"}, "danger"))
        with self.assertRaises(ValueError):
            activity_log.listing(self.d, "grabbed")
        with self.assertRaises(ValueError):
            activity_log.record(self.d, "removed", "Reelix", "x")

    def test_capped_by_entries_and_by_size(self):
        long = "word " * 1000
        for i in range(activity_log.CAP + activity_log.SLACK + 50):
            activity_log.record(self.d, "failed", long, long, long, when=i)
        self.assertLessEqual(len(self.lines()), activity_log.CAP + activity_log.SLACK)
        out = activity_log.listing(self.d)
        self.assertEqual(out["total"], activity_log.CAP)
        self.assertEqual(max(len(i["detail"]) for i in out["items"]), 300)
        # the oldest went, the newest stayed, and the whole file stays small whatever is written
        self.assertGreaterEqual(min(json.loads(line)["t"] for line in self.lines()), 101)
        self.assertLess(os.path.getsize(os.path.join(self.d, activity_log.FILE)), 450 * 1024)

    def test_a_key_is_written_once_and_personal_details_go(self):
        self.assertTrue(activity_log.record(self.d, "failed", "Sonarr", "Not responding at 192.168.1.20", "sam@example.org", key="alert:down:1"))
        self.assertFalse(activity_log.record(self.d, "failed", "Sonarr", "Not responding", key="alert:down:1"))
        item = activity_log.listing(self.d)["items"][0]
        self.assertNotIn("192.168.1.20", item["what"])
        self.assertNotIn("sam@example.org", item["detail"])
        self.assertEqual(oct(os.stat(os.path.join(self.d, activity_log.FILE)).st_mode & 0o777), "0o600")

    def test_week_counts_and_clear(self):
        activity_log.record(self.d, "added", "Reelix", "Old", when=1000)
        activity_log.record(self.d, "added", "Reelix", "New", when=10 * 86400)
        activity_log.record(self.d, "upgraded", "Jellyfin", "Updated", when=10 * 86400)
        self.assertEqual(activity_log.week(self.d, now=10 * 86400 + 60), {"added": 1, "failed": 0, "upgraded": 1})
        self.assertEqual(activity_log.clear(self.d), 3)
        self.assertEqual(activity_log.listing(self.d)["total"], 0)

    def test_note_writes_only_for_a_running_app_and_never_raises(self):
        self.assertFalse(activity_log.note("added", "Kavita", "Added to Starboard"))
        activity_log.start(self.d)
        self.assertTrue(activity_log.note("added", "Kavita", "Added to Starboard"))
        with mock.patch.object(activity_log, "record", side_effect=OSError("disk full")):
            self.assertFalse(activity_log.note("added", "Kavita", "Added to Starboard"))

    def test_a_broken_line_is_left_out(self):
        activity_log.record(self.d, "added", "Reelix", "Fine")
        with open(os.path.join(self.d, activity_log.FILE), "a", encoding="utf-8") as f:
            f.write("{not json\n[1]\n")
        self.assertEqual(activity_log.listing(self.d)["total"], 1)


class AtRest(unittest.TestCase):
    def test_no_thread_no_file_and_no_call_until_something_happens(self):
        with tempfile.TemporaryDirectory() as d:
            before = threading.active_count()
            with mock.patch.object(services, "_api") as api:
                activity_log.start(d)
                self.addCleanup(activity_log.start, None)
                self.assertEqual(threading.active_count(), before)
                self.assertEqual(os.listdir(d), [])
                api.assert_not_called()


REELIX = {"items": [
    {"id": 9, "event_type": "imported", "date": "2026-11-20T10:00:00Z", "media": {"title": "Big Buck Bunny", "year": 2008},
     "quality": {"quality": "1080p"}, "data": {"is_upgrade": True}},
    {"id": 8, "event_type": "imported", "date": "2026-11-19T10:00:00Z", "media": {"title": "Sintel", "year": 2010}},
    {"id": 7, "event_type": "download_failed", "date": "2026-11-18T10:00:00Z", "source_title": "Tears.of.Steel.2012", "data": {"message": "No files found"}},
    {"id": 6, "event_type": "grabbed", "date": "2026-11-17T10:00:00Z", "source_title": "Sintel.2010"}], "total": 4}


class Gather(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        self.svc = [{"id": "reelix", "name": "Reelix", "type": "link", "icon": "reelix"}]

    def test_reelix_added_failed_upgraded_once(self):
        with mock.patch.object(services, "reelix_native", return_value=self.svc), \
                mock.patch.object(services, "_api", return_value=REELIX) as api:
            self.assertEqual(activity_log.gather(self.d, self.svc), [])
            self.assertEqual(activity_log.gather(self.d, self.svc), [])
            self.assertEqual(api.call_count, 2)  # one small page each time the page is opened, nothing more
        out = activity_log.listing(self.d)
        self.assertEqual([(i["kind"], i["what"], i["app"]) for i in out["items"]],
                         [("upgraded", "Big Buck Bunny (2008)", "Reelix"), ("added", "Sintel (2010)", "Reelix"),
                          ("failed", "Tears.of.Steel.2012", "Reelix")])
        self.assertEqual(out["items"][2]["detail"], "No files found")
        self.assertEqual(out["items"][0]["when"], "2026-11-20T10:00:00Z")

    def test_nothing_from_before_delete_history(self):
        with mock.patch.object(services, "reelix_native", return_value=self.svc), mock.patch.object(services, "_api", return_value=REELIX):
            activity_log.clear(self.d, now=activity_log._stamp("2026-11-19T12:00:00Z"))
            activity_log.gather(self.d, self.svc)
        self.assertEqual([i["what"] for i in activity_log.listing(self.d)["items"]], ["Big Buck Bunny (2008)"])

    def test_an_app_that_does_not_answer_is_named(self):
        with mock.patch.object(services, "reelix_native", return_value=self.svc), \
                mock.patch.object(services, "_api", side_effect=services.ServiceError("Cannot reach Reelix")):
            notes = activity_log.gather(self.d, self.svc)
        self.assertEqual(len(notes), 1)
        self.assertIn("Reelix did not answer", notes[0])

    def test_other_apps_recent_imports(self):
        rows = activity_log.from_recent([{"service_name": "Sonarr", "title": "Pioneer One", "detail": "S01E02 · Earthfall", "when": "2026-11-20T09:00:00Z", "quality": "720p"},
                                         {"service_name": "Radarr", "title": "Sintel", "detail": "Film", "when": "2026-11-20T08:00:00Z", "quality": ""}])
        self.assertEqual([(r[0], r[1], r[2]) for r in rows], [("added", "Sonarr", "Pioneer One S01E02"), ("added", "Radarr", "Sintel")])


class Hooks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        activity_log.start(self.d)
        self.addCleanup(activity_log.start, None)

    def test_a_problem_alert_is_a_failed_entry_once(self):
        from starboard import watch
        w = watch.Watch.__new__(watch.Watch)
        w.state = {"alerted": {}}
        w.settings = lambda: {"channel": {}}
        self.assertTrue(w.alert("down:sonarr", "Sonarr is not responding", "Home: Sonarr did not answer."))
        self.assertFalse(w.alert("down:sonarr", "Sonarr is not responding", "Home: Sonarr did not answer."))
        w.alert("full:Media", "Media is 91% full", "9 GB free.", "warning")       # a warning is not a failure
        w.alert("update:reelix:1", "Reelix was not updated", "It said no", "problem")  # the update writes its own entry
        items = activity_log.listing(self.d)["items"]
        self.assertEqual([(i["kind"], i["what"]) for i in items], [("failed", "Sonarr is not responding")])

    def test_an_update_is_upgraded_or_failed(self):
        from starboard import update_runs
        for state, said in (("updated", "Updated to 0.9.0"), ("failed", "The image was not found"), ("up-to-date", "Nothing to do")):
            run = {"id": f"r-{state}", "name": "Reelix", "target": "app:reelix", "action": "update", "from": "0.8.6", "to": "0.9.0", "steps": []}
            with mock.patch.object(update_runs, "_save"), mock.patch.object(update_runs.api_v1, "audit"):
                update_runs._end(self.d, run, state, said)
        items = activity_log.listing(self.d)["items"]
        self.assertEqual(sorted((i["kind"], i["app"], i["what"], i["detail"]) for i in items),
                         [("failed", "Reelix", "Reelix was not updated", "The image was not found"),
                          ("upgraded", "Reelix", "Reelix updated from 0.8.6 to 0.9.0", "")])

    def test_the_weekly_summary_says_the_week(self):
        from starboard import watch
        activity_log.record(self.d, "added", "Reelix", "Sintel (2010)")
        activity_log.record(self.d, "failed", "Reelix", "Was not updated")
        w = watch.Watch.__new__(watch.Watch)
        w.app = mock.Mock(data_dir=self.d, disks=[])
        w.settings = lambda: {"channel": {"kind": "ntfy"}}
        w.uptime = lambda services_: {}
        with mock.patch.object(watch.sysinfo, "disk_health", return_value={}), mock.patch.object(watch.sysinfo, "snapshot", return_value={}), \
                mock.patch.object(watch, "send") as send:
            w._weekly("Home", {"services": []})
        self.assertIn("This week: 1 added, 1 failed, 0 upgraded.", send.call_args[0][2])


if __name__ == "__main__":
    unittest.main()
