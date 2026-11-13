"""A plug-in's own screen, drawn by Starboard from data (11 November 2026)."""
import http.server
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import plugin_custom, plugin_cards, plugins_admin


class Plugin(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def answer(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        Plugin.seen.append((self.command, self.headers.get("X-Api-Key"), (self.path, raw) if "/file?" in self.path else json.loads(raw) if raw else None))
        body = {"type": "list", "title": "Add-ons", "intro": "x" * 900, "evil": "<script>",
                "add": {"label": "Add an add-on", "placeholder": "https://…/manifest.json", "onclick": "alert(1)"},
                "items": [{"id": "streams|https://a.example/manifest.json", "title": "A", "state": "boom", "group": "Streams",
                           "actions": ["test", "remove", "rm -rf"]}], "said": "Done"}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_GET = do_POST = answer


class PluginCustomTest(unittest.TestCase):
    def setUp(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Plugin)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.port = srv.server_address[1]
        self.d = tempfile.mkdtemp()
        folder = plugins_admin.folder(self.d, "made-up")
        os.makedirs(folder)
        plugins_admin._write(f"{folder}/manifest.json", {"id": "made-up", "name": "Made-up", "containers": [{"name": "main", "port": self.port}],
                                                       "settings": [{"key": "sources", "label": "Add-ons", "type": "custom", "choices": "/api/sources"}]})
        plugins_admin._write(f"{folder}/key", "plugin-key")

    def call(self, body=None):
        with mock.patch.object(plugin_cards, "_host", return_value="127.0.0.1"):
            return plugin_custom.call(self.d, "made-up", "sources", body)

    def test_the_list_is_cleaned_and_the_plugin_called_with_its_own_key(self):
        out = self.call()
        self.assertNotIn("evil", out)
        self.assertEqual(len(out["intro"]), 400)
        self.assertEqual(out["add"], {"label": "Add an add-on", "hint": "", "placeholder": "https://…/manifest.json", "file": None})
        self.assertEqual((out["items"][0]["state"], out["items"][0]["actions"]), ("unknown", ["test", "remove"]))
        self.assertEqual(Plugin.seen[-1][:2], ("GET", "plugin-key"))
        out = self.call({"action": "remove", "id": "streams|https://a.example/manifest.json", "extra": "dropped"})
        self.assertEqual(out["said"], "Done")
        self.assertEqual(Plugin.seen[-1], ("POST", "plugin-key", {"action": "remove", "id": "streams|https://a.example/manifest.json", "value": ""}))

    def test_a_chosen_file_is_streamed_to_the_plugin(self):
        # DASH-359 (owner, 12 November 2026): a file picker beside Add a list or guide.
        import io
        data = b"#EXTM3U\n" + b"x" * 3_000_000
        with mock.patch.object(plugin_cards, "_host", return_value="127.0.0.1"):
            out = plugin_custom.upload(self.d, "made-up", "sources", "my list.m3u", len(data), io.BytesIO(data))
            self.assertEqual(out["said"], "Done")
            self.assertEqual(Plugin.seen[-1], ("POST", "plugin-key", ("/api/sources/file?name=my%20list.m3u", data)))
            with self.assertRaisesRegex(ValueError, "60 MB"):
                plugin_custom.upload(self.d, "made-up", "sources", "big.xml", 61 * 1024 * 1024, io.BytesIO(b""))
            with self.assertRaisesRegex(ValueError, "stopped before the end"):
                plugin_custom.upload(self.d, "made-up", "sources", "short.m3u", 100, io.BytesIO(b"only this"))
        self.assertEqual(plugin_custom._file({"label": "Or choose a file", "accept": ".m3u,.json,evil;js,.xml.gz,.gz", "hint": "Up to 60 MB"}),
                         {"label": "Or choose a file", "hint": "Up to 60 MB", "accept": ".m3u,.json,.gz"})
        self.assertIsNone(plugin_custom._file("nope"))

    def test_unknown_actions_and_screens_are_refused(self):
        with self.assertRaises(ValueError):
            self.call({"action": "format-disk"})
        with self.assertRaises(LookupError):
            plugin_custom.call(self.d, "made-up", "nothing")


if __name__ == "__main__":
    unittest.main()


class Choice(unittest.TestCase):
    """A small choice on a row, such as a catalogue's share (12 November 2026)."""
    def test_choice_cleaned(self):
        from starboard import plugin_custom
        out = plugin_custom.clean({"type": "list", "items": [
            {"id": "a", "title": "A", "choice": {"label": "Share", "value": "9", "options": [["1", "Less"], ["3", "Normal"], "bad"]}},
            {"id": "b", "title": "B", "choice": {"options": "nope"}}]})
        self.assertEqual(out["items"][0]["choice"], {"label": "Share", "value": "1", "options": [["1", "Less"], ["3", "Normal"]]})
        self.assertIsNone(out["items"][1]["choice"])
        self.assertIn("choose", plugin_custom.ACTIONS)

    def test_bulk_switches_cleaned(self):
        # DASH-359 (owner, 12 November 2026): switches for whole sets, such as Live TV's sources and sections.
        out = plugin_custom.clean({"type": "list", "items": [], "bulk": [
            {"id": "all", "label": "Every channel", "kind": "", "on": 3, "total": 5},
            {"id": "lists:pluto", "label": "Pluto TV", "kind": "Lists", "on": 99, "total": "4", "onclick": "x", "active": "yes", "hint": "h" * 300},
            {"id": "no-label"}, "bad", {"id": "x", "label": "X", "on": "many", "total": None}]})
        self.assertEqual(out["bulk"], [
            {"id": "all", "label": "Every channel", "kind": "", "on": 3, "total": 5, "active": None, "hint": ""},
            {"id": "lists:pluto", "label": "Pluto TV", "kind": "Lists", "on": 4, "total": 4, "active": None, "hint": "h" * 160},
            {"id": "x", "label": "X", "kind": "", "on": 0, "total": 0, "active": None, "hint": ""}])
        self.assertIs(plugin_custom.clean({"type": "list", "items": [], "bulk": [{"id": "a", "label": "A", "active": False}]})["bulk"][0]["active"], False)
        self.assertEqual(plugin_custom.clean({"type": "list", "items": [], "bulk": "nope"})["bulk"], [])
        self.assertIn("bulk", plugin_custom.ACTIONS)

    def test_sub_menus_cleaned(self):
        # Plug-in API 1.7 (DASH-361): sub menus, each after its parent, at most four deep; items and switches placed in them.
        out = plugin_custom.clean({"type": "list", "items": [
            {"id": "a", "title": "A", "menu": "news"}, {"id": "b", "title": "B", "menu": "nowhere"}, {"id": "c", "title": "C"}],
            "bulk": [{"id": "news", "label": "Every news channel", "menu": "news", "on": 1, "total": 1}, {"id": "all", "label": "All", "menu": "gone"}],
            "menus": [{"id": "uk", "title": "UK", "group": "Regions", "onclick": "x"}, {"id": "news", "title": "News", "parent": "uk", "active": False},
                      {"id": "orphan", "title": "Orphan", "parent": "later"}, {"id": "later", "title": "Later"}, {"id": "uk", "title": "Again"},
                      {"id": "no-title"}, "bad", {"id": "d3", "title": "3", "parent": "news"}, {"id": "d4", "title": "4", "parent": "d3"},
                      {"id": "d5", "title": "5", "parent": "d4"}]})
        self.assertEqual(out["menus"], [
            {"id": "uk", "title": "UK", "detail": "", "group": "Regions", "parent": "", "active": None},
            {"id": "news", "title": "News", "detail": "", "group": "", "parent": "uk", "active": False},
            {"id": "later", "title": "Later", "detail": "", "group": "", "parent": "", "active": None},
            {"id": "d3", "title": "3", "detail": "", "group": "", "parent": "news", "active": None},
            {"id": "d4", "title": "4", "detail": "", "group": "", "parent": "d3", "active": None}])
        self.assertEqual([it.get("menu") for it in out["items"]], ["news", None, None])
        self.assertEqual([b.get("menu") for b in out["bulk"]], ["news", None])
        # A screen without menus is the same as before: no menus, and nothing placed
        old = plugin_custom.clean({"type": "list", "items": [{"id": "a", "title": "A", "menu": "x"}], "bulk": [{"id": "s", "label": "S", "menu": "x"}]})
        self.assertNotIn("menus", old)
        self.assertNotIn("menu", old["items"][0])
        self.assertNotIn("menu", old["bulk"][0])
        # Up to 400 switches with menus, 60 without
        many = [{"id": f"s{i}", "label": "S"} for i in range(500)]
        self.assertEqual(len(plugin_custom.clean({"type": "list", "items": [], "bulk": many})["bulk"]), 60)
        self.assertEqual(len(plugin_custom.clean({"type": "list", "items": [], "bulk": many, "menus": [{"id": "m", "title": "M"}]})["bulk"]), 400)


class FoldsAndNotices(unittest.TestCase):
    """Plug-in API 1.8 (DASH-359): sections that fold with a table each, ticked items, a guide per item, notices."""

    def test_the_new_fields_are_cleaned(self):
        out = plugin_custom.clean({"type": "list", "layout": "folds",
                                   "columns": [{"key": "number", "label": "No.", "type": "number"}, {"key": "Bad Key", "label": "x"}, {"key": "name", "label": "Channel"}],
                                   "filters": [{"key": "name", "label": "Name"}, {"key": "missing", "label": "x"}],
                                   "notices": [{"id": "a", "title": "Adding", "tone": "evil", "progress": 140}, {"text": "no title"}],
                                   "bulk": [{"id": "sections:Sport", "label": "Sport", "fold": "Sport", "on": 1, "total": 2}],
                                   "items": [{"id": "1", "title": "601 Kestrel", "cells": {"number": "601", "name": "Kestrel", "evil": "x"},
                                              "attach": {"label": "Add guide", "accept": ".xml,.exe;rm"}}]})
        self.assertEqual([c["key"] for c in out["columns"]], ["number", "name"])
        self.assertEqual(out["filters"], [{"key": "name", "label": "Name"}])
        self.assertEqual(out["items"][0]["cells"], {"number": "601", "name": "Kestrel"})
        self.assertEqual(out["items"][0]["attach"]["accept"], ".xml")
        self.assertEqual(out["notices"], [{"id": "a", "tone": "info", "title": "Adding", "text": "", "progress": 100, "dismiss": False}])
        self.assertEqual(out["bulk"][0]["fold"], "Sport")
        plain = plugin_custom.clean({"type": "list", "columns": [{"key": "a", "label": "A"}], "items": [{"id": "1", "cells": {"a": "x"}}]})
        self.assertNotIn("layout", plain)  # columns only with the folds layout
        self.assertNotIn("cells", plain["items"][0])
        self.assertIn("bulk_ids", plugin_custom.ACTIONS)
