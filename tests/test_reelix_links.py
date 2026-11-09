"""Starboard runs Reelix, so nobody needs Reelix's own pages (DASH-161). These are the only places Starboard links
to them; a new one fails this test until it is added here with its reason."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LINK = re.compile(r'Open in Reelix|open\("reelix"\)|reelix\["link"\]')
ALLOWED = {
    ("web/js/install.js", 'open("reelix")'): "the TMDB key, the one setting still made in Reelix until DASH-178",
    ("starboard/library.py", 'Open in Reelix'): "an item page's optional link to the same item in Reelix",
    ("starboard/library.py", 'reelix["link"]'): "the address that link uses",
}


class ReelixLinks(unittest.TestCase):
    def test_only_the_known_links_to_reelix_pages(self):
        found = set()
        for path in list((ROOT / "web" / "js").glob("*.js")) + list((ROOT / "starboard").glob("*.py")):
            for m in LINK.finditer(path.read_text(encoding="utf-8")):
                found.add((str(path.relative_to(ROOT)), m.group(0)))
        self.assertEqual(sorted(found - set(ALLOWED)), [], "A new link to Reelix's own pages: add a Starboard page instead, or list it here with why")


if __name__ == "__main__":
    unittest.main()
