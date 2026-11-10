"""The folder picker's server side (DASH-240): tidy, browse and check folders, directly or through the helper."""
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from starboard import folders


class FoldersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "mnt")
        for d in ("disk1/media/movies", "disk1/media/tv", "disk1/.hidden", "disk2"):
            os.makedirs(os.path.join(self.root, d))
        open(os.path.join(self.root, "disk1", "a-file"), "w").close()
        p = mock.patch.object(folders, "ROOTS", (self.root,))
        p.start()
        self.addCleanup(p.stop)

    def helper(self, root, script):  # what the helper prints, with the place at /r
        return subprocess.run(["sh", "-c", script.replace("/r", root)], capture_output=True, text=True).stdout

    def test_tidy(self):
        self.assertEqual(folders.tidy("  /srv/media/  "), "/srv/media")
        for bad in ("media", "/srv/../etc", "~/media"):
            with self.assertRaises(ValueError):
                folders.tidy(bad)
        with mock.patch.dict(os.environ, {"STARBOARD_HOST_HOME": "/home/sam"}):
            self.assertEqual(folders.tidy("~/media"), "/home/sam/media")

    def test_browse_directly_and_through_the_helper_agree(self):
        with mock.patch.object(folders, "_in_docker", return_value=False):
            direct = folders.browse(self.root + "/disk1")
        through = folders.browse(self.root + "/disk1", run=self.helper)
        for out in (direct, through):
            self.assertEqual([f["name"] for f in out["folders"]], ["media"])  # no files, no hidden folders
            self.assertTrue(out["free"] > 0 and out["total"] >= out["free"])
            self.assertEqual(out["crumbs"][-1]["name"], "disk1")
        with self.assertRaises(LookupError):
            folders.browse(self.root + "/missing", run=self.helper)
        with self.assertRaises(ValueError):
            folders.browse("/etc")

    def test_check_says_what_happens_in_plain_words(self):
        here = folders.check(self.root + "/disk1/media/", run=self.helper)
        self.assertEqual(here["path"], self.root + "/disk1/media")
        self.assertIn("This folder is there.", here["lines"])
        later = folders.check(self.root + "/disk2/new/media", run=self.helper)
        self.assertTrue(any("made for you" in line and line.endswith(self.root + "/disk2.") for line in later["lines"]), later)
        self.assertIn("never uses system folders", folders.check("/etc/media")["lines"][0])
        self.assertIn("/srv/media.", folders.check("/srv")["lines"][0])
        self.assertFalse(folders.check("relative/path")["ok"])


if __name__ == "__main__":
    unittest.main()
