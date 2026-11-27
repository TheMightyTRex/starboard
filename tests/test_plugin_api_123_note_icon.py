"""Plug-in API 1.23 (DASH-585, DASH-604): replaces_or_adds, the one line on what a plug-in replaces or adds to, and icon, the
name of one icon in Starboard's set for its tab in Settings, Plug-ins."""
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from starboard import plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Note(unittest.TestCase):
    def test_a_good_line_passes_and_is_shown(self):
        line = "Adds to Jellyfin: stops it converting files as they play."
        m = {**ON_DEMAND, "replaces_or_adds": line}
        self.assertEqual(plugins.check(m), [])
        self.assertEqual(pa.summary(m, [])["note"], line)

    def test_bad_lines_are_refused_in_words_and_never_shown(self):
        for bad in ("", "   ", "x" * 141, "two\nlines", "a <b> tag", "a `quote`", 5, ["x"]):
            m = {**ON_DEMAND, "replaces_or_adds": bad}
            self.assertTrue(any("replaces_or_adds" in p for p in plugins.check(m)), repr(bad))
            self.assertEqual(pa.summary(m, [])["note"], "")

    def test_a_plugin_without_one_works_as_before(self):
        self.assertEqual(plugins.check(ON_DEMAND), [])
        self.assertEqual(pa.summary(ON_DEMAND, [])["note"], "")

    def test_a_catalogue_entry_carries_its_line(self):
        e = pa._clean_entry({"id": "hello", "name": "Hello", "manifest": "https://example.org/hello.json",
                             "replaces_or_adds": "Adds to Starboard: a card."})
        self.assertEqual(e["note"], "Adds to Starboard: a card.")
        self.assertEqual(pa._clean_entry({"id": "hello", "name": "Hello", "manifest": "https://example.org/hello.json",
                                          "replaces_or_adds": "<b>x</b>"})["note"], "")

    def test_every_plug_in_that_comes_with_starboard_has_a_line(self):
        with open(os.path.join(ROOT, "plugins", "catalogue.json"), encoding="utf-8") as f:
            entries = json.load(f)["plugins"]
        self.assertTrue(entries)
        for e in entries:
            self.assertEqual(plugins.note_problems(e.get("replaces_or_adds")), [], e["id"])
        for pid in ("livetv", "jellyfin", "plex", "emby"):
            with open(os.path.join(ROOT, "plugins", pid, "starboard-plugin.json"), encoding="utf-8") as f:
                self.assertEqual(plugins.note_problems(json.load(f).get("replaces_or_adds")), [], pid)

    def test_the_schema_knows_both_fields(self):
        with open(os.path.join(ROOT, "starboard", "plugin-manifest.schema.json"), encoding="utf-8") as f:
            props = json.load(f)["properties"]
        self.assertEqual(props["replaces_or_adds"]["maxLength"], 140)
        self.assertIn("icon", props)


class Icon(unittest.TestCase):
    def test_the_icon_is_checked_against_the_set(self):
        self.assertEqual(plugins.check({**ON_DEMAND, "icon": "bell"}), [])
        self.assertTrue(any("icon must be" in p for p in plugins.check({**ON_DEMAND, "icon": "not-an-icon"})))
        self.assertTrue(any("icon must be" in p for p in plugins.check({**ON_DEMAND, "icon": 5})))
        self.assertEqual(plugins.clean_icon("puzzle"), "puzzle")
        self.assertEqual(plugins.clean_icon("../x"), "")

    def test_the_set_is_the_sprite_the_pages_use(self):
        with open(os.path.join(ROOT, "web", "icons", "sprite.svg"), encoding="utf-8") as f:
            names = set(re.findall(r'<symbol[^>]* id="i-([a-z0-9-]+)"', f.read()))
        self.assertEqual(set(plugins.icon_names()), names)
        # every icon the menu's own list uses is in the set, so the fallback never draws nothing
        with open(os.path.join(ROOT, "web", "js", "common.js"), encoding="utf-8") as f:
            text = f.read()
        block = text[text.index("const PLUGIN_TAB_ICONS"):text.index("function pluginTabs")]
        for name in re.findall(r'"[a-z0-9-]+": "([a-z0-9-]+)"', block):
            self.assertIn(name, names, name)
        self.assertIn("puzzle", names)

    def test_the_session_lists_each_added_plugin_with_a_checked_icon(self):
        with tempfile.TemporaryDirectory() as d:
            for pid, icon in (("alpha", "bell"), ("beta", "nope"), ("gamma", None)):
                os.makedirs(pa.folder(d, pid))
                m = {"id": pid, "name": pid.title(), "version": "1.0.0"}
                if icon:
                    m["icon"] = icon
                with open(os.path.join(pa.folder(d, pid), "manifest.json"), "w") as f:
                    json.dump(m, f)
            got = {p["id"]: p["icon"] for p in pa.added(d)}
        self.assertEqual(got, {"alpha": "bell", "beta": "", "gamma": ""})

    def test_the_menu_prefers_the_manifest_then_its_own_list_then_the_puzzle(self):
        with open(os.path.join(ROOT, "web", "js", "common.js"), encoding="utf-8") as f:
            self.assertIn('icon(p.icon || PLUGIN_TAB_ICONS[p.id] || "puzzle")', f.read())


if __name__ == "__main__":
    unittest.main()
