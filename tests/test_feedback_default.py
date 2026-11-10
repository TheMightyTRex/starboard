"""Send feedback (Snaglist) is on by default on every page, with a switch in Settings, General (owner, 10 November 2026)."""
import json
import os
import pathlib
import tempfile
import unittest

from starboard.config import Config

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FeedbackDefaultTest(unittest.TestCase):
    def test_on_for_a_new_install(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(Config(d).data["ux_notes"])

    def test_switched_on_once_for_an_existing_install_then_the_switch_decides(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            path = os.path.join(d, "config.json")
            data = json.load(open(path))
            data["ux_notes"] = False
            data.pop("feedback_default_on", None)  # as an install from before 0.15.2
            json.dump(data, open(path, "w"))
            self.assertTrue(Config(d).data["ux_notes"])
            c = Config(d)
            c.update_general({"ux_notes": False})
            self.assertFalse(Config(d).data["ux_notes"])  # the person's choice stays

    def test_the_copy_is_snaglists_own(self):
        self.assertIn('const VERSION = "0.4.0"', (ROOT / "web/js/snaglist.js").read_text())


class StylesBeforeSignInTest(unittest.TestCase):
    def test_the_styles_file_is_css_before_sign_in(self):
        import http.client
        import threading
        from starboard import auth
        from starboard.server import make_server
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        with tempfile.TemporaryDirectory() as d:
            server, _ = make_server("127.0.0.1", 0, d)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
                conn.request("GET", "/api/styles.css")
                r = conn.getresponse()
                r.read()
                self.assertEqual((r.status, r.getheader("Content-Type")), (200, "text/css; charset=utf-8"))
            finally:
                server.shutdown()


if __name__ == "__main__":
    unittest.main()
