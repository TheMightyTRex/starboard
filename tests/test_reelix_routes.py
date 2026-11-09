"""Every group of Reelix's API routes has a decision: where Starboard covers it, the task that will, or why it is not
needed (DASH-177). With REELIX_OPENAPI set to a running Reelix's /api/v1/openapi.json, a new group fails the test."""
import json
import os
import pathlib
import re
import unittest
import urllib.request

LIST = pathlib.Path(__file__).parent / "reelix" / "routes.json"
TASKS = re.compile(r"^DASH-\d+$")


def groups(paths):
    return {re.sub(r"^/api/v1", "", p).split("/")[1] for p in paths if p.count("/") >= 1}


class ReelixRoutes(unittest.TestCase):
    def setUp(self):
        self.routes = json.loads(LIST.read_text())["routes"]

    def test_every_group_has_one_kind_of_decision(self):
        for name, d in self.routes.items():
            kinds = [k for k in ("starboard", "task", "not_for_lite") if d.get(k)]
            self.assertTrue(kinds, f"{name} has no decision")
            if "task" in d:
                self.assertRegex(d["task"], TASKS, f"{name}: a task looks like DASH-123")

    @unittest.skipUnless(os.environ.get("REELIX_OPENAPI"), "set REELIX_OPENAPI to check against a running Reelix")
    def test_a_running_reelix_has_no_group_without_a_decision(self):
        with urllib.request.urlopen(os.environ["REELIX_OPENAPI"], timeout=10) as r:  # nosec B310: an address the tester gives
            live = groups(json.load(r)["paths"])
        self.assertEqual(sorted(live - set(self.routes)), [], "Reelix has new route groups: add a decision to tests/reelix/routes.json")


if __name__ == "__main__":
    unittest.main()
