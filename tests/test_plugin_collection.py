"""The plug-in collection page: each plug-in links its install address and zip in the Starboard plug-ins repository
(github.com/TheMightyTRex/starboard-plugins), where tools/make_zips.py --check keeps each zip in step."""
import os
import re
import unittest

HELP = os.path.join(os.path.dirname(__file__), "..", "docs", "help", "basics", "plugin-collection.md")
REPO = "TheMightyTRex/starboard-plugins"


class CollectionTest(unittest.TestCase):
    def test_each_plugin_links_its_address_and_zip(self):
        with open(HELP) as fh:
            text = fh.read()
        addresses = re.findall(rf"https://raw\.githubusercontent\.com/{REPO}/main/([a-z0-9-]+)/starboard-plugin\.json", text)
        self.assertIn("styles", addresses)
        for name in addresses:
            self.assertIn(f"https://github.com/{REPO}/raw/main/zips/{name}.zip", text)

    def test_no_links_to_the_old_folder(self):
        with open(HELP) as fh:
            self.assertNotIn("plugins-collection", fh.read())


if __name__ == "__main__":
    unittest.main()
