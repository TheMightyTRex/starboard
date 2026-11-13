"""Copies off this computer (DASH-380): what the page may save, what never comes back to it, and the scripts the
helper runs. Docker is never called here: the helper is replaced by one that records what it was asked to do.
tools/try-backup-copies.py runs the real thing against scratch folders and local stand-ins."""
import base64
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import backup_copies as bc, folders, full_backup


class Saving(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.status = mock.patch.object(full_backup, "default_folder", lambda data_dir: "/mnt/disk2/backups/starboard")
        self.status.start()

    def tearDown(self):
        self.status.stop()

    def test_starts_off_with_five_kept(self):
        self.assertEqual((bc.settings(self.d)["kind"], bc.settings(self.d)["keep"]), ("off", 5))

    def test_another_disk(self):
        new, _ = bc.check(self.d, {"kind": "disk", "folder": "/mnt/usb/starboard/", "keep": "3"})
        self.assertEqual((new["folder"], new["keep"]), ("/mnt/usb/starboard", 3))
        with self.assertRaisesRegex(ValueError, "folder the full backups are made in"):
            bc.check(self.d, {"kind": "disk", "folder": "/mnt/disk2/backups/starboard"})
        with self.assertRaisesRegex(ValueError, "Choose a folder under"):
            bc.check(self.d, {"kind": "disk", "folder": "/etc/backups"})
        with self.assertRaisesRegex(ValueError, "1 to 50"):
            bc.check(self.d, {"kind": "disk", "folder": "/mnt/usb", "keep": 0})

    def test_shares(self):
        new, sec = bc.check(self.d, {"kind": "smb", "smb": "\\\\nas.home\\backups\\starboard", "smb_user": "sam", "smb_password": "pa,ss"})
        self.assertEqual((new["smb"], new["smb_user"], sec["smb_password"]), ("//nas.home/backups/starboard", "sam", "pa,ss"))
        with self.assertRaisesRegex(ValueError, "//computer/share"):
            bc.check(self.d, {"kind": "smb", "smb": "nas.home/backups"})
        new, _ = bc.check(self.d, {"kind": "nfs", "nfs": "192.168.1.20:/export/backups"})
        self.assertEqual(new["nfs"], "192.168.1.20:/export/backups")
        with self.assertRaisesRegex(ValueError, "computer:/folder"):
            bc.check(self.d, {"kind": "nfs", "nfs": "//192.168.1.20/backups"})

    def test_rclone_needs_its_remote_in_the_config(self):
        conf = "[mycloud]\ntype = b2\naccount = made-up\nkey = made-up-key\n"
        new, sec = bc.check(self.d, {"kind": "rclone", "remote": "mycloud:starboard", "rclone_config": conf})
        self.assertEqual((new["remote"], sec["rclone_config"].strip()), ("mycloud:starboard", conf.strip()))
        with self.assertRaisesRegex(ValueError, r"starts with \[other\]"):
            bc.check(self.d, {"kind": "rclone", "remote": "other:x", "rclone_config": conf})
        bc.save(self.d, new, sec)
        # an empty config box keeps the one already kept
        new2, sec2 = bc.check(self.d, {"kind": "rclone", "remote": "mycloud:elsewhere", "rclone_config": ""})
        self.assertEqual(sec2["rclone_config"], sec["rclone_config"])

    def test_secrets_never_go_back_to_the_page_and_are_private(self):
        new, sec = bc.check(self.d, {"kind": "smb", "smb": "//nas/backups", "smb_user": "sam", "smb_password": "made-up-share-password"})
        bc.save(self.d, new, sec)
        page = json.dumps(bc.public(self.d))
        self.assertNotIn("made-up-share-password", page)
        self.assertTrue(bc.public(self.d)["smb_password_set"])
        self.assertEqual(os.stat(os.path.join(self.d, bc.SECRET)).st_mode & 0o777, 0o600)

    def test_secrets_and_status_are_never_in_a_full_backup(self):
        for name in (bc.SECRET, bc.STATUS, bc.WORK + "/rclone.conf", bc.SETTINGS):
            path = os.path.join(self.d, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("{}")
        rels = [rel for _, rel in full_backup._starboard_files(self.d, False)]
        self.assertEqual(rels, [bc.SETTINGS])  # where copies go is kept; its passwords are not

    def test_forget_keeps_the_place_but_not_the_passwords(self):
        new, sec = bc.check(self.d, {"kind": "smb", "smb": "//nas/backups", "smb_user": "sam", "smb_password": "x"})
        bc.save(self.d, new, sec)
        bc.forget(self.d)
        self.assertEqual((bc.settings(self.d)["kind"], bc.secrets(self.d)["smb_password"]), ("off", ""))


class Running(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.calls = []

        def helper(script, binds, image=None, network="none", volumes=(), timeout=7200):
            self.calls.append({"script": script, "binds": list(binds), "image": image, "network": network, "volumes": list(volumes)})
            return 0, "COUNT 3\n"
        self.patches = [mock.patch.object(bc, "_helper", helper),
                        mock.patch("starboard.stack.env_values", lambda d: {"PUID": "1000", "PGID": "1000"}),
                        mock.patch("starboard.stack.host_folder", lambda d: "/srv/starboard/data/stack"),
                        mock.patch.object(bc, "_address", lambda host: "192.0.2.20"),
                        mock.patch("starboard.containers.docker", self.docker)]
        for p in self.patches:
            p.start()
        self.volumes = []

    def docker(self, method, path, body=None, **k):
        self.volumes.append((method, path, body))
        return {}

    def tearDown(self):
        for p in self.patches:
            p.stop()

    SOURCE = "/mnt/disk2/backups/starboard/starboard-full-2026-11-13-030000.starboard"

    def test_disk_copy_checks_the_size_and_prunes_only_backups(self):
        bc.save(self.d, {**bc.settings(self.d), "kind": "disk", "folder": "/media/usb/copies", "keep": 4}, bc.secrets(self.d))
        said = bc._run(self.d, self.SOURCE)
        call = self.calls[0]
        self.assertEqual(call["network"], "none")
        self.assertIn("/mnt:/s:ro", call["binds"])
        self.assertIn("/media:/t", call["binds"])
        self.assertIn("wc -c", call["script"])
        self.assertIn("tail -n +5", call["script"])
        self.assertIn("grep -E '^starboard-full-[0-9-]+(-pictures)?\\.starboard$'", call["script"])
        self.assertEqual(said, "Copied to /media/usb/copies, which keeps 3 full backups")

    def test_smb_is_a_short_lived_volume_let_go_after(self):
        bc.save(self.d, {**bc.settings(self.d), "kind": "smb", "smb": "//nas.home/backups/starboard", "smb_user": "sam"},
                {"smb_password": "a,b", "rclone_config": ""})
        bc._run(self.d, self.SOURCE)
        create = next(b for m, p, b in self.volumes if p == "/volumes/create")
        self.assertEqual(create["DriverOpts"]["type"], "cifs")
        self.assertEqual(create["DriverOpts"]["device"], "//192.0.2.20/backups/starboard")
        self.assertIn("password=a,,b", create["DriverOpts"]["o"])
        self.assertTrue(any(m == "DELETE" and p == f"/volumes/{create['Name']}" for m, p, _ in self.volumes))
        self.assertEqual(self.calls[0]["volumes"], [create["Name"]])
        self.assertEqual(self.calls[0]["network"], "none")

    def test_rclone_runs_in_its_own_image_with_network(self):
        conf = "[mycloud]\ntype = b2\n"
        bc.save(self.d, {**bc.settings(self.d), "kind": "rclone", "remote": "mycloud:starboard"}, {"smb_password": "", "rclone_config": conf})
        bc._run(self.d, self.SOURCE)
        call = self.calls[0]
        self.assertEqual((call["image"], call["network"]), (bc.RCLONE_IMAGE, "bridge"))
        self.assertIn("copyto '/s/disk2/backups/starboard/starboard-full-2026-11-13-030000.starboard' 'mycloud:starboard/starboard-full-2026-11-13-030000.starboard'", call["script"])
        self.assertIn("/srv/starboard/data/backup-copy-work:/c", call["binds"])
        self.assertFalse(os.path.exists(os.path.join(self.d, bc.WORK, "rclone.conf")))  # the short-lived copy is gone

    def test_refuses_anything_but_a_full_backup(self):
        bc.save(self.d, {**bc.settings(self.d), "kind": "disk", "folder": "/media/usb"}, bc.secrets(self.d))
        with self.assertRaisesRegex(bc.CopyError, "not a Starboard full backup"):
            bc._run(self.d, "/mnt/disk2/backups/other.zip")

    def test_after_a_backup_a_failed_copy_is_said_never_raised(self):
        bc.save(self.d, {**bc.settings(self.d), "kind": "disk", "folder": "/media/usb"}, bc.secrets(self.d))
        with mock.patch.object(bc, "_helper", lambda *a, **k: (1, "cp: can't create '/t/usb/x': Permission denied")), \
                mock.patch("starboard.logs.event"):
            bc.after_full(self.d, self.SOURCE)
        s = bc.status(self.d)
        self.assertEqual(s["state"], "failed")
        self.assertIn("not allowed to write", s["error"])

    def test_off_does_nothing(self):
        bc.after_full(self.d, self.SOURCE)
        self.assertEqual(self.calls, [])

    def test_plain_words(self):
        s = {"kind": "smb", "smb": "//nas/b", "folder": "", "nfs": "", "remote": ""}
        self.assertIn("is full", bc._plain("cp: write error: No space left on device", s))
        self.assertIn("did not answer", bc._plain("mount error: Host is down", s))


class Pattern(unittest.TestCase):
    def test_backup_names_match_full_backups_only(self):
        import re
        rx = re.compile(bc.BACKUP_GLOB)
        self.assertTrue(rx.match("starboard-full-2026-11-13-030000.starboard"))
        self.assertTrue(rx.match("starboard-full-2026-11-13-030000-pictures.starboard"))
        self.assertFalse(rx.match("starboard-full-2026-11-13-030000.starboard.part"))
        self.assertFalse(rx.match("holiday-photos.zip"))
        self.assertTrue(folders.allowed("/media/usb"))
        self.assertTrue(base64)


if __name__ == "__main__":
    unittest.main()
