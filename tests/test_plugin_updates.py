"""The plug-in update list (owner, 26 November 2026) for Settings, Plug-ins, Manage and Settings, Updates, Plug-ins: the
rows, the count, new permissions in words, what waits for you, the setting and the history, from what Starboard already
knows. Nothing is fetched to list them."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugin_life, plugin_updates, plugins_admin as pa, update_runs


class Config:
    def __init__(self):
        self.data = {"services": [], "plugins_auto_update": False}


class App:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.config = Config()


def add_plugin(data_dir, pid, version, permissions=()):
    os.makedirs(pa.folder(data_dir, pid), exist_ok=True)
    with open(os.path.join(pa.folder(data_dir, pid), "manifest.json"), "w") as f:
        json.dump({"manifest_version": 1, "id": pid, "name": pid.title(), "version": version, "permissions": list(permissions)}, f)
    with open(os.path.join(pa.folder(data_dir, pid), "state.json"), "w") as f:
        json.dump({"state": "installed"}, f)


class Listing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = App(self.tmp.name)
        update_runs._runs.clear()
        update_runs._loaded.discard(self.tmp.name)
        add_plugin(self.tmp.name, "alpha", "1.0.0", ["apps:read"])
        add_plugin(self.tmp.name, "beta", "1.0.0", ["apps:read"])
        add_plugin(self.tmp.name, "gamma", "1.0.0")

    def known(self, **more):
        base = {"alpha": {"version": "1.1.0", "changelog": "Faster", "manifest": "https://x/a.json", "sha256": "", "permissions": ["apps:read"], "released": ""},
                "beta": {"version": "1.1.0", "changelog": "", "manifest": "https://x/b.json", "sha256": "", "permissions": ["apps:read", "jellyfin:key"], "released": ""},
                "gamma": {"version": "2.0.0", "changelog": "", "manifest": "https://x/g.json", "sha256": "", "permissions": [], "released": ""}}
        base.update(more)
        return mock.patch.object(plugin_life, "updates_known", lambda d: base)

    def test_rows_counts_and_what_waits_for_you(self):
        with self.known():
            got = plugin_updates.listing(self.app)
        by = {t["id"]: t for t in got["items"]}
        self.assertEqual(got["counts"], {"total": 3, "by_kind": {"plugin": 3}})
        self.assertEqual((by["plugin:alpha"]["current"], by["plugin:alpha"]["latest"], by["plugin:alpha"]["held"]), ("1.0.0", "1.1.0", ""))
        # New permissions are said in words, with their risk, and the update waits for the owner.
        self.assertEqual([p["permission"] for p in by["plugin:beta"]["new_permissions"]], ["jellyfin:key"])
        self.assertIn("Jellyfin's API key", by["plugin:beta"]["new_permissions"][0]["words"])
        self.assertEqual(by["plugin:beta"]["new_permissions"][0]["risk"], "high")
        self.assertTrue(by["plugin:beta"]["held"])
        self.assertIn("big change", by["plugin:gamma"]["held"])  # 1.x to 2.x
        self.assertEqual(got["read"]["errors"], 0)

    def test_the_count_is_one_function(self):
        items = [{"update_available": True, "kind": "plugin"}, {"update_available": False, "kind": "plugin"},
                 {"update_available": True, "kind": "app"}]
        self.assertEqual(update_runs.counts(items), {"total": 2, "by_kind": {"plugin": 1, "app": 1}})

    def test_nothing_waiting_lists_every_plug_in_up_to_date(self):
        with mock.patch.object(plugin_life, "updates_known", lambda d: {}):
            got = plugin_updates.listing(self.app)
        self.assertEqual(got["counts"]["total"], 0)
        self.assertEqual(len(got["items"]), 3)
        self.assertTrue(all(not t["update_available"] for t in got["items"]))

    def test_the_setting_and_the_history_are_the_plug_in_ones(self):
        update_runs._new(self.tmp.name, "plugin:alpha", "plugin", "Alpha", "update", "0.9.0", "1.0.0", "automatic", [("install", "Installing")])
        update_runs._new(self.tmp.name, "app:sonarr", "app", "Sonarr", "update", "1", "2", "you", [("install", "Installing")])
        with self.known():
            got = plugin_updates.listing(self.app)
        self.assertEqual(got["auto"]["id"], "plugins")
        self.assertFalse(got["auto"]["active"])
        self.assertEqual([r["target"] for r in got["recent"]], ["plugin:alpha"])  # the app's run is not plug-in history
        self.assertIn("hours", got["hours_words"].lower() + "hours")


if __name__ == "__main__":
    unittest.main()
