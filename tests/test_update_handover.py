"""update.sh runs the new version's own update.sh (DASH-429), so a fix to it takes effect in the update that brings
it, not one update later. Going back keeps the running copy, and the new copy never hands over again.

Each test makes a scratch "origin" with two releases and a clone of it, then runs update.sh in the clone. The copy
that should not run anything heavy is a short stand-in that says it ran, so nothing is built or restarted."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
STAND_IN = '#!/usr/bin/env bash\necho "STAND-IN RAN args=$* handed=${STARBOARD_UPDATE_HANDED:-} dir=${STARBOARD_UPDATE_DIR:-}"\nrm -f "$0"  # as update.sh does\n'
GIT = ["git", "-c", "user.name=TheMightyTRexUK", "-c", "user.email=test@example.invalid", "-c", "init.defaultBranch=main",
       "-c", "advice.detachedHead=false"]


@unittest.skipUnless(shutil.which("git"), "needs git")
class UpdateHandOver(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("STARBOARD_", "GIT_"))}

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd):
        subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, env=self.env)

    def releases(self, first, second):
        """origin with v0.1.0 (update.sh = first) and v0.2.0 (update.sh = second); a clone on v0.1.0 or v0.2.0."""
        origin = self.dir / "origin"
        origin.mkdir()
        self.git("init", "-q", cwd=origin)
        for tag, text in (("v0.1.0", first), ("v0.2.0", second)):
            (origin / "update.sh").write_text(text)
            (origin / "VERSION").write_text(tag)
            self.git("add", "-A", cwd=origin)
            self.git("commit", "-q", "-m", tag, cwd=origin)
            self.git("tag", tag, cwd=origin)
        clone = self.dir / "starboard"
        self.git("clone", "-q", str(origin), str(clone), cwd=self.dir)
        (clone / ".env").write_text("STARBOARD_MODE=native\nSTARBOARD_PORT=9\n")
        return clone

    def run_update(self, clone, at, *args, env=None):
        self.git("checkout", "-q", at, cwd=clone)
        return subprocess.run(["bash", "update.sh", *args], cwd=clone, capture_output=True, text=True, timeout=60,
                              env={**self.env, **(env or {})})

    def test_an_update_runs_the_new_versions_update_sh_pinned_to_that_version(self):
        clone = self.releases((ROOT / "update.sh").read_text(), STAND_IN)
        done = self.run_update(clone, "v0.1.0")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Using the update steps from v0.2.0", done.stdout)
        self.assertIn(f"STAND-IN RAN args=--to v0.2.0 handed=1 dir={clone}", done.stdout)
        self.assertFalse((clone / "backups").exists())  # the old copy stopped before its backup
        self.assertEqual((clone / "VERSION").read_text(), "v0.1.0")  # and changed nothing

    def test_the_new_copy_never_hands_over_again(self):
        clone = self.releases((ROOT / "update.sh").read_text(), STAND_IN)
        done = self.run_update(clone, "v0.1.0", env={"STARBOARD_UPDATE_HANDED": "1"})
        self.assertNotIn("STAND-IN RAN", done.stdout)
        self.assertNotIn("Using the update steps", done.stdout)
        self.assertIn("Backing up your settings", done.stdout)  # it carried on itself (and stopped: no data folder)

    def test_going_back_keeps_the_running_copy(self):
        clone = self.releases(STAND_IN, (ROOT / "update.sh").read_text())
        done = self.run_update(clone, "v0.2.0", "--to", "v0.1.0")
        self.assertNotIn("STAND-IN RAN", done.stdout)
        self.assertIn("Backing up your settings", done.stdout)

    def test_check_only_never_hands_over(self):
        clone = self.releases((ROOT / "update.sh").read_text(), STAND_IN)
        done = self.run_update(clone, "v0.1.0", "--check")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn("STAND-IN RAN", done.stdout)
        self.assertIn("Available: v0.2.0", done.stdout)

    def test_no_temporary_copies_are_left_behind(self):
        clone = self.releases((ROOT / "update.sh").read_text(), STAND_IN)
        tmp = self.dir / "tmp"
        tmp.mkdir()
        self.run_update(clone, "v0.1.0", env={"TMPDIR": str(tmp)})
        self.assertEqual(list(tmp.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
