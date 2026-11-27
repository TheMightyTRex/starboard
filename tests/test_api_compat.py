"""The compatibility checks (DASH-603): the API only grows inside version 1, older plug-in manifests still work, and a
removal is caught unless it went through the deprecation steps. Starts nothing: it reads files and calls functions."""
import copy
import datetime as dt
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import api_compat  # noqa: E402

TODAY = dt.date(2026, 11, 26)


class Baseline(unittest.TestCase):
    def test_nothing_taken_away_since_the_baseline(self):
        bad, _ = api_compat.check(TODAY)
        self.assertEqual(bad, [], "The API lost or changed something without the deprecation steps")

    def test_frozen_older_manifests_still_pass(self):
        failed = [r for r in api_compat.run_frozen() if r[2] or r[3]]
        self.assertEqual(failed, [])

    def test_there_are_frozen_manifests_from_old_levels(self):
        apis = {r[1] for r in api_compat.run_frozen()}
        self.assertIn(">=1.1 <2.0", apis)
        self.assertGreaterEqual(len(apis), 8)


class Detects(unittest.TestCase):
    def setUp(self):
        self.old = json.load(open(api_compat.BASE, encoding="utf-8"))

    def breaks(self, mutate):
        new = copy.deepcopy(self.old)
        mutate(new)
        return [b[0] for b in api_compat.compare(self.old, new)[0]]

    def test_removed_route_permission_field_card_event_scope(self):
        route = next(iter(self.old["routes"]))
        perm = next(iter(self.old["permissions"]))
        self.assertIn("route:" + route, self.breaks(lambda n: n["routes"].pop(route)))
        self.assertIn("permission:" + perm, self.breaks(lambda n: n["permissions"].pop(perm)))
        self.assertIn("manifest_fields:update", self.breaks(lambda n: n["manifest_fields"].remove("update")))
        self.assertIn("card_types:sparkline", self.breaks(lambda n: n["card_types"].remove("sparkline")))
        self.assertIn("event:disk.changed", self.breaks(lambda n: n["events"].pop("disk.changed")))
        self.assertIn("key_scopes:logs", self.breaks(lambda n: n["key_scopes"].remove("logs")))

    def test_stricter_is_a_break_and_new_is_not(self):
        route = next(r for r, v in self.old["routes"].items() if v["answer"])
        field = self.old["routes"][route]["answer"][0]
        self.assertTrue(self.breaks(lambda n: n["routes"][route]["answer"].remove(field)))
        self.assertTrue(self.breaks(lambda n: n["routes"][route]["required_in"].append("newparam")))
        self.assertTrue(self.breaks(lambda n: n["manifest_required"].append("logo")))
        self.assertEqual(self.breaks(lambda n: n["card_types"].append("gauge")), [])
        self.assertEqual(self.breaks(lambda n: n["permissions"].update({"x:read": {"risk": "low", "scope": None}})), [])

    def test_deprecation_steps(self):
        entry = {"item": "card_types:sparkline", "remove_not_before": "2027-06-01"}
        ok, why = api_compat.allowed("card_types:sparkline", [entry], TODAY, 1)
        self.assertFalse(ok)
        self.assertIn("2.0", why)
        self.assertFalse(api_compat.allowed("card_types:sparkline", [entry], dt.date(2027, 1, 1), 2)[0])
        self.assertTrue(api_compat.allowed("card_types:sparkline", [entry], dt.date(2027, 6, 2), 2)[0])
        self.assertFalse(api_compat.allowed("card_types:sparkline", [], TODAY, 2)[0])
        self.assertTrue(api_compat.allowed("card_types:sparkline", [{"item": "card_types:sparkline", "security": True,
                                                                     "announced": "2026-11-26"}], TODAY, 1)[0])


class Rehearsal(unittest.TestCase):
    def test_names_the_plugins_that_would_stop(self):
        hit, total = api_compat.rehearse("permission:library:holding")
        self.assertEqual([h[0] for h in hit], ["library-cleanup"])
        self.assertGreater(total, 30)

    def test_a_field_nobody_uses_stops_nothing(self):
        self.assertEqual(api_compat.rehearse("permission:made-up")[0], [])


if __name__ == "__main__":
    unittest.main()
