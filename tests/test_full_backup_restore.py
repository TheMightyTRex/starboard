"""Full without media (DASH-260): make one and restore it onto a fresh install, all in scratch folders.

The helper container is stood in for by the same shell scripts run here, with each folder it would mount pointed at a
scratch folder that stands for the computer. Docker is never called: the one running app is a made-up container whose
stop and start are recorded. Also: which disk a folder is on, and the default folder on another disk.
"""
import json
import os
import re
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from starboard import backup, containers, full_backup as fb, stack
from starboard.config import Config

try:
    import cryptography  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False

PASSWORD = "a long backup password"


def fake_helper(host):
    """Runs a helper script here: each mount point (/r, /w, /t, /c) becomes host + the folder it mounts."""
    def run(script, binds, timeout=0):
        for b in binds:
            src, dst = b.split(":")[:2]
            real = host + src
            os.makedirs(real, exist_ok=True)
            script = re.sub(r"(?<![\w./*-])" + re.escape(dst) + r"(?=[/\s'\"]|$)", lambda m: real, script)
        r = subprocess.run(["sh", "-c", script], capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout + r.stderr
    return run


def write(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


@unittest.skipUnless(HAVE, "cryptography is not installed here")
class MakeAndRestore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.host = self.tmp.name + "/host"  # stands for the computer's /
        self.data = self.host + "/srv/starboard/data"
        self.fresh = self.host + "/srv/fresh/data"
        self.config = self.host + "/srv/stack/config"
        uid, gid = os.getuid(), os.getgid()
        # The installed Starboard: its settings, the stack files and what never goes in.
        os.makedirs(self.data)
        c = Config(self.data)
        c.update_general({"site_name": "Harbour", "backup_schedule": "weekly"})
        write(self.data + "/api-keys.json", json.dumps({"reelix": "made-up-key"}))
        write(self.data + "/stack/.env", f"CONFIG_DIR=/srv/stack/config\nDATA_DIR=/mnt/media\nPUID={uid}\nPGID={gid}\nREELIX_KEY=made-up\n")
        write(self.data + "/stack/compose.yaml", "services: {}\n")
        write(self.data + "/plugins/styles/settings.json", "{}")
        write(self.data + "/sessions.json", "{}")
        write(self.data + "/logs/starboard.log", "log")
        write(self.data + "/posters/a.jpg", "jpg")
        # Each app's settings folder: databases and settings go in, caches, logs and fetched artwork stay out.
        write(self.config + "/reelix/reelix.db", "reelix database")
        write(self.config + "/reelix/MediaCover/1/poster.jpg", "poster")
        write(self.config + "/jellyfin/data/data/jellyfin.db", "jellyfin database")
        write(self.config + "/jellyfin/log/log_1.txt", "log")
        write(self.config + "/jellyfin/cache/images/x", "cache")
        write(self.config + "/qbittorrent/qBittorrent/qBittorrent.conf", "[Preferences]")
        self.calls = []
        hosts = {self.data: "/srv/starboard/data/stack", self.fresh: "/srv/fresh/data/stack"}

        def docker(method, path, body=None, timeout=None, raw=False):
            self.calls.append((method, path))
            if path == "/containers/json":
                return [{"Id": "reelix-id", "Labels": {"com.docker.compose.service": "reelix"},
                         "Mounts": [{"Source": "/srv/stack/config/reelix"}]},
                        {"Id": "starboard-id", "Labels": {"com.docker.compose.service": "starboard"},
                         "Mounts": [{"Source": "/srv/stack/config/starboard"}]}]
            return {}
        for p in (mock.patch.object(fb, "_helper", fake_helper(self.host)), mock.patch.object(containers, "available", lambda: True),
                  mock.patch.object(containers, "docker", docker), mock.patch.object(stack, "host_folder", lambda d: hosts.get(d))):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, keep=fb.KEEP):
        fb.start(self.data, "0.15.0", PASSWORD, "/mnt/backups/starboard", False, site_name="Harbour", keep=keep)
        for _ in range(300):
            s = fb.status(self.data)
            if s.get("state") != "running":
                return s
            time.sleep(0.05)
        self.fail("The backup did not finish")

    def test_make_then_restore_onto_a_fresh_install(self):
        s = self.make()
        self.assertEqual(s["state"], "done", s.get("error"))
        self.assertTrue(re.match(r"^/mnt/backups/starboard/starboard-full-[0-9-]+\.starboard$", s["file"]), s["file"])
        on_disk = self.host + s["file"]
        self.assertTrue(os.path.isfile(on_disk))
        self.assertEqual(oct(os.stat(on_disk).st_mode & 0o777), "0o600")
        self.assertFalse(os.path.exists(self.data + "/" + fb.WORK), "the work folder is tidied away")
        # The running app stopped while its folder was copied, then started again; Starboard itself never stopped.
        self.assertIn(("POST", "/containers/reelix-id/stop?t=30"), self.calls)
        self.assertIn(("POST", "/containers/reelix-id/start"), self.calls)
        self.assertFalse(any("starboard-id" in p for _, p in self.calls))
        # The header is readable without the password, so a new install can list the copies first.
        found = fb.found("/mnt/backups/starboard")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["apps"], ["jellyfin", "qbittorrent", "reelix"])
        self.assertEqual(found[0]["site_name"], "Harbour")
        with open(on_disk, "rb") as f:
            self.assertNotIn(b"made-up-key", f.read(), "the file is encrypted")

        # A wrong password restores nothing.
        os.makedirs(self.fresh)
        with self.assertRaisesRegex(fb.BackupError, "password does not open"):
            fb.restore(self.fresh, s["file"], "another long password", config_dir="/srv/fresh/config")
        self.assertFalse(os.path.exists(self.host + "/srv/fresh/config"))

        # The right one, into a fresh data folder and a fresh settings folder.
        out = fb.restore(self.fresh, s["file"], PASSWORD, config_dir="/srv/fresh/config", puid=os.getuid(), pgid=os.getgid())
        self.assertEqual(out["apps"], ["jellyfin", "qbittorrent", "reelix"])
        self.assertEqual(out["header"]["site_name"], "Harbour")
        cfg = self.host + "/srv/fresh/config"
        with open(cfg + "/reelix/reelix.db", encoding="utf-8") as f:
            self.assertEqual(f.read(), "reelix database")
        self.assertTrue(os.path.isfile(cfg + "/jellyfin/data/data/jellyfin.db"))
        self.assertTrue(os.path.isfile(cfg + "/qbittorrent/qBittorrent/qBittorrent.conf"))
        for gone in ("/reelix/MediaCover/1/poster.jpg", "/jellyfin/log/log_1.txt", "/jellyfin/cache/images/x"):
            self.assertFalse(os.path.exists(cfg + gone), gone)
        for kept in ("/api-keys.json", "/stack/.env", "/stack/compose.yaml", "/plugins/styles/settings.json"):
            self.assertTrue(os.path.isfile(self.fresh + kept), kept)
        for never in ("/sessions.json", "/logs/starboard.log", "/posters/a.jpg", "/config.json", "/" + fb.WORK):
            self.assertFalse(os.path.exists(self.fresh + never), never)
        with open(self.fresh + "/stack/.env", encoding="utf-8") as f:
            self.assertIn("REELIX_KEY=made-up", f.read())
        # Starboard's settings come back through the settings restore, as the set-up does it; the sign-in stays.
        fresh = Config(self.fresh)
        raw = out["settings"]
        backup.restore(fresh, {"format": backup.FORMAT, "schema": raw.get("schema"), "services": raw.get("services") or [],
                               "settings": {k: raw[k] for k in backup.GENERAL_KEYS + backup.OTHER_KEYS if k in raw}})
        self.assertEqual((fresh.data["site_name"], fresh.data["backup_schedule"]), ("Harbour", "weekly"))

    def test_only_the_newest_are_kept(self):
        folder = self.host + "/mnt/backups/starboard"
        os.makedirs(folder)
        old = [f"starboard-full-2026-10-0{n}-030000.starboard" for n in (1, 2, 3)]
        for n, name in enumerate(old):
            write(f"{folder}/{name}", "old")
            os.utime(f"{folder}/{name}", (1_700_000_000 + n, 1_700_000_000 + n))
        write(folder + "/notes.txt", "the person's own file")
        write(folder + "/starboard-full-2026-10-04-030000.starboard.part", "cut off")
        s = self.make(keep=2)
        self.assertEqual(s["state"], "done", s.get("error"))
        left = sorted(os.listdir(folder))
        self.assertEqual(left, sorted([old[2], os.path.basename(s["file"]), "notes.txt"]))

    # DASH-381: each copy is read back after it is written.

    def test_a_new_backup_is_checked(self):
        s = self.make()
        self.assertEqual(s["state"], "done", s.get("error"))
        name = os.path.basename(s["file"])
        mark = fb.checked(self.data)[name]
        self.assertEqual(mark["size"], os.path.getsize(self.host + s["file"]))
        listed = fb.with_checked(self.data, fb.found("/mnt/backups/starboard"))
        self.assertEqual([bool(b["checked"]) for b in listed], [True])
        # A file that changed size since is not the one that was checked.
        with open(self.host + s["file"], "ab") as f:
            f.write(b"x")
        self.assertEqual([b["checked"] for b in fb.with_checked(self.data, fb.found("/mnt/backups/starboard"))], [None])
        self.assertNotIn(fb.CHECKED, [rel for _, rel in fb._starboard_files(self.data, True)], "the marks stay out of backups")

    def damaged_as_written(self, change):
        """Makes one whose copy in the folder is changed straight after it is written, as a failing disk would."""
        real = fake_helper(self.host)

        def helper(script, binds, timeout=0):
            out = real(script, binds, timeout)
            if "cp " in script and ".part" in script:
                folder = self.host + "/mnt/backups/starboard"
                new = max((f for f in os.listdir(folder) if f.endswith(".starboard")), key=lambda f: os.path.getmtime(f"{folder}/{f}"))
                os.chmod(f"{folder}/{new}", 0o600)
                change(f"{folder}/{new}")
            return out
        with mock.patch.object(fb, "_helper", helper):
            return self.make(keep=1)

    def test_a_backup_that_does_not_read_back_is_not_kept(self):
        folder = self.host + "/mnt/backups/starboard"
        os.makedirs(folder)
        write(folder + "/starboard-full-2026-10-01-030000.starboard", "the older one")
        os.utime(folder + "/starboard-full-2026-10-01-030000.starboard", (1_700_000_000, 1_700_000_000))

        def flip_last_byte(path):
            with open(path, "r+b") as f:
                f.seek(-1, os.SEEK_END)
                last = f.read(1)
                f.seek(-1, os.SEEK_END)
                f.write(bytes([last[0] ^ 1]))
        s = self.damaged_as_written(flip_last_byte)
        self.assertEqual(s["state"], "failed")
        self.assertRegex(s["error"], r"did not read back as it was written \(its last part does not open\)")
        left = sorted(os.listdir(folder))
        self.assertEqual(len(left), 2, left)
        self.assertEqual(left[0], "starboard-full-2026-10-01-030000.starboard", "the older one stays although only 1 is kept")
        self.assertTrue(left[1].endswith(".starboard.part"), "the one that did not read back is no backup")
        self.assertEqual(fb.checked(self.data), {})

    def test_a_backup_cut_short_on_the_disk_is_noticed(self):
        def cut(path):
            with open(path, "r+b") as f:
                f.truncate(os.path.getsize(path) - 10)
        s = self.damaged_as_written(cut)
        self.assertEqual(s["state"], "failed")
        self.assertIn("it is not the size that was written", s["error"])

    # DASH-387: restore a full backup on this server.

    def restore_here(self, file, password=PASSWORD, apply=None):
        applied = []
        fb.start_restore(self.data, "0.15.0", file, password, apply or (lambda raw: applied.append(raw) or len(raw.get("services") or [])), "Harbour")
        for _ in range(400):
            s = fb.restore_status(self.data)
            if s.get("state") != "running":
                return s, applied
            time.sleep(0.05)
        self.fail("The restore did not finish")

    def test_restore_on_this_server(self):
        first = self.make(keep=1)
        self.assertEqual(first["state"], "done", first.get("error"))
        # Since the backup: Reelix's database changed and was not closed cleanly, a plug-in setting changed, an app was added.
        write(self.config + "/reelix/reelix.db", "reelix database, changed since")
        write(self.config + "/reelix/reelix.db-wal", "pages of the newer database")
        write(self.config + "/reelix/notes-journal", "a file of the person's own that only ends the same")
        write(self.config + "/reelix/MediaCover/1/poster.jpg", "poster")
        write(self.data + "/plugins/styles/settings.json", '{"changed": true}')
        write(self.config + "/kavita/kavita.db", "added after the backup")
        time.sleep(1.1)  # file names are to the second
        self.calls.clear()

        s, applied = self.restore_here(first["file"])
        self.assertEqual(s["state"], "done", s.get("error"))
        # A full backup of how things were was made first, and the one being restored was not removed to make room.
        folder = self.host + "/mnt/backups/starboard"
        self.assertEqual(len([f for f in os.listdir(folder) if f.endswith(".starboard")]), 2)
        self.assertTrue(os.path.isfile(self.host + s["safety"]))
        self.assertNotEqual(s["safety"], first["file"])
        # Reelix stopped (twice: for the copy, then for the restore) and runs again; Starboard never stopped.
        self.assertEqual(self.calls.count(("POST", "/containers/reelix-id/stop?t=30")), 2)
        self.assertEqual(self.calls.count(("POST", "/containers/reelix-id/start")), 2)
        self.assertEqual(self.calls[-1], ("POST", "/containers/reelix-id/start"))
        self.assertFalse(any("starboard-id" in p for _, p in self.calls))
        self.assertEqual(s["stopped"], [])
        # The apps' settings are as they were in the backup; what was not in it is left alone.
        with open(self.config + "/reelix/reelix.db", encoding="utf-8") as f:
            self.assertEqual(f.read(), "reelix database")
        self.assertFalse(os.path.exists(self.config + "/reelix/reelix.db-wal"), "never played into the older database")
        self.assertTrue(os.path.exists(self.config + "/reelix/notes-journal"))
        self.assertTrue(os.path.exists(self.config + "/reelix/MediaCover/1/poster.jpg"))
        self.assertTrue(os.path.exists(self.config + "/kavita/kavita.db"))
        with open(self.data + "/plugins/styles/settings.json", encoding="utf-8") as f:
            self.assertEqual(f.read(), "{}")
        self.assertTrue(os.path.isfile(self.data + "/sessions.json"), "the sign-ins stay")
        self.assertEqual(applied[0]["site_name"], "Harbour")
        self.assertEqual(s["apps"], ["jellyfin", "qbittorrent", "reelix"])
        self.assertFalse(os.path.exists(self.data + "/" + fb.WORK))
        # The copy made first restores too, and brings the changed state back.
        s2, _ = self.restore_here(s["safety"])
        self.assertEqual(s2["state"], "done", s2.get("error"))
        with open(self.config + "/reelix/reelix.db", encoding="utf-8") as f:
            self.assertEqual(f.read(), "reelix database, changed since")

    def test_a_wrong_password_changes_nothing(self):
        first = self.make()
        write(self.config + "/reelix/reelix.db", "changed since")
        self.calls.clear()
        with self.assertRaisesRegex(fb.BackupError, "password does not open"):
            fb.start_restore(self.data, "0.15.0", first["file"], "another long password", lambda raw: 0)
        self.assertEqual(self.calls, [], "nothing stopped")
        self.assertEqual(len(os.listdir(self.host + "/mnt/backups/starboard")), 1, "no copy made")
        self.assertEqual(fb.restore_status(self.data), {"state": "none"})
        self.assertFalse(fb._restoring.locked())
        with open(self.config + "/reelix/reelix.db", encoding="utf-8") as f:
            self.assertEqual(f.read(), "changed since")

    def test_a_damaged_backup_changes_nothing_and_the_apps_start_again(self):
        first = self.make()
        with open(self.host + first["file"], "r+b") as f:  # cut inside its last part: the first part still opens
            f.truncate(os.path.getsize(self.host + first["file"]) - 10)
        with open(self.host + first["file"], "rb") as f:
            small = len(fb.read_header(f)[1]) + fb.CHUNK > os.path.getsize(self.host + first["file"])
        write(self.config + "/reelix/reelix.db", "changed since")
        write(self.data + "/plugins/styles/settings.json", '{"changed": true}')
        time.sleep(1.1)
        if small:  # one part only: the password check itself refuses it
            with self.assertRaisesRegex(fb.BackupError, "cut short|damaged|does not open"):
                fb.start_restore(self.data, "0.15.0", first["file"], PASSWORD, lambda raw: 0)
        else:
            s, applied = self.restore_here(first["file"])
            self.assertEqual(s["state"], "failed")
            self.assertEqual(applied, [])
            self.assertEqual(self.calls[-1], ("POST", "/containers/reelix-id/start"))
        with open(self.config + "/reelix/reelix.db", encoding="utf-8") as f:
            self.assertEqual(f.read(), "changed since")
        with open(self.data + "/plugins/styles/settings.json", encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"changed": true}')
        self.assertFalse(fb._restoring.locked())

    def test_a_backup_cut_after_several_parts_changes_nothing(self):
        write(self.config + "/jellyfin/data/data/big.bin", "")
        with open(self.config + "/jellyfin/data/data/big.bin", "wb") as f:
            f.write(os.urandom(3 * fb.CHUNK))  # does not compress, so the backup has several parts
        first = self.make()
        self.assertEqual(first["state"], "done", first.get("error"))
        with open(self.host + first["file"], "r+b") as f:
            f.truncate(os.path.getsize(self.host + first["file"]) - 10)
        write(self.config + "/reelix/reelix.db", "changed since")
        write(self.data + "/plugins/styles/settings.json", '{"changed": true}')
        time.sleep(1.1)
        self.calls.clear()
        s, applied = self.restore_here(first["file"])
        self.assertEqual(s["state"], "failed")
        self.assertIn("cut short", s["error"])
        self.assertEqual(applied, [])
        self.assertTrue(os.path.isfile(self.host + s["safety"]), "the copy of how things were is there all the same")
        self.assertEqual(self.calls[-1], ("POST", "/containers/reelix-id/start"), "the apps run again")
        with open(self.config + "/reelix/reelix.db", encoding="utf-8") as f:
            self.assertEqual(f.read(), "changed since")
        with open(self.data + "/plugins/styles/settings.json", encoding="utf-8") as f:
            self.assertEqual(f.read(), '{"changed": true}')

    def test_a_backup_from_another_layout_or_a_newer_starboard_is_refused(self):
        first = self.make()
        write(self.data + "/stack/.env", f"CONFIG_DIR=/srv/elsewhere/config\nDATA_DIR=/mnt/media\nPUID={os.getuid()}\nPGID={os.getgid()}\n")
        with self.assertRaisesRegex(fb.BackupError, "keeps its apps' settings in /srv/stack/config"):
            fb.start_restore(self.data, "0.15.0", first["file"], PASSWORD, lambda raw: 0)
        write(self.data + "/stack/.env", f"CONFIG_DIR=/srv/stack/config\nDATA_DIR=/mnt/media\nPUID={os.getuid()}\nPGID={os.getgid()}\n")
        with self.assertRaisesRegex(fb.BackupError, "newer than this one"):
            fb.start_restore(self.data, "0.14.9", first["file"], PASSWORD, lambda raw: 0)
        self.assertFalse(fb._restoring.locked())

    def test_no_backup_is_made_while_one_is_restored(self):
        self.assertTrue(fb._restoring.acquire(blocking=False))
        try:
            with self.assertRaisesRegex(fb.BackupError, "is being restored"):
                fb.start(self.data, "0.15.0", PASSWORD, "/mnt/backups/starboard", False)
        finally:
            fb._restoring.release()

    def test_apps_a_restore_stopped_start_again_when_starboard_starts(self):
        fb._tell(self.data, state="running", step="Putting the backup back", stopped=["reelix-id"])
        self.calls.clear()
        self.assertEqual(fb.start_left_stopped(self.data), ["reelix-id"])
        self.assertEqual(self.calls, [("POST", "/containers/reelix-id/start")])
        now = fb.restore_status(self.data)
        self.assertEqual((now["state"], now["stopped"]), ("failed", []))
        self.assertIn("Restore it again", now["error"])


class WhichDisk(unittest.TestCase):
    DRIVES = [{"mount": "/mnt/disk1", "model": "WDC WD40EFRX", "label": "", "device": "sdb1", "size": 4000},
              {"mount": "/mnt/disk2", "model": "ST3000VN007", "label": "Backups", "device": "sdc1", "size": 8000}]

    def test_a_folder_on_another_disk(self):
        d = fb.disk_of("", "/mnt/disk2/backups", self.DRIVES)
        self.assertEqual((d["system"], d["name"], d["mount"]), (False, "Backups", "/mnt/disk2"))
        self.assertFalse(fb.disk_of("", "/mnt/pool/backups", self.DRIVES)["system"])

    def test_a_folder_on_the_system_disk(self):
        d = fb.disk_of("", "/srv/media/backups", self.DRIVES)
        self.assertEqual((d["system"], d["others"]), (True, 2))
        self.assertTrue(fb.disk_of("", "/mnt/disk10/x", self.DRIVES)["system"], "a name that only starts the same is not that disk")
        self.assertEqual(fb.disk_of("", "/srv/x", [])["others"], 0)

    def test_unknown_without_a_drive_list(self):
        self.assertIsNone(fb.disk_of("", "/mnt/disk1", None))
        self.assertIsNone(fb.disk_of("", "relative/folder", self.DRIVES))

    def test_the_default_folder_is_on_another_disk(self):
        with tempfile.TemporaryDirectory() as d:
            write(d + "/stack/.env", "DATA_DIR=/srv/media\n")
            with mock.patch.object(fb, "_drives", lambda _: self.DRIVES):
                self.assertEqual(fb.default_folder(d), "/mnt/disk2/backups/starboard", "the biggest other disk")
            with mock.patch.object(fb, "_drives", lambda _: []):
                self.assertEqual(fb.default_folder(d), "/srv/media/backups/starboard", "only the system disk: the media folder")
            with mock.patch.object(fb, "_drives", lambda _: None):
                self.assertEqual(fb.default_folder(d), "/srv/media/backups/starboard")
            write(d + "/stack/.env", "DATA_DIR=/mnt/disk1/media\n")
            with mock.patch.object(fb, "_drives", lambda _: self.DRIVES):
                self.assertEqual(fb.default_folder(d), "/mnt/disk1/media/backups/starboard", "the media is on another disk already")


if __name__ == "__main__":
    unittest.main()
