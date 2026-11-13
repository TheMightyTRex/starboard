"""Whether the apps chosen fit this computer, in both set-ups (DASH-114; docs/test-plans/install.md WIZ-31 to WIZ-33,
WIZ-72): memory advice with what to leave out, apps with no version for a Raspberry Pi left out with the reason, and a
disk that gives no health data said plainly. Nothing is asked of a real registry."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import containers, stack, sysinfo


class MemoryAdviceTest(unittest.TestCase):
    def test_basics_fits_two_gb_and_full_does_not(self):
        self.assertIsNone(stack.memory_advice(stack.INSTALLS["basics"]["apps"], 1900))
        advice = stack.memory_advice(stack.INSTALLS["full"]["apps"], 1900)
        self.assertIn("Leave out Tdarr and FlareSolverr", advice["text"])
        self.assertEqual(advice["leave_out"], ["tdarr", "flaresolverr"])

    def test_never_suggests_reelix_a_download_app_or_the_vpn_and_the_players_last(self):
        advice = stack.memory_advice(["reelix", "qbittorrent", "gluetun", "jellyfin", "jellystat"], 900)
        self.assertNotIn("reelix", advice["leave_out"])
        self.assertNotIn("qbittorrent", advice["leave_out"])
        self.assertNotIn("gluetun", advice["leave_out"])
        self.assertEqual(advice["leave_out"][0], "jellystat")

    def test_unknown_memory_gives_no_advice(self):
        self.assertIsNone(stack.memory_advice(stack.INSTALLS["full"]["apps"], 0))

    def test_the_machine_reads_meminfo(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("MemTotal:        2000000 kB\n")
        try:
            self.assertEqual(stack.machine(f.name)["memory_mb"], 1953)
        finally:
            os.unlink(f.name)


class ProcessorTest(unittest.TestCase):
    def setUp(self):
        stack._arm64_images.clear()
        self.addCleanup(stack._arm64_images.clear)

    def test_only_a_64_bit_arm_computer_asks_and_a_lost_connection_hides_nothing(self):
        asked = []
        def platforms(ref):
            asked.append(ref)
            if "gluetun" in ref:
                raise OSError("offline")
            return {"amd64"} if "reelix" in ref else {"amd64", "arm64"}
        self.assertEqual(stack.no_image_here(["reelix", "jellyfin"], platforms, arm64=False), [])
        self.assertEqual(asked, [])
        self.assertEqual(stack.no_image_here(["reelix", "jellyfin", "gluetun"], platforms, arm64=True), ["reelix"])

    def test_the_catalogue_and_installs_leave_them_out_with_the_reason(self):
        with mock.patch.object(stack, "no_image_here", side_effect=lambda keys, check=None, arm64=None: [k for k in keys if k == "bazarr"]):
            cat = stack.catalogue(set())
            bazarr = next(a for a in cat["apps"] if a["key"] == "bazarr")
            self.assertFalse(bazarr["default"])
            self.assertIn("64-bit ARM", bazarr["no_image"])
            c = stack.install_choice("basics", check=lambda ref: {"digest": "x", "version": ""})
        self.assertNotIn("bazarr", c["apps"])
        self.assertEqual(c["left_out"], ["bazarr"])
        self.assertIn("Left out", c["note"])

    def test_platforms_reads_a_list_and_a_single_image(self):
        index = {"manifests": [{"platform": {"os": "linux", "architecture": "amd64"}},
                               {"platform": {"os": "linux", "architecture": "arm64"}},
                               {"platform": {"os": "unknown", "architecture": "unknown"}}]}
        with mock.patch.object(containers, "_registry", return_value=({}, json.dumps(index).encode())):
            self.assertEqual(containers.platforms("ghcr.io/example/app:latest"), {"amd64", "arm64"})
        replies = [({}, json.dumps({"config": {"digest": "sha256:c"}}).encode()), ({}, json.dumps({"architecture": "amd64"}).encode())]
        with mock.patch.object(containers, "_registry", side_effect=replies):
            self.assertEqual(containers.platforms("ghcr.io/example/app:latest"), {"amd64"})


class NoHealthDataTest(unittest.TestCase):
    def test_a_virtual_disk_says_it_gives_no_health_data(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "current"))
            with open(os.path.join(d, "current", "sdb.json"), "w") as f:
                json.dump({"model_name": "QEMU HARDDISK", "smart_support": {"available": False}}, f)
            with open(os.path.join(d, "current", "sda.json"), "w") as f:
                json.dump({"model_name": "Disk", "smart_status": {"passed": True}}, f)
            with mock.patch.dict(os.environ, {"STARBOARD_SMART_DIR": d}):
                disks = {x["model"]: x for x in sysinfo.disk_health()["disks"]}
        self.assertTrue(disks["QEMU HARDDISK"]["no_data"])
        self.assertFalse(disks["Disk"]["no_data"])

    def test_the_page_says_so_plainly(self):
        import pathlib
        js = (pathlib.Path(__file__).resolve().parent.parent / "web" / "js" / "system-disks.js").read_text()
        self.assertIn("This disk gives no health data", js)


if __name__ == "__main__":
    unittest.main()
