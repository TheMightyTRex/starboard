"""DASH-79: heavy jobs run in a short-lived process, so the long-running server's memory stays low (on the owner's
server the hourly watch history import took Starboard from 18 MB to 164 MB, and it was still at 61 MB eight minutes
later). These run the real child process."""

import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import child, library, logs, services


class Reelix(BaseHTTPRequestHandler):
    fail = False

    def log_message(self, *a):
        pass

    def do_GET(self):
        if Reelix.fail:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        u = urllib.parse.urlparse(self.path)
        films = [{"id": i, "title": f"Film {i}", "sort_title": "", "year": 2000 + i, "status": "released", "has_file": True,
                  "monitored": True, "images": {"poster": f"http://127.0.0.1:1/p/{i}.jpg"}, "added": "2026-01-01T00:00:00Z",
                  "genres": [], "movie_file": {"id": i, "cutoff_met": True}} for i in range(1, 4)]
        body = json.dumps({"items": films if u.path.endswith("/movies") else [], "total": 3, "page": 1}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Child(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Reelix)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.reelix = {"name": "Reelix", "type": "link", "url": f"http://127.0.0.1:{cls.server.server_port}/api/v1", "api_key": "k"}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "config.json"), "w") as f:
            json.dump({"show_posters": False}, f)
        Reelix.fail = False
        patcher = mock.patch.object(child, "ENABLED", True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_library_index_is_built_in_another_process(self):
        with mock.patch.object(library, "build", side_effect=AssertionError("built in the server")):
            self.assertEqual(library.refresh(self.dir, self.reelix, "films"), 3)
        index = library.load(self.dir, self.reelix, "films")
        self.assertEqual([e["t"] for e in index["items"]], ["Film 1", "Film 2", "Film 3"])

    def test_errors_come_back_as_the_same_kind(self):
        Reelix.fail = True
        with self.assertRaises(services.ServiceError) as caught:
            child.run("library", {"data_dir": self.dir, "reelix": self.reelix, "tab": "films"})
        self.assertEqual(caught.exception.status, 500)
        with self.assertRaisesRegex(ValueError, "Add Jellyfin"):
            child.run("import", {"data_dir": self.dir, "services": []})

    def test_what_it_logs_goes_to_the_servers_log(self):
        class Log:
            lines = []

            def detailed(self):
                return True

            def write(self, level, area, message, **extra):
                self.lines.append((level, area, message))
        with mock.patch.object(logs, "_current", Log()):
            child.run("library", {"data_dir": self.dir, "reelix": self.reelix, "tab": "films"})
        self.assertTrue(any(level == "detail" and area == "apps" and "GET /movies 200" in message for level, area, message in Log.lines), Log.lines)

    def test_the_live_tv_plugin_run_goes_through_it(self):
        from starboard import livetv_plugin
        with mock.patch.object(child, "ENABLED", False), mock.patch.object(livetv_plugin, "run_once", return_value="Guides refreshed") as run:
            self.assertEqual(child.run("livetv-plugin", {"force": True}), "Guides refreshed")
        run.assert_called_once_with(force=True)

    def test_off_runs_here(self):
        with mock.patch.object(child, "ENABLED", False), mock.patch.object(child, "_work", return_value="done here") as work:
            self.assertEqual(child.run("import", {"x": 1}), "done here")
        work.assert_called_once_with("import", {"x": 1})


if __name__ == "__main__":
    unittest.main()
