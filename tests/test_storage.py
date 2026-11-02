"""Storage: sorting by media type, pools, the daily record and the settings that control them."""

import json
import os
import tempfile
import unittest

from starboard import sysinfo
from starboard.config import Config, ConfigError


def write(path, size):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(os.urandom(size))


class StorageTest(unittest.TestCase):
    def test_folder_names_give_the_type(self):
        self.assertEqual([sysinfo.media_type(n) for n in ("TV", "Films", "audiobooks", "Comics", "usenet", "media")],
                         ["tv", "movies", "audiobooks", "books", "downloads", None])

    def test_a_pool_is_the_sum_of_every_folder_under_one_parent(self):
        disks = [{"label": "Pool", "path": "/disks/pool", "total": 30}, {"label": "System", "path": "/data", "total": 1}] + \
            [{"label": n, "path": f"/disks/each/{n}", "total": t} for n, t in (("a", 4), ("b", 4), ("c", 2), ("d", 2), ("e", 8), ("f", 6), ("g", 4))]
        self.assertEqual(sysinfo.pools(disks), {"Pool": ["a", "b", "c", "d", "e", "f", "g"]})
        self.assertEqual(sysinfo.pools(disks[1:]), {})  # without the pool, two 2s do not make a 4

    def test_the_scan_sorts_by_type_counts_hard_links_once_and_finds_the_biggest(self):
        with tempfile.TemporaryDirectory() as d:
            root = os.path.join(d, "pool")
            write(f"{root}/media/tv/Series A/e1.mkv", 300_000)
            write(f"{root}/media/tv/Series B/e1.mkv", 100_000)
            write(f"{root}/media/movies/Film/f.mkv", 200_000)
            write(f"{root}/torrents/Film/f.mkv", 1)
            os.remove(f"{root}/torrents/Film/f.mkv")
            os.link(f"{root}/media/movies/Film/f.mkv", f"{root}/torrents/Film/f.mkv")  # seeding and in the library
            write(f"{root}/notes/readme.txt", 5_000)
            u = sysinfo.Usage(d, lambda: {"usage_every": "ask"})
            u.running = True
            u._scan([("Pool", root)])
            f = u.get()["folders"][0]
            t = f["types"]
            self.assertGreater(t["tv"], t["movies"])
            self.assertGreater(t["movies"], 190_000)
            self.assertLess(t["downloads"], 10_000)  # the hard-linked film counts for the library
            self.assertGreater(t["other"], 0)
            self.assertEqual([b["name"] for b in f["biggest"]][:2], ["Series A", "Film"])

    def test_off_refuses_and_nightly_keeps_a_thread_only_while_chosen(self):
        settings = {"usage_every": "off"}
        with tempfile.TemporaryDirectory() as d:
            u = sysinfo.Usage(d, lambda: settings, [("Pool", d)])
            with self.assertRaises(ValueError):
                u.start([("Pool", d)])
            self.assertIsNone(u.thread)
            settings["usage_every"] = "nightly"
            u.ensure()  # waits for 3 am: no reading starts now
            self.assertTrue(u.thread.is_alive())
            self.assertFalse(u.running)
            settings["usage_every"] = "ask"
            u.ensure()
            u.thread.join(timeout=5)
            self.assertFalse(u.thread.is_alive())

    def test_scheduled_readings_wait_for_3_am(self):
        from datetime import datetime
        noon = datetime(2026, 11, 2, 12, 0).timestamp()
        at = datetime.fromtimestamp(sysinfo.Usage.next_run(86400, 0, noon))
        self.assertEqual((at.day, at.hour), (3, 3))
        last = datetime(2026, 11, 2, 3, 5).timestamp()
        at = datetime.fromtimestamp(sysinfo.Usage.next_run(7 * 86400, last, noon))
        self.assertEqual((at.day, at.hour), (9, 3))

    def test_space_log_records_once_a_day_and_not_when_off(self):
        settings = {"space_log": True}
        with tempfile.TemporaryDirectory() as d:
            log = sysinfo.SpaceLog(d, lambda: settings)
            log.record([{"label": "Pool", "used": 5, "total": 10}])
            self.assertFalse(log.due())
            self.assertEqual(list(log.get().values())[0], {"Pool": [5, 10]})
            settings["space_log"] = False
            log.today = None
            self.assertFalse(log.due())

    def test_settings_and_presets(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual((c.data["performance"]["usage_every"], c.data["performance"]["storage_refresh"]), ("ask", 0))
            c.update_general({"preset": "everything"})
            self.assertEqual((c.data["performance"]["usage_every"], c.data["performance"]["storage_refresh"]), ("weekly", 60))
            with self.assertRaises(ConfigError):
                c.update_general({"performance": {"usage_every": "hourly"}})
            with self.assertRaises(ConfigError):
                c.update_general({"performance": {"storage_refresh": 5}})

    def test_an_older_config_gets_the_new_settings_and_keeps_its_preset(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            for k in ("usage_every", "storage_refresh", "space_log"):
                del c.data["performance"][k]
            c.save()
            again = Config(d)
            self.assertEqual(again.data["performance"]["usage_every"], "ask")
            self.assertEqual(again.public()["performance"]["preset"], "balanced")


if __name__ == "__main__":
    unittest.main()
