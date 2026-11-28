"""DASH-631 (owner, 28 November 2026): a page with more than one topic uses page topics (tabs), never an On this page list
of jump links. This runs the design system's check over Starboard's own pages and scripts."""
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class OnThisPageTest(unittest.TestCase):
    def test_no_page_has_an_on_this_page_list(self):
        done = subprocess.run([sys.executable, str(ROOT / "tools/check_on_this_page.py"), str(ROOT / "web"), str(ROOT / "starboard")],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
