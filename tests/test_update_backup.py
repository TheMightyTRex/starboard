"""update.sh's backup before an update (14 November 2026): each plug-in's own data folder belongs to the plug-in's
user, so Starboard's user cannot read it and tar stopped the update ("Cannot open: Permission denied", exit 2). The
backup leaves those folders out, and going back after a failed start keeps them with their plug-in.

The test runs update.sh's own backup_data and restore_data functions, cut out between their markers, in a scratch
folder with a plug-in data folder nobody can read.

16 November 2026: Update now on the page stopped at the backup with "tar: data/self-update.log.new: No such file or
directory". The page's helper rewrites its log after every line as self-update.log.new and renames it, so tar listed
the file and found it gone. The backup now leaves out that log and every half-written .tmp or .new file, and a backup
that fails says why."""
import os
import pathlib
import subprocess
import tarfile
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def functions():
    text = (ROOT / "update.sh").read_text(encoding="utf-8")
    start = text.index("# update-data-functions-begin")
    return text[start:text.index("# update-data-functions-end")]


class UpdateBackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        plugin = self.dir / "data" / "plugins" / "watch-stats"
        (plugin / "data" / "main").mkdir(parents=True)
        (plugin / "data" / "main" / "plays.db").write_text("plays")
        (plugin / "settings.json").write_text('{"keep": 1}')
        (plugin / "manifest.json").write_text("{}")
        (self.dir / "data" / "config.json").write_text('{"site_name": "before"}')
        (plugin / "data" / "main").chmod(0o000)  # as the plug-in's own user's folder looks to Starboard's user

    def tearDown(self):
        for p in self.dir.rglob("*"):
            if p.is_dir() and not p.is_symlink():
                p.chmod(0o755)
        self.tmp.cleanup()

    def run_sh(self, body):
        return subprocess.run(["bash", "-c", "set -euo pipefail\n" + functions() + body], cwd=self.dir,
                              capture_output=True, text=True)

    def test_the_backup_leaves_out_plug_in_data_and_keeps_their_settings(self):
        done = self.run_sh('backup_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        with tarfile.open(self.dir / "backup.tar.gz") as t:
            names = t.getnames()
        self.assertIn("data/config.json", names)
        self.assertIn("data/plugins/watch-stats/settings.json", names)
        self.assertIn("data/plugins/watch-stats/manifest.json", names)
        self.assertFalse([n for n in names if n.startswith("data/plugins/watch-stats/data")])
        self.assertEqual(os.stat(self.dir / "backup.tar.gz").st_mode & 0o077, 0)  # private

    def test_going_back_restores_settings_and_keeps_plug_in_data_in_place(self):
        self.assertEqual(self.run_sh('backup_data backup.tar.gz\n').returncode, 0)
        # The failed version changed the settings and the plug-in's settings.
        (self.dir / "data" / "config.json").write_text('{"site_name": "after"}')
        (self.dir / "data" / "plugins" / "watch-stats" / "settings.json").write_text('{"keep": 2}')
        done = self.run_sh('restore_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        plugin = self.dir / "data" / "plugins" / "watch-stats"
        self.assertEqual((self.dir / "data" / "config.json").read_text(), '{"site_name": "before"}')
        self.assertEqual((plugin / "settings.json").read_text(), '{"keep": 1}')
        (plugin / "data" / "main").chmod(0o755)
        self.assertEqual((plugin / "data" / "main" / "plays.db").read_text(), "plays")
        self.assertTrue((self.dir / "data.failed-update" / "config.json").exists())
        self.assertFalse([p.name for p in self.dir.joinpath("data").iterdir() if p.name.startswith(".restore-")])

    def test_update_sh_uses_them_and_says_so(self):
        text = (ROOT / "update.sh").read_text(encoding="utf-8")
        self.assertIn('backup_data "$BACKUP"', text)
        self.assertIn('restore_data "$BACKUP"', text)
        self.assertIn("plug-ins' own data folders are not in it", text)
        self.assertNotIn('tar -czf "$BACKUP" data)', text)

    def test_the_backup_leaves_out_the_update_log_and_half_written_files(self):
        data = self.dir / "data"
        for name in ("self-update.log", "self-update.log.new", "config.json.tmp", "versions.json.tmp"):
            (data / name).write_text("half written")
        (data / "self-update.json").write_text("{}")
        done = self.run_sh('backup_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        with tarfile.open(self.dir / "backup.tar.gz") as t:
            names = t.getnames()
        self.assertIn("data/config.json", names)
        self.assertIn("data/self-update.json", names)
        for name in ("self-update.log", "self-update.log.new", "config.json.tmp", "versions.json.tmp"):
            self.assertNotIn("data/" + name, names)

    def test_the_backup_carries_on_while_the_page_rewrites_its_log(self):
        # The page's helper, as self_update.WRAPPER writes: copy to .new, then rename, as fast as it can.
        data = self.dir / "data"
        for i in range(200):
            (data / f"settings-{i}.json").write_text("x" * 2000)
        writer = subprocess.Popen(["bash", "-c", 'while :; do echo line >> t; cp t data/self-update.log.new && '
                                   'mv -f data/self-update.log.new data/self-update.log; done'], cwd=self.dir)
        try:
            for n in range(15):
                done = self.run_sh(f'backup_data backup-{n}.tar.gz\n')
                self.assertEqual(done.returncode, 0, done.stderr)
        finally:
            writer.kill()
            writer.wait()

    def test_a_backup_that_fails_stops_the_update_and_says_why(self):
        text = (ROOT / "update.sh").read_text(encoding="utf-8")
        self.assertIn('if ! backup_err="$(backup_data "$BACKUP" 2>&1)"; then', text)
        self.assertIn("Stopped: your settings could not be backed up, so nothing was changed.", text)


if __name__ == "__main__":
    unittest.main()
