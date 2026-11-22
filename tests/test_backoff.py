"""Backing off from apps that are not responding (DASH-66): checked less often up to a limit, back to every check as
soon as they answer, and Check again always checks."""

import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import services


class App(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        raw = json.dumps({"version": "4.0.0", "records": []}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class BackOffTest(unittest.TestCase):
    def setUp(self):
        for store in (services.RECENT, services.DOWN_SINCE, services._backoff, services.SAID_DOWN):
            store.clear()
        self.gone = {"id": "gone", "name": "Gone", "type": "sonarr", "url": "http://127.0.0.1:9", "api_key": "k", "enabled": True}
        self.clock = [1000.0]
        patch = mock.patch.object(services.time, "monotonic", lambda: self.clock[0])
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(services._backoff.clear)

    def checks(self):
        return len(services.RECENT["gone"])

    def test_the_wait_doubles_up_to_the_limit(self):
        self.assertEqual([services.backoff_wait(n) for n in range(1, 9)], [0, 30, 60, 120, 240, 300, 300, 300])
        self.assertEqual(services.backoff_wait(500), services.BACKOFF_MAX)

    def test_an_app_that_is_down_is_checked_less_often(self):
        for _ in range(2):  # the first two checks run at the usual pace, as alerts need two in a row
            services.status_all([self.gone])
            self.clock[0] += 15
        self.assertEqual(self.checks(), 2)
        row = services.status_all([self.gone])[0]  # 15 seconds after the second: not due for another 15
        self.assertEqual(self.checks(), 2)
        self.assertEqual((row["state"], row["check_every"]), ("down", 30))
        self.assertIn("down_since", row)
        self.clock[0] += 15
        services.status_all([self.gone])  # due now
        self.assertEqual(self.checks(), 3)
        self.clock[0] += 59
        services.status_all([self.gone])
        self.assertEqual(self.checks(), 3)
        self.clock[0] += 1
        self.assertEqual(services.status_all([self.gone])[0]["check_every"], 120)
        self.assertEqual(self.checks(), 4)

    def test_never_longer_than_the_limit(self):
        for _ in range(12):
            services.status_all([self.gone], fresh=True)
        before = self.checks()
        self.clock[0] += services.BACKOFF_MAX - 1
        services.status_all([self.gone])
        self.assertEqual(self.checks(), before)
        self.clock[0] += 1
        services.status_all([self.gone])
        self.assertEqual(self.checks(), before + 1)

    def test_check_again_always_checks(self):
        for _ in range(3):
            services.status_all([self.gone], fresh=True)
        self.assertEqual(self.checks(), 3)
        services.status_all([self.gone], only="gone")
        self.assertEqual(self.checks(), 4)
        services.status_all([self.gone])
        self.assertEqual(self.checks(), 4)

    def test_back_to_every_check_as_soon_as_it_answers(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), App)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        for _ in range(4):
            services.status_all([self.gone], fresh=True)
        self.assertIn("gone", services._backoff)
        back = dict(self.gone, url=f"http://127.0.0.1:{server.server_address[1]}")
        services._backoff["gone"]["url"] = back["url"]  # the same app, started again at its address
        services._queue_one(back)  # anything it answers, here its queue, ends the wait
        self.assertNotIn("gone", services._backoff)
        row = services.status_all([back])[0]
        self.assertEqual(row["state"], "up")
        self.assertNotIn("check_every", row)
        self.clock[0] += 15
        services.status_all([back])
        self.assertEqual([c["state"] for c in services.RECENT["gone"]][-2:], ["up", "up"])

    def test_a_changed_address_is_checked_at_once(self):
        for _ in range(4):
            services.status_all([self.gone], fresh=True)
        before = self.checks()
        services.status_all([dict(self.gone, url="http://127.0.0.1:10")])
        self.assertEqual(self.checks(), before + 1)

    def test_an_app_that_follows_one_backing_off_shows_its_last_answer(self):
        for _ in range(3):
            services.status_all([self.gone], fresh=True)
        before = self.checks()
        rows = services.status_all([self.gone, {"id": "f", "name": "F", "type": "link", "follows": "gone", "enabled": True}])
        self.assertEqual(self.checks(), before)
        self.assertEqual(rows[1]["state"], "down")

    def test_the_public_api_does_not_carry_the_dashboards_detail(self):
        import pathlib
        text = (pathlib.Path(__file__).resolve().parent.parent / "starboard" / "api_v1.py").read_text(encoding="utf-8")
        self.assertIn('if k != "check_every"', text)


if __name__ == "__main__":
    unittest.main()
