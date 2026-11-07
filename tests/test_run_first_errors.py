"""Every error number Run first and the installer print is on the help page, and the page has no others."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class RunFirstErrorsTest(unittest.TestCase):
    def test_script_and_help_page_list_the_same_numbers(self):
        script = (ROOT / "run-first.sh").read_text()
        page = (ROOT / "docs/help/topics/run-first-errors.md").read_text()
        installer = (ROOT / "install.sh").read_text()
        used = set(re.findall(r"\bRF-\d\d\b", script)) | set(re.findall(r"\bIN-\d\d\b", installer))
        explained = set(re.findall(r"^### ((?:RF|IN)-\d\d)$", page, re.M))
        self.assertTrue(used)
        self.assertEqual(used, explained)

    def test_the_link_points_at_the_page(self):
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('ERR_URL="https://themightytrex.github.io/starboard/help/topics/run-first-errors.html"', script)


if __name__ == "__main__":
    unittest.main()
