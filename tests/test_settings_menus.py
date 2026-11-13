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
        "General": ["Names and apps", "Appearance", "Pages and lists", "Download hours", "Logs and feedback"],
        "Downloads": ["VPN", "Usenet", "Download hours"],
    }

    BEFORE = {
        "General": ["gn-name", "gn-cat", "gn-card", "gn-up", "gn-dh", "gn-guide", "gn-logs", "gn-design", "gn-style", "gn-test", "gn-scroll"],
        "Downloads": ["dl-vpn", "dl-usenet", "dl-hours"],
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


if __name__ == "__main__":
    unittest.main()
