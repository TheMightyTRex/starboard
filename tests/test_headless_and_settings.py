"""Running with no screen (DASH-89) and settings from the terminal (DASH-90).

deploy/headless.sh changes this computer's system settings, so it is never run here: only its words and shape are
checked (bash -n reads it without running it). The terminal settings run against a real Starboard on this computer."""
import io
import os
import pathlib
import subprocess
import tempfile
import threading
import unittest

from starboard import auth, terminal_settings
from starboard.server import make_server
from tests.test_terminal_setup import Answers

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "deploy" / "headless.sh"


class HeadlessScriptTest(unittest.TestCase):
    def test_it_parses_and_is_never_run_by_other_scripts(self):
        self.assertEqual(subprocess.run(["bash", "-n", str(SCRIPT)]).returncode, 0)
        for name in ("install.sh", "run-first.sh", "update.sh", "starter.sh"):
            text = (ROOT / name).read_text()
            self.assertNotIn("deploy/headless.sh --", text, name)
            for line in text.splitlines():
                if "deploy/headless.sh" in line:  # only ever shown as a command to type
                    self.assertIn("card_row", line, name)

    def test_it_shows_then_asks_then_changes_and_can_undo(self):
        text = SCRIPT.read_text()
        self.assertLess(text.index('tell "   Change: $(will "$c")."'), text.index("ask_choice \"Your choice\" 3"))
        self.assertLess(text.index("ask_choice \"Your choice\" 3"), text.index('if apply "$c"; then'))
        self.assertIn("Nothing has changed yet.", text)
        for change in ("systemctl mask", "GRUB_TIMEOUT=2", "GRUB_RECORDFAIL_TIMEOUT=5", "fsck.repair=yes", "kernel.panic = 10",
                       "HandleLidSwitch=ignore", "HandlePowerKey=poweroff", "RuntimeWatchdogSec=30s"):
            self.assertIn(change, text)
        self.assertIn("--undo", text)
        self.assertIn("save_copy", text)
        self.assertIn("Restore on AC power loss", text)  # the firmware help
        self.assertNotIn("rm -", text)  # undo moves its files aside; it never deletes

    def test_words_follow_the_content_rules(self):
        import re
        text = SCRIPT.read_text()
        self.assertNotIn("—", text)
        self.assertIsNone(re.search(r"\b(can't|won't|don't|doesn't|isn't|it's|you're)\b", text))


class TerminalSettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = terminal_settings.Api(self.server.server_address[1])
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"})
        self.api = terminal_settings.Api(self.server.server_address[1])  # signed out: the settings sign in themselves

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_deactivate_the_update_check_through_the_api(self):
        self.assertTrue(self.app.config.data["update_check"])
        out = io.StringIO()
        # Automatic updates; 2 deactivates looking for new versions; Enter; Enter (Done, recommended); 2 closes.
        term = terminal_settings.Terminal(out=out, ask=Answers(["", "2", "", "", "2"]), secret=Answers(["correct horse battery"]), fancy=False)
        self.assertEqual(terminal_settings.run(self.api, term, "0.0.0"), 0)
        self.assertFalse(self.app.config.data["update_check"])
        text = out.getvalue()
        self.assertIn("Look for new versions is now inactive.", text)
        self.assertIn("Done: back to the settings (recommended)", text)
        self.assertNotIn("correct horse battery", text)

    def test_the_versions_to_go_back_to(self):
        tags = terminal_settings.releases(run=lambda cmd: "v0.17.0\nv0.16.2\nv0.16.1\n")
        self.assertEqual(tags, ["v0.17.0", "v0.16.2", "v0.16.1"])
        self.assertTrue((ROOT / "settings.sh").stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
