"""Settings groups with their sections as level 2 pages (DASH-389 to 391, owner, 13 November 2026): each page lists the
parts it shows, each part is drawn by the page's script, every page has help, and every old anchor for a part that
moved goes to a page that holds that part."""
import importlib.util
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")


def load_shell():
    spec = importlib.util.spec_from_file_location("apply_shell", os.path.join(ROOT, "tools", "apply_shell.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


SHELL = load_shell()
SCRIPTS = "".join(read(WEB, "js", name) for name in ("settings.js", "radio-settings.js", "library-settings.js"))


def level2(group):
    section = next(s for s in SHELL.MENU if s[0] == "settings")
    return next(pages for label, _, pages in section[3] if label == group)


def parts_of(page):
    m = re.search(r'data-parts="([^"]+)"', read(WEB, page))
    return m.group(1).split() if m else []


class SettingsMenusTest(unittest.TestCase):
    WANT = {
        "General": ["Names and apps", "Appearance", "Pages and lists", "Discover rows", "Download hours", "Logs and feedback"],
        "Downloads": ["VPN", "Usenet", "Download hours"],
        "Radio": ["Sources", "Add a show from a link", "Your podcast library", "Station logos"],
        "Performance": ["Preset", "Pictures"],
        "Security": ["Who can open the dashboard", "Password", "API keys", "Sign out everywhere"],
    }

    BEFORE = {
        "General": ["gn-name", "gn-cat", "gn-card", "gn-up", "gn-dh", "gn-guide", "gn-logs", "gn-design", "gn-style", "gn-test", "gn-scroll"],
        "Downloads": ["dl-vpn", "dl-usenet", "dl-hours"],
        "Radio": ["radio-sources", "radio-link", "radio-library", "radio-logos"],
        "Performance": ["pf-now", "pf-preset", "pf-bg", "pf-pages", "pf-pictures", "pf-danger"],
        "Security": ["sc-who", "sc-pw", "sc-ses", "sc-keys", "sc-danger"],
    }

    def test_each_group_has_its_pages_on_the_level_2_menu(self):
        for group, labels in self.WANT.items():
            self.assertEqual([label for _, label, _ in level2(group)], labels, group)

    def test_each_page_lists_its_parts_and_the_script_draws_them(self):
        for group in self.WANT:
            seen = []
            for page, label, _ in level2(group):
                parts = parts_of(page)
                self.assertTrue(parts, f"{page} has no data-parts")
                self.assertIn(f"<h1>{label}</h1>", read(WEB, page))
                for part in parts:
                    if part.startswith("dr-"):  # Discover rows: a section per area in DISCOVER_AREAS (DASH-396)
                        self.assertIn(f'["{part[3:]}", ', SCRIPTS.split("const DISCOVER_AREAS = ", 1)[1].split("\n", 1)[0], part)
                        continue
                    self.assertTrue(re.search(rf'(section|dangerSection|downloadHoursSection)\(\s*"{re.escape(part)}"', SCRIPTS)
                                    or f'"{part}"' in SCRIPTS, f"{page}: no part {part} in the scripts")
                seen += parts
            self.assertEqual(len(seen), len(set(seen)), f"{group}: a part is on two pages")

    def test_every_page_has_help(self):
        for group in self.WANT:
            for page, _, _ in level2(group):
                self.assertIn(page, SHELL.HELP)
                path = SHELL.HELP[page][0].split("#")[0]
                self.assertTrue(os.path.isfile(os.path.join(ROOT, "docs", "help", path)), path)

    def test_moved_anchors_go_to_a_page_that_holds_the_part(self):
        block = SCRIPTS.split("const MOVED_PARTS = {", 1)[1].split("\n};", 1)[0]
        pages = set(re.findall(r'"(settings-[a-z-]+\.html)"', block))
        self.assertTrue(pages)
        for page in pages:
            self.assertTrue(os.path.isfile(os.path.join(WEB, page)), page)
            self.assertIn(page, SHELL.PAGES, f"{page} is not in the menu")
        # Every part the one page used to show is on one of the group's pages now.
        for group, before in self.BEFORE.items():
            now = [p for page, _, _ in level2(group) for p in parts_of(page)]
            self.assertEqual(sorted(set(before) - set(now)), [], f"{group}: parts on no page")

    def test_download_hours_is_one_shared_field(self):
        self.assertEqual(len(re.findall(r"^function downloadHoursSection\(", SCRIPTS, re.M)), 1)
        self.assertIn('downloadHoursSection("gn-dh")', SCRIPTS)
        self.assertIn('downloadHoursSection("dl-hours")', SCRIPTS)
        self.assertNotIn("Change download hours", SCRIPTS, "Downloads shows the field itself, not a link to General")
        self.assertEqual(SCRIPTS.count('"dh-on-l"'), 2, "one switch, defined once, labelled once")

    def test_appearance_replaces_style(self):
        labels = [label for _, label, _ in level2("General")]
        self.assertIn("Appearance", labels)
        self.assertNotIn("Style", labels)
        self.assertIn('"gn-access", "Accessibility"', SCRIPTS)


class DiscoverRowsPageTest(unittest.TestCase):
    """DASH-396 (owner, 13 November 2026: "might need a separate section for each in the settings"): Discover rows is
    its own level 2 page under General with one section per area, in the Discover menu's order; each Discover page's
    Change these rows opens its own area's section; old addresses go there."""

    AREAS = ["films", "tv", "music", "radio", "books", "audiobooks"]

    def test_one_section_per_area_in_the_discover_menu_order(self):
        self.assertEqual(parts_of("settings-general-discover.html"), [f"dr-{a}" for a in self.AREAS])
        order = [p[0][0].replace("discover-", "").replace(".html", "") for label, _, p in
                 next(s for s in SHELL.MENU if any(pg[0] == "discover-films.html" for _, _, pages in s[3] for pg in pages))[3]
                 if p[0][0].replace("discover-", "").replace(".html", "") in self.AREAS]
        self.assertEqual(order, self.AREAS)
        self.assertNotIn('id="discover-rows"', read(WEB, "settings-general-lists.html"))

    def test_each_discover_page_opens_its_own_section(self):
        for area in self.AREAS:
            self.assertIn(f'href="/settings-general-discover.html#dr-{area}">Change these rows', read(WEB, f"discover-{area}.html"))

    def test_old_addresses_go_to_the_page(self):
        block = SCRIPTS.split("const MOVED_PARTS = {", 1)[1].split("\n};", 1)[0]
        self.assertIn('"discover-rows-s": "settings-general-discover.html"', block)
        self.assertIn("#dr-${area}", SCRIPTS)


if __name__ == "__main__":
    unittest.main()
