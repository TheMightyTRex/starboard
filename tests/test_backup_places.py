"""Several backup places (26 November 2026): the old single place moves over without loss, each place has its own switch,
keep count and status, one failing never stops the others, a backup is safe only when every place that is on has read it
back, and the server's settings zip is only ever sent encrypted. Docker is never called: the helper is replaced."""
import json
import os
import pathlib
import stat
import tempfile
import unittest
from unittest import mock

from starboard import backup_copies as bc, cloud_connect, full_backup, settings_zip as sz

SOURCE = "/mnt/disk2/backups/starboard/starboard-full-2026-11-13-030000.starboard"


def write(d, name, value):
    with open(os.path.join(d, name), "w", encoding="utf-8") as f:
        json.dump(value, f)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.calls = []
        self.bad = set()

        def helper(script, binds, image=None, network="none", volumes=(), timeout=7200):
            self.calls.append({"script": script, "binds": list(binds), "image": image, "network": network})
            if any(f in script for f in self.bad) or any(f in " ".join(binds) for f in self.bad):
                return 1, "Permission denied"
            return 0, "COUNT 2\n"
        self.patches = [mock.patch.object(bc, "_helper", helper),
                        mock.patch.object(full_backup, "default_folder", lambda data_dir: "/mnt/disk2/backups/starboard"),
                        mock.patch("starboard.stack.env_values", lambda d: {"PUID": "1000", "PGID": "1000"}),
                        mock.patch("starboard.stack.host_folder", lambda d: "/srv/starboard/data/stack"),
                        mock.patch("starboard.containers.docker", lambda *a, **k: {}),
                        mock.patch("starboard.logs.event")]
        for p in self.patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])

    def add(self, kind="disk", **kw):
        new, sec = bc.check(self.d, {"id": "new", "kind": kind, **({"folder": "/media/usb/copies"} if kind == "disk" else {}), **kw})
        return bc.save(self.d, new, sec)["id"]


class Migration(Base):
    def test_the_old_single_place_becomes_the_first_without_losing_anything(self):
        write(self.d, bc.SETTINGS, {"kind": "rclone", "remote": "starboard-cloud:starboard-backups", "keep": 5, "service": "drive",
                                    "signin_way": "browser", "detailed_log": True})
        write(self.d, bc.SECRET, {"smb_password": "", "rclone_config": "[starboard-cloud]\ntype = drive\ntoken = {made-up}\n"})
        write(self.d, bc.STATUS, {"state": "done", "file": SOURCE, "said": "Copied"})
        write(self.d, bc.TESTED, {"ok": True, "where": "starboard-cloud:starboard-backups", "kind": "rclone"})
        places = bc.destinations(self.d)
        self.assertEqual([(p["id"], p["kind"], p["enabled"], p["service"], p["keep"]) for p in places], [("main", "rclone", True, "drive", 5)])
        self.assertIn("token = {made-up}", bc.secrets(self.d)["rclone_config"])
        self.assertEqual(bc.status(self.d)["state"], "done")
        self.assertTrue(bc.tested(self.d)["ok"])
        self.assertTrue(bc.settings(self.d)["detailed_log"])
        # adding a second place keeps the first one's sign-in and last copy, and the second has its own
        second = self.add("disk")
        self.assertIn("token = {made-up}", bc.secrets(self.d, "main")["rclone_config"])
        self.assertEqual(bc.secrets(self.d, second)["rclone_config"], "")
        self.assertEqual(bc.status(self.d, "main")["state"], "done")
        self.assertEqual(bc.status(self.d, second)["state"], "none")
        self.assertEqual([p["id"] for p in bc.destinations(self.d)], ["main", second])
        self.assertTrue(bc.settings(self.d)["detailed_log"])

    def test_the_first_place_is_what_the_old_calls_mean(self):
        write(self.d, bc.SETTINGS, {"kind": "disk", "folder": "/media/usb/copies", "keep": 3})
        self.assertEqual((bc.settings(self.d)["kind"], bc.public(self.d)["destinations"][0]["keep"]), ("disk", 3))

    def test_none_is_off(self):
        self.assertEqual((bc.settings(self.d)["kind"], bc.destinations(self.d)), ("off", []))


class Places(Base):
    def test_each_place_has_its_own_keep_switch_and_words(self):
        a, b = self.add("disk", keep=3), self.add("nfs", nfs="192.168.1.20:/export/b", keep=7)
        self.assertEqual((bc.settings(self.d, a)["keep"], bc.settings(self.d, b)["keep"]), (3, 7))
        bc.set_enabled(self.d, b, False)
        got = {p["id"]: p for p in bc.public(self.d)["destinations"]}
        self.assertEqual((got[a]["state_word"], got[a]["shape"]), ("Not copied yet", "circle"))
        self.assertEqual((got[b]["state_word"], got[b]["shape"]), ("Deactivated", "minus"))

    def test_up_to_eight_places(self):
        for _ in range(bc.MAX_PLACES):
            self.add("disk")
        with self.assertRaisesRegex(ValueError, "up to 8"):
            bc.check(self.d, {"id": "new", "kind": "disk", "folder": "/media/usb"})

    def test_one_failing_never_stops_the_others_and_the_alert_says_which(self):
        a, b, c = self.add("disk", folder="/media/bad/x", name="Pool disk"), self.add("nfs", nfs="192.168.1.20:/export/b", name="The NAS"), self.add("disk", folder="/media/ok/x")
        self.bad = {"/bad/x"}
        with mock.patch("starboard.logs.event") as ev:
            bc.after_full(self.d, SOURCE)
        self.assertEqual([bc.status(self.d, i)["state"] for i in (a, b, c)], ["failed", "done", "done"])
        said = [c.args[2] for c in ev.call_args_list if c.args[0] == "error"]
        self.assertTrue(any("Pool disk" in s and "1 of 3" in s for s in said), said)
        self.assertEqual([f["title"] for f in bc.failures(self.d)], ["Pool disk"])

    def test_safe_only_when_every_place_that_is_on_read_it_back(self):
        a, b = self.add("disk"), self.add("nfs", nfs="192.168.1.20:/export/b")
        with mock.patch.object(bc, "newest", lambda d: SOURCE):
            self.assertFalse(bc.safe(self.d)["safe"])
            bc._copy(self.d, SOURCE, a)
            s = bc.safe(self.d)
            self.assertFalse(s["safe"])
            self.assertIn("has not read back", s["words"])
            bc._copy(self.d, SOURCE, b)
            self.assertTrue(bc.safe(self.d)["safe"])
            bc.set_enabled(self.d, b, False)  # a place that is off does not count
            self.assertTrue(bc.safe(self.d)["safe"])
            self.bad = {"/usb/copies"}
            bc._copy(self.d, SOURCE, a)
            self.assertFalse(bc.safe(self.d)["safe"])

    def test_a_cloud_copy_is_read_back_by_size(self):
        write(self.d, bc.SETTINGS, {"destinations": [{"id": "x", "kind": "rclone", "remote": "mycloud:b", "keep": 2}]})
        write(self.d, bc.SECRET, {"items": {"x": {"rclone_config": "[mycloud]\ntype = b2\n"}}})
        bc._run(self.d, SOURCE, dest="x")
        self.assertIn("lsf --format s", self.calls[0]["script"])
        self.assertIn("wc -c", self.calls[0]["script"])

    def test_removing_one_removes_its_secrets_only(self):
        a = self.add("smb", smb="//nas/b", smb_user="sam", smb_password="made-up-password")
        b = self.add("smb", smb="//nas/c", smb_user="sam", smb_password="other-password")
        bc.forget(self.d, a)
        self.assertEqual([p["id"] for p in bc.destinations(self.d)], [b])
        self.assertEqual(bc.secrets(self.d, b)["smb_password"], "other-password")
        self.assertNotIn("made-up-password", pathlib.Path(self.d, bc.SECRET).read_text())

    def test_secrets_stay_private_and_out_of_the_page(self):
        a = self.add("smb", smb="//nas/b", smb_user="sam", smb_password="made-up-password")
        self.assertNotIn("made-up-password", json.dumps(bc.public(self.d)))
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.d, bc.SECRET)).st_mode), 0o600)
        self.assertTrue(bc.public(self.d)["destinations"][0]["smb_password_set"])
        self.assertTrue(a)

    def test_copy_now_to_every_place_that_is_on(self):
        a, b = self.add("disk"), self.add("nfs", nfs="192.168.1.20:/export/b")
        bc.set_enabled(self.d, b, False)
        done = []
        with mock.patch("starboard.containers.available", lambda: True), mock.patch.object(bc, "newest", lambda d: SOURCE), \
                mock.patch.object(bc, "_copy", lambda d, f, dest=None: done.append(dest)), \
                mock.patch("threading.Thread", lambda target, **k: mock.Mock(start=target)):
            bc.copy_now(self.d)
        self.assertEqual(done, [a])


class Names(Base):
    def test_each_connection_has_its_own_remote_name(self):
        self.assertEqual(cloud_connect.remote_name(self.d, "drive"), "starboard-cloud")
        write(self.d, bc.SETTINGS, {"destinations": [{"id": "x", "kind": "rclone", "remote": "starboard-cloud:b", "service": "drive"}]})
        self.assertEqual(cloud_connect.remote_name(self.d, "onedrive"), "starboard-onedrive")
        self.assertEqual(cloud_connect.remote_name(self.d, "drive", "x"), "starboard-cloud")  # signing in again keeps the name
        bc.save(self.d, {"id": "y", "kind": "rclone", "remote": "starboard-onedrive:b", "service": "onedrive"}, {"rclone_config": "[starboard-onedrive]\n"})
        self.assertEqual(cloud_connect.remote_name(self.d, "onedrive"), "starboard-onedrive-2")
        self.assertEqual(cloud_connect._section([("type", "drive")], "starboard-onedrive"), "[starboard-onedrive]\ntype = drive\n")


class SettingsZip(Base):
    ZIP = "server-settings-2026-11-26.zip"

    def setUp(self):
        super().setUp()
        self.folder = tempfile.mkdtemp()
        with open(os.path.join(self.folder, self.ZIP), "wb") as f:
            f.write(b"zip")
        for p in (mock.patch("starboard.backup.backup_dir", lambda: self.folder), mock.patch.object(sz, "_host_of", lambda p: "/home/x/jellyfin/backups"),
                  mock.patch("starboard.containers.available", lambda: True)):
            p.start()
            self.addCleanup(p.stop)
        self.seen = []

    def run_all(self):
        with mock.patch("threading.Thread", lambda target, args=(), **k: mock.Mock(start=lambda: target(*args))):
            return sz.start(self.d, self.ZIP)

    def test_never_without_a_key(self):
        self.add("disk")
        with self.assertRaisesRegex(sz.ZipError, "never sent without being encrypted"):
            sz.start(self.d, self.ZIP)
        self.assertEqual(self.calls, [])

    def test_the_key_is_private_shown_once_and_not_replaced_by_accident(self):
        card = sz.make_key(self.d)
        self.assertIn("rclone config create", card["text"])
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.d, sz.KEY_FILE)).st_mode), 0o600)
        self.assertNotIn(card["password"], json.dumps(sz.overview(self.d)))
        with self.assertRaisesRegex(sz.ZipError, "kept already"):
            sz.make_key(self.d)
        self.assertIn(sz.KEY_FILE, full_backup.NEVER_BACK)

    def test_only_a_server_settings_zip_in_the_server_folder(self):
        sz.make_key(self.d)
        self.add("disk")
        for bad in ("../x.zip", "server-settings-2026-11-26.zip.enc", "notes.zip", "server-settings-2026-11-27.zip"):
            with self.assertRaises(sz.ZipError):
                sz.start(self.d, bad)

    def test_every_place_gets_it_encrypted_and_nothing_goes_plain(self):
        sz.make_key(self.d)
        a, b = self.add("disk", keep_settings=3), self.add("disk", folder="/media/other/x")
        write(self.d, bc.SETTINGS, {"destinations": bc.destinations(self.d) + [
            {"id": "cl", "kind": "rclone", "remote": "starboard-cloud:starboard-backups", "service": "drive", "keep": 5}]})
        write(self.d, bc.SECRET, {"items": {"cl": {"rclone_config": "[starboard-cloud]\ntype = drive\n"}}})
        got = self.run_all()
        self.assertEqual([r["state"] for r in got["places"]], ["done", "done", "done"])
        self.assertEqual(len(self.calls), 3)
        for c in self.calls:
            self.assertEqual(c["image"], bc.RCLONE_IMAGE)
            self.assertIn(":crypt,remote=", c["script"])
            self.assertIn("filename_encryption=off", c["script"])
            self.assertIn("cryptcheck", c["script"])  # read back by checksum
            self.assertNotIn("/s/" + self.ZIP + " \"/t", c["script"])
            self.assertNotIn(sz._read_key(self.d)["password"], c["script"])  # the phrases are never on the command line
        self.assertEqual([c["network"] for c in self.calls], ["none", "none", "bridge"])
        self.assertIn("tail -n +4", self.calls[0]["script"])  # its own keep count for the zips
        self.assertIn("tail -n +3", self.calls[1]["script"])  # the default of 2
        self.assertTrue(a and b)

    def test_key_files_are_removed_and_one_failing_never_stops_the_others(self):
        sz.make_key(self.d)
        self.add("disk", folder="/media/bad/x", name="Pool disk")
        self.add("disk", folder="/media/ok/x")
        self.bad = {"/bad/x"}
        got = self.run_all()
        self.assertEqual([r["state"] for r in got["places"]], ["failed", "done"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.d, bc.WORK))), [])
        self.assertIn("not allowed to write", got["places"][0]["error"])

    def test_never_in_a_full_backup(self):
        self.assertIn(sz.KEY_FILE, full_backup.COPY_SKIP)
        self.assertIn(sz.STATUS, full_backup.COPY_SKIP)


if __name__ == "__main__":
    unittest.main()
