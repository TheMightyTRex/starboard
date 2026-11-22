"""update.sh's backup before an update (14 November 2026): each plug-in's own data folder belongs to the plug-in's
user, so Starboard's user cannot read it and tar stopped the update ("Cannot open: Permission denied", exit 2). The
backup leaves those folders out, and going back after a failed start keeps them with their plug-in.

The test runs update.sh's own backup_data and restore_data functions, cut out between their markers, in a scratch
folder with a plug-in data folder nobody can read.

16 November 2026: Update now on the page stopped at the backup with "tar: data/self-update.log.new: No such file or
directory". The page's helper rewrites its log after every line as self-update.log.new and renames it, so tar listed
the file and found it gone. The backup now leaves out that log and every half-written .tmp or .new file, and a backup
that fails says why."""
import json
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

    # DASH-484 (owner, 19 November 2026): plug-ins added or removed between updates must not stop or spoil a backup.
    # A folder only a plug-in's user can read is shown here with no rights, as Starboard's user would find it.
    def held(self, name, plays):
        held = self.dir / "data" / "holding" / name
        (held / "data" / "main").mkdir(parents=True)
        (held / "data" / "main" / "plays.db").write_text(plays)
        (held / "settings.json").write_text('{"held": 1}')
        (held / "data" / "main").chmod(0o000)
        return held

    def test_a_removed_plug_in_in_holding_is_left_out_and_comes_back_whole(self):
        # 19 November 2026: a Watch stats copy in holding stopped the update to 0.22.0
        # ("data/holding/.../data/main: Cannot open: Permission denied").
        held = self.held("2026-11-17-165959-watch-stats", "held plays")
        done = self.run_sh('backup_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        with tarfile.open(self.dir / "backup.tar.gz") as t:
            names = t.getnames()
        self.assertIn("data/holding/2026-11-17-165959-watch-stats/settings.json", names)
        self.assertFalse([n for n in names if n.startswith("data/holding/2026-11-17-165959-watch-stats/data/main")])
        done = self.run_sh('restore_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        (held / "data" / "main").chmod(0o755)
        self.assertEqual((held / "data" / "main" / "plays.db").read_text(), "held plays")
        self.assertEqual((held / "settings.json").read_text(), '{"held": 1}')

    def test_a_folder_no_one_expected_is_left_out_too(self):
        odd = self.dir / "data" / "cache" / "some-plug-in" / "inner"
        odd.mkdir(parents=True)
        (odd / "x").write_text("x")
        odd.chmod(0o000)
        done = self.run_sh('backup_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.run_sh('restore_data backup.tar.gz\n').returncode, 0)
        odd.chmod(0o755)
        self.assertEqual((odd / "x").read_text(), "x")

    def test_plug_ins_added_or_removed_after_the_backup_keep_their_data_when_going_back(self):
        self.assertEqual(self.run_sh('backup_data backup.tar.gz\n').returncode, 0)
        # After the backup: a new plug-in is added, and Watch stats is removed to holding.
        new = self.dir / "data" / "plugins" / "tv-station"
        (new / "data" / "main").mkdir(parents=True)
        (new / "data" / "main" / "schedule.db").write_text("schedule")
        (new / "settings.json").write_text('{"new": 1}')
        (new / "data" / "main").chmod(0o000)
        old = self.dir / "data" / "plugins" / "watch-stats"
        old.chmod(0o755)
        (old / "data" / "main").chmod(0o755)
        held = self.dir / "data" / "holding" / "2026-11-19-090000-watch-stats"
        held.parent.mkdir(parents=True)
        old.rename(held)
        (held / "data" / "main").chmod(0o000)
        done = self.run_sh('restore_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        (new / "data" / "main").chmod(0o755)
        self.assertEqual((new / "data" / "main" / "schedule.db").read_text(), "schedule")
        (held / "data" / "main").chmod(0o755)
        self.assertEqual((held / "data" / "main" / "plays.db").read_text(), "plays")
        # The backup's Watch stats comes back with its settings; its data folder stays with the held copy.
        self.assertEqual((self.dir / "data" / "plugins" / "watch-stats" / "settings.json").read_text(), '{"keep": 1}')

    def caches(self):
        data = self.dir / "data"
        for name in ("posters/library/a.img", "posters/tv-series-1.jpg", "icons/sonarr.png", "logs/starboard.log",
                     "library/films.json", "library/tv.json", "library/music.json", "library/books.json",
                     "library/audiobooks.json", "library/radio.json", "library/network-logos.json",
                     "library/views.json", "library/station-logos/one.png", "plugins/watch-stats/logs/kept.txt"):
            (data / name).parent.mkdir(parents=True, exist_ok=True)
            (data / name).write_text("before " + name)

    def test_the_backup_leaves_out_caches(self):
        """DASH-384: posters, icons, logs and the Library's lists are made again, so they are not in the copy."""
        self.caches()
        done = self.run_sh('backup_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        with tarfile.open(self.dir / "backup.tar.gz") as t:
            names = t.getnames()
        left_out = [n for n in names if n.startswith(("data/posters", "data/icons", "data/logs"))
                    or n in ["data/library/" + f for f in ("films.json", "tv.json", "music.json", "books.json", "audiobooks.json",
                                                           "radio.json", "network-logos.json")]]
        self.assertEqual(left_out, [])
        for kept in ("data/config.json", "data/library/views.json", "data/library/station-logos/one.png",
                     "data/plugins/watch-stats/logs/kept.txt", "data/plugins/watch-stats/settings.json"):
            self.assertIn(kept, names)  # settings, what someone added, and a plug-in's own folder of the same name

    def test_going_back_keeps_posters_icons_and_logs_and_drops_the_lists(self):
        self.caches()
        done = self.run_sh('backup_data backup.tar.gz\n'
                           'echo "the update failed here" >> data/logs/starboard.log\n'
                           'echo "written by the newer version" > data/library/films.json\n'
                           'echo \'{"site_name": "after"}\' > data/config.json\n'
                           'restore_data backup.tar.gz\n')
        self.assertEqual(done.returncode, 0, done.stderr)
        data = self.dir / "data"
        self.assertEqual(json.loads((data / "config.json").read_text())["site_name"], "before")
        self.assertIn("the update failed here", (data / "logs" / "starboard.log").read_text())  # the log says why
        self.assertTrue((data / "posters" / "library" / "a.img").exists())
        self.assertTrue((data / "icons" / "sonarr.png").exists())
        self.assertFalse((data / "library" / "films.json").exists())  # made again by the version that runs
        self.assertEqual((data / "library" / "views.json").read_text(), "before library/views.json")
        self.assertTrue((data / "library" / "station-logos" / "one.png").exists())

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


class BusyBoxTarTest(unittest.TestCase):
    """16 November 2026: the update test found that the page's updater, which has BusyBox tar, made no backup at all.
    BusyBox tar knows no --warning options and ends with 1, which the backup took for GNU tar's "a file changed", so
    going back after a failed start had nothing to restore. A tar that is not GNU tar gets no --warning options and
    only 0 is accepted, and the backup must read back before the update goes on."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        (self.dir / "data").mkdir()
        (self.dir / "data" / "config.json").write_text('{"site_name": "before"}')
        self.bin = self.dir / "bin"
        self.bin.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def fake_tar(self, body):
        tar = self.bin / "tar"
        tar.write_text("#!/bin/bash\n" + body)
        tar.chmod(0o755)

    def run_backup(self):
        env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}")
        return subprocess.run(["bash", "-c", "set -euo pipefail\n" + functions() + "backup_data backup.tar.gz\n"],
                              cwd=self.dir, capture_output=True, text=True, env=env)

    def test_busybox_tar_gets_no_warning_options_and_the_backup_is_made(self):
        real = subprocess.run(["bash", "-c", "command -v tar"], capture_output=True, text=True).stdout.strip()
        self.fake_tar(f'[ "${{1:-}}" = --version ] && {{ echo "BusyBox v1.36"; exit 0; }}\n'
                      f'for a in "$@"; do case "$a" in --warning=*) echo "tar: unrecognized option $a" >&2; exit 1;; esac; done\n'
                      f'exec {real} "$@"\n')
        done = self.run_backup()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        with tarfile.open(self.dir / "backup.tar.gz") as t:
            self.assertIn("data/config.json", t.getnames())

    def test_a_backup_that_was_not_written_stops_the_update(self):
        self.fake_tar('[ "${1:-}" = --version ] && { echo "tar (GNU tar) 1.35"; exit 0; }\nexit 1\n')
        done = self.run_backup()
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("could not be read back", done.stdout)


class RaceWithThePageHelperTest(unittest.TestCase):
    """17 November 2026: Update now to 0.20.1 stopped at the backup with "tar: data/self-update.log.new: No such file
    or directory" once more. The page's helper has BusyBox tar, which looks each file up before its --exclude list, so
    leaving the log out did not help when the helper renamed it away mid-read. The helper now writes its half-made
    log beside data, not in it, and a backup that fails is tried again, up to five times (three until 19 November 2026,
    when the race below still failed one run in three)."""

    setUp = BusyBoxTarTest.setUp
    tearDown = BusyBoxTarTest.tearDown
    fake_tar = BusyBoxTarTest.fake_tar
    run_backup = BusyBoxTarTest.run_backup

    def busybox_failing(self, times):
        real = subprocess.run(["bash", "-c", "command -v tar"], capture_output=True, text=True).stdout.strip()
        self.fake_tar(f'[ "${{1:-}}" = --version ] && {{ echo "tar (busybox) 1.37.0"; exit 0; }}\n'
                      f'case "$*" in *-tzf*) exec {real} "$@";; esac\n'
                      f'n=$(cat {self.dir}/calls 2>/dev/null || echo 0); echo $((n + 1)) > {self.dir}/calls\n'
                      f'if [ "$n" -lt {times} ]; then echo "tar: data/self-update.log.new: No such file or directory" >&2; '
                      f'echo "tar: error exit delayed from previous errors" >&2; exit 1; fi\n'
                      f'exec {real} "$@"\n')

    def calls(self):
        return int((self.dir / "calls").read_text())

    def test_a_file_renamed_away_is_tried_again(self):
        self.busybox_failing(1)
        done = self.run_backup()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls(), 2)
        self.assertIn("trying again (1 of 5)", done.stderr)
        with tarfile.open(self.dir / "backup.tar.gz") as t:
            self.assertIn("data/config.json", t.getnames())

    def test_five_failures_stop_the_update(self):
        self.busybox_failing(99)
        done = self.run_backup()
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(self.calls(), 5)
        self.assertIn("No such file or directory", done.stderr)

    def test_the_helper_writes_its_half_made_log_outside_data(self):
        from starboard import self_update
        self.assertIn("next=.self-update.log.new", self_update.WRAPPER)
        self.assertNotIn('"$log.new"', self_update.WRAPPER)
        self.assertIn(".self-update.log.new", (ROOT / ".gitignore").read_text(encoding="utf-8").split())

    def test_real_busybox_tar_beside_a_racing_log(self):
        """With the page helper's own image, when it is on this computer: the old helper's renames inside data, as fast
        as they come, while the backup runs ten times. Every backup must be made."""
        import shutil
        if not shutil.which("docker"):
            self.skipTest("Docker is not here")
        images = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}", "starboard-updater"],
                                capture_output=True, text=True).stdout.split()
        if not images:
            self.skipTest("the page helper's image is not on this computer")
        for i in range(300):
            (self.dir / "data" / f"f{i}").write_text("x")
        (self.dir / "functions.sh").write_text(functions())
        script = ('set -u\n. ./functions.sh\n'
                  '(while :; do echo l >> t; cp t data/self-update.log.new && mv -f data/self-update.log.new data/self-update.log; done) &\n'
                  'w=$!; ok=0\nfor i in 1 2 3 4 5 6 7 8 9 10; do backup_data b.tgz 2>>err && ok=$((ok + 1)); done\n'
                  'kill $w; echo "made $ok"\n')
        done = subprocess.run(["docker", "run", "--rm", "--network", "none", "--memory", "256m", "-u", f"{os.getuid()}:{os.getgid()}",
                               "-v", f"{self.dir}:/w", "-w", "/w", "--entrypoint", "bash", images[0], "-c", script],
                              capture_output=True, text=True, timeout=300)
        self.assertIn("made 10", done.stdout, done.stdout + done.stderr + (self.dir / "err").read_text() if (self.dir / "err").exists() else done.stderr)
