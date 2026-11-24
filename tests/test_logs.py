"""Starboard's own log: personal details removed, days kept, the size limit (DASH-451), detailed logging, reading,
deleting all logs and the report."""

import json
import os
import tempfile
import time
import unittest
from unittest import mock

from starboard import logs
from starboard.config import Config, ConfigError


class ShownTest(unittest.TestCase):
    """DASH-534: the newest N lines, Alerts only, how many there are, and reading only the end of a file."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.settings = {"keep_days": 60, "max_mb": 50, "detail": "on", "detail_until": 0, "show_lines": 200, "alerts_only": False}
        self.log = logs.Log(self.dir.name, lambda: self.settings, lambda: [])
        self.addCleanup(self.dir.cleanup)

    def fill(self, n, every=10):
        for i in range(n):
            level = "error" if i % every == 0 else "warning" if i % every == 1 else "detail" if i % every == 2 else "info"
            self.log.write(level, "area", f"line {i}")

    def test_the_newest_lines_up_to_the_limit_and_how_many_there_are(self):
        self.fill(120)
        self.settings["show_lines"] = 50
        v = self.log.view()
        self.assertEqual((len(v["entries"]), v["total"], v["limit"], v["all_found"], v["filtered"]), (50, 120, 50, False, False))
        self.assertEqual([e["message"] for e in v["entries"]][:2], ["line 119", "line 118"])
        self.assertEqual(v["entries"][-1]["message"], "line 70")  # the newest 50, not the oldest
        self.settings["show_lines"] = 200
        v = self.log.view()
        self.assertEqual((len(v["entries"]), v["all_found"]), (120, True))

    def test_every_choice_works_and_a_wrong_one_means_the_default(self):
        for n in logs.SHOW_CHOICES:
            self.settings["show_lines"] = n
            self.assertEqual(self.log.show_lines(), n)
        for bad in (0, 7, "x", None, 100000):
            self.settings["show_lines"] = bad
            self.assertEqual(self.log.show_lines(), 200)
        self.assertEqual(logs.SHOW_CHOICES, (50, 100, 200, 500, 1000))
        self.assertEqual(logs.DEFAULTS["show_lines"], 200)

    def test_alerts_only_keeps_errors_and_warnings_and_combines_with_the_rest(self):
        self.fill(100)
        self.settings["alerts_only"] = True
        v = self.log.view()
        self.assertEqual({e["level"] for e in v["entries"]}, {"error", "warning"})
        self.assertEqual((len(v["entries"]), v["filtered"]), (20, True))
        self.assertEqual(len(self.log.view(limit=5)["entries"]), 5)  # with the line limit
        self.settings["show_lines"] = 50
        self.assertEqual(len(self.log.view(query="line 9")["entries"]), 2)  # line 90 (error) and 91 (warning), with the search
        self.assertEqual({e["level"] for e in self.log.view("problems")["entries"]}, {"error", "warning"})  # with the level
        self.assertEqual(self.log.view("detail")["entries"], [])  # detail entries are not alerts
        self.assertEqual(len(self.log.view(alerts_only=False)["entries"]), 50)  # and off, everything again

    def test_a_search_that_matches_a_few_still_finds_them_far_back(self):
        self.fill(600)
        self.settings["show_lines"] = 50
        v = self.log.view(query="line 13")
        self.assertEqual(len(v["entries"]), 11)  # line 13 and 130 to 139 are all found, however far back
        self.assertTrue(v["all_found"])

    def test_only_the_end_of_a_file_is_read(self):
        self.fill(6000)
        path = os.path.join(self.dir.name, "logs", self.log.files()[0])
        size = os.path.getsize(path)
        self.assertGreater(size, 4 * logs.BLOCK)
        read = []

        class Counting:
            def __init__(self, f):
                self.f = f

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self.f.close()

            def read(self, n=-1):
                data = self.f.read(n)
                read.append(len(data))
                return data

            def __getattr__(self, name):
                return getattr(self.f, name)
        with mock.patch.object(logs, "open", lambda p, mode="r", *a, **k: Counting(open(p, mode)), create=True):
            got = self.log.read(limit=50)
        self.assertEqual(len(got), 50)
        self.assertEqual(got[0]["message"], "line 5999")
        self.assertLessEqual(sum(read), 2 * logs.BLOCK)  # a block or two of a file many times larger

    def test_lines_that_cross_a_block_are_whole(self):
        self.log.write("info", "area", "x" * 5000)
        self.fill(2000)
        path = os.path.join(self.dir.name, "logs", self.log.files()[0])
        lines = list(logs._lines_backwards(path))
        self.assertEqual(len(lines), 2001)
        self.assertTrue(all(json.loads(line) for line in lines))
        with open(path, "rb") as f:
            self.assertEqual(list(reversed(lines)), [x for x in f.read().split(b"\n") if x])

    def test_the_count_is_kept_until_a_file_changes(self):
        self.fill(30)
        self.assertEqual(self.log.total(), 30)
        with mock.patch.object(logs, "_count_lines", side_effect=AssertionError("counted again")):
            self.assertEqual(self.log.total(), 30)
        self.log.write("info", "area", "one more")
        self.assertEqual(self.log.total(), 31)
        self.assertEqual(logs._count_lines(os.path.join(self.dir.name, "logs", self.log.files()[0])), 31)

    def test_a_file_that_does_not_end_in_a_new_line_is_counted_and_read(self):
        path = os.path.join(self.dir.name, "logs", "2026-01-01.log")
        with open(path, "w") as f:
            f.write(json.dumps({"t": 1, "level": "error", "area": "a", "message": "first"}) + "\n"
                    + json.dumps({"t": 2, "level": "error", "area": "a", "message": "second"}))
        self.assertEqual(self.log.total(), 2)
        self.assertEqual([e["message"] for e in self.log.read()], ["second", "first"])

    def test_the_report_uses_the_limit_and_alerts_only(self):
        self.fill(60)
        self.settings.update(show_lines=50, alerts_only=True)
        app = mock.Mock()
        app.config.data = {}
        app.version = "x"
        text = logs.report(app, self.log)
        self.assertIn("line 50", text)
        self.assertNotIn("line 52", text)  # an information line
        self.assertNotIn("line 3\n", text)  # older than the newest 50 alerts allow? line 3 is info


class RedactTest(unittest.TestCase):
    def test_personal_details_are_removed(self):
        cases = {
            "GET http://192.168.1.3:8989/api/v3/queue?apikey=abcdef0123456789abcdef0123456789": "abcdef0123456789",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def": "eyJ",
            "password=hunter22": "hunter22",
            '{"apiKey": "zzzzzzzzzzzzzzzzzzzzzzzzzz"}': "zzzz",
            "mail sam@example.com": "sam@example.com",
            "open /home/sam/media/file.json": "/home/sam",
            "fe80:0:0:0:1:2:3:4 down": "fe80",
            "https://media.example.org/web": "media.example.org",
        }
        for text, secret in cases.items():
            self.assertNotIn(secret, logs.redact(text), text)

    def test_names_given_to_starboard_are_removed_and_local_addresses_kept(self):
        out = logs.redact("Sam's server stopped; http://127.0.0.1:7878 and http://localhost:8096 fine; Cannot reach Sonarr", ["Sam's server"])
        self.assertIn("[name]", out)
        self.assertIn("127.0.0.1:7878", out)
        self.assertIn("Cannot reach Sonarr", out)


class LogTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.settings = {"keep_days": 60, "max_mb": 50, "detail": "off", "detail_until": 0}
        self.log = logs.Log(self.dir.name, lambda: self.settings, lambda: ["Sam's server"])

    def tearDown(self):
        self.dir.cleanup()

    def test_entries_are_written_redacted_and_read_newest_first(self):
        self.log.write("info", "apps", "Added Sonarr")
        self.log.write("error", "request", "token=secret123456 failed")
        got = self.log.read()
        self.assertEqual([e["message"] for e in got], ["token=[removed] failed", "Added Sonarr"])
        self.assertEqual([e["level"] for e in self.log.read("problems")], ["error"])
        self.assertEqual(len(self.log.read(query="sonarr")), 1)
        raw = open(os.path.join(self.dir.name, "logs", self.log.files()[0])).read()
        self.assertNotIn("secret123456", raw)

    def test_a_hidden_secret_is_never_logged_or_printed(self):
        import contextlib
        import io
        from unittest import mock
        self.addCleanup(logs._hidden.clear)
        logs.hide("Plain Pass 7")  # spaces: no pattern would catch it
        logs.hide("ab")  # too short to hide safely, so left alone
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.log.write("error", "install apps", "Jellyfin said: bad request (Plain Pass 7)")
            with mock.patch.object(logs, "_current", None):
                logs.event("info", "install apps", "Set up with Plain Pass 7")
        raw = open(os.path.join(self.dir.name, "logs", self.log.files()[0])).read()
        for where in (raw, out.getvalue()):
            self.assertNotIn("Plain Pass 7", where)
            self.assertIn("[removed]", where)
        self.assertEqual(logs._hidden, ["Plain Pass 7"])

    def test_detail_only_while_on_and_24_hours_runs_out(self):
        self.log.write("detail", "request", "GET /index.html 200")
        self.assertEqual(self.log.read(), [])
        self.settings.update(detail="day", detail_until=time.time() + 60)
        self.log.write("detail", "request", "GET /index.html 200")
        self.assertEqual(len(self.log.read("detail")), 1)
        self.settings["detail_until"] = time.time() - 1
        self.assertFalse(self.log.detailed())

    def day(self, days_ago, size=0, name=None):
        """A day file from days_ago, of about size bytes; returns its path."""
        name = name or time.strftime("%Y-%m-%d", time.localtime(time.time() - days_ago * 86400)) + ".log"
        path = os.path.join(self.dir.name, "logs", name)
        line = json.dumps({"t": 1, "level": "info", "area": "x", "message": "old"}) + "\n"
        with open(path, "w") as f:
            f.write(line * max(1, size // len(line)))
        return path

    def names(self):
        return sorted(os.listdir(os.path.join(self.dir.name, "logs")))

    def test_old_days_are_removed_when_a_new_day_starts(self):
        self.day(90)
        kept = self.day(10)
        self.log.write("info", "start", "new day")  # the first write of a day applies the limits
        self.assertEqual(len(self.log.files()), 2)
        self.assertTrue(os.path.exists(kept))

    def test_pruning_by_days(self):
        self.settings["keep_days"] = 7
        old, edge, recent = self.day(20), self.day(8), self.day(6)
        self.log.write("info", "start", "today")
        self.assertEqual([os.path.exists(p) for p in (old, edge, recent)], [False, False, True])

    def test_pruning_by_size_removes_the_oldest_days_first_and_never_today(self):
        self.settings["max_mb"] = 1
        oldest, middle, newest = self.day(3, 600_000), self.day(2, 600_000), self.day(1, 300_000)
        self.log.write("info", "start", "today")
        self.assertEqual([os.path.exists(p) for p in (oldest, middle, newest)], [False, True, True])
        self.assertLessEqual(self.log.summary()["bytes"], 1024 * 1024)
        # Today's file alone over the limit stays, and the rest go.
        today = self.day(0, 1_200_000)
        out = self.log.prune()
        self.assertEqual(out["removed"], 2)
        self.assertEqual(self.log.files(), [os.path.basename(today)])

    def test_both_limits_whichever_comes_first(self):
        self.settings.update(keep_days=14, max_mb=1)
        too_old = self.day(30, 1000)
        big_ones = [self.day(n, 400_000) for n in (5, 4, 3)]
        self.log.write("info", "start", "today")
        self.assertFalse(os.path.exists(too_old))  # by days, though small
        self.assertEqual([os.path.exists(p) for p in big_ones], [False, True, True])  # by size, the oldest first

    def test_the_size_written_today_is_counted_without_looking_at_the_folder(self):
        self.settings["max_mb"] = 1
        self.log.write("info", "start", "today")  # the day's first look: plenty of room
        old = self.day(2, 1_100_000)  # written after the look, so only the count can find it
        with mock.patch.object(self.log, "_prune", wraps=self.log._prune) as prune:
            self.log.write("info", "x", "y")
            prune.assert_not_called()  # room left: no look
            self.log.room = 10
            self.log.write("info", "x", "y" * 50)  # past the room: one look, which removes the older day
            prune.assert_called_once()
        self.assertFalse(os.path.exists(old))

    def test_a_missing_or_unreadable_file_does_not_stop_the_rest(self):
        self.settings["keep_days"] = 7
        gone = self.day(20)
        stuck = self.day(19)
        old = self.day(18)
        real_remove = os.remove

        def remove(path):
            if path == stuck:
                raise PermissionError(13, "Permission denied")
            if path == gone:
                real_remove(path)  # gone between the listing and the removal
                raise FileNotFoundError(2, "No such file")
            return real_remove(path)
        with mock.patch("starboard.logs.os.remove", side_effect=remove):
            out = self.log.prune()
        self.assertTrue(os.path.exists(stuck))
        self.assertFalse(os.path.exists(old))
        self.assertEqual(out["removed"], 2)  # the old one, and the one that went by itself
        with mock.patch("starboard.logs.os.stat", side_effect=OSError("unreadable")):
            self.assertEqual(self.log.summary()["bytes"], 0)  # nothing it can read is counted, and nothing fails

    def test_the_audit_log_and_update_log_count_and_old_audit_copies_go_first(self):
        self.settings["max_mb"] = 1
        logs_dir = os.path.join(self.dir.name, "logs")
        for name, size, age in (("audit.jsonl", 100, 0), ("audit.jsonl.1", 700_000, 5), ("audit.jsonl.2", 700_000, 9)):
            with open(os.path.join(logs_dir, name), "w") as f:
                f.write("x" * size)
            os.utime(os.path.join(logs_dir, name), (time.time() - age * 86400,) * 2)
        with open(os.path.join(self.dir.name, logs.UPDATE_LOG), "w") as f:
            f.write("== Preparing the update\n")
        day = self.day(1, 200_000)
        s = self.log.summary()
        self.assertEqual((s["days"], s["files"]), (1, 5))
        self.log.prune()
        self.assertEqual(self.names(), [os.path.basename(day), "audit.jsonl", "audit.jsonl.1"])  # the oldest copy went
        self.assertTrue(os.path.exists(os.path.join(self.dir.name, logs.UPDATE_LOG)))  # the last update's log stays

    def test_delete_all_keeps_today_s_file_and_says_who(self):
        self.day(3, 5000)
        self.day(1, 5000)
        self.log.write("info", "apps", "Added Sonarr")
        logs_dir = os.path.join(self.dir.name, "logs")
        for name in ("audit.jsonl", "audit.jsonl.1"):
            with open(os.path.join(logs_dir, name), "w") as f:
                f.write("{}\n" * 10)
        update_log = os.path.join(self.dir.name, logs.UPDATE_LOG)
        with open(update_log, "w") as f:
            f.write("== Preparing the update\n")
        today = time.strftime("%Y-%m-%d") + ".log"
        out = self.log.clear("a signed-in browser (session 1a2b3c4d)", update_running=True)
        self.assertEqual((out["removed"], out["emptied"]), (3, 2))
        self.assertGreater(out["freed"], 10_000)
        self.assertEqual(self.names(), [today, "audit.jsonl"])
        self.assertEqual(os.path.getsize(os.path.join(logs_dir, "audit.jsonl")), 0)
        self.assertTrue(os.path.exists(update_log))  # an update is running: its log stays
        entries = self.log.read()
        self.assertEqual(len(entries), 1)
        self.assertRegex(entries[0]["message"], r"^All logs deleted by a signed-in browser \(session 1a2b3c4d\): \d+ KB in 5 files$")
        self.assertEqual(self.log.files(), [today])  # Starboard keeps logging into the same file
        self.log.clear("the API key Home")
        self.assertFalse(os.path.exists(update_log))  # no update running: it goes too
        self.assertIn("by the API key Home", self.log.read()[0]["message"])

    def test_delete_all_with_nothing_there(self):
        out = self.log.clear()
        self.assertEqual(out, {"removed": 0, "emptied": 0, "freed": 0})
        self.assertEqual(self.log.read()[0]["message"], "All logs deleted: 0 bytes in 0 files")

    def test_size_words(self):
        self.assertEqual([logs.size_words(n) for n in (0, 1, 1023, 360448, 5 * 1024 ** 2 + 1, 15 * 1024 ** 2)],
                         ["0 bytes", "1 byte", "1023 bytes", "352 KB", "5.0 MB", "15 MB"])

    def test_settings_choices(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual((c.data["logs"]["keep_days"], c.data["logs"]["max_mb"]), (30, 50))
            c.update_general({"logs": {"detail": "day"}})
            self.assertGreater(c.data["logs"]["detail_until"], time.time() + 86000)
            c.update_general({"logs": {"keep_days": 14, "detail": "off"}})
            self.assertEqual((c.data["logs"]["keep_days"], c.data["logs"]["detail_until"]), (14, 0))
            with self.assertRaises(ConfigError):
                c.update_general({"logs": {"keep_days": 3}})
            with self.assertRaises(ConfigError):
                c.update_general({"logs": {"detail": "always"}})
            c.update_general({"logs": {"max_mb": 100}})
            self.assertEqual(c.data["logs"]["max_mb"], 100)
            for bad in (7, "lots", None, 0):
                with self.assertRaises(ConfigError):
                    c.update_general({"logs": {"max_mb": bad}})

    def test_a_starboard_from_before_keeps_its_days_and_gets_the_size_limit(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"logs": {"keep_days": 60, "detail": "off", "detail_until": 0}}, f)
            c = Config(d)
            self.assertEqual((c.data["logs"]["keep_days"], c.data["logs"]["max_mb"]), (60, 50))


if __name__ == "__main__":
    unittest.main()
