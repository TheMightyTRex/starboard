"""Location and keyboard first (DASH-259) and help with symbols when the layout is wrong (DASH-112): one list for the
Run first script, both set-ups and the installer; the arrow-key list in the Run first script and the terminal set-up;
the recommended answer from what the Run first script chose, then this computer's own. 13 November 2026."""
import fcntl
import json
import os
import pathlib
import pty
import select
import struct
import subprocess
import tempfile
import termios
import time
import unittest

from starboard import places, start

ROOT = pathlib.Path(__file__).resolve().parent.parent


class ListsTest(unittest.TestCase):
    def test_run_firsts_copy_is_the_same(self):
        script = (ROOT / "run-first.sh").read_text(encoding="utf-8")
        copy = script[script.index("# places: start"):script.index("# places: end") + len("# places: end") + 1]
        self.assertEqual(copy, places.bash_block(), "Copy starboard/places.py's bash_block() into run-first.sh")

    def test_every_location_suggests_a_known_keyboard_and_time_zones_are_unique(self):
        for title, tz, kid, lang in places.LOCATIONS:
            self.assertIn(kid, places.KEYBOARD_IDS, title)
            self.assertRegex(tz, places.TZ_RE)
            self.assertTrue(lang.endswith(".UTF-8"), lang)
        tzs = [p[1] for p in places.LOCATIONS]
        self.assertEqual(len(tzs), len(set(tzs)))
        self.assertEqual(places.LOCATIONS[0][0], "United Kingdom")

    def test_the_recommended_one_comes_first_and_says_so(self):
        o = places.options({"tz": "Europe/Paris", "keyboard": ""})
        self.assertEqual(o["locations"][0]["tz"], "Europe/Paris")
        self.assertTrue(o["locations"][0]["recommended"])
        self.assertEqual(o["keyboards"][0]["id"], "fr")  # suggested from the location: the US default was nobody's choice
        self.assertEqual(sum(p["recommended"] for p in o["locations"]), 1)

    def test_a_layout_someone_chose_is_kept_and_the_run_first_answer_wins(self):
        self.assertEqual(places.recommended({"tz": "Europe/London", "keyboard": "de"}), ("Europe/London", "de"))
        self.assertEqual(places.recommended({"tz": "Europe/London", "keyboard": "us"}), ("Europe/London", "gb"))
        self.assertEqual(places.recommended({"tz": "Etc/UTC", "keyboard": ""}, {"tz": "Europe/Dublin", "keyboard": "ie"}),
                         ("Europe/Dublin", "ie"))

    def test_a_time_zone_not_in_the_list_is_kept_first(self):
        o = places.options({"tz": "Asia/Tokyo", "keyboard": "us"})
        self.assertEqual(o["locations"][0]["tz"], "Asia/Tokyo")
        self.assertIn("Keep this computer's time zone", o["locations"][0]["title"])

    def test_answers_are_checked(self):
        self.assertEqual(places.clean({"tz": "Europe/London", "keyboard": "gb"}), {"tz": "Europe/London", "keyboard": "gb"})
        for bad in ({"tz": "../etc", "keyboard": "gb"}, {"tz": "Europe/London; rm", "keyboard": "gb"}, {"tz": "Europe/London", "keyboard": "xx"}):
            with self.assertRaises(ValueError):
                places.clean(bad)

    def test_the_change_to_this_computer_only_holds_what_differs(self):
        self.assertEqual(places.change({"tz": "Europe/London", "keyboard": "gb"}, {"tz": "Europe/London", "keyboard": "gb"}),
                         {"timezone": "", "keyboard": ""})
        self.assertEqual(places.change({"tz": "Europe/London", "keyboard": "gb"}, {"tz": "Etc/UTC", "keyboard": "us"}),
                         {"timezone": "Europe/London", "keyboard": "gb"})
        # Unknown keyboard on this computer (no installer reading): never a change on a guess.
        self.assertEqual(places.change({"tz": "Etc/UTC", "keyboard": "gb"}, {"tz": "Etc/UTC", "keyboard": ""})["keyboard"], "")
        self.assertEqual(start.host_args({"timezone": "Europe/London", "keyboard": "gb"}),
                         ["--timezone", "Europe/London", "--keyboard", "gb"])
        self.assertEqual(start.host_args({"timezone": "../x", "keyboard": "nope"}), [])

    def test_reading_this_computer(self):
        out = {("timedatectl", "show", "-p", "Timezone", "--value"): "Europe/London\n",
               ("localectl", "status"): "   System Locale: LANG=en_GB.UTF-8\n       VC Keymap: (unset)\n      X11 Layout: gb\n       X11 Model: pc105\n"}
        found = places.read_computer(run=lambda cmd: out[tuple(cmd)])
        self.assertEqual((found["tz"], found["keyboard"]), ("Europe/London", "gb"))

    def test_symbols_for_a_uk_keyboard_with_the_us_layout(self):
        # DASH-112's first case: | is Shift and the # ~ key beside Enter, not the key marked \\ | by the left Shift.
        lines = places.symbols_help("gb")
        self.assertIn("| is Shift and the key marked # ~ (beside Enter)", lines)
        self.assertIn("@ is Shift and 2 (the key marked \")", lines)
        self.assertEqual(places.symbols_help("us"), [])
        self.assertEqual(places.symbols_help("ie"), [lines[0].replace("UK", "Irish")] + lines[1:])


class ServerTest(unittest.TestCase):
    def setUp(self):
        import threading
        from starboard import auth
        from starboard.server import make_server
        from starboard.terminal_setup import Api
        self.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = Api(self.server.server_address[1])
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"})

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_asked_unless_run_first_answered_and_the_answer_is_saved(self):
        self.assertFalse(self.api.call("GET", "/api/setup/place")["answered"])
        pathlib.Path(self.tmp.name, "run-first.json").write_text(json.dumps({"tz": "Europe/Dublin", "keyboard": "ie"}))
        got = self.api.call("GET", "/api/setup/place")
        self.assertTrue(got["answered"])
        self.assertEqual((got["tz"], got["keyboard"]), ("Europe/Dublin", "ie"))
        with unittest.mock.patch.dict(os.environ, {"TZ": "Etc/UTC", "STARBOARD_HOST_KEYBOARD": "us"}):
            saved = self.api.call("POST", "/api/setup/place", {"tz": "Europe/London", "keyboard": "gb"})
        self.assertEqual(saved["change"], {"timezone": "Europe/London", "keyboard": "gb"})
        again = self.api.call("GET", "/api/setup/place")
        self.assertFalse(again["answered"])  # asked again on a later run, with the saved answer first
        self.assertEqual((again["tz"], again["keyboard"]), ("Europe/London", "gb"))
        # The apps the set-up installs take the chosen time zone.
        self.assertEqual(self.api.call("GET", "/api/stack")["defaults"]["tz"], "Europe/London")


import unittest.mock  # noqa: E402


class TerminalStepsTest(unittest.TestCase):
    """The terminal set-up's two steps, answered in plain mode (numbers), as a screen reader user would."""

    def test_place_then_keyboard_and_the_symbols_help(self):
        import io
        from starboard import terminal_setup as ts
        from tests.test_terminal_setup import Answers

        class FakeApi:
            def __init__(self):
                self.posts = []

            def call(self, method, path, body=None):
                if path == "/api/setup/place" and method == "GET":
                    return {**places.options({"tz": "Etc/UTC", "keyboard": "us"}), "answered": False}
                if path == "/api/setup/place":
                    self.posts.append(body)
                    return {**body, "change": places.change(body, {"tz": "Etc/UTC", "keyboard": "us"})}
                if path == "/api/cleanup":
                    return {"left_over": []}
                raise AssertionError(path)

        out, api, state = io.StringIO(), FakeApi(), {}
        # UTC is kept first (recommended); 2 is the United Kingdom; ? shows the symbols; Enter takes the UK keyboard.
        term = ts.Terminal(out=out, ask=Answers(["2", "?", ""]), secret=Answers([]), fancy=False)
        self.assertTrue(ts.step_place(api, term, state))
        self.assertEqual(state["tz"], "Europe/London")
        self.assertTrue(ts.step_keyboard(api, term, state))
        self.assertEqual(api.posts, [{"tz": "Europe/London", "keyboard": "gb"}])
        self.assertEqual(state["host"], {"timezone": "Europe/London", "keyboard": "gb"})
        text = out.getvalue()
        self.assertIn("UK (recommended)", text)
        self.assertIn("| is Shift and the key marked # ~ (beside Enter)", text)
        self.assertEqual(state["left_over"], [])


class RunFirstPickTest(unittest.TestCase):
    """Run first's arrow-key list, in a pretend terminal as a person uses it: Down then Enter, letters to jump, and a
    number then Enter. Plain mode keeps numbered answers."""

    def run_pick(self, keys, plain=False):
        script = (ROOT / "run-first.sh").read_text(encoding="utf-8")
        frame = script[script.index("# terminal-frame: start"):script.index("# terminal-frame: end")]
        part = script[script.index("# Location and keyboard (DASH-259)"):script.index("# The steps ----")]
        with tempfile.TemporaryDirectory() as d:
            result = os.path.join(d, "choice")
            body = (f"APP_NAME=Starboard; APP_VERSION=0; ISSUES=x/y; LOG={d}/log; PLAIN={'1' if plain else ''}; IN=/dev/tty; STEPS=3\n"
                    "TITLES=('' 'Welcome' 'Where you are' 'Your keyboard')\nerr() { :; }\nhas() { command -v \"$1\" >/dev/null 2>&1; }\n"
                    + frame + part +
                    "\npage 2\npick 'Where are you?' 1 'Help words' 'United Kingdom (recommended)|Europe/London' 'Ireland|Europe/Dublin' "
                    "'Germany|Europe/Berlin' 'France|Europe/Paris'\n"
                    f"finish\necho \"$CHOICE\" > {result}\n")
            pathlib.Path(d, "run.sh").write_text(body)
            pid, fd = pty.fork()
            if pid == 0:
                os.environ.update({"TERM": "xterm", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
                os.execvp("bash", ["bash", os.path.join(d, "run.sh")])
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
            seen = b""
            deadline = time.time() + 20

            def read_until(word):
                nonlocal seen
                while word not in seen and time.time() < deadline:
                    if select.select([fd], [], [], 0.2)[0]:
                        try:
                            seen += os.read(fd, 4096)
                        except OSError:
                            return
            read_until(b"Your choice" if plain else b"Enter: choose")
            for k in keys:
                os.write(fd, k)
                time.sleep(0.15)
            while time.time() < deadline:
                done, _ = os.waitpid(pid, os.WNOHANG)
                if done:
                    break
                if select.select([fd], [], [], 0.2)[0]:
                    try:
                        seen += os.read(fd, 4096)
                    except OSError:
                        pass
            else:
                os.kill(pid, 9)
            os.close(fd)
            return pathlib.Path(result).read_text().strip() if os.path.exists(result) else "", seen.decode(errors="replace")

    def test_down_then_enter(self):
        choice, seen = self.run_pick([b"\x1b[B", b"\r"])
        self.assertEqual(choice, "2", seen[-800:])
        self.assertIn("Esc", seen)  # the list's own menu: Esc Back, ? Help, Tab Feedback, Ctrl+C Stop

    def test_letters_jump(self):
        self.assertEqual(self.run_pick([b"f", b"\r"])[0], "4")
        self.assertEqual(self.run_pick([b"g", b"e", b"\r"])[0], "3")

    def test_a_number_then_enter(self):
        self.assertEqual(self.run_pick([b"3", b"\r"])[0], "3")

    def test_plain_mode_is_numbered(self):
        choice, seen = self.run_pick([b"2\r"], plain=True)
        self.assertEqual(choice, "2", seen[-800:])
        self.assertIn("2. Ireland: Europe/Dublin", seen)
        self.assertNotIn("\x1b[", seen.split("Where are you?")[-1].split("Your choice")[0])


class InstallerOptionsTest(unittest.TestCase):
    def test_the_installer_and_helpers_know_the_options(self):
        install = (ROOT / "install.sh").read_text()
        self.assertIn("--timezone) TIMEZONE=", install)
        self.assertIn("--keyboard) KEYBOARD=", install)
        self.assertIn("sudo -n localectl set-x11-keymap", install)
        self.assertIn("set_env STARBOARD_HOST_KEYBOARD", install)
        self.assertIn("--timezone|--keyboard)", (ROOT / "starter.sh").read_text())
        self.assertIn("--timezone|--keyboard)", (ROOT / "run-first.sh").read_text())
        self.assertIn("STARBOARD_HOST_KEYBOARD=${STARBOARD_HOST_KEYBOARD:-}", (ROOT / "compose.yaml").read_text())

    def test_run_first_asks_location_then_keyboard_first(self):
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('TITLES=("" "Welcome" "Where you are" "Your keyboard" "Check this computer"', script)
        self.assertIn('"tz": "%s", "keyboard": "%s"', script)  # handed over, so both set-ups recommend the same
        self.assertIn("sudo timedatectl set-timezone", script)
        self.assertIn("sudo localectl set-x11-keymap", script)
        self.assertIn("try_keys", script)  # the test line before going on


if __name__ == "__main__":
    unittest.main()
