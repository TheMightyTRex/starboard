"""The image build's permissions step (Dockerfile, optimisation review 16 November 2026): starboard/fix_modes.py ends
with the same permissions as chmod -R a+rX,go-w, and changes nothing that is right already, so the image layer does
not keep a second copy of every file."""
import os
import shutil
import stat
import subprocess  # nosec B404: the system's own chmod, on a temporary folder
import tempfile
import unittest

from starboard import fix_modes

MODES = {"a.py": 0o664, "b.sh": 0o775, "c.txt": 0o600, "d.css": 0o644, "e.bin": 0o700, "f.txt": 0o622, "g": 0o640}


def make(top):
    os.makedirs(os.path.join(top, "web", "js"))
    os.makedirs(os.path.join(top, "private"))
    for i, (name, mode) in enumerate(MODES.items()):
        path = os.path.join(top, ["web", "web/js", "private", ""][i % 4], name)
        with open(path, "w") as f:
            f.write(name)
        os.chmod(path, mode)
    os.chmod(os.path.join(top, "private"), 0o700)
    os.chmod(os.path.join(top, "web", "js"), 0o775)
    os.symlink("a.py", os.path.join(top, "web", "link"))


def modes(top):
    return {os.path.relpath(os.path.join(d, n), top): stat.S_IMODE(os.lstat(os.path.join(d, n)).st_mode)
            for d, dirs, files in os.walk(top) for n in dirs + files if not os.path.islink(os.path.join(d, n))}


@unittest.skipUnless(shutil.which("chmod"), "needs chmod")
class FixModes(unittest.TestCase):
    def test_the_same_permissions_as_chmod(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            make(one)
            make(two)
            subprocess.run(["chmod", "-R", "a+rX,go-w", one], check=True)  # nosec B603 B607
            fix_modes.fix(two)
            self.assertEqual(modes(two), modes(one))
            self.assertEqual(stat.S_IMODE(os.stat(two).st_mode), stat.S_IMODE(os.stat(one).st_mode))

    def test_right_ones_are_left_alone(self):
        with tempfile.TemporaryDirectory() as top:
            make(top)
            self.assertGreater(fix_modes.fix(top), 0)
            self.assertEqual(fix_modes.fix(top), 0)  # a second run changes nothing


if __name__ == "__main__":
    unittest.main()
