"""The own style's colours (DASH-388, owner, 13 November 2026): one of the design system's palettes for everyone on the
server, Blue (Mica) unless another is chosen, kept in a backup, and the palette files synced from the design system."""
import json
import os
import re
import tempfile
import unittest

from starboard import backup, config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class OwnColoursTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.config = config.Config(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_blue_by_default_and_shown_to_the_pages(self):
        self.assertEqual(self.config.data["own_colours"], "blue")
        self.assertEqual(self.config.public()["own_colours"], "blue")

    def test_a_palette_is_saved_and_another_word_refused(self):
        self.config.update_general({"own_colours": "lime"})
        self.assertEqual(config.Config(self.dir.name).data["own_colours"], "lime")
        with self.assertRaises(config.ConfigError):
            self.config.update_general({"own_colours": "pink"})
        self.assertEqual(self.config.data["own_colours"], "lime")

    def test_a_palette_that_has_gone_falls_back_to_blue(self):
        self.config.update_general({"own_colours": "rose"})
        path = os.path.join(self.dir.name, "config.json")
        with open(path) as f:
            data = json.load(f)
        data["own_colours"] = "gone"
        with open(path, "w") as f:
            json.dump(data, f)
        self.assertEqual(config.Config(self.dir.name).data["own_colours"], "blue")

    def test_a_renamed_palette_moves_to_its_new_name(self):
        """The design system replaced Indigo, Forest, Plum and Ember with Dusk, Lime, Rose and Amber (20 November
        2026): a page from before that names an old one gets the new one. (A settings file from before 0.31.0 is no
        longer converted when it loads, DASH-596.)"""
        moved = config.Config(self.dir.name)
        for old, new in (("forest", "lime"), ("indigo", "dusk"), ("plum", "rose"), ("ember", "amber")):
            moved.update_general({"own_colours": old})
            self.assertEqual(moved.data["own_colours"], new)
        with open(os.path.join(ROOT, "web", "js", "common.js")) as f:
            js = f.read()
        self.assertIn('RENAMED_COLOURS = { indigo: "dusk", plum: "rose", ember: "amber", forest: "lime" }', js)
        self.assertEqual(config.RENAMED_COLOURS, {"indigo": "dusk", "plum": "rose", "ember": "amber", "forest": "lime"})

    def test_everyday_right_and_kept_in_a_backup(self):
        self.assertEqual(config.general_right({"own_colours": "amber"}), "manage")
        self.assertIn("own_colours", backup.GENERAL_KEYS)

    def test_every_choice_has_its_palette_from_the_design_system(self):
        with open(os.path.join(ROOT, "web", "palettes.json")) as f:
            palettes = json.load(f)
        with open(os.path.join(ROOT, "web", "css", "palettes.css")) as f:
            css = f.read()
        self.assertEqual(sorted(palettes), sorted(c for c in config.OWN_COLOURS if c != "blue"))
        for name in palettes:
            self.assertIn(f':root[data-palette="{name}"]:where(:not(.pref-contrast))', css)
        with open(os.path.join(ROOT, "web", "js", "common.js")) as f:
            labels = re.search(r"PALETTE_LABELS = \{([^}]*)\}", f.read()).group(1)
        self.assertEqual(sorted(re.findall(r"(\w+):", labels)), sorted(config.OWN_COLOURS))


if __name__ == "__main__":
    unittest.main()
