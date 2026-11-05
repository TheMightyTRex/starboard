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
import platform
import re
import shutil
import signal
import socket
import sys
import textwrap
import time
import urllib.parse

from starboard import qr

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



# Feedback (f at any question): Snaglist's kinds and questions, sent as a pre-filled GitHub issue. Each kind is
# (key, label, short name for the QR code, group, questions); a question is (label, hint, required, options).
USING = ["Keyboard only", "A screen reader", "Zoom or large text", "Voice control", "Switch access",
         "High contrast or forced colours", "Nothing special", "Something else"]
KINDS = [
    ("bug", "Something is broken", "Broken", "problem",
     [("What happened", "", True, None), ("What you expected", "", False, None)]),
    ("ux", "Hard to use", "Hard to use", "problem", [("What is wrong", "What did you expect, and what happened?", True, None)]),
    ("content", "Words are wrong", "Wrong words", "problem",
     [("What is wrong", "", True, None), ("Suggested wording", "", False, None)]),
    ("accessibility", "Hard to use with my tools or needs", "Hard with my tools", "problem",
     [("What is wrong", "", True, None), ("What were you using", "", False, USING)]),
    ("feature", "A new feature", "New feature", "suggestion",
     [("What would you like to be able to do", "", True, None),
      ("What would it help you with", "The task or goal behind it, so the team can find the best way.", False, None),
      ("How do you manage today", "A workaround, another app, or not at all.", False, None)]),
    ("idea", "Make something better", "Could be better", "suggestion",
     [("What could be better", "", True, None), ("Your suggestion", "", False, None)]),
    ("other", "Something else", "Feedback", "suggestion", [("Your message", "", True, None)]),
]
SENDS = ["Show as a QR code (recommended)", "Show the link", "Save to a file", "Cancel"]
REPO = "TheMightyTRex/starboard"
QR_LIMIT = 1200    # bytes: the most a QR code holds and still scans reliably from a terminal
LINK_LIMIT = 2000  # characters: a longer link is hard to copy from a terminal; the file has the whole report
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Anonymity, as Snaglist's: anything that looks like an email address, a key or token, an address or a long number.
PATTERNS = [
    (r"[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}", "[email]"),
    (r"\b(?:ghp|gho|github_pat|sk|pk|xox[bap])[-_][A-Za-z0-9_-]{8,}", "[key]"),
    (r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+", "[key]"),
    (r"\bAKIA[0-9A-Z]{16}\b", "[key]"),
    (r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{6,}", "[key]"),
    (r"(?i)(?:\b|_)(?:bearer|token|api[_-]?key|password|passwd|pwd|secret|private[_-]?key|session(?:[_-]?id)?|"
     r"auth(?:orization)?)\s*[:=]\s*\S+", "[key]"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b", "[address]"),
    (r"(?i)\b(?:[0-9a-f]{1,4}:){3,7}[0-9a-f]{1,4}\b", "[address]"),
    (r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "[id]"),
    (r"\b[A-Za-z0-9_-]*\d[A-Za-z0-9_-]*[A-Za-z][A-Za-z0-9_-]{22,}\b", "[key]"),
    (r"[A-Za-z0-9+/]{20,}={1,2}", "[key]"),
    (r"\+?\d[\d ()-]{5,}\d", "[number]"),
    (r"(/home/|/Users/|[A-Za-z]:\\Users\\)[^/\\\s]+", r"\1[user]"),
]


def redact(text, secrets=()):
    """Takes out what was typed as an answer (longest first), then anything that looks private."""
    out = str(text or "")
    for value in sorted({s for s in secrets if s and len(s) >= 4}, key=len, reverse=True):
        out = out.replace(value, "[your answer]")
    for pattern, label in PATTERNS:
        out = re.sub(pattern, label, out)
    for name, label in ((_user(), "[user]"), (socket.gethostname().split(".")[0], "[computer]")):
        if name and len(name) >= 3:
            out = re.sub(rf"(?<![\w-]){re.escape(name)}(?![\w-])", label, out)
    return out


def _user():
    try:
        return getpass.getuser()
    except Exception:  # no user name to be found: nothing to take out
        return ""


def clip(text, n):
    return text if len(text) <= n else text[:max(n - 3, 0)].rstrip() + "..."


def starboard_version():
    try:
        with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def system_name():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return f"{platform.system()} {platform.release()}".strip() or "unknown"


def issue_url(title, body, labels):
    q = lambda text: urllib.parse.quote_plus(text, safe=":/,()!*';?")  # noqa: E731
    return f"https://github.com/{REPO}/issues/new?title={q(title)}&body={q(body)}&labels={q(labels)}"


class Report:
    """One piece of feedback: the kind, the person's own words and what the set-up knows about where it happened.
    Everything in it has been through redact() already; nothing typed as an answer to the set-up is in it."""

    def __init__(self, kind, answers, step, part, window, plain, error):
        self.kind, self.answers, self.step, self.part = kind, answers, step, part
        self.window, self.plain, self.error = window, plain, error
        self.version, self.system, self.processor = starboard_version(), system_name(), platform.machine() or "unknown"
        self.created = time.strftime("%Y-%m-%d %H:%M")
        self.file = None  # where Save to a file put it, as shown (~/...)

    @property
    def label(self):
        return self.kind[1]

    def page(self):
        n, name = self.step
        return f"Terminal set-up, step {n}: {name}" if n else f"Terminal set-up: {name}"

    def title(self, n=90):
        error = (self.error or "").strip().split("\n")[-1].split(": ", 1)[-1]
        first = next((a for _, a in self.answers if len(a) > 8), error or self.label).split("\n")[0]
        where = f"Terminal set-up, step {self.step[0]}" if self.step[0] else "Terminal set-up"
        return clip(f"{where}: {first}", n)

    def labels(self):
        return f"feedback,{self.kind[3]},type: {self.kind[0]}"

    def markdown(self, short=False):
        cell = lambda v: str(v).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")  # noqa: E731
        lines = []
        for label, text in self.answers:
            lines += [f"**{label}**", clip(text, 600) if short else text, ""]
        n, name = self.step
        rows = [("Report", self.label), ("App", f"Starboard {self.version}"), ("Page", self.page()),
                ("Path", f"`terminal-setup/step-{n}`" if n else "`terminal-setup`"),
                ("Part", f'"{self.part}"' if self.part else ""), ("Window", self.window),
                ("System", f"{self.system}, {self.processor}"), ("Plain mode", self.plain), ("Reported", self.created)]
        lines += ["| | |", "|---|---|"] + [f"| {k} | {cell(v)} |" for k, v in rows if v]
        if self.error:
            error = self.error
            if short:
                error = clip("\n".join(error.splitlines()[-4:]), 300)
            lines += ["", "**Last error**", "", "```", error, "```"]
        if short:
            lines += ["", "_Shortened to fit. The whole report was saved on the server._"]
        lines += ["", "<sub>Sent with Starboard's terminal set-up, which leaves out passwords, keys, VPN details, the "
                      "setup code and the answers typed into the set-up.</sub>"]
        # Nothing in a report may notify anyone on GitHub: an invisible space after @ stops a mention.
        return re.sub(r"@(?=[A-Za-z0-9-])", "@\u200b", "\n".join(lines))

    def text(self):
        """The report as plain lines, as it is shown before sending."""
        md = self.markdown()
        md = re.sub(r"^\|---\|---\|$|^\| \| \|$", "", md, flags=re.M)
        md = re.sub(r"^\| (.+?) \| (.*) \|$", r"\1: \2", md, flags=re.M)
        md = re.sub(r"\*\*|`|</?sub>|\u200b", "", md)
        md = re.sub(r"^_(.*)_$", r"\1", md, flags=re.M)
        return re.sub(r"\n{3,}", "\n\n", md).strip().split("\n")

    def link(self):
        """The issue address with the whole report, or a shorter one when that is too long to copy; and whether it
        was shortened."""
        for short in (False, True):
            url = issue_url(self.title(), self.markdown(short), self.labels())
            if len(url) <= LINK_LIMIT:
                return url, short
        return self.tiny(400), True

    def compact(self, words):
        """For a small window: the step and the person's first words as the title, and a body of one line saying
        where the whole report is, with no labels."""
        n, _ = self.step
        said = " ".join(a.replace("\n", " ") for _, a in self.answers) or (self.error or "").split("\n")[-1]
        title = f"{self.kind[2]}: step {n}" if n else f"{self.kind[2]}: terminal set-up"
        if said and words:
            title += ": " + clip(said, words).rstrip(".")
        body = f"Starboard {self.version}." + (f" Whole report: {self.file}" if self.file else "")
        q = urllib.parse.quote_plus
        return f"https://github.com/{REPO}/issues/new?title={q(title)}&body={q(body)}"

    def title_only(self):
        """The smallest address of all, for the smallest windows: the title alone, with no body or labels."""
        n, _ = self.step
        title = f"{self.kind[2]}: terminal set-up" + (f", step {n}" if n else "")
        return f"https://github.com/{REPO}/issues/new?title={urllib.parse.quote_plus(title)}"

    def tiny(self, words):
        """The smallest report: the title and one or two sentences, for a QR code that has to fit the window."""
        n, name = self.step
        said = " ".join(a.replace("\n", " ") for _, a in self.answers) or (self.error or "").split("\n")[-1]
        body = f"{self.kind[2]} at step {n}: {name}." if n else f"{self.kind[2]} in the terminal set-up."
        if said and words:
            body += " " + clip(said, words).rstrip(".") + "."
        body += f" Starboard {self.version}, {self.system}."
        if self.file:
            body += f" Full report saved on the server as {self.file}."
        return issue_url(self.title(min(60, 30 + words)), body, self.labels())


class Closed(Exception):
    """The person typed q in the feedback: back to the step."""


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
        self.last_error = None   # Starboard's own reply to the last call that failed, for a feedback report
        self.on_error = None

    def _failed(self, method, path, message):
        self.last_error = f"{method} {path}: {message}"
        if self.on_error:
            self.on_error(self.last_error)
        return Problem(message)

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
            raise self._failed(method, path, f"Starboard is not answering on port {self.port} ({e}). Is it running?") from e
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
            raise self._failed(method, path, data.get("error") or f"Starboard answered {resp.status}")
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
        self.fixed_size = (width, rows)  # given by a test; otherwise the window is measured at every step
        self._measure()
        tty = hasattr(out, "isatty") and out.isatty()
        self.fancy = (tty and os.environ.get("TERM") != "dumb") if fancy is None else fancy
        self.fancy = self.fancy and self.width >= 60 and self.rows >= 20
        self.colour = self.fancy and not os.environ.get("NO_COLOR") if colour is None else colour and self.fancy
        self.header = []          # the step's heading box and progress bar: kept at the top, never scrolled away
        self.screen = []          # what this step has shown under the heading, to draw it again after help
        self.pending = ""         # the question waiting for an answer, to write again after the window changes size
        self.can_back = False
        self.came_back = False    # this step was reached with b: the last answers are the defaults
        self.keys = []
        self.drawn = False        # whether the scroll area and menu are set up
        self.step = (None, "")    # (number, name) of the step shown, for feedback
        self.part = ""            # the question being asked, for feedback
        self.typed = set()        # answers typed to the set-up and hidden ones: never in a report
        self.problem = None       # the last thing that failed at this step: r reports it
        self.last_error = None    # Starboard's reply to the last failed call, or the apps' start log
        self.plain_asked = False  # plain lines because the person asked (STARBOARD_PLAIN or --plain)
        self.save_dir = os.path.expanduser("~")

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

    def _measure(self):
        """The window's size now: columns and lines (a test can fix them)."""
        size = shutil.get_terminal_size((80, 24))
        self.cols = self.fixed_size[0] or size.columns   # the whole window, for a QR code
        self.width = min(self.cols, 78)
        self.rows = self.fixed_size[1] or size.lines

    def watch_size(self):
        """Draws the step again when the window changes size, keeping the heading, the bar and the menu in place."""
        if self.fancy and hasattr(signal, "SIGWINCH") and self.fixed_size == (None, None):
            signal.signal(signal.SIGWINCH, lambda *_: self._resized())

    def _resized(self):
        self._measure()
        if self.fancy and self.drawn and self.width >= 60 and self.rows >= 20:
            self._redraw()
            self._write(self.pending)

    def _region(self):
        """Lines between the fixed heading and the fixed menu: the only part that scrolls."""
        return max(self.rows - 2 - len(self.header), 3)

    def _menu(self, keys, right=""):
        """The two bottom lines: a rule, then the keys. Drawn outside the scrolling area, so they stay put."""
        line = "   ".join(f"{self.accent(k)} {label}" for k, label in keys)
        plain = "   ".join(f"{k} {label}" for k, label in keys)
        gap = max(self.width - 4 - len(plain) - len(right), 1)
        self._write(f"\0337\033[{self.rows - 1};1H\033[2K{self.dim('─' * self.width)}"
                    f"\033[{self.rows};1H\033[2K  {line}{' ' * gap}{self.dim(right)}\0338")

    def _page(self, keys, right):
        """Clears the screen and draws the step's heading box and progress bar at the top and the menu on the last
        two lines. Only the lines between them scroll, so the heading, the bar and the menu are always in view."""
        top = len(self.header) + 1
        self._write(f"\033[r\033[2J")
        for i, line in enumerate(self.header, 1):
            self._write(f"\033[{i};1H{line}")
        self._write(f"\033[{top};{self.rows - 2}r")
        self._menu(keys, right)
        self._write(f"\033[{top};1H")
        self.drawn = True

    def finish(self):
        """Gives the whole window back to the terminal: no scrolling area, cursor below everything."""
        if self.fancy and self.drawn:
            # The menu lines go (their keys no longer work), the whole window scrolls again, and the cursor goes
            # back under the last thing shown, ready for the shell's prompt.
            self._write(f"\0337\033[r\033[{self.rows - 1};1H\033[2K\033[{self.rows};1H\033[2K\0338\n")
            self.drawn = False

    def step_keys(self):
        right = "Enter: keep" if self.came_back else "Enter: recommended"
        keys = ([("b", "Back")] if self.can_back else []) + [("?", "Help"), ("f", "Feedback"), ("q", "Stop")]
        if self.problem:
            keys.insert(-1, ("r", "Report this problem"))
            if sum(len(k) + len(label) + 4 for k, label in keys) + len(right) + 4 > self.width:
                keys.remove(("f", "Feedback"))  # f still works; r is feedback with the error filled in
        return keys, right

    def heading(self, text, step=None):
        self.step, self.problem = (step, text), None
        if not self.fancy:
            self.say(f"\n== Starboard | {text}" + (f" (step {step} of {len(STEPS)})" if step else ""))
            self.say(("Type b to go back, ? for help, f to send feedback or q to stop." if self.can_back else
                      "Type ? for help, f to send feedback or q to stop.") if step else "")
            if self.came_back:
                self.say("You came back to this step. Your last answers are in [brackets]: press Enter to keep each one.")
            return
        if self.fixed_size == (None, None):
            self._measure()  # the window may have changed size since the last step
        self.screen = []
        self.keys = self.step_keys()
        self.header_args = (text, step)
        self.header = self._header(text, step)
        self._page(*self.keys)
        if self.came_back:
            self.say("")
            self.note("You came back to this step. Your last answers are in [brackets]: press Enter to keep each one.")
            self.say("")

    def _header(self, text, step):
        """The heading box ("Starboard | step" and "step n of 5") and the progress bar, fitted to the width now."""
        inner = self.width - 4
        right = f"step {step} of {len(STEPS)}" if step else ""
        # "Starboard | Your password": the product name in bold, then the step, then the count on the right.
        left = f"Starboard | {text}"
        gap = max(inner - len(left) - len(right) - 2, 1)
        lines = [self.dim("┌" + "─" * (inner + 2) + "┐"),
                 self.dim("│") + "  " + self._c("1", "Starboard") + self.dim(" | ") + self.accent(text) + " " * gap
                 + self.dim(right) + "  " + self.dim("│"),
                 self.dim("└" + "─" * (inner + 2) + "┘")]
        if step:
            bar = self.width - 12
            done = round(bar * (step - 1) / len(STEPS))
            pct = f"{round(100 * (step - 1) / len(STEPS)):>3}%"
            lines.append("  " + self._c("36", "█" * done) + self.dim("░" * (bar - done)) + "  " + self.dim(pct))
        return lines

    def _redraw(self):
        """The step as it was: the heading, the bar and the menu in place, then the step's last lines between them."""
        if getattr(self, "header_args", None):
            self.header = self._header(*self.header_args)  # the width may have changed
        self._page(*self.keys)
        for line in self.screen[-self._region():]:
            self._write(line + "\n")

    def popup(self, title, text):
        """Help over the step: the step is dimmed behind a box in the middle. Enter closes it (Esc then Enter too).
        Long help shows a page at a time. Plain output prints the help under the question instead."""
        if not self.fancy:
            self.note(text)
            return
        self.box(title, text.split("\n\n"), close="Enter or Esc: close help", keys=[("Enter", "Close help")])
        self._redraw()

    def box(self, title, paras, prompt=None, close="", keys=()):
        """A box over the dimmed step, as help is. paras are paragraphs to wrap, or (text,) for a line kept as it is,
        set in under itself when it wraps. A long box shows a page at a time. With prompt, the last page asks it
        inside the box and returns the answer; without, Enter closes it."""
        bw = min(62, self.width - 6)
        left, inner = (self.width - bw) // 2, bw - 4
        body = []
        for para in paras:
            if isinstance(para, tuple):
                line = para[0]
                indent = len(line) - len(line.lstrip()) + (4 if re.match(r"\s*\d+\. ", line) else 0)
                body += textwrap.wrap(line, inner, subsequent_indent=" " * indent, drop_whitespace=True) or [""]
            else:
                body += (textwrap.wrap(para, inner) if para else []) + [""]
        while body and body[-1] == "":
            body.pop()
        room = max(self.rows - 10, 4)
        pages = [body[i:i + room] for i in range(0, len(body), room)] or [[""]]
        behind = [ANSI.sub("", line) for line in self.header + self.screen[-self._region():]]
        behind += [""] * (self.rows - 2 - len(behind))
        edge = lambda text: self._c("36", text)  # noqa: E731
        answer = ""
        for n, part in enumerate(pages):
            more = n < len(pages) - 1
            foot = "Enter: more below" if more else close
            title_cut = title[:bw - 6]
            box = [edge("╭─ ") + self.accent(title_cut) + edge(" " + "─" * max(bw - 5 - len(title_cut), 0) + "╮")]
            box += [edge("│") + " " + line.ljust(inner) + " " + edge("│") for line in [""] + part + [""]]
            asking = prompt is not None and not more
            if asking:
                box.append(edge("│") + " " * (bw - 2) + edge("│"))
            if foot:
                box.append(edge("│") + " " + self.dim(foot.rjust(inner)) + " " + edge("│"))
            box.append(edge("╰" + "─" * (bw - 2) + "╯"))
            top = 3
            self._write("\033[r\033[2J")
            self._menu(list(keys) if not more else [("Enter", "More")], "")
            for row, line in enumerate(behind[:self.rows - 2], 1):
                self._write(f"\033[{row};1H" + self._c("2;90", line[:self.width]))
            for i, line in enumerate(box):
                self._write(f"\033[{top + i};{left + 1}H{line}")
            if asking:
                at = top + len(box) - (3 if foot else 2)
                self._write(f"\033[{at};{left + 3}H{self.accent('›')} {prompt}")
                answer = self._ask("")
            elif foot:
                self._write(f"\033[{top + len(box) - 2};{left + bw - 1}H")  # inside the box, after the closing words
                self._ask("")
            else:
                self._ask("")
        return answer

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
        if not self.fancy:
            self.say(text)
            return
        for i, line in enumerate(textwrap.wrap(text, self.width - 6) or [""]):
            self.say(f"  {self.warn_colour('⚠')} {line}" if i == 0 else f"    {line}")

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
        """One answer. q stops, b goes back a step, ? opens help, f sends feedback and r reports what just failed;
        anything in extra is returned as typed."""
        while True:
            shown = self._prompt(prompt)
            self.pending = shown
            answer = self._ask(shown).strip()
            low = answer.lower()
            if self._feedback_key(low):
                continue
            if self.fancy:
                self.screen.append(shown + answer)
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
            self.typed.add(answer)
            return answer

    def _feedback_key(self, low):
        """f opens feedback and r reports the problem shown; both come back to the question as it was."""
        if low == "f" or (low == "r" and self.problem):
            self.feedback(self.problem if low == "r" else None)
            return True
        return False

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
        self.part = question.strip()  # the question being asked, for feedback
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
            fits = max(min(len(options), self._region() - len(self.screen) - 4), 4)
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
            self.pending = shown
            answer = self._secret(shown)
            low = answer.strip().lower()
            self.part = question
            if self._feedback_key(low):
                continue
            if self.fancy:
                self.screen.append(shown)
            if low == "q":
                raise Stop()
            if low == "b" and self.can_back:
                raise Back()
            if answer.strip() == "?":
                self.popup("Help", HELP.get(help_key, "There is no more help for this question."))
                continue
            if keep and not answer:
                return None
            self.typed.add(answer)
            return answer

    def failed(self, line, problem):
        """Shows what failed and offers r, Report this problem, with the error filled in."""
        self.problem = problem
        self.record_error(problem)
        self.warn(line)
        self.note("Type r to report this problem.")
        if self.fancy and self.drawn:
            self.keys = self.step_keys()
            self._menu(*self.keys)

    def record_error(self, text):
        if text and text not in (self.last_error or ""):
            self.last_error = text

    # Feedback: f at any question -------------------------------------------------------------------------

    def feedback(self, problem=None):
        """Snaglist's report from the terminal: the kind, a question or two, the whole report, then how to send it.
        Then back to the step as it was. q closes it at any point."""
        screen = list(self.screen)  # the step's own lines, to draw it again exactly as it was
        try:
            self._feedback(problem)
        except Closed:
            pass
        self.screen = screen
        if self.fancy:
            self._redraw()
        else:
            self.say("Back to the set-up.")

    def _ask_box(self, title, paras, prompt, keys=(("q", "Close feedback"),)):
        """One feedback question: in a box over the step, or as plain lines."""
        if self.fancy:
            answer = self.box(title, paras, prompt=prompt, keys=keys)
        else:
            self.say("")
            for p in paras:
                if isinstance(p, tuple) or p:
                    self.say(p[0] if isinstance(p, tuple) else p)
            answer = self._ask(prompt)
        answer = answer.strip()
        if answer.lower() in ("q", "quit"):
            raise Closed()
        return answer

    def _pick(self, title, lead, options, error, default=None):
        paras, note = [lead], ""
        while True:
            lines = ([note, ""] if note else []) + paras + [(f"  {i}. {o}",) for i, o in enumerate(options, 1)]
            hint = f" [{default}]" if default else ""
            answer = self._ask_box(title, lines, f"Your choice{hint}: ") or (str(default) if default else "")
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            if answer == "" and default is None and error is None:
                return None
            note = error or f"Type a number from 1 to {len(options)}, or q to close feedback."

    def _feedback(self, problem):
        secrets = self.typed
        if problem:
            kind = KINDS[0]
            title = "Report this problem"
        else:
            kind = KINDS[self._pick("Send feedback", "What is it about? Type q to close this and go back.",
                                    [k[1] for k in KINDS], "")]
            title = f"Send feedback: {kind[1]}"
        answers = []
        for number, (label, hint, required, options) in enumerate(kind[4]):
            required = required and not problem
            if options:
                lead = f"{label}. Press Enter to skip."
                i = self._pick(title, lead, options, None if not required else "")
                if i is not None:
                    answers.append((label, options[i]))
                continue
            paras = []
            if problem and number == 0:
                paras += ["Starboard said:", (f"  {clip(redact(problem, secrets), 300)}",),
                          "The report holds this error. Add a few words if you can."]
            paras += [label + ("" if required else ". Press Enter to skip.")] + ([hint] if hint else [])
            note = ""
            while True:
                answer = self._ask_box(title, ([note] if note else []) + paras, "")
                if answer or not required:
                    break
                note = "Type a few words, or q to close feedback."
            if answer:
                answers.append((label, clip(redact(answer, secrets), 3000)))
        n, name = self.step
        if self.fancy:
            plain = "off"
        else:
            plain = "on" if self.plain_asked else "on, because the window is small or there is no terminal"
        error = redact(self.last_error or problem or "", secrets)
        report = Report(kind, answers, self.step, redact(self.part, secrets), f"{self.cols} x {self.rows} characters, "
                        f"{os.environ.get('TERM', 'no TERM')}", plain, error.strip()[-1500:])
        self._send(report)

    def _send(self, report):
        """The whole report first, then the ways to send it."""
        lead = ["This is everything the report holds. Nothing is sent until you choose how."]
        lines = [(line,) for line in report.text()]
        if self.fancy:
            self.box("The whole report", lead + lines, close="Enter: choose how to send it",
                     keys=[("Enter", "Next"), ("q", "Close feedback")])
            options, done = list(SENDS), False
            while True:
                if done:
                    options[3] = "Done: back to the set-up"
                i = self._pick("Send the report", "How do you want to send it? It opens as a new issue on "
                               "Starboard's GitHub page, sent from your own GitHub account.", options, None, 1)
                if i == 0:
                    self._show_qr(report)
                elif i == 1:
                    self._show_link(report)
                elif i == 2:
                    self._message("Saved", self._saved_words(report))
                else:
                    return
                done = True
        # Plain lines: never a QR code, which software that reads text aloud cannot read.
        self.say("")
        for line in lead + [line[0] for line in lines]:
            self.say(line)
        url, short = report.link()
        self.say("")
        self.say("To send it, open this link in a browser on any device. GitHub opens a new issue with the report "
                 "filled in, and you send it from your own GitHub account:")
        self.say(url)
        if short:
            self.say("The link holds a shorter report. Save to a file keeps the whole report.")
        if self._pick("Send feedback", "Save the report to a file too?", ["Save to a file", "Done: back to the set-up"],
                      None, 2) == 0:
            self.say(self._saved_words(report))

    def _save(self, report):
        """Saves the whole report and the link in a file in the home folder, readable only by you."""
        if report.file:
            return report.file
        stem, n = time.strftime("starboard-feedback-%Y-%m-%d-%H%M"), 1
        name = f"{stem}.md"
        while os.path.exists(os.path.join(self.save_dir, name)):
            n += 1
            name = f"{stem}-{n}.md"
        path = os.path.join(self.save_dir, name)
        report.file = "~/" + name if self.save_dir == os.path.expanduser("~") else path
        url, _ = report.link()
        body = (f"# {report.title()}\n\nTo send it, open this link in a browser:\n\n{url}\n\n"
                f"Or open a new issue on https://github.com/{REPO}/issues and paste the report below.\n\n---\n\n"
                f"{report.markdown()}\n")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        return report.file

    def _saved_words(self, report):
        try:
            where = self._save(report)
        except OSError as e:
            return f"The report could not be saved ({e})."
        return (f"Saved as {where}. It holds the whole report and the link. Copy it to another device and open the "
                "link there.")

    def _message(self, title, text):
        if self.fancy:
            self.box(title, [text], close="Enter: back", keys=[("Enter", "Back")])
        else:
            self.say(text)

    def _full_page(self, keys):
        self._write("\033[r\033[2J")
        self._menu(keys, "")
        self._write("\033[H")

    def qr_fit(self, report):
        """What goes in the code, chosen from the window's size. The code takes every line but the title line and
        the two menu lines; it keeps the standard 4-module edge when that leaves room for a useful report, and
        drops to a 2-module edge (which phones still read) in a small window, such as 80 by 24. The more the
        window holds, the more of the report goes in: the report without its technical parts, then the person's
        words cut to fit, then a sentence or two, then the title alone. Returns (address, version, edge, what it
        holds), or None when not even the title fits."""
        lines = self.rows - 3
        for edge in (qr.QUIET, 2):
            version = qr.largest_version(self.cols, lines, edge)
            if not version:
                continue
            room = min(qr.byte_capacity(version, "L"), QR_LIMIT)
            if edge == qr.QUIET and room < 180 and qr.largest_version(self.cols, lines, 2) > version:
                continue  # a smaller edge buys a code that holds a sentence, not just a title
            fuller = issue_url(report.title(), report.markdown(short=True), report.labels())
            choices = [(fuller, "the report without its technical details")]
            choices += [(report.tiny(w), "a short report") for w in (300, 200, 140, 90, 50)]
            choices += [(report.compact(w), "a short report") for w in (60, 40, 25)]
            choices += [(report.compact(0), "the step, the version and where the whole report is"),
                        (report.title_only(), "only the title")]
            for url, holds in choices:
                if len(url.encode()) <= room:
                    return url, version, edge, holds
        return None

    def _show_qr(self, report):
        """The QR code on a page of its own: a title line, the code, the link under it when there is room, the
        menu. The whole report is saved first, so the short one in the code can say where it is."""
        try:
            self._save(report)
        except OSError:
            pass
        fit = self.qr_fit(report)
        if not fit:
            self._show_link(report, "The QR code does not fit this window. Make the window larger, or use Show the "
                                    "link.")
            return
        url, version, edge, holds = fit
        code = qr.encode(url, largest=version)
        drawing = qr.draw(code, quiet=edge)
        width = qr.width_of(code.version, edge)
        left = max((self.cols - width) // 2, 0)
        scan = "Scan it with your phone's camera to open the report there."
        more = f"It holds {holds}." + (f" The whole report is in {report.file}." if report.file else "")
        beside = len(scan + more) + 1 <= self.cols
        free = self.rows - 3 - len(drawing) - (0 if beside or not more else 1)  # lines left between code and menu
        link_lines = -(-len(url) // self.cols)
        link_below = free >= link_lines + 1
        self._full_page([("Enter", "Back" if link_below else "Show the link")])
        self._write("\033[1;1H" + self.accent(scan) + (" " + self.dim(more) if beside else ""))
        for i, line in enumerate(drawing):
            self._write(f"\033[{i + 2};{left + 1}H{line}")
        below = len(drawing) + 2
        if more and not beside:
            if below <= self.rows - 2:  # only where it leaves the menu's lines alone
                self._write(f"\033[{below};1H" + self.dim(more[:self.cols]))
                below += 1
                more = ""
        else:
            more = ""
        self.qr_note = more  # said on the link's view instead, when there was no room for it here
        if link_below:
            self._write(f"\033[{below + 1};1H{url}")
        self._write(f"\033[{self.rows};{len('  Enter ' + ('Back' if link_below else 'Show the link')) + 2}H")
        self._ask("")
        if not link_below:
            self._show_link(report, getattr(self, "qr_note", "") or None)

    def _show_link(self, report, warning=None):
        """The link as one line, so the terminal can wrap it and it copies whole."""
        url, short = report.link()
        screen = list(self.screen)
        self._full_page([("Enter", "Back")])
        if warning:
            self.warn(warning)
            self._write("\n")
        self.say("  " + self.accent("The link to the report"))
        self.note("Open it in a browser on any device. GitHub opens a new issue with the report filled in, and you "
                  "send it from your own GitHub account.")
        if short:
            self.note("The link holds a shorter report. Save to a file keeps the whole report.")
        if report.file:
            self.note(f"The whole report is saved as {report.file}.")
        self._write("\n" + url + "\n")
        self.screen = screen
        self._ask("")

    def offer_report(self, message):
        """After a stop: the error, and r to report it."""
        try:
            self.can_back, self.came_back = False, False
            if self.fancy:
                self.heading("Something went wrong")
            self.problem = message
            self.record_error(message)
            if self.fancy:
                self.keys = self.step_keys()
                self._menu(*self.keys)
                self.warn(f"Stopped: {message}")
            self.note("Type r to report this problem.")
            self._read("Press Enter to finish, or type r to report this problem: ", None)
        except (Stop, Back, EOFError, KeyboardInterrupt):
            pass
        finally:
            self.finish()

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
        term.typed.add(token)  # never in a feedback report
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
                term.failed(f"Starboard said: {e}", str(e))
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
    lines = (job.get("log") or "").strip().splitlines()[-12:]
    term.warn("The apps did not all start. The last lines Docker wrote:")
    for line in lines:
        term.say(f"  {line}")
    term.last_error = "The apps did not all start. The last lines Docker wrote:\n" + "\n".join(lines)
    term.failed("Starboard cannot carry on with the apps from here.", "The apps did not all start.")
    term.text("Press Enter to carry on")
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
        except ValueError as e:
            term.say(f"That did not work: {e}. Type whole hours, such as 1 and 7.")
        except Problem as e:
            term.failed(f"That did not work: {e}. Type whole hours, such as 1 and 7.", str(e))


STEP_FUNCTIONS = [step_password, step_apps, step_vpn, step_check, step_hours]


def run(api, term, data_dir, port, address=""):
    if not term.fancy:
        term.say("\nStarboard set-up, in the terminal")
        term.note("Every question has a number or a word to type, and Enter takes the answer in [brackets]. "
                  "Type ? at any question for help, b to go back a step, f to send feedback, or q to stop. You can "
                  "carry on later in a browser instead.")
    state = {"data_dir": data_dir}
    api.on_error = term.record_error
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
                term.failed(f"Starboard said: {e}", str(e))
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
    plain = bool(args.plain or os.environ.get("STARBOARD_PLAIN"))
    term = Terminal(fancy=False if plain else None)
    term.watch_size()
    term.plain_asked = plain
    try:
        return run(Api(args.port), term, args.data, args.port, args.address)
    except Stop:
        term.say("\nStopped. Nothing else was changed. Carry on later in a browser, or run this again.")
        return 1
    except Problem as e:
        term.finish()
        term.say(f"\nStopped: {e}")
        term.offer_report(str(e))
        return 1
    except (KeyboardInterrupt, EOFError):
        term.finish()
        term.say("\nStopped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
