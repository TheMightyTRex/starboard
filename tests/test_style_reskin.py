"""Style settings for a full reskin (API 1.2, 12 November 2026): fixed values, new contrast pairs, CSS behind High
contrast."""
import json
import os
import unittest

from starboard import plugin_styles as ps

STYLES = os.path.expanduser("~/src/starboard-plugins/styles/starboard-plugin.json")


def base():
    light = {"bg": "#ffffff", "header": "#ffffff", "surface": "#ffffff", "surface_raised": "#ffffff", "surface_sunken": "#eeeeee",
             "text": "#000000", "text_muted": "#333333", "border": "#555555", "divider": "#dddddd", "accent": "#0038a8",
             "accent_text": "#ffffff", "accent_soft": "#dde6fb", "focus": "#000000"}
    dark = {k: v for k, v in light.items()}
    dark.update(bg="#000000", header="#000000", surface="#000000", surface_raised="#111111", surface_sunken="#000000",
                text="#ffffff", text_muted="#dddddd", border="#bbbbbb", divider="#444444", accent="#ffd23f", accent_text="#000000",
                accent_soft="#3a3000", focus="#ffffff")
    return {"id": "tt", "name": "T", "light": light, "dark": dark}


class Reskin(unittest.TestCase):
    def errors(self, s):
        return [i["what"] for i in ps.check_style(s) if i["severity"] == "error"]

    def test_values_checked(self):
        self.assertEqual(self.errors({**base(), "card_style": "tonal", "tab_style": "boxed", "border_width": 2}), [])
        self.assertTrue(self.errors({**base(), "card_style": "wobbly"}))
        self.assertTrue(self.errors({**base(), "border_width": 9}))

    def test_gradient_needs_its_colour_and_contrast(self):
        s = {**base(), "primary_gradient": True}
        self.assertTrue(any("accent_to" in e for e in self.errors(s)))
        s["light"] = {**s["light"], "accent_to": "#eeeeee"}  # white words on near white: refused
        s["dark"] = {**s["dark"], "accent_to": "#ffe680"}
        self.assertTrue(any("accent_text on accent_to" in e for e in self.errors(s)))

    def test_css_behind_high_contrast(self):
        out = ps.css("styles", [{**base(), "card_style": "outlined", "header_style": "rule", "heading_case": "labels"}])
        self.assertIn(':root[data-style="styles.tt"]:not(.pref-contrast)', out)
        self.assertIn("border-bottom: 3px solid var(--color-text)", out)
        self.assertIn("text-transform: uppercase", out)

    @unittest.skipUnless(os.path.exists(STYLES), "the Styles plug-in is not checked out here")
    def test_published_styles_pass(self):
        for s in json.load(open(STYLES))["styles"]:
            self.assertEqual(self.errors(s), [], s["id"])


if __name__ == "__main__":
    unittest.main()
