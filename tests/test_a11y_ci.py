"""The pull request accessibility check (tools/a11y_ci.py, .github/workflows/a11y.yml)."""
import contextlib
import io
import json
import pathlib
import re
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import a11y_ci  # noqa: E402


class A11yCiTest(unittest.TestCase):
    def run_with(self, axe, order):
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            (out / "a11y.json").write_text(json.dumps(axe))
            (out / "order.json").write_text(json.dumps(order))
            return a11y_ci.main(out)

    def test_no_findings_passes(self):
        self.assertEqual(self.run_with([], []), 0)

    def test_a_new_finding_fails(self):
        self.assertEqual(self.run_with([{"page": "p.html", "area": "axe", "rule": "label"}], []), 1)

    def test_a_finding_known_on_main_does_not_fail(self):
        baseline = json.loads((ROOT / "tools" / "done-check-baseline.json").read_text())["steps"]["axe"]["known"]
        known = [dict(zip(("page", "area", "rule"), k.split("|"))) for k in baseline]
        self.assertTrue(known, "the baseline lists no axe finding to try")
        self.assertEqual(self.run_with(known, []), 0)

    def test_one_more_than_known_on_main_fails(self):
        key = next(iter(json.loads((ROOT / "tools" / "done-check-baseline.json").read_text())["steps"]["axe"]["known"]))
        page, area, rule = key.split("|")
        one = {"page": page, "area": area, "rule": rule}
        self.assertEqual(self.run_with([one, one], []), 1)

    def test_a_page_error_is_new_and_fails_and_says_what_it_waited_for(self):
        said = io.StringIO()
        error = {"page": "x.html, a state", "area": "page", "rule": "error", "detail": "waiting for locator('#list li')"}
        with contextlib.redirect_stdout(said):
            self.assertEqual(self.run_with([error], []), 1)
        self.assertIn("x.html, a state|page|error (1): waiting for locator('#list li')", said.getvalue())

    def test_the_workflow_gives_the_example_server_the_library_the_image_has(self):
        # Without it the full backups panel says it cannot make backups and the page's check waits for a list (DASH-636).
        want = re.search(r'"cryptography==([\d.]+)"', (ROOT / "Dockerfile").read_text()).group(1)
        self.assertIn(f"cryptography=={want}", (ROOT / ".github" / "workflows" / "a11y.yml").read_text())

    def test_signed_in_the_sign_in_and_set_up_pages_sending_on_is_not_a_finding(self):
        text = (ROOT / "tools" / "a11y" / "a11y.mjs").read_text()
        self.assertRegex(text, r'SENDS_ON = new Set\(\["login\.html", "setup\.html"\]\)')
        self.assertIn("if (!SENDS_ON.has(name)) add(name, \"page\", \"redirects\"", text)  # every other page still is

    def test_the_workflow_is_named_for_the_check_and_limited(self):
        text = (ROOT / ".github" / "workflows" / "a11y.yml").read_text()
        self.assertIn("name: a11y (changed pages)", text)
        self.assertIn("timeout-minutes: 10", text)
        self.assertIn("cancel-in-progress: true", text)


if __name__ == "__main__":
    unittest.main()
