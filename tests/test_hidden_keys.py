"""Filling the keys the old apps hide, for a move into Reelix (DASH-128): Prowlarr's and the other apps' own
databases, what is left for the person to type, one set per app, and SABnzbd's key from sabnzbd.ini for a SABnzbd
that stays. Made-up settings files only; Docker is never called."""
import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest import mock

from starboard import reelix_move, reelix_setup, server, usenet_move
from tests.test_reelix_move import FakeAdmin, src


def made_up_db(folder, name, rows):
    path = os.path.join(folder, name)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE Indexers (Id INTEGER, Settings TEXT)")
    con.execute("CREATE TABLE DownloadClients (Id INTEGER, Settings TEXT)")
    for table, i, settings in rows:
        con.execute(f"INSERT INTO {table} VALUES (?, ?)", (i, json.dumps(settings)))
    con.commit()
    con.close()
    return path


class FromTheirDatabasesTest(unittest.TestCase):
    def setUp(self):
        self.made = tempfile.mkdtemp()
        reelix_move._found.clear()

    def tearDown(self):
        shutil.rmtree(self.made, ignore_errors=True)
        reelix_move._found.clear()

    def fake_read(self, files):
        """_read_files as Docker would answer: a copy of each made-up file that exists, in its own folder."""
        def read(container, paths, limit=None):
            folder = tempfile.mkdtemp(dir=self.made)
            out = {}
            for p in paths:
                there = files.get((container, p))
                if there:
                    local = os.path.join(folder, os.path.basename(p))
                    shutil.copy(there, local)
                    out[p] = local
            return out, folder
        return read

    def test_radarr_keeps_keys_for_sites_added_straight_into_it(self):
        db = made_up_db(self.made, "radarr.db", [("Indexers", 2, {"apiKey": "radarr-site-key"})])
        with mock.patch.object(reelix_move, "_read_files", self.fake_read({("radarr", "/config/radarr.db"): db})):
            self.assertEqual(reelix_move.app_secrets("radarr", "radarr", ["indexer:2:apiKey"]), {"indexer:2:apiKey": "radarr-site-key"})

    def test_bookshelf_may_name_its_own_database(self):
        db = made_up_db(self.made, "bookshelf.db", [("Indexers", 1, {"apiKey": "books-key"})])
        with mock.patch.object(reelix_move, "_read_files", self.fake_read({("bookshelf", "/config/bookshelf.db"): db})):
            self.assertEqual(reelix_move.app_secrets("bookshelf", "readarr", ["indexer:1:apiKey"]), {"indexer:1:apiKey": "books-key"})

    def test_seerr_and_unreadable_databases_give_nothing(self):
        self.assertEqual(reelix_move.app_secrets("jellyseerr", "jellyseerr", ["indexer:1:apiKey"]), {})
        with mock.patch.object(reelix_move, "_read_files", self.fake_read({})):
            self.assertEqual(reelix_move.app_secrets("sonarr", "sonarr", ["indexer:1:apiKey"]), {})

    def test_the_temporary_copies_are_removed(self):
        db = made_up_db(self.made, "sonarr.db", [("Indexers", 4, {"apiKey": "k4"})])
        folders = []
        read = self.fake_read({("sonarr", "/config/sonarr.db"): db})

        def keep(container, paths, limit=None):
            files, folder = read(container, paths)
            folders.append(folder)
            return files, folder
        with mock.patch.object(reelix_move, "_read_files", keep):
            reelix_move.app_secrets("sonarr", "sonarr", ["indexer:4:apiKey"])
        self.assertTrue(folders and not any(os.path.exists(f) for f in folders))

    def test_preview_fills_radarr_then_the_move_uses_what_it_read(self):
        plan_missing = {"items": [{"key": "indexer:2", "name": "NZB Harbour", "category": "indexer", "missing_secrets": ["apiKey"]}]}
        admin = FakeAdmin(previews=[plan_missing, {"items": [{"key": "indexer:2", "category": "indexer"}]}],
                          runs=[{"state": "finished", "items": []}])
        docker = mock.Mock(return_value=None)
        with mock.patch.object(reelix_move, "_admin", return_value=admin), \
                mock.patch.object(reelix_move, "app_secrets", return_value={"indexer:2:apiKey": "read"}) as read:
            out = reelix_move.preview("http://127.0.0.1:7700", "pw", [src("radarr")], docker=docker)
            self.assertEqual(out[0]["still_missing"], [])
            self.assertEqual(out[0]["filled"], 1)
            reelix_move.run_all("http://127.0.0.1:7700", "pw", [src("radarr")], hold=False, docker=docker, sleep=lambda s: None)
        read.assert_called_once_with("radarr", "radarr", ["indexer:2:apiKey"])
        run = next(b for m, p, b in admin.calls if p == "/system/migrate/run")
        self.assertEqual(run["secrets"], {"indexer:2:apiKey": "read"})
        # Radarr's preview reads its whole library, so the move does not ask for it again.
        self.assertEqual(sum(1 for m, p, b in admin.calls if p == "/system/migrate/preview"), 2)


class WhatIsLeftToTypeTest(unittest.TestCase):
    def test_download_apps_are_not_counted(self):
        plan = {"items": [{"key": "indexer:3", "category": "indexer", "missing_secrets": ["apiKey"]},
                          {"key": "download_client:1", "category": "download_client", "missing_secrets": ["apiKey"]},
                          {"key": "download_client:2", "missing_secrets": ["password"]}]}
        self.assertEqual(reelix_move.missing(plan), ["indexer:3:apiKey"])

    def test_each_key_is_named(self):
        plan = {"items": [{"key": "indexer:3", "name": "NZB Harbour", "category": "indexer", "missing_secrets": ["apiKey"]}]}
        self.assertEqual(reelix_move.needs(plan, ["indexer:3:apiKey"]),
                         [{"id": "indexer:3:apiKey", "name": "NZB Harbour", "category": "indexer", "field": "apiKey"}])

    def test_typed_keys_go_to_their_own_app(self):
        typed = {"prowlarr": {"indexer:3:apiKey": "p"}, "radarr": {"indexer:3:apiKey": "r"}, "indexer:9:apiKey": "all"}
        self.assertEqual(reelix_move.typed_for(src("prowlarr"), typed), {"indexer:3:apiKey": "p", "indexer:9:apiKey": "all"})
        self.assertEqual(reelix_move.typed_for(src("radarr"), typed), {"indexer:3:apiKey": "r", "indexer:9:apiKey": "all"})
        self.assertEqual(reelix_move._connection(src("sonarr"), typed)["secrets"], {"indexer:9:apiKey": "all"})

    def test_the_server_keeps_only_what_was_typed(self):
        got = server.typed_secrets({"prowlarr": {"indexer:3:apiKey": "p", "indexer:4:apiKey": ""}, "radarr": {}, "flat": "x", "empty": ""})
        self.assertEqual(got, {"prowlarr": {"indexer:3:apiKey": "p"}, "flat": "x"})
        self.assertEqual(server.typed_secrets(["not", "a", "dict"]), {})


class SabnzbdTest(unittest.TestCase):
    INI = "[misc]\nport = 8080\napi_key = 0123456789abcdef0123456789abcdef\n[servers]\n[[news.example]]\nhost = news.example\n"

    def test_key_and_port_from_sabnzbd_ini(self):
        self.assertEqual(usenet_move.sab_api_key(self.INI), "0123456789abcdef0123456789abcdef")
        self.assertEqual(usenet_move.sab_port(self.INI), 8080)
        self.assertIsNone(usenet_move.sab_api_key("[misc]\napi_key = \n"))
        self.assertEqual(usenet_move.sab_port("[misc]\n"), 8080)
        self.assertIsNone(usenet_move.sab_api_key("[servers]\napi_key = 0123456789abcdef0123\n"))  # only [misc]

    def test_reelix_gets_sabnzbd_with_that_key_and_port(self):
        admin = FakeAdmin(clients=[])
        with mock.patch.object(reelix_setup, "Session", return_value=admin):
            done = reelix_setup.switch_usenet("http://127.0.0.1:7700", "pw", "sabnzbd", "gluetun",
                                              sab_key=usenet_move.sab_api_key(self.INI), sab_port=usenet_move.sab_port(self.INI))
        method, path, body = admin.calls[-1]
        self.assertEqual((method, path), ("POST", "/downloadclients"))
        self.assertEqual(body["settings"], {"host": "gluetun", "port": 8080, "use_ssl": False,
                                            "api_key": "0123456789abcdef0123456789abcdef"})
        self.assertEqual(done, ["Connected Reelix to SABnzbd"])


if __name__ == "__main__":
    unittest.main()
