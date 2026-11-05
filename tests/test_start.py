"""How to start and Storage, the shared first questions of both set-ups (DASH-102, DASH-103)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from starboard import start, sysinfo, terminal_setup  # noqa: E402
from starboard.server import App  # noqa: E402

TB = 10 ** 12


def drive(mount, size, fs="ext4", label=""):
    return {"mount": mount, "device": "sdx1", "size": size, "fs": fs, "model": "Example drive", "label": label}


class StartTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_new_install_is_recommended_when_nothing_is_found(self):
        found = start.options([], self.tmp.name, search=lambda s: {"items": []})
        self.assertEqual(found["recommended"], "new")
        self.assertEqual([c["key"] for c in found["choices"]], ["new", "move", "restore"])
        self.assertEqual([c["recommended"] for c in found["choices"]], [True, False, False])

    def test_move_is_recommended_when_media_apps_run(self):
        found = start.options([], self.tmp.name, search=lambda s: {"items": [{"key": "sonarr", "name": "Sonarr"}]})
        self.assertEqual(found["recommended"], "move")
        self.assertEqual(found["found"], ["Sonarr"])

    def test_the_run_first_hand_over_counts_too(self):
        with open(os.path.join(self.tmp.name, "run-first.json"), "w") as f:
            json.dump({"apps": ["radarr"]}, f)
        found = start.options([], self.tmp.name, search=lambda s: {"items": []})
        self.assertEqual(found["recommended"], "move")

    def test_finding_apps_failing_never_stops_the_set_up(self):
        def broken(services):
            raise OSError("no network")
        self.assertEqual(start.options([], self.tmp.name, search=broken)["recommended"], "new")

    def test_storage_with_no_other_drive_is_the_main_disk(self):
        found = start.storage("/srv/media", [], False)
        self.assertEqual(found["recommended"], "main")
        self.assertEqual([c["key"] for c in found["choices"]], ["main"])

    def test_storage_recommends_the_biggest_separate_disk(self):
        found = start.storage("/srv/media", [drive("/mnt/a", 2 * TB), drive("/mnt/b", 4 * TB, "ntfs")], False)
        keys = [c["key"] for c in found["choices"]]
        self.assertEqual(keys, ["main", "disk:/mnt/b", "disk:/mnt/a", "pool"])
        self.assertEqual(found["recommended"], "disk:/mnt/b")
        self.assertIn("ext4 is better", found["choices"][1]["about"])
        self.assertEqual(found["choices"][1]["folder"], "/mnt/b/media")
        self.assertIn("run ./install.sh again", found["choices"][3]["about"])  # the pool helper is not set up

    def test_storage_recommends_the_pool_when_the_helper_is_there(self):
        found = start.storage("/srv/media", [drive("/mnt/a", 2 * TB), drive("/mnt/b", 4 * TB)], True)
        self.assertEqual(found["recommended"], "pool")
        self.assertEqual(found["choices"][-1]["folder"], "/mnt/pool/media")

    def test_the_drive_list_from_the_hand_over(self):
        listing = {"blockdevices": [
            {"name": "sda", "type": "disk", "size": 500, "model": "System", "children": [
                {"name": "sda1", "type": "part", "size": 500, "fstype": "ext4", "mountpoints": ["/"]}]},
            {"name": "sdb", "type": "disk", "size": 4 * TB, "model": "Data", "children": [
                {"name": "sdb1", "type": "part", "size": 4 * TB, "fstype": "ext4", "mountpoints": ["/mnt/data"]}]}]}
        with open(os.path.join(self.tmp.name, "run-first.json"), "w") as f:
            json.dump({"lsblk": listing}, f)
        os.environ.pop("STARBOARD_SMART_DIR", None)
        found = sysinfo.pool_candidates(self.tmp.name)
        self.assertEqual([d["mount"] for d in found], ["/mnt/data"])  # the system disk is left out


class WizardSecurityTest(unittest.TestCase):
    """The security review of 5 November 2026: what the set-ups hand to the installer, and what they read."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_only_safe_folders_reach_the_installer(self):
        for bad in ("/", "/home", "/var", "/etc/cron.d", "/var/spool/cron", "/srv/m\n", "/a b", "relative", "/x/../etc", "--docker"):
            self.assertFalse(start.safe_folder(bad), bad)
        for good in ("/srv/media", "/home/sam/media", "/mnt/disks/media-1/media", "/mnt/pool/media"):
            self.assertTrue(start.safe_folder(good), good)
        self.assertEqual(start.host_args({"media": "/srv/m\n", "livetv": "/home", "health": True}), ["--disk-health"])
        self.assertEqual(start.host_args({"media": "/srv/media"}), ["--disk", "Media=/srv/media"])

    def test_the_setup_code_is_never_read_through_a_link(self):
        secret = os.path.join(self.tmp.name, "secret")
        with open(secret, "w") as f:
            f.write("PRIVATE KEY that must stay on this computer")
        code = os.path.join(self.tmp.name, "setup-token")
        os.symlink(secret, code)
        self.assertEqual(terminal_setup.read_setup_code(code), "")
        os.remove(code)
        with open(code, "w") as f:
            f.write("not a code: spaces and a colon")
        self.assertEqual(terminal_setup.read_setup_code(code), "")
        with open(code, "w") as f:
            f.write("Abc_def-12345678\n")
        self.assertEqual(terminal_setup.read_setup_code(code), "Abc_def-12345678")

    def test_only_this_computer_s_own_names_are_allowed(self):
        app = App.__new__(App)
        app.machine_name, app.allowed_hosts = "starboard-pi", set()
        for name in ("starboard-pi", "starboard-pi.local", "starboard-pi.lan", "localhost", "192.168.1.20"):
            self.assertTrue(app.host_allowed(name), name)
        for name in ("starboard-pi.attacker.example", "starboard-pi.local.attacker.example", "evil.example"):
            self.assertFalse(app.host_allowed(name), name)


if __name__ == "__main__":
    unittest.main()
