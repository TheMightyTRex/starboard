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
