"""Restore a full backup on this server (DASH-387), through the route: it needs Starboard's password, refuses in words
before anything starts, and gives the settings to the settings restore, which saves a copy first. Nothing is
restored: the restore itself is stood in for (tests/test_full_backup_restore.py covers it)."""
import http.client
import json
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, full_backup
from starboard.server import make_server

PASSWORD = "correct horse battery"


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for name in ("HISTORY", "SCHEDULE", "WATCH", "JOBS"):
            os.environ[f"STARBOARD_{name}"] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        resp, _ = cls.request("POST", "/api/setup", {"token": cls.app.setup_token, "password": PASSWORD})
        cls.cookie = resp.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    @classmethod
    def request(cls, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = {"Content-Type": "application/json", **({"X-Starboard": "1"} if method != "GET" else {}),
             **({"Cookie": cls.cookie} if getattr(cls, "cookie", None) else {})}
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        resp = conn.getresponse()
        raw = resp.read()
        return resp, (json.loads(raw) if raw[:1] in (b"{", b"[") else raw)

    def test_it_needs_starboards_password(self):
        with mock.patch.object(full_backup, "start_restore") as start:
            resp, data = self.request("POST", "/api/backup/full/restore-here", {"password": "wrong", "backup_password": "x" * 12, "file": "/mnt/b/x"})
        self.assertEqual(resp.status, 401)
        start.assert_not_called()
        self.app.limits.clear("127.0.0.1")

    def test_a_refusal_is_said_in_words_and_nothing_starts(self):
        resp, data = self.request("POST", "/api/backup/full/restore-here", {"password": PASSWORD, "backup_password": "a long backup password",
                                                                            "file": "/mnt/b/starboard-full-2026-11-01-030000.starboard"})
        self.assertEqual(resp.status, 400)
        self.assertRegex(data["error"], "Docker access|cryptography")
        resp, data = self.request("GET", "/api/backup/full/restore-here")
        self.assertEqual((resp.status, data["status"]), (200, {"state": "none"}))

    def test_the_settings_go_through_the_settings_restore_which_saves_a_copy_first(self):
        seen = {}

        def start(data_dir, version, file_path, password, apply_settings, site_name=""):
            seen.update(file=file_path, password=password)
            seen["count"] = apply_settings({"schema": 4, "site_name": "Harbour", "services": [
                {"id": "notes", "type": "link", "name": "Notes", "url": "http://notes.example:8080", "category": "Tools"}]})
            full_backup._tell(data_dir, state="done", finished=1.0)
        with mock.patch.object(full_backup, "start_restore", start):
            resp, data = self.request("POST", "/api/backup/full/restore-here", {"password": PASSWORD, "backup_password": "a long backup password",
                                                                                "file": "/mnt/b/starboard-full-2026-11-01-030000.starboard"})
        self.assertEqual((resp.status, data["status"]["state"]), (202, "done"))
        self.assertEqual(seen, {"file": "/mnt/b/starboard-full-2026-11-01-030000.starboard", "password": "a long backup password", "count": 1})
        self.assertEqual((self.app.config.data["site_name"], [s["id"] for s in self.app.config.data["services"]]), ("Harbour", ["notes"]))
        self.assertTrue(any("before-restore" in name for name in os.listdir(os.path.join(self.tmp.name, "backups"))), "a copy of the settings from before")
        self.assertTrue(auth.check_password(PASSWORD, self.app.config.data["auth"]["password_hash"]), "the password stays")
        resp, data = self.request("GET", "/api/backup/full")
        self.assertEqual(data["restore"]["state"], "done")


if __name__ == "__main__":
    unittest.main()
