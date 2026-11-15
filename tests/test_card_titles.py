"""A title for each card size (plug-in API 1.15, DASH-443, owner 15 November 2026: "different titles for each type of
card and cap the max number of characters for each type", "only to go on one line per card"): the manifest check,
the schema, the plug-in tester, the cards Starboard hands the dashboard, and the dashboard's own names."""
import copy
import json
import os
import pathlib
import re
import tempfile
import unittest
from unittest import mock

from starboard import plugin_cards, plugin_tester, plugins
from starboard import plugins_admin as pa
from tests.test_plugins import ON_DEMAND

ROOT = pathlib.Path(__file__).resolve().parent.parent
CARD = {"id": "saved", "title": "Space saved", "type": "stat", "path": "/card", "format": "bytes", "example": {"value": 1}}


def with_titles(titles, name=None):
    m = copy.deepcopy(ON_DEMAND)
    m["cards"] = [{**CARD, "titles": titles}]
    if name:
        m["name"] = name
    return m


def title_problems(m):
    return [p for p in plugins.check(m) if "title" in p]


class TitlesCheck(unittest.TestCase):
    def test_every_size_has_a_cap(self):
        self.assertEqual(tuple(plugins.CARD_TITLE_MAX), plugins.CARD_SIZES)
        caps = [plugins.CARD_TITLE_MAX[s] for s in plugins.CARD_SIZES]
        self.assertTrue(all(10 <= c <= 80 for c in caps), caps)
        # The smallest card has the least room; full width has at least what wide has (both are measured at
        # their narrowest screens: medium's chip and time sit under its title, half's beside it).
        self.assertEqual(min(caps), plugins.CARD_TITLE_MAX["small"])
        self.assertGreaterEqual(plugins.CARD_TITLE_MAX["full"], plugins.CARD_TITLE_MAX["wide"])

    def test_titles_at_their_cap_pass(self):
        titles = {s: "T" + "x" * (n - 1) for s, n in plugins.CARD_TITLE_MAX.items()}
        self.assertEqual({s: len(t) for s, t in titles.items()}, plugins.CARD_TITLE_MAX)
        self.assertEqual(title_problems(with_titles(titles)), [])
        self.assertEqual(title_problems(with_titles({"small": "Saved"})), [])  # the other sizes use the card's title

    def test_a_title_too_long_for_its_size_is_refused_with_its_room(self):
        n = plugins.CARD_TITLE_MAX["small"]
        out = title_problems(with_titles({"small": "x" * (n + 1)}))
        self.assertEqual(out, [f"cards[0]: the small title is {n + 1} characters, and a small card has room for {n} on one line"])

    def test_wrong_shapes_are_refused(self):
        for titles, words in (({"huge": "Saved"}, "unknown size huge"), ({"small": ""}, "small title must be words"),
                              ({"small": "   "}, "small title must be words"), ({"small": 3}, "small title must be words"),
                              ({"half": "Two\nlines"}, "line break"), ({}, "titles must be an object"),
                              ("Saved", "titles must be an object"), (["Saved"], "titles must be an object")):
            out = title_problems(with_titles(titles))
            self.assertTrue(out and words in out[0], (titles, out))
        self.assertNotIn("titles", " ".join(plugins.check(with_titles({"small": "Saved"}))))

    def test_the_schema_says_the_same(self):
        with tempfile.TemporaryDirectory() as d:
            plugins.write_schema(os.path.join(d, "s.json"))
            schema = json.loads(pathlib.Path(d, "s.json").read_text())
        titles = schema["properties"]["cards"]["items"]["properties"]["titles"]
        self.assertFalse(titles["additionalProperties"])
        self.assertEqual({k: v["maxLength"] for k, v in titles["properties"].items()}, plugins.CARD_TITLE_MAX)
        here = json.loads((ROOT / "starboard" / "plugin-manifest.schema.json").read_text())
        self.assertEqual(here["properties"]["cards"]["items"]["properties"]["titles"], titles)


class Tester(unittest.TestCase):
    def test_a_title_too_long_is_one_error_with_its_fix(self):
        n = plugins.CARD_TITLE_MAX["medium"]
        issues = plugin_tester.run(with_titles({"medium": "y" * (n + 4)}))
        mine = [i for i in issues if "medium title" in i["what"]]
        self.assertEqual(len(mine), 1, mine)
        self.assertEqual((mine[0]["severity"], mine[0]["where"]), ("error", "cards[0].titles"))
        self.assertIn(f"{n} characters or fewer", mine[0]["fix"])
        self.assertTrue(mine[0]["what"][0].isupper())

    def test_a_long_name_without_a_small_title_is_a_tip(self):
        small = plugins.CARD_TITLE_MAX["small"]
        long_name = ("Weekly library clean-up and holding area")[:40]
        self.assertGreater(len(long_name), small)
        m = copy.deepcopy(ON_DEMAND)
        m["name"], m["cards"] = long_name, [dict(CARD)]
        tips = [i for i in plugin_tester.run(m) if "small card" in i["what"]]
        self.assertEqual([t["severity"] for t in tips], ["info"])
        self.assertEqual([i for i in plugin_tester.run(with_titles({"small": "Clean-up"}, long_name)) if "small card" in i["what"]], [])


class Handed(unittest.TestCase):
    def test_the_dashboard_gets_the_titles_that_pass(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pa, "host_path", return_value="/srv/p"):
            m = copy.deepcopy(ON_DEMAND)
            m["cards"] = [{**CARD, "titles": {"small": "Saved", "wide": "Space saved by On demand"}},
                          {**CARD, "id": "other", "title": "Other"}]
            pa.install(d, m, "/srv/media")
            pa.set_state(d, "on-demand", "enabled")
            cards = {c["id"]: c for c in plugin_cards.available(d)}
        self.assertEqual(cards["plugin:on-demand:saved"]["titles"], {"small": "Saved", "wide": "Space saved by On demand"})
        self.assertEqual(cards["plugin:on-demand:other"]["titles"], {})


class Page(unittest.TestCase):
    js = (ROOT / "web" / "js" / "dashboard.js").read_text(encoding="utf-8")

    def test_the_band_and_the_tools_use_the_title_for_the_size(self):
        band = self.js.split("function pluginBand(c) {")[1].split("\n}\n")[0]
        self.assertIn("info.titles?.[c.size]", band)
        self.assertIn("visually-hidden", band)  # the plug-in's name, for screen readers
        tools = self.js.split("function cardShell(c, i, list) {")[1].split("\n}\n")[0]
        self.assertNotIn("CARD_TITLES[c.id]", tools)
        self.assertIn("nameFor(c)", tools)

    def test_shorter_built_in_names_are_for_real_cards_and_sizes(self):
        short = self.js.split("const CARD_SHORT = {")[1].split("};")[0]
        titles = set(re.findall(r"(\w+): \"", self.js.split("const CARD_TITLES = {")[1].split("};")[0]))
        for card, sizes in re.findall(r"(\w+): \{([^}]*)\}", short):
            self.assertIn(card, titles)
            self.assertTrue(set(re.findall(r"(\w+):", sizes)) <= set(plugins.CARD_SIZES), sizes)


if __name__ == "__main__":
    unittest.main()
