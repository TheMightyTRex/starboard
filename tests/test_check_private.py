"""Tests for tools/check-private.sh, in a throwaway git repository with made-up private words."""

import pathlib
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "tools" / "check-private.sh"


def check(text):
    """Exit code of the privacy check for one tracked file holding text: 0 passes, 1 stops."""
    with tempfile.TemporaryDirectory() as repo:
        root = pathlib.Path(repo)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        (root / "tools").mkdir()
        shutil.copy(SCRIPT, root / "tools" / "check-private.sh")
        (root / ".private-words").write_text("exampletrex\n-dashword\n")
        (root / ".gitignore").write_text(".private-words\n")
        (root / "notes.md").write_text(text + "\n")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        return subprocess.run(["tools/check-private.sh"], cwd=root, capture_output=True).returncode


class CheckPrivateTest(unittest.TestCase):
    def test_private_word_written_with_trex_is_caught(self):
        self.assertEqual(check("Made by ExampleTRex"), 1)

    def test_private_word_in_lower_case_is_caught(self):
        self.assertEqual(check("Made by exampletrex"), 1)

    def test_public_names_pass(self):
        self.assertEqual(check("By TheMightyTRex and TheMightyTRexUK, for the TRex Design System"), 0)

    def test_private_word_starting_with_a_hyphen_is_checked(self):
        self.assertEqual(check("see -dashword here"), 1)


if __name__ == "__main__":
    unittest.main()
