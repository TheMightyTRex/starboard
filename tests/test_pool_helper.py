"""The drive pool helper (DASH-87), against a made-up computer in a temporary folder: no drive is touched, and every
command it would run is recorded instead."""
import json
import os
import shutil
import tempfile
import time
import unittest

from starboard import pool_helper as ph


def disk(name, size, serial, model="WDC WD40EFRX", parts=(), fstype=None, mounts=()):
    return {"name": name, "path": f"/dev/{name}", "size": size, "type": "disk", "fstype": fstype, "serial": serial,
            "model": model, "mountpoints": list(mounts) or [None], "tran": "sata", "rota": True, "rm": False,
            "children": [dict({"type": "part", "path": f"/dev/{p['name']}", "mountpoints": [None]}, **p) for p in parts] or None}


TB = 1000 ** 4


class Computer:
    """A temporary root with /dev/disk/by-id links, an fstab and a recorded command log."""

    def __init__(self, devices, fstab="UUID=root / ext4 defaults 0 1\n", mounts=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        byid = os.path.join(self.root, "dev/disk/by-id")
        os.makedirs(byid)
        for d in devices:
            open(os.path.join(self.root, "dev", d["name"]), "w").close()
            os.symlink(f"../../{d['name']}", os.path.join(byid, f"ata-{d['model'].replace(' ', '_')}_{d['serial']}"))
        os.makedirs(os.path.join(self.root, "etc"))
        with open(os.path.join(self.root, "etc/fstab"), "w") as f:
            f.write(fstab)
        self.devices = devices
        self.exchange = os.path.join(self.root, "exchange")
        os.makedirs(os.path.join(self.exchange, "requests"))
        self.host = ph.Host(root=self.root, exchange=self.exchange, run=self.command,
                            lsblk=lambda: {"blockdevices": self.devices}, mounts=mounts or {})

    def command(self, cmd):
        return ""

    def fstab(self):
        with open(self.host.fstab) as f:
            return f.read()

    def byid(self, name):
        return self.host.by_id(name)


def standard():
    return [
        disk("sda", 250 * 1000 ** 3, "S2R5NX0H", "Samsung SSD 850", parts=[
            {"name": "sda1", "size": 512 * 1000 ** 2, "fstype": "vfat", "mountpoints": ["/boot/efi"]},
            {"name": "sda2", "size": 249 * 1000 ** 3, "fstype": "ext4", "uuid": "root", "mountpoints": ["/"]}]),
        disk("sdb", 4 * TB, "WD-WCC7K1ABC9KX1"),
        disk("sdc", 2 * TB, "Z4Z0C3D", "ST2000DM", parts=[
            {"name": "sdc1", "size": 2 * TB, "fstype": "ext4", "uuid": "keep-uuid", "label": "media"}]),
        disk("sdd", 4 * TB, "WD-55B0", "WDC WD40EFZX"),
        disk("sde", 1 * TB, "RAID1", "ST1000", parts=[{"name": "sde1", "size": TB, "fstype": "linux_raid_member"}]),
    ]


class DrivesTest(unittest.TestCase):
    def test_system_and_raid_drives_are_never_offered(self):
        c = Computer(standard())
        uses = {d["name"]: d for d in ph.drives(c.host)}
        self.assertEqual(uses["sda"]["use"], "system")
        self.assertIn("system drive", uses["sda"]["blocked"])
        self.assertEqual(uses["sde"]["use"], "in use")
        self.assertIn("RAID", uses["sde"]["blocked"])
        self.assertEqual(uses["sdb"]["use"], "free")
        self.assertEqual(uses["sdb"]["ends"], "9KX1")
        self.assertTrue(uses["sdb"]["by_id"].startswith("/dev/disk/by-id/ata-"))

    def test_a_pool_made_by_hand_is_shown_and_never_changed(self):
        c = Computer(standard(), fstab="UUID=root / ext4 defaults 0 1\n/mnt/disks/a:/mnt/disks/b /mnt/pool fuse.mergerfs allow_other 0 0\n")
        self.assertEqual(ph.handmade_pool(c.host)["mount"], "/mnt/pool")
        with self.assertRaisesRegex(ph.Refused, "made outside Starboard"):
            ph.plan_add(c.host, "sdb", "pool", erase=True)
        self.assertNotIn(ph.BEGIN, c.fstab())


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.c = Computer(standard())
        self.h = self.c.host

    def test_the_check_lists_every_change_and_changes_nothing(self):
        before = self.c.fstab()
        plan = ph.plan_add(self.h, "sdb", "pool", erase=True)
        says = " ".join(s["say"] for s in plan["steps"])
        self.assertIn("Erase", says)
        self.assertIn("ends 9KX1", says)
        self.assertIn("Make the pool", says)
        self.assertEqual(plan["erases"], [self.c.byid("sdb")])
        self.assertEqual(self.c.fstab(), before)
        self.assertEqual(self.h.log, [])
        self.assertTrue(os.path.exists(os.path.join(self.c.exchange, "status/plans", plan["id"] + ".json")))

    def test_an_erase_needs_the_serial_ending(self):
        plan = ph.plan_add(self.h, "sdb", "pool", erase=True)
        with self.assertRaisesRegex(ph.Refused, "last 4 characters of its serial number, 9KX1"):
            ph.apply(self.h, plan["id"], {})
        with self.assertRaisesRegex(ph.Refused, "9KX1"):
            ph.apply(self.h, plan["id"], {self.c.byid("sdb"): "1234"})
        self.assertEqual(self.h.log, [])

    def test_a_drive_that_changed_since_the_check_is_refused(self):
        plan = ph.plan_add(self.h, "sdb", "pool", erase=True)
        self.c.devices[1]["children"] = [{"name": "sdb1", "type": "part", "size": TB, "fstype": "ntfs", "mountpoints": [None]}]
        with self.assertRaisesRegex(ph.Refused, "changed since the check"):
            ph.apply(self.h, plan["id"], {self.c.byid("sdb"): "9kx1"})

    def test_an_old_check_is_refused(self):
        plan = ph.plan_add(self.h, "sdb", "pool", erase=True)
        path = os.path.join(self.h.state, "plans", plan["id"] + ".json")
        data = json.load(open(path))
        data["expires"] = time.time() - 1
        json.dump(data, open(path, "w"))
        with self.assertRaisesRegex(ph.Refused, "more than 15 minutes old"):
            ph.apply(self.h, plan["id"], {self.c.byid("sdb"): "9KX1"})

    def test_adding_writes_only_its_own_block(self):
        plan = ph.plan_add(self.h, "sdb", "pool", erase=True)
        ph.apply(self.h, plan["id"], {self.c.byid("sdb"): "9KX1"})
        text = self.c.fstab()
        self.assertTrue(text.startswith("UUID=root / ext4 defaults 0 1\n"))
        block = text.split(ph.BEGIN)[1].split(ph.END)[0]
        self.assertIn("/mnt/disks/disk1 ext4 defaults,nofail,x-systemd.device-timeout=30s 0 2", block)
        self.assertIn("fuse.mergerfs", block)
        self.assertIn("category.create=mfs", block)
        commands = [c[0] for c in self.h.log]
        self.assertEqual(commands[:4], ["wipefs", "sgdisk", "sgdisk", "udevadm"])
        self.assertIn("mkfs.ext4", commands)
        self.assertTrue(os.listdir(os.path.join(self.h.state, "saved")))
        self.assertTrue(os.path.exists(self.h.docker_dropin))
        job = json.load(open(os.path.join(self.c.exchange, "status/job.json")))
        self.assertEqual(job["state"], "done")
        # The same drive cannot be planned twice, and the second drive goes in the same pool line.
        with self.assertRaisesRegex(ph.Refused, "already used"):
            ph.plan_add(self.h, "sdb", "pool", erase=True)
        plan = ph.plan_add(self.h, "sdc", "pool")
        self.assertEqual(plan["erases"], [])
        ph.apply(self.h, plan["id"], {})
        self.assertIn("/mnt/disks/disk1:/mnt/disks/disk2 ", self.c.fstab())
        self.assertEqual(self.c.fstab().count(ph.BEGIN), 1)

    def test_keeping_files_on_a_drive_without_files_is_refused(self):
        with self.assertRaisesRegex(ph.Refused, "no files to keep"):
            ph.plan_add(self.h, "sdb", "pool", erase=False)

    def test_parity_must_be_as_big_as_the_biggest_pool_drive(self):
        ph.apply(self.h, ph.plan_add(self.h, "sdb", "pool", erase=True)["id"], {self.c.byid("sdb"): "9KX1"})
        with self.assertRaisesRegex(ph.Refused, "at least as big"):
            ph.plan_add(self.h, "sdc", "parity", erase=True)
        plan = ph.plan_add(self.h, "sdd", "parity", erase=True)
        ph.apply(self.h, plan["id"], {self.c.byid("sdd"): "55B0"})
        conf = open(self.h.snapraid_conf).read()
        self.assertTrue(conf.startswith(ph.SNAP_HEAD))
        self.assertIn("/mnt/parity/parity1/snapraid.parity", conf)
        self.assertIn("data disk1 ", conf)

    def test_a_snapraid_conf_written_by_hand_is_left_alone(self):
        ph.apply(self.h, ph.plan_add(self.h, "sdb", "pool", erase=True)["id"], {self.c.byid("sdb"): "9KX1"})
        with open(self.h.snapraid_conf, "w") as f:
            f.write("parity /somewhere\n")
        plan = ph.plan_add(self.h, "sdd", "parity", erase=True)
        with self.assertRaisesRegex(ph.Refused, "not written by Starboard"):
            ph.apply(self.h, plan["id"], {self.c.byid("sdd"): "55B0"})
        self.assertEqual(open(self.h.snapraid_conf).read(), "parity /somewhere\n")

    def test_erasing_a_drive_already_in_fstab_is_refused(self):
        c = Computer(standard(), fstab="UUID=root / ext4 defaults 0 1\nUUID=keep-uuid /media/old ext4 defaults 0 2\n")
        with self.assertRaisesRegex(ph.Refused, "already mounts this drive"):
            ph.plan_add(c.host, "sdc", "pool", erase=True)
        plan = ph.plan_add(c.host, "sdc", "pool")
        self.assertIn("/media/old", " ".join(s["say"] for s in plan["steps"]))


@unittest.skipUnless(shutil.which("findmnt"), "needs findmnt")
class FstabCheckTest(unittest.TestCase):
    def test_a_missing_mount_folder_is_an_error_and_warnings_are_not(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "disk1"))
            line = f"{root}/disk1 {root}/pool fuse.mergerfs defaults,allow_other,nofail 0 0"
            self.assertIn("unreachable", ph.fstab_problems([line]))
            os.makedirs(os.path.join(root, "pool"))
            self.assertEqual(ph.fstab_problems([line]), "")


class BalanceTest(unittest.TestCase):
    def make(self, root, name, files):
        branch = os.path.join(root, name)
        for rel, size in files.items():
            path = os.path.join(branch, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(b"x" * size)
            old = time.time() - 7200
            os.utime(path, (old, old))
        os.makedirs(branch, exist_ok=True)
        return branch

    def test_whole_series_folders_move_from_the_fullest_drive(self):
        with tempfile.TemporaryDirectory() as root:
            mb = 1024 * 1024
            full = self.make(root, "disk1", {"media/tv/Show A/S1/e1.mkv": 30 * mb, "media/tv/Show A/S1/e2.mkv": 30 * mb,
                                             "media/tv/Show B/e1.mkv": 20 * mb, "media/movies/Film (2019)/f.mkv": 25 * mb})
            empty = self.make(root, "disk2", {})
            pieces = ph.units(full)
            self.assertIn(os.path.join("media", "tv", "Show A"), pieces)
            self.assertNotIn(os.path.join("media", "tv", "Show A", "S1"), pieces)
            branches = {full: {"size": 120 * mb, "used": 105 * mb}, empty: {"size": 120 * mb, "used": 0}}
            moves, sides = ph.balance_moves(None, branches)
            self.assertTrue(moves)
            self.assertTrue(all(m["from"] == full and m["to"] == empty for m in moves))
            after = {b: s["after"] / s["size"] for b, s in sides.items()}
            self.assertLess(abs(after[full] - after[empty]), 0.4)

    def test_folders_changed_in_the_last_hour_stay(self):
        with tempfile.TemporaryDirectory() as root:
            mb = 1024 * 1024
            full = self.make(root, "disk1", {"torrents/new/a.mkv": 50 * mb})
            os.utime(os.path.join(full, "torrents/new/a.mkv"))
            empty = self.make(root, "disk2", {})
            moves, _ = ph.balance_moves(None, {full: {"size": 60 * mb, "used": 50 * mb}, empty: {"size": 60 * mb, "used": 0}})
            self.assertEqual(moves, [])

    @unittest.skipUnless(__import__("shutil").which("rsync"), "rsync is not on this computer (the pool helper's servers have it)")
    def test_a_move_copies_checks_then_removes(self):
        with tempfile.TemporaryDirectory() as root:
            full = self.make(root, "disk1", {"media/tv/Show A/e1.mkv": 1000})
            empty = self.make(root, "disk2", {})
            host = ph.Host(root=root)
            m = {"from": "/disk1", "to": "/disk2", "path": "media/tv/Show A", "bytes": 4096,
                 "mtime": os.lstat(os.path.join(full, "media/tv/Show A/e1.mkv")).st_mtime}
            self.assertEqual(ph.move_piece(host, m, None), "moved")
            self.assertTrue(os.path.exists(os.path.join(empty, "media/tv/Show A/e1.mkv")))
            self.assertFalse(os.path.exists(os.path.join(full, "media/tv/Show A")))

    def test_pause_windows_cross_midnight(self):
        import datetime
        at = lambda h, m: datetime.datetime(2026, 11, 5, h, m)  # noqa: E731
        self.assertTrue(ph.in_pause([["23:00", "07:00"]], at(2, 0)))
        self.assertFalse(ph.in_pause([["23:00", "07:00"]], at(12, 0)))
        self.assertTrue(ph.in_pause([["01:00", "07:00"]], at(6, 59)))


class RequestTest(unittest.TestCase):
    def setUp(self):
        self.c = Computer(standard())

    def put(self, name, data):
        path = os.path.join(self.c.exchange, "requests", name)
        with open(path, "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def answer(self, rid):
        return json.load(open(os.path.join(self.c.exchange, "status/answers", rid + ".json")))

    def test_a_plan_request_is_answered_and_removed(self):
        self.put("a1b2c3d4.json", {"action": "plan", "id": "a1b2c3d4", "kind": "add", "drive": "sdb", "as": "pool", "erase": True})
        ph.serve(self.c.host)
        a = self.answer("a1b2c3d4")
        self.assertTrue(a["ok"], a)
        self.assertEqual(a["result"]["erases"], [self.c.byid("sdb")])
        self.assertEqual(os.listdir(os.path.join(self.c.exchange, "requests")), [])
        self.assertTrue(os.path.exists(os.path.join(self.c.exchange, "status/status.json")))

    def test_unknown_actions_links_and_large_files_are_refused(self):
        self.put("aaaaaaaa.json", {"action": "shell", "id": "aaaaaaaa", "cmd": "rm -rf /"})
        target = os.path.join(self.c.root, "secret")
        open(target, "w").write("{}")
        os.symlink(target, os.path.join(self.c.exchange, "requests", "bbbbbbbb.json"))
        self.put("cccccccc.json", "{" + " " * (ph.REQUEST_MAX + 10) + "}")
        ph.serve(self.c.host)
        self.assertFalse(self.answer("aaaaaaaa")["ok"])
        self.assertFalse(self.answer("bbbbbbbb")["ok"])
        self.assertFalse(self.answer("cccccccc")["ok"])
        self.assertTrue(os.path.exists(target))
        self.assertEqual(self.c.host.log, [])

    def test_apply_through_a_request_needs_the_serial(self):
        self.put("a1b2c3d4.json", {"action": "plan", "id": "a1b2c3d4", "kind": "add", "drive": "sdb", "as": "pool", "erase": True})
        ph.serve(self.c.host)
        plan = self.answer("a1b2c3d4")["result"]["id"]
        self.put("e1e2e3e4.json", {"action": "apply", "id": "e1e2e3e4", "plan": plan})
        ph.serve(self.c.host)
        self.assertIn("9KX1", self.answer("e1e2e3e4")["error"])
        self.put("f1f2f3f4.json", {"action": "apply", "id": "f1f2f3f4", "plan": plan, "confirm": {self.c.byid("sdb"): "9KX1"}})
        ph.serve(self.c.host)
        self.assertTrue(self.answer("f1f2f3f4")["ok"])
        self.assertIn("mkfs.ext4", [c[0] for c in self.c.host.log])


if __name__ == "__main__":
    unittest.main()
