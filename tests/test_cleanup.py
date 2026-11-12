"""System, Clean up (DASH-77): what is left over, the holding folder, putting back, and deleting for good only when
the person asks, with their password. Owner rule: Starboard never deletes for good by itself."""
import json
import os
import pathlib
import tempfile
import threading
import time
import unittest

from starboard import auth, cleanup
from starboard.server import make_server
from starboard.terminal_setup import Api, Problem

ROOT = pathlib.Path(__file__).resolve().parent.parent


def make_left_overs(data):
    removed = pathlib.Path(data, "plugins", ".removed", "radio-20261101-101010")
    removed.mkdir(parents=True)
    (removed / "manifest.json").write_text("x" * 1000)
    copies = pathlib.Path(data, "backups")
    copies.mkdir()
    old = time.time() - 200 * 86400
    for n in range(12):
        f = copies / f"config-2026010{n % 10}-{n:02d}-migration.json"
        f.write_text("{}")
        os.utime(f, (old, old))
    pathlib.Path(data, "backup-work").mkdir()


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = os.path.join(self.tmp.name, "data")
        os.mkdir(self.data)
        make_left_overs(self.data)

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_what_is_left_over_with_sizes(self):
        items = cleanup.left_over(self.data)
        kinds = [i["kind"] for i in items]
        self.assertEqual(kinds.count("plugin"), 1)
        self.assertEqual(kinds.count("copy"), 0)  # saved copies are kept or removed by their own setting (DASH-109)
        self.assertEqual(kinds.count("work"), 1)
        plugin = next(i for i in items if i["kind"] == "plugin")
        self.assertEqual(plugin["what"], "A removed plug-in: radio")
        self.assertEqual(plugin["size"], 1000)
        self.assertTrue(all(i["movable"] for i in items))
        self.assertNotIn("work", [i["kind"] for i in cleanup.left_over(self.data, backup_running=True)])

    def test_hold_put_back_and_delete_for_good(self):
        items = cleanup.left_over(self.data)
        plugin = next(i for i in items if i["kind"] == "plugin")
        cleanup.hold(self.data, [plugin["id"]])
        self.assertFalse(os.path.exists(os.path.join(self.data, "plugins", ".removed", "radio-20261101-101010")))
        held = cleanup.holding(self.data)
        self.assertEqual(len(held), 1)
        self.assertTrue(held[0]["from"].endswith("radio-20261101-101010"))
        cleanup.put_back(self.data, held[0]["id"])
        self.assertTrue(os.path.exists(os.path.join(self.data, "plugins", ".removed", "radio-20261101-101010")))
        self.assertEqual(cleanup.holding(self.data), [])
        cleanup.hold(self.data, [i["id"] for i in cleanup.left_over(self.data)])
        self.assertEqual(cleanup.left_over(self.data), [])
        held = cleanup.holding(self.data)
        self.assertEqual(len(held), 2)  # the removed plug-in and the work folder; saved copies are DASH-109's
        freed = cleanup.delete_for_good(self.data, next(i for i in held if i["kind"] == "plugin")["id"])
        self.assertEqual(freed, 1000)
        self.assertEqual(len(cleanup.holding(self.data)), 1)

    def test_a_request_never_names_a_path(self):
        with self.assertRaises(ValueError):
            cleanup.hold(self.data, ["/etc"])
        with self.assertRaises(ValueError):
            cleanup.delete_for_good(self.data, "../../etc")
        with self.assertRaises(ValueError):
            cleanup.put_back(self.data, "nothing")


class CleanupApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = Api(self.server.server_address[1])
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"})
        make_left_overs(self.tmp.name)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_deleting_needs_the_password(self):
        found = self.api.call("GET", "/api/cleanup")
        self.assertEqual(len(found["left_over"]), 2)
        moved = self.api.call("POST", "/api/cleanup/hold", {"ids": [found["left_over"][0]["id"]]})
        self.assertEqual(len(moved["holding"]), 1)
        item = moved["holding"][0]["id"]
        with self.assertRaises(Problem):
            self.api.call("POST", "/api/cleanup/delete", {"id": item, "password": "wrong password"})
        self.assertEqual(len(self.api.call("GET", "/api/cleanup")["holding"]), 1)
        done = self.api.call("POST", "/api/cleanup/delete", {"id": item, "password": "correct horse battery"})
        self.assertEqual(done["holding"], [])

    def test_the_pages_and_menu(self):
        shell = (ROOT / "tools" / "apply_shell.py").read_text()
        self.assertIn('("Clean up", "trash-2", [("system-cleanup.html", "What is left over"', shell)
        self.assertIn('("system-holding.html", "Holding folder"', shell)
        js = (ROOT / "web" / "js" / "system-cleanup.js").read_text()
        self.assertIn("This cannot be undone.", js)
        self.assertIn("danger: true", js)
        steps = json.loads((ROOT / "web" / "setup-steps.json").read_text())["steps"]
        self.assertIn("cleanup", [s["id"] for s in steps])
        self.assertIn('{ id: "cleanup"', (ROOT / "web" / "js" / "settings.js").read_text())


if __name__ == "__main__":
    unittest.main()
