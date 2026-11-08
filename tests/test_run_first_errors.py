"""Every error number Run first and the installer print is on the help page, and the page has no others."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class RunFirstErrorsTest(unittest.TestCase):
    def test_script_and_help_page_list_the_same_numbers(self):
        script = (ROOT / "run-first.sh").read_text()
        page = (ROOT / "docs/help/topics/run-first-errors.md").read_text()
        installer = (ROOT / "install.sh").read_text() + (ROOT / "starboard/terminal_setup.py").read_text()
        used = set(re.findall(r"\bRF-\d\d\b", script)) | set(re.findall(r"\bIN-\d\d\b", installer))
        explained = set(re.findall(r"^### ((?:RF|IN)-\d\d)$", page, re.M))
        self.assertTrue(used)
        self.assertEqual(used, explained)

    def test_the_link_points_at_the_page(self):
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('ERR_URL="https://themightytrex.github.io/starboard/help/topics/run-first-errors.html"', script)


class InstallerStopNoteTest(unittest.TestCase):
    """DASH-147: the installer writes how it stopped for the Run first script, which then ends on that number."""

    def test_the_installer_writes_its_error_number(self):
        import os
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            note = os.path.join(d, "stopped-with")
            env = dict(os.environ, STARBOARD_ERROR_FILE=note)
            done = subprocess.run([str(ROOT / "install.sh"), "--not-an-option"], env=env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=30)
            self.assertEqual(done.returncode, 2)
            self.assertIn("Error IN-01. What it means and how to fix it:", done.stderr)
            self.assertEqual(open(note).read().strip(), "IN-01")

    def test_run_first_ends_on_the_installers_number_not_its_own(self):
        script = (ROOT / "run-first.sh").read_text()
        ending = script[script.index('inner="$(head -n 1 "$STARBOARD_ERROR_FILE"'):]
        ending = ending[:ending.index("esac")]
        self.assertIn('err "$inner"', ending)
        self.assertLess(ending.index("stopped)"), ending.index("err RF-40"))
        self.assertEqual(ending.count("err RF-40"), 1)  # only when the installer gave no number

    def test_a_person_stopping_is_noted_without_a_number(self):
        frame = (ROOT / "lib/terminal-frame.sh").read_text()
        self.assertIn("stopped_by_person; exit 1", frame)
        self.assertIn("stopped_by_person; exit 130", frame)



class PlainCarriesOnTest(unittest.TestCase):
    def test_second_installer_run_keeps_accessible_mode(self):
        # Run first runs the installer again for the set-up's changes to this computer; in accessible mode that run
        # must be plain too, or the very last page is boxed (night of 8 November 2026).
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('[ -z "$PLAIN" ] || again+=(--plain)', script)
        plain_choice = 'case "$first" in a|A) FANCY=0; PLAIN=1'
        self.assertIn(plain_choice, script)


if __name__ == "__main__":
    unittest.main()
