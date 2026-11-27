"""tools/check-wizard-coverage.py: a wizard cannot be added without a keyboard task."""
import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wizard_coverage", ROOT / "tools" / "check-wizard-coverage.py")
cov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cov)


def make(root, flows, tasks='check("T-A", "x", true);', scripts=None):
    (root / "tools/a11y").mkdir(parents=True)
    (root / "web/js").mkdir(parents=True)
    (root / "tools/a11y/wizards.json").write_text(json.dumps({"flows": flows}))
    (root / "tools/a11y/tasks.mjs").write_text(tasks)
    for name, body in (scripts or {}).items():
        (root / "web/js" / name).write_text(body)


class CoverageTest(unittest.TestCase):
    def run_case(self, flows, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            make(root, flows, **kw)
            return cov.problems(root)

    def test_the_shipped_registry_is_complete(self):
        self.assertEqual(cov.problems(), [])

    def test_a_flow_with_a_task_passes(self):
        self.assertEqual(self.run_case([{"id": "a", "files": ["web/js/a.js"], "tasks": ["T-A"]}], scripts={"a.js": "x"}), [])

    def test_a_flow_without_a_task_fails(self):
        self.assertTrue(any("no keyboard task" in p for p in self.run_case([{"id": "a", "files": [], "tasks": []}])))

    def test_a_task_that_does_not_exist_fails(self):
        self.assertTrue(any("T-GONE" in p for p in self.run_case([{"id": "a", "files": [], "tasks": ["T-GONE"]}])))

    def test_a_missing_file_fails(self):
        self.assertTrue(any("does not exist" in p for p in self.run_case([{"id": "a", "files": ["web/js/none.js"], "tasks": ["T-A"]}])))

    def test_a_new_wizard_script_in_no_flow_fails(self):
        found = self.run_case([{"id": "a", "files": [], "tasks": ["T-A"]}], scripts={"new.js": "wizardFrame({ root });"})
        self.assertTrue(any("web/js/new.js" in p for p in found))

    def test_a_terminal_flow_needs_its_tests(self):
        found = self.run_case([{"id": "t", "browser": False, "files": [], "covered_by": ["tests/none.py"]}])
        self.assertTrue(any("does not exist" in p for p in found))


if __name__ == "__main__":
    unittest.main()
