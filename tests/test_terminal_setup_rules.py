"""The terminal set-up follows the terminal rules (design system TERMINAL.md and WIZARD.md): refusals ask again, Back
stops once files are written, the step count is the chosen job's, jobs say what they are doing, and the words are the
browser set-up's. Answers are scripted, as in test_terminal_setup; Starboard's API is a stand-in here."""
import io
import re
import signal
import sys
import unittest
from unittest import mock

from starboard import terminal_setup as ts
from tests.test_terminal_drives import TB, Helper, drive
from tests.test_terminal_setup import Answers


class FakeApi:
    """Answers each call from replies, and refuses the calls in refuse once each, with Starboard's own words."""

    def __init__(self, replies=None, refuse=()):
        self.replies, self.refuse, self.calls = replies or {}, list(refuse), []

    def call(self, method, path, body=None, timeout=30):
        self.calls.append((method, path, body))
        for i, (m, p, words) in enumerate(self.refuse):
            if (m, p) == (method, path):
                del self.refuse[i]
                raise ts.Problem(words)
        return self.replies.get((method, path), {})


def plain(typed=(), hidden=()):
    out = io.StringIO()
    return ts.Terminal(out=out, ask=Answers(typed), secret=Answers(hidden), fancy=False), out


def boxed(typed=(), hidden=(), width=78, rows=30):
    out = io.StringIO()
    return ts.Terminal(out=out, ask=Answers(typed), secret=Answers(hidden), fancy=True, colour=False, width=width,
                       rows=rows), out


class RefusalsTest(unittest.TestCase):
    def test_a_refused_alert_address_is_explained_and_asked_again(self):
        api = FakeApi(refuse=[("PUT", "/api/config/general", "That is not an address Starboard can post to.")])
        term, out = plain(["2", "not an address", "2", "https://ntfy.sh/a-long-private-name", ""])
        self.assertTrue(ts.step_alerts(api, term, {}))
        text = out.getvalue()
        self.assertIn("Starboard said: That is not an address Starboard can post to.", text)
        self.assertEqual(text.count(ts.question("alerts")), 2)  # the same question again
        self.assertEqual(api.calls[-1][2]["watch"]["channel"]["url"], "https://ntfy.sh/a-long-private-name")

    def test_refused_hours_preset_and_extras_ask_again(self):
        api = FakeApi(refuse=[("PUT", "/api/config/general", "Starboard answered 500")])
        term, out = plain(["2", "2"])
        self.assertTrue(ts.step_hours(api, term, {}))
        self.assertIn("Starboard said: Starboard answered 500", out.getvalue())
        self.assertEqual(api.calls[-1][2], {"download_hours": {"enabled": False}})

        config = {"preset_recommended": "balanced", "presets": {"small": "Small", "balanced": "Balanced", "everything": "All"},
                  "preset_about": {"small": "a", "balanced": "b", "everything": "c"}, "performance": {"preset": "balanced"}}
        api = FakeApi({("GET", "/api/config"): config}, refuse=[("PUT", "/api/config/general", "Not now")])
        term, out = plain(["2", ""])  # refused; Enter keeps the answer chosen before
        self.assertTrue(ts.step_preset(api, term, {}))
        self.assertEqual(api.calls[-1][2], {"preset": "small"})
        self.assertIn("Your choice [2]", "\n".join(term._ask.prompts))

        config = {"services": [{"type": "jellyfin"}], "extras": {}}
        api = FakeApi({("GET", "/api/config"): config}, refuse=[("PUT", "/api/config/general", "Not now")])
        term, out = plain(["0", "0"])
        self.assertTrue(ts.step_connect(api, term, {}))
        self.assertEqual(out.getvalue().count(ts.question("extras")), 2)

    def test_a_refused_write_asks_again_and_back_then_stops_at_the_check(self):
        api = FakeApi({("POST", "/api/stack/write"): {"can_start": False, "command": "docker compose up -d"}},
                      refuse=[("POST", "/api/stack/write", "The settings folder is full.")])
        seen = []

        def first(api, term, state):
            seen.append("first")
            ts.head(term, state, "start")
            term.text("First question")
            return True

        def after(api, term, state):
            ts.head(term, state, "hours")
            term.text("A later question")
            return True
        state_choice = {"apps": ["jellyfin"], "data_dir": "/srv/media", "config_dir": "/srv/config"}

        def chosen(api, term, state):
            state["choice"] = dict(state_choice)
            return False
        # first; write refused, then yes; b at the later step goes back to the check, where b stops; Enter; on.
        term, out = plain(["", "y", "y", "b", "b", "", ""])
        with mock.patch.object(ts, "STEP_FUNCTIONS", [first, chosen, ts.step_check, after]), \
                mock.patch.object(ts, "add_drives_step"):
            self.assertEqual(ts.run(api, term, "/nonexistent", 8095), 0)
        text = " ".join(out.getvalue().split())
        self.assertEqual(seen, ["first"])  # never back before the step that wrote the files
        self.assertIn("Starboard said: The settings folder is full.", text)
        self.assertIn("Back stops here. Change earlier answers in Starboard's settings now", text)
        self.assertIn("Written already", text)
        self.assertIn("docker compose up -d", text)
        self.assertIn("== Starboard | Done", out.getvalue())  # the end, in plain mode too

    def test_preview_errors_go_to_the_step_that_can_fix_them(self):
        self.assertIs(ts.preview_step("The media folder /srv/media cannot be made: permission denied"), ts.step_storage)
        self.assertIs(ts.preview_step("The WireGuard key is not valid"), ts.step_vpn)
        self.assertIs(ts.preview_step("Radarr needs Prowlarr"), ts.step_apps)

    def test_long_words_from_starboard_wrap_like_a_note(self):
        api = mock.Mock()
        api.call.side_effect = [ts.Problem("That password is not right. " * 6), {}]
        term, out = boxed(hidden=["wrong password here", "right password here"], width=60, rows=24)
        term._page = lambda *a: None
        with mock.patch.object(ts, "read_setup_code", return_value=""):
            self.assertTrue(ts.step_password(api, term, {"data_dir": "/nonexistent"}))
        self.assertTrue(all(len(line) <= 60 for line in ts.ANSI.sub("", out.getvalue()).splitlines()))


class StepCountTest(unittest.TestCase):
    def test_a_restore_counts_only_its_own_steps(self):
        self.assertEqual(ts.job_steps({"start": "restore"}), ["password", "start", "extras", "alerts", "preset"])
        term, out = plain()
        ts.head(term, {"start": "restore"}, "extras")
        self.assertIn("(step 3 of 5)", out.getvalue())
        moving = ts.job_steps({"start": "move", "no_extras": True})
        self.assertEqual(moving, ["password", "start", "docker", "hours", "alerts", "preset"])  # DASH-267: before any move
        self.assertNotIn("docker", ts.job_steps({"start": "move", "docker_access": True}))

    def test_a_new_install_leaves_out_what_the_apps_do_not_need(self):
        state = {"start": "new", "storage": {"key": "disk"}, "choice": {"apps": ["jellyfin"]}}
        self.assertEqual(ts.job_steps(state), ["password", "start", "storage", "apps", "check", "extras", "hours",
                                               "docker", "alerts", "preset"])  # DASH-139: at the end
        term, _ = boxed()
        term._page = lambda *a: None
        ts.head(term, state, "check")
        self.assertIn("step 5 of 10", term.header[1])


class ResizeTest(unittest.TestCase):
    def test_the_signal_only_sets_a_flag_and_the_next_read_draws_again(self):
        out = io.StringIO()
        term = ts.Terminal(out=out, fancy=True, colour=False, ask=Answers(["1"]))
        with mock.patch.object(signal, "signal") as sig:
            term.watch_size()
        handler = sig.call_args[0][1]
        term.heading("Download hours", 5)
        out.truncate(0)
        out.seek(0)
        handler(signal.SIGWINCH, None)
        self.assertEqual(out.getvalue(), "")  # nothing drawn inside the signal handler
        self.assertTrue(term.resize_due)
        term.choose("Only download at set hours?", ["Yes", "No"])
        self.assertIn("\033[2J", out.getvalue())  # drawn again at the read
        self.assertFalse(term.resize_due)


class KeysAndHelpTest(unittest.TestCase):
    def test_help_titles_keep_the_question_in_its_own_words(self):
        term, out = boxed(["", ""], ["?", "a-hidden-key"])  # ? at the hidden question; Enter closes the help
        term._page = lambda *a: None
        term.heading("VPN", 5)
        self.assertEqual(term.hidden("WireGuard private key, from your provider", help_key="vpn"), "a-hidden-key")
        self.assertIn("Help: WireGuard private key, from your provider", out.getvalue())
        self.assertNotIn("a-hidden-key", out.getvalue())
        term.choose("Which VPN provider do you have?", ["Proton VPN", "AirVPN"], help_key="vpn")
        self.assertEqual(term._title("Which VPN provider do you have?"), "Which VPN provider do you have?")

    def test_f_opens_feedback_in_the_arrow_key_list(self):
        term, out = boxed(["q"])  # feedback opens; q closes it
        term._page = lambda *a: None
        term.heading("Jellyfin extras", 6)
        keys = iter(["f", " ", "\r"])
        with mock.patch.object(ts, "_read_keys", lambda fd: next(keys)), \
                mock.patch("termios.tcgetattr", return_value=[]), mock.patch("termios.tcsetattr"), \
                mock.patch("tty.setcbreak"), mock.patch.object(sys, "stdin", mock.Mock(fileno=lambda: 0)):
            picked = term._pick_many("Use Starboard's Jellyfin extras?", ["Live TV", "Watch history"], [], "extras", True)
        self.assertEqual(picked, [0])
        self.assertIn("╭─ Send feedback", out.getvalue())


class JobsTest(unittest.TestCase):
    def test_plain_mode_says_when_a_job_starts_and_ends(self):
        term, out = plain()
        self.assertEqual(term.waiting("Setting up Reelix", lambda: 1, 0, (2, 3)), 1)
        text = out.getvalue()
        self.assertIn("Job 2 of 3: Setting up Reelix. Please wait, this can take some time...", text)
        self.assertIn("Done: Job 2 of 3: Setting up Reelix", text)

    def test_a_job_that_did_not_finish_keeps_its_line_and_offers_the_choices(self):
        term, out = boxed(["2", "1"])  # Show the details, then Try again
        term.heading("Check", 7)
        term.waiting("Downloading and starting the apps", lambda: {"ok": False}, 0, (1, 1), ok=lambda j: j["ok"])
        raw = out.getvalue()
        self.assertIn("Ctrl+C Stop", raw)  # the only key while it waits
        self.assertIn("✖ Job 1 of 1: Downloading and starting the apps: did not finish", raw)
        self.assertTrue(any("did not finish" in str(line) for line in term.screen))  # kept when drawn again
        self.assertEqual(term.job_failed("The apps did not all start.", ["pull access denied for made-up/app"]), "again")
        raw = out.getvalue()
        for choice in ("Try again (recommended)", "Show the details", "Report this problem", "Stop"):
            self.assertIn(choice, raw)
        self.assertIn("pull access denied for made-up/app", raw)
        self.assertLess(raw.rindex("did not finish"), raw.index("The apps did not all start."))  # the error below

    def test_a_failed_job_shows_its_error_number_the_same_boxed_and_plain(self):
        # DASH-152: the boxed frame showed no number while plain lines did (only in the details). Both now show it under
        # the problem, then the address of its help on a line of its own, before the choices.
        url = "https://themightytrex.github.io/starboard/help/topics/run-first-errors.html#in-33"
        for make in (plain, boxed):
            term, out = make(["1"])
            if make is boxed:
                term.heading("Check", 7)
            self.assertEqual(term.job_failed("The apps did not all start.", ["made-up/app failed"], code="IN-33"), "again")
            raw = out.getvalue()
            self.assertIn("Error IN-33. What it means and how to fix it:", raw, make.__name__)
            line = next(line for line in raw.splitlines() if url in line)
            self.assertEqual(line.strip(), url)  # whole, on its own line
            self.assertLess(raw.index("Error IN-33."), raw.index("What do you want to do?"))
            self.assertIn("Error IN-33", term.problem)  # and in Report this problem

    def test_the_installers_number_is_read_from_its_lines(self):
        lines = ["Note: Downloading and starting 7 apps did not work. Error IN-33.", "Error IN-33. What it means..."]
        self.assertEqual(ts.error_number(lines), "IN-33")
        self.assertIsNone(ts.error_number(["Pulling sonarr", "done"]))

    def test_stop_after_a_failed_job_tells_run_first_its_number(self):
        import os
        import tempfile
        term, _ = plain(["4"])
        with self.assertRaises(ts.Stop):
            term.job_failed("The apps did not all start.", code="IN-33")
        self.assertEqual(term.stop_code, "IN-33")
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"STARBOARD_ERROR_FILE": d + "/e"}):
            ts.note_stop("IN-33")
            self.assertEqual(open(d + "/e").read().strip(), "IN-33")

    def test_the_wait_for_the_apps_leaves_out_apps_that_did_not_start(self):
        # DASH-151: qBittorrent behind a VPN that never connected kept the wait going for the full time, with nothing
        # new on the screen. Only the apps that started are waited for.
        api = FakeApi({("GET", "/api/discover"): {"items": [{"key": "reelix"}], "known": ["reelix", "qbittorrent"]}})
        term, _ = plain()
        clock = iter(range(0, 10000, 10))
        with mock.patch.object(ts.time, "time", lambda: next(clock)), mock.patch.object(ts.time, "sleep", lambda s: None):
            items = ts.found_when_settled(api, term, 0, ["reelix", "qbittorrent"], running={"reelix", "starboard"})
        self.assertEqual(items, [{"key": "reelix"}])
        self.assertEqual(len([c for c in api.calls if c[1] == "/api/discover"]), 1)  # no waiting at all
        term, _ = plain()
        clock = iter(range(0, 10000, 10))
        with mock.patch.object(ts.time, "time", lambda: next(clock)), mock.patch.object(ts.time, "sleep", lambda s: None):
            ts.found_when_settled(api, term, 0, ["reelix", "qbittorrent"])  # not known what started: waits it out
        self.assertGreater(len([c for c in api.calls if c[1] == "/api/discover"]), 3)

    def test_the_running_apps_are_read_from_the_installers_note(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(ts.running_apps(d))
            os.makedirs(os.path.join(d, "data", "stack"))
            with open(os.path.join(d, "data", "stack", "running.txt"), "w") as f:
                f.write("reelix\njellyfin\n\n")
            self.assertEqual(ts.running_apps(d), {"reelix", "jellyfin"})

    def test_stop_after_a_failed_job_stops(self):
        term, _ = plain(["4"])
        with self.assertRaises(ts.Stop):
            term.job_failed("Reelix is not set up yet.")

    def test_pool_changes_have_a_progress_line_and_can_be_tried_again(self):
        class Flaky(Helper):
            failed = False

            def __call__(self, args):
                if args[0] == "apply" and not self.failed:
                    self.failed = True
                    raise ts.Problem("the drive is busy")
                return super().__call__(args)
        h = Flaky([drive(1, 2 * TB, "0C3D", files=TB), drive(2, 2 * TB, "A81F", files=TB)])
        term, out = plain(["", "", "", "", "y", "1", "n"])  # yes; both; keep both; yes; Try again; no balancing
        ts.add_drives_step(True)
        try:
            self.assertTrue(ts.step_drives(None, term, {"pool_run": h}))
        finally:
            ts.STEP_FUNCTIONS.remove(ts.step_drives)
            ts.STEPS.remove("Your drives")
        text = out.getvalue()
        self.assertIn("Job 1 of 2: Adding Drive 1 to the pool. Please wait, this can take some time...", text)
        self.assertIn("Did not finish: Job 1 of 2", text)
        self.assertIn("The pool helper stopped: the drive is busy", text)
        self.assertIn("Done: Job 2 of 2", text)
        self.assertIn(ts.question("drives"), text)


class LiveRunTest(unittest.TestCase):
    """What a live run at 80 by 24 found."""

    def test_yes_or_no_is_numbered_with_the_recommended_answer_first(self):
        term, out = plain(["", "2", "y", "1"])
        self.assertTrue(term.yes_no("Write the apps' files now?", True))
        self.assertTrue(term.yes_no("Make these changes now?", False))  # 2 is Yes when No is recommended
        self.assertTrue(term.yes_no("Write the apps' files now?", True))  # y still works
        self.assertFalse(term.yes_no("Balance the files now?", False))
        text = out.getvalue()
        self.assertNotRegex(text + "\n".join(term._ask.prompts), r"\[Y/n\]|\[y/N\]")
        self.assertIn("1. Yes (recommended)", text)
        self.assertIn("1. No (recommended)", text)
        self.assertIn("Your choice [1]", term._ask.prompts[0])
        term, out = boxed([""])
        term._page = lambda *a: None
        term.yes_no("Write the apps' files now?", True)
        self.assertIn("●  1  Yes (recommended)", out.getvalue())

    def test_the_menu_says_what_enter_does(self):
        term, out = boxed(["", "x", ""], ["a password here"])
        term.heading("Check", 7)
        term.text("Press Enter to carry on")
        self.assertEqual(term.step_keys()[1], "Enter: carry on")
        self.assertIn("Enter: carry on", out.getvalue())
        term.text("OpenVPN user name, from your provider")
        self.assertEqual(term.step_keys()[1], "")  # no default: Enter does nothing to say
        term.hidden("OpenVPN password")
        self.assertEqual(term.step_keys()[1], "")
        term.choose("Which one?", ["A", "B"])
        self.assertEqual(term.step_keys()[1], "Enter: recommended")

    def test_a_long_link_is_on_a_line_of_its_own_with_no_indent(self):
        term, out = boxed(["2", "", ""], width=80, rows=24)
        term._page = lambda *a: None
        self.assertTrue(ts.step_usenet(None, term, {"choice": {"apps": ["nzbget"]}}))
        link = f"{ts.HELP_CENTRE}topics/choose-a-usenet-provider.html"
        self.assertIn("\n" + link + "\n", out.getvalue())
        lines = ts.ANSI.sub("", out.getvalue()).splitlines()
        self.assertTrue(all(len(line) <= 80 or line == link for line in lines))

    def test_help_with_a_long_address_stays_inside_its_box(self):
        term, out = boxed(["?", "", "1"], width=78, rows=30)
        term._page = lambda *a: None
        term.heading("Download hours", 9)
        term.choose(ts.question("hours"), ["Yes", "No"], help_key="hours")
        box = [line for line in re.findall(r"\033\[\d+;9H([│╭╰][^\033]*)", out.getvalue())]
        self.assertTrue(box)
        self.assertEqual({len(line) for line in box}, {62})


class WordsTest(unittest.TestCase):
    def test_the_usenet_step_names_the_app_chosen(self):
        term, out = plain(["2", "", ""])
        self.assertTrue(ts.step_usenet(None, term, {"choice": {"apps": ["nzbget"]}}))
        text = " ".join(out.getvalue().split())
        self.assertIn("NZBGet needs an account with a Usenet provider", text)
        self.assertNotIn("SABnzbd", text)

    def test_questions_are_the_browser_set_ups(self):
        term, out = plain(["2", "", ""])
        ts.step_hours(FakeApi(), term, {})
        ts.step_alerts(FakeApi(), term, {})
        for step in ("hours", "alerts"):
            self.assertIn(ts.question(step), out.getvalue())


class NarrowCardTest(unittest.TestCase):
    """The last card at 60 columns cut its labels and let a long folder run past its edge (8 November 2026)."""

    ROWS = [("On your other devices", "http://192.0.2.15:8095"),
            ("Changes to this computer", "./install.sh --livetv-folder /srv/media-stack/config/jellyfin/iptv-folder-that-is-long")]

    def lines(self, width):
        out = io.StringIO()
        term = ts.Terminal(out=out, ask=lambda p="": "", fancy=True, colour=False, width=width, rows=30)
        term.card("Starboard is ready", self.ROWS)
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[78]", "", out.getvalue())
        return [line for line in text.split("\n") if line.strip().startswith(("│", "╭", "╰"))]

    def test_every_width_fits_and_keeps_labels_whole(self):
        for width in (60, 80, 100):
            lines = self.lines(width)
            self.assertTrue(all(len(line) <= width - 2 for line in lines), (width, lines))
            body = "\n".join(lines)
            for label, _ in self.ROWS:
                self.assertIn(label, body, width)


class LongAddressOptionTest(unittest.TestCase):
    """PrivadoVPN's affiliate address is one word wider than the about column at 80 columns: it ran past the edge
    (9 November 2026). The list then puts each about under its name."""

    OPTIONS = [("ExpressVPN", "expressvpn.com"),
               ("PrivadoVPN", "privadovpn.com/getprivadovpn/#a_aid=themightytrexuk (Ad)"),
               ("Private Internet Access", "privateinternetaccess.com")]

    def lines(self, width):
        out = io.StringIO()
        term = ts.Terminal(out=out, ask=lambda p="": "1", fancy=True, colour=False, width=width, rows=30)
        term._options(self.OPTIONS, {0})
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[78]", "", out.getvalue()).replace("\r", "\n")
        return [line for line in text.split("\n") if line.strip()]

    def test_fits_at_80_and_stays_in_columns_when_wide(self):
        narrow = self.lines(80)
        self.assertTrue(all(len(line) <= 80 for line in narrow), narrow)
        self.assertIn("privadovpn.com/getprivadovpn/#a_aid=themightytrexuk (Ad)", "\n".join(narrow))
        wide = self.lines(120)
        self.assertTrue(any("PrivadoVPN" in line and "privadovpn.com" in line for line in wide), wide)


if __name__ == "__main__":
    unittest.main()


class AppByAppTest(unittest.TestCase):
    def test_choosing_app_by_app_after_basics_starts_from_basics(self):
        """Basics, then Let me choose app by app: the groups ticked are Basics' groups (its VPN included), not the
        catalogue's first ones, so Enter keeps what Basics chose."""
        groups = [{"key": k, "name": k.title(), "about": "", "default": k in ("movies", "tv")}
                  for k in ("movies", "tv", "vpn", "subtitles")]
        apps = [{"key": k, "name": k.title(), "groups": [g], "installed": False, "default": True, "memory": 100,
                 "notes": ""} for k, g in (("reelix", "movies"), ("gluetun", "vpn"), ("bazarr", "subtitles"))]
        overview = {"groups": groups, "apps": apps, "installs": [{"key": "basics", "name": "Basics", "about": "",
                                                                  "recommended": True}],
                    "defaults": {"data_dir": "/srv/media", "config_dir": "/srv/media-stack/config", "puid": 1000,
                                 "pgid": 1000, "tz": "UTC"}}
        basics = {"name": "Basics", "apps": ["reelix", "gluetun", "bazarr"], "groups": ["movies", "tv", "vpn", "subtitles"],
                  "memory": 300, "reelix_edition": "lite", "disk_health": False}
        api = FakeApi({("GET", "/api/stack"): overview, ("POST", "/api/stack/install"): basics})
        # Yes, Basics, Let me choose app by app, Enter for the ticked groups, Yes to install them.
        term, out = plain(["1", "1", "2", "", "1"])
        state = {}
        with mock.patch.object(ts, "ask_reelix_edition", return_value="lite"):
            self.assertTrue(ts.step_apps(api, term, state))
        self.assertEqual(state["choice"]["groups"], ["movies", "subtitles", "tv", "vpn"])
        self.assertEqual(state["choice"]["apps"], ["reelix", "gluetun", "bazarr"])
