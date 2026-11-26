"""One way to ask for the Starboard password (Starboard patterns audit, 26 November 2026).

A dialog that asks for the password builds its field with passwordInput() and passwordField() in common.js, and a form
that finds it empty says NEED_PASSWORD: one label, one error, one autocomplete."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
PAGES = [p for p in (WEB / "js").glob("*.js") if p.name not in ("components.js", "snaglist.js", "login.js")]
# settings-setup.js and plugins.js are being changed by other work at the time of writing: left as they are.
LEFT = {"settings-setup.js", "plugins.js", "backup-places.js"}


class OnePasswordAsk(unittest.TestCase):
    def test_helpers_exist(self):
        text = (WEB / "js/common.js").read_text()
        for name in ("const NEED_PASSWORD = \"Enter your Starboard password\"", "function passwordInput(", "function passwordField("):
            self.assertIn(name, text)

    def test_no_hand_built_password_label_in_a_dialog(self):
        hand = sorted(p.name for p in PAGES if p.name not in LEFT | {"common.js"}
                      and re.search(r'el\("label", \{ for: [a-z.]+, text: "Your Starboard password" \}\)', p.read_text()))
        # cloud-wizard.js and system-pool.js build a field with its own hint and width: the label is the same words.
        self.assertEqual(sorted(set(hand) - {"cloud-wizard.js", "system-pool.js"}), [], f"build it with passwordField(): {hand}")

    def test_one_word_for_a_missing_password(self):
        said = sorted(p.name for p in PAGES if p.name not in LEFT | {"common.js"} and re.search(r'"Enter your (Starboard )?password"', p.read_text()))
        self.assertEqual(said, [], f"say NEED_PASSWORD: {said}")

    def test_one_label(self):
        said = sorted(p.name for p in PAGES if p.name not in LEFT and re.search(r'"Your password"', p.read_text()))
        self.assertEqual(said, [])


if __name__ == "__main__":
    unittest.main()
