"""A plug-in's own key (DASH-603, security fix 2): new at each start and update, 30 days that move on while it is used, and
accepted on the plug-in's socket alone when it cannot reach Starboard's port anyway."""
import copy
import datetime as dt
import http.client
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, plugin_socket, plugins_admin as pa
from starboard.server import make_server
from tests.test_plugins import ON_DEMAND


def lan(manifest):
    m = copy.deepcopy(manifest)
    for c in m["containers"]:
        c["network"] = "lan"
    m["permissions"] = sorted(set(m.get("permissions") or []) | {"network:lan"})
    return m


class Keys(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, name, kw in ((pa, "host_path", {"side_effect": lambda d, pid: f"/srv/starboard/data/plugins/{pid}"}),
                                 (pa, "_compose_run", {"return_value": (True, "")})):
            p = mock.patch.object(target, name, **kw)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(plugin_socket, "serve")
        p.start()
        self.addCleanup(p.stop)

    def key_of(self, pid="on-demand"):
        where = pa.folder(self.tmp.name, pid)
        with open(os.path.join(where, "key")) as f:
            return f.read().strip(), pa._read(os.path.join(where, "state.json"), {})["key_id"]

    def record(self, kid):
        return next(k for k in api_v1._load(self.tmp.name) if k["id"] == kid)

    def test_a_new_key_lasts_30_days_and_moves_on_while_used(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        key, kid = self.key_of()
        r = self.record(kid)
        self.assertEqual(r["slide_days"], 30)
        days = (dt.datetime.strptime(r["expires_at"], "%Y-%m-%dT%H:%M:%SZ") - dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)).days
        self.assertIn(days, (29, 30))
        old = (dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) + dt.timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        keys = api_v1._load(self.tmp.name)
        for k in keys:
            if k["id"] == kid:
                k["expires_at"] = old
        api_v1._save(self.tmp.name, keys)
        api_v1._used.clear()
        api_v1.note_use(self.tmp.name, self.record(kid))
        self.assertGreater(self.record(kid)["expires_at"], old)

    def test_an_unused_key_still_ends(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        key, kid = self.key_of()
        keys = api_v1._load(self.tmp.name)
        for k in keys:
            if k["id"] == kid:
                k["expires_at"] = "2020-01-01T00:00:00Z"
        api_v1._save(self.tmp.name, keys)
        self.assertIsNone(api_v1.find_key(self.tmp.name, f"Bearer {key}"))

    def test_start_makes_a_new_key_and_revokes_the_old_one(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        old_key, old_id = self.key_of()
        old_scopes = self.record(old_id)["scopes"]
        pa.set_state(self.tmp.name, "on-demand", "installed")
        pa.save_settings(self.tmp.name, "on-demand", {})
        pa.enable(self.tmp.name, "on-demand")
        new_key, new_id = self.key_of()
        self.assertNotEqual(old_key, new_key)
        self.assertIsNone(api_v1.find_key(self.tmp.name, f"Bearer {old_key}"))
        self.assertEqual(api_v1.find_key(self.tmp.name, f"Bearer {new_key}")["id"], new_id)
        self.assertEqual(self.record(new_id)["scopes"], old_scopes)
        self.assertEqual(len([k for k in api_v1._load(self.tmp.name) if k["name"].startswith("Plug-in:")]), 1)

    def test_socket_only_where_the_plugin_cannot_reach_the_port_anyway(self):
        self.assertTrue(pa.key_socket_only(ON_DEMAND))  # on the VPN
        self.assertFalse(pa.key_socket_only(lan(ON_DEMAND)))
        self.assertFalse(pa.key_socket_only({"id": "styles"}))

    def test_old_keys_are_given_an_end_date_once_and_do_not_change(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        key, kid = self.key_of()
        keys = api_v1._load(self.tmp.name)
        for k in keys:
            if k["id"] == kid:
                k["expires_at"] = None
                k.pop("slide_days", None)
                k.pop("socket_only", None)
        api_v1._save(self.tmp.name, keys)
        self.assertEqual(pa.renew_old_keys(self.tmp.name), 1)
        r = self.record(kid)
        self.assertEqual((r["slide_days"], bool(r["expires_at"]), r.get("socket_only")), (30, True, True))
        self.assertEqual(api_v1.find_key(self.tmp.name, f"Bearer {key}")["id"], kid)  # the key itself is the same
        self.assertEqual(pa.renew_old_keys(self.tmp.name), 0)


class OnThePort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.sock_key, _ = api_v1.create_key(cls.tmp.name, "Plug-in: A", "read", [], 30, socket_only=True, slide=True)
        cls.lan_key, _ = api_v1.create_key(cls.tmp.name, "Plug-in: B", "read", [], 30, socket_only=False, slide=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def status(self, key):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/api/v1/me", headers={"Authorization": f"Bearer {key}"})
        r = c.getresponse()
        r.read()
        c.close()
        return r.status

    def test_a_socket_only_key_is_refused_on_the_port_and_a_lan_key_is_not(self):
        self.assertEqual(self.status(self.sock_key), 401)
        self.assertEqual(self.status(self.lan_key), 200)

    def test_the_socket_handler_says_it_is_the_socket(self):
        self.assertTrue(plugin_socket.handler_for(type("B", (__import__("starboard.server").server.Handler,), {"app": self.app})).via_socket)


if __name__ == "__main__":
    unittest.main()
