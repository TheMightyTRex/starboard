"""DASH-622: the Catalogue page groups plug-ins by their `kind`, in a fixed order. AI assistants is in that order, and, like every
group, it shows only when a listed plug-in uses it (the headings are made from the entries, so an empty group never appears)."""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = (ROOT / "web" / "js" / "plugins.js").read_text(encoding="utf-8")


def order():
    m = re.search(r"const ORDER = \[([^\]]*)\];", JS)
    return re.findall(r'"([^"]+)"', m.group(1))


class CatalogueCategories(unittest.TestCase):
    def test_ai_assistants_is_in_the_order_before_apps_you_can_add(self):
        o = order()
        self.assertIn("AI assistants", o)
        self.assertLess(o.index("AI assistants"), o.index("Apps you can add"))
        self.assertEqual(len(o), len(set(o)))

    def test_every_name_is_sentence_case(self):
        for name in order():
            for word in name.split()[1:]:
                self.assertEqual(word, word.lower(), name)

    def test_groups_are_made_from_the_entries_so_an_empty_one_is_not_shown(self):
        self.assertIn("const kinds = new Map();", JS)
        self.assertIn("if (!kinds.has(e.kind)) kinds.set(e.kind, []);", JS)
        self.assertNotIn("for (const k of ORDER)", JS)

    def test_no_listed_plug_in_is_in_it_yet(self):
        rows = json.loads((ROOT / "plugins" / "catalogue.json").read_text(encoding="utf-8"))["plugins"]
        self.assertEqual([e["id"] for e in rows if e.get("kind") == "AI assistants"], [])
        fx = json.loads((ROOT / "tests" / "fixtures" / "stallboard-catalogue.json").read_text(encoding="utf-8"))["plugins"]
        self.assertEqual([e["id"] for e in fx if e.get("kind") == "AI assistants"], [])


if __name__ == "__main__":
    unittest.main()
