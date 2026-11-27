"""The pull request accessibility check (tools/a11y_ci.py, .github/workflows/a11y.yml)."""
import json
import pathlib
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

    def test_the_workflow_is_named_for_the_check_and_limited(self):
        text = (ROOT / ".github" / "workflows" / "a11y.yml").read_text()
        self.assertIn("name: a11y (changed pages)", text)
        self.assertIn("timeout-minutes: 10", text)
        self.assertIn("cancel-in-progress: true", text)


if __name__ == "__main__":
    unittest.main()
