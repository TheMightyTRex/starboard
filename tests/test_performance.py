"""Presets and background work that runs only while it is on."""

import tempfile
import time
import unittest

from starboard import sysinfo
from starboard.config import Config, ConfigError


class PerformanceTest(unittest.TestCase):
    def test_presets_set_everything_and_a_change_by_hand_is_custom(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual(c.public()["performance"]["preset"], "balanced")
            c.update_general({"preset": "small"})
            self.assertFalse(c.data["watch"]["enabled"])
            self.assertFalse(c.data["performance"]["history"])
            self.assertEqual(c.public()["performance"]["preset"], "small")
            c.update_general({"performance": {"monitor_refresh": 10}})
            self.assertEqual(c.public()["performance"]["preset"], "custom")
            c.update_general({"preset": "everything"})
            self.assertEqual((c.data["watch"]["every"], c.data["performance"]["history_every"]), (5, 60))
            with self.assertRaises(ConfigError):
                c.update_general({"performance": {"monitor_refresh": 1}})
            with self.assertRaises(ConfigError):
                c.update_general({"preset": "turbo"})

    def test_history_thread_ends_when_turned_off(self):
        settings = {"history": True, "history_every": 60}
        with tempfile.TemporaryDirectory() as d:
            h = sysinfo.History(d, lambda: settings)
            self.assertTrue(h.thread.is_alive())
            settings["history"] = False
            h.ensure()
            h.thread.join(timeout=5)
            self.assertFalse(h.thread.is_alive() if h.thread else False)

    def test_self_usage_reports_memory_and_threads(self):
        me = sysinfo.self_usage()
        self.assertGreater(me["memory"], 1_000_000)
        self.assertIn("MainThread", me["threads"])
        time.sleep(0)


if __name__ == "__main__":
    unittest.main()
