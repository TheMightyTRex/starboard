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
        Plugin.seen.append((self.command, self.headers.get("X-Api-Key"), json.loads(self.rfile.read(n)) if n else None))
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
        self.assertEqual(out["add"], {"label": "Add an add-on", "hint": "", "placeholder": "https://…/manifest.json"})
        self.assertEqual((out["items"][0]["state"], out["items"][0]["actions"]), ("unknown", ["test", "remove"]))
        self.assertEqual(Plugin.seen[-1][:2], ("GET", "plugin-key"))
        out = self.call({"action": "remove", "id": "streams|https://a.example/manifest.json", "extra": "dropped"})
        self.assertEqual(out["said"], "Done")
        self.assertEqual(Plugin.seen[-1], ("POST", "plugin-key", {"action": "remove", "id": "streams|https://a.example/manifest.json", "value": ""}))

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
