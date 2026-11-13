"""The idle benchmark's summary scripts (tools/bench, DASH-398): readings to one row per app, rows to whole stacks."""

import importlib.util
import pathlib
import unittest

BENCH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "bench"


def load(name):
    spec = importlib.util.spec_from_file_location(name, BENCH / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


summarise = load("summarise")
stacks = load("stacks")

READINGS = """13:51:00 bench-starboard 0.00% 16.5MiB / 15.53GiB 5
13:51:05 bench-starboard 0.01% 17.3MiB / 15.53GiB 5
13:51:10 bench-starboard 0.00% 18.7MiB / 15.53GiB 5
13:51:00 bench-radarr 0.08% 1.1GiB / 15.53GiB 23
not a reading
""".splitlines()


class SummariseTest(unittest.TestCase):
    def test_units(self):
        self.assertEqual(summarise.mib("512KiB"), 0.5)
        self.assertEqual(summarise.mib("2GiB"), 2048)
        self.assertEqual(summarise.mib("3.5MiB"), 3.5)

    def test_one_row_per_app_with_median_and_peak(self):
        out = summarise.rows(summarise.collect(READINGS))
        self.assertTrue(out[0].startswith("name\tsamples\tmem_median_MiB"))
        self.assertIn("bench-starboard\t3\t17.3\t18.7\t0.00\t0.00\t0.01\t5", out)
        self.assertIn("bench-radarr\t1\t1126.4\t1126.4\t0.08\t0.08\t0.08\t23", out)
        self.assertEqual(len(out), 3)  # the line that is not a reading is skipped


def row(mem, cpu, threads):
    return {"mem_median_MiB": str(mem), "cpu_median_pct": str(cpu), "threads_median": str(threads)}


class StacksTest(unittest.TestCase):
    def test_adds_the_shared_apps_to_every_stack(self):
        bench = {"starboard": row(16.9, 0.00, 5), "reelix-lite": row(17.9, 0.03, 22)}
        live = {"jellyfin": row(677.3, 1.54, 34), "audiobookshelf": row(69.9, 0.02, 12),
                "qbittorrent": row(8.4, 0.03, 17), "nzbget": row(7.9, 0.01, 17)}
        lines = stacks.totals(bench, live)
        self.assertEqual(lines[1], "This stack: Starboard, Reelix Lite\t2\t34.8\t0.03\t27\t763.5\t1.60\t798.3\t1.63\t6")
        self.assertEqual(len(lines), 2)  # stacks with apps not measured are left out

    def test_readarr_uses_the_estimate_and_missing_shared_apps_are_left_out(self):
        names = ["radarr", "sonarr", "lidarr", "prowlarr", "jellyseerr"]
        bench = {n: row(100.0, 0.08, 23) for n in names}
        lines = stacks.totals(bench, {"jellyfin": row(600.0, 1.0, 30)})
        classic = [line for line in lines if line.startswith("Classic")][0].split("\t")
        self.assertEqual(classic[2], "620.0")  # five apps at 100 plus Readarr's estimate of 120
        self.assertEqual(classic[7], "1220.0")
        self.assertEqual(classic[9], "7")  # six apps and the one shared app that is running


if __name__ == "__main__":
    unittest.main()
