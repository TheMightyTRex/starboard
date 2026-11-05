"""Set Starboard up in the terminal, for a server with no desktop and no other device to hand (DASH-86).

Run by ./install.sh --terminal once Starboard is running, or by hand from the Starboard folder:
    python3 -m starboard.terminal_setup --port 8095

It asks the same questions as the browser, one step at a time. In a terminal, each step starts on a cleared screen
with a menu fixed at the bottom, and help opens as a pop-up over the step. Enter takes the recommended answer, b goes
back a step (with your last answers kept), ? shows help and q stops. With STARBOARD_PLAIN=1, --plain, a small window
or no terminal, it prints plain numbered lines instead, with nothing redrawn, which suits software that reads text
aloud. It talks to Starboard's own API on this computer, so every answer is checked exactly as the browser's would
be, and nothing changes until you confirm. Passwords and VPN keys are typed hidden and never written to the screen.
Standard library only.
"""
import argparse
import getpass
import http.client
import json
import os
import re
import shutil
import sys
import textwrap
import time

VPNS = [  # (Gluetun's provider name, shown name)
    ("protonvpn", "Proton VPN"),
    ("airvpn", "AirVPN"),
    ("private internet access", "Private Internet Access"),
    ("surfshark", "Surfshark"),
    ("expressvpn", "ExpressVPN"),
]
HELP = {
    "password": "Your password signs you in to Starboard from any device. Use 10 characters or more; a few unrelated "
                "words are easy to remember and hard to guess. If you forget it, run ./reset-password.sh.",
    "groups": "Each kind of media installs the apps that look after it. Watching installs Jellyfin, to play everything. "
              "Downloads installs the download apps and the sites to search. You can add more later in Starboard, "
              "Settings, Install apps.",
    "apps": "These are the apps for what you chose. Apps already running on this computer are left out.",
    "folders": "The media folder holds your films, series, books and downloads, all in one place so files move in an "
               "instant. The settings folder holds each app's own settings. Both are made for you if they are missing.",
    "vpn": "A VPN sends the torrent app's traffic through your VPN provider, so sites see its address, not yours. "
           "Gluetun connects it. WireGuard is faster; OpenVPN works with every provider. Your provider's website shows "
           "the details to type here. Some providers we suggest have affiliate links: see Starboard's help, VPN.",
    "hours": "Downloading uses most of your internet connection while it runs, so streaming, video calls and games on "
             "other devices can slow down. With download hours, Starboard pauses the download apps outside them and "
             "starts them again when they begin. Nothing is lost.",
    "check": "This is everything that will change. Nothing has changed yet: type b to go back and change an answer, or "
             "q to stop. The apps' files are written to Starboard's data folder, then the apps are downloaded and started.",
    "keep": "Your password is already saved. Change it later in Starboard, Settings, Security.",
}


class Stop(Exception):
    """The person typed q."""


class Back(Exception):
    """The person typed b: go back to the step before, with the answers kept."""


class Problem(Exception):
    """Starboard said no: the message is Starboard's own, for the person."""


class GoTo(Exception):
    """Starboard refused an answer from an earlier step: ask that step again."""

    def __init__(self, step, message):
        super().__init__(message)
        self.step = step


class Api:
    """Starboard's API on this computer, with the session cookie from signing in."""

    def __init__(self, port, host="127.0.0.1"):
        self.host, self.port, self.cookie = host, port, None

    def call(self, method, path, body=None, timeout=30):
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        headers = {"Content-Type": "application/json"}
        if method != "GET":
            headers["X-Starboard"] = "1"
        if self.cookie:
            headers["Cookie"] = self.cookie
        try:
            conn.request(method, path, json.dumps(body) if body is not None else None, headers)
            resp = conn.getresponse()
            raw = resp.read()
        except OSError as e:
            raise Problem(f"Starboard is not answering on port {self.port} ({e}). Is it running?") from e
        finally:
            conn.close()
        cookie = resp.getheader("Set-Cookie")
        if cookie and cookie.split(";")[0].split("=", 1)[-1]:
            self.cookie = cookie.split(";")[0]
        try:
            data = json.loads(raw) if raw else {}
        except ValueError:
            data = {}
        if resp.status >= 400:
            raise Problem(data.get("error") or f"Starboard answered {resp.status}")
        return data

STEPS = ["Your password", "Your media server", "Your VPN", "Check before anything changes", "Download hours"]
ANSI = re.compile(r"\033\[[0-9;]*[A-Za-z]|\0337|\0338")


class Terminal:
    """Questions and answers. ask and secret are replaceable, so the tests can answer.

    In a terminal at least 60 characters wide and 20 lines tall, each step clears the screen and starts with a boxed
    heading and a progress bar; a menu stays at the bottom (the lines above it scroll), summaries are cards, finished
    steps are ticked and help opens as a pop-up over the dimmed step. Colour only adds to the words: every mark has
    words after it, and recommended answers say so. With --plain, TERM=dumb or output that is not a terminal, it
    prints plain numbered lines and never redraws, which suits a screen reader (one reads box characters aloud, and
    loses its place when a screen is redrawn). NO_COLOR keeps the boxes without colour."""

    def __init__(self, out=sys.stdout, ask=input, secret=getpass.getpass, fancy=None, colour=None, width=None, rows=None):
        self.out, self._ask, self._secret = out, ask, secret
        size = shutil.get_terminal_size((80, 24))
        self.width = min(width or size.columns, 78)
        self.rows = rows or size.lines
        tty = hasattr(out, "isatty") and out.isatty()
        self.fancy = (tty and os.environ.get("TERM") != "dumb") if fancy is None else fancy
        self.fancy = self.fancy and self.width >= 60 and self.rows >= 20
        self.colour = self.fancy and not os.environ.get("NO_COLOR") if colour is None else colour and self.fancy
        self.screen = []          # what this step has shown, to draw it again after help
        self.can_back = False
        self.came_back = False    # this step was reached with b: the last answers are the defaults
        self.keys = []
        self.drawn = False        # whether the scroll area and menu are set up

    # Marks ------------------------------------------------------------------------------------------------

    def _c(self, code, text):
        return f"\033[{code}m{text}\033[0m" if self.colour else text

    def accent(self, text):
        return self._c("1;36", text)

    def dim(self, text):
        return self._c("2", text)

    def good(self, text):
        return self._c("32", text)

    def warn_colour(self, text):
        return self._c("33", text)

    def _write(self, text):
        self.out.write(text)
        self.out.flush()

    def say(self, text=""):
        print(text, file=self.out, flush=True)
        if self.fancy:
            self.screen += str(text).split("\n")

    # The screen: a cleared page per step, with the menu fixed below a scrolling area ---------------------------

    def _menu(self, keys, right=""):
        """The two bottom lines: a rule, then the keys. Drawn outside the scrolling area, so they stay put."""
        line = "   ".join(f"{self.accent(k)} {label}" for k, label in keys)
        plain = "   ".join(f"{k} {label}" for k, label in keys)
        gap = max(self.width - 4 - len(plain) - len(right), 1)
        self._write(f"\0337\033[{self.rows - 1};1H\033[2K{self.dim('─' * self.width)}"
                    f"\033[{self.rows};1H\033[2K  {line}{' ' * gap}{self.dim(right)}\0338")

    def _page(self, keys, right):
        """Clears the screen, keeps the menu on the last two lines and lets the rest scroll above it."""
        self._write(f"\033[r\033[2J\033[1;{self.rows - 2}r")
        self._menu(keys, right)
        self._write("\033[H")
        self.drawn = True

    def finish(self):
        """Gives the whole window back to the terminal: no scrolling area, cursor below everything."""
        if self.fancy and self.drawn:
            # The menu lines go (their keys no longer work), the whole window scrolls again, and the cursor goes
            # back under the last thing shown, ready for the shell's prompt.
            self._write(f"\0337\033[r\033[{self.rows - 1};1H\033[2K\033[{self.rows};1H\033[2K\0338\n")
            self.drawn = False

    def step_keys(self):
        keys = ([("b", "Back")] if self.can_back else []) + [("?", "Help"), ("q", "Stop")]
        return keys, "Enter: keep" if self.came_back else "Enter: recommended"

    def heading(self, text, step=None):
        if not self.fancy:
            self.say(f"\n== Starboard | {text}" + (f" (step {step} of {len(STEPS)})" if step else ""))
            self.say(("Type b to go back, ? for help or q to stop." if self.can_back else
                      "Type ? for help or q to stop.") if step else "")
            if self.came_back:
                self.say("You came back to this step. Your last answers are in [brackets]: press Enter to keep each one.")
            return
        self.screen = []
        self.keys = self.step_keys()
        self._page(*self.keys)
        inner = self.width - 4
        right = f"step {step} of {len(STEPS)}" if step else ""
        # "Starboard | Your password": the product name in bold, then the step, then the count on the right.
        left = f"Starboard | {text}"
        gap = max(inner - len(left) - len(right) - 2, 1)
        self.say(self.dim("┌" + "─" * (inner + 2) + "┐"))
        self.say(self.dim("│") + "  " + self._c("1", "Starboard") + self.dim(" | ") + self.accent(text) + " " * gap
                 + self.dim(right) + "  " + self.dim("│"))
        self.say(self.dim("└" + "─" * (inner + 2) + "┘"))
        if step:
            bar = self.width - 12
            done = round(bar * (step - 1) / len(STEPS))
            pct = f"{round(100 * (step - 1) / len(STEPS)):>3}%"
            self.say("  " + self._c("36", "█" * done) + self.dim("░" * (bar - done)) + "  " + self.dim(pct))
        if self.came_back:
            self.say("")
            self.note("You came back to this step. Your last answers are in [brackets]: press Enter to keep each one.")
            self.say("")

    def _redraw(self):
        """The step as it was before help opened: the page again, then its last lines."""
        self._page(*self.keys)
        for line in self.screen[-(self.rows - 3):]:
            self._write(line + "\n")

    def popup(self, title, text):
        """Help over the step: the step is dimmed behind a box in the middle. Enter closes it (Esc then Enter too).
        Long help shows a page at a time. Plain output prints the help under the question instead."""
        if not self.fancy:
            self.note(text)
            return
        bw = min(62, self.width - 6)
        left, inner = (self.width - bw) // 2, bw - 4
        body = []
        for para in text.split("\n\n"):
            body += textwrap.wrap(para, inner) + [""]
        room = max(self.rows - 10, 4)
        pages = [body[i:i + room] for i in range(0, len(body), room)] or [[""]]
        behind = [ANSI.sub("", line) for line in self.screen[-(self.rows - 3):]]
        behind += [""] * (self.rows - 2 - len(behind))
        for n, part in enumerate(pages):
            more = n < len(pages) - 1
            close = "Enter: more below" if more else "Enter or Esc: close help"
            box = [self._c("36", "╭─ ") + self.accent(title[:bw - 6]) + self._c("36", " " + "─" * max(bw - 5 - len(title[:bw - 6]), 0) + "╮")]
            box += [self._c("36", "│") + " " + line.ljust(inner) + " " + self._c("36", "│") for line in [""] + part]
            box += [self._c("36", "│") + " " + self.dim(close.rjust(inner)) + " " + self._c("36", "│"),
                    self._c("36", "╰" + "─" * (bw - 2) + "╯")]
            top = 3
            self._write(f"\033[r\033[2J")
            self._menu([("Enter", "Close help" if not more else "More")], "")
            for row, line in enumerate(behind[:self.rows - 2], 1):
                self._write(f"\033[{row};1H" + self._c("2;90", line[:self.width]))
            for i, line in enumerate(box):
                self._write(f"\033[{top + i};{left + 1}H{line}")
            self._write(f"\033[{top + len(box) - 2};{left + bw - 1}H")  # inside the box, after "close help"
            self._ask("")
        self._redraw()

    def card(self, title, rows, colour="36"):
        """A box of label and value rows, for reading rather than answering."""
        if not self.fancy:
            self.say(f"\n{title}")
            for label, value in rows:
                self.say(f"{label}: {value}")
            return
        label_w = max(len(label) for label, _ in rows) + 2
        inner = self.width - 4
        top = f"─ {title} "
        self.say("")
        self.say(self._c(colour, "╭" + top + "─" * (inner + 2 - len(top)) + "╮"))
        for label, value in rows:
            lines = textwrap.wrap(str(value), inner - label_w) or [""]
            for i, line in enumerate(lines):
                left = (label if i == 0 else "").ljust(label_w)
                self.say(self._c(colour, "│") + " " + self.dim(left) + line.ljust(inner - label_w) + " " + self._c(colour, "│"))
        self.say(self._c(colour, "╰" + "─" * (inner + 2) + "╯"))

    def ok(self, text):
        self.say(f"  {self.good('✔')} {text}" if self.fancy else text)

    def warn(self, text):
        self.say(f"  {self.warn_colour('⚠')} {text}" if self.fancy else text)

    def note(self, text):
        """A paragraph, wrapped to the width and set in from the box."""
        if not self.fancy:
            self.say(text)
            return
        for line in textwrap.wrap(text, self.width - 4):
            self.say(f"  {line}")

    # Questions ----------------------------------------------------------------------------------------------

    def _prompt(self, text):
        return f"  {self.accent('›')} {text}" if self.fancy else text

    def _read(self, prompt, help_key, title="Help", extra=()):
        """One answer. q stops, b goes back a step, ? opens help; anything in extra is returned as typed."""
        while True:
            shown = self._prompt(prompt)
            answer = self._ask(shown).strip()
            if self.fancy:
                self.screen.append(shown + answer)
            low = answer.lower()
            if low in ("q", "quit"):
                raise Stop()
            if low == "b" and self.can_back:
                raise Back()
            if low == "b":
                self.say("This is the first step, so there is nothing to go back to.")
                continue
            if answer == "?":
                self.popup(f"Help: {title}", HELP.get(help_key, "There is no more help for this question."))
                continue
            if low in extra:
                return low
            return answer

    def _options(self, options, defaults, start=0):
        """Options are text, or (name, about) pairs set in two columns."""
        name_w = max((len(o[0]) for o in options if isinstance(o, tuple)), default=0) + 2
        for i, o in enumerate(options, 1):
            if i <= start:
                continue
            text = f"{o[0]}: {o[1]}" if isinstance(o, tuple) else o
            if not self.fancy:
                self.say(f"  {i}. {text}")
                continue
            mark = self.accent("●") if i - 1 in defaults else " "
            if isinstance(o, tuple):  # the about column wraps under itself, inside the width
                about = textwrap.wrap(o[1], self.width - 8 - name_w) or [""]
                text = o[0].ljust(name_w) + self.dim(about[0])
                text += "".join("\n" + " " * (8 + name_w) + self.dim(more) for more in about[1:])
            text = re.sub(r"\(recommended[^)]*\)|\(your last answer\)", lambda m: self.good(m.group(0)), text)
            self.say(f"  {mark} {self.accent(str(i).rjust(2))}  {text}")

    def _title(self, question):
        return question.rstrip("?").rstrip(".")[:40].lower()

    def choose(self, question, options, default=1, help_key=None):
        """Numbered options; returns the index (0-based)."""
        self.say(f"\n  {question}" if self.fancy else f"\n{question}")
        self._options(options, {default - 1})
        while True:
            answer = self._read(f"Your choice [{default}]: ", help_key, self._title(question)) or str(default)
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            self.say(f"Type a number from 1 to {len(options)}, ? for help or q to stop.")

    def choose_many(self, question, options, defaults, help_key=None):
        """Numbered options, several at once (1,3,4); returns the indexes chosen. A long list on a short screen
        shows what fits, and m shows the rest."""
        lead = "  " if self.fancy else ""
        self.say(f"\n{lead}{question} Type the numbers, separated by commas.")
        fits = len(options)
        if self.fancy:
            fits = max(min(len(options), self.rows - 2 - len(self.screen) - 4), 4)
        self._options(options[:fits], set(defaults))
        if fits < len(options):
            self.say("  " + self.dim(f"{len(options) - fits} more: type m to see them"))
        shown = ",".join(str(i + 1) for i in defaults)
        while True:
            answer = self._read(f"Your choice [{shown}]: ", help_key, self._title(question), extra=("m",)) or shown
            if answer == "m":
                if fits < len(options):
                    self._options(options, set(defaults), start=fits)
                    fits = len(options)
                continue
            parts = [p.strip() for p in answer.replace(" ", ",").split(",") if p.strip()]
            if parts and all(p.isdigit() and 1 <= int(p) <= len(options) for p in parts):
                return sorted({int(p) - 1 for p in parts})
            self.say(f"Type numbers from 1 to {len(options)}, such as 1,2, or ? for help, or q to stop.")

    def yes_no(self, question, default=True, help_key=None):
        while True:
            answer = self._read(f"{question} [{'Y/n' if default else 'y/N'}]: ", help_key, self._title(question)).lower()
            if not answer:
                return default
            if answer[0] in "yn":
                return answer[0] == "y"
            self.say("Type y for yes or n for no.")

    def text(self, question, default="", help_key=None):
        shown = f" [{default}]" if default else ""
        return self._read(f"{question}{shown}: ", help_key, self._title(question)) or default

    def hidden(self, question, keep=False, help_key="password"):
        """Typed without showing it. With keep, Enter on its own keeps the one typed before (returns None)."""
        while True:
            hint = "nothing shows as you type" + ("; Enter keeps the one you typed before" if keep else "")
            shown = self._prompt(f"{question} ({hint}): ")
            answer = self._secret(shown)
            if self.fancy:
                self.screen.append(shown)
            low = answer.strip().lower()
            if low == "q":
                raise Stop()
            if low == "b" and self.can_back:
                raise Back()
            if answer.strip() == "?":
                self.popup("Help", HELP.get(help_key, "There is no more help for this question."))
                continue
            if keep and not answer:
                return None
            return answer

    def waiting(self, text, check, wait):
        """Shows a turning mark and the time taken until check() returns something, then returns it."""
        began, turn = time.time(), 0
        while True:
            result = check()
            if result is not None:
                if self.fancy:
                    self._write("\r" + " " * (self.width - 1) + "\r")
                return result
            if self.fancy:
                secs = int(time.time() - began)
                self._write(f"\r  {self.accent('◐◓◑◒'[turn % 4])} {text} {self.dim(f'{secs // 60} min {secs % 60:02d} s')}")
                turn += 1
            time.sleep(wait)


# The steps. Each takes what was answered before (state), so going back shows the last answers as the defaults.

def step_password(api, term, state):
    if state.get("password"):
        term.heading("Your password", 1)
        term.ok("Your password is saved.")
        term.note("Change it later in Starboard, Settings, Security.")
        term.text("Press Enter to carry on", help_key="keep")
        return True
    token_file = os.path.join(state["data_dir"], "setup-token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read().strip()
        term.heading("Your password", 1)
        term.note("Choose the password for Starboard. You use it to sign in from any device. No setup code is needed: "
                  "you are on the server itself. Type ? for help.")
        while True:
            first = term.hidden("Choose a password, 10 characters or more")
            if len(first) < 10:
                term.say("Use at least 10 characters.")
                continue
            if term.hidden("Type it again") != first:
                term.say("The two did not match. Try again.")
                continue
            try:
                api.call("POST", "/api/setup", {"token": token, "password": first})
            except Problem as e:
                term.say(f"Starboard said: {e}")
                continue
            term.ok("Password saved. You are signed in.")
            state["password"] = first
            return True
    term.heading("Sign in", 1)
    term.note("Starboard already has a password. Type it to carry on (forgotten it? Stop with q and run ./reset-password.sh).")
    for _ in range(5):
        password = term.hidden("Your Starboard password")
        try:
            api.call("POST", "/api/login", {"password": password})
            term.ok("Signed in.")
            state["password"] = password
            return True
        except Problem as e:
            term.say(f"Starboard said: {e}")
    raise Problem("Too many wrong passwords. Run this again later")


def step_apps(api, term, state):
    """Sets state["choice"] (the Install apps choice) and state["names"], or None to install nothing."""
    overview = state.get("overview") or api.call("GET", "/api/stack")
    state["overview"] = overview
    groups = overview["groups"]
    term.heading("Your media server", 2)
    last = state.get("apps", {})
    if term.choose("Install the apps for your media server now?",
                   ["Yes (recommended)", "No: I have my apps already, or I will add them later in the browser"],
                   last.get("install", 1), help_key="groups") == 1:
        last["install"], state["apps"], state["choice"] = 2, last, None
        return True
    last["install"] = 1
    picked = term.choose_many("What do you want?", [(g["name"], g["about"]) for g in groups],
                              last.get("groups", [i for i, g in enumerate(groups) if g["default"]]), help_key="groups")
    last["groups"] = picked
    keys = {groups[i]["key"] for i in picked}
    apps = [a for a in overview["apps"] if set(a["groups"]) & keys and not a["installed"]]
    if not apps:
        term.say("Every app for that is running already. Nothing to install.")
        state["apps"], state["choice"] = last, None
        return True
    before = last.get("chosen")
    chosen = [a for a in apps if (a["key"] in before if before is not None else a["default"])]
    if chosen:
        term.card("These apps would be installed", [("Apps", ", ".join(a["name"] for a in chosen)),
                                                    ("Memory", f"about {sum(a['memory'] for a in chosen):,} MB")])
    if not chosen or term.choose("Install these?", ["Yes (recommended)", "Let me choose app by app"],
                                 help_key="apps") == 1:
        was = {a["key"] for a in chosen}
        chosen = []
        for a in apps:
            about = f" ({a['notes']})" if a["notes"] else ""
            if term.yes_no(f"Install {a['name']}{about}?", a["key"] in was if was else a["default"], help_key="apps"):
                chosen.append(a)
    last["chosen"] = [a["key"] for a in chosen]
    if not chosen:
        term.say("No apps chosen. Nothing to install.")
        state["apps"], state["choice"] = last, None
        return True
    d = overview["defaults"]
    term.say("")
    data_dir = term.text("Media folder, for films, series, books and downloads", last.get("data_dir", d["data_dir"]),
                         help_key="folders")
    config_dir = term.text("Settings folder, for each app's own settings", last.get("config_dir", d["config_dir"]),
                           help_key="folders")
    last.update(data_dir=data_dir, config_dir=config_dir)
    state["apps"] = last
    state["choice"] = {"apps": [a["key"] for a in chosen], "data_dir": data_dir, "config_dir": config_dir,
                       "puid": d["puid"], "pgid": d["pgid"], "tz": d["tz"]}
    state["names"] = [a["name"] for a in chosen]
    return True


def step_vpn(api, term, state):
    choice = state.get("choice")
    if not choice or "gluetun" not in choice["apps"]:
        return False
    last = state.get("vpn_answers", {})
    term.heading("Your VPN", 3)
    term.note("Some of the VPN providers below have affiliate links in Starboard's help. If you sign up through one, the "
              "provider pays a small amount towards Starboard's development, at no extra cost to you.")
    pick = term.choose("Which VPN provider do you have?", [n for _, n in VPNS] + ["Another one that Gluetun supports"],
                       last.get("pick", 1), help_key="vpn")
    if pick < len(VPNS):
        provider = VPNS[pick][0]
    else:
        provider = term.text("Its name, as Gluetun's list writes it (for example: mullvad)", last.get("other", ""),
                             help_key="vpn").lower()
        last["other"] = provider
    last["pick"] = pick + 1
    kind_i = term.choose("How should it connect?", ["WireGuard (recommended: faster)", "OpenVPN"],
                         last.get("kind", 1), help_key="vpn")
    kind = ["wireguard", "openvpn"][kind_i]
    countries = term.text("Countries to connect through (Enter for any)", last.get("countries", ""), help_key="vpn")
    old = state.get("vpn") or {}
    vpn = {"provider": provider, "type": kind, "countries": countries}
    if kind == "wireguard":
        key = term.hidden("WireGuard private key, from your provider", keep=bool(old.get("wireguard_private_key")),
                          help_key="vpn")
        vpn["wireguard_private_key"] = old.get("wireguard_private_key", "") if key is None else key
        vpn["wireguard_addresses"] = term.text("WireGuard address from your provider, ending in /32",
                                               last.get("address", ""), help_key="vpn")
        last["address"] = vpn["wireguard_addresses"]
    else:
        vpn["openvpn_user"] = term.text("OpenVPN user name, from your provider", last.get("user", ""), help_key="vpn")
        secret = term.hidden("OpenVPN password", keep=bool(old.get("openvpn_password")), help_key="vpn")
        vpn["openvpn_password"] = old.get("openvpn_password", "") if secret is None else secret
        last["user"] = vpn["openvpn_user"]
    last.update(kind=kind_i + 1, countries=countries)
    state["vpn_answers"], state["vpn"] = last, vpn
    return True


def step_check(api, term, state, wait=2.0):
    """Shows what will be written, writes it once confirmed, and starts the apps when Starboard may."""
    choice = state.get("choice")
    if not choice:
        return False
    if "gluetun" in choice["apps"]:
        choice["vpn"] = state.get("vpn")
    else:
        choice.pop("vpn", None)
    term.heading("Check before anything changes", 4)
    names = state.get("names") or choice["apps"]
    rows = [("Install", ", ".join(names)), ("Media folder", choice["data_dir"]), ("Settings folder", choice["config_dir"])]
    if choice.get("vpn"):
        rows.append(("VPN", f"{dict(VPNS).get(choice['vpn']['provider'], choice['vpn']['provider'])}, "
                            f"{'WireGuard' if choice['vpn']['type'] == 'wireguard' else 'OpenVPN'}"))
    if state.get("written"):
        term.card("Written already", rows)
        term.ok("The apps' files are written.")
        term.note("Earlier answers cannot change here any more. Change the apps later in Starboard, Settings, Install apps.")
        term.text("Press Enter to carry on", help_key="check")
        return True
    try:
        preview = api.call("POST", "/api/stack/preview", choice)
    except Problem as e:
        low = str(e).lower()
        raise GoTo(2 if any(w in low for w in ("vpn", "wireguard", "openvpn")) else 1, str(e)) from e
    term.card("What will change", rows)
    for line in preview.get("moved", []):
        term.warn(line)
    term.say("")
    term.note("Nothing has changed yet. Type b to go back and change an answer.")
    if not term.yes_no("Write the apps' files now?", True, help_key="check"):
        term.say("Nothing written.")
        return True
    written = api.call("POST", "/api/stack/write", choice)
    state["written"] = True
    term.ok(f"{len(choice['apps'])} apps written.")
    if not written.get("can_start"):
        term.note("Starboard cannot start apps itself, because it has no full Docker access. Start them with:")
        term.say(f"  {written['command']}")
        return True
    if not term.yes_no("Start the apps now? They are downloaded first, which can take a few minutes.", True):
        term.say(f"Start them later with:  {written['command']}")
        return True
    api.call("POST", "/api/stack/start", {"password": state["password"]})
    if not term.fancy:
        term.say("Downloading and starting the apps ...")

    def finished():
        job = api.call("GET", "/api/stack/job")
        return job if job.get("finished") else None
    job = term.waiting("Downloading and starting the apps ...", finished, wait)
    if job.get("ok"):
        term.ok(f"All {len(choice['apps'])} apps are running.")
        return True
    term.warn("The apps did not all start. The last lines Docker wrote:")
    for line in (job.get("log") or "").strip().splitlines()[-12:]:
        term.say(f"  {line}")
    return True


def step_hours(api, term, state):
    last = state.get("hours", {})
    term.heading("Download hours", 5)
    term.note("Downloading uses most of your internet connection while it runs, so other devices can slow down. "
              "Downloading at night keeps the day free.")
    if term.choose("When should downloads run?", ["Only at set hours (recommended)", "At any time"],
                   last.get("when", 1), help_key="hours") == 1:
        api.call("PUT", "/api/config/general", {"download_hours": {"enabled": False}})
        state["hours"] = {"when": 2}
        return True
    while True:
        start = term.text("From, as an hour from 0 to 23", str(last.get("start", 1)), help_key="hours")
        end = term.text("Until, as an hour from 0 to 23", str(last.get("end", 7)), help_key="hours")
        try:
            api.call("PUT", "/api/config/general", {"download_hours": {"enabled": True, "start": int(start), "end": int(end)}})
            term.ok(f"Download hours: {int(start):02d}:00 to {int(end):02d}:00. Change them later in Settings, General.")
            state["hours"] = {"when": 1, "start": int(start), "end": int(end)}
            return True
        except (ValueError, Problem) as e:
            term.say(f"That did not work: {e}. Type whole hours, such as 1 and 7.")


STEP_FUNCTIONS = [step_password, step_apps, step_vpn, step_check, step_hours]


def run(api, term, data_dir, port, address=""):
    if not term.fancy:
        term.say("\nStarboard set-up, in the terminal")
        term.note("Every question has a number or a word to type, and Enter takes the answer in [brackets]. "
                  "Type ? at any question for help, b to go back a step, or q to stop. You can carry on later in a "
                  "browser instead.")
    state = {"data_dir": data_dir}
    shown, i = [], 0  # the steps shown so far, for Back
    try:
        while i < len(STEP_FUNCTIONS):
            term.can_back = bool(shown)
            try:
                if STEP_FUNCTIONS[i](api, term, state):
                    shown.append(i)
                i += 1
                term.came_back = False
            except Back:
                i = shown.pop() if shown else 0
                term.came_back = True
            except GoTo as e:
                term.warn(f"Starboard said: {e}")
                term.text("Press Enter to change that answer")
                while shown and shown[-1] >= e.step:
                    shown.pop()
                i = e.step
        term.can_back = False
        if term.fancy:
            term.heading("Done")
        rows = [("On this computer", f"http://localhost:{port}")]
        if address:
            rows.append(("On your other devices", f"http://{address}:{port}"))
        rows.append(("Ask these again", f"python3 -m starboard.terminal_setup --port {port}"))
        term.card("Starboard is ready", rows, colour="32")
        term.note("Everything here can be changed later in Starboard's Settings.")
    finally:
        term.finish()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Set Starboard up in the terminal.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("STARBOARD_PORT", "8095")))
    parser.add_argument("--data", default="data", help="Starboard's data folder (default: ./data)")
    parser.add_argument("--address", default="", help="This computer's address on the home network, to show at the end")
    parser.add_argument("--plain", action="store_true", help="Plain lines with no boxes, colour or redrawing, for a screen reader")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        print("Stopped: this needs a terminal to type in. Finish set-up in a browser instead.", file=sys.stderr)
        return 2
    term = Terminal(fancy=False if args.plain or os.environ.get("STARBOARD_PLAIN") else None)
    try:
        return run(Api(args.port), term, args.data, args.port, args.address)
    except Stop:
        term.say("\nStopped. Nothing else was changed. Carry on later in a browser, or run this again.")
        return 1
    except (Problem, KeyboardInterrupt, EOFError) as e:
        term.finish()
        term.say(f"\nStopped: {e}" if isinstance(e, Problem) else "\nStopped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
