"""Starboard reads apps' keys from their own files (owner, 10 November 2026: nothing to type during set-up). Docker is
a stand-in that serves made-up files; nothing real is read."""
import io
import os
import sqlite3
import tarfile
import tempfile
import unittest
from unittest import mock

from starboard import containers, discovery


def tar_of(data):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w") as tar:
        info = tarfile.TarInfo("file")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return out.getvalue()


def database(sql):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "x.db")
        db = sqlite3.connect(path)
        db.executescript(sql)
        db.commit()
        db.close()
        with open(path, "rb") as f:
            return f.read()


class FakeDocker:
    def __init__(self, files):
        self.files = files  # {(container, path): bytes}

    def __call__(self, method, path, body=None, raw=False, timeout=None):
        import urllib.parse
        name = path.split("/")[2]
        want = urllib.parse.unquote(path.split("path=", 1)[1])
        if (name, want) not in self.files:
            raise containers.DockerError("no such file")
        return tar_of(self.files[(name, want)])


BAZARR = b"""general:
  port: 6767
sonarr:
  apikey: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
auth:
  type: form
  apikey: 0123456789abcdef0123456789abcdef
radarr:
  apikey: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
"""


class ReadKeysTest(unittest.TestCase):
    def read(self, key, files, container="app"):
        with mock.patch.object(containers, "available", return_value=True), \
                mock.patch.object(containers, "docker", FakeDocker(files)):
            return discovery.read_key(key, container)

    def test_bazarr_is_its_own_key_not_sonarrs(self):
        self.assertEqual(self.read("bazarr", {("app", "/config/config/config.yaml"): BAZARR}), "0123456789abcdef0123456789abcdef")

    def test_nzbget_is_its_sign_in(self):
        conf = b"MainDir=/data\nControlUsername=nzbget\nControlPassword=made-up-word\n"
        self.assertEqual(self.read("nzbget", {("app", "/config/nzbget.conf"): conf}), "nzbget:made-up-word")
        self.assertIsNone(self.read("nzbget", {("app", "/config/nzbget.conf"): b"ControlUsername=nzbget\n"}))

    def test_jellyfin_uses_its_newest_key(self):
        db = database("CREATE TABLE ApiKeys (Id INTEGER, DateCreated TEXT, Name TEXT, AccessToken TEXT);"
                      "INSERT INTO ApiKeys VALUES (1, '2026-01-01', 'Old', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');"
                      "INSERT INTO ApiKeys VALUES (2, '2026-06-01', 'New', 'cccccccccccccccccccccccccccccccc');")
        self.assertEqual(self.read("jellyfin", {("app", "/config/data/jellyfin.db"): db}), "c" * 32)
        empty = database("CREATE TABLE ApiKeys (Id INTEGER, DateCreated TEXT, Name TEXT, AccessToken TEXT);")
        self.assertIsNone(self.read("jellyfin", {("app", "/config/data/jellyfin.db"): empty}))

    def test_audiobookshelf_uses_its_root_users_token(self):
        db = database("CREATE TABLE users (id TEXT, type TEXT, token TEXT);"
                      "INSERT INTO users VALUES ('1', 'user', 'not-this-one-xxxxxxxxxxxxx');"
                      "INSERT INTO users VALUES ('2', 'root', 'the-root-token-made-up-1234567');")
        self.assertEqual(self.read("audiobookshelf", {("app", "/config/absdatabase.sqlite"): db}), "the-root-token-made-up-1234567")

    def test_nothing_without_docker_or_with_an_odd_name(self):
        with mock.patch.object(containers, "available", return_value=False):
            self.assertIsNone(discovery.read_key("bazarr", "bazarr"))
        self.assertIsNone(self.read("bazarr", {}, container="../etc"))

    def test_missing_keys_are_read_and_saved(self):
        class Cfg:
            data = {"services": [
                {"id": "1", "name": "Bazarr", "type": "bazarr", "url": "http://127.0.0.1:6767", "container": "bazarr"},
                {"id": "2", "name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "container": "jellyfin"},
                {"id": "3", "name": "Radarr", "type": "radarr", "url": "http://127.0.0.1:7878", "api_key": "kept"}]}
            saved = []

            def upsert_service(self, s):
                self.saved.append(s)

        cfg = Cfg()
        with mock.patch.object(containers, "available", return_value=True), \
                mock.patch.object(containers, "docker", FakeDocker({("bazarr", "/config/config/config.yaml"): BAZARR})):
            out = discovery.read_missing_keys(cfg)
        self.assertEqual(out["found"], ["Bazarr"])
        self.assertEqual([m["name"] for m in out["missing"]], ["Jellyfin"])
        self.assertEqual(cfg.saved[0]["api_key"], "0123456789abcdef0123456789abcdef")  # Radarr, with a key, is left alone


if __name__ == "__main__":
    unittest.main()
