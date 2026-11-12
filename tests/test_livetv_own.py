"""The owner's own Live TV lists and guides (DASH-359, owner 12 November 2026)."""
import io
import json
import xml.etree.ElementTree as ET  # parsing the test's own made-up guide  # nosec B405
import os
import tempfile
import unittest
from unittest import mock

from starboard import livetv, livetv_own, livetv_plugin

M3U = b'#EXTM3U\n#EXTINF:-1 tvg-id="news.uk" tvg-logo="https://x/n.png" group-title="News",Made-up News\nhttps://a.example/news.m3u8\n' \
      b'#EXTINF:-1 group-title="Films",Made-up Films\nhttps://a.example/films.m3u8\n#EXTINF:-1,No address\nnot-a-url\n'
JSON = json.dumps({"channels": {"sport1": {"name": "Made-up Sport", "url": "https://b.example/sport.m3u8", "group": "Sport"},
                                "bad": {"name": "No stream"}}}).encode()
XML = b'<?xml version="1.0"?>\n<tv><channel id="news.uk"><display-name>Made-up News</display-name></channel>' \
      b'<programme channel="news.uk" start="20261112180000 +0000" stop="20261112190000 +0000"><title>Evening</title></programme>' \
      b'<programme channel="other" start="20261112180000 +0000" stop="20261112190000 +0000"><title>Elsewhere</title></programme></tv>'
STREMIO = json.dumps({"id": "org.example", "resources": ["stream"], "catalogs": []}).encode()
PAGES = {"https://a.example/list.m3u": M3U, "https://b.example/list.json": JSON, "https://c.example/guide.xml": XML,
         "https://d.example/manifest.json": STREMIO, "https://e.example/page": b"<html><body>Hello</body></html>"}


def fetch(url, **k):
    if url not in PAGES:
        raise OSError("refused")
    return PAGES[url]


class OwnSourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = os.path.join(self.tmp.name, "iptv")
        self.data = os.path.join(self.tmp.name, "data")
        os.makedirs(self.d)
        os.makedirs(self.data)

    def test_each_kind_is_found_and_the_wrong_ones_are_refused_in_words(self):
        self.assertEqual(livetv_own.add(self.data, "https://a.example/list.m3u", fetch)["said"], "2 channels found")
        self.assertEqual(livetv_own.add(self.data, "https://b.example/list.json", fetch)["kind"], "list")
        self.assertEqual(livetv_own.add(self.data, "https://c.example/guide.xml", fetch)["kind"], "guide")
        for url, words in (("https://d.example/manifest.json", "Stremio add-on"), ("https://e.example/page", "not an M3U"),
                           ("ftp://x.example/a.m3u", "http"), ("https://a.example/list.m3u", "already added")):
            with self.assertRaisesRegex(ValueError, words):
                livetv_own.add(self.data, url, fetch)
        self.assertEqual(len(livetv_own.sources(self.data)), 3)

    def test_active_lists_are_built_into_one_playlist_with_their_guide(self):
        for url in ("https://a.example/list.m3u", "https://b.example/list.json", "https://c.example/guide.xml"):
            livetv_own.add(self.data, url, fetch)
        with mock.patch.object(livetv, "_guide_events", side_effect=lambda url: ET.iterparse(io.BytesIO(fetch(url)))):
            said = livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: "films" not in url)
        self.assertIn("Your lists: 2 channels", said)
        chans = livetv._parse(os.path.join(self.d, "own.m3u"))
        self.assertEqual([c["name"] for c in chans], ["Made-up News", "Made-up Sport"])  # Films does not play
        self.assertEqual(chans[0]["attrs"]["group-title"], "a.example · list.m3u · News")
        self.assertTrue(all(c["attrs"]["starboard-src"] for c in chans))
        with open(os.path.join(self.d, "guide-own.xml")) as f:
            guide = f.read()
        self.assertIn("Evening", guide)
        self.assertNotIn("Elsewhere", guide)  # only programmes for channels in the list
        notes = {s["url"]: (s["said"], s.get("state")) for s in livetv_own.sources(self.data)}
        self.assertEqual(notes["https://a.example/list.m3u"], ("1 of 2 channels play", "ok"))

    def test_the_screen_activates_deactivates_tests_and_removes_each_one(self):
        with mock.patch.object(livetv_plugin, "DATA", self.data), mock.patch.object(livetv, "folder", return_value=self.d), \
                mock.patch.object(livetv_plugin, "JELLYFIN", os.path.join(self.data, "none.json")), \
                mock.patch("starboard.livetv_jellyfin.refresh_guide"):
            out = livetv_plugin.sources_act({"action": "add", "value": "https://a.example/list.m3u"}, fetch)
            self.assertIn("Channel list added: 2 channels found", out["said"])
            sid = out["items"][0]["id"]
            self.assertEqual(out["items"][0]["actions"], ["toggle", "test", "remove"])
            livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: True)
            out = livetv_plugin.sources_act({"action": "toggle", "id": sid})
            self.assertEqual(out["said"], "a.example · list.m3u deactivated: its 2 channels leave Jellyfin now")
            self.assertFalse(out["items"][0]["on"])
            self.assertEqual(livetv._parse(os.path.join(self.d, "own.m3u")), [])
            self.assertIn("activated", livetv_plugin.sources_act({"action": "toggle", "id": sid})["said"])
            self.assertIn("answers: 2 channels", livetv_plugin.sources_act({"action": "test", "id": sid}, fetch)["said"])
            self.assertIn("removed", livetv_plugin.sources_act({"action": "remove", "id": sid})["said"])
            self.assertEqual(livetv_own.sources(self.data), [])
            with self.assertRaises(ValueError):
                livetv_plugin.sources_act({"action": "toggle", "id": "nope"})
        livetv_plugin._force["now"] = False

    def test_a_run_builds_them_when_they_change(self):
        livetv_own.save(self.data, [{"id": "a1", "url": "https://a.example/list.m3u", "kind": "list", "name": "Mine", "on": True}])
        built = []
        with mock.patch.object(livetv, "folder", return_value=self.d), mock.patch.dict(os.environ, {"STARBOARD_DATA": self.data}), \
                mock.patch.object(livetv, "build_guide", return_value="Guide"), \
                mock.patch.object(livetv_own, "build", side_effect=lambda d, data: built.append(d) or "Your lists: 1 channels"), \
                mock.patch.object(livetv, "_channels_json", side_effect=OSError("offline")), \
                mock.patch.object(livetv, "number_and_logos", return_value="Numbered"):
            open(os.path.join(self.d, "own.m3u"), "w").write("#EXTM3U\n")
            self.assertIn("Your lists", livetv.run("http://sb", False))
            livetv.run("http://sb", False)
            self.assertEqual(len(built), 1)  # unchanged: not built again
            livetv_own.save(self.data, [{"id": "a1", "url": "https://a.example/list.m3u", "kind": "list", "name": "Mine", "on": False}])
            livetv.run("http://sb", False)
            self.assertEqual(len(built), 2)


if __name__ == "__main__":
    unittest.main()
