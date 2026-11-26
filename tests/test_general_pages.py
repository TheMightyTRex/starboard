"""Alerts and Performance are part of General (DASH-584, owner, 26 November 2026): their tabs sit in General's menu, their
pages have their new addresses, and the old addresses answer 301 with the new one, keeping what follows the page."""
import http.client
import os
import tempfile
import threading
import unittest

from starboard import auth, server, shell

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = {"settings-general-alerts.html": "Alerts", "settings-general-performance.html": "Performance", "settings-general-pictures.html": "Pictures"}
OLD = {"/settings-alerts.html": "/settings-general-alerts.html", "/settings-performance.html": "/settings-general-performance.html",
       "/settings-performance-pictures.html": "/settings-general-pictures.html"}


class Menu(unittest.TestCase):
    def test_the_tabs_are_general_s(self):
        settings = next(items for key, _n, _i, items in shell.MENU if key == "settings")
        groups = {name: [p for p, _l, _i in pages] for name, _icon, pages in settings}
        for page, label in NEW.items():
            self.assertIn(page, groups["General"])
            self.assertEqual(shell.PAGES[page], ("settings", [n for n, _i, _p in settings].index("General")))
        self.assertNotIn("Alerts", groups)
        self.assertNotIn("Performance", groups)
        labels = [(p, l) for _name, _icon, pages in settings for p, l, _i in pages]
        for page, label in NEW.items():
            self.assertIn((page, label), labels)

    def test_the_pages_moved_and_the_old_files_are_gone(self):
        for new in NEW:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "web", new)), new)
        for old in OLD:
            self.assertFalse(os.path.exists(os.path.join(ROOT, "web", old.lstrip("/"))), old)
        self.assertEqual(server.MOVED_PAGES.get("/settings-alerts.html"), "/settings-general-alerts.html")

    def test_every_page_has_its_help(self):
        for page in NEW:
            self.assertIn(page, shell.HELP, page)
        self.assertTrue(all(old.lstrip("/") not in shell.HELP for old in OLD))

    def test_no_page_script_links_an_old_address(self):
        bad = []
        for folder in ("web", os.path.join("web", "js")):
            for name in os.listdir(os.path.join(ROOT, folder)):
                if name.endswith((".html", ".js")):
                    with open(os.path.join(ROOT, folder, name), encoding="utf-8") as f:
                        text = f.read()
                    bad += [name for old in OLD if old.lstrip("/") in text]
        self.assertEqual(bad, [])


class Redirect(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = server.make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path):
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=10)
        c.request("GET", path)
        r = c.getresponse()
        r.read()
        c.close()
        return r

    def test_old_addresses_move(self):
        for old, new in OLD.items():
            r = self.get(old)
            self.assertEqual((r.status, r.getheader("Location")), (301, new))
            r = self.get(old + "?x=1")
            self.assertEqual(r.getheader("Location"), new + "?x=1")


if __name__ == "__main__":
    unittest.main()
