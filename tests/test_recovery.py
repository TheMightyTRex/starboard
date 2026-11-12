"""After an unexpected shutdown (DASH-88): one check at start, a report on System, Overview and through Alerts."""
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from starboard import recovery

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FakeConfig:
    def __init__(self, services, channel=None):
        self.data = {"services": services, "site_name": "Home", "watch": {"channel": channel or {}}}


class FakeApp:
    def __init__(self, data_dir, disks=(), services=(), channel=None):
        self.data_dir, self.disks, self.config = data_dir, list(disks), FakeConfig(list(services), channel)


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_clean_stop_says_nothing_and_a_cut_is_noticed(self):
        self.assertIsNone(recovery.at_start(self.d, boot="a", now=1000))  # the first start ever
        recovery.mark_clean(self.d)
        self.assertIsNone(recovery.at_start(self.d, boot="b", now=2000))  # stopped cleanly, then a restart
        verdict = recovery.at_start(self.d, boot="c", now=3000)  # no clean stop, a new boot: the power went off
        self.assertEqual(verdict["kind"], "server")
        self.assertEqual(recovery.at_start(self.d, boot="c", now=4000)["kind"], "starboard")  # same boot: Starboard killed

    def test_the_check_reports_in_words_and_sends_an_alert(self):
        disk = os.path.join(self.d, "media")
        os.mkdir(disk)
        app = FakeApp(self.d, disks=[("Media", disk), ("Gone", os.path.join(self.d, "missing"))],
                      services=[{"id": "a", "name": "Jellyfin"}, {"id": "b", "name": "Reelix"}],
                      channel={"kind": "ntfy", "url": "https://ntfy.example/x"})
        with mock.patch("starboard.watch.send") as send:
            report = recovery.check(app, {"kind": "server", "last_seen": 0},
                                    status_all=lambda apps: [{"id": "a", "state": "up"}, {"id": "b", "state": "down"}],
                                    pool_status=lambda: {"set_up": True, "mounted": True, "job": {"state": "running", "action": "balance"}},
                                    backup_status=lambda d: {"state": "none"})
        self.assertTrue(report["title"].startswith("The server went off without shutting down at about"))
        self.assertIn("1 of 2 folders answering", report["checked"])
        self.assertIn("1 of 2 apps answering", report["checked"])
        self.assertIn("the pool is mounted", report["checked"])
        self.assertTrue(any("Not answering: Reelix" in p for p in report["problems"]))
        self.assertTrue(any("balance" in p for p in report["problems"]))
        send.assert_called_once()
        self.assertEqual(recovery.report(self.d)["title"], report["title"])
        recovery.dismiss(self.d)
        self.assertIsNone(recovery.report(self.d))

    def test_nothing_needed_fixing(self):
        app = FakeApp(self.d)
        report = recovery.check(app, {"kind": "starboard", "last_seen": 0}, status_all=lambda a: [],
                                pool_status=lambda: {"set_up": False}, backup_status=lambda d: {"state": "none"})
        self.assertEqual(report["problems"], [])
        self.assertTrue(report["message"].endswith("Nothing needed fixing."))

    def test_starboard_notes_a_clean_stop(self):
        main = (ROOT / "starboard" / "__main__.py").read_text()
        self.assertIn("signal.signal(signal.SIGTERM, stop_cleanly)", main)
        self.assertIn("recovery.mark_clean(data_dir)", main)
        self.assertIn("loadRecovery", (ROOT / "web" / "js" / "system.js").read_text())


if __name__ == "__main__":
    unittest.main()
