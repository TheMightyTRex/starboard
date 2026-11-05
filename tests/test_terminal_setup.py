"""The terminal-only set-up (DASH-86): answers typed in turn against a real Starboard on this computer."""
import io
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, terminal_setup
from starboard.server import make_server

PASSWORD = "correct horse battery"


class Answers:
    """Plays the person at the keyboard: each call takes the next answer and keeps the prompt."""

    def __init__(self, answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt=""):
        self.prompts.append(prompt)
        if not self.answers:
            raise AssertionError(f"No answer left for: {prompt}")
        return self.answers.pop(0)


class TerminalSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k, v in {"STARBOARD_HISTORY": "0", "STARBOARD_SCHEDULE": "0", "STARBOARD_WATCH": "0", "STARBOARD_JOBS": "0",
                     "STARBOARD_DOCKER": "/nonexistent/docker.sock"}.items():
            os.environ[k] = v
        # Nothing found running: this computer's own apps must not change what the questions offer.
        patcher = mock.patch("starboard.server.discovery.search", return_value={"items": []})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.port = self.server.server_address[1]
        self.api = terminal_setup.Api(self.port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def term(self, typed, hidden):
        out = io.StringIO()
        return terminal_setup.Terminal(out=out, ask=Answers(typed), secret=Answers(hidden)), out

    def test_whole_set_up_with_the_recommended_answers(self):
        media, settings = os.path.join(self.tmp.name, "media"), os.path.join(self.tmp.name, "config")
        typed = ["", "", "", media, settings, "y", "", "", ""]
        term, out = self.term(typed, [PASSWORD, PASSWORD])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        self.assertFalse(self.app.needs_setup)
        self.assertTrue(auth.check_password(PASSWORD, self.app.config.data["auth"]["password_hash"]))
        self.assertNotIn(PASSWORD, text)  # typed hidden, never shown
        # No Docker access here: the files are written, and the command to start them is shown.
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "stack", "compose.yaml")))
        self.assertIn("docker compose -p media-stack up -d", text)
        self.assertEqual(self.app.config.data["download_hours"], {"enabled": True, "start": 1, "end": 7})

    def test_help_mismatch_and_short_passwords_ask_again(self):
        term, out = self.term(["2", "2"], ["?", "short", PASSWORD, "different words", PASSWORD, PASSWORD])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        self.assertIn("a few unrelated words", text)
        self.assertIn("Use at least 10 characters", text)
        self.assertIn("did not match", text)
        self.assertFalse(self.app.config.data["download_hours"]["enabled"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "stack", "compose.yaml")))

    def test_wrong_number_and_question_mark_then_q_stops(self):
        term, out = self.term(["9", "?", "q"], [PASSWORD, PASSWORD])
        with self.assertRaises(terminal_setup.Stop):
            terminal_setup.run(self.api, term, self.tmp.name, self.port)
        self.assertIn("Type a number from 1 to 2", out.getvalue())
        self.assertIn("Each kind of media installs", out.getvalue())

    def test_signs_in_when_a_password_is_set(self):
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": PASSWORD})
        api = terminal_setup.Api(self.port)
        term, out = self.term(["2", "2"], ["wrong password here", PASSWORD])
        self.assertEqual(terminal_setup.run(api, term, self.tmp.name, self.port), 0)
        self.assertIn("That password is not right", out.getvalue())
        self.assertIn("Signed in.", out.getvalue())

    def test_vpn_details_are_asked_and_kept_out_of_the_screen(self):
        media, settings = os.path.join(self.tmp.name, "media"), os.path.join(self.tmp.name, "config")
        # Downloads and VPN only, every default app; Proton VPN over WireGuard.
        typed = ["", "8,9", "", media, settings, "1", "1", "", "192.168.1.20/32", "y", "2"]
        term, out = self.term(typed, [PASSWORD, PASSWORD, "secret-wireguard-key"])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        self.assertIn("affiliate links", text)
        self.assertNotIn("secret-wireguard-key", text)
        with open(os.path.join(self.tmp.name, "stack", ".env")) as f:
            env = f.read()
        self.assertIn("VPN_SERVICE_PROVIDER=protonvpn", env)
        self.assertIn("secret-wireguard-key", env)

    def test_bad_hours_ask_again(self):
        term, out = self.term(["2", "", "5", "5", "22", "6"], [PASSWORD, PASSWORD])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        self.assertIn("That did not work", out.getvalue())
        self.assertEqual(self.app.config.data["download_hours"], {"enabled": True, "start": 22, "end": 6})

    def test_needs_a_terminal(self):
        import sys
        stdin = sys.stdin
        sys.stdin = io.StringIO("")
        try:
            self.assertEqual(terminal_setup.main(["--port", str(self.port)]), 2)
        finally:
            sys.stdin = stdin


if __name__ == "__main__":
    unittest.main()
