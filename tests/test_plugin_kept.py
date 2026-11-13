"""Optimisation review (owner, 13 November 2026): every page asks /api/session, which read and parsed each plug-in's
manifest (13 KB for On demand), and the plug-ins list, cards and jobs read about 13 files for each plug-in. Plug-in
files read only to show them are now parsed once and kept while the file is unchanged (DASH-397)."""
import json
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from starboard import plugin_life, plugins_admin as pa
from tests.test_plugins import ON_DEMAND


class KeptPluginFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/starboard/data/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")

    def test_parsed_once_while_unchanged(self):
        pa.listing(self.tmp.name)
        real = json.load
        with mock.patch("starboard.plugins_admin.json.load", side_effect=real) as parsed:
            for _ in range(5):
                pa.listing(self.tmp.name)
                pa.added(self.tmp.name)
                plugin_life.jobs(self.tmp.name)
        self.assertEqual(parsed.call_count, 0)

    def test_changes_show_at_once(self):
        self.assertEqual(pa.listing(self.tmp.name)[0]["state"], "installed")
        before = {s["key"]: s["value"] for s in pa.listing(self.tmp.name)[0]["settings"]}
        self.assertEqual(before["min_seeders"], 5)
        pa.save_settings(self.tmp.name, "on-demand", {"min_seeders": 10})
        after = {s["key"]: s["value"] for s in pa.listing(self.tmp.name)[0]["settings"]}
        self.assertEqual(after["min_seeders"], 10)
        path = os.path.join(pa.folder(self.tmp.name, "on-demand"), "state.json")
        with open(path) as f:
            st = json.load(f)
        with open(path + ".new", "w") as f:
            json.dump({**st, "state": "disabled"}, f)
        os.replace(path + ".new", path)
        self.assertEqual(pa.listing(self.tmp.name)[0]["state"], "disabled")

    def test_a_removed_plugin_is_gone(self):
        self.assertEqual([p["id"] for p in pa.added(self.tmp.name)], ["on-demand"])
        shutil.rmtree(pa.folder(self.tmp.name, "on-demand"))
        self.assertEqual(pa.added(self.tmp.name), [])
        self.assertEqual(pa.listing(self.tmp.name), [])


if __name__ == "__main__":
    unittest.main()
