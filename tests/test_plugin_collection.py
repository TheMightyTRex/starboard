"""The plug-in collection folder: each zip matches its folder, each manifest passes the tester, and the help page
links both."""
import json
import os
import unittest
import zipfile

from starboard import plugin_tester

ROOT = os.path.join(os.path.dirname(__file__), "..", "plugins-collection")
HELP = os.path.join(os.path.dirname(__file__), "..", "docs", "help", "basics", "plugin-collection.md")


class CollectionTest(unittest.TestCase):
    def folders(self):
        return sorted(n for n in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, n)))

    def test_zip_matches_folder(self):
        for name in self.folders():
            with zipfile.ZipFile(os.path.join(ROOT, name + ".zip")) as z:
                for f in sorted(os.listdir(os.path.join(ROOT, name))):
                    with open(os.path.join(ROOT, name, f), "rb") as fh:
                        self.assertEqual(z.read(f"{name}/{f}"), fh.read(), f"{name}.zip is out of date: {f}")

    def test_manifests_pass(self):
        for name in self.folders():
            with open(os.path.join(ROOT, name, "starboard-plugin.json")) as fh:
                issues = plugin_tester.run(json.load(fh))
            self.assertEqual([i for i in issues if i["severity"] == "error"], [], name)

    def test_help_links_both(self):
        with open(HELP) as fh:
            text = fh.read()
        for name in self.folders():
            self.assertIn(f"plugins-collection/{name}/starboard-plugin.json", text)
            self.assertIn(f"plugins-collection/{name}.zip", text)


if __name__ == "__main__":
    unittest.main()
