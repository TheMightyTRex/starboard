"""Menu rows (owner, 26 November 2026): when a row shows icons only, two tabs must not look the same, and the three icons that did
(Pictures, Tdarr and Updates) are changed."""
import importlib.util
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("shell", os.path.join(ROOT, "starboard", "shell.py"))
shell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shell)


class MenuIcons(unittest.TestCase):
    def test_no_two_tabs_in_one_row_share_an_icon(self):
        for key, _, _, items in shell.MENU:
            for label, _, pages in items:
                icons = [ic for _, _, ic in pages]
                self.assertEqual(len(icons), len(set(icons)), f"{key}, {label}: {icons}")
            first = [ic for _, ic, _ in items]
            self.assertEqual(len(first), len(set(first)), f"{key}: first level")

    def test_the_three_swaps(self):
        rows = {p: ic for _, _, _, items in shell.MENU for _, _, pages in items for p, _, ic in pages}
        self.assertEqual(rows["settings-general-pictures.html"], "image")
        self.assertEqual(rows["settings-tdarr.html"], "cpu")
        self.assertEqual(rows["settings-updates.html"], "circle-arrow-up")

    def test_every_icon_is_in_the_sprite(self):
        with open(os.path.join(ROOT, "web", "icons", "sprite.svg"), encoding="utf-8") as f:
            have = set(re.findall(r'<symbol id="i-([^"]+)"', f.read()))
        for _, _, _, items in shell.MENU:
            for _, ic, pages in items:
                for _, _, ic2 in pages:
                    self.assertIn(ic2, have)
