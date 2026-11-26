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
TITLES = {"Lists": "Lists and Discover rows", "Performance": "Performance and pictures", "Hours": "Download hours"}  # tab name: page heading (DASH-595)
SCRIPTS = "".join(read(WEB, "js", name) for name in (*sorted(n for n in os.listdir(os.path.join(WEB, "js")) if n.startswith("settings-")),  # settings.js, split by page
                                                     "radio-settings.js", "library-settings.js"))


def level2(group):
    section = next(s for s in SHELL.MENU if s[0] == "settings")
    return next(pages for label, _, pages in section[3] if label == group)


def parts_of(page):
    m = re.search(r'data-parts="([^"]+)"', read(WEB, page))
    return m.group(1).split() if m else []


class SettingsMenusTest(unittest.TestCase):
    WANT = {
        "General": ["General", "Appearance", "Lists", "Hours", "Alerts", "Performance", "Backup/Logs"],
        "Downloads": ["VPN", "Usenet", "Download hours"],
        "Radio": ["Sources", "Add a show from a link", "Your podcast library", "Station logos"],
        "Security": ["Who can open the dashboard", "Password", "Sign-in methods", "API keys", "Sign out everywhere"],
    }

    BEFORE = {
        "General": ["gn-name", "gn-cat", "gn-card", "gn-up", "gn-dh", "gn-guide", "gn-logs", "gn-design", "gn-style", "gn-test", "gn-scroll",
                    "pf-now", "pf-preset", "pf-bg", "pf-pages", "pf-pictures", "pf-danger"],  # Performance's parts moved in (DASH-584)
        "Downloads": ["dl-vpn", "dl-usenet", "dl-hours"],
        "Radio": ["radio-sources", "radio-link", "radio-library", "radio-logos"],
        "Security": ["sc-who", "sc-pw", "sc-ses", "sc-keys", "sc-danger"],
    }

    def test_each_group_has_its_pages_on_the_level_2_menu(self):
        for group, labels in self.WANT.items():
            self.assertEqual([label for _, label, _ in level2(group)], labels, group)

    def test_each_page_lists_its_parts_and_the_script_draws_them(self):
        for group in self.WANT:
            seen = []
            for page, label, _ in level2(group):
                if page in ("settings-general-backup.html", "settings-general-alerts.html"):  # backup and logs: one page of panels, with its own check below (DASH-595); alerts: one page, every part shown (DASH-584)
                    continue
                parts = parts_of(page)
                self.assertTrue(parts, f"{page} has no data-parts")
                self.assertIn(f"<h1>{TITLES.get(label, label)}</h1>", read(WEB, page))  # the tab's name is short; the page's heading is in full
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
        self.assertIn(" ".join(f"dr-{a}" for a in self.AREAS), read(WEB, "settings-general-lists.html"))
        order = [p[0][0].replace("discover-", "").replace(".html", "") for label, _, p in
                 next(s for s in SHELL.MENU if any(pg[0] == "discover-films.html" for _, _, pages in s[3] for pg in pages))[3]
                 if p[0][0].replace("discover-", "").replace(".html", "") in self.AREAS]
        self.assertEqual(order, self.AREAS)
        self.assertNotIn('id="discover-rows"', read(WEB, "settings-general-lists.html"))

    def test_each_discover_page_opens_its_own_section(self):
        for area in self.AREAS:
            self.assertIn(f'href="/settings-general-lists.html#dr-{area}">Change these rows', read(WEB, f"discover-{area}.html"))

    def test_old_addresses_go_to_the_page(self):
        block = SCRIPTS.split("const MOVED_PARTS = {", 1)[1].split("\n};", 1)[0]
        self.assertIn('"discover-rows-s": "settings-general-lists.html"', block)
        self.assertIn("#dr-${/^[a-z]{2,12}$/.test(area || \"\") ? area : \"films\"}-h", SCRIPTS)


if __name__ == "__main__":
    unittest.main()


class BackupLogsTabTest(unittest.TestCase):
    """DASH-595 (owner, 26 November 2026): Backup and restore and Logs and feedback are one tab, Settings, General,
    Backup/Logs. Nothing is lost, every old address answers 301, and the tab names stay short."""

    PAGE = "settings-general-backup.html"

    def test_one_page_holds_the_backups_and_the_logs(self):
        html = read(WEB, self.PAGE)
        for part in ("bk-when-h", "bk-full-h", "bk-copies-h", "bk-sb-h", "bk-server-h"):
            self.assertIn(f'id="{part}"', html)
        self.assertEqual(parts_of(self.PAGE), ["gn-logs", "gn-test", "gn-logdel"])
        for script in ("settings-core.js", "settings-general.js", "system-backup.js", "backup-places.js", "cloud-wizard.js", "reelix-system.js"):
            self.assertIn(f'/js/{script}"', html)
        self.assertEqual(html.count("<h1>"), 1)
        self.assertIn("<h1>Backup/Logs</h1>", html)

    def test_every_in_page_link_has_a_place_to_go(self):
        html = read(WEB, self.PAGE)
        links = re.findall(r'<a href="#([^"]+)"', html)
        self.assertGreaterEqual(len(links), 8)
        for target in links:
            if target in ("logs", "testing", "delete-logs"):  # drawn by settings-general.js
                self.assertRegex(SCRIPTS, rf'id: "{target}"')
            else:
                self.assertIn(f'id="{target}"', html)

    def test_the_old_pages_are_gone_and_their_addresses_move(self):
        server = load_server()
        for old in ("system-backup.html", "settings-general-logs.html"):
            self.assertFalse(os.path.exists(os.path.join(WEB, old)), old)
            self.assertEqual(server.MOVED_PAGES.get("/" + old), "/" + self.PAGE)
        # Every address that moved ends on a page that exists (no chain of moves, none to a missing page).
        for old, new in server.MOVED_PAGES.items():
            self.assertTrue(os.path.isfile(os.path.join(WEB, new.lstrip("/").split("?")[0].split("#")[0])), f"{old} moves to a missing page {new}")
            self.assertNotIn(new.split("?")[0].split("#")[0], server.MOVED_PAGES, f"{old} moves to {new}, which moved again")

    def test_pages_that_moved_in_earlier_work_answer_301_too(self):
        server = load_server()
        want = {"/settings-alerts.html": "/settings-general-alerts.html", "/settings-performance.html": "/settings-general-performance.html",
                "/settings-performance-pictures.html": "/settings-general-performance.html#pf-pictures-h", "/settings-media-server.html": "/settings-jellyfin.html",
                "/wanted.html": "/wanted-films.html", "/wanted-quality.html": "/wanted-films.html?list=cutoff", "/discover-trending.html": "/discover-films.html"}
        for old, new in want.items():
            self.assertEqual(server.MOVED_PAGES.get(old), new, old)
            self.assertFalse(os.path.exists(os.path.join(WEB, old.lstrip("/"))), old)

    def test_old_parts_of_general_go_to_the_new_page(self):
        block = SCRIPTS.split("const MOVED_PARTS = {", 1)[1].split("\n};", 1)[0]
        for part in ("gn-logs", "logs", "gn-test", "testing", "feedback-list", "gn-logdel", "delete-logs"):
            self.assertIn(f'"{part}"', block)
        self.assertNotIn("settings-general-logs.html", SCRIPTS)

    def test_logs_and_delete_all_logs_are_not_hidden_under_more_settings(self):
        advanced = SCRIPTS.split("const ADVANCED_SECTIONS = new Set([", 1)[1].split("]);", 1)[0]
        self.assertNotIn('"gn-logs"', advanced)
        self.assertNotIn('"gn-logdel"', advanced)

    def test_the_general_tab_names_are_short(self):
        labels = [label for _, label, _ in level2("General")]
        self.assertLessEqual(sum(len(label) for label in labels), 75, labels)
        self.assertTrue(all(len(label) <= 11 for label in labels), labels)


def load_server():
    import sys
    sys.path.insert(0, ROOT)
    from starboard import server
    return server
