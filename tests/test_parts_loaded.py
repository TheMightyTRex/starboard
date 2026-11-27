"""Parts of the design system load only where they are used (DASH-507). A page that loads a script which uses a part must
load that part's styles and script, in order after components.js; a page may not load a part nothing on it uses."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"
# page script -> the parts it needs on the page (what it draws or calls from the design system)
NEEDS = {"app-logs.js": ["log-view"], "library-item.js": ["tabs"], "system.js": ["charts"],
         "settings-apps.js": ["error-summary"], "dispatcharr-settings.js": ["error-summary"],
         "settings-security.js": ["error-summary", "secret-field"], "settings-people.js": ["secret-field"], "reelix-settings.js": ["tag-input"]}
NEEDS_PART = {"secret-field": ["error-summary"], "alerts": ["popover"], "command-palette": ["combobox"]}


def loaded(text):
    return re.findall(r'<script src="/js/parts/([a-z-]+)\.js">', text), re.findall(r'<link rel="stylesheet" href="/css/parts/([a-z-]+)\.css">', text)


class PartsLoaded(unittest.TestCase):
    def test_every_page_loads_what_its_scripts_use_and_nothing_else(self):
        for page in sorted(WEB.glob("*.html")):
            text = page.read_text()
            scripts = set(re.findall(r'<script src="/js/([a-z-]+\.js)"', text))
            want = {part for s in scripts for part in NEEDS.get(s, [])}
            for part in list(want):
                want.update(NEEDS_PART.get(part, []))
            js, css = loaded(text)
            self.assertEqual(set(js), want, f"{page.name}: parts loaded as scripts")
            self.assertEqual(set(css), want, f"{page.name}: parts loaded as styles")
            self.assertEqual(len(js), len(set(js)), f"{page.name}: a part loaded twice")
            if js:
                self.assertLess(text.index("/js/components.js"), text.index(f"/js/parts/{js[0]}.js"), page.name)
                self.assertLess(text.index(f"/js/parts/{js[-1]}.js"), text.index("/js/common.js"), page.name)
                for part in js:  # a part comes after the parts it needs
                    for need in NEEDS_PART.get(part, []):
                        self.assertLess(js.index(need), js.index(part), f"{page.name}: {need} before {part}")

    def test_part_files_exist_and_the_core_has_none_of_them(self):
        for part in ("log-view", "tabs", "combobox", "charts", "pagination", "error-summary", "secret-field", "schedule",
                     "tag-input", "popover", "alerts", "command-palette"):
            self.assertTrue((WEB / "js/parts" / f"{part}.js").exists() and (WEB / "css/parts" / f"{part}.css").exists(), part)
        core = (WEB / "js/components.js").read_text()
        self.assertNotIn("function logView", core)
        self.assertIn("addSetup", core)
        self.assertNotIn(".log-view", (WEB / "css/components.css").read_text())


if __name__ == "__main__":
    unittest.main()
