"""Check your answers (28 November 2026, docs/WIZARD.md section 10), in the terminal and in the browser's script: one numbered line for
each answer, a number that changes that answer and comes back to the answers, an error that starts "There is a problem", the
browser's Back button going step to step, and "(optional)" on a step that can be skipped. Never an asterisk."""
import pathlib
import unittest

from starboard import terminal_setup as ts
from tests.test_terminal_setup_rules import FakeApi, plain

ROOT = pathlib.Path(__file__).resolve().parent.parent


def choice():
    return {"apps": ["jellyfin", "gluetun"], "data_dir": "/srv/media", "config_dir": "/srv/config", "vpn": {"provider": "mullvad", "type": "wireguard"}}


class TerminalCheckAnswers(unittest.TestCase):
    def setUp(self):
        self.api = FakeApi(replies={("POST", "/api/stack/preview"): {"moved": []}, ("POST", "/api/stack/write"): {"can_start": False, "command": "docker compose up -d"}})

    def state(self):
        return {"choice": choice(), "names": ["Jellyfin", "Gluetun"], "password": "x", "vpn": {"provider": "mullvad", "type": "wireguard"}}

    def test_each_answer_is_a_numbered_line_and_a_number_changes_it(self):
        term, out = plain(["2"])
        with self.assertRaises(ts.Change) as got:
            ts.step_check(self.api, term, self.state())
        self.assertEqual(got.exception.step_function, ts.step_storage, "2 is the media folder")
        text = out.getvalue()
        self.assertIn("Check your answers", text)
        for line in ("1. Install", "2. Media folder", "3. Settings folder", "4. VPN"):
            self.assertIn(line, text)
        self.assertIn("enter a number from 1 to 4 to change that answer", "\n".join(term._ask.prompts))

    def test_enter_writes_and_a_wrong_number_is_refused_with_there_is_a_problem(self):
        term, out = plain(["9", ""])
        state = self.state()
        ts.step_check(self.api, term, state)
        text = out.getvalue()
        self.assertIn("There is a problem. Enter a number from 1 to 4, or press Enter to write the files.", text)
        self.assertTrue(state.get("written"))

    def test_the_check_step_is_called_check_your_answers_in_both_set_ups(self):
        self.assertEqual(ts.title("check"), "Check your answers")
        self.assertEqual(ts.question("check"), "Check your answers")

    def test_a_refusal_says_there_is_a_problem(self):
        term, out = plain()
        term.refuse("That folder is not there.")
        self.assertIn("There is a problem. That folder is not there.", out.getvalue())


class BrowserWizardFrame(unittest.TestCase):
    def setUp(self):
        self.core = (ROOT / "web/js/settings-core.js").read_text(encoding="utf-8")
        self.install = (ROOT / "web/js/install.js").read_text(encoding="utf-8")
        self.setup = (ROOT / "web/js/settings-setup.js").read_text(encoding="utf-8")

    def test_back_in_the_browser_goes_step_to_step(self):
        self.assertIn("history.pushState({ wiz: key, i: index }", self.core)
        self.assertIn('window.addEventListener("popstate"', self.core)
        self.assertIn("history.back()", self.core)

    def test_a_step_that_can_be_skipped_says_optional_and_back_stays_in_the_foot(self):
        self.assertIn('" (optional)"', self.core)
        self.assertIn('"Skip this step"', self.core)
        self.assertRegex(self.core, r'cont,\s*index > 0 \? el\("button", \{ type: "button", class: "btn", onclick: goBack \}, "Back"\)')

    def test_change_on_check_your_answers_comes_back_to_the_answers(self):
        self.assertIn('wizardReturn.to = "review"', self.install)
        self.assertIn("wizardReturn.to", self.setup)
        self.assertIn('returning ? "Check your answers"', self.core)

    def test_a_wizard_has_no_asterisks_and_says_optional_on_a_field_that_may_be_left(self):
        self.assertIn('document.body.hasAttribute("data-wizard")', self.core)
        self.assertIn('" (optional)"', self.core)
        for page in ("install-apps", "setup-guide", "bring-in", "upgrade"):
            self.assertIn("data-wizard", (ROOT / f"web/{page}.html").read_text(encoding="utf-8"), page)
        cloud = (ROOT / "web/js/cloud-wizard.js").read_text(encoding="utf-8")
        self.assertNotIn('text: "*"', cloud)
        self.assertIn('" (optional)"', cloud)

    def test_the_error_summary_words_are_the_designs(self):
        components = (ROOT / "web/js/parts/error-summary.js").read_text(encoding="utf-8")
        self.assertIn("There is a problem", components)


if __name__ == "__main__":
    unittest.main()
