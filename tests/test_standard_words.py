"""One plural and one clock (Starboard patterns audit, 26 November 2026).

Eight page scripts each had their own plural(), in three shapes, and three had their own timeNow(). The library has
SharedComponents.plural and SharedComponents.clock, common.js passes on to them, and no page script may define a top-level copy."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
COPY = re.compile(r"^(?:const|let|var|function) (plural|timeNow)\b", re.M)


class OnePlural(unittest.TestCase):
    def test_only_common_js_defines_them(self):
        found = {p.name: COPY.findall(p.read_text()) for p in (WEB / "js").glob("*.js") if p.name not in ("components.js", "snaglist.js")}
        found = {k: v for k, v in found.items() if v}
        self.assertEqual(found, {"common.js": ["plural", "timeNow"]}, f"a page script has its own copy: {found}")

    def test_the_library_has_them(self):
        text = (WEB / "js/components.js").read_text()
        self.assertIn("const plural = (n, one, many)", text)
        self.assertIn("Array.isArray(one)", text)
        self.assertIn("const clock =", text)
        self.assertIn("{ plural, clock, num }", text)


if __name__ == "__main__":
    unittest.main()
