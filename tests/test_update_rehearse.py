"""The plug-in tester's update rehearsal (DASH-423): python3 -m starboard.plugin_tester --previous old new."""
import json
import os
import tempfile
import unittest

from starboard import plugin_tester, plugin_update

OLD = {"id": "x", "version": "1.0.0", "permissions": ["apps:read"],
       "settings": [{"key": "minutes", "type": "number", "default": 30}, {"key": "colour", "type": "text", "default": "teal"}]}


def new(**kw):
    m = {"id": "x", "version": "1.1.0", "permissions": ["apps:read"],
         "settings": [{"key": "every_minutes", "type": "number", "default": 30}, {"key": "colour", "type": "text", "default": "teal"}],
         "update": {"migrations": [{"version": "1.1.0", "rename": {"minutes": "every_minutes"}}]}}
    m.update(kw)
    return m


class Rehearse(unittest.TestCase):
    def test_a_good_update_keeps_the_settings(self):
        issues = plugin_update.rehearse(OLD, new())
        self.assertFalse([i for i in issues if i[0] == "error"])
        self.assertIn("minutes is now every_minutes", issues[-1][1])

    def test_a_setting_left_behind_is_an_error(self):
        issues = plugin_update.rehearse(OLD, new(update={}))
        self.assertTrue(any(sev == "error" and "minutes" in what for sev, what, _ in issues))

    def test_an_older_or_equal_version_is_an_error(self):
        self.assertEqual(plugin_update.rehearse(OLD, new(version="1.0.0"))[0][0], "error")

    def test_new_permissions_are_said_as_never_updating_by_itself(self):
        issues = plugin_update.rehearse(OLD, new(permissions=["apps:read", "jellyfin:admin"]))
        self.assertTrue(any("never updates by itself" in what for _, what, _ in issues))

    def test_a_changed_type_needs_a_new_default(self):
        m = new(settings=[{"key": "every_minutes", "type": "number", "default": 30}, {"key": "colour", "type": "choice", "default": 2}])
        self.assertTrue(any(sev == "warning" and "colour" in what for sev, what, _ in plugin_update.rehearse(OLD, m)))

    def test_the_tester_takes_previous(self):
        d = tempfile.mkdtemp()
        old_path = os.path.join(d, "old.json")
        with open(old_path, "w") as f:
            json.dump(OLD, f)
        bad = os.path.join(d, "new.json")
        with open(bad, "w") as f:
            json.dump(new(version="0.9.0"), f)
        self.assertEqual(plugin_tester.main(["--previous"]), 2)
        self.assertNotEqual(plugin_tester.main(["--previous", old_path, bad]), 0)


if __name__ == "__main__":
    unittest.main()
