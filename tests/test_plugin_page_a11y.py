"""Starboard's drawing of plug-in pages, after the accessibility check of the Philips Hue and Uptime and status pages
(20 November 2026, axe-core with the plug-ins' tools/hue_screens): three findings in Starboard, not in the plug-ins.
These read the page's own files, as the other page tests do; the plug-in check is the one that drives a browser."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"


def custom_screen():
    js = (WEB / "js" / "plugins.js").read_text()
    start = js.index("function customScreen(p, s) {")
    end = js.index("\nfunction ", start + 10)
    return js[start:end]


class SectionTabsStayClearTest(unittest.TestCase):
    """Target size (WCAG 2.5.8): scrolled, a section tab sat part under the sticky header, too small to press."""

    def test_the_tabs_stay_under_the_header_in_a_tall_enough_window(self):
        css = (WEB / "css" / "app.css").read_text()
        block = re.search(r"@media \(min-width: 768px\) and \(min-height: 640px\) \{(.*?)\n\}", css, re.S)
        self.assertIsNotNone(block, "the sticky topic tabs need their media query")
        self.assertRegex(block.group(1), r"\.topic-tabs \{ position: sticky; top: calc\(var\(--header-h\) \+ 1px\)")
        self.assertIn(":root:has(.site-header__tabs) .topic-tabs { top: calc(var(--header-h) + var(--tabs-h) + 1px); }", block.group(1))

    def test_focus_is_never_under_the_tabs(self):
        """Focus not obscured (2.4.11): the page keeps the tabs' height clear above what has focus, as they wrap."""
        css = (WEB / "css" / "app.css").read_text()
        self.assertIn("scroll-padding-top: calc(var(--header-h) + var(--tabs-h) + var(--topic-tabs-h, 48px) + var(--space-4))", css)
        core = (WEB / "js" / "settings-core.js").read_text()
        self.assertIn('setProperty("--topic-tabs-h", `${nav.offsetHeight}px`)', core)


class HeadingsFollowTheSectionTest(unittest.TestCase):
    """Heading order: a grouped custom list went from the section's h2 straight to h4."""

    def test_no_fixed_heading_levels_in_a_custom_screen(self):
        body = custom_screen()
        self.assertEqual(re.findall(r'el\("h[1-6]"', body), [], "a custom screen's headings take their level from level()")
        self.assertIn('box.closest("section")?.querySelector("h2, h3, h4")', body)

    def test_groups_and_rows_go_one_level_down_each(self):
        body = custom_screen()
        self.assertIn("g ? h(at, { text: g }) : null", body)
        self.assertIn('h(cards || g ? at + 1 : at, { class: "row__title", text: it.title })', body)
        self.assertIn("itemRows(data, shown, level() + (here ? 1 : 0))", body)


class ChangeEditorIsAListItemTest(unittest.TestCase):
    """Valid list markup: with Change open (Philips Hue's schedules) the editor's li had role="group", so the list
    held something that was not a list item."""

    def test_the_editor_is_a_plain_list_item_holding_its_group(self):
        body = custom_screen()
        self.assertIn('el("li", { class: "attach-form", id: base }, el("div", { class: "stack-2", role: "group"', body)
        self.assertNotRegex(body, r'el\("li", \{[^}]*role: "group"')


if __name__ == "__main__":
    unittest.main()
