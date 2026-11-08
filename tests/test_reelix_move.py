"""Moving the old apps into Reelix through Reelix's own migrator (reelix_move.py, DASH-127 to 129): path rewrites,
the keys the apps hide, the order and settings of each run, holding the indexers, and qBittorrent."""
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from starboard import reelix_move, reelix_setup


class FakeAdmin:
    """Reelix's API as the move uses it, answering from canned replies and keeping every call."""

    def __init__(self, previews=None, runs=None, indexers=None, clients=None):
        self.calls = []
        self.previews = list(previews or [])
        self.runs = list(runs or [])
        self.indexers = indexers or []
        self.clients = clients or []

    def call(self, method, path, body=None, timeout=20, ok=(200, 201, 204)):
        self.calls.append((method, path, body))
        if path == "/system/migrate/preview":
            return 200, self.previews.pop(0)
        if path == "/system/migrate/run":
            return 202, None
        if path == "/system/migrate":
            return 200, self.runs.pop(0)
        if path == "/indexers" and method == "GET":
            return 200, self.indexers
        if path == "/downloadclients" and method == "GET":
            return 200, self.clients
        return 200, {}


def src(kind="radarr", **extra):
    return {"source": kind, "app": reelix_move.LABELS[kind], "container": kind, "url": f"http://{kind}:7878",
            "api_key": "k", "networks": ["stack_proxy"], "path_rewrites": [], **extra}


class PathTest(unittest.TestCase):
    def test_rewrites_only_where_the_paths_differ(self):
        radarr = {"Mounts": [{"Type": "bind", "Source": "/mnt/pool", "Destination": "/data"},
                             {"Type": "bind", "Source": "/srv/films", "Destination": "/movies"},
                             {"Type": "bind", "Source": "/home/o/config/radarr", "Destination": "/config"}]}
        reelix = {"Mounts": [{"Type": "bind", "Source": "/mnt/pool", "Destination": "/data"},
                             {"Type": "bind", "Source": "/srv", "Destination": "/srv"}]}
        self.assertEqual(reelix_move.path_rewrites(radarr, reelix), [{"from": "/movies", "to": "/srv/films"}])


class HiddenKeysTest(unittest.TestCase):
    def test_reads_the_hidden_keys_from_the_database(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "prowlarr.db")
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE Indexers (Id INTEGER, Settings TEXT)")
            con.execute("INSERT INTO Indexers VALUES (3, ?)", (json.dumps({"apiKey": "real-key", "baseUrl": "x"}),))
            con.execute("INSERT INTO Indexers VALUES (4, ?)", (json.dumps({"apiKey": "********"}),))
            con.commit()
            con.close()
            got = reelix_move.hidden_from_db(db, ["indexer:3:apiKey", "indexer:4:apiKey", "indexer:9:apiKey",
                                                  "indexer:3; DROP TABLE Indexers:apiKey", "tag:1:name"])
        self.assertEqual(got, {"indexer:3:apiKey": "real-key"})

    def test_missing_lists_each_field(self):
        plan = {"items": [{"key": "indexer:3", "missing_secrets": ["apiKey"]}, {"key": "movie:1"}]}
        self.assertEqual(reelix_move.missing(plan), ["indexer:3:apiKey"])


class MoveTest(unittest.TestCase):
    def setUp(self):
        self.docker = mock.Mock(return_value=None)

    def run_all(self, admin, srcs, **kw):
        with mock.patch.object(reelix_move, "_admin", return_value=admin):
            return reelix_move.run_all("http://127.0.0.1:7700", "pw", srcs, docker=self.docker, sleep=lambda s: None, **kw)

    def test_moves_in_order_with_search_off_and_without_download_apps(self):
        done = {"state": "finished", "items": [{"category": "movie", "action": "create"},
                                               {"category": "movie", "action": "skip", "name": "Disc", "detail": "iso"}]}
        admin = FakeAdmin(runs=[{"state": "running"}, done, done], indexers=[])
        report = self.run_all(admin, [src("radarr"), src("sonarr")], hold=False)
        runs = [b for m, p, b in admin.calls if p == "/system/migrate/run"]
        self.assertEqual([r["source"] for r in runs], ["radarr", "sonarr"])
        self.assertTrue(all(r["search_missing"] is False for r in runs))
        self.assertNotIn("download_client", runs[0]["categories"])
        self.assertEqual(report[0]["counts"], {"movie": {"create": 1, "skip": 1}})
        self.assertEqual(report[0]["not_moved"], [{"name": "Disc", "category": "movie", "why": "iso"}])
        joined = [c for c in self.docker.call_args_list if c[0][1].endswith("/connect")]
        left = [c for c in self.docker.call_args_list if c[0][1].endswith("/disconnect")]
        self.assertEqual(len(joined), 1)  # one network, joined once
        self.assertEqual(len(left), 1)  # and left afterwards

    def test_leaves_the_networks_even_when_reelix_fails(self):
        admin = FakeAdmin()
        admin.call = mock.Mock(side_effect=reelix_setup.ReelixError("Reelix said 500"))
        with self.assertRaises(reelix_setup.ReelixError):
            self.run_all(admin, [src("radarr")])
        self.assertTrue(any(c[0][1].endswith("/disconnect") for c in self.docker.call_args_list))

    def test_prowlarr_gets_its_hidden_keys(self):
        admin = FakeAdmin(previews=[{"items": [{"key": "indexer:3", "missing_secrets": ["apiKey"]}]}],
                          runs=[{"state": "finished", "items": []}])
        with mock.patch.object(reelix_move, "prowlarr_secrets", return_value={"indexer:3:apiKey": "real"}) as read:
            self.run_all(admin, [src("prowlarr")], hold=False)
        read.assert_called_once_with("prowlarr", ["indexer:3:apiKey"])
        run = next(b for m, p, b in admin.calls if p == "/system/migrate/run")
        self.assertEqual(run["secrets"], {"indexer:3:apiKey": "real"})

    def test_holding_switches_the_indexers_off(self):
        ix = [{"id": 1, "enabled": True, "implementation": "torznab", "name": "A", "priority": 25, "tags": [], "settings": {"api_key": "********"}},
              {"id": 2, "enabled": False, "implementation": "torznab", "name": "B", "priority": 25, "tags": [], "settings": {}}]
        admin = FakeAdmin(runs=[{"state": "finished", "items": []}], indexers=ix)
        report = self.run_all(admin, [src("radarr")], hold=True)
        puts = [(p, b) for m, p, b in admin.calls if m == "PUT"]
        self.assertEqual(puts, [("/indexers/1", {"implementation": "torznab", "name": "A", "priority": 25, "tags": [],
                                                 "settings": {"api_key": "********"}, "enabled": False})])
        self.assertEqual(report[-1], {"held": 1})

    def test_an_app_without_a_key_is_reported_not_sent(self):
        admin = FakeAdmin()
        report = self.run_all(admin, [src("radarr", api_key=None)], hold=False)
        self.assertEqual(report[0]["state"], "failed")
        self.assertFalse(any(p == "/system/migrate/run" for _, p, _ in admin.calls))

    def test_reelix_must_be_starboards_own(self):
        with self.assertRaises(reelix_setup.ReelixError):
            reelix_move._admin("http://example.com:7700", "pw")


class QbitTest(unittest.TestCase):
    def test_changes_the_one_reelix_has(self):
        admin = FakeAdmin(clients=[{"id": 5, "implementation": "qbittorrent", "name": "qBittorrent", "enabled": True,
                                    "priority": 25, "tags": [], "settings": {"host": "10.88.0.2", "port": 8080, "category": "films"}}])
        note = reelix_move.connect_qbittorrent(admin, "gluetun", "secret")
        method, path, body = admin.calls[-1]
        self.assertEqual((method, path), ("PUT", "/downloadclients/5"))
        self.assertEqual(body["settings"]["host"], "gluetun")
        self.assertEqual(body["settings"]["password"], "secret")
        self.assertEqual(body["settings"]["category"], "films")  # what was there stays
        self.assertIn("gluetun", note)

    def test_adds_one_when_there_is_none(self):
        admin = FakeAdmin(clients=[])
        reelix_move.connect_qbittorrent(admin, "qbittorrent", "secret")
        self.assertEqual(admin.calls[-1][:2], ("POST", "/downloadclients"))


if __name__ == "__main__":
    unittest.main()
