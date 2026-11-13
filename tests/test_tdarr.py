"""Tdarr from Starboard (DASH-306): choices written into Tdarr, and an old Tdarr link moved to the Tdarr type."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import config, services, tdarr


class TdarrTest(unittest.TestCase):
    def test_save_adds_libraries_sets_workers_and_marks_set_up_done(self):
        calls = []
        nodes = {"n1": {"nodeName": "starboard", "workerLimits": {"transcodecpu": 0, "healthcheckcpu": 0}}}

        def fake(s, path, body=None, timeout=None):
            calls.append((path, body))
            if path == "cruddb" and body["data"]["mode"] == "getAll":
                return []
            if path == "get-nodes":
                return nodes
            if path == "cruddb" and body["data"]["mode"] == "getById":
                return {}
            return "OK"
        d = tempfile.mkdtemp()
        cfg = mock.Mock(data={"services": [{"type": "tdarr", "api_key": "tapi_x", "url": "http://t"}]}, data_dir=d)
        with mock.patch.object(services, "tdarr", side_effect=fake):
            out = tdarr.save(cfg, {"mode": "save_space", "at_once": 2, "night": True, "libraries": {"films": True, "series": False}})
        inserts = [b["data"]["obj"] for p, b in calls if p == "cruddb" and b["data"]["mode"] == "insert"]
        self.assertEqual([(o["name"], o["folder"], o["cache"]) for o in inserts], [("Films", "/media/movies", "/temp")])
        self.assertEqual(sum(1 for o in inserts[0]["schedule"] if o["checked"]), 5 * 7)  # quiet hours, 01:00 to 06:00 (DASH-411)
        workers = [b["data"]["workerType"] for p, b in calls if p == "alter-worker-limit"]
        self.assertEqual(workers.count("transcodecpu"), 2)
        self.assertIn("2 at a time, in quiet hours only", out["done"][-1])

    def test_the_cache_is_on_the_pool_when_the_plugin_mounts_it(self):
        d = tempfile.mkdtemp()
        cfg = mock.Mock(data={"services": [{"type": "tdarr", "api_key": "tapi_x", "url": "http://t"}]}, data_dir=d)
        self.assertEqual(tdarr.cache_folder(cfg), "/temp")  # no plug-in: Tdarr's own /temp
        os.makedirs(os.path.join(d, "plugins", "tdarr"))
        with open(os.path.join(d, "plugins", "tdarr", "manifest.json"), "w") as f:
            json.dump({"containers": [{"name": "server", "volumes": ["data/cache:/temp", "media/tdarr-cache"]}]}, f)
        self.assertEqual(tdarr.cache_folder(cfg), "/media/tdarr-cache")
        calls = []

        def fake(s, path, body=None, timeout=None):
            calls.append((path, body))
            if path == "cruddb" and body["data"]["mode"] == "getAll":
                return [{"_id": "sb-films", "cache": "/temp"}, {"_id": "mine", "cache": "/somewhere"}]
            return {} if path in ("get-nodes", "cruddb") else "OK"
        with mock.patch.object(services, "tdarr", side_effect=fake):
            tdarr.save(cfg, {"mode": "check_only", "at_once": 0, "libraries": {"films": True, "series": False}})
        updates = [b["data"] for p, b in calls if p == "cruddb" and b["data"]["mode"] == "update"]
        self.assertEqual([(u["docID"], u["obj"]["cache"]) for u in updates], [("sb-films", "/media/tdarr-cache")])  # not the person's own

    def test_quiet_hours_follow_the_download_hours(self):
        cfg = mock.Mock(data={"download_hours": {"enabled": True, "start": 23, "end": 7}})
        self.assertEqual(tdarr.quiet_hours(cfg), (23, 7))
        on = [o["_id"] for o in tdarr._schedule(True, (23, 7)) if o["checked"] and o["_id"].startswith("Mon")]
        self.assertEqual(len(on), 8)
        self.assertIn("Mon:23-00", on)
        self.assertEqual(tdarr.quiet_hours(mock.Mock(data={})), (1, 6))
        self.assertTrue(all(o["checked"] for o in tdarr._schedule(False)))

    def test_an_old_tdarr_link_becomes_a_tdarr_app(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({**json.loads(json.dumps(config.DEFAULTS)), "schema": config.SCHEMA,
                       "services": [{"id": "t", "name": "Tdarr", "type": "link", "icon": "tdarr", "url": "http://x:8265"}]}, f)
        self.assertEqual(config.Config(d).data["services"][0]["type"], "tdarr")


if __name__ == "__main__":
    unittest.main()
