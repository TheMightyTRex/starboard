"""Signing in to Plex with its link code (DASH-595): a code from plex.tv, polled only while the page asks, the token kept on
the server and never shown or logged, Plex's token never read from its container. plex.tv is a made-up stand-in."""
import io
import tempfile
import unittest
import urllib.error
from unittest import mock

from starboard import discovery, logs, plex_link

TOKEN = "made-up-token-abc123XYZ789"


class FakePlexTv:
    def __init__(self):
        self.calls = []
        self.token = None
        self.fail = None

    def __call__(self, url, method="GET", body=None, headers=None, timeout=10, limit=None):
        self.calls.append((method, url, dict(headers or {})))
        if self.fail:
            raise self.fail
        if method == "POST":
            return {"id": 4242, "code": "AB12", "expiresIn": 900, "authToken": None}
        return {"id": 4242, "code": "AB12", "authToken": self.token}


class PlexLinkTest(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp()
        self.tv = FakePlexTv()
        self.clock = [1000.0]
        plex_link.reset()

    def tearDown(self):
        plex_link.reset()

    def now(self):
        return self.clock[0]

    def start(self):
        return plex_link.start(self.data, call=self.tv, now=self.now)

    def poll(self, pid=4242):
        return plex_link.poll(pid, call=self.tv, now=self.now)

    def test_a_code_is_asked_for_and_shown_with_the_link_page(self):
        got = self.start()
        self.assertEqual((got["id"], got["code"], got["link"]), (4242, "AB12", "https://plex.tv/link"))
        method, url, headers = self.tv.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.startswith("https://plex.tv/api/v2/pins"))
        self.assertEqual(headers["X-Plex-Product"], "Starboard")
        self.assertGreaterEqual(len(headers["X-Plex-Client-Identifier"]), 16)

    def test_the_client_name_is_made_once_and_kept(self):
        self.start()
        self.start()
        first, second = self.tv.calls[0][2], self.tv.calls[1][2]
        self.assertEqual(first["X-Plex-Client-Identifier"], second["X-Plex-Client-Identifier"])

    def test_waiting_then_approved_and_the_token_is_not_in_the_answer(self):
        self.start()
        self.assertEqual(self.poll()["state"], "waiting")
        self.tv.token = TOKEN
        self.clock[0] += 3
        got = self.poll()
        self.assertEqual(got["state"], "approved")
        self.assertNotIn(TOKEN, repr(got))
        self.assertEqual(plex_link.token_of(4242, keep=True, now=self.now), TOKEN)  # a test of the connection
        self.assertEqual(plex_link.token_of(4242, now=self.now), TOKEN)  # the save takes it
        self.assertEqual(plex_link.token_of(4242, now=self.now), "")  # and only once

    def test_a_quick_second_ask_does_not_call_plex_again(self):
        self.start()
        self.poll()
        self.poll()
        self.assertEqual(len([c for c in self.tv.calls if c[0] == "GET"]), 1)
        self.clock[0] += 2
        self.poll()
        self.assertEqual(len([c for c in self.tv.calls if c[0] == "GET"]), 2)

    def test_the_code_runs_out_after_five_minutes_and_nothing_more_is_asked(self):
        self.start()
        self.clock[0] += plex_link.LIFE + 1
        self.assertEqual(self.poll()["state"], "expired")
        self.assertEqual([c for c in self.tv.calls if c[0] == "GET"], [])
        self.tv.token = TOKEN
        self.assertEqual(plex_link.token_of(4242, now=self.now), "")

    def test_cancel_forgets_the_code(self):
        self.start()
        plex_link.cancel(4242)
        self.assertEqual(self.poll()["state"], "expired")

    def test_nothing_is_asked_without_a_request_from_the_page(self):
        self.start()
        self.clock[0] += 120
        self.assertEqual(len(self.tv.calls), 1)  # only the code itself: the server has no timer of its own

    def test_at_most_three_codes_wait_and_the_oldest_goes(self):
        for pid in (1, 2, 3, 4):
            self.clock[0] += 1
            plex_link.start(self.data, call=lambda *a, _p=pid, **k: {"id": _p, "code": "ZZ99"}, now=self.now)
        self.assertEqual(sorted(plex_link._pending), [2, 3, 4])

    def test_plex_tv_unreachable_is_said_in_words(self):
        self.tv.fail = urllib.error.URLError("no route")
        with self.assertRaises(plex_link.LinkError) as e:
            self.start()
        self.assertIn("paste the token", str(e.exception))
        self.assertNotIn("no route", str(e.exception))

    def test_an_answer_that_is_not_a_code_is_refused(self):
        with self.assertRaises(plex_link.LinkError):
            plex_link.start(self.data, call=lambda *a, **k: {"id": "x", "code": "<script>"}, now=self.now)

    def test_plex_tv_dropping_the_code_ends_it(self):
        self.start()
        self.tv.fail = urllib.error.HTTPError("u", 404, "gone", {}, io.BytesIO(b""))
        self.assertEqual(self.poll()["state"], "expired")

    def test_a_token_that_does_not_look_like_one_is_ignored(self):
        self.start()
        self.tv.token = "x y\n"
        self.assertEqual(self.poll()["state"], "waiting")

    def test_the_token_is_never_logged(self):
        events = []
        with mock.patch.object(logs, "event", side_effect=lambda *a, **k: events.append(a)):
            self.start()
            self.tv.token = TOKEN
            self.clock[0] += 3
            self.poll()
            plex_link.token_of(4242, now=self.now)
        self.assertNotIn(TOKEN, repr(events))


class TokenIsNotReadFromThePlexContainerTest(unittest.TestCase):
    def test_no_key_file_for_plex(self):
        self.assertNotIn("plex", discovery.KEY_FILES)
        self.assertNotIn("plex", discovery.READABLE)
        self.assertIsNone(discovery.read_key("plex", "plex"))

    def test_nothing_in_the_code_looks_for_plexs_preferences_file(self):
        import os
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starboard")
        for name in os.listdir(root):
            if name.endswith((".py", ".sh")):
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    self.assertNotIn("PlexOnlineToken", f.read(), name)


if __name__ == "__main__":
    unittest.main()
