"""Settings, Plug-ins: each plug-in's tab has its own icon (owner, 26 November 2026: "It is hard to know which one is which
on the phone"). The icons come from the shared line icon set by plug-in id, with a neutral one for the rest."""
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


def tab_icons():
    body = re.search(r"const PLUGIN_TAB_ICONS = \{(.*?)\};", read("web", "js", "common.js"), re.S).group(1)
    return dict(re.findall(r'"([a-z0-9-]+)": "([a-z0-9-]+)"', body))


class PluginTabIcons(unittest.TestCase):
    def test_every_icon_is_in_the_shared_sprite(self):
        sprite = set(re.findall(r'<symbol id="i-([^"]+)"', read("web", "icons", "sprite.svg")))
        for pid, name in tab_icons().items():
            self.assertIn(name, sprite, pid)

    def test_no_two_plug_ins_share_an_icon_and_none_looks_like_a_neighbour_or_the_default(self):
        icons = tab_icons()
        self.assertEqual(len(set(icons.values())), len(icons), "two plug-ins share an icon")
        for taken in ("puzzle", "list-checks", "layout-grid"):  # the default, Manage and Catalogue
            self.assertNotIn(taken, icons.values())

    def test_the_plug_ins_starboard_lists_and_ships_have_one(self):
        with open(os.path.join(ROOT, "plugins", "catalogue.json"), encoding="utf-8") as f:
            ids = {e["id"] for e in json.load(f)["plugins"]}
        ids |= {"livetv", "on-demand"}
        self.assertEqual(sorted(ids - set(tab_icons())), [])

    def test_a_plug_in_without_one_gets_the_neutral_puzzle_piece(self):
        self.assertIn('icon(PLUGIN_TAB_ICONS[p.id] || "puzzle")', read("web", "js", "common.js"))

    def test_the_icon_is_hidden_from_screen_readers_and_the_name_stays_as_text(self):
        js = read("web", "js", "common.js")
        self.assertIn('a.querySelector(".menu-tabs__label").textContent = p.name', js)
        self.assertIn('svg.setAttribute("aria-hidden", "true")', js)  # icon() is decorative beside the name

    def test_icons_only_tabs_are_44px_wide_and_name_the_current_and_focused_tab(self):
        css = read("web", "css", "components.css")
        tab = re.search(r"\.menu-tabs--scroll\.is-compact a \{(.*?)\}", css, re.S).group(1)
        self.assertIn("min-width: var(--control-h)", tab)
        self.assertIn("flex: none", tab)
        self.assertIn('.menu-tabs--scroll.is-compact a[aria-current="page"] .menu-tabs__label', css)
        self.assertIn(".menu-tabs--scroll.is-compact a:focus-visible .menu-tabs__label", css)
        self.assertIn('nav.classList.add("menu-tabs--scroll")', read("web", "js", "common.js"))
        self.assertIn("a.title = name", read("web", "js", "components.js"))

    def test_a_notice_with_buttons_puts_them_on_their_own_row_on_a_phone(self):
        self.assertRegex(read("web", "css", "app.css"), r"max-width: 600px\) \{\s*\.notice > \.actions \{ grid-column: 2 / -1; \}")


if __name__ == "__main__":
    unittest.main()
