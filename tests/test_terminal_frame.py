"""run-first.sh carries a copy of lib/terminal-frame.sh (it arrives alone through curl): the two stay the same."""

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TerminalFrameCopyTest(unittest.TestCase):
    def test_run_first_has_the_same_frame(self):
        script = (ROOT / "run-first.sh").read_text()
        start = script.index("# terminal-frame: start")
        start = script.index("\n", start) + 1
        end = script.index("# terminal-frame: end")
        self.assertEqual(script[start:end], (ROOT / "lib/terminal-frame.sh").read_text(),
                         "Copy lib/terminal-frame.sh into run-first.sh between its terminal-frame lines")

    def test_the_installer_reads_it(self):
        self.assertIn("lib/terminal-frame.sh", (ROOT / "install.sh").read_text())


if __name__ == "__main__":
    unittest.main()
