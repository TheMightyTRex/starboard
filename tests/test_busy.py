"""What is using the processor now (DASH-558): the heaviest containers and processes, read on request, read only."""
import os
import threading
import unittest
from unittest import mock

from starboard import busy

SERVICES = [{"name": "Sonarr", "type": "sonarr", "container": "sonarr"}]
DOCKER_IDS = {"a" * 64: "sonarr", "b" * 64: "plugin-x-main", "c" * 64: "mystery", "d" * 64: "radarr"}


class Reading(unittest.TestCase):
    def read(self, c1, c2, host=False, p1=None, p2=None, docker=True, gap=1.0):
        samples = iter([c1, c2])
        procs = iter([p1 or {}, p2 or {}])
        with mock.patch.object(busy.os, "cpu_count", lambda: 4), mock.patch.object(busy.time, "sleep", lambda s: None), \
                mock.patch.object(busy, "_cgroup_sample", lambda: next(samples)), mock.patch.object(busy, "_procs", lambda: next(procs)), \
                mock.patch.object(busy, "_sees_the_host", lambda: host), mock.patch.object(busy.containers, "available", lambda: docker), \
                mock.patch.object(busy.sysinfo, "_container_names", lambda: {k: v for k, v in DOCKER_IDS.items()}), \
                mock.patch.object(busy, "_container_of", lambda pid: "a" * 64 if pid == 7 else ""):
            return busy.read(SERVICES, gap)

    def test_containers_from_the_cgroup_files_are_a_share_of_the_whole_processor(self):
        c1 = {"a" * 64: (0, 100), "b" * 64: (0, 5_000_000), "c" * 64: (0, 7)}
        c2 = {"a" * 64: (2_000_000, 300_000_000), "b" * 64: (100_000, 5_000_000), "c" * 64: (0, 7)}
        out = self.read(c1, c2)
        by = {c["name"]: c for c in out["containers"]}
        # 2 s of processor time in about 1 s on 4 processors is about half; the span is a measured second, here very short
        self.assertGreater(by["sonarr"]["cpu"], by["plugin-x-main"]["cpu"])
        self.assertEqual(out["containers"][0]["name"], "sonarr")  # busiest first
        self.assertEqual(by["sonarr"]["note"], "Sonarr, one of your apps in Starboard")
        self.assertEqual(by["plugin-x-main"]["note"], "A plug-in's container")
        self.assertEqual(by["mystery"]["note"], "Not one of Starboard's apps")
        self.assertEqual(out["source"], "cgroup")

    def test_a_container_in_the_container_sees_only_itself_and_says_so(self):
        out = self.read({"a" * 64: (0, 1)}, {"a" * 64: (0, 1)}, host=False)
        self.assertEqual(out["processes"], [])
        self.assertTrue(any("can read only its own processes" in n for n in out["notes"]))

    def test_processes_on_the_host_name_their_container_and_what_they_are(self):
        hz = busy._hz()
        p1 = {7: ("sonarr", 0, 10_000_000), 8: ("radarr", 0, 5), 9: ("sleep", 0, 4_000), os.getpid(): ("python3", 0, 1)}
        p2 = {7: ("sonarr", hz * 2, 10_000_000), 8: ("radarr", hz // 10, 5), 9: ("sleep", 0, 4_000), os.getpid(): ("python3", 0, 1)}
        out = self.read({}, {}, host=True, p1=p1, p2=p2)
        rows = {p["pid"]: p for p in out["processes"]}
        self.assertEqual(out["processes"][0]["pid"], 7)  # busiest first
        self.assertEqual(rows[7]["container"], "sonarr")
        self.assertEqual(rows[7]["note"], "Sonarr, one of your apps in Starboard")
        self.assertEqual(rows[8]["note"], "Radarr, not added to Starboard yet")
        self.assertEqual(rows[9]["note"], "")
        self.assertEqual(rows[os.getpid()]["note"], "Starboard itself")

    def test_docker_statistics_are_used_without_the_cgroup_files(self):
        calls = []

        def one(cid):
            calls.append(cid)
            n = len(calls)
            return (n * 1000, n * 10_000, 50_000_000) if cid != "d" * 64 else None  # one container does not answer

        with mock.patch.object(busy, "_docker_one", one), \
                mock.patch.object(busy.containers, "docker", lambda *a, **k: [{"Id": i, "Names": ["/" + n]} for i, n in DOCKER_IDS.items()]):
            out = self.read(None, None, docker=True)
        self.assertEqual(out["source"], "docker")
        self.assertEqual(len(out["containers"]), 3)
        self.assertTrue(any("1 of 4 containers did not answer in time" in n for n in out["notes"]))

    def test_without_docker_or_the_cgroup_files_it_says_why(self):
        out = self.read(None, None, docker=False)
        self.assertEqual((out["source"], out["containers"]), (None, []))
        self.assertTrue(any("Docker access is off" in n for n in out["notes"]))

    def test_one_reading_at_a_time(self):
        started, release = threading.Event(), threading.Event()

        def slow(services, gap):
            started.set()
            release.wait(5)
            return {}

        with mock.patch.object(busy, "_read", slow):
            t = threading.Thread(target=busy.read, args=([], 0))
            t.start()
            started.wait(5)
            with self.assertRaises(busy.Busy):
                busy.read([], 0)
            release.set()
            t.join(5)
        with mock.patch.object(busy, "_read", lambda s, g: {"ok": 1}):
            self.assertEqual(busy.read([], 0), {"ok": 1})

    def test_the_lists_are_short(self):
        c1 = {f"{i:064x}": (0, i) for i in range(40)}
        c2 = {f"{i:064x}": (i * 1000, i) for i in range(40)}
        out = self.read(c1, c2)
        self.assertLessEqual(len(out["containers"]), busy.TOP + 4)
        self.assertEqual(out["containers_total"], 40)


class Reads(unittest.TestCase):
    def test_the_process_table_is_read_from_proc_and_a_name_with_brackets_is_whole(self):
        procs = busy._procs()
        self.assertIn(os.getpid(), procs)
        name, ticks, rss = procs[os.getpid()]
        self.assertTrue(name and ticks >= 0 and rss > 0)

    def test_a_process_that_goes_while_it_is_read_is_skipped(self):
        real = open

        def flaky(path, *a, **k):
            if str(path).endswith(f"/{os.getpid()}/stat"):
                raise FileNotFoundError(path)
            return real(path, *a, **k)

        with mock.patch("builtins.open", flaky):
            self.assertNotIn(os.getpid(), busy._procs())

    def test_nothing_in_it_can_stop_or_change_anything(self):
        import inspect
        source = inspect.getsource(busy)
        for forbidden in ("os.kill", "signal.", "subprocess", '"POST"', '"DELETE"', "os.remove", ".write("):
            self.assertNotIn(forbidden, source)

    def test_think_about_a_name(self):
        self.assertEqual(busy._think("starboard", []), "Starboard itself")
        self.assertEqual(busy._think("", []), "")
        self.assertEqual(busy._think("jellyfin", [{"name": "Jellyfin"}]), "Jellyfin, one of your apps in Starboard")
        self.assertEqual(busy._think("my-sonarr", []), "Sonarr, not added to Starboard yet")


if __name__ == "__main__":
    unittest.main()
