"""Single sign-on in the set-up (DASH-589): both set-ups ask "Will other people use your apps?" in the same place with the same
words, unticked, and a yes saves a wish only; the Plug-ins pages offer the install until it is added or someone chooses Not now.
The words explain the Tailscale name: chosen once, and changing it later breaks passkeys."""
import json
import os
import unittest

from starboard import config as config_mod
from starboard import plugins_admin as pa
from starboard import setup_answers
from starboard import terminal_setup as ts
from tests.test_setup_audio_description import Cfg
from tests.test_terminal_setup_rules import FakeApi, plain

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WORDS = setup_answers.WORDS["single_sign_on"]


def steps():
    with open(os.path.join(ROOT, "web", "setup-steps.json"), encoding="utf-8") as f:
        return [s["id"] for s in json.load(f)["steps"]]


class Order(unittest.TestCase):
    def test_the_question_comes_straight_after_the_jellyfin_extras_in_both_set_ups(self):
        order = steps()
        self.assertEqual(order[order.index("extras") + 1], "people")
        self.assertEqual(ts.question("people"), "Will other people use your apps?")
        for job in ({"start": "new", "choice": {"apps": ["jellyfin"]}}, {"start": "move", "move_into": False}):
            ids = ts.job_steps(job)
            self.assertEqual(ids[ids.index("people") - 1] in ("extras", "keys", "shadows", "check", "move"), True, ids)
            self.assertIn("people", ids)
        self.assertNotIn("people", ts.job_steps({"start": "restore", "place_answered": True}))  # a restore brought its answers
        js = open(os.path.join(ROOT, "web", "js", "settings-setup.js"), encoding="utf-8").read()
        self.assertIn('id: "people", ...stepNamed(T, "people")', js)
        self.assertIn('.single_sign_on;', js)
        self.assertLess(js.index('id: "jellyfin", ...stepNamed(T, "extras")'), js.index('id: "people", ...stepNamed(T, "people")'))
        self.assertLess(js.index('id: "people", ...stepNamed(T, "people")'), js.index('id: "hours", ...stepNamed(T, "hours")'))


class TerminalSetup(unittest.TestCase):
    def test_asked_with_no_as_the_default_in_the_same_words(self):
        api = FakeApi({("GET", "/api/config"): {"services": [], "extras": dict(config_mod.DEFAULTS["extras"])}})
        term, out = plain(["", ""])
        self.assertTrue(ts.step_people(api, term, {}))
        text = " ".join(out.getvalue().split())
        self.assertIn(" ".join(WORDS["hint"].split()[:8]), text)
        self.assertIn(WORDS["ask"], text)
        self.assertIs(api.calls[-1][2]["extras"]["single_sign_on"], False)
        self.assertNotIn(" ".join(WORDS["chosen"].split()[:5]), text)

    def test_yes_saves_the_wish_and_says_where_to_install_it(self):
        api = FakeApi({("GET", "/api/config"): {"services": [], "extras": dict(config_mod.DEFAULTS["extras"])}})
        term, out = plain(["y"])
        self.assertTrue(ts.step_people(api, term, {}))
        self.assertIs(api.calls[-1][2]["extras"]["single_sign_on"], True)
        self.assertIn(" ".join(WORDS["chosen"].split()[:5]), " ".join(out.getvalue().split()))


class Words(unittest.TestCase):
    def test_they_explain_the_recommendation_and_the_tailscale_name_in_plain_words(self):
        hint = WORDS["hint"]
        self.assertIn("Recommended when other people use your apps", hint)
        self.assertIn("Leave it unticked on a server only you use", hint)
        self.assertIn("Tailscale name", hint)
        self.assertIn("once", hint)
        self.assertIn("passkeys are tied to it for ever", hint)
        text = json.dumps(WORDS, ensure_ascii=False)
        self.assertNotIn("—", text)
        for bad in ("n't", "activate", "deactivate", "switch on", "switch off", "enable", "disable"):
            self.assertNotIn(bad, text.lower())

    def test_the_browser_reads_the_same_words(self):
        js = open(os.path.join(ROOT, "web", "js", "settings-setup.js"), encoding="utf-8").read()
        self.assertIn("text: w.label", js)
        self.assertIn("text: w.hint", js)
        self.assertIn("single_sign_on: tick.checked", js)


class Config(unittest.TestCase):
    def test_unticked_by_default_and_saved_as_true_or_false(self):
        self.assertIs(config_mod.DEFAULTS["extras"]["single_sign_on"], False)
        self.assertIs(config_mod.clean_extras({"single_sign_on": 1}, config_mod.DEFAULTS["extras"])["single_sign_on"], True)


class Offer(unittest.TestCase):
    def test_offered_until_added_or_not_now(self):
        cfg = Cfg({"single_sign_on": True})
        got = pa.wanted_from_setup(cfg, set())
        self.assertEqual([w["id"] for w in got], ["single-sign-on"])
        self.assertEqual(got[0]["title"], WORDS["notice_title"])
        self.assertEqual(pa.wanted_from_setup(cfg, {"single-sign-on"}), [])
        self.assertEqual(pa.drop_wanted(cfg, "single-sign-on"), WORDS["later_done"])
        self.assertIs(cfg.data["extras"]["single_sign_on"], False)


class Recommendations(unittest.TestCase):
    def test_the_people_page_and_security_recommend_it_in_the_same_way(self):
        people = open(os.path.join(ROOT, "web", "js", "settings-people.js"), encoding="utf-8").read()
        self.assertIn("Single sign-on is recommended when other people use your apps", people)
        self.assertIn("Leave it off on a server only you use", people)
        self.assertIn("settings-plugins-catalogue.html", people)
        signin = open(os.path.join(ROOT, "web", "settings-security-signin.html"), encoding="utf-8").read()
        self.assertIn("Single sign-on plug-in is recommended", signin)
        self.assertIn("Leave it off on a server only you use", signin)
        self.assertIn("Tailscale name once", signin)


if __name__ == "__main__":
    unittest.main()
