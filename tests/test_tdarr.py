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
        self.assertEqual(sum(1 for o in inserts[0]["schedule"] if o["checked"]), 7 * 7)  # midnight to 07:00, every day
        workers = [b["data"]["workerType"] for p, b in calls if p == "alter-worker-limit"]
        self.assertEqual(workers.count("transcodecpu"), 2)
        self.assertIn("2 at a time, overnight only", out["done"][-1])

    def test_an_old_tdarr_link_becomes_a_tdarr_app(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({**json.loads(json.dumps(config.DEFAULTS)), "schema": config.SCHEMA,
                       "services": [{"id": "t", "name": "Tdarr", "type": "link", "icon": "tdarr", "url": "http://x:8265"}]}, f)
        self.assertEqual(config.Config(d).data["services"][0]["type"], "tdarr")


if __name__ == "__main__":
    unittest.main()
