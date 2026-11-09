"""The terminal-only set-up (DASH-86): answers typed in turn against a real Starboard on this computer."""
import io
import os
import re
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, qr, terminal_setup
from starboard.server import make_server

SIGN_IN_WORDS = "correct horse battery"


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
        offline = mock.patch("starboard.stack.can_download", return_value=False)  # no registry calls in tests
        offline.start()
        self.addCleanup(offline.stop)
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

    def test_which_reelix_is_asked_only_when_both_can_be_downloaded(self):
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": SIGN_IN_WORDS})  # asked after sign-in
        last = {}
        with mock.patch("starboard.stack.can_download", return_value=True):
            term, out = self.term(["2"], [])
            self.assertEqual(terminal_setup.ask_reelix_edition(self.api, term, last), "full")
            self.assertIn("Reelix (recommended)", out.getvalue())
            self.assertEqual(last["reelix_edition"], "full")
            term, out = self.term([""], [])  # Enter keeps the earlier answer
            self.assertEqual(terminal_setup.ask_reelix_edition(self.api, term, last), "full")
        with mock.patch("starboard.stack.can_download", return_value=False):
            term, out = self.term([], [])
            self.assertEqual(terminal_setup.ask_reelix_edition(self.api, term, {}), "lite")
            self.assertNotIn("Which Reelix", out.getvalue())

    def test_whole_set_up_with_the_recommended_answers(self):
        media, settings = os.path.join(self.tmp.name, "media"), os.path.join(self.tmp.name, "config")
        # name, start, storage, folder; install now, Basics (recommended), install these; the VPN (Basics has one):
        # provider, WireGuard, any country, the address; Usenet: no provider yet, Enter; Sites to search: none, no address
        # of your own; Films and series: no TMDB key (hidden), English; then write, extras, hours, alerts, health, preset
        typed = ["", "", "", media, "", "", "", "5", "", "", "192.168.1.20/32", "", "", "", "", "", "", "y", "", "", "", "", "", "", ""]
        term, out = self.term(typed, [SIGN_IN_WORDS, SIGN_IN_WORDS, "secret-wireguard-key", ""])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        self.assertFalse(self.app.needs_setup)
        self.assertTrue(auth.check_password(SIGN_IN_WORDS, self.app.config.data["auth"]["password_hash"]))
        self.assertNotIn(SIGN_IN_WORDS, text)  # typed hidden, never shown
        # No Docker access here: the files are written, and the command to start them is shown.
        self.assertTrue(os.path.exists(os.path.join(self.tmp.name, "stack", "compose.yaml")))
        self.assertIn("./install.sh --start-apps", text)
        self.assertEqual(self.app.config.data["download_hours"], {"enabled": True, "start": 1, "end": 7})

    def test_usenet_step_shows_the_affiliate_note_links_and_the_rules(self):
        """Only with SABnzbd: the Ad note before the providers, each with its full affiliate address, then the rules."""
        term, out = self.term(["", ""], [])  # no provider yet (the list), then Enter
        self.assertFalse(terminal_setup.step_usenet(None, term, {"choice": {"apps": ["qbittorrent"]}}))
        self.assertTrue(terminal_setup.step_usenet(None, term, {"choice": {"apps": ["sabnzbd"]}}))
        text = " ".join(out.getvalue().split())
        self.assertLess(text.index("Ad: these are affiliate links"), text.index("Newshosting https://www.newshosting.com/?a_aid="))
        for name, url in terminal_setup.USENET:
            self.assertIn(f"- {name}\n    {url}\n", out.getvalue())  # a bullet each, the whole address on its own line
        self.assertIn("Use Usenet only for files you have the right to download", text)

    def test_someone_with_a_usenet_provider_is_not_shown_the_list(self):
        term, out = self.term(["2", "", ""], [])  # Yes, I have one; no server address for now; then Enter
        self.assertTrue(terminal_setup.step_usenet(None, term, {"choice": {"apps": ["nzbget"]}}))
        self.assertNotIn("a_aid=", out.getvalue())
        self.assertIn("choose-a-usenet-provider", out.getvalue())
        self.assertIn("Use Usenet only for files you have the right to download", " ".join(out.getvalue().split()))

    def test_usenet_list_matches_the_browser(self):
        """The browser wizard and Settings use the same providers and words (web/js/common.js)."""
        js = open(os.path.join(os.path.dirname(__file__), "..", "web", "js", "common.js"), encoding="utf-8").read()
        self.assertEqual(re.findall(r'\["([^"]+)", "(https://[^"]+)"\]', js), [list(x) for x in terminal_setup.USENET] and
                         [tuple(x) for x in terminal_setup.USENET])
        self.assertIn(terminal_setup.USENET_RIGHTS, js)
        self.assertIn(terminal_setup.USENET_ABOUT, js)
        self.assertIn(terminal_setup.USENET_AD.removeprefix("Ad: "), js)

    def test_help_mismatch_and_short_passwords_ask_again(self):
        term, out = self.term(["", "", "", "", "2", "2", "", "", ""], ["?", "short", SIGN_IN_WORDS, "different words", SIGN_IN_WORDS, SIGN_IN_WORDS])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        self.assertIn("a few unrelated words", text)
        self.assertIn("Use at least 10 characters", text)
        self.assertIn("did not match", text)
        self.assertFalse(self.app.config.data["download_hours"]["enabled"])
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "stack", "compose.yaml")))

    def test_wrong_number_and_question_mark_then_q_stops(self):
        term, out = self.term(["", "", "", "", "9", "?", "q"], [SIGN_IN_WORDS, SIGN_IN_WORDS])
        with self.assertRaises(terminal_setup.Stop):
            terminal_setup.run(self.api, term, self.tmp.name, self.port)
        self.assertIn("Type a number from 1 to 2", out.getvalue())
        self.assertIn("Each kind of media installs", out.getvalue())

    def test_signs_in_when_a_password_is_set(self):
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": SIGN_IN_WORDS})
        api = terminal_setup.Api(self.port)
        term, out = self.term(["", "", "", "2", "2", "", "", ""], ["wrong password here", SIGN_IN_WORDS])
        self.assertEqual(terminal_setup.run(api, term, self.tmp.name, self.port), 0)
        self.assertIn("That password is not right", out.getvalue())
        self.assertIn("Signed in.", out.getvalue())

    def test_vpn_details_are_asked_and_kept_out_of_the_screen(self):
        media, settings = os.path.join(self.tmp.name, "media"), os.path.join(self.tmp.name, "config")
        # Downloads and VPN only, every default app; Proton VPN over WireGuard.
        typed = ["", "", "", media, "", "4", "9,10", "", "5", "1", "", "192.168.1.20/32", "", "", "y", "2", "", "", ""]
        term, out = self.term(typed, [SIGN_IN_WORDS, SIGN_IN_WORDS, "secret-wireguard-key"])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        self.assertNotIn("secret-wireguard-key", text)
        with open(os.path.join(self.tmp.name, "stack", ".env")) as f:
            env = f.read()
        self.assertIn("VPN_SERVICE_PROVIDER=protonvpn", env)
        self.assertIn("secret-wireguard-key", env)
        # PrivadoVPN's link is an affiliate link: the Ad note comes before the list, and its line says Ad.
        flat = " ".join(text.split())
        self.assertLess(flat.index("Ad: the PrivadoVPN link is an affiliate link"), flat.index("Which VPN provider do you have?"))
        self.assertIn("privadovpn.com/getprivadovpn/#a_aid=themightytrexuk (Ad)", flat)

    def test_vpn_affiliate_note_matches_the_browser(self):
        """The browser set-up says the same about an affiliate VPN link (vpnAd in web/js/install.js)."""
        js = open(os.path.join(os.path.dirname(__file__), "..", "web", "js", "install.js"), encoding="utf-8").read()
        self.assertEqual(terminal_setup.VPN_AFFILIATE, {"privado"})
        for words in ("link is an affiliate link. If you sign up through it,",
                      "pays a small commission towards Starboard's development. You pay the same price."):
            self.assertIn(words, terminal_setup.vpn_ad())
            self.assertIn(words, js)

    def test_bad_hours_ask_again(self):
        term, out = self.term(["", "", "", "", "2", "", "5", "5", "22", "6", "", "", ""], [SIGN_IN_WORDS, SIGN_IN_WORDS])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        self.assertIn("That did not work", out.getvalue())
        self.assertEqual(self.app.config.data["download_hours"], {"enabled": True, "start": 22, "end": 6})

    def test_boxes_and_cards_line_up_and_plain_has_none(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=70, rows=30)
        term._page = lambda *a: None  # the screen clearing is tested on its own
        term.heading("What to set up", 2)
        term.card("What will change", [("Install", "Radarr, Sonarr, Jellyfin, " * 4), ("Media folder", "/srv/media")])
        term._options([("Movies", "Find films " * 8), "Yes (recommended)"], {0})
        lines = term.header + out.getvalue().splitlines()  # the heading is drawn in place, not printed
        self.assertTrue(any("step 2 of 13" in l for l in lines))
        self.assertTrue(any("█" in l and " 8%" in l for l in lines))
        boxed = [l for l in lines if l and l[0] in "┌│└╭╰"]
        self.assertTrue(boxed)
        self.assertEqual({len(l) for l in boxed}, {70})  # every box line ends at the same column
        cards = [l for l in lines if l.startswith(("  ╭", "  │", "  ╰"))]
        self.assertTrue(cards)
        self.assertEqual({len(l) for l in cards}, {68})  # a card is set in by 2 and fits the column (width - 4)
        self.assertTrue(all(len(l) <= 70 for l in lines))  # long descriptions wrap inside the width
        plain = io.StringIO()
        term = terminal_setup.Terminal(out=plain, fancy=False)
        term.heading("What to set up", 2)
        term.card("What will change", [("Media folder", "/srv/media")])
        self.assertNotRegex(plain.getvalue(), "[┌│└╭╰█●✔\x1b]")
        self.assertIn("Media folder: /srv/media", plain.getvalue())

    def test_back_returns_with_the_last_answers(self):
        media, settings = os.path.join(self.tmp.name, "media"), os.path.join(self.tmp.name, "config")
        # Step 2 with Downloads and VPN; step 3 with Surfshark over WireGuard; then back from the check to step 3,
        # where Enter keeps every answer, including the hidden key; then on.
        typed = ["", "", "", media, "", "4", "9,10", "",     # name, start, storage and folder, Let me choose, the apps
                 "6", "", "", "192.168.1.20/32",            # step 3: Surfshark, WireGuard, any country, the address
                 "", "",                                      # Usenet (NZBGet comes with Downloads): no provider, Enter
                 "b", "b",                                    # the check: back to Usenet, back again to the VPN
                 "", "", "", "",                              # step 3 again: every answer kept with Enter
                 "", "",                                      # Usenet again
                 "y", "2", "", "", ""]                        # write, any time, no alerts, disk health, Balanced
        term, out = self.term(typed, [SIGN_IN_WORDS, SIGN_IN_WORDS, "secret-wireguard-key", ""])
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        text = out.getvalue()
        prompts = "\n".join(term._ask.prompts + term._secret.prompts)
        self.assertEqual(text.count("== Starboard | VPN"), 2)
        self.assertIn("Your choice [6]", prompts)  # the provider chosen before is the default after Back
        self.assertIn("[192.168.1.20/32]", prompts)
        self.assertIn("Enter keeps the one you typed before", prompts)
        with open(os.path.join(self.tmp.name, "stack", ".env")) as f:
            env = f.read()
        self.assertIn("VPN_SERVICE_PROVIDER=surfshark", env)
        self.assertIn("secret-wireguard-key", env)  # kept from before, without typing it again

    def test_b_on_the_first_step_and_the_password_is_kept_after_back(self):
        term, out = self.term(["", "b", "2", "b", "", "", "", "", "2", "2", "", "", ""], ["b", SIGN_IN_WORDS, SIGN_IN_WORDS])
        # b while choosing the password does nothing (first step); b at step 2 shows the saved password.
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        self.assertIn("Your password is saved.", out.getvalue())

    def test_a_wide_window_centres_a_column_100_wide(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=200, rows=40)
        self.assertEqual((term.width, term.left), (100, 50))
        term.heading("How to start", 2)
        term.note("A paragraph in the column.")
        raw = out.getvalue()
        self.assertIn("\033[1;51H┌", raw)                       # the heading box starts at the column's edge
        self.assertIn(" " * 50 + "  A paragraph in the column.", raw)
        self.assertIn("\033[40;51H", raw)                        # the menu too
        narrow = terminal_setup.Terminal(out=io.StringIO(), fancy=True, colour=False, width=80, rows=24)
        self.assertEqual((narrow.width, narrow.left), (80, 0))  # up to 100 wide, the column is the window

    def test_text_wraps_again_when_the_window_changes_size(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=80, rows=30)
        term._page = lambda *a: None
        term.heading("How to start", 2)
        term.note("A long paragraph of words that wraps inside the frame at whatever width the window has now. " * 3)
        term.warn("A warning that is long enough to wrap onto a second and a third line at a narrow width. " * 2)
        term._options([("Move from apps you already run (recommended)", "Starboard adds the apps already running " * 3),
                       ("Short", "A short name in two columns " * 4), "Plain text option " * 8], {0})
        term.card("What will change", [("Install", "Radarr, Sonarr, Jellyfin, " * 4)])
        for width in (80, 60, 100):
            term.width = width
            lines = [terminal_setup.ANSI.sub("", line) for line in term._lines()]
            self.assertTrue(all(len(line) <= width for line in lines), width)
            words = " ".join(lines)
            self.assertIn("whatever width", words)  # whole words, never cut in the middle
            self.assertNotRegex(words, r"wha\s+tever")

    def test_screen_is_cleared_with_a_fixed_menu_and_given_back(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=78, rows=30)
        term.can_back = True
        term.heading("VPN", 3)
        term.finish()
        raw = out.getvalue()
        self.assertIn("\033[2J", raw)            # cleared
        self.assertIn("\033[5;28r", raw)         # only the lines between the heading and the menu scroll
        self.assertIn("b Back   ? Help   f Feedback   q Stop", raw)
        self.assertTrue(raw.endswith("\033[r\033[29;1H\033[2K\033[30;1H\033[2K\0338\n"))  # menu gone, window given back

    def test_heading_bar_and_menu_stay_put_and_the_window_is_measured_again(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=80, rows=24)
        term.heading("What to set up", 2)
        for i in range(40):  # far more than the window holds: only the middle scrolls
            term.say(f"line {i}")
        raw = out.getvalue()
        self.assertIn("\033[1;1H┌", raw)          # the heading box is drawn in place at the top
        self.assertIn("\033[5;22r", raw)          # lines 5 to 22 scroll; the box, the bar and the menu do not
        self.assertEqual(len(term.header), 4)
        out.truncate(0); out.seek(0)
        term.fixed_size, term.drawn, term.pending = (100, 40), True, "  › Your choice [1]: "
        term._resized()                            # the window grew: drawn again to fit
        raw = out.getvalue()
        self.assertIn("\033[5;38r", raw)
        self.assertIn("line 39", raw)
        self.assertTrue(raw.endswith("  › Your choice [1]: "))

    def test_help_pop_up_draws_a_box_and_the_step_again(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=78, rows=30, ask=Answers(["?", "", "2"]))
        term._page = lambda *a: None
        term.heading("Download hours", 5)
        self.assertEqual(term.choose("When should downloads run?", ["Set hours", "Any time"], help_key="hours"), 1)
        raw = out.getvalue()
        self.assertIn("╭─ Help: When should downloads run?", raw)  # the question in its own case
        self.assertIn("Enter or Esc: close help", raw)
        self.assertGreaterEqual(raw.count("When should downloads run?"), 2)  # drawn again after help closes

    # Feedback (f) ------------------------------------------------------------------------------------------

    def fancy(self, answers, width=78, rows=30):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=width, rows=rows, ask=Answers(answers))
        term.save_dir = self.tmp.name
        return term, out

    def test_f_opens_feedback_at_a_step_and_returns_to_it(self):
        # f, Hard to use, the words, Enter after the whole report, Cancel; then the question again, answered 2.
        term, out = self.fancy(["f", "2", "The list is hard to read", "", "4", "2"])
        term.can_back = True
        term.heading("What to set up", 2)
        self.assertEqual(term.choose("Install the apps?", ["Yes", "No"]), 1)
        raw = out.getvalue()
        self.assertIn("f Feedback", raw)
        self.assertIn("╭─ Send feedback", raw)
        self.assertIn("6. Make something better", raw)
        self.assertIn("╭─ The whole report", raw)
        self.assertIn("Page: Terminal set-up, step 2: What to set up", raw)
        self.assertIn("1. Show as a QR code (recommended)", raw)
        self.assertEqual(term.screen[-1], "  › Your choice [1]: 2")  # the f is not left on the step
        after = raw.rsplit("Show as a QR code", 1)[1]
        self.assertIn("Install the apps?", after)  # the step drawn again as it was
        self.assertIn("b Back   ? Help   f Feedback   q Stop", after)
        self.assertFalse([n for n in os.listdir(self.tmp.name) if n.startswith("starboard-feedback-")])  # nothing saved

    def test_q_closes_feedback_and_the_step_carries_on(self):
        term, out = self.fancy(["f", "q", ""])
        term.heading("Download hours", 5)
        self.assertEqual(term.choose("When should downloads run?", ["Set hours", "Any time"]), 0)

    def test_nothing_typed_as_an_answer_is_in_the_report(self):
        media, settings = os.path.join(self.tmp.name, "my-own-media"), os.path.join(self.tmp.name, "config")
        # Hidden answers (the password and the WireGuard key) are not remembered, so they are not typed in here.
        words = (f"It broke near {media} with 192.168.1.20/32. "
                 "Mail me at sam@example.org, token=abc123def456")
        # Downloads and VPN (Proton over WireGuard), then f at the check: Something is broken, the words, skip the
        # second question, save to a file; then write and downloads at any time.
        typed = ["", "", "", media, "", "4", "9,10", "", "5", "1", "Netherlands", "192.168.1.20/32", "", "",
                 "f", "1", words, "", "1", "y", "2", "", "", ""]
        term, out = self.term(typed, [SIGN_IN_WORDS, SIGN_IN_WORDS, "secret-wireguard-key"])
        term.save_dir = self.tmp.name
        token = self.app.setup_token
        self.assertEqual(terminal_setup.run(self.api, term, self.tmp.name, self.port), 0)
        [name] = [n for n in os.listdir(self.tmp.name) if n.startswith("starboard-feedback-")]
        with open(os.path.join(self.tmp.name, name)) as f:
            saved = f.read()
        report = out.getvalue().split("This is everything the report holds")[1].split("Back to the set-up")[0]
        for text in (saved, report):
            for private in (media, "my-own-media", SIGN_IN_WORDS, "secret-wireguard-key", "192.168.1.20", "Netherlands",
                            "sam@example.org", "abc123def456", token):
                self.assertNotIn(private, text)
            self.assertIn("[your answer]", text)
            self.assertIn("[email]", text)
            self.assertIn("Terminal set-up, step 7: Check", text)
        self.assertIn("https://github.com/TheMightyTRex/starboard/issues/new?title=", saved)
        self.assertIn("labels=feedback,problem,type:+bug", saved)
        self.assertEqual(os.stat(os.path.join(self.tmp.name, name)).st_mode & 0o777, 0o600)

    def test_report_this_problem_after_a_failure(self):
        with open(os.path.join(self.tmp.name, "setup-token"), "w") as f:
            f.write("made-up-setup-code")
        self.server.shutdown()
        self.server.server_close()
        self.server = mock.Mock()  # tearDown has nothing left to stop
        api = terminal_setup.Api(self.port)
        # Both passwords, then Starboard is not answering: r, skip both questions, Done; then q.
        term, out = self.term(["", "", "", "2"], [SIGN_IN_WORDS, SIGN_IN_WORDS, "r", "q"])  # the name, then the report
        with self.assertRaises(terminal_setup.Stop):
            terminal_setup.run(api, term, self.tmp.name, self.port)
        text = out.getvalue()
        self.assertIn("Type r to report this problem.", text)
        self.assertIn("Starboard said:", text)
        self.assertIn("Last error", text)
        self.assertIn("POST /api/setup: Starboard is not answering", text)
        self.assertNotIn("made-up-setup-code", text)
        self.assertIn("title=Terminal+set-up,+step+1:+Starboard+is+not+answering", text)

    def test_r_is_on_the_menu_after_a_failure(self):
        out = io.StringIO()
        term = terminal_setup.Terminal(out=out, fancy=True, colour=False, width=78, rows=30)
        term.heading("Download hours", 5)
        term.failed("That did not work.", "Starboard answered 500")
        keys, right = term.step_keys()
        self.assertIn(("r", "Report this problem"), keys)
        self.assertIn("r Report this problem", out.getvalue())
        self.assertEqual(right, "Enter: recommended")
        term.heading("Download hours", 5)
        self.assertNotIn(("r", "Report this problem"), term.step_keys()[0])  # a new step clears it

    def test_plain_mode_never_draws_a_qr_code(self):
        term, out = self.term(["f", "7", "Thank you", "2", "2"], [])
        term.heading("Download hours", 5)
        self.assertEqual(term.choose("When should downloads run?", ["Set hours", "Any time"]), 1)
        text = out.getvalue()
        self.assertNotIn("QR", text)
        self.assertNotRegex(text, "[▀▄█╭│\x1b]")
        self.assertIn("https://github.com/TheMightyTRex/starboard/issues/new?title=", text)
        self.assertIn("Save to a file", text)
        self.assertIn("Back to the set-up.", text)

    def test_the_qr_code_is_chosen_by_the_window_size(self):
        # The more the window holds, the more of the report goes in, and the code always fits the window.
        report = terminal_setup.Report(terminal_setup.KINDS[0], [("What happened", "The apps list stops after Jellyfin")],
                                       (2, "What to set up"), "Install the apps?", "80 x 30", False, None)
        report.file = "~/starboard-feedback-2026-11-05-1216.md"
        expect = {(140, 60): "the report without its technical details", (100, 50): "a short report",
                  (80, 40): "a short report", (80, 30): "a short report", (80, 24): "only the title"}
        for (width, rows), holds in expect.items():
            with self.subTest(window=f"{width} by {rows}"):
                term = terminal_setup.Terminal(out=io.StringIO(), fancy=True, colour=False, width=width, rows=rows)
                url, version, edge, got = term.qr_fit(report)
                self.assertEqual(got, holds)
                self.assertLessEqual(qr.width_of(version, edge), width)
                self.assertLessEqual(qr.lines_of(version, edge), rows - 3)
                self.assertLessEqual(len(url.encode()), qr.byte_capacity(version, "L"))
                self.assertEqual(edge, 2 if rows <= 30 else qr.QUIET)

    def test_the_qr_view_draws_inside_the_window(self):
        # At 80 by 24 the whole report takes two pages, and the link has a view of its own after the code.
        # l on the QR view shows the link; Enter closes it; Done; then the question.
        term, out = self.fancy(["f", "1", "The apps list stops after Jellyfin", "", "", "", "1", "l", "", "4", "1"],
                               width=80, rows=24)
        term.heading("What to set up", 2)
        term.choose("Install the apps?", ["Yes", "No"])
        raw = out.getvalue()
        self.assertIn("Scan it with your phone's camera to open the report there.", raw)
        self.assertIn("Enter Done   l Show the link", raw)  # the QR view's menu
        self.assertIn("The link to the report", raw)
        self.assertIn("\033[38;5;16;48;5;231m", raw)  # dark on light, forced
        rows = re.findall(r"\033\[(\d+);\d+H\033\[38;5;16;48;5;231m", raw)
        self.assertTrue(rows and max(map(int, rows)) <= 24 - 2)  # never over the menu

    def test_80_by_24_uses_a_2_module_edge_and_the_title(self):
        term, _ = self.fancy([], width=80, rows=24)
        report = mock.Mock(title=lambda *a: "Broken: the apps list stops after Jellyfin", markdown=lambda short=False: "x" * 900,
                           labels=lambda: "feedback,problem", tiny=lambda words: "y" * (300 + words), compact=lambda words: "z" * (200 + words),
                           title_only=lambda: "https://github.com/TheMightyTRex/starboard/issues/new?title=Broken%3A+terminal+set-up%2C+step+2")
        url, version, edge, holds = term.qr_fit(report)
        self.assertEqual((edge, holds), (2, "only the title"))
        self.assertLessEqual(qr.lines_of(version, edge), 24 - 3)
        self.assertLessEqual(qr.width_of(version, edge), 80)
        self.assertIsNone(self.fancy([], width=60, rows=20)[0].qr_fit(report))  # too small even for the title

    def test_redact_takes_out_what_looks_private(self):
        text = terminal_setup.redact("sam@example.org at 10.0.0.4 and fe80:0:0:0:1:2:3:4 in /home/sam/media, "
                                     "key ghp_abcdefghijklmnop, WireGuard aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789abcdefg=",
                                     {"my folder answer"})
        self.assertEqual(text, "[email] at [address] and [address] in /home/[user]/media, key [key], "
                               "WireGuard [key]")
        self.assertEqual(terminal_setup.redact("in my folder answer here", {"my folder answer"}),
                         "in [your answer] here")
        # Only fingerprints of typed answers are kept, never the answers themselves.
        term = terminal_setup.Terminal(out=io.StringIO(), fancy=False, ask=Answers(["my secret folder"]))
        term.text("Where?")
        self.assertTrue(term.typed and all(isinstance(t, tuple) and len(t[1]) == 64 for t in term.typed))  # HMAC-SHA-256
        self.assertNotIn("my secret folder", repr(term.typed))
        self.assertEqual(terminal_setup.redact("it is my secret folder", term.typed), "it is [your answer]")

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


class StillWorking(unittest.TestCase):
    """Plain mode is never silent through a long job (DASH-236)."""

    def test_a_line_every_so_often_while_a_job_runs(self):
        import time
        from starboard import terminal_setup as ts
        out = []

        class Plain:
            fancy = False
            resize_due = False
            _plain = out.append
        with mock.patch.object(ts, "STILL_EVERY", 1):
            start = time.time()
            ts.Terminal._waiting(Plain(), "Starting the apps. Please wait, this can take some time...",
                                 lambda: "ok" if time.time() > start + 2.3 else None, 0.1, start)
        self.assertGreaterEqual(len(out), 2)
        self.assertEqual(out[0], "Still working: Starting the apps (0 min).")
