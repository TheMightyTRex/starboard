"""Reduce motion Off means full movement, even when the device asks for less (DASH-437, 15 November 2026).

Display offers Match device, On and Off. On (pref-motion) always stills movement; Match device follows the device's
prefers-reduced-motion; Off (pref-motion-off) must win over the device. Before DASH-437 the media queries in
tokens.css and components.css, and two scroll checks in components.js, ignored pref-motion-off. These checks fail if
a reduced-motion rule or script comes back that the Off choice cannot override. The browser check is in
tools/a11y/tasks.mjs (T23)."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"


def media_blocks(css):
    """The body of every @media (prefers-reduced-motion: reduce) block, matched by braces."""
    for m in re.finditer(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{", css):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(css[i], 0)
            i += 1
        yield css[m.end():i - 1]


def parts(selector):
    """A selector list split at its top-level commas (not those inside :is() or :not())."""
    out, depth, start = [], 0, 0
    for i, ch in enumerate(selector):
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and not depth:
            out.append(selector[start:i])
            start = i + 1
    return [p.strip() for p in out + [selector[start:]] if p.strip()]


def selectors(block):
    """Each rule's selector list inside a block (comments taken out)."""
    block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    return [s.strip() for s in re.findall(r"([^{}]+)\{[^{}]*\}", block)]


class ReduceMotionOffTest(unittest.TestCase):
    def test_every_reduced_motion_rule_leaves_out_off(self):
        for name in ("tokens.css", "components.css"):
            css = (WEB / "css" / name).read_text()
            blocks = list(media_blocks(css))
            self.assertTrue(blocks, f"{name} has no reduced-motion rules to check")
            for block in blocks:
                for sel in selectors(block):
                    for part in parts(sel):
                        self.assertIn(":root:not(.pref-motion-off)", part, f"{name}: '{part}' ignores Reduce motion Off")

    def test_starboard_styles_have_no_reduced_motion_query_of_their_own(self):
        for path in (WEB / "css").glob("*.css"):
            if path.name in ("tokens.css", "components.css"):
                continue
            for block in media_blocks(path.read_text()):
                for sel in selectors(block):
                    for part in parts(sel):
                        self.assertIn("pref-motion-off", part, f"{path.name}: '{part}' ignores Reduce motion Off")

    def test_scripts_ask_motion_still_not_the_media_query(self):
        js = (WEB / "js" / "components.js").read_text()
        # The media query is read in one place, motionStill(), after On and Off.
        self.assertEqual(js.count("prefers-reduced-motion"), 1, "components.js reads prefers-reduced-motion outside motionStill()")
        still = js[js.index("const motionStill"):js.index("prefers-reduced-motion")]
        self.assertIn('"pref-motion-off"', still)
        for path in (WEB / "js").glob("*.js"):
            if path.name in ("components.js", "snaglist.js"):  # Snaglist is its own project, with its own setting
                continue
            self.assertNotIn("prefers-reduced-motion", path.read_text(), f"{path.name} reads the device setting directly: use SharedComponents.motionStill()")

    def test_display_radios_set_both_classes(self):
        js = (WEB / "js" / "components.js").read_text()
        self.assertIn('html.classList.toggle("pref-motion-off", input.value === "off")', js)
        common = (WEB / "js" / "common.js").read_text()
        self.assertIn('root.classList.toggle("pref-motion-off", prefs.motion === "off")', common)


if __name__ == "__main__":
    unittest.main()
