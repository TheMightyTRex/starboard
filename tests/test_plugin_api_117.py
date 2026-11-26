"""Plug-in API 1.17 (20 November 2026): the sparkline card, such as Advanced dashboard's response times, and the
permission alerts:send with POST /api/v1/plugin/alerts (Starboard API 1.8.0), so a plug-in raises and clears alerts
through Starboard's own, answered only to the plug-in's own key."""
import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, auth, plugin_cards, plugin_socket, plugin_tester, plugins, plugins_admin as pa
from starboard.server import make_server
from tests.test_plugin_api_socket import UnixConnection
from tests.test_plugins import ON_DEMAND

TREND = {"series": [{"title": "Router", "points": [12.5, 14, None, 15], "unit": "ms", "detail": "Average 13 ms"}],
         "note": "Hourly averages, the last 24 hours", "status": "ok", "updated": 1794694110}
CARD = {"id": "times", "title": "Response times", "type": "sparkline", "path": "/trend", "example": TREND}


class SparklineCard(unittest.TestCase):
    def test_a_good_answer_is_kept_with_its_words(self):
        out = plugin_cards.clean("sparkline", TREND, strict=True)
        s = out["series"][0]
        self.assertEqual((s["title"], s["points"], s["unit"], s["detail"]), ("Router", [12.5, 14, None, 15], "ms", "Average 13 ms"))
        self.assertEqual(s["summary"], "Now 15 ms, lowest 12.5 ms, highest 15 ms")
        self.assertEqual((out["note"], out["status"], out["updated"]), ("Hourly averages, the last 24 hours", "ok", 1794694110))

    def test_gaps_and_rounding(self):
        self.assertEqual(plugin_cards.spark_summary([None, 3.14159, None]), "Latest 3.14, lowest 3.14, highest 3.14")
        self.assertEqual(plugin_cards.spark_summary([1499.6, 0.254], "ms"), "Now 0.25 ms, lowest 0.25 ms, highest 1,500 ms")
        self.assertEqual(plugin_cards.spark_summary([40, 87.26], "%"), "Now 87.3%, lowest 40%, highest 87.3%")
        self.assertEqual(plugin_cards.spark_summary([None, None]), "No readings yet")
        out = plugin_cards.clean("sparkline", {"series": [{"title": "Disk", "points": [None]}]})
        self.assertEqual(out["series"][0]["summary"], "No readings yet")

    def test_too_many_points_or_none_are_refused(self):
        for points in ([1] * 97, [], "12,14", None):
            with self.assertRaises(ValueError) as e:
                plugin_cards.clean("sparkline", {"series": [{"title": "Router", "points": points}]})
            self.assertIn("1 to 96", str(e.exception))
        self.assertEqual(len(plugin_cards.clean("sparkline", {"series": [{"title": "A", "points": [1] * 96}]})["series"][0]["points"]), 96)

    def test_bad_values_are_refused_in_plain_words(self):
        for bad in (-1, "15", True, float("nan"), float("inf"), {"v": 1}):
            with self.assertRaises(ValueError) as e:
                plugin_cards.clean("sparkline", {"series": [{"title": "Router", "points": [1, bad]}]})
            self.assertEqual(str(e.exception), "Each point in a sparkline card must be a number of 0 or more, or null for a gap")
        for bad in ({}, {"series": "Router"}, {"series": [{"points": [1]}]}, {"series": ["Router"]}):
            with self.assertRaises(ValueError):
                plugin_cards.clean("sparkline", bad)

    def test_an_empty_list_of_series_is_allowed_with_its_note(self):
        # A plug-in not set up yet, or with no checks or backups to draw, answers an empty list; the dashboard says why (DASH-556 release check).
        self.assertEqual(plugin_cards.clean("sparkline", {"series": [], "note": "Add checks in the plug-in's settings"}),
                         {"series": [], "note": "Add checks in the plug-in's settings"})

    def test_long_text_is_cut_and_only_8_series_are_kept(self):
        one = {"title": "t" * 200, "points": [1], "unit": "requests", "detail": "d" * 300}
        out = plugin_cards.clean("sparkline", {"series": [one] * 12, "note": "n" * 300})
        self.assertEqual(len(out["series"]), 8)
        s = out["series"][0]
        self.assertEqual((len(s["title"]), s["unit"], len(s["detail"]), len(out["note"])), (80, "requests", 120, 120))
        self.assertEqual(plugin_cards.clean("sparkline", {"series": [{**one, "unit": "kilobytes"}]})["series"][0]["unit"], "kilobyte")

    def test_the_manifest_and_the_tester_take_a_sparkline(self):
        m = {**ON_DEMAND, "starboard_api": ">=1.17 <2.0", "cards": [CARD]}
        self.assertEqual(plugins.check(m), [])
        self.assertFalse([i for i in plugin_tester.run(m) if i["where"].startswith("cards[0]") and i["severity"] == "error"])
        bad = {**m, "cards": [{**CARD, "example": {"series": [{"title": "Router", "points": [1, -2]}]}}]}
        self.assertTrue(any(i["where"] == "cards[0].example" and "0 or more" in i["what"] for i in plugin_tester.run(bad)))
        wrong = plugins.check({**m, "cards": [{**CARD, "type": "chart"}]})
        self.assertIn("cards[0]: needs a type (stat, list, status, guide, sparkline) and a path on the plug-in", wrong)
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starboard", "plugin-manifest.schema.json")
        with open(here) as f:
            schema = json.load(f)
        self.assertIn("sparkline", schema["properties"]["cards"]["items"]["properties"]["type"]["enum"])
        self.assertIn("alerts:send", schema["properties"]["permissions"]["items"]["enum"])

    def test_alerts_send_is_a_low_risk_permission_with_no_key_scope(self):
        m = {**ON_DEMAND, "permissions": ["media:read", "network:vpn", "alerts:send"]}
        self.assertEqual(plugins.check(m), [])
        self.assertEqual(plugins.key_scopes(m), ["media"])
        self.assertEqual(plugins.PERMISSIONS["alerts:send"][1:], ("low", None))
        self.assertIn("Alerts: it can send alerts through Starboard, to where Starboard sends its own", plugins.install_warning(m)["change"])
        self.assertGreaterEqual(tuple(map(int, plugins.API_VERSION.split("."))), (1, 17, 0))


ALERTING = {**ON_DEMAND, "id": "advanced-dashboard", "name": "Advanced dashboard", "permissions": ["apps:read", "alerts:send"],
            "containers": [{**ON_DEMAND["containers"][0], "network": "default"}], "resources": {"main": {"memory": 40}}}
QUIET = {**ALERTING, "id": "quiet-one", "name": "Quiet one", "permissions": ["apps:read"]}
RAISE = {"key": "check-router", "state": "raised", "title": "Router is not answering", "message": "Ping: no answer for 3 checks in a row.",
         "level": "problem"}


class PluginAlerts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sbalert")  # short: a Unix socket's address holds at most 107 bytes
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.host_path = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}")
        cls.host_path.start()
        cls.keys = {}
        for m in (ALERTING, QUIET):
            pa.install(cls.tmp, m, "/srv/media")
            pa.set_state(cls.tmp, m["id"], "enabled")
            with open(os.path.join(pa.folder(cls.tmp, m["id"]), "key")) as f:
                cls.keys[m["id"]] = f.read().strip()
        cls.key = cls.keys["advanced-dashboard"]
        cls.manager, _ = api_v1.create_key(cls.tmp, "Home Assistant", "manage", [], 90)
        plugin_socket.start(cls.app)

    @classmethod
    def tearDownClass(cls):
        plugin_socket._reset_for_tests()
        cls.host_path.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.app.config.data["watch"]["enabled"] = True
        self.app.config.data["watch"]["channel"] = {"kind": "ntfy", "url": "https://ntfy.example.invalid/starboard"}
        self.app.watch.state["alerted"].clear()
        api_v1._raised.clear()
        pa.set_state(self.tmp, "advanced-dashboard", "enabled")
        sent = mock.patch("starboard.watch.send")
        self.sent = sent.start()
        self.addCleanup(sent.stop)
        published = mock.patch.object(api_v1, "publish")
        self.published = published.start()
        self.addCleanup(published.stop)

    def post(self, body, key=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("POST", "/api/v1/plugin/alerts", body=json.dumps(body).encode(),
                     headers={"Authorization": f"Bearer {key or self.key}", "Content-Type": "application/json"})
        r = conn.getresponse()
        out = json.loads(r.read() or b"null")
        conn.close()
        return r, out

    def test_raised_once_until_cleared_through_starboards_own_alerts(self):
        r, body = self.post(RAISE)
        self.assertEqual((r.status, body), (200, {"ok": True, "sent": True}))
        self.sent.assert_called_once()
        channel, title, message, level = self.sent.call_args[0]
        self.assertEqual((title, message, level), ("Router is not answering", "Advanced dashboard: Ping: no answer for 3 checks in a row.", "problem"))
        self.published.assert_called_with("alert.raised", {"title": "Router is not answering",
                                                           "message": "Advanced dashboard: Ping: no answer for 3 checks in a row.", "level": "problem"})
        self.assertIn("plugin:advanced-dashboard:check-router", self.app.watch.state["alerted"])
        r, body = self.post(RAISE)  # already raised: not sent again
        self.assertEqual((r.status, body["sent"]), (200, False))
        self.assertEqual(self.sent.call_count, 1)
        r, body = self.post({"key": "check-router", "state": "cleared", "title": "Router is answering again"})
        self.assertEqual((r.status, body["sent"]), (200, True))
        self.published.assert_called_with("alert.cleared", {"title": "Router is answering again", "message": "Advanced dashboard: check-router"})
        self.assertNotIn("plugin:advanced-dashboard:check-router", self.app.watch.state["alerted"])
        r, body = self.post({"key": "check-router", "state": "cleared"})  # nothing to clear
        self.assertEqual((r.status, body["sent"]), (200, False))
        with open(os.path.join(self.tmp, "logs", "audit.jsonl")) as f:
            self.assertTrue(any('"api_write"' in line and "/api/v1/plugin/alerts" in line for line in f))

    def test_through_the_plugins_own_socket(self):
        c = UnixConnection(plugin_socket.path_for(self.tmp, "advanced-dashboard"))
        try:
            c.request("POST", "/api/v1/plugin/alerts", body=json.dumps({**RAISE, "level": "warning"}).encode(),
                      headers={"Authorization": f"Bearer {self.key}"})
            r = c.getresponse()
            self.assertEqual((r.status, json.loads(r.read())), (200, {"ok": True, "sent": True}))
        finally:
            c.close()
        self.assertEqual(self.sent.call_args[0][3], "warning")

    def test_any_other_key_gets_404(self):
        for key in (self.manager, self.keys["quiet-one"]):  # a person's key, a plug-in without alerts:send
            r, body = self.post(RAISE, key)
            self.assertEqual((r.status, body["code"]), (404, "not_found"))
        pa.set_state(self.tmp, "advanced-dashboard", "disabled")  # not active
        r, body = self.post(RAISE)
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        self.sent.assert_not_called()

    def test_a_bad_body_gets_400_in_plain_words(self):
        for bad, words in (({"state": "raised", "title": "x"}, "Send key"), ({**RAISE, "key": "has spaces"}, "Send key"),
                           ({**RAISE, "key": "k" * 81}, "Send key"), ({**RAISE, "state": "on"}, "raised or cleared"),
                           ({**RAISE, "title": ""}, "Send title"), ({**RAISE, "title": "t" * 121}, "up to 120"),
                           ({**RAISE, "title": "two\nlines"}, "one line"), ({**RAISE, "message": "m" * 501}, "up to 500"),
                           ({**RAISE, "level": "urgent"}, "problem, warning or info")):
            r, body = self.post(bad)
            self.assertEqual((r.status, body["code"]), (400, "bad_request"), bad)
            self.assertIn(words, body["title"])
        self.sent.assert_not_called()

    def test_30_new_alerts_an_hour_then_429_with_retry_after(self):
        for i in range(30):
            self.assertEqual(self.post({**RAISE, "key": f"check-{i}"})[1]["sent"], True)
        self.assertEqual(self.post({**RAISE, "key": "check-0"})[1]["sent"], False)  # already raised: not counted, not refused
        r, body = self.post({**RAISE, "key": "check-30"})
        self.assertEqual((r.status, body["code"]), (429, "rate_limited"))
        self.assertGreater(int(r.getheader("Retry-After")), 3000)
        self.assertEqual(self.post({"key": "check-1", "state": "cleared"})[0].status, 200)  # clearing is never limited

    def test_alerts_off_sends_nothing(self):
        self.app.config.data["watch"]["enabled"] = False
        r, body = self.post(RAISE)
        self.assertEqual((r.status, body["sent"]), (200, False))
        self.sent.assert_not_called()
        self.published.assert_not_called()

    def test_removing_a_plugin_drops_its_alerts_quietly(self):
        w = self.app.watch
        w.state["alerted"].update({"plugin:advanced-dashboard:a": 1, "plugin:advanced-dashboard:b": 2, "plugin:advanced-dash:c": 3, "down:x": 4})
        self.assertEqual(w.forget("plugin:advanced-dashboard:"), 2)
        self.assertEqual(sorted(w.state["alerted"]), ["down:x", "plugin:advanced-dash:c"])
        self.sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
