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
import gzip  # noqa: E402
BIG = gzip.compress(XML.replace(b"</tv>", b"<!-- " + b"x" * 5_000_000 + b" --></tv>"))  # like xmltv.live's gb.xml.gz
PAGES = {"https://f.example/gb.xml.gz": BIG, "https://a.example/list.m3u": M3U, "https://b.example/list.json": JSON, "https://c.example/guide.xml": XML,
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
        with mock.patch.object(livetv, "_gunzip", side_effect=AssertionError("a guide is never unpacked whole to look at it")):
            self.assertEqual(livetv_own.add(self.data, "https://f.example/gb.xml.gz", fetch)["kind"], "guide")
        for url, words in (("https://d.example/manifest.json", "Stremio add-on"), ("https://e.example/page", "not an M3U"),
                           ("ftp://x.example/a.m3u", "http"), ("https://a.example/list.m3u", "already added")):
            with self.assertRaisesRegex(ValueError, words):
                livetv_own.add(self.data, url, fetch)
        self.assertEqual(len(livetv_own.sources(self.data)), 4)

    def test_active_lists_are_built_into_one_playlist_with_their_guide(self):
        for url in ("https://a.example/list.m3u", "https://b.example/list.json", "https://c.example/guide.xml"):
            livetv_own.add(self.data, url, fetch)
        with mock.patch.object(livetv, "_guide_events", side_effect=lambda url: ET.iterparse(io.BytesIO(fetch(url)))):
            said = livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: "films" not in url, why=lambda url: "answer Not found")
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
        self.assertEqual(notes["https://a.example/list.m3u"], ("1 of 3 channels play", "ok"))  # "not-a-url" counts, as one Jellyfin cannot play
        result = {x["url"]: x.get("result") for x in livetv_own.sources(self.data)}["https://a.example/list.m3u"]
        self.assertEqual((result["added"], result["total"]), (1, 3))
        self.assertIn("1 address answers Not found", result["text"])

    def test_a_file_can_be_uploaded_instead_of_an_address(self):
        # DASH-359 (owner, 12 November 2026): "allow a file picker ... as well as the URL".
        item = livetv_own.add_file(self.data, "../My channels.m3u", io.BytesIO(M3U), len(M3U))
        self.assertEqual((item["kind"], item["name"], item["said"]), ("list", "My channels.m3u", "2 channels found"))
        stored = livetv_own.local_path(self.data, item["url"])
        self.assertTrue(stored.startswith(os.path.join(self.data, "own-files")) and os.path.exists(stored))
        guide = livetv_own.add_file(self.data, "gb.xml.gz", io.BytesIO(BIG), len(BIG))
        self.assertEqual(guide["kind"], "guide")
        with self.assertRaisesRegex(ValueError, "already added"):
            livetv_own.add_file(self.data, "again.m3u", io.BytesIO(M3U), len(M3U))
        with self.assertRaisesRegex(ValueError, "Stremio"):
            livetv_own.add_file(self.data, "manifest.json", io.BytesIO(STREMIO), len(STREMIO))
        with self.assertRaisesRegex(ValueError, "stopped before the end"):
            livetv_own.add_file(self.data, "short.m3u", io.BytesIO(b"#EXTM3U"), 500)
        self.assertEqual(sorted(os.listdir(os.path.join(self.data, "own-files"))), sorted([os.path.basename(stored), guide["url"][5:]]))
        self.assertIsNone(livetv_own.local_path(self.data, "file:../../etc/passwd"))
        # Built like an address: the uploaded list's channels and the uploaded guide's programmes
        livetv_own.build(self.d, self.data, plays=lambda url, ua: True)
        self.assertEqual(len(livetv._parse(os.path.join(self.d, "own.m3u"))), 2)
        with open(os.path.join(self.d, "guide-own.xml")) as f:
            self.assertIn("Evening", f.read())  # read from the stored .gz copy, a piece at a time
        livetv_own.forget(self.data, item)
        self.assertFalse(os.path.exists(stored))

    def test_a_guide_that_is_not_packed_is_read_as_it_is(self):
        path = os.path.join(self.data, "plain.xml")
        with open(path, "wb") as f:
            f.write(XML)
        self.assertEqual(sum(1 for _, el in livetv._guide_events(path) if el.tag == "programme"), 2)

    def test_the_screen_activates_deactivates_tests_and_removes_each_one(self):
        with mock.patch.object(livetv_plugin, "DATA", self.data), mock.patch.object(livetv, "folder", return_value=self.d), \
                mock.patch.object(livetv_plugin, "JELLYFIN", os.path.join(self.data, "none.json")), \
                mock.patch("starboard.livetv_jellyfin.refresh_guide"):
            with mock.patch.object(livetv_plugin, "_quick") as quick:
                out = livetv_plugin.sources_act({"action": "add", "value": "https://a.example/list.m3u"}, fetch)
                for _ in range(50):
                    if quick.called:
                        break
                    import time
                    time.sleep(0.01)
            self.assertIn("Channel list added: 2 channels found. Testing them now", out["said"])
            sid = out["items"][0]["id"]
            quick.assert_called_once_with(sid)  # tested at once, on its own
            self.assertEqual(out["items"][0]["actions"], ["toggle", "test", "attach", "remove"])
            self.assertEqual(out["items"][0]["attach"]["label"], "Add guide")
            livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: True)
            # A guide for this list (owner, 13 November 2026): its address, checked to be a guide
            with mock.patch.object(livetv_plugin, "_guides_now") as again:
                out = livetv_plugin.sources_act({"action": "attach", "id": sid, "value": "https://c.example/guide.xml"}, fetch)
                again.assert_called_once()
            self.assertEqual(out["said"], "Guide added to a.example · list.m3u: its programmes arrive in a few minutes")
            row = out["items"][0]
            self.assertEqual((row["attach"]["label"], row["attach"]["value"]), ("Change guide", "https://c.example/guide.xml"))
            self.assertIn("detach", row["actions"])
            with self.assertRaisesRegex(ValueError, "not an XMLTV guide"):
                livetv_plugin.sources_act({"action": "attach", "id": sid, "value": "https://b.example/list.json"}, fetch)
            with mock.patch.object(livetv_plugin, "_guides_now"):
                self.assertIn("Guide removed", livetv_plugin.sources_act({"action": "detach", "id": sid})["said"])
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

    def test_a_channel_already_in_live_tv_comes_in_inactive_once(self):
        # Owner, 13 November 2026: "Have them import as inactive if a duplicate so they can be turned on at any point".
        with open(os.path.join(self.d, "samsung.m3u"), "w") as f:
            f.write('#EXTM3U\n#EXTINF:-1 tvg-id="S1" tvg-chno="701",Made-up News HD\nhttps://s.example/news.m3u8\n')
        with open(os.path.join(self.d, livetv.ALL), "w") as f:  # hidden in Live TV: still a duplicate
            json.dump([{"id": "S1", "name": "Made-up News HD", "number": "701", "section": "News", "list": "samsung.m3u"}], f)
        livetv.save_hidden(self.data, {"S1"})
        livetv_own.add(self.data, "https://a.example/list.m3u", fetch)
        livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: True, why=lambda u: "x")
        self.assertEqual(livetv.hidden_ids(self.data), {"S1", "news.uk"})  # "Made-up News" is "Made-up News HD"
        result = livetv_own.sources(self.data)[0]["result"]
        self.assertEqual((result["added"], result["inactive"]), (1, 1))
        self.assertIn("1 is already in Live TV, so it came in inactive", result["text"])
        notice = livetv_own.notices(self.data)[0]
        self.assertEqual((notice["title"], notice["tone"], notice["dismiss"]), ("a.example · list.m3u: 1 of 3 channels added, 1 inactive", "success", True))
        livetv.save_hidden(self.data, {"S1"})  # activated by hand: it stays active at the next build
        livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: True, why=lambda u: "x")
        self.assertEqual(livetv.hidden_ids(self.data), {"S1"})
        livetv_own.dismiss(self.data, livetv_own.sources(self.data)[0]["id"])
        self.assertEqual(livetv_own.notices(self.data), [])

    def test_progress_shows_while_a_list_is_tested(self):
        livetv_own.add(self.data, "https://a.example/list.m3u", fetch)
        seen = []
        def plays(url, ua):
            seen.append([n["title"] for n in livetv_own.notices(self.data)])
            return True
        livetv_own.build(self.d, self.data, fetch, plays=plays)
        self.assertIn("Adding a.example · list.m3u: 0 of 2 channels tested", seen[0][0])
        self.assertEqual(livetv_own.notices(self.data)[0]["title"], "a.example · list.m3u: 2 of 3 channels added")
        self.assertIn("not web addresses", livetv_own.notices(self.data)[0]["text"])

    def test_kodi_links_are_said_by_name(self):
        kodi = b'#EXTM3U\n#EXTINF:0,Sky Sport 1\nplugin://plugin.video.sky.sport.now/?_=play\n#EXTINF:-1,Made-up\nhttps://k.example/a.m3u8\n'
        PAGES["https://k.example/kodi.m3u"] = kodi
        livetv_own.add(self.data, "https://k.example/kodi.m3u", fetch)
        livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: False, why=lambda u: "answer Not found")
        n = livetv_own.notices(self.data)[0]
        self.assertEqual((n["title"], n["tone"]), ("k.example · kodi.m3u: 0 of 2 channels added", "danger"))
        self.assertEqual(n["text"], "1 address answers Not found. 1 is a Kodi add-on link (plugin://), which Jellyfin cannot play.")

    def test_a_lists_guide_fills_its_channels_by_name(self):
        guide_xml = (b'<?xml version="1.0"?><tv><channel id="FilmsX.uk"><display-name>Made-up Films</display-name></channel>'
                     b'<programme channel="FilmsX.uk" start="20261113180000 +0000" stop="20261113200000 +0000"><title>A Film</title></programme></tv>')
        PAGES["https://g.example/films.xml"] = guide_xml
        item = livetv_own.add(self.data, "https://a.example/list.m3u", fetch)
        livetv_own.build(self.d, self.data, fetch, plays=lambda url, ua: True)
        livetv_own.set_guide(self.data, item["id"], "https://g.example/films.xml", fetch)
        with mock.patch.object(livetv, "_guide_events", side_effect=lambda url: ET.iterparse(io.BytesIO(fetch(url)), events=("end",))):
            livetv_own.guide(self.d, self.data)
        ids = [c["attrs"]["tvg-id"] for c in livetv._parse(os.path.join(self.d, "own.m3u"))]
        self.assertIn("FilmsX.uk", ids)  # its channel took the guide's id, matched by name
        with open(os.path.join(self.d, "guide-own.xml")) as f:
            self.assertIn("A Film", f.read())
        self.assertEqual(livetv_own.sources(self.data)[0]["guide_said"], "1 of 2 channels have programmes")

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


class OnTvNowTest(unittest.TestCase):
    """The On TV now card (DASH-359, owner 13 November 2026: option 5 on the dashboard)."""

    def test_the_next_few_hours_are_written_and_the_card_shows_now_and_next(self):
        import calendar
        import time as t
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as data:
            with open(os.path.join(d, "samsung.m3u"), "w") as f:
                f.write('#EXTM3U\n#EXTINF:-1 tvg-id="s1" tvg-chno="601" group-title="Sport",Kestrel Sport\nhttp://a\n'
                        '#EXTINF:-1 tvg-id="n1" tvg-chno="701" group-title="News",Lantern News\nhttp://b\n')
            with open(os.path.join(d, "guide-samsung.xml"), "w") as f:
                f.write('<?xml version="1.0"?><tv>'
                        '<programme channel="s1" start="20261113180000 +0000" stop="20261113190000 +0000"><title>Football Extra</title></programme>'
                        '<programme channel="s1" start="20261113190000 +0000" stop="20261113200000 +0000"><title>Darts</title></programme>'
                        '<programme channel="s1" start="20261120190000 +0000" stop="20261120200000 +0000"><title>Next week</title></programme>'
                        '<programme channel="n1" start="20261113180000 +0100" stop="20261113194500 +0100"><title>Evening News</title></programme>'
                        '<programme channel="gone" start="20261113180000 +0000" stop="20261113190000 +0000"><title>Not in Jellyfin</title></programme></tv>')
            now = calendar.timegm(t.strptime("20261113183000", "%Y%m%d%H%M%S"))
            self.assertEqual(livetv.write_now(d, data, now=now), 2)
            with open(os.path.join(data, livetv.NOW)) as f:
                got = json.load(f)
            self.assertEqual([p[2] for p in got["channels"]["s1"]["programmes"]], ["Football Extra", "Darts"])  # next week left out
            self.assertNotIn("gone", got["channels"])
            settings = os.path.join(data, "settings.json")
            json.dump({}, open(settings, "w"))
            with mock.patch.object(livetv_plugin, "DATA", data), mock.patch.object(livetv_plugin, "SETTINGS", settings):
                card = livetv_plugin.now_card(now=now)
                self.assertEqual([(i["number"], i["channel"], i["now"], i.get("next")) for i in card["items"]],
                                 [("601", "Kestrel Sport", "Football Extra", "Darts"), ("701", "Lantern News", "Evening News", None)])
                json.dump({"now_section": "Sport"}, open(settings, "w"))
                self.assertEqual([i["channel"] for i in livetv_plugin.now_card(now=now)["items"]], ["Kestrel Sport"])
                json.dump({"now_section": "Kids"}, open(settings, "w"))
                self.assertEqual(livetv_plugin.now_card(now=now)["note"], "Nothing on now in Kids.")
            from starboard import plugin_cards
            cleaned = plugin_cards.clean("guide", card)
            self.assertEqual(cleaned["items"][0]["start"], now - 1800)
            with self.assertRaises(ValueError):
                plugin_cards.clean("guide", {"items": [{"now": "no channel"}]})
