"""Rules both set-ups keep, checked over their own words: the recommended answer is at the top of every list, and
the text follows the content rules (no em dashes, no contractions). Also the terminal's key reading, which must
take keys that arrive together, or one key that arrives in two pieces. Taken from the Reelix wizard's tests,
written for Starboard. 6 November 2026."""
import pathlib
import re
import unittest

from starboard import config, start, terminal_setup

ROOT = pathlib.Path(__file__).resolve().parent.parent
WIZARDS = ["starboard/terminal_setup.py", "web/js/install.js", "web/js/settings.js", "run-first.sh", "install.sh"]
CONTRACTIONS = re.compile(r"\b(can't|won't|don't|doesn't|isn't|aren't|didn't|wasn't|haven't|hasn't|shouldn't|wouldn't|"
                          r"couldn't|you're|you'll|you've|we're|they're|it's|that's|there's|let's|I'm)\b", re.I)


def strings(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    return [a or b for a, b in re.findall(r'"((?:[^"\\\n]|\\.)*)"|`((?:[^`\\]|\\.)*)`', text)], text


class WizardRulesTest(unittest.TestCase):
    def test_words_follow_the_content_rules(self):
        for path in WIZARDS:
            for s in strings(path)[0]:
                self.assertNotIn("—", s, f"an em dash in {path}: {s}")
                self.assertIsNone(CONTRACTIONS.search(s), f"a contraction in {path}: {s}")

    def test_the_recommended_answer_is_first_in_every_written_list(self):
        # Lists written out in full: ["Yes (recommended)", "No: ..."]. Only literal strings between the brackets.
        lists = re.compile(r'\[\s*((?:"(?:[^"\\\n]|\\.)*"\s*(?:,\s*)?)+)\]')  # one way to match the spaces (CodeQL py/redos)
        for path in WIZARDS:
            for m in lists.finditer(strings(path)[1]):
                items = re.findall(r'"((?:[^"\\\n]|\\.)*)"', m.group(1))
                marked = [i for i, s in enumerate(items) if "(recommended" in s]
                if marked:
                    self.assertEqual(marked, [0], f"the recommended answer is not first in {path}: {items}")

    def test_the_recommended_start_storage_and_preset_come_first(self):
        found = start.recommended_first([{"key": "a", "recommended": False}, {"key": "b", "recommended": True}])
        self.assertEqual([c["key"] for c in found], ["b", "a"])
        small = ROOT / "tests" / "meminfo-small.tmp"
        try:
            small.write_text("MemTotal:         524288 kB\n")
            self.assertEqual(config.recommended_preset(str(small)), "small")
            small.write_text("MemTotal:        8000000 kB\n")
            self.assertEqual(config.recommended_preset(str(small)), "balanced")
        finally:
            small.unlink(missing_ok=True)
        self.assertEqual(config.recommended_preset("/nowhere"), "balanced")

    def test_both_set_ups_name_their_steps_from_one_table(self):
        import json
        table = json.loads((ROOT / "web" / "setup-steps.json").read_text(encoding="utf-8"))["steps"]
        ids = [s["id"] for s in table]
        self.assertEqual(len(ids), len(set(ids)), "a step id is there twice")
        for s in table:
            self.assertTrue(s["title"] and s["question"], s)
        for path in ("web/js/settings.js", "web/js/install.js"):
            for used in re.findall(r'stepNamed\(T, "([a-z-]+)"\)', (ROOT / path).read_text(encoding="utf-8")):
                self.assertIn(used, ids, f"{path} asks for a step the table does not have")
        self.assertEqual(terminal_setup.STEPS[:5], [terminal_setup.title(i) for i in ("password", "place", "keyboard", "start", "storage")])
        self.assertIn(terminal_setup.title("extras"), terminal_setup.STEPS)

    def test_keys_sent_together_are_taken_one_at_a_time(self):
        self.assertEqual(terminal_setup._keys(" \x1b[B \x1b[B \r"), [" ", "\x1b[B", " ", "\x1b[B", " ", "\r"])

    def test_an_arrow_key_in_two_pieces_is_one_key(self):
        reads = iter([b"\x1b", b"[B"])
        data = terminal_setup._read_keys(0, read=lambda _fd, _n: next(reads), ready=lambda: True)
        self.assertEqual(terminal_setup._keys(data), ["\x1b[B"])

    def test_escape_on_its_own_does_not_wait_for_ever(self):
        data = terminal_setup._read_keys(0, read=lambda _fd, _n: b"\x1b", ready=lambda: False)
        self.assertEqual(terminal_setup._keys(data), ["\x1b"])


if __name__ == "__main__":
    unittest.main()
