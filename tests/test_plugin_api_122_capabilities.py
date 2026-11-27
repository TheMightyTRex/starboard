"""Plug-in API 1.22 (DASH-603): starboard_tested, named capabilities, and what the tester says about the range a plug-in names."""
import copy
import http.client
import json
import tempfile
import threading
import unittest

from starboard import api_v1, plugin_capabilities, plugin_life, plugin_tester, plugins
from starboard.server import make_server
from tests.test_plugins import ON_DEMAND


def run(extra):
    return plugin_tester.run({**copy.deepcopy(ON_DEMAND), **extra})


def compat(issues):
    return [i for i in issues if i["area"] == "compatibility"]


class Manifest(unittest.TestCase):
    def test_both_new_fields_are_known_and_checked(self):
        self.assertEqual(plugins.check({**ON_DEMAND, "starboard_tested": "1.22", "capabilities": {"needs": ["first-sign-in"], "uses": ["sparkline-card"]}}), [])
        self.assertTrue(any("starboard_tested" in p for p in plugins.check({**ON_DEMAND, "starboard_tested": "latest"})))
        self.assertTrue(any("capabilities" in p for p in plugins.check({**ON_DEMAND, "capabilities": ["first-sign-in"]})))
        self.assertTrue(any("capabilities.needs" in p for p in plugins.check({**ON_DEMAND, "capabilities": {"needs": ["Bad Name"]}})))

    def test_a_plugin_that_needs_a_part_this_starboard_lacks_is_refused_in_words(self):
        bad = plugins.check({**ON_DEMAND, "capabilities": {"needs": ["teleport"]}})
        self.assertIn("It needs teleport, which this Starboard does not have", bad)
        self.assertEqual(plugins.check({**ON_DEMAND, "capabilities": {"uses": ["teleport"]}}), [])  # a soft use is fine

    def test_names_are_the_ones_in_the_api(self):
        self.assertIn("media-server-slot", plugin_capabilities.names())
        self.assertIn("first-sign-in", plugin_capabilities.names())
        self.assertEqual(plugin_capabilities.missing(["first-sign-in", "x-y"]), ["x-y"])


class Catalogue(unittest.TestCase):
    def test_a_version_that_needs_a_missing_part_is_not_offered_and_the_next_is(self):
        entry = {"versions": [
            {"version": "2.0.0", "manifest": "https://example.org/a.json", "starboard_api": ">=1.14 <2.0", "capabilities_needed": ["teleport"]},
            {"version": "1.9.0", "manifest": "https://example.org/b.json", "starboard_api": ">=1.14 <2.0"}]}
        best, hidden, needs = plugin_life.best_version(plugin_life.clean_versions(entry))
        self.assertEqual((best["version"], hidden), ("1.9.0", 1))
        self.assertEqual(needs, "needs teleport")


class Tester(unittest.TestCase):
    def test_no_top_end_and_too_high_a_top_end(self):
        self.assertTrue(any("no top end" in i["what"] for i in compat(run({"starboard_api": ">=1.14"}))))
        self.assertTrue(any("next major" in i["what"] for i in compat(run({"starboard_api": ">=1.14 <3.0"}))))
        self.assertFalse([i for i in compat(run({"starboard_api": ">=1.14 <2.0"})) if i["severity"] == "warning"])

    def test_a_lower_end_below_what_it_uses(self):
        got = compat(run({"starboard_api": ">=1.14 <2.0", "first_sign_in": {"user": "a", "secret": "s", "ready_file": "x/y"}}))
        self.assertTrue(any("first_sign_in came in at 1.20" in i["what"] for i in got), got)

    def test_a_soft_use_of_a_missing_part_is_only_information(self):
        got = compat(run({"capabilities": {"uses": ["teleport"]}}))
        self.assertTrue(any(i["severity"] == "info" and "teleport" in i["what"] for i in got))


class OnTheServer(unittest.TestCase):
    def test_the_root_lists_the_capabilities(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        server, app = make_server("127.0.0.1", 0, tmp.name)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        key, _ = api_v1.create_key(tmp.name, "T", "read", [], 30)
        c = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        c.request("GET", "/api/v1/", headers={"Authorization": f"Bearer {key}"})
        body = json.loads(c.getresponse().read())
        self.assertEqual(body["capabilities"], plugin_capabilities.names())


if __name__ == "__main__":
    unittest.main()
