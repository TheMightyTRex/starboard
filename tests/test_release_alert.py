"""A new Starboard release through Alerts (DASH-105): one line, at most once a week, once for each version."""
import threading
import unittest
from unittest import mock

from starboard import watch
from starboard.server import newer


class FakeApp:
    def __init__(self, latest, version="0.15.4"):
        self.latest, self.version, self.repo = latest, version, "TheMightyTRex/starboard"

    def latest_release(self):
        return self.latest


class ReleaseAlertTest(unittest.TestCase):
    def make(self, latest, channel=True):
        w = watch.Watch.__new__(watch.Watch)
        w.app, w.state, w.lock = FakeApp(latest), {}, threading.Lock()
        w.settings = lambda: {"releases": True, "channel": {"kind": "ntfy", "url": "https://ntfy.example/x"} if channel else {}}
        return w

    def test_one_line_once_for_each_version(self):
        w = self.make("v0.16.0")
        with mock.patch.object(watch, "send") as sent:
            w._release("Harbour")
            w._release("Harbour")
        self.assertEqual(sent.call_count, 1)
        self.assertIn("Starboard 0.16.0 is out", sent.call_args[0][1])
        self.assertIn("releases/tag/v0.16.0", sent.call_args[0][2])

    def test_nothing_when_up_to_date_or_no_channel(self):
        for w in (self.make("v0.15.4"), self.make("v0.15.3"), self.make(None), self.make("v0.16.0", channel=False)):
            with mock.patch.object(watch, "send") as sent:
                w._release("Harbour")
            self.assertEqual(sent.call_count, 0)

    def test_versions_compare_as_numbers(self):
        self.assertTrue(newer("v0.10.0", "0.9.9"))
        self.assertFalse(newer("v0.15.4", "0.15.4"))
        self.assertFalse(newer("nonsense", "0.1.0"))


if __name__ == "__main__":
    unittest.main()
