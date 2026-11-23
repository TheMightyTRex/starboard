"""Remove drop shadows (DASH-536, owner, 23 November 2026): the default follows the install (Reelix Lite starts with the
shadows removed, any other install keeps them), always asked, the person's own answer never overwritten when the route
changes, an install from before keeps its shadows with a note, and the design system's switch turns every shadow
token to none. Both set-ups ask the same question in the same words, with the default from one place."""
import json
import os
import re
import tempfile
import unittest

from starboard import config, shadows, stack
from starboard import terminal_setup as ts
from tests.test_terminal_setup import Answers
from tests.test_terminal_setup_rules import FakeApi, plain

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_stack(data_dir, edition, apps=("reelix", "jellyfin")):
    """A data/stack as Install apps writes it: the compose file names the apps and the Reelix image, .env the folders."""
    folder = stack.folder(data_dir)
    os.makedirs(folder, exist_ok=True)
    image = stack.reelix_image(edition)
    services = "".join(f"  {k}:\n    image: {image if k == 'reelix' else 'x/' + k}\n    container_name: {k}\n" for k in apps)
    with open(os.path.join(folder, "compose.yaml"), "w", encoding="utf-8") as f:
        f.write("services:\n" + services)
    with open(os.path.join(folder, ".env"), "w", encoding="utf-8") as f:
        f.write("CONFIG_DIR=/c\nDATA_DIR=/d\nPUID=1000\nPGID=1000\nTZ=Etc/UTC\n")


class DefaultsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.config = config.Config(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def off(self):
        return self.config.public()["shadows_off"]

    def test_the_rule_for_each_install(self):
        self.assertTrue(shadows.default_off("lite"))
        self.assertFalse(shadows.default_off("full"))
        self.assertFalse(shadows.default_off(None))  # no Reelix at all

    def test_a_new_install_is_unanswered_and_follows_the_install(self):
        self.assertIsNone(self.config.data["shadows_off"])
        self.assertFalse(self.config.data["shadows_note"])  # a new install has nothing to be told
        self.assertFalse(self.off())  # nothing installed yet: shadows stay
        write_stack(self.dir.name, "lite")
        self.assertTrue(self.off())  # Reelix Lite: no shadows
        self.assertTrue(self.config.public()["shadows_default_off"])
        write_stack(self.dir.name, "full")
        self.assertFalse(self.off())  # the full Reelix: shadows stay

    def test_no_reelix_keeps_the_shadows(self):
        write_stack(self.dir.name, "lite", apps=("jellyfin",))
        self.assertFalse(self.off())

    def test_an_unanswered_setting_follows_a_route_switch_but_an_answer_never_changes(self):
        write_stack(self.dir.name, "lite")
        self.assertTrue(self.off())
        write_stack(self.dir.name, "full")  # switched to the full Reelix in Settings
        self.assertFalse(self.off())  # unanswered, so it follows
        write_stack(self.dir.name, "lite")
        self.config.update_general({"shadows_off": False})  # the person keeps their shadows on Lite
        self.assertFalse(self.off())
        write_stack(self.dir.name, "full")
        write_stack(self.dir.name, "lite")
        self.assertFalse(self.off())  # switching either way leaves the choice
        self.config.update_general({"shadows_off": True})
        write_stack(self.dir.name, "full")
        self.assertTrue(self.off())  # nor does the full Reelix put the shadows back
        self.assertTrue(config.Config(self.dir.name).data["shadows_off"])  # kept on disk

    def test_an_install_from_before_keeps_its_shadows_and_is_told_once(self):
        path = os.path.join(self.dir.name, "config.json")
        with open(path) as f:
            data = json.load(f)
        data.update(schema=3)
        data.pop("shadows_off", None)
        data.pop("shadows_note", None)
        with open(path, "w") as f:
            json.dump(data, f)
        write_stack(self.dir.name, "lite")  # even a Lite install that exists today keeps its shadows
        moved = config.Config(self.dir.name)
        self.assertIs(moved.data["shadows_off"], False)
        self.assertFalse(moved.public()["shadows_off"])
        self.assertTrue(moved.public()["shadows_note"])
        moved.update_general({"shadows_note": False})  # the first visit marks it told
        self.assertFalse(config.Config(self.dir.name).public()["shadows_note"])
        self.assertFalse(config.Config(self.dir.name).public()["shadows_off"])

    def test_answering_clears_the_note_and_only_a_switch_is_accepted(self):
        self.config.update_general({"shadows_note": True})
        self.config.update_general({"shadows_off": True})
        self.assertFalse(self.config.data["shadows_note"])
        with self.assertRaises(config.ConfigError):
            self.config.update_general({"shadows_off": "yes"})
        self.assertEqual(config.general_right({"shadows_off": True}), "manage")

    def test_the_answer_is_kept_in_a_backup(self):
        from starboard import backup
        self.assertIn("shadows_off", backup.GENERAL_KEYS)


class TerminalStepTest(unittest.TestCase):
    """The terminal set-up asks the same question as the browser, in the words of web/setup-answers.json."""

    def run_step(self, typed, replies, state=None):
        api = FakeApi(replies)
        term, out = plain(typed)
        state = {} if state is None else state
        self.assertTrue(ts.step_shadows(api, term, state))
        return api, " ".join(out.getvalue().split()), state

    def test_it_comes_straight_after_how_much_it_does_in_both_names_and_steps(self):
        steps = [s["id"] for s in json.load(open(os.path.join(ROOT, "web", "setup-steps.json"), encoding="utf-8"))["steps"]]
        self.assertEqual(steps[steps.index("preset") + 1], "shadows")
        self.assertEqual(ts.question("shadows"), "Remove drop shadows?")
        ids = ts.job_steps({"start": "new", "storage": {"key": "disk"}, "choice": {"apps": ["jellyfin"]}})
        self.assertEqual(ids[ids.index("preset") + 1], "shadows")
        self.assertNotIn("shadows", ts.job_steps({"start": "restore", "place_answered": True}))  # the backup brought its answer

    def test_lite_shows_remove_first_as_recommended_and_the_note(self):
        replies = {("GET", "/api/shadows/default?reelix=lite"): {"off": True}, ("GET", "/api/config"): {"shadows_answered": False}}
        api, text, state = self.run_step([""], replies, {"choice": {"apps": ["reelix"], "reelix_edition": "lite"}})
        self.assertIn("Drop shadows cost a little processor on every scroll; turning them off helps small and older computers", text)
        self.assertLess(text.index("Yes, remove the drop shadows (recommended for Reelix Lite)"), text.index("No, keep the drop shadows"))
        self.assertEqual(api.calls[-1], ("PUT", "/api/config/general", {"shadows_off": True}))  # Enter takes the default
        self.assertIs(state["shadows_off"], True)

    def test_full_shows_keep_first_as_recommended(self):
        replies = {("GET", "/api/shadows/default?reelix=full"): {"off": False}, ("GET", "/api/config"): {"shadows_answered": False}}
        api, text, _ = self.run_step([""], replies, {"choice": {"apps": ["reelix"], "reelix_edition": "full"}})
        self.assertLess(text.index("No, keep the drop shadows (recommended)"), text.index("Yes, remove the drop shadows"))
        self.assertEqual(api.calls[-1][2], {"shadows_off": False})

    def test_no_reelix_asks_for_the_none_route_and_a_choice_is_always_possible(self):
        replies = {("GET", "/api/shadows/default?reelix=none"): {"off": False}, ("GET", "/api/config"): {"shadows_answered": False}}
        api, _, _ = self.run_step(["2"], replies, {"choice": {"apps": ["jellyfin"]}})
        self.assertEqual(api.calls[-1][2], {"shadows_off": True})  # the person chose Remove over the default

    def test_a_kept_install_asks_about_the_install_that_runs_now(self):
        replies = {("GET", "/api/shadows/default"): {"off": True}, ("GET", "/api/config"): {"shadows_answered": False}}
        api, _, _ = self.run_step([""], replies)
        self.assertEqual(api.calls[0], ("GET", "/api/shadows/default", None))

    def test_an_earlier_answer_is_the_default_shown_again(self):
        replies = {("GET", "/api/shadows/default"): {"off": True}, ("GET", "/api/config"): {"shadows_answered": True, "shadows_off": False}}
        api, _, _ = self.run_step([""], replies)
        self.assertEqual(api.calls[-1][2], {"shadows_off": False})  # on a Lite install, the person's own answer stays

    def test_a_refusal_asks_again(self):
        api = FakeApi({("GET", "/api/shadows/default"): {"off": False}, ("GET", "/api/config"): {"shadows_answered": False}},
                      refuse=[("PUT", "/api/config/general", "Not now")])
        term, out = plain(["", ""])
        self.assertTrue(ts.step_shadows(api, term, {}))
        self.assertIn("Starboard said: Not now", out.getvalue())
        self.assertEqual(out.getvalue().count(ts.question("shadows")), 2)

    def test_the_words_are_shared_with_the_browser_and_follow_the_content_rules(self):
        words = json.load(open(os.path.join(ROOT, "web", "setup-answers.json"), encoding="utf-8"))["shadows"]
        for text in words.values():
            self.assertNotIn("—", text)
            self.assertIsNone(re.search(r"\b(can't|don't|it's|won't|isn't)\b", text, re.I))
            self.assertNotRegex(text, r"\b(See|Look)\b")
        self.assertEqual(words["note"], shadows.NOTE)
        browser = open(os.path.join(ROOT, "web", "js", "settings-setup.js"), encoding="utf-8").read()
        self.assertIn("/api/shadows/default", browser)  # one source for the default
        self.assertIn('id === "shadows"', browser)
        self.assertGreaterEqual(browser.count("shadowsStep()"), 4)  # after every How much it does


class SwitchTest(unittest.TestCase):
    def read(self, *path):
        with open(os.path.join(ROOT, *path), encoding="utf-8") as f:
            return f.read()

    def test_one_rule_turns_every_shadow_token_to_none(self):
        css = self.read("web", "css", "tokens.css")
        m = re.search(r':root:root\[data-shadows="off"\],\s*\[data-shadows="off"\]\s*\{([^}]*)\}', css)
        self.assertTrue(m, "the design system's data-shadows switch is in tokens.css")
        tokens = set(re.findall(r"--(shadow-[a-z]+):", css))
        for name in tokens:
            self.assertRegex(m.group(1), rf"--{name}:\s*none")

    def test_no_style_sheet_draws_a_shadow_the_switch_cannot_reach(self):
        """Every box-shadow outside the design system's own files uses a token, none, an inset edge or the colour swatch."""
        for name in sorted(n for n in os.listdir(os.path.join(ROOT, "web", "css")) if n.endswith(".css")):
            if name in ("components.css", "tokens.css", "palettes.css"):  # the design system's own files, synced
                continue
            for line in self.read("web", "css", name).splitlines():
                m = re.search(r"(?<![-\w])box-shadow:\s*([^;}]+)", line)
                if m and not re.match(r"(var\(--shadow-(card|raised)\)|none|inset|var\(--p-shadow\))", m.group(1).strip()):
                    if ".collection-card__poster" in line and ':root[data-shadows="off"] .collection-card__poster' in self.read("web", "css", name):
                        continue  # its own small shadow, switched off by its own rule
                    self.fail(f"{name} draws its own shadow: {line.strip()}")
        for line in self.read("web", "css", "components.css").splitlines():
            m = re.search(r"(?<![-\w])box-shadow:\s*([^;}]+)", line)
            if m and not re.match(r"(var\(--shadow-(card|raised)\)|none|inset|0 0 0 (0|5px) color-mix)", m.group(1).strip()):
                self.fail(f"components.css draws its own shadow: {line.strip()}")

    def test_the_page_applies_it_before_first_paint_from_the_last_answer(self):
        js = self.read("web", "js", "common.js")
        self.assertIn('root.dataset.shadows = "off"', js)
        self.assertIn('localStorage.getItem(SHADOWS_KEY) === "off"', js)
        self.assertLess(js.index("let shadowsOff"), js.index("\napplyPrefs();"))  # read before the first applyPrefs
        self.assertIn("session.shadows_off", js)

    def test_the_session_tells_every_page(self):
        server = self.read("starboard", "server.py")
        self.assertIn('"shadows_off": shadows.effective_off(', server)

    def test_the_note_is_the_owners_words(self):
        self.assertEqual(shadows.NOTE, "Drop shadows cost a little processor on every scroll; turning them off helps small and older computers")
        self.assertIn("SHADOWS_NOTE", self.read("web", "js", "common.js"))


if __name__ == "__main__":
    unittest.main()
