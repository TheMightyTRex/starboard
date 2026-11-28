"""Design system parts no page loads are not in Starboard (DASH-596, 27 November 2026).

web/parts-used.json names the parts this app loads. Every other part, and its styles, stays in the design system for the
day a page needs one: then the name goes in the list, tools/sync.py writes the part, and the page loads it."""
import json
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"
USED = json.loads((WEB / "parts-used.json").read_text())["use"]


class OnlyTheUsedParts(unittest.TestCase):
    def test_the_folders_hold_exactly_the_parts_in_the_list(self):
        for kind in ("css", "js"):
            have = {p.stem for p in (WEB / kind / "parts").glob("*")}
            self.assertLessEqual(have, set(USED), f"{kind}/parts has a part that is not in parts-used.json")

    def test_every_part_in_the_list_is_loaded_by_a_page(self):
        text = "".join(p.read_text() for p in WEB.glob("*.html"))
        lazy = (WEB / "js/plugin-pages.js").read_text()  # the plug-in page parts load when a plug-in answers with them (API 1.26)
        for part in USED:
            if part in lazy:
                self.assertRegex(lazy, rf'"{re.escape(part)}"', part)
                continue
            self.assertRegex(text, rf"/(css|js)/parts/{re.escape(part)}\.(css|js)", part)

    def test_each_style_part_is_well_formed(self):
        for path in (WEB / "css/parts").glob("*.css"):
            text = path.read_text()
            self.assertIn("@layer shared {", text)
            self.assertEqual(text.count("{"), text.count("}"), path.name)


if __name__ == "__main__":
    unittest.main()
