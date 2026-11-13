"""Starboard's own log: personal details removed, days kept, detailed logging, reading, deleting and the report."""

import json
import os
import tempfile
import time
import unittest

from starboard import logs
from starboard.config import Config, ConfigError


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
        self.settings = {"keep_days": 60, "detail": "off", "detail_until": 0}
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

    def test_old_days_are_removed_and_delete_removes_everything(self):
        old = time.strftime("%Y-%m-%d", time.localtime(time.time() - 90 * 86400))
        with open(os.path.join(self.dir.name, "logs", f"{old}.log"), "w") as f:
            f.write(json.dumps({"t": 1, "level": "info", "area": "x", "message": "old"}) + "\n")
        self.log.write("info", "start", "new day")  # the first write of a day removes old days
        self.assertEqual(len(self.log.files()), 1)
        self.assertEqual(self.log.clear(), 1)
        self.assertEqual(self.log.files(), [])

    def test_settings_choices(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual(c.data["logs"]["keep_days"], 60)
            c.update_general({"logs": {"detail": "day"}})
            self.assertGreater(c.data["logs"]["detail_until"], time.time() + 86000)
            c.update_general({"logs": {"keep_days": 14, "detail": "off"}})
            self.assertEqual((c.data["logs"]["keep_days"], c.data["logs"]["detail_until"]), (14, 0))
            with self.assertRaises(ConfigError):
                c.update_general({"logs": {"keep_days": 3}})
            with self.assertRaises(ConfigError):
                c.update_general({"logs": {"detail": "always"}})


if __name__ == "__main__":
    unittest.main()
