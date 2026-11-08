"""Sites to search in both set-ups (DASH-155): the same questions, in the same order and words, from one file
(web/reelix-sites.json); nothing is added unless chosen; a wrong address is asked again."""
import json
import os
import re
import unittest

from starboard import reelix_sites, terminal_setup as ts
from tests.test_terminal_setup_rules import plain

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
CHOICE = {"apps": ["reelix", "gluetun", "qbittorrent"]}


class TerminalStepTest(unittest.TestCase):
    def test_only_with_reelix(self):
        term, out = plain()
        self.assertFalse(ts.step_sites(None, term, {"choice": {"apps": ["jellyfin"]}}))
        self.assertFalse(ts.step_sites(None, term, {"choice": None}))
        self.assertEqual(out.getvalue(), "")

    def test_nothing_is_chosen_for_you(self):
        term, out = plain(["", ""])  # Enter on the list (none ticked), Enter on your own address (No)
        state = {"choice": dict(CHOICE)}
        self.assertTrue(ts.step_sites(None, term, state))
        self.assertEqual(state["choice"]["sites"], {"builtin": [], "own": []})
        text = " ".join(out.getvalue().split())
        self.assertIn(reelix_sites.WORDS["intro"], text)
        self.assertIn(reelix_sites.WORDS["vpn"], text)  # Gluetun is chosen
        self.assertIn("Use these sites only for files you have the right to download", text)

    def test_sites_and_your_own_address_with_a_wrong_address_asked_again(self):
        term, out = plain(["1,4", "3", "not an address", "https://usenet.example/api"], ["key-one", "key-two"])
        state = {"choice": {"apps": ["reelix"]}}
        self.assertTrue(ts.step_sites(None, term, state))
        self.assertEqual(state["choice"]["sites"]["builtin"], ["definition:internetarchive", "definition:yts"])
        self.assertEqual(state["choice"]["sites"]["own"], [{"kind": "newznab", "url": "https://usenet.example/api",
                                                           "api_key": "key-two", "name": "usenet.example"}])
        self.assertIn("Enter the site's address, starting http:// or https://", out.getvalue())
        self.assertNotIn("key-two", out.getvalue())  # typed hidden
        self.assertNotIn(reelix_sites.WORDS["vpn"], " ".join(out.getvalue().split()))  # no VPN chosen

    def test_going_back_keeps_the_answers(self):
        state = {"choice": {"apps": ["reelix"]}, "sites": {"builtin": ["definition:yts"], "own": []}}
        term, out = plain(["", ""])
        ts.step_sites(None, term, state)
        self.assertEqual(state["sites"]["builtin"], ["definition:yts"])  # Enter keeps the earlier ticks

    def test_a_refused_site_goes_back_to_this_step(self):
        self.assertIs(ts.preview_step("Enter the site's address, starting http:// or https://"), ts.step_sites)
        self.assertIs(ts.preview_step("definition:x is not one of Reelix's sites"), ts.step_sites)


class SameInBothTest(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(WEB, "js", "install.js"), encoding="utf-8") as f:
            self.js = f.read()
        with open(os.path.join(WEB, "setup-steps.json"), encoding="utf-8") as f:
            self.steps = [s["id"] for s in json.load(f)["steps"]]

    def test_one_list_and_one_set_of_words(self):
        self.assertIn('fetch("/reelix-sites.json"', self.js)
        for key in ("intro", "own_question", "own_choices", "address", "key", "vpn", "rights"):
            self.assertIn(f"w.{key}", self.js, f"The browser set-up should take {key} from web/reelix-sites.json")
            self.assertIn(key, reelix_sites.WORDS)
        for words in reelix_sites.WORDS.values():
            if isinstance(words, str):
                self.assertNotIn(words, self.js, "Words belong in web/reelix-sites.json, not in install.js")
        self.assertEqual(len(reelix_sites.WORDS["own_choices"]), 1 + len(reelix_sites.OWN_KINDS))

    def test_same_place_in_both(self):
        self.assertLess(self.steps.index("usenet"), self.steps.index("sites"))
        self.assertLess(self.steps.index("sites"), self.steps.index("check"))
        self.assertLess(ts.STEPS.index(ts.title("usenet")), ts.STEPS.index(ts.title("sites")))
        self.assertLess(ts.STEPS.index(ts.title("sites")), ts.STEPS.index(ts.title("check")))
        self.assertLess(ts.STEP_FUNCTIONS.index(ts.step_usenet), ts.STEP_FUNCTIONS.index(ts.step_sites))
        order = [m.group(1) for m in re.finditer(r'\{ id: "(\w+)", \.\.\.stepNamed', self.js)]
        self.assertLess(order.index("usenet"), order.index("sites"))
        self.assertLess(order.index("sites"), order.index("moving"))
        self.assertIn("sites", ts.job_steps({"choice": {"apps": ["reelix"]}}))
        self.assertNotIn("sites", ts.job_steps({"choice": {"apps": ["jellyfin"]}}))

    def test_none_is_ticked_by_default(self):
        self.assertIn("sites: { builtin: [], own: [] }", self.js)


if __name__ == "__main__":
    unittest.main()
