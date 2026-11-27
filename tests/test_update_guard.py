"""The update guard for the clean break (DASH-596, owner, 26 November 2026): Starboard 0.40.0 and later can be
installed only from 0.31.0 or later; the update saves a backup first and says plainly that there is no way back; and
going back past 0.40.0 warns, saves a fresh backup first and offers --restore as the safe way.

Each test makes a scratch "origin" with releases whose VERSION files say what they are, and a clone of it, then runs the
real update.sh in the clone. Stand-ins for systemctl and python3 stop it from restarting anything or waiting for an
answer, so nothing real is built or started."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GIT = ["git", "-c", "user.name=TheMightyTRexUK", "-c", "user.email=test@example.invalid", "-c", "init.defaultBranch=main",
       "-c", "advice.detachedHead=false"]
SYSTEMCTL = "#!/bin/sh\nexit 0\n"  # a restart that always works
PYTHON = '#!/bin/sh\ncase "$*" in *urlopen*) exit 0;; *) echo 5;; esac\n'  # Starboard always answers; keep 5 copies


@unittest.skipUnless(shutil.which("git") and shutil.which("tar"), "needs git and tar")
class UpdateGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        for name, text in (("systemctl", SYSTEMCTL), ("python3", PYTHON)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("STARBOARD_", "GIT_"))}
        self.env["PATH"] = f"{self.bin}:{self.env['PATH']}"

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, cwd):
        subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, env=self.env)

    def releases(self, *versions):
        """origin with a release for each version (VERSION says it, update.sh is the real one); a clone, on the first."""
        origin = self.dir / "origin"
        origin.mkdir()
        self.git("init", "-q", cwd=origin)
        for version in versions:
            (origin / "update.sh").write_text((ROOT / "update.sh").read_text())
            (origin / "VERSION").write_text(version + "\n")
            self.git("add", "-A", cwd=origin)
            self.git("commit", "-q", "-m", version, cwd=origin)
            self.git("tag", "v" + version, cwd=origin)
        clone = self.dir / "starboard"
        self.git("clone", "-q", str(origin), str(clone), cwd=self.dir)
        self.git("checkout", "-q", "v" + versions[0], cwd=clone)
        (clone / ".env").write_text("STARBOARD_MODE=native\nSTARBOARD_PORT=9\n")
        return clone

    def with_settings(self, clone, text="made-up settings"):
        (clone / "data").mkdir(exist_ok=True)
        (clone / "data" / "config.json").write_text(text)

    def run_update(self, clone, *args):
        return subprocess.run(["bash", "update.sh", *args], cwd=clone, capture_output=True, text=True, timeout=120, env=self.env)

    def version(self, clone):
        return (clone / "VERSION").read_text().strip()

    # The supported-from rule -----------------------------------------------------------------------------------

    def test_an_install_before_0_31_0_is_told_to_update_to_0_31_first_and_nothing_changes(self):
        clone = self.releases("0.30.2", "0.31.0", "0.40.0")
        self.with_settings(clone)
        done = self.run_update(clone)  # the newest release is 0.40.0
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn("Starboard 0.40.0 can only be installed from 0.31.0 or later", done.stderr)
        self.assertIn("./update.sh --to v0.31.0", done.stderr)
        self.assertEqual(self.version(clone), "0.30.2")
        self.assertFalse((clone / "backups").exists())  # it stopped before anything was backed up or changed

    def test_the_check_says_the_same_and_changes_nothing(self):
        clone = self.releases("0.30.2", "0.31.0", "0.40.0")
        done = self.run_update(clone, "--check")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Update to v0.31.0 first", done.stdout)
        self.assertNotIn("Run ./update.sh to install it", done.stdout)

    def test_the_way_to_0_31_is_open_from_an_older_version(self):
        clone = self.releases("0.30.2", "0.31.0", "0.40.0")
        self.with_settings(clone)
        done = self.run_update(clone, "--to", "v0.31.0")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.version(clone), "0.31.0")
        self.assertNotIn("cannot be undone", done.stdout)  # 0.31.0 is not the break

    def test_0_31_0_and_every_0_31_x_may_update_to_0_40_0(self):
        for start in ("0.31.0", "0.31.3"):
            with self.subTest(start=start):
                clone = self.releases(start, "0.40.0")
                self.with_settings(clone)
                done = self.run_update(clone)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertNotIn("can only be installed from", done.stdout + done.stderr)
                self.assertEqual(self.version(clone), "0.40.0")
                shutil.rmtree(self.dir / "origin")
                shutil.rmtree(clone)

    # Rule 1: a backup first that reads back ------------------------------------------------------------------------

    def test_the_update_saves_a_backup_that_reads_back_before_it_changes_anything(self):
        clone = self.releases("0.31.0", "0.40.0")
        self.with_settings(clone, "made-up settings that must survive")
        done = self.run_update(clone)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertLess(done.stdout.index("Backing up your settings"), done.stdout.index("Installing v0.40.0"))
        saved = sorted((clone / "backups").glob("starboard-data-*.tar.gz"))
        self.assertEqual(len(saved), 1)
        listing = subprocess.run(["tar", "-tzf", str(saved[0])], capture_output=True, text=True, check=True).stdout
        self.assertIn("data/config.json", listing)
        self.assertIn(f"Keep {saved[0].relative_to(clone)}: it is your way back", done.stdout)

    def test_no_backup_that_reads_back_means_no_update(self):
        clone = self.releases("0.31.0", "0.40.0")  # no data folder: tar cannot make a backup
        done = self.run_update(clone)
        self.assertEqual(done.returncode, 1)
        self.assertIn("could not be backed up, so nothing was changed", done.stdout)
        self.assertEqual(self.version(clone), "0.31.0")

    # Rule 2: one way, said plainly ------------------------------------------------------------------------------------

    def test_the_update_says_in_plain_words_that_you_cannot_go_back(self):
        clone = self.releases("0.31.0", "0.40.0")
        self.with_settings(clone)
        done = self.run_update(clone)
        words = done.stdout
        self.assertIn("== This update cannot be undone", words)
        self.assertIn("You cannot go back to an older Starboard after this update.", words)
        self.assertIn("To go back, you restore that backup.", words)
        self.assertIn("Settings you change after the update are lost", words)
        self.assertLess(words.index("cannot be undone"), words.index("Backing up your settings"))

    def test_an_ordinary_update_says_nothing_about_it(self):
        clone = self.releases("0.40.0", "0.40.1")
        self.with_settings(clone)
        done = self.run_update(clone)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("cannot be undone", done.stdout)
        self.assertNotIn("your way back", done.stdout)

    def test_going_back_past_the_break_warns_saves_a_fresh_backup_and_goes_on(self):
        clone = self.releases("0.40.0", "0.31.0")
        self.with_settings(clone, "settings from 0.40.0")
        done = self.run_update(clone, "--to", "v0.31.0")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("== Going back past 0.40.0", done.stdout)
        self.assertIn("your settings may not match v0.31.0", done.stdout)
        self.assertIn("--restore backups/NAME", done.stdout)
        self.assertLess(done.stdout.index("Going back past"), done.stdout.index("Backing up your settings"))
        self.assertEqual(self.version(clone), "0.31.0")
        saved = list((clone / "backups").glob("starboard-data-*.tar.gz"))
        self.assertEqual(len(saved), 1)  # a fresh backup of the settings it left
        self.assertEqual((clone / "data" / "config.json").read_text(), "settings from 0.40.0")  # not replaced

    def test_going_back_with_the_backup_puts_the_old_settings_back(self):
        clone = self.releases("0.31.0", "0.40.0")
        self.with_settings(clone, "settings from 0.31.0")
        self.assertEqual(self.run_update(clone).returncode, 0)
        (clone / "data" / "config.json").write_text("settings after 0.40.0")
        backup = next((clone / "backups").glob("starboard-data-*.tar.gz"))
        done = self.run_update(clone, "--to", "v0.31.0", "--restore", str(backup))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.version(clone), "0.31.0")
        self.assertEqual((clone / "data" / "config.json").read_text(), "settings from 0.31.0")
        self.assertEqual((clone / "data.failed-update" / "config.json").read_text(), "settings after 0.40.0")  # kept, not deleted

    def test_a_backup_that_cannot_be_read_stops_going_back(self):
        clone = self.releases("0.40.0", "0.31.0")
        self.with_settings(clone)
        (clone / "not-a-backup.tar.gz").write_text("not a backup")
        done = self.run_update(clone, "--to", "v0.31.0", "--restore", "not-a-backup.tar.gz")
        self.assertEqual(done.returncode, 1)
        self.assertIn("could not be read, so nothing was changed", done.stderr)
        self.assertEqual(self.version(clone), "0.40.0")

    def test_restore_is_only_for_going_back_past_the_break(self):
        clone = self.releases("0.31.0", "0.32.0")
        done = self.run_update(clone, "--restore", "x.tar.gz")
        self.assertEqual(done.returncode, 1)
        self.assertIn("--restore is only for going back", done.stderr)


if __name__ == "__main__":
    unittest.main()
