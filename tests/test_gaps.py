"""The API gaps filled in 0.7.0: one app's check and its history, queue actions, warnings by app, categories in
one save, saved copies, server backup files, disk events and a wrong password that keeps the page."""

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import backup, services, sysinfo
from starboard.config import Config, ConfigError


class FakeSonarr(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *a):
        pass

    def reply(self, body):
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path.endswith("/health"):
            return self.reply([{"type": "warning", "message": self.server.warning, "wikiUrl": "https://wiki.example/x"}])
        if path.endswith("/queue"):
            return self.reply({"records": [{"id": 7, "title": "A.Show.S01E01", "downloadId": "abc", "added": "2026-11-02T10:00:00Z",
                                            "statusMessages": [{"messages": [f"m{i}" for i in range(25)]}]}]})
        self.reply({"version": "4.0.0"})

    def do_DELETE(self):
        FakeSonarr.calls.append(self.path)
        self.reply({})


class GapsTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSonarr)
        self.server.warning = "Indexers unavailable"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.sonarr = {"id": "tv", "name": "TV", "type": "sonarr", "url": f"http://127.0.0.1:{self.server.server_address[1]}", "api_key": "k", "enabled": True}
        services.RECENT.clear()
        services.DOWN_SINCE.clear()
        services.FIRST_SEEN.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_one_app_check_keeps_history_and_down_time(self):
        gone = dict(self.sonarr, id="gone", url="http://127.0.0.1:9")
        first = services.status_all([self.sonarr, gone], only="gone")
        self.assertEqual([r["id"] for r in first], ["gone"])
        since = first[0]["down_since"]
        time.sleep(0.01)
        self.assertEqual(services.status_all([gone])[0]["down_since"], since)  # the first failure is kept
        self.assertEqual(len(services.recent_checks("gone")), 2)
        services.status_all([dict(gone, url=self.sonarr["url"])])
        self.assertNotIn("gone", services.DOWN_SINCE)
        self.assertEqual(services.recent_checks("gone")[0]["state"], "up")  # newest first
        for _ in range(30):
            services.check(self.sonarr)
        self.assertEqual(len(services.recent_checks("tv")), 20)

    def test_warnings_carry_the_app_and_when_first_seen(self):
        a = services.health([self.sonarr])["items"][0]
        self.assertEqual((a["service"], a["wiki"]), ("tv", "https://wiki.example/x"))
        time.sleep(0.01)
        self.assertEqual(services.health([self.sonarr])["items"][0]["first_seen"], a["first_seen"])
        self.server.warning = "Something else"
        services.health([self.sonarr])
        self.assertEqual([k[1] for k in services.FIRST_SEEN], ["Something else"])  # the old one is forgotten

    def test_queue_items_and_actions(self):
        row = services.queue([self.sonarr])["items"][0]
        self.assertEqual((row["id"], row["service"], row["download_id"], len(row["messages"])), (7, "tv", "abc", 20))
        services.queue_action(self.sonarr, 7, "block-search")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(FakeSonarr.calls[-1]).query)
        self.assertEqual((q["blocklist"], q["skipRedownload"]), (["true"], ["false"]))
        with self.assertRaises(services.ServiceError):
            services.queue_action(self.sonarr, 7, "explode")

    def test_category_rename_moves_apps_in_one_save(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(d)
            cfg.data["services"] = [{"id": "a", "name": "A", "type": "link", "group": "Old"}, {"id": "b", "name": "B", "type": "link", "group": "Other"}]
            cfg.data["groups"] = ["Old", "Other"]
            cfg.update_general({"groups": ["New", "Other"], "move_apps": {"from": "Old", "to": "New"}})
            self.assertEqual([s["group"] for s in cfg.data["services"]], ["New", "Other"])
            with self.assertRaises(ConfigError):
                cfg.update_general({"move_apps": {"from": "Other", "to": "Nowhere"}})

    def test_saved_copy_detail_and_download(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Config(d)
            cfg.data["auth"]["password_hash"] = "secret-hash"
            cfg.data["services"] = [{"id": "a", "name": "A", "type": "link"}]
            cfg.save()
            cfg.backup("restore")
            name = backup.saved_copies(cfg)[0]["name"]
            self.assertEqual(backup.saved_detail(cfg, name)["apps"], 1)
            out = backup.export_saved(cfg, name, "0.7.0")
            self.assertEqual(out["format"], "starboard-settings")
            self.assertNotIn("secret-hash", json.dumps(out))  # never the password
            with self.assertRaises(ConfigError):
                backup.saved_detail(cfg, "../config.json")

    def test_server_backup_files_only_from_the_backup_folder(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "server-2026-11-02.tar.gz"), "w").close()
            open(os.path.join(d, "notes.txt"), "w").close()
            with mock.patch.dict(os.environ, {"STARBOARD_BACKUP_DIR": d}):
                self.assertTrue(backup.server_file("server-2026-11-02.tar.gz"))
                self.assertIsNone(backup.server_file("notes.txt"))
                self.assertIsNone(backup.server_file("../etc/passwd"))

    def test_disk_events_are_split(self):
        self.assertEqual(sysinfo._event("2026-11-02 09:15:00 /dev/sda: SMART test failed"),
                         {"when": "2026-11-02 09:15:00", "text": "/dev/sda: SMART test failed", "tone": "danger"})
        self.assertEqual(sysinfo._event("no time here")["when"], "")


if __name__ == "__main__":
    unittest.main()
