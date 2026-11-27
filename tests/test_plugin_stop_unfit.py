"""A plug-in this Starboard cannot run is stopped, with its reason, and kept (DASH-603, security fix 1 and the clean break)."""
import copy
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugin_life, plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND


class StopUnfit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/starboard/data/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)
        p = mock.patch.object(pa, "_compose_run", return_value=(True, ""))
        self.compose = p.start()
        self.addCleanup(p.stop)
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        pa.save_settings(self.tmp.name, "on-demand", {"quality": "720p"})
        pa.set_state(self.tmp.name, "on-demand", "enabled")
        self.where = pa.folder(self.tmp.name, "on-demand")

    def test_a_plugin_that_fits_is_left_running(self):
        self.assertEqual(plugin_life.stop_unfit(self.tmp.name), [])
        self.assertEqual(pa._read(os.path.join(self.where, "state.json"), {})["state"], "enabled")
        self.compose.assert_not_called()

    def test_a_range_that_leaves_this_starboard_out_stops_it_and_says_why(self):
        with mock.patch.object(plugins, "API_VERSION", "2.0.0"):
            self.assertEqual(plugin_life.stop_unfit(self.tmp.name), ["On demand"] if ON_DEMAND["name"] == "On demand" else [ON_DEMAND["name"]])
            s = plugin_life.status(self.tmp.name, "on-demand")
        self.assertTrue(any(c.args[2] == "stop" for c in self.compose.call_args_list))
        self.assertEqual((s["state"], s["button"]), ("not-supported", "Check for an update"))
        self.assertIn("2.0.0", s["sentence"])
        self.assertIn("settings and data are kept", s["sentence"])
        self.assertIn("stopped", pa._read(os.path.join(self.where, "state.json"), {})["message"].lower())

    def test_it_stays_installed_with_its_settings_and_key(self):
        with mock.patch.object(plugins, "API_VERSION", "2.0.0"):
            plugin_life.stop_unfit(self.tmp.name)
        self.assertTrue(os.path.exists(os.path.join(self.where, "manifest.json")))
        self.assertEqual(pa._read(os.path.join(self.where, "settings.json"), {})["quality"], "720p")
        self.assertTrue(os.path.exists(os.path.join(self.where, "key")))

    def test_it_cannot_be_turned_on_again_while_it_does_not_fit(self):
        with mock.patch.object(plugins, "API_VERSION", "2.0.0"):
            plugin_life.stop_unfit(self.tmp.name)
            with self.assertRaisesRegex(ValueError, "2.0.0"):
                pa.enable(self.tmp.name, "on-demand")
        pa.enable(self.tmp.name, "on-demand")  # fits again: works as normal
        self.assertEqual(plugin_life.status(self.tmp.name, "on-demand")["state"], "enabled")

    def test_a_removed_item_is_named_in_words(self):
        m = copy.deepcopy(ON_DEMAND)
        m["permissions"] = list(m.get("permissions") or []) + ["gone:permission"]
        why = plugin_life.does_not_fit(m)
        self.assertIn("gone:permission", why)
        self.assertIn("does not have", why)
        self.assertEqual(plugin_life.does_not_fit({**m, "permissions": []}), "")
        self.assertIn("manifest field wibble", plugin_life.does_not_fit({**ON_DEMAND, "wibble": 1}))
        self.assertIn("setting type", plugin_life.does_not_fit({**ON_DEMAND, "settings": [{"key": "a", "type": "gone"}]}))

    def test_a_plugin_that_was_never_on_is_not_touched(self):
        pa.set_state(self.tmp.name, "on-demand", "disabled")
        with mock.patch.object(plugins, "API_VERSION", "2.0.0"):
            self.assertEqual(plugin_life.stop_unfit(self.tmp.name), [])
        self.compose.assert_not_called()


if __name__ == "__main__":
    unittest.main()
