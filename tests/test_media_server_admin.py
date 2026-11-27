"""Administration of the media server in use from Starboard (DASH-568): libraries and scans, scheduled tasks, activity and logs
for Jellyfin, Emby and Plex, and where every other job is done. Answered from recorded answers of each server's documented
interface: no real Plex or Emby was available."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, mediaserver, services
from starboard.mediaservers import emby, plex
from tests.test_media_servers_other import EMBY, JF, PLEX, Fetch

DAY = {"Type": "DailyTrigger", "TimeOfDayTicks": 3 * 36_000_000_000 + 30 * 600_000_000}
MB_TABLE = {
    "/Library/VirtualFolders": [{"ItemId": "lib1", "Name": "Films", "CollectionType": "movies", "Locations": ["/data/media/movies", 5]}, {"Name": "no id"}, "junk"],
    "/Library/Refresh": "", "/Items/lib1/Refresh": "",
    "/ScheduledTasks": [{"Id": "t1", "Name": "Scan media library", "Category": "Library", "State": "Idle", "Triggers": [DAY, {"Type": "IntervalTrigger", "IntervalTicks": 12 * 36_000_000_000}, {"Type": "StartupTrigger"}],
                         "LastExecutionResult": {"Status": "Completed", "EndTimeUtc": "2026-11-27T03:31:00Z"}},
                        {"Id": "t2", "Name": "Clean logs", "State": "Running", "Triggers": []}, {"Name": "no id"}],
    "/ScheduledTasks/Running/t1": "",
    "/System/ActivityLog/Entries": {"Items": [{"Date": "2026-11-27T10:00:00Z", "Name": "Sam signed in", "ShortOverview": "from 192.168.1.5", "Severity": "Information"}, "junk"]},
    "/System/Logs": [{"Name": "log_20261126.log", "Size": 2048, "DateModified": "2026-11-26T23:59:00Z"}, {"Name": "log_20261127.log", "Size": 10, "DateModified": "2026-11-27T09:00:00Z"}],
    "/System/Logs/Log": "\n".join(f"line {i}" for i in range(500)),
}
PLEX_ADMIN = {
    "/library/sections": {"MediaContainer": {"Directory": [{"key": "1", "title": "Films", "type": "movie", "Location": [{"path": "/data/movies"}]}, {"key": "x;", "title": "bad"}]}},
    "/library/sections/1/all": {"MediaContainer": {"totalSize": 1234}},
    "/library/sections/1/refresh": "", "/library/sections/all/refresh": "",
    "/butler": {"ButlerTasks": {"ButlerTask": [{"name": "BackupDatabase", "title": "Backup database", "enabled": True}, {"name": "../x", "title": "bad"}, {"name": "CleanOldBundles", "enabled": False}]}},
    "/butler/BackupDatabase": "",
    "/accounts": {"MediaContainer": {"Account": [{"id": 1, "name": "Owner"}]}},
    "/status/sessions/history/all": {"MediaContainer": {"Metadata": [{"title": "Pilot", "grandparentTitle": "Harbour", "viewedAt": 1795000000, "accountID": 1}]}},
}


class Patched(unittest.TestCase):
    table = {}

    def setUp(self):
        self.fetch = Fetch(self.table)
        p = mock.patch.object(services, "_fetch", side_effect=self.fetch)
        p.start()
        self.addCleanup(p.stop)

    def seen(self, method):
        return [p for m, p, *_ in self.fetch.seen if m == method]


class BrowserAdmin(Patched):
    """Jellyfin and Emby ask the same questions, Emby under /emby."""

    @property
    def table(self):  # noqa: D401
        return MB_TABLE

    def setUp(self):
        self.fetch = Fetch(MB_TABLE)
        self.fetch_emby = Fetch({"/emby" + k: v for k, v in MB_TABLE.items()})
        self.cases = [(mediaserver.ADAPTERS["jellyfin"](), JF, self.fetch), (emby.Emby(), EMBY, self.fetch_emby)]

    def each(self):
        for one, svc, fetch in self.cases:
            with mock.patch.object(services, "_fetch", side_effect=fetch):
                yield one, [svc]

    def test_libraries_list_their_folders_and_leave_out_odd_rows(self):
        for one, saved in self.each():
            self.assertEqual(one.admin_libraries(saved), [{"id": "lib1", "name": "Films", "type": "movies", "folders": ["/data/media/movies"], "count": None}], one.name)

    def test_a_scan_of_one_or_all_and_a_full_refresh(self):
        for one, saved in self.each():
            self.assertEqual(one.admin_scan(saved, "", "new"), {"asked": True})
            one.admin_scan(saved, "lib1", "all")
        for _, _, fetch in self.cases:
            paths = [(m, u) for m, _, _, u in fetch.seen]
            self.assertTrue(any("/Library/Refresh" in u for m, u in paths))
            full = [u for m, u in paths if "/Items/lib1/Refresh" in u][0]
            self.assertIn("MetadataRefreshMode=FullRefresh", full)
            self.assertIn("ReplaceAllMetadata=true", full)
        for one, saved in self.each():
            for bad in (("../x", "new"), ("lib1", "sideways")):
                with self.assertRaises(ValueError):
                    one.admin_scan(saved, *bad)

    def test_tasks_say_when_they_run_in_plain_words_and_run_now(self):
        for one, saved in self.each():
            rows = one.admin_tasks(saved)
            self.assertEqual([r["id"] for r in rows], ["t1", "t2"])
            self.assertEqual(rows[0]["when"], "every day at 03:30, every 12 hours, when the server starts")
            self.assertEqual((rows[0]["state"], rows[1]["state"], rows[1]["when"]), ("idle", "running", "only when you run it"))
            self.assertEqual(rows[0]["last"], "Completed 2026-11-27 03:31")
            one.admin_run_task(saved, "t1")
            with self.assertRaises(ValueError):
                one.admin_run_task(saved, "t1/../../x")

    def test_activity_and_logs(self):
        for one, saved in self.each():
            self.assertEqual(one.admin_activity(saved), [{"when": "2026-11-27 10:00", "what": "Sam signed in", "who": "from 192.168.1.5", "kind": "Information"}])
            self.assertEqual([r["name"] for r in one.admin_logs(saved)], ["log_20261127.log", "log_20261126.log"], "newest first")
            text = one.admin_log(saved, "log_20261127.log")
            self.assertEqual(text.splitlines()[0], "line 200")
            self.assertEqual(len(text.splitlines()), 300)
            for bad in ("../../etc/passwd", "a/b", ""):
                with self.assertRaises(ValueError):
                    one.admin_log(saved, bad)

    def test_no_key_ever_goes_in_an_address(self):
        for one, saved in self.each():
            one.admin_tasks(saved)
        for _, _, fetch in self.cases:
            self.assertFalse([u for *_, u in fetch.seen if "made-up" in u])


class PlexAdmin(Patched):
    table = PLEX_ADMIN

    def setUp(self):
        super().setUp()
        self.one, self.list = plex.Plex(), [PLEX]

    def test_libraries_count_their_items_and_skip_a_bad_key(self):
        self.assertEqual(self.one.admin_libraries(self.list), [{"id": "1", "name": "Films", "type": "movies", "folders": ["/data/movies"], "count": 1234}])

    def test_scans(self):
        self.one.admin_scan(self.list, "1", "all")
        self.one.admin_scan(self.list, "", "new")
        self.assertEqual([u.split(":32400")[-1] for *_, u in self.fetch.seen if "refresh" in u], ["/library/sections/1/refresh?force=1", "/library/sections/all/refresh"])
        with self.assertRaises(ValueError):
            self.one.admin_scan(self.list, "1;2", "new")

    def test_the_butler_lists_and_runs_tasks_and_drops_odd_names(self):
        rows = self.one.admin_tasks(self.list)
        self.assertEqual([(r["id"], r["when"]) for r in rows], [("BackupDatabase", "every day, in the maintenance hours"), ("CleanOldBundles", "switched off")])
        self.one.admin_run_task(self.list, "BackupDatabase")
        self.assertEqual(self.seen("POST"), ["/butler/BackupDatabase"])
        with self.assertRaises(ValueError):
            self.one.admin_run_task(self.list, "Backup/../x")

    def test_activity_is_what_was_watched_with_the_account_name(self):
        got = self.one.admin_activity(self.list)
        self.assertEqual((got[0]["what"], got[0]["who"]), ("Watched Harbour: Pilot", "Owner"))

    def test_logs_are_not_offered_and_say_why(self):
        self.assertNotIn("admin_logs", self.one.capabilities)
        rows = {r["id"]: r for r in self.one.capability_rows()}
        self.assertIn("zip file", rows["admin_logs"]["why"])
        with self.assertRaises(services.ServiceError):
            self.one.admin_logs(self.list)


class Coverage(unittest.TestCase):
    def test_every_server_says_where_each_job_is_done(self):
        for cls in mediaserver.ADAPTERS.values():
            rows = cls().admin_coverage()
            self.assertGreaterEqual(len(rows), 14, cls.name)
            for r in rows:
                self.assertIn(r["who"], ("starboard", "later", "server", "no"))
                self.assertTrue(r["says"].endswith("."), (cls.name, r["job"]))
                self.assertTrue(r["page"] or r["who"] in ("starboard", "no") or r["job"].startswith("Backup"), (cls.name, r["job"], "a job done elsewhere gives its page"))
            self.assertFalse([r for r in rows if r["who"] == "starboard" and "On this tab" not in r["says"] and "Settings" not in r["says"]
                              and "System" not in r["says"] and "Ready to update" not in r["says"]], "where Starboard does it is named")

    def test_plex_says_plainly_what_plex_tv_holds(self):
        by = {r["job"]: r for r in plex.Plex().admin_coverage()}
        self.assertEqual(by["People: accounts, sharing and their rights"]["who"], "no")
        self.assertIn("plex.tv", by["People: accounts, sharing and their rights"]["says"])
        self.assertEqual(by["Remote access"]["who"], "no")

    def test_the_parts_offered_follow_the_capabilities(self):
        got = mediaserver.admin_overview({"services": [PLEX], "extras": {"media_server": "plex"}})
        self.assertEqual(got["parts"], ["libraries", "tasks", "activity"])
        self.assertEqual(mediaserver.admin_overview({"services": [], "extras": {"media_server": ""}}), {"active": "", "name": "", "parts": [], "coverage": []})


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from starboard.server import make_server
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        r, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def call(cls, method, path, body=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        headers = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            headers["Cookie"] = cls.cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r, json.loads(raw) if raw[:1] in (b"{", b"[") else raw

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.app.config.data["services"] = [{**JF, "id": "j1"}]
        self.app.config.data["extras"]["media_server"] = "jellyfin"
        services.forget()

    def test_every_route_needs_a_signed_in_person(self):
        for method, path in (("GET", "/api/media-server/admin"), ("GET", "/api/media-server/admin/libraries"), ("POST", "/api/media-server/admin/scan"), ("POST", "/api/media-server/admin/run")):
            self.assertIn(self.call(method, path, {}, cookie=False)[0].status, (401, 403), path)

    def test_the_overview_asks_the_server_nothing(self):
        with mock.patch.object(services, "_fetch", side_effect=AssertionError("nothing is asked")):
            r, got = self.call("GET", "/api/media-server/admin")
        self.assertEqual((r.status, got["active"], got["parts"]), (200, "jellyfin", ["libraries", "tasks", "activity", "logs"]))
        self.assertTrue(got["coverage"])

    def test_a_part_is_read_only_when_asked_and_a_scan_is_audited(self):
        fetch = Fetch(MB_TABLE)
        with mock.patch.object(services, "_fetch", side_effect=fetch):
            r, got = self.call("GET", "/api/media-server/admin/libraries")
            self.assertEqual((r.status, got["rows"][0]["name"]), (200, "Films"))
            r, got = self.call("POST", "/api/media-server/admin/scan", {"id": "lib1", "how": "new"})
            self.assertEqual(r.status, 200)
            self.assertIn("asked to scan that library", got["said"])
            self.assertEqual(self.call("POST", "/api/media-server/admin/scan", {"id": "../x", "how": "new"})[0].status, 400)
            self.assertEqual(self.call("POST", "/api/media-server/admin/run", {"id": ""})[0].status, 400)
            self.assertEqual(self.call("GET", "/api/media-server/admin/nonsense")[0].status, 404)
            self.assertEqual(self.call("GET", "/api/media-server/admin/log?name=../../x")[0].status, 400)
        with open(os.path.join(self.app.data_dir, "logs", "audit.jsonl")) as f:
            audit = f.read()
        self.assertIn("media_server_scan", audit)
        self.assertNotIn("made-up-jf-key", audit)

    def test_a_server_that_does_not_answer_says_so_in_words(self):
        with mock.patch.object(services, "_fetch", side_effect=services.ServiceError("Cannot reach Jellyfin")):
            r, got = self.call("GET", "/api/media-server/admin/tasks")
        self.assertEqual(r.status, 502)
        self.assertIn("Cannot reach Jellyfin", json.dumps(got))

    def test_no_media_server_means_nothing_to_read(self):
        self.app.config.data["extras"]["media_server"] = ""
        self.assertEqual(self.call("GET", "/api/media-server/admin/libraries")[0].status, 404)


if __name__ == "__main__":
    unittest.main()
