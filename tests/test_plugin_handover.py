"""Plug-in API 1.6 (owner, 12 November 2026): a plug-in allowed reelix:key or usenet:servers gets Reelix's key and the
news servers from NZBGet or SABnzbd in its run/ folder; one not allowed them gets nothing."""
import copy
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugins, plugins_admin as pa, services as svc
from tests.test_plugins import ON_DEMAND

NZB_CONFIG = [{"Name": "Server1.Host", "Value": "news.example.invalid"}, {"Name": "Server1.Port", "Value": "563"},
              {"Name": "Server1.Encryption", "Value": "yes"}, {"Name": "Server1.Username", "Value": "sam"},
              {"Name": "Server1.Password", "Value": "made-up"}, {"Name": "Server1.Connections", "Value": "40"},
              {"Name": "Server1.Active", "Value": "yes"}, {"Name": "Server1.Level", "Value": "0"},
              {"Name": "Server2.Host", "Value": "off.example.invalid"}, {"Name": "Server2.Active", "Value": "no"}]
SERVICES = [{"id": "reelix", "type": "link", "icon": "reelix", "url": "http://127.0.0.1:7700", "api_key": "rx-key"},
            {"id": "nzbget", "type": "nzbget", "name": "NZBGet", "url": "http://127.0.0.1:6789", "api_key": "user:pass"}]


class Handover(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, value in (("host_path", lambda d, pid: f"/srv/data/plugins/{pid}"),):
            p = mock.patch.object(pa, name, side_effect=value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(pa, "_compose_run", return_value=(True, ""))
        p.start()
        self.addCleanup(p.stop)

    def add(self, perms):
        m = copy.deepcopy(ON_DEMAND)
        m["permissions"] = sorted(set(m["permissions"]) | set(perms))
        pa.install(self.tmp.name, m, "/srv/media")
        return os.path.join(self.tmp.name, "plugins", "on-demand")

    def test_the_permissions_are_known(self):
        for p in ("reelix:key", "usenet:servers"):
            self.assertIn(p, plugins.PERMISSIONS)
            self.assertIn(p, plugins.SEES)

    def test_allowed_gets_both_in_run(self):
        where = self.add(["reelix:key", "usenet:servers"])
        with mock.patch.object(svc, "nzbget", return_value=NZB_CONFIG), mock.patch("starboard.stack.reelix_url", return_value="http://127.0.0.1:7700"):
            pa.enable(self.tmp.name, "on-demand", services=SERVICES)
        with open(os.path.join(where, "run", "reelix.json")) as f:
            self.assertEqual(json.load(f), {"url": "http://host.docker.internal:7700", "api_key": "rx-key"})
        with open(os.path.join(where, "run", "usenet.json")) as f:
            servers = json.load(f)["servers"]
        self.assertEqual([(s["host"], s["port"], s["ssl"], s["user"], s["connections"]) for s in servers],
                         [("news.example.invalid", 563, True, "sam", 40)])  # the inactive one is left out

    def test_not_allowed_gets_nothing(self):
        where = self.add([])
        with mock.patch.object(svc, "nzbget", return_value=NZB_CONFIG):
            pa.enable(self.tmp.name, "on-demand", services=SERVICES)
        for name in ("reelix.json", "usenet.json"):
            self.assertFalse(os.path.exists(os.path.join(where, "run", name)), name)


if __name__ == "__main__":
    unittest.main()
