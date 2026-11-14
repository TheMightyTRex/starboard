"""Plug-in cards (DASH-149): the answer's shape is checked, text is cut and links are checked; the tester tests the
example answer; styles get a picture and a choice (DASH-284)."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugin_cards, plugin_tester, plugins_admin as pa
from tests.test_plugins import ON_DEMAND


class FakeOpener:
    def __init__(self, body):
        self.body, self.urls = body, []

    def open(self, req, timeout=None):
        self.urls.append(req.full_url)
        body = self.body

        class R:
            def read(self, n):
                return body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        return R()


class PluginCardsTest(unittest.TestCase):
    def test_answers_are_checked_and_cut(self):
        self.assertEqual(plugin_cards.clean("stat", {"value": 3, "label": "x" * 99})["label"], "x" * 40)
        items = plugin_cards.clean("list", {"items": [{"title": "<b>Dune</b>", "link": "javascript:alert(1)"}] * 20})["items"]
        self.assertEqual((len(items), items[0]["link"], items[0]["title"]), (10, "", "<b>Dune</b>"))  # drawn as text, never HTML
        for kind, bad in (("stat", {"value": "42"}), ("status", {"state": "fine"}), ("list", {"items": [{}]}), ("chart", {})):
            with self.assertRaises(ValueError):
                plugin_cards.clean(kind, bad)

    def test_the_tester_tests_each_example(self):
        m = {**ON_DEMAND, "cards": [{"id": "a", "title": "A", "type": "stat", "path": "/a", "example": {"value": "lots"}},
                                    {"id": "b", "title": "B", "type": "status", "path": "/b"}]}
        issues = plugin_tester.run(m)
        self.assertTrue(any(i["where"] == "cards[0].example" and i["severity"] == "error" for i in issues))
        self.assertTrue(any(i["where"] == "cards[1]" and "No example" in i["what"] for i in issues))

    def test_a_card_is_asked_once_a_minute_from_its_container(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pa, "host_path", return_value="/srv/p"):
            pa.install(d, ON_DEMAND, "/srv/media")
            pa.set_state(d, "on-demand", "enabled")
            self.assertEqual(plugin_cards.available(d)[0]["id"], "plugin:on-demand:titles")
            plugin_cards._cache.clear()
            op = FakeOpener(json.dumps({"value": 1200}).encode())
            out = plugin_cards.answer(d, "on-demand", "titles", op)
            plugin_cards.answer(d, "on-demand", "titles", op)
            self.assertEqual((out["data"]["value"], len(op.urls)), (1200, 1))
            self.assertTrue(op.urls[0].endswith(":7790/api/card"))  # On demand runs inside the VPN, reached through Gluetun
            plugin_cards._cache.clear()
            self.assertIn("No answer", plugin_cards.answer(d, "on-demand", "titles", FakeOpener(b"not json"))["problem"])

    def test_a_plug_in_is_found_by_its_address_when_names_do_not_resolve(self):
        from starboard import containers
        info = {"NetworkSettings": {"Networks": {"plugin-livetv_lan": {"IPAddress": "172.30.0.3"}, "plugin-livetv": {"IPAddress": "172.29.0.2"}}}}
        with mock.patch("socket.gethostbyname", side_effect=OSError), mock.patch.object(containers, "docker", return_value=info):
            self.assertEqual(plugin_cards._host("livetv", {"name": "main"}), "172.29.0.2")
        with mock.patch("socket.gethostbyname", return_value="172.29.0.2"):
            self.assertEqual(plugin_cards._host("livetv", {"name": "main"}), "plugin-livetv-main")

    def test_styles_listing_carries_what_the_pictures_need(self):
        path = os.path.join(os.path.dirname(__file__), "..", "tools", "screenshots", "example-plugin-styles.json")
        with open(path) as f:
            styles = json.load(f)
        with tempfile.TemporaryDirectory() as d:
            pa.install(d, styles, "/srv/media")
            looks = pa.listing(d)[0]["looks"]
            self.assertEqual(len(looks), 13)  # Styles 1.1.0: five more (11 November 2026)
            self.assertEqual(looks[2]["value"], "styles.bold")
            self.assertIn("text", looks[2]["dark"])
            self.assertEqual(plugin_tester.report(styles)["ok"], True)


    def test_a_style_may_set_more_and_every_extra_pair_is_checked(self):
        # Owner, 11 November 2026: styles may change most things, still accessible.
        from starboard import plugin_styles as ps
        path = os.path.join(os.path.dirname(__file__), "..", "tools", "screenshots", "example-plugin-styles.json")
        with open(path) as f:
            graphite = next(s for s in json.load(f)["styles"] if s["id"] == "graphite")
        self.assertEqual([p for p in ps.check_style(graphite) if p["severity"] == "error"], [])
        css = ps.css("styles", [graphite])
        for var in ("--color-rail:", "--status-danger-fg:", "--series-7:", "--weight-heading: 800", "--focus-w: 4px"):
            self.assertIn(var, css)
        bad = json.loads(json.dumps(graphite))
        bad["light"]["rail"] = "#111113"  # black side menu behind dark words
        self.assertIn("text on rail", " ".join(p["what"] for p in ps.check_style(bad)))
        bad = json.loads(json.dumps(graphite))
        bad["focus_width"] = 2
        self.assertIn("focus_width", " ".join(p["what"] for p in ps.check_style(bad)))


class CardRefreshTest(unittest.TestCase):
    """A card's own refresh time (plug-in API 1.14, owner 14 November 2026): 10 seconds at the quickest."""

    def test_the_answer_is_held_to_10_to_3600_seconds(self):
        self.assertEqual(plugin_cards.clean("stat", {"value": 1, "refresh_seconds": 2})["refresh_seconds"], 10)
        self.assertEqual(plugin_cards.clean("list", {"items": [], "refresh_seconds": 30})["refresh_seconds"], 30)
        self.assertEqual(plugin_cards.clean("status", {"state": "ok", "refresh_seconds": 99999})["refresh_seconds"], 3600)
        for nothing in (None, True, "30", [30]):
            self.assertNotIn("refresh_seconds", plugin_cards.clean("stat", {"value": 1, "refresh_seconds": nothing}))
        self.assertNotIn("refresh_seconds", plugin_cards.clean("stat", {"value": 1}))  # says nothing: as before

    def test_the_manifest_is_checked(self):
        from starboard import plugins
        card = {"id": "a", "title": "A", "type": "stat", "path": "/a"}
        for ok in (10, 30, 3600):
            m = {**ON_DEMAND, "cards": [{**card, "refresh_seconds": ok}]}
            self.assertFalse([p for p in plugins.check(m) if "refresh_seconds" in p], ok)
        for bad in (2, 9, 3601, "30", 30.5, True):
            m = {**ON_DEMAND, "cards": [{**card, "refresh_seconds": bad}]}
            self.assertTrue([p for p in plugins.check(m) if "refresh_seconds" in p], bad)
        self.assertTrue(any(i["where"].startswith("cards") or "refresh_seconds" in i["what"]
                            for i in plugin_tester.run({**ON_DEMAND, "cards": [{**card, "refresh_seconds": 5}]})))

    def test_answers_are_kept_for_the_cards_own_time_and_asked_together(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pa, "host_path", return_value="/srv/p"):
            m = {**ON_DEMAND, "cards": [{"id": "titles", "title": "Titles", "type": "stat", "path": "/api/card", "refresh_seconds": 30}]}
            pa.install(d, m, "/srv/media")
            pa.set_state(d, "on-demand", "enabled")
            plugin_cards._cache.clear()
            op = FakeOpener(json.dumps({"value": 5, "refresh_seconds": 2}).encode())
            out = plugin_cards.answer(d, "on-demand", "titles", op)
            self.assertEqual(out["refresh_seconds"], 10)  # asked for 2, held to 10
            self.assertNotIn("refresh_seconds", out["data"])
            with mock.patch("time.time", return_value=plugin_cards._cache[("on-demand", "titles")][0] + 9):
                plugin_cards.answer(d, "on-demand", "titles", op)
            self.assertEqual(len(op.urls), 1)  # kept for 10 seconds
            with mock.patch("time.time", return_value=plugin_cards._cache[("on-demand", "titles")][0] + 11):
                plugin_cards.answer(d, "on-demand", "titles", op)
            self.assertEqual(len(op.urls), 2)
            plugin_cards._cache.clear()
            op = FakeOpener(json.dumps({"value": 5}).encode())
            self.assertEqual(plugin_cards.answer(d, "on-demand", "titles", op)["refresh_seconds"], 30)  # the manifest's
            got = plugin_cards.answers(d, ["plugin:on-demand:titles", "plugin:on-demand:nothing", "rubbish"], op)
            self.assertEqual(sorted(got), ["plugin:on-demand:nothing", "plugin:on-demand:titles"])
            self.assertIn("problem", got["plugin:on-demand:nothing"])


if __name__ == "__main__":
    unittest.main()
