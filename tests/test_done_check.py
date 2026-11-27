"""The done gate (tools/done_check.py): what it reads from each step's output, how it tells new failures from the ones
already on main, and which pages a change touches (tools/changed-pages.py). No browser, no Docker."""
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import done_check as gate  # noqa: E402

spec = importlib.util.spec_from_file_location("changed_pages", ROOT / "tools" / "changed-pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)


class ParserTest(unittest.TestCase):
    def test_unit_failures_by_test(self):
        log = "FAIL: test_a (tests.test_x.Case.test_a)\nERROR: test_b (tests.test_y.Case.test_b)\nRan 12 tests in 1s\n"
        found, notes = gate.parse_unit(log, {})
        self.assertEqual(set(found), {"tests.test_x.Case.test_a", "tests.test_y.Case.test_b"})
        self.assertEqual(notes, ["12 tests ran"])

    def test_checks_count_each_tool_by_file(self):
        log = ("FAIL Ruff (Python)\n     B018 Found useless expression.\n       --> starboard/a.py:90:9\n"
               "PASS Biome (JavaScript and CSS)\nFAIL typos (spelling)\n     ./starboard/b.py:697:6: error: `xyz` should be `be`\n"
               "     ./starboard/b.py:711:56: error: `xyz` should be `be`\n2 failed: Ruff typos\n")
        found, _ = gate.parse_checks(log, {})
        self.assertEqual(found, {"Ruff (Python)|starboard/a.py": 1, "typos (spelling)|starboard/b.py": 2})

    def test_a_tool_that_fails_in_a_way_not_known_is_still_a_failure(self):
        found, _ = gate.parse_checks("FAIL Biome (JavaScript and CSS)\n     something odd\n", {})
        self.assertEqual(list(found.values()), [1])

    def test_help_problems_without_line_numbers_and_the_picture_count(self):
        log = ("topics/a.md: the link to ../images/x.png goes nowhere\n25 topics have fewer than 3 screenshots (x)\n"
               "docs/help/topics/a.md:22: the link to ../images/x.png goes nowhere\n")
        found, _ = gate.parse_help(log, {})
        self.assertEqual(found, {"topics/a.md: the link to ../images/x.png goes nowhere": 1, "topics have fewer than 3 screenshots": 25})

    def test_named_lines_for_journeys_and_tasks(self):
        found, notes = gate.parse_named_lines("PASS T1 ok\nFAIL T2 Escape returns focus: BODY\n\n== 40 passed, 1 failed\n", {})
        self.assertEqual(found, {"T2 Escape returns focus": 1})
        self.assertEqual(notes, ["40 passed"])

    def test_verbose_fails_only_for_long_sentences_and_paragraphs(self):
        log = "::warning file=a.md,line=3,title=Sentence over 25 words::30 words: x\n::warning file=a.md,line=4,title=Passive voice::1\n"
        found, notes = gate.parse_verbose(log, {})
        self.assertEqual(found, {"a.md": 1})
        self.assertEqual(len(notes), 1)

    def test_axe_findings_from_the_result_file(self):
        path = pathlib.Path(self.id() + ".json")
        path.write_text(json.dumps([{"page": "p.html", "area": "axe", "rule": "label", "count": 2}, {"page": "p.html", "area": "axe", "rule": "label"}]))
        try:
            found, _ = gate.parse_axe("", {"json": path})
        finally:
            path.unlink()
        self.assertEqual(found, {"p.html|axe|label": 3})

    def test_a_missing_result_file_is_a_failure(self):
        found, _ = gate.parse_axe("", {"json": "does-not-exist.json"})
        self.assertEqual(len(found), 1)


class JudgeTest(unittest.TestCase):
    base = {"steps": {"unit": {"known": {"a": 1, "b": 2}}}}

    def test_nothing_failing_passes(self):
        self.assertEqual(gate.judge("unit", 0, {}, self.base)[0], "pass")

    def test_only_known_failures_are_known_not_failed(self):
        result, new, old = gate.judge("unit", 1, {"a": 1, "b": 1}, self.base)
        self.assertEqual((result, new), ("known", {}))
        self.assertEqual(old, {"a": 1, "b": 1})

    def test_a_new_failure_beside_known_ones_fails(self):
        result, new, _ = gate.judge("unit", 1, {"a": 1, "c": 1}, self.base)
        self.assertEqual((result, new), ("fail", {"c": 1}))

    def test_more_of_a_known_failure_than_main_has_fails(self):
        self.assertEqual(gate.judge("unit", 1, {"a": 2}, self.base)[0], "fail")

    def test_a_crash_with_nothing_recognised_fails(self):
        self.assertEqual(gate.judge("unit", 2, {}, self.base)[0], "fail")

    def test_an_unlisted_step_has_no_known_failures(self):
        self.assertEqual(gate.judge("api", 1, {"x": 1}, self.base)[0], "fail")

    def test_owed_at_release_is_taken_out_and_counted(self):
        base = {"steps": {"help": {"owed_at_release": ["^topics have fewer"]}}}
        found = {"topics have fewer than 3 screenshots": 25, "a.md: broken": 1}
        self.assertEqual(gate.owed("help", found, base), {"topics have fewer than 3 screenshots": 25})
        self.assertEqual(found, {"a.md: broken": 1})

    def test_the_shipped_baseline_is_well_formed(self):
        data = json.loads((ROOT / "tools" / "done-check-baseline.json").read_text())
        for step, entry in data["steps"].items():
            self.assertTrue(all(isinstance(n, int) and n > 0 for n in entry["known"].values()), step)


class ChangedPagesTest(unittest.TestCase):
    def test_a_page_maps_to_itself(self):
        got, _, kinds, shared = pages.pages_for(["web/system.html"])
        self.assertEqual((got, shared, kinds["web"]), (["system.html"], False, True))

    def test_a_script_maps_to_the_pages_that_load_it(self):
        got, _, _, shared = pages.pages_for(["web/js/settings-people.js"])
        self.assertFalse(shared)
        self.assertIn("settings-people.html", got)
        self.assertLess(len(got), 5)

    def test_a_shared_style_file_is_every_page_or_the_sample(self):
        every, _, kinds, shared = pages.pages_for(["web/css/components.css"])
        self.assertTrue(shared and kinds["css"])
        self.assertGreater(len(every), 50)
        sample, _, _, _ = pages.pages_for(["web/css/components.css"], sample=True)
        self.assertEqual(sample, sorted(pages.SAMPLE))

    def test_server_only_and_docs_changes_touch_no_page(self):
        got, _, kinds, _ = pages.pages_for(["starboard/app.py", "docs/help/x.md", "CHANGELOG.md"])
        self.assertEqual(got, [])
        self.assertTrue(kinds["server"] and not kinds["web"])

    def test_a_change_to_the_checks_themselves_checks_every_page(self):
        _, _, kinds, shared = pages.pages_for(["tools/a11y/tasks.mjs"])
        self.assertTrue(shared and kinds["checks"])


if __name__ == "__main__":
    unittest.main()
