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

    def test_the_old_default_teal_moves_to_blue_once(self):
        """Mica became the default (DASH-479): a settings file from before, on Teal, the old default, moves to Blue;
        Teal chosen after that stays Teal."""
        path = os.path.join(self.dir.name, "config.json")
        with open(path) as f:
            data = json.load(f)
        data.update(schema=2, own_colours="teal")
        with open(path, "w") as f:
            json.dump(data, f)
        moved = config.Config(self.dir.name)
        self.assertEqual(moved.data["own_colours"], "blue")
        moved.update_general({"own_colours": "teal"})
        self.assertEqual(config.Config(self.dir.name).data["own_colours"], "teal")

    def test_a_palette_is_saved_and_another_word_refused(self):
        self.config.update_general({"own_colours": "forest"})
        self.assertEqual(config.Config(self.dir.name).data["own_colours"], "forest")
        with self.assertRaises(config.ConfigError):
            self.config.update_general({"own_colours": "pink"})
        self.assertEqual(self.config.data["own_colours"], "forest")

    def test_a_palette_that_has_gone_falls_back_to_blue(self):
        self.config.update_general({"own_colours": "plum"})
        path = os.path.join(self.dir.name, "config.json")
        with open(path) as f:
            data = json.load(f)
        data["own_colours"] = "gone"
        with open(path, "w") as f:
            json.dump(data, f)
        self.assertEqual(config.Config(self.dir.name).data["own_colours"], "blue")

    def test_everyday_right_and_kept_in_a_backup(self):
        self.assertEqual(config.general_right({"own_colours": "ember"}), "manage")
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
