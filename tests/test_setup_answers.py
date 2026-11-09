"""The set-up's TMDB key, language of releases and Usenet server answers (DASH-178, DASH-189, DASH-183)."""
import json
import os
import socketserver
import tempfile
import threading
import unittest
from unittest import mock

from starboard import setup_answers, stack

TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJtYWRlLXVwIn0.c2lnbmF0dXJl"  # made up, the shape of a TMDB read token


class News(socketserver.StreamRequestHandler):
    """A stand-in news server: greets, then accepts one user name and password."""

    def handle(self):
        self.wfile.write(b"200 stand-in news server ready\r\n")
        user = None
        for raw in self.rfile:
            line = raw.decode().strip()
            if line.startswith("AUTHINFO USER "):
                user = line.split(" ", 2)[2]
                self.wfile.write(b"381 password please\r\n")
            elif line.startswith("AUTHINFO PASS "):
                ok = user == "made-up-user" and line.split(" ", 2)[2] == "made-up-pass"
                self.wfile.write(b"281 welcome\r\n" if ok else b"481 no\r\n")
            elif line == "QUIT":
                self.wfile.write(b"205 bye\r\n")
                return


class Answers(unittest.TestCase):
    def test_tmdb_keys_of_both_kinds_and_nothing_else(self):
        self.assertEqual(setup_answers.clean_tmdb(""), "")
        self.assertEqual(setup_answers.clean_tmdb("0123456789abcdef0123456789abcdef"), "0123456789abcdef0123456789abcdef")
        self.assertEqual(setup_answers.clean_tmdb(TOKEN), TOKEN)
        with self.assertRaises(ValueError):
            setup_answers.clean_tmdb("not a key")

    def test_the_key_goes_in_the_field_reelix_reads(self):
        self.assertEqual(setup_answers.tmdb_settings(TOKEN, {"language": "en-GB"}), {"language": "en-GB", "tmdb_read_token": TOKEN})
        self.assertEqual(setup_answers.tmdb_settings("0123456789abcdef0123456789abcdef", {})["tmdb_api_key"], "0123456789abcdef0123456789abcdef")

    def test_language_choices(self):
        for v in ("English", "Original", ""):
            self.assertEqual(setup_answers.clean_language(v), v)
        with self.assertRaises(ValueError):
            setup_answers.clean_language("Klingon")

    def test_language_goes_on_video_profiles_only(self):
        class R:
            puts = []

            def call(self, method, path, body=None):
                if method == "GET":
                    return 200, [{"id": 1, "name": "HD", "language": "English"}, {"id": 2, "name": "Any", "language": None},
                                 {"id": 3, "name": "Music", "family": "music", "language": None}]
                self.puts.append((path, body["language"]))
                return 200, body
        r = R()
        setup_answers.apply_language(r, "Original")
        self.assertEqual(r.puts, [("/qualityprofiles/1", "Original"), ("/qualityprofiles/2", "Original")])

    def test_usenet_server_is_checked(self):
        self.assertIsNone(setup_answers.clean_usenet({}))
        s = setup_answers.clean_usenet({"host": "News.Example.com", "username": "u", "password": "p"})
        self.assertEqual((s["host"], s["port"], s["ssl"], s["connections"]), ("news.example.com", 563, True, 8))
        for bad in ({"host": "not a host"}, {"host": "news.example.com", "port": 70000}, {"host": "news.example.com", "password": "a\nb"}):
            with self.assertRaises(ValueError):
                setup_answers.clean_usenet(bad)

    def test_the_server_test_signs_in_like_a_usenet_app(self):
        srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), News)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.addCleanup(srv.server_close)
        port = srv.server_address[1]
        with mock.patch.object(setup_answers, "HOST_RE", mock.Mock(match=lambda h: True)):
            ok = {"host": "127.0.0.1", "port": port, "ssl": False, "username": "made-up-user", "password": "made-up-pass"}
            self.assertTrue(setup_answers.test_usenet(ok))
            with self.assertRaisesRegex(ValueError, "did not accept"):
                setup_answers.test_usenet({**ok, "password": "wrong"})

    def test_the_server_waits_in_a_private_file_and_reaches_nzbget(self):
        with tempfile.TemporaryDirectory() as d:
            setup_answers.save_usenet(d, {"host": "news.example.com", "username": "made-up-user", "password": "made-up-pass"})
            path = os.path.join(stack.folder(d), setup_answers.USENET_FILE)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            calls = []

            def rpc(method, params=None):
                calls.append(method)
                return [] if method == "config" else True
            with mock.patch.object(stack, "chosen_keys", return_value=["nzbget"]), \
                    mock.patch("starboard.reelix_setup.nzbget_rpc", return_value=rpc), \
                    mock.patch.object(stack, "nzbget_key", return_value="made-up"):
                lines = setup_answers.apply_usenet(d)
            self.assertEqual(lines, ["Added your Usenet server to NZBGet"])
            self.assertEqual(calls, ["config", "saveconfig", "reload"])
            self.assertFalse(os.path.exists(path))

    def test_both_set_ups_read_the_same_words(self):
        with open(os.path.join(setup_answers.HERE, "web", "setup-answers.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), setup_answers.WORDS)

    def test_both_set_ups_ask_films_and_series_after_the_sites(self):
        from starboard import terminal_setup as ts
        with open(os.path.join(setup_answers.HERE, "web", "js", "install.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn('fetch("/setup-answers.json"', js)
        self.assertLess(js.index('stepNamed(T, "sites")'), js.index('stepNamed(T, "films")'))
        self.assertIn("/api/setup/test-tmdb", js)
        self.assertIn("/api/setup/test-usenet", js)
        for words in (setup_answers.WORDS["tmdb"]["intro"], setup_answers.WORDS["usenet"]["server_intro"]):
            self.assertNotIn(words, js, "Words belong in web/setup-answers.json, not in install.js")
        ids = ts.job_steps({"start": "new", "choice": {"apps": ["reelix", "nzbget"]}})
        self.assertEqual(ids[ids.index("sites") + 1], "films")
        self.assertNotIn("films", ts.job_steps({"start": "new", "choice": {"apps": ["jellyfin"]}}))


if __name__ == "__main__":
    unittest.main()
