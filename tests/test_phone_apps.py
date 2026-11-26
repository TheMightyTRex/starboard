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
        self.assertEqual(names, ["KOReader", "Calibre-Web-Companion", "Readest", "KOReader", "Kover", "Sutra", "Komic"])
        self.assertEqual(re.findall(r'os: "([^"]+)"', js), ["Android", "Android", "iPhone and iPad", "Android", "Android", "iPhone and iPad", "iPhone and iPad"])
        links = re.findall(r'"(https?://[^"]+)"', js)
        self.assertTrue(links and all(x.startswith("https://") for x in links))
        for banned in ("Quire", "Book Isle", "Librera", "weblate", "play.google.com/store/apps/details?id=org.koreader"):
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
        self.assertIn('p.id === "calibre-web" || p.id === "kavita" ? section(', read("web", "js", "plugins.js"))
        self.assertRegex(read("web", "js", "settings-apps.js"), r"calibre\|kavita/i\.test")

    def test_kavita_says_what_each_needs_in_its_own_words(self):
        js = read("web", "js", "phone-apps.js")
        for word in ("Auth key", "3rd Party Clients", "iOS 17", "https", "kavita-dedicated"):
            self.assertIn(word, js)
        self.assertNotIn("API key", js.split("PHONE_APPS_KAVITA", 1)[1])
        self.assertIn("github.com/rodonisi/kover", js)
        self.assertIn("play.google.com/store/apps/details?id=com.rodonisi.kover", js)
        self.assertIn("Tested with Kavita on 26 November 2026", js)

    def test_the_kavita_help_names_the_apps(self):
        text = read("docs", "help", "topics", "read-kavita-books-on-your-phone.md")
        for name in ("KOReader", "Kover", "Sutra", "Komic", "Auth key", "iOS 17"):
            self.assertIn(name, text)

    def test_the_help_names_the_apps(self):
        text = read("docs", "help", "topics", "read-calibre-web-books-on-your-phone.md")
        for name in ("KOReader", "Calibre-Web-Companion", "Readest"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
