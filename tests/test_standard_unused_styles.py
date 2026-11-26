"""Styles no page uses stay out of the core (Starboard patterns audit, 26 November 2026).

The design system marks the styles of components that no page of Starboard uses as the parts extras, media-extras,
logo-picker and wizard-review. They are in css/parts for the day a page needs one: the core style sheet has none of
those rules, and no page loads them (a page that needs one loads it, and then this test is changed with it)."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"
PARTS = ("extras", "media-extras", "logo-picker", "wizard-review")


def rules(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return {re.sub(r"\s+", " ", f"{sel.strip()} {{ {body.strip()} }}") for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text)}


class UnusedStyles(unittest.TestCase):
    def test_the_core_has_none_of_the_rules_in_a_part(self):
        core = rules((WEB / "css/components.css").read_text())
        for part in PARTS:
            moved = rules((WEB / "css/parts" / f"{part}.css").read_text())
            self.assertGreater(len(moved), 5, part)
            self.assertEqual(core & moved, set(), f"{part}: rules in both the core and the part")

    def test_each_part_is_well_formed(self):
        for part in PARTS:
            text = (WEB / "css/parts" / f"{part}.css").read_text()
            self.assertIn("@layer shared {", text)
            self.assertEqual(text.count("{"), text.count("}"), part)

    def test_no_page_loads_one_and_none_has_a_script(self):
        for page in WEB.glob("*.html"):
            for part in PARTS:
                self.assertNotIn(f"/css/parts/{part}.css", page.read_text(), page.name)
        for part in PARTS:
            self.assertFalse((WEB / "js/parts" / f"{part}.js").exists(), part)


if __name__ == "__main__":
    unittest.main()
