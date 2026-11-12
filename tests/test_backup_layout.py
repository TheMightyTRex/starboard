"""The settings backup holds every setting (owner, 12 November 2026: "is the backup updated with all the new
settings"): each setting is backed up, kept with its own check, or named as never backed up."""
import json
import os
import tempfile
import unittest

from starboard import backup
from starboard.config import DEFAULTS, Config


class Layout(unittest.TestCase):
    def test_every_setting_has_a_place(self):
        placed = set(backup.GENERAL_KEYS) | set(backup.OTHER_KEYS) | set(backup.NEVER_KEYS)
        self.assertEqual(sorted(set(DEFAULTS) - placed), [], "a new setting needs a place in backup.py")

    def test_new_settings_go_out_and_come_back(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            one = Config(a)
            one.data.update(history_keep_days=30, plugin_catalogues=[{"url": "https://example.org/c.json", "name": "Mine"}],
                            infinite_scroll=False, reelix_auto_update=True)
            one.data["dashboard"] = {"layout": "glance", "cards": None}
            one.save()
            os.makedirs(os.path.join(a, "plugins", "styles"))
            with open(os.path.join(a, "plugins", "styles", "manifest.json"), "w") as f:
                json.dump({"id": "styles", "name": "Styles", "version": "1.3.0", "settings": [{"key": "shade", "type": "switch", "label": "Shade"}]}, f)
            with open(os.path.join(a, "plugins", "styles", "settings.json"), "w") as f:
                json.dump({"shade": True}, f)
            os.makedirs(os.path.join(a, "library"))
            with open(os.path.join(a, "library", "network-logos.json"), "w") as f:
                json.dump({"bbc one": {"url": "https://x/y.png", "checked": 1, "tone": "dark"}}, f)
            out = backup.export(one, "0.16.6", a)
            self.assertEqual(out["settings"]["history_keep_days"], 30)
            self.assertFalse(out["settings"]["infinite_scroll"])
            self.assertEqual(out["plugins"]["styles"]["settings"], {"shade": True})
            self.assertEqual(out["logos"]["network-logos.json"], {"bbc one": {"tone": "dark"}})
            self.assertNotIn("auth", out["settings"])
            two = Config(b)
            backup.restore(two, out)
            self.assertEqual(two.data["history_keep_days"], 30)
            self.assertEqual(two.data["plugin_catalogues"][0]["name"], "Mine")
            self.assertTrue(two.data["reelix_auto_update"])
            self.assertEqual(backup.restore_plugin_settings(b, out["plugins"]), ["Styles"])  # not added there yet
            backup.restore_logo_choices(b, out["logos"])
            with open(os.path.join(b, "library", "network-logos.json")) as f:
                self.assertEqual(json.load(f)["bbc one"]["tone"], "dark")

    def test_bad_catalogue_address_is_dropped(self):
        with tempfile.TemporaryDirectory() as a:
            c = Config(a)
            backup._restore_others(c, {"plugin_catalogues": [{"url": "http://plain.example/c.json"}], "history_keep_days": 12})
            self.assertEqual(c.data["plugin_catalogues"], [])
            self.assertEqual(c.data["history_keep_days"], 0)


if __name__ == "__main__":
    unittest.main()
