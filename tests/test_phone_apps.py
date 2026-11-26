"""Phone apps for Calibre-Web (DASH-583, owner, 26 November 2026): KOReader and Calibre-Web-Companion for Android and Readest
for iOS, with links, where Calibre-Web is set up (Manage apps, the plug-in's page) and in the help."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*p):
    with open(os.path.join(ROOT, *p), encoding="utf-8") as f:
        return f.read()


class PhoneApps(unittest.TestCase):
    def test_the_decided_apps_and_only_those_are_offered_with_https_links(self):
        js = read("web", "js", "phone-apps.js")
        names = re.findall(r'name: "([^"]+)"', js)
        self.assertEqual(names, ["KOReader", "Calibre-Web-Companion", "Readest"])
        self.assertEqual(re.findall(r'os: "([^"]+)"', js), ["Android", "Android", "iPhone and iPad"])
        links = re.findall(r'"(https?://[^"]+)"', js)
        self.assertTrue(links and all(x.startswith("https://") for x in links))
        for banned in ("Quire", "Book Isle", "Librera"):
            self.assertNotIn(banned, js)

    def test_the_links_open_safely_in_a_new_tab_and_say_so(self):
        js = read("web", "js", "phone-apps.js")
        self.assertIn('rel: "noopener noreferrer"', js)
        self.assertIn("opens in a new tab", js)

    def test_the_pages_that_show_them_load_the_script_and_others_do_not(self):
        self.assertIn("/js/phone-apps.js", read("web", "settings.html"))
        self.assertIn("/js/phone-apps.js", read("web", "settings-plugin.html"))
        for name in os.listdir(os.path.join(ROOT, "web")):
            if name.endswith(".html") and name not in ("settings.html", "settings-plugin.html"):
                self.assertNotIn("phone-apps.js", read("web", name), name)

    def test_manage_apps_and_the_plug_in_page_use_it_for_calibre_web_only(self):
        self.assertRegex(read("web", "js", "settings-apps.js"), r"calibre/i\.test")
        self.assertIn('p.id === "calibre-web" ? section("pl-calibre-web-phone"', read("web", "js", "plugins.js"))

    def test_the_help_names_the_apps(self):
        text = read("docs", "help", "topics", "read-calibre-web-books-on-your-phone.md")
        for name in ("KOReader", "Calibre-Web-Companion", "Readest"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
