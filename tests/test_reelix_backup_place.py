"""Where Reelix keeps its backups (DASH-386): the one line of config.toml, which disk each choice is on, and moving the
backups already made. Docker is stood in for: nothing real is read or changed."""
import io
import tarfile
import tomllib
import unittest
from unittest import mock

from starboard import containers, full_backup, reelix_backup_place as place

TEMPLATE = """# Reelix bootstrap configuration.

[server]
# port = 7700

[paths]
# backup_dir = "<data_dir>/backups"
# log_dir = "<data_dir>/logs"

[security]
# secret_key_file = "<data_dir>/secret.key"
"""
DRIVES = [{"mount": "/mnt/disk1", "model": "WDC WD40EFRX", "label": "", "device": "sdb1", "size": 4000}]


class OneLine(unittest.TestCase):
    def test_set_change_and_take_out(self):
        once = place.with_backup_dir(TEMPLATE, "/data/backups/reelix")
        self.assertEqual(tomllib.loads(once)["paths"], {"backup_dir": "/data/backups/reelix"})
        self.assertEqual(once.replace('backup_dir = "/data/backups/reelix"\n', ""), TEMPLATE, "only that line is new")
        self.assertEqual(place.backup_dir_in(once), "/data/backups/reelix")
        self.assertEqual(place.with_backup_dir(once, "/data/backups/reelix"), once, "the same again changes nothing")
        self.assertEqual(place.with_backup_dir(once, None), TEMPLATE)
        self.assertIsNone(place.backup_dir_in(TEMPLATE), "a commented line is not a setting")

    def test_other_tables_and_files(self):
        other = '[database]\nbackup_dir = "not ours"\n'
        out = place.with_backup_dir(other, "/data/backups/reelix")
        self.assertEqual(tomllib.loads(out), {"database": {"backup_dir": "not ours"}, "paths": {"backup_dir": "/data/backups/reelix"}})
        self.assertEqual(tomllib.loads(place.with_backup_dir("", "/data/backups/reelix")), {"paths": {"backup_dir": "/data/backups/reelix"}})
        self.assertEqual(place.with_backup_dir("", None), "")
        twice = "[paths]\nbackup_dir = '/a' # mine\nlog_dir = \"/l\"\n"
        self.assertEqual(place.backup_dir_in(twice), "/a")
        self.assertEqual(tomllib.loads(place.with_backup_dir(twice, "/data/backups/reelix"))["paths"], {"backup_dir": "/data/backups/reelix", "log_dir": "/l"})


class Docker(unittest.TestCase):
    """A made-up Reelix container: its config.toml, its two folders, and the commands run in it."""

    def setUp(self):
        self.text, self.ran, self.put = TEMPLATE, [], []
        self.data_source = "/mnt/disk1/media"

        def docker(method, path, body=None, raw=False, timeout=30):
            if path == "/containers/reelix/json":
                return {"Config": {"Env": ["PUID=1001", "PGID=1002"]},
                        "Mounts": [{"Destination": "/config", "Source": "/srv/stack/config/reelix"}, {"Destination": "/data", "Source": self.data_source},
                                   {"Destination": "/tmp", "Source": "/x"}]}
            if path.startswith("/containers/reelix/archive"):
                if self.text is None:
                    raise containers.DockerError("Docker answered 404: no such file")
                buf = io.BytesIO()
                with tarfile.open(fileobj=buf, mode="w") as tar:
                    info = tarfile.TarInfo("config.toml")
                    info.size, info.mode = len(self.text.encode()), 0o640
                    tar.addfile(info, io.BytesIO(self.text.encode()))
                return buf.getvalue()
            raise AssertionError(path)

        def put_file(name, path, data, mode=0o644):
            self.put.append((name, path, mode))
            self.text = data.decode()

        for p in (mock.patch.object(containers, "docker", docker), mock.patch.object(containers, "available", lambda: True),
                  mock.patch.object(containers, "put_file", put_file), mock.patch.object(full_backup, "_drives", lambda _: DRIVES)):
            p.start()
            self.addCleanup(p.stop)

    def run_in(self, container, cmd, user="", timeout=60):
        self.ran.append((container, cmd, user))
        return (1 if "stuck.zip" in " ".join(cmd) else 0), "", ""

    def test_the_page_is_told_which_disk_each_choice_is_on(self):
        p = place.place("", "/config/backups")
        self.assertEqual((p["now"], p["chosen"], p["restart"], p["same_disk"]), ("settings", "settings", False, False))
        self.assertEqual([(c["key"], c["folder"], c["system"]) for c in p["choices"]],
                         [("settings", "/srv/stack/config/reelix/backups", True), ("media", "/mnt/disk1/media/backups/reelix", False)])
        self.assertEqual(p["choices"][1]["disk"], "WDC WD40EFRX")
        self.data_source = "/srv/media"
        self.assertTrue(place.place("", "/config/backups")["same_disk"], "the media folder is on the system disk too")
        self.assertEqual(place.place("", "/somewhere/else")["other"], "/somewhere/else")

    def test_choosing_the_media_folder(self):
        said = place.choose("", "media", ["reelix-1.zip", "stuck.zip", "../etc/passwd"], False, run_in=self.run_in)
        self.assertEqual(self.ran[0], ("reelix", ["mkdir", "-p", "/data/backups/reelix"], "1001:1002"))
        self.assertEqual([c[1] for c in self.ran[1:]], [["mv", "-n", "/config/backups/reelix-1.zip", "/data/backups/reelix/reelix-1.zip"],
                                                       ["mv", "-n", "/config/backups/stuck.zip", "/data/backups/reelix/stuck.zip"]])
        self.assertEqual(self.put, [("reelix", "/config/config.toml", 0o640)], "the file keeps its mode")
        self.assertEqual(tomllib.loads(self.text)["paths"]["backup_dir"], "/data/backups/reelix")
        self.assertIn("in the media folder from its next start", said)
        self.assertIn("1 could not be moved and stays in /config/backups", said)
        # Reelix still runs with the old folder until it starts again: the page offers Restart Reelix.
        p = place.place("", "/config/backups")
        self.assertEqual((p["now"], p["chosen"], p["restart"]), ("settings", "media", True))
        # And back: the line is taken out, so Reelix's own default applies.
        self.ran.clear()
        place.choose("", "settings", ["reelix-1.zip"], False, run_in=self.run_in)
        self.assertEqual(self.text, TEMPLATE)
        self.assertEqual(self.ran[1][1], ["mv", "-n", "/data/backups/reelix/reelix-1.zip", "/config/backups/reelix-1.zip"])

    def test_refused_in_words(self):
        with self.assertRaisesRegex(ValueError, "restore is waiting"):
            place.choose("", "media", [], True, run_in=self.run_in)
        with self.assertRaisesRegex(ValueError, "Choose next to"):
            place.choose("", "/etc", [], False, run_in=self.run_in)
        self.assertEqual(place.choose("", "settings", [], False, run_in=self.run_in), "Reelix keeps its backups there already")
        self.assertEqual((self.ran, self.put), ([], []))

    def test_no_config_file_yet_and_no_docker(self):
        self.text = None
        place.choose("", "media", [], False, run_in=self.run_in)
        self.assertEqual(tomllib.loads(self.text), {"paths": {"backup_dir": "/data/backups/reelix"}})
        with mock.patch.object(containers, "available", lambda: False):
            self.assertIsNone(place.place("", "/config/backups"))


if __name__ == "__main__":
    unittest.main()
