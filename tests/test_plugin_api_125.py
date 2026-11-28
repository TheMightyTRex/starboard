"""Plug-in API 1.25 (28 November 2026): the shared wizard, a sentence, media cards, more rows, a preview and a desktop notice
on a plug-in's own page, drawn by Starboard from data. Additive: an older plug-in's answer is drawn as before."""
import http.server
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import plugin_cards, plugin_custom, plugins, plugins_admin

WIZARD = {"type": "wizard", "title": "What plays between programmes", "mode": "again", "mode_label": "Run again for Comedy", "finish": "Save the changes",
          "preview": {"title": "What a break plays like"}, "desktop_only": True, "evil": "<script>",
          "steps": [
              {"id": "style", "question": "Which style?", "hint": "Pick one.", "kind": "choice",
               "options": [{"id": "quiet", "label": "Quiet", "current": True, "preview": {"lines": ["Next: News", "b", "c", "d"], "corner": "Example TV",
                                                                                             "strip": [{"label": "Title clip", "seconds": 6, "kind": "title"}, {"label": "x", "seconds": 9999, "kind": "boom"}],
                                                                                             "caption": "Quiet.", "total": "About 10 seconds", "video": "no.mp4"}},
                           {"id": "classic", "label": "Classic TV", "recommended": True, "checked": True}, {"label": "no id"}]},
              {"id": "clips", "question": "Which clips?", "kind": "media", "optional": True,
               "options": [{"id": "c1", "label": "Station title", "media": {"kind": "audio", "length": "0:12", "preview": True, "thumb_path": True}},
                           {"id": "c2", "label": "Corner", "media": {"kind": "video", "thumb": {"src": "data:image/png;base64,AAAA", "alt": "A frame"}}}]},
              {"id": "name", "question": "Name?", "kind": "text", "required": True, "error": "Enter a name", "label": "Channel name", "value": "Comedy"},
              {"id": "Bad Id", "question": "dropped", "kind": "choice", "options": [{"id": "x", "label": "x"}]},
              {"id": "style", "question": "repeat", "kind": "choice", "options": [{"id": "x", "label": "x"}]},
              {"id": "empty", "question": "dropped: no options", "kind": "choice", "options": []}]}
SENTENCE = {"type": "sentence", "title": "A break", "parts": ["Between programmes, play ", {"id": "idents", "label": "Short title clips",
            "options": [["one", "a short title clip"], ["none", "no title clip"]], "value": "nope"}, ", then ", {"id": "bad id", "options": [["a", "A"]]}, "."]}


class Plugin(http.server.BaseHTTPRequestHandler):
    seen = []
    media = (b"RIFF....WAVE", "audio/wav")

    def log_message(self, *a):
        pass

    def do_GET(self):  # noqa: N802
        Plugin.seen.append(("GET", self.path, self.headers.get("X-Api-Key"), self.headers.get("X-Starboard-Can")))
        if "/media" in self.path:
            body, ctype = Plugin.media
        else:
            body, ctype = json.dumps(WIZARD).encode(), "application/json"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        Plugin.seen.append(("POST", self.path, body))
        raw = json.dumps({**SENTENCE, "said": "Saved"} if body.get("action") == "choose" else {**WIZARD, "said": "Saved the breaks"}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Api125(unittest.TestCase):
    def setUp(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Plugin)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.d = tempfile.mkdtemp()
        folder = plugins_admin.folder(self.d, "tv-test")
        os.makedirs(folder)
        plugins_admin._write(f"{folder}/manifest.json", {"id": "tv-test", "name": "TV", "containers": [{"name": "main", "port": srv.server_address[1]}],
                                                       "settings": [{"key": "setup", "label": "Set up", "type": "custom", "choices": "/setup"}]})
        plugins_admin._write(f"{folder}/key", "k")
        Plugin.seen.clear()
        Plugin.media = (b"RIFF....WAVE", "audio/wav")

    def call(self, body=None):
        with mock.patch.object(plugin_cards, "_host", return_value="127.0.0.1"):
            return plugin_custom.call(self.d, "tv-test", "setup", body)

    def test_the_version_and_what_this_starboard_draws(self):
        self.assertEqual(plugins.API_VERSION, "1.25.0")
        self.assertEqual(plugin_custom.CAN, "partial,picker,cards,wizard,sentence,media,more,desktop")

    def test_a_wizard_is_cleaned_to_what_starboard_draws(self):
        out = plugin_custom.clean(WIZARD)
        self.assertEqual((out["type"], out["mode"], out["mode_label"], out["finish"], out["desktop_only"]), ("wizard", "again", "Run again for Comedy", "Save the changes", True))
        self.assertNotIn("evil", out)
        self.assertEqual(out["preview"], {"title": "What a break plays like"})
        self.assertEqual([s["id"] for s in out["steps"]], ["style", "clips", "name"], "a bad id, a repeat and a step with no options are left out")
        quiet, classic = out["steps"][0]["options"]
        self.assertTrue(quiet["current"] and classic["recommended"] and classic["checked"])
        self.assertEqual(quiet["preview"]["lines"], ["Next: News", "b", "c"], "three lines at most")
        self.assertEqual(quiet["preview"]["strip"], [{"label": "Title clip", "seconds": 6, "kind": "title"}, {"label": "x", "seconds": 600, "kind": "other"}])
        self.assertNotIn("video", quiet["preview"], "a preview is a picture or styles, never video")
        clips = out["steps"][1]
        self.assertTrue(clips["optional"] and not clips["required"])
        self.assertEqual(clips["options"][0]["media"], {"kind": "audio", "length": "0:12", "preview": True, "thumb_path": True})
        self.assertEqual(clips["options"][1]["media"]["thumb"], {"src": "data:image/png;base64,AAAA", "alt": "A frame"})
        self.assertTrue(out["steps"][2]["required"] and out["steps"][2]["error"] == "Enter a name")

    def test_a_wizard_with_no_steps_is_refused(self):
        with self.assertRaises(ValueError):
            plugin_custom.clean({"type": "wizard", "steps": [{"id": "x", "kind": "choice", "options": []}]})

    def test_a_sentence_keeps_its_gaps_and_words(self):
        out = plugin_custom.clean(SENTENCE)
        self.assertEqual(out["type"], "sentence")
        self.assertEqual([p.get("text") or p["id"] for p in out["parts"]], ["Between programmes, play ", "idents", ", then ", "."])
        self.assertEqual(out["parts"][1]["value"], "one", "a value that is not an option falls back to the first")
        with self.assertRaises(ValueError):
            plugin_custom.clean({"type": "sentence", "parts": ["no gaps"]})

    def test_a_list_may_have_media_cards_more_rows_a_preview_and_the_desktop_notice(self):
        out = plugin_custom.clean({"type": "list", "layout": "media", "desktop_only": True, "more_switch": {"hint": "Fit and where breaks go"},
                                   "preview": {"caption": "Quiet.", "lines": ["x"]},
                                   "items": [{"id": "a", "title": "A", "media": {"kind": "audio", "preview": True}, "actions": ["toggle"]},
                                             {"id": "b", "title": "B", "more": True}]})
        self.assertEqual((out["layout"], out["desktop_only"]), ("media", True))
        self.assertEqual(out["more_switch"], {"label": "Show more settings", "hint": "Fit and where breaks go"})
        self.assertEqual(out["preview"]["caption"], "Quiet.")
        self.assertTrue(out["items"][1]["more"] and "media" in out["items"][0] and "more" not in out["items"][0])

    def test_an_older_list_is_drawn_as_before(self):
        out = plugin_custom.clean({"type": "list", "items": [{"id": "a", "title": "A"}]})
        for key in ("more_switch", "preview", "desktop_only"):
            self.assertNotIn(key, out)
        self.assertNotIn("media", out["items"][0])

    def test_a_wizard_is_asked_for_and_its_answers_go_back(self):
        got = self.call()
        self.assertEqual(got["type"], "wizard")
        self.assertEqual(Plugin.seen[-1][3], plugin_custom.CAN)
        out = self.call({"action": "wizard", "answers": {"style": "quiet", "clips": ["c1", "c2", 7], "Bad Id": "x", "name": "Comedy"}})
        self.assertEqual(Plugin.seen[-1][2]["answers"], {"style": "quiet", "clips": ["c1", "c2"], "name": "Comedy"})
        self.assertEqual(out["said"], "Saved the breaks")

    def test_a_sentence_change_is_a_choose_and_answers_the_sentence(self):
        out = self.call({"action": "choose", "id": "idents", "value": "none"})
        self.assertEqual((out["type"], out["said"]), ("sentence", "Saved"))

    def test_media_comes_through_starboard_and_only_as_a_picture_a_clip_or_a_sound(self):
        with mock.patch.object(plugin_cards, "_host", return_value="127.0.0.1"):
            ctype, raw = plugin_custom.media(self.d, "tv-test", "setup", {"step": "clips", "id": "c1", "kind": "thumb", "evil": "x"})
            self.assertEqual((ctype, raw), ("audio/wav", b"RIFF....WAVE"))
            self.assertEqual(Plugin.seen[-1][1], "/setup/media?step=clips&id=c1&kind=thumb")
            self.assertEqual(Plugin.seen[-1][2], "k")
            Plugin.media = (b"<script>alert(1)</script>", "text/html")
            with self.assertRaises(ValueError):
                plugin_custom.media(self.d, "tv-test", "setup", {"id": "c1"})
            Plugin.media = (b"x" * (plugin_custom.MAX_MEDIA + 1), "video/mp4")
            with self.assertRaises(ValueError):
                plugin_custom.media(self.d, "tv-test", "setup", {"id": "c1"})
        with self.assertRaises(LookupError):
            plugin_custom.media(self.d, "tv-test", "nope", {})


if __name__ == "__main__":
    unittest.main()
