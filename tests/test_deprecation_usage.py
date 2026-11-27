"""Who still uses a feature that is going, and the warnings a plug-in gets (DASH-603)."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, deprecations, plugin_tester
from starboard.server import make_server
from tests.test_plugins import ON_DEMAND

ROUTE = {"method": "GET", "path": "/api/v1/status", "deprecated": "2027-01-15", "sunset": "2028-01-15", "replacement": "Use /api/v1/apps",
         "link": "", "removed": False}
FIELD = {"manifest": "field:notices", "deprecated": "2027-01-15", "sunset": "2028-01-15", "replacement": "Use the install warning.", "link": "", "removed": False}


class Counter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        deprecations._used.clear()
        deprecations._saved_at = 0.0

    def test_counts_each_key_and_saves_at_most_once_an_hour(self):
        deprecations.note_use(self.tmp.name, "abc123", ROUTE, now=1_800_000_000)
        deprecations.note_use(self.tmp.name, "abc123", ROUTE, now=1_800_000_100)
        deprecations.note_use(self.tmp.name, "zzz999", ROUTE, now=1_800_000_200)
        saved = json.load(open(os.path.join(self.tmp.name, "api-retiring.json")))
        self.assertEqual(saved, {"GET /api/v1/status|abc123": [1, "2027-01-15"]})  # the first call saved; the rest wait
        deprecations.note_use(self.tmp.name, "abc123", ROUTE, now=1_800_000_000 + 3700)
        rows = {(r["key"]): r["calls"] for r in deprecations.routes_in_use(self.tmp.name)}
        self.assertEqual(rows, {"abc123": 3, "zzz999": 1})

    def test_nothing_is_written_when_nothing_is_going(self):
        self.assertEqual(os.listdir(self.tmp.name), [])


class Manifest(unittest.TestCase):
    def test_a_plugin_that_uses_a_going_field_gets_a_plain_sentence_with_the_day(self):
        with mock.patch.object(deprecations, "_items", [FIELD]):
            found = deprecations.for_manifest({**ON_DEMAND, "notices": ["x"]})
            self.assertEqual(deprecations.for_manifest(ON_DEMAND), [])
            sentence = deprecations.warning_sentence(found[0])
            tester = [i for i in plugin_tester.run({**ON_DEMAND, "notices": ["x"]}) if i["area"] == "compatibility"]
        self.assertEqual(sentence, "It uses the manifest field notices, which is going. It stops working after 15 January 2028. Use the install warning. Ask its maker for an update.")
        self.assertTrue(any(i["severity"] == "warning" and "15 January 2028" in i["what"] for i in tester))

    def test_a_removed_part_is_an_error_in_the_tester(self):
        with mock.patch.object(deprecations, "_items", [{**FIELD, "removed": True}]):
            tester = [i for i in plugin_tester.run({**ON_DEMAND, "notices": ["x"]}) if i["area"] == "compatibility"]
        self.assertTrue(any(i["severity"] == "error" for i in tester))


class OnTheServer(unittest.TestCase):
    def test_a_call_to_a_going_route_is_counted_and_the_report_lists_it(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        deprecations._used.clear()
        deprecations._saved_at = 0.0
        server, app = make_server("127.0.0.1", 0, tmp.name)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        key, item = api_v1.create_key(tmp.name, "Counter test", "read", [], 30)
        with mock.patch.object(deprecations, "_items", [ROUTE]):
            c = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            c.request("GET", "/api/v1/status", headers={"Authorization": f"Bearer {key}"})
            r = c.getresponse()
            r.read()
            self.assertIn("Deprecation", dict(r.getheaders()))
            rows = deprecations.routes_in_use(tmp.name)
        self.assertEqual([(x["route"], x["key"], x["calls"]) for x in rows], [("GET /api/v1/status", item["id"], 1)])


if __name__ == "__main__":
    unittest.main()
