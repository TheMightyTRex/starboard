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
import hmac
import http.client
import json
import os
import platform
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import textwrap
import time
import urllib.parse

from starboard import qr, start

def _read_keys(fd, read=os.read, ready=None):
    """What was typed, as text. An arrow key's code can arrive in two reads (over SSH, or on a busy server): when a
    read ends part way through one, it waits a moment for the rest, so the key is not taken as Escape and letters."""
    import select
    ready = ready or (lambda: select.select([fd], [], [], 0.05)[0])
    data = read(fd, 64).decode(errors="ignore")
    while data and re.search(r"\x1b(\[[0-9;]*|O)?$", data) and ready():
        more = read(fd, 64).decode(errors="ignore")
        if not more:
            break
        data += more
    return data


def _keys(chunk):
    """Splits what one read gave into single key presses: an arrow key is one escape code, everything else one
    character."""
    return re.findall(r"\x1b(?:\[[0-9;]*[A-Za-z~]|O[A-Za-z])|\x1b|[\s\S]", chunk)


def _wrap(text, width, **kw):
    """Lines of text between words only: never at a hyphen ("open-source" stays whole) and never inside a long word,
    such as an address, which gets a line of its own."""
    return textwrap.wrap(text, width, break_on_hyphens=False, break_long_words=False, **kw)


VPNS = [  # (Gluetun's provider name, shown name)
    ("protonvpn", "Proton VPN"),
    ("airvpn", "AirVPN"),
    ("private internet access", "Private Internet Access"),
    ("surfshark", "Surfshark"),
    ("expressvpn", "ExpressVPN"),
]
# Usenet providers for SABnzbd, with affiliate links (the same list and words as USENET in web/js/common.js).
# Usenet is never shown as a way to get copyrighted films, series, music or books.
USENET = [
    ("Newshosting", "https://www.newshosting.com/?a_aid=6aec3d712dec1"),
    ("Easynews", "https://easynews.com/?a_aid=6aec3d712dec1"),
    ("UsenetServer", "https://www.usenetserver.com/?a_aid=6aec3d712dec1&a_bid=ef245116"),
    ("Pure Usenet", "https://www.pureusenet.nl/?a_aid=6aec3d712dec1&a_bid=9fa99e6a"),
    ("XLned", "https://www.xlned.com/?a_aid=6aec3d712dec1&a_bid=dbc287fb"),
]
USENET_ABOUT = ("SABnzbd needs an account with a Usenet provider. Usenet is a worldwide network of discussion groups, "
                "running since 1980, that also carries files. Any provider works with SABnzbd.")
USENET_AD = ("Ad: these are affiliate links. If you sign up through one, the provider pays a small commission towards "
             "Starboard's development. You pay the same price.")
USENET_RIGHTS_TITLE = "Download only what you have the right to"
USENET_RIGHTS = ("Use Usenet only for files you have the right to download, such as open-source software, works in the "
                 "public domain and your own backups. Downloading films, series, music or books without the copyright "
                 "holder's permission is against the law in the UK and most other countries. Starboard does not host "
                 "or provide any files, and you are responsible for what you download.")
HELP = {
    "pool": "A pool joins several drives into one folder, /mnt/pool, so your media has one place however many "
            "drives you have. Each drive stays a normal drive that can be read on its own. Keeping a drive's files "
            "puts them in the pool as they are; erasing prepares an empty drive. Nothing changes until you say yes.",
    "backup": "A backup drive is not part of the pool: it protects it. Parity (SnapRAID) needs one drive at least "
              "as big as the biggest pool drive and can rebuild any one failed drive; it is checked every night. A "
              "copy (rsync) is a full, readable copy of your media folder and needs as much space as it. Neither is "
              "a full backup on its own: keep a third copy of what matters somewhere else.",
    "balance": "Balancing moves whole series, film and book folders from fuller drives to emptier ones, so the "
               "drives fill evenly and each series stays on one drive. It runs at low priority and can be stopped.",
    "password": "Your password signs you in to Starboard from any device. Use 10 characters or more; a few unrelated "
                "words are easy to remember and hard to guess. If you forget it, run ./reset-password.sh.",
    "groups": "Each kind of media installs the apps that look after it. Watching installs Jellyfin, to play everything. "
              "Downloads installs the download apps and the sites to search. You can add more later in Starboard, "
              "Settings, Install apps.",
    "apps": "These are the apps for what you chose. Apps already running on this computer are left out.",
    "usenet-app": "Both download from Usenet through your provider's servers. NZBGet is written in C++ and uses far less "
                  "memory and processor; SABnzbd is written in Python and has more extras. Reelix works with either. "
                  "You can switch later in Starboard, Settings, Your install, and your Usenet servers come across.",
    "installs": "Basics is Starboard with Reelix Lite, Jellyfin, Audiobookshelf, subtitles, and torrent and Usenet "
                "downloads through a VPN, with NZBGet for Usenet. Full install uses the full Reelix, with YouTube and Spotify downloads, and adds "
                "disk health, watch statistics, invites, live TV, logs, FlareSolverr and Tdarr. Everything installs every "
                "app Starboard offers. Whatever you choose, an app also brings what it needs, such as Jellyfin for "
                "Jellystat. You can add or remove apps later in Starboard, Settings, Install apps.",
    "folders": "The media folder holds your films, series, books and downloads, all in one place so files move in an "
               "instant. The settings folder holds each app's own settings. Both are made for you if they are missing.",
    "vpn": "A VPN sends the torrent app's traffic through your VPN provider, so sites see its address, not yours. "
           "Gluetun connects it. WireGuard is faster; OpenVPN works with every provider. Your provider's website shows "
           "the details to type here.",
    "reelix-edition": "Reelix looks after films, series, books, audiobooks, music and radio. The other version adds "
                      "downloads straight from YouTube and Spotify, and takes about 600 MB more disk. Both keep the same "
                      "settings, so you can switch either way later in Starboard, Settings, Reelix.",
    "usenet": "SABnzbd downloads from Usenet through a provider's servers. Make an account with any provider, then type "
              "its server name, user name and password in SABnzbd's first-run wizard. " + USENET_RIGHTS,
    "hours": "Downloading uses most of your internet connection while it runs, so streaming, video calls and games on "
             "other devices can slow down. With download hours, Starboard pauses the download apps outside them and "
             "starts them again when they begin. Nothing is lost.",
    "check": "This is everything that will change. Nothing has changed yet: type b to go back and change an answer, or "
             "q to stop. The apps' files are written to Starboard's data folder, then the apps are downloaded and started.",
    "keep": "Your password is already saved. Change it later in Starboard, Settings, Security.",
    "storage": "The media folder holds your films, series, books and downloads together.",
    "extras": "Live TV builds free channel playlists and TV guides for Jellyfin once a day. Watch history brings what "
              "everyone has watched from Plex, Emby or another Jellyfin. Defaults set Jellyfin's options for users who "
              "have not chosen their own.",
    "alerts": "Starboard checks your apps every few minutes and sends an alert when one stops answering or a disk has a "
              "problem. ntfy has a free phone app: choose a long private topic name, such as https://ntfy.sh/a-long-private-name.",
    "health": "A small script reads each disk's health report (SMART) as root every 30 minutes, so Starboard can warn "
              "you before a disk fails. Setting it up needs sudo once, so it is done at the end.",
    "name": "The name is shown in the header of every page and in the browser tab, so you can tell this server "
            "from another one. Change it later in Settings, General.",
    "restore": "The backup file is the one downloaded from Starboard's System, Backup and restore, Download a copy of "
               "the settings. Type where it is, such as ~/Downloads/starboard-settings.json. It is checked before "
               "anything changes.",
    "found": "These apps are running on this computer and are not in Starboard yet. Starboard adds the ones you "
             "choose and reads their API keys where it can. Nothing in the apps changes.",
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


# A random key made for each run and kept only in memory: a fingerprint cannot be matched against a list of common
# passwords, and none is kept or sent anywhere.
_FINGERPRINT_KEY = os.urandom(32)


def fingerprint(value):
    """What the set-up keeps of an answer typed to it: its length and a keyed hash (HMAC-SHA-256 with this run's
    random key), never the answer itself. It is only used to find the answer in a feedback report and take it out."""
    return len(value), hmac.new(_FINGERPRINT_KEY, value.encode(), "sha256").hexdigest()


def redact(text, typed=()):
    """Takes out what was typed as an answer (longest first), then anything that looks private. typed holds
    fingerprints (or plain values, which are fingerprinted here): every stretch of the text the length of an answer
    is hashed and compared, so the answers themselves are never kept or searched for."""
    out = str(text or "")
    prints = {fingerprint(t) if isinstance(t, str) else t for t in typed if t}
    for size in sorted({n for n, _ in prints if n >= 4}, reverse=True):
        hashes = {h for n, h in prints if n == size}
        i = 0
        while i + size <= len(out):
            if fingerprint(out[i:i + size])[1] in hashes:
                out = out[:i] + "[your answer]" + out[i + size:]
                i += len("[your answer]")
            else:
                i += 1
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

# The agreed order (DASH-103), the same as the browser set-up: each thing is decided before what depends on it.
# The frame and text sit in a column at most this wide, centred in a wider window.
COLUMN_MAX = 100

def _step_table():
    """Each step's name and question, from web/setup-steps.json, which the browser set-up reads too."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "setup-steps.json")
    with open(path, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["steps"]}


STEP_TABLE = _step_table()


def title(step_id):
    return STEP_TABLE[step_id]["title"]


STEPS = [title(i) for i in ("password", "start", "storage", "apps", "vpn", "usenet", "check", "extras", "hours", "alerts",
                            "preset")]
POOL_HELPER = "/usr/local/bin/starboard-pool"


def num(name):
    """A step's number, from the list: Your drives is only there when the pool helper is installed."""
    return STEPS.index(name) + 1
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
        self._measure()  # again, now that it is known whether the column is centred
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
        self.typed = set()        # fingerprints of answers typed to the set-up (not hidden ones): never in a report
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
        pad = getattr(self, "pad", "") if self.fancy else ""
        print("\n".join(pad + line for line in str(text).split("\n")), file=self.out, flush=True)
        if self.fancy:
            self.screen += str(text).split("\n")

    def _show(self, render):
        """Draws render(width), a function giving the lines for a width, and keeps the function, so a change of
        window size draws the piece again wrapped to the new width instead of cutting its old lines."""
        for line in render(self.width):
            print(getattr(self, "pad", "") + line, file=self.out, flush=True)
        if self.fancy:
            self.screen.append(render)

    def _lines(self):
        """The step's lines at the width now: kept pieces are wrapped again."""
        out = []
        for item in self.screen:
            out += item(self.width) if callable(item) else [item]
        return out

    def _plain(self, text, indent=0):
        """Plain lines wrapped between words to the window's width, for a terminal with no boxes."""
        width = max(shutil.get_terminal_size((80, 24)).columns - 1, 20)
        for para in str(text).split("\n"):
            for line in _wrap(para, width, subsequent_indent=" " * indent) or [""]:
                self.say(line)

    # The screen: a cleared page per step, with the menu fixed below a scrolling area ---------------------------

    def _measure(self):
        """The window's size now: columns and lines (a test can fix them)."""
        size = shutil.get_terminal_size((80, 24))
        self.cols = self.fixed_size[0] or size.columns   # the whole window, for a QR code
        self.width = min(self.cols, COLUMN_MAX)
        self.left = (self.cols - self.width) // 2 if getattr(self, "fancy", False) else 0  # centred in a wide window
        self.pad = " " * self.left
        self.rows = self.fixed_size[1] or size.lines

    def watch_size(self):
        """Draws the step again when the window changes size, keeping the heading, the bar and the menu in place."""
        if self.fancy and hasattr(signal, "SIGWINCH") and self.fixed_size == (None, None):
            signal.signal(signal.SIGWINCH, lambda *_: self._resized())

    def _resized(self):
        self._measure()
        if self.fancy and self.drawn and self.width >= 60 and self.rows >= 20:
            self._redraw()
            self._write(getattr(self, "pad", "") + self.pending)

    def _region(self):
        """Lines between the fixed heading and the fixed menu: the only part that scrolls."""
        return max(self.rows - 2 - len(self.header), 3)

    def _menu(self, keys, right=""):
        """The two bottom lines: a rule, then the keys. Drawn outside the scrolling area, so they stay put."""
        line = "   ".join(f"{self.accent(k)} {label}" for k, label in keys)
        plain = "   ".join(f"{k} {label}" for k, label in keys)
        if self.width - 4 - len(plain) - len(right) < 3:
            right = ""  # a narrow window: the keys matter more than the hint
        gap = max(self.width - 4 - len(plain) - len(right), 1)
        col = getattr(self, "left", 0) + 1
        self._write(f"\0337\033[{self.rows - 1};1H\033[2K\033[{self.rows - 1};{col}H{self.dim('─' * self.width)}"
                    f"\033[{self.rows};1H\033[2K\033[{self.rows};{col}H  {line}{' ' * gap}{self.dim(right)}\0338")

    def _page(self, keys, right):
        """Clears the screen and draws the step's heading box and progress bar at the top and the menu on the last
        two lines. Only the lines between them scroll, so the heading, the bar and the menu are always in view."""
        top = len(self.header) + 1
        self._write(f"\033[r\033[2J")
        for i, line in enumerate(self.header, 1):
            self._write(f"\033[{i};{getattr(self, 'left', 0) + 1}H{line}")
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
                self._plain("You came back to this step. Your last answers are in [brackets]: press Enter to keep each one.")
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
        for line in self._lines()[-self._region():]:
            self._write(getattr(self, "pad", "") + line + "\n")

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
        left, inner = getattr(self, "left", 0) + (self.width - bw) // 2, bw - 4
        body = []
        for para in paras:
            if isinstance(para, tuple):
                line = para[0]
                indent = len(line) - len(line.lstrip()) + (4 if re.match(r"\s*\d+\. ", line) else 0)
                body += _wrap(line, inner, subsequent_indent=" " * indent, drop_whitespace=True) or [""]
            else:
                body += (_wrap(para, inner) if para else []) + [""]
        while body and body[-1] == "":
            body.pop()
        room = max(self.rows - 10, 4)
        pages = [body[i:i + room] for i in range(0, len(body), room)] or [[""]]
        behind = [ANSI.sub("", line) for line in self.header + self._lines()[-self._region():]]
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
                self._write(f"\033[{row};{getattr(self, 'left', 0) + 1}H" + self._c("2;90", line[:self.width]))
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
                self._plain(f"{label}: {value}", indent=2)
            return

        def render(width):
            label_w = min(max(len(label) for label, _ in rows) + 2, max(width // 3, 8))
            inner = width - 4
            top = f"─ {title} "
            out = ["", self._c(colour, "╭" + top + "─" * max(inner + 2 - len(top), 0) + "╮")]
            for label, value in rows:
                lines = _wrap(str(value), inner - label_w) or [""]
                for i, line in enumerate(lines):
                    left = (label[:label_w - 1] if i == 0 else "").ljust(label_w)
                    out.append(self._c(colour, "│") + " " + self.dim(left) + line.ljust(inner - label_w) + " " + self._c(colour, "│"))
            out.append(self._c(colour, "╰" + "─" * (inner + 2) + "╯"))
            return out
        self._show(render)

    def ok(self, text):
        if not self.fancy:
            self._plain(text)
            return
        self._show(lambda width: [(f"  {self.good('✔')} " if i == 0 else "    ") + line
                                  for i, line in enumerate(_wrap(text, width - 6) or [""])])

    def warn(self, text):
        if not self.fancy:
            self._plain(text)
            return
        self._show(lambda width: [(f"  {self.warn_colour('⚠')} " if i == 0 else "    ") + line
                                  for i, line in enumerate(_wrap(text, width - 6) or [""])])

    def note(self, text):
        """A paragraph, wrapped to the width and set in from the box."""
        if not self.fancy:
            self._plain(text)
            return
        self._show(lambda width: [f"  {line}" for line in _wrap(text, width - 4)])

    # Questions ----------------------------------------------------------------------------------------------

    def _prompt(self, text):
        """The question before the cursor. In the boxed look, a question longer than the window is wrapped at spaces:
        its first lines are written above, so the line the answer is typed on fits."""
        if not self.fancy:
            return text
        room = max(self.width - 6, 20)
        if len(text) <= room:
            return f"  {self.accent('›')} {text}"
        lines = _wrap(text, room)
        self.say(f"  {self.accent('›')} {lines[0]}")
        for line in lines[1:-1]:
            self.say(f"    {line}")
        return f"    {lines[-1]}" + (" " if text.endswith(" ") else "")

    def _read(self, prompt, help_key, title="Help", extra=()):
        """One answer. q stops, b goes back a step, ? opens help, f sends feedback and r reports what just failed;
        anything in extra is returned as typed."""
        while True:
            shown = self._prompt(prompt)
            self.pending = shown
            answer = self._ask((getattr(self, "pad", "") if self.fancy else "") + shown).strip()
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
            if not re.fullmatch(r"[\d,\s]*|[ynq?bfmr]", answer.strip().lower()):  # menu numbers and keys are not private
                self.typed.add(fingerprint(answer))
            return answer

    def _feedback_key(self, low):
        """f opens feedback and r reports the problem shown; both come back to the question as it was."""
        if low == "f" or (low == "r" and self.problem):
            self.feedback(self.problem if low == "r" else None)
            return True
        return False

    def _options(self, options, defaults, start=0):
        """Options are text, or (name, about) pairs: in two columns when the names are short, otherwise the name on
        its line and the about under it. Each wraps inside the width, again whenever the window changes size."""
        names = [o[0] for o in options if isinstance(o, tuple)]
        for i, o in enumerate(options, 1):
            if i <= start:
                continue
            if not self.fancy:
                self._plain(f"  {i}. " + (f"{o[0]}: {o[1]}" if isinstance(o, tuple) else o), indent=5)
                continue
            mark = self.accent("●") if i - 1 in defaults else " "
            self._show(lambda width, o=o, i=i, mark=mark: self._option_lines(o, i, mark, names, width))

    def _option_lines(self, o, i, mark, names, width):
        name_w = max((len(n) for n in names), default=0) + 2
        green = lambda s: re.sub(r"\(recommended[^)]*\)|\(your last answer\)", lambda m: self.good(m.group(0)), s)  # noqa: E731
        lead = f"  {mark} {self.accent(str(i).rjust(2))}  "
        if isinstance(o, tuple) and name_w <= min(30, width // 3):  # two columns: the about wraps under itself
            about = _wrap(o[1], width - 8 - name_w) or [""]
            return [lead + green(o[0].ljust(name_w)) + self.dim(about[0])] + [" " * (8 + name_w) + self.dim(m) for m in about[1:]]
        if isinstance(o, tuple):  # long names: the name on its line, the about wrapped under it
            name = _wrap(o[0], width - 8) or [""]
            return ([lead + green(name[0])] + [" " * 8 + green(m) for m in name[1:]]
                    + [" " * 8 + self.dim(m) for m in _wrap(o[1], width - 10)])
        lines = _wrap(o, width - 8) or [""]
        return [lead + green(lines[0])] + [" " * 8 + green(m) for m in lines[1:]]

    def _title(self, question):
        self.part = question.strip()  # the question being asked, for feedback
        return question.rstrip("?").rstrip(".")[:40].lower()

    def choose(self, question, options, default=1, help_key=None):
        """Numbered options; returns the index (0-based)."""
        self.say("")
        self.note(question)
        self._options(options, {default - 1})
        while True:
            answer = self._read(f"Your choice [{default}]: ", help_key, self._title(question)) or str(default)
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            self.say(f"Type a number from 1 to {len(options)}, ? for help or q to stop.")

    def _keys_work(self):
        """Arrow keys and Space can be read one at a time: the boxed way, in a real terminal (not plain mode, which
        stays numbered for software that reads text aloud, and not a test's answers)."""
        try:
            return self.fancy and self._ask is input and sys.stdin.isatty() and sys.stdout.isatty()
        except (AttributeError, ValueError):
            return False

    def choose_many(self, question, options, defaults, help_key=None, allow_none=False):
        """Numbered options, several at once (1,3,4); returns the indexes chosen. A long list on a short screen
        shows what fits, and m shows the rest. With allow_none, 0 (or Enter when none is ticked) chooses none.
        In a real terminal with the boxed look, the arrow keys move and Space ticks (_pick_many)."""
        if self._keys_work() and len(options) + 6 <= self._region():
            return self._pick_many(question, options, defaults, help_key, allow_none)
        self.say("")
        self.note(f"{question} Type the numbers, separated by commas" + (", or 0 for none." if allow_none else "."))
        fits = len(options)
        if self.fancy:
            fits = max(min(len(options), self._region() - len(self._lines()) - 4), 4)
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
            if allow_none and answer in ("", "0"):
                return []
            parts = [p.strip() for p in answer.replace(" ", ",").split(",") if p.strip()]
            if parts and all(p.isdigit() and 1 <= int(p) <= len(options) for p in parts):
                return sorted({int(p) - 1 for p in parts})
            self.say(f"Type numbers from 1 to {len(options)}, such as 1,2, or ? for help, or q to stop.")

    def _pick_many(self, question, options, defaults, help_key, allow_none):
        """Up and Down move, Space ticks or unticks, Enter carries on. A number ticks that line too. ? opens help,
        b goes back and q stops, as everywhere. The list is drawn in place, so it never repeats down the window."""
        import termios
        import tty
        ticked, at = set(defaults), 0
        note = ["Up and Down move, Space ticks or unticks, Enter carries on."]

        def render(width):
            out = []
            green = lambda s: re.sub(r"\(recommended[^)]*\)", lambda m: self.good(m.group(0)), s)  # noqa: E731
            for i, o in enumerate(options):
                name, about = o if isinstance(o, tuple) else (o, "")
                mark = self.good("[x]") if i in ticked else "[ ]"
                cursor = self.accent("›") if i == at else " "
                first = _wrap(name, width - 10) or [""]
                out.append(f"  {cursor} {mark} {green(first[0])}")
                out += [" " * 8 + green(more) for more in first[1:]]
                out += [" " * 8 + self.dim(more) for more in _wrap(about, width - 10)]
            out += ["", "  " + self.dim(note[0])]
            return out

        self.say("")
        self.note(question)
        self.say("")
        self._show(render)
        self.pending = ""

        def draw():
            # Back to the list's first line and over it. Counted at the width now, so a change of window size
            # (which draws the step again, the list last) does not throw it off.
            lines = render(self.width)
            self._write(f"\033[{len(lines)}A\r")
            for line in lines:
                self._write("\033[2K" + getattr(self, "pad", "") + line + "\n")

        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            queue = []
            while True:
                # Keys typed quickly, or sent together over SSH, arrive in one read: take them one at a time.
                if not queue:
                    queue = _keys(_read_keys(fd))
                    if not queue:
                        continue
                key = queue.pop(0)
                if key in ("\x1b[A", "\x1bOA", "k"):
                    at = (at - 1) % len(options)
                elif key in ("\x1b[B", "\x1bOB", "j"):
                    at = (at + 1) % len(options)
                elif key == " ":
                    ticked ^= {at}
                elif key.isdigit() and 1 <= int(key) <= len(options):
                    at = int(key) - 1
                    ticked ^= {at}
                elif key in ("\r", "\n"):
                    if ticked or allow_none:
                        return sorted(ticked)
                    note[0] = "Tick at least one with Space, then press Enter."
                elif key.lower() == "q":
                    raise Stop()
                elif key.lower() == "b":
                    if self.can_back:
                        raise Back()
                    note[0] = "This is the first step, so there is nothing to go back to."
                elif key == "?":
                    termios.tcsetattr(fd, termios.TCSADRAIN, saved)
                    self.popup(f"Help: {self._title(question)}", HELP.get(help_key, "There is no more help for this question."))
                    tty.setcbreak(fd)
                    continue  # the help drew the step again, with the list last
                draw()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)

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
            answer = self._secret((getattr(self, "pad", "") if self.fancy else "") + shown)
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
            # Not remembered at all: a hidden answer is never shown and never goes into a feedback report. If one is
            # pasted into feedback, only the report's general checks (such as "password=...") can take it out.
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
        self.note("To send it, open this link in a browser on any device. GitHub opens a new issue with the report "
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
        """Shows a turning mark and the time taken until check() returns something, then returns it. Keys pressed
        meanwhile are not shown and are thrown away, so Enter does not push the line down the window."""
        quiet = self._quiet_keys()
        try:
            return self._waiting(text, check, wait)
        finally:
            quiet()

    def _quiet_keys(self):
        """Stops the terminal showing keys; returns how to put it back (after throwing away what was typed)."""
        try:
            import termios
            fd = sys.stdin.fileno()
            if not (self.fancy and self._ask is input and os.isatty(fd)):
                return lambda: None
            saved = termios.tcgetattr(fd)
            quiet = termios.tcgetattr(fd)
            quiet[3] &= ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSADRAIN, quiet)
        except (ImportError, OSError, ValueError, AttributeError):
            return lambda: None

        def back():
            try:
                termios.tcflush(fd, termios.TCIFLUSH)
                termios.tcsetattr(fd, termios.TCSADRAIN, saved)
            except OSError:
                pass
        return back

    def _waiting(self, text, check, wait):
        began, turn = time.time(), 0
        while True:
            result = check()
            if result is not None:
                if self.fancy:
                    self._write("\r\033[2K")
                return result
            if self.fancy:
                secs = int(time.time() - began)
                timer = f"{secs // 60} min {secs % 60:02d} s"
                words = text[:max(self.width - len(timer) - 7, 10)]  # one line, never wrapped onto a second
                self._write(f"\r\033[2K{getattr(self, 'pad', '')}  {self.accent('◐◓◑◒'[turn % 4])} {words} {self.dim(timer)}")
                turn += 1
            time.sleep(wait)


# The steps. Each takes what was answered before (state), so going back shows the last answers as the defaults.

def read_setup_code(path):
    """The setup code from Starboard's file, or "": a regular file only (never through a link, which could point at
    a secret elsewhere on this computer), at most 64 bytes, and only the characters a code has."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return ""
    with os.fdopen(fd, "rb") as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            return ""
        code = f.read(65).decode("ascii", "replace").strip()
    return code if re.fullmatch(r"[A-Za-z0-9_-]{8,64}", code) else ""


def step_password(api, term, state):
    if state.get("password"):
        term.heading(title("password"), num(title("password")))
        term.ok("Your password is saved.")
        term.note("Change it later in Starboard, Settings, Security.")
        term.text("Press Enter to carry on", help_key="keep")
        return True
    token = read_setup_code(os.path.join(state["data_dir"], "setup-token"))
    if token:
        term.typed.add(fingerprint(token))  # never in a feedback report
        term.heading(title("password"), num(title("password")))
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
            name = term.text("Name your dashboard, shown in the header", state.get("site_name", "Starboard"),
                             help_key="name").strip()[:60] or "Starboard"
            state["site_name"] = name
            try:
                api.call("POST", "/api/setup", {"token": token, "password": first, "site_name": name})
            except Problem as e:
                term.failed(f"Starboard said: {e}", str(e))
                continue
            term.ok("Password saved. You are signed in.")
            state["password"] = first
            return True
    term.heading("Sign in", num(title("password")))
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


def step_start(api, term, state):
    """How to start: the same question, answers and help as the browser's set-up guide (starboard/start.py)."""
    found = api.call("GET", "/api/setup/start")
    choices = found["choices"]
    HELP["start"] = "\n\n".join(f"{c['title']}: {c['help']}" for c in choices)
    term.heading(title("start"), num(title("start")))
    if found["found"]:
        term.note("Found on this computer: " + ", ".join(found["found"]) + ".")
    keys = [c["key"] for c in choices]
    default = keys.index(state.get("start", found["recommended"])) + 1
    picked = term.choose("How do you want to start?",
                         [(c["title"] + (" (recommended)" if c["recommended"] else ""), c["about"]) for c in choices],
                         default, help_key="start")
    state["start"] = keys[picked]
    if state["start"] == "restore":
        return restore_backup(api, term, state)
    if state["start"] == "move":
        return add_found_apps(api, term, state)
    return True


def restore_backup(api, term, state):
    """Restore a backup: a settings file, checked by Starboard, restored through its API."""
    guess = ""
    for folder in ("~/Downloads", "~"):
        try:
            names = sorted((n for n in os.listdir(os.path.expanduser(folder)) if n.startswith("starboard") and n.endswith(".json")),
                           key=lambda n: os.path.getmtime(os.path.join(os.path.expanduser(folder), n)), reverse=True)
        except OSError:
            names = []
        if names:
            guess = os.path.join(folder, names[0])
            break
    while True:
        path = os.path.expanduser(term.text("The backup file", state.get("backup_file", guess), help_key="restore"))
        try:
            with open(path, encoding="utf-8") as f:
                backup = json.load(f)
        except (OSError, ValueError) as e:
            term.failed(f"That file could not be read: {e}. Type where the backup file is.", str(e))
            continue
        try:
            done = api.call("POST", "/api/backup/restore", {"backup": backup, "password": state["password"]})
        except Problem as e:
            term.failed(f"Starboard did not restore it: {e}", str(e))
            continue
        state["backup_file"] = path
        term.ok(f"Restored: {done['apps']} apps, with your categories, design and alerts.")
        return True


def add_found_apps(api, term, state):
    """Move from apps you already run: the apps found on this computer, added to Starboard."""
    items = api.call("GET", "/api/discover").get("items", [])
    if not items:
        term.note("No apps were found on this computer that are not in Starboard already. Add them later in "
                 "Starboard, Settings, Manage apps, Search for new apps.")
        term.text("Press Enter to carry on")
        return True
    picked = term.choose_many("Add these apps to Starboard?", [(i["name"], i.get("url", "")) for i in items],
                              state.get("found_picked", list(range(len(items)))), help_key="found")
    state["found_picked"] = picked
    if picked:
        added = api.call("POST", "/api/discover/add", {"items": [items[i] for i in picked]})
        term.ok(f"Added {len(picked)} {'app' if len(picked) == 1 else 'apps'}.")
        if added.get("missing_keys"):
            term.note("Still without an API key: " + ", ".join(added["missing_keys"]) + ". Add them in Starboard, "
                      "Settings, Manage apps.")
    return True


def step_storage(api, term, state):
    """Storage: this computer's main disk, a separate disk or a pool. Only for a new install: moving keeps the apps'
    folders, and a restore brings its own."""
    if state.get("start", "new") != "new":
        return False
    found = api.call("GET", "/api/setup/storage")
    choices = found["choices"]
    HELP["storage"] = found["help"]
    term.heading(title("storage"), num(title("storage")))
    term.note("Where your films, series, books and downloads go. The folder is made for you when the apps start.")
    keys = [c["key"] for c in choices]
    last = state.get("storage", {})
    default = keys.index(last.get("key", found["recommended"])) + 1 if last.get("key", found["recommended"]) in keys else 1
    while True:
        picked = choices[term.choose("Where should your media go?",
                                     [(c["title"] + (" (recommended)" if c["recommended"] else ""), c["about"]) for c in choices],
                                     default, help_key="storage")]
        if picked["key"] == "pool" and not picked.get("ready"):
            term.warn("The pool helper is not set up yet. Choose another place for now; make the pool later with "
                      "./install.sh and Drive pools, then System, Storage, Pool.")
            continue
        break
    folder = term.text("Media folder", last.get("folder") if last.get("key") == picked["key"] else picked["folder"],
                       help_key="storage")
    state["storage"] = {"key": picked["key"], "folder": folder}
    state["media_dir"] = folder
    state.setdefault("host", {})["disk"] = f"Media={folder}"  # free space on System, Storage: applied at the end
    term.ok(f"Media folder: {folder}")
    return True


def step_apps(api, term, state):
    """Sets state["choice"] (the Install apps choice) and state["names"], or None to install nothing."""
    if state.get("start", "new") != "new":
        state["choice"] = None  # moving or restoring: the apps are there already
        return False
    overview = state.get("overview") or api.call("GET", "/api/stack")
    state["overview"] = overview
    groups = overview["groups"]
    term.heading(title("apps"), num(title("apps")))
    last = state.get("apps", {})
    if term.choose("Install the apps for your media server now?",
                   ["Yes (recommended)", "No: I have my apps already, or I will add them later in the browser"],
                   last.get("install", 1), help_key="groups") == 1:
        last["install"], state["apps"], state["choice"] = 2, last, None
        return True
    last["install"] = 1
    # Basics, Full install or Everything (the browser set-up asks the same), or the groups one by one.
    installs = overview.get("installs") or []
    if installs:
        options = [(i["name"] + (" (recommended)" if i["recommended"] else ""), i["about"]) for i in installs]
        options.append(("Let me choose", "Pick each group, and each app if you like."))
        pick = term.choose("What do you want to install?", options, last.get("which", 1), help_key="installs")
        last["which"] = pick + 1
        if pick < len(installs):
            usenet = "nzbget"
            if installs[pick].get("usenet_choice"):
                u = term.choose("Which app downloads from Usenet?",
                                [("NZBGet (recommended)", "Light on memory and processor."),
                                 ("SABnzbd", "If you know it already, or want its own extras.")],
                                last.get("usenet", 1), help_key="usenet-app")
                last["usenet"] = u + 1
                usenet = ("nzbget", "sabnzbd")[u]
            c = api.call("POST", "/api/stack/install", {"install": installs[pick]["key"], "usenet": usenet})
            names = {a["key"]: a["name"] for a in overview["apps"]}
            rows = [("Apps", ", ".join(names.get(k, k) for k in c["apps"])), ("Memory", f"about {c['memory']:,} MB")]
            if c.get("note"):
                rows.append(("Reelix", c["note"]))
            term.card(c["name"], rows)
            if term.choose("Install these?", ["Yes (recommended)", "Let me choose app by app"], help_key="apps") == 0:
                state.setdefault("host", {}).setdefault("health", bool(c["disk_health"]))
                d = overview["defaults"]
                data_dir = state.get("media_dir") or (state["pool_dir"] + "/media" if state.get("pool_dir") else d["data_dir"])
                config_dir = last.get("config_dir", d["config_dir"])
                last.update(data_dir=data_dir, config_dir=config_dir, chosen=c["apps"], groups=None)
                state["apps"] = last
                state["choice"] = {"apps": c["apps"], "groups": c["groups"], "data_dir": data_dir, "config_dir": config_dir,
                                   "puid": d["puid"], "pgid": d["pgid"], "tz": d["tz"], "reelix_edition": c["reelix_edition"]}
                state["names"] = [names.get(k, k) for k in c["apps"]]
                return True
            last["chosen"] = c["apps"]
    picked = term.choose_many("What do you want?", [(g["name"], g["about"]) for g in groups],
                              last.get("groups") or [i for i, g in enumerate(groups) if g["default"]], help_key="groups")
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
    edition = "lite"
    if any(a["key"] == "reelix" for a in chosen):
        edition = ask_reelix_edition(api, term, last)
    d = overview["defaults"]
    data_dir = state.get("media_dir") or (state["pool_dir"] + "/media" if state.get("pool_dir") else d["data_dir"])
    config_dir = last.get("config_dir", d["config_dir"])  # shown in the check, where b changes it
    last.update(data_dir=data_dir, config_dir=config_dir)
    state["apps"] = last
    state["choice"] = {"apps": [a["key"] for a in chosen], "groups": sorted(keys), "data_dir": data_dir, "config_dir": config_dir,
                       "puid": d["puid"], "pgid": d["pgid"], "tz": d["tz"], "reelix_edition": edition}
    state["names"] = [a["name"] for a in chosen]
    return True


def ask_reelix_edition(api, term, last):
    """Reelix, or Reelix with YouTube and Spotify downloads (the browser set-up asks the same). Reelix comes first: it
    is the recommended one. The other is offered only when it can be downloaded now."""
    try:
        editions = api.call("GET", "/api/reelix/editions").get("editions", [])
    except Exception:  # noqa: BLE001  Reelix it is, as before
        return "lite"
    offered = [e for e in editions if e["available"]]
    if len(offered) < 2:
        return "lite"
    offered.sort(key=lambda e: not e["recommended"])
    options = [(e["name"] + (" (recommended)" if e["recommended"] else ""), e["about"]) for e in offered]
    keys = [e["key"] for e in offered]
    was = last.get("reelix_edition", "lite")
    pick = term.choose("Which Reelix?", options, keys.index(was) + 1 if was in keys else 1, help_key="reelix-edition")
    last["reelix_edition"] = keys[pick]
    return keys[pick]


def step_vpn(api, term, state):
    choice = state.get("choice")
    if not choice or "gluetun" not in choice["apps"]:
        return False
    last = state.get("vpn_answers", {})
    term.heading(title("vpn"), num(title("vpn")))
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


def step_usenet(api, term, state):
    """Your Usenet provider: only when SABnzbd is chosen. The providers' addresses in full (a terminal shows the link
    itself), the affiliate note before them and what Usenet may be used for after them."""
    choice = state.get("choice")
    if not choice or not ({"sabnzbd", "nzbget"} & set(choice["apps"])):
        return False
    term.heading(title("usenet"), num(title("usenet")))
    term.say("")
    term.note(USENET_ABOUT)
    term.say("")
    term.note(USENET_AD)
    term.say("")
    # One bullet each, the name then the whole address on its own line, so a long address is never cut.
    bullet = "•" if term.fancy else "-"
    for name, url in USENET:
        term.say(f"  {bullet} {name}")
        term.say(f"    {term.accent(url)}")
        term.say("")
    term.note(term.accent(USENET_RIGHTS_TITLE))
    term.note(USENET_RIGHTS)
    term.say("")
    term.text("Press Enter to carry on", help_key="usenet")
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
    term.heading(title("check"), num(title("check")))
    names = state.get("names") or choice["apps"]
    rows = [("Install", ", ".join(names)), ("Media folder", choice["data_dir"]), ("Settings folder", choice["config_dir"])]
    if "reelix" in choice["apps"] and choice.get("reelix_edition") == "full":
        rows.append(("Reelix", "With YouTube and Spotify downloads"))
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
        raise GoTo(STEP_FUNCTIONS.index(step_vpn if any(w in low for w in ("vpn", "wireguard", "openvpn")) else step_apps), str(e)) from e
    term.card("What will change", rows)
    for line in preview.get("moved", []):
        term.warn(line)
    term.say("")
    term.note("Nothing has changed yet. Type b to go back and change an answer.")
    if not term.yes_no("Write the apps' files now?", True, help_key="check"):
        term.say("Nothing written.")
        return True
    written = api.call("POST", "/api/stack/write", {**choice, "password": state.get("password", "")})
    state["written"] = True
    term.ok(f"{len(choice['apps'])} apps written.")
    if not written.get("can_start"):
        if os.environ.get("STARBOARD_STARTS_APPS") == "1":
            # Run by the installer, which can use Docker: it downloads and starts them (./install.sh --start-apps).
            return start_with_installer(api, term, state, choice, wait)
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


def set_up_reelix(api, term, state, wait):
    """Reelix's admin account (with Starboard's password), Starboard's manager key, its library folders, qBittorrent and
    its place on the dashboard: Starboard does it over Reelix's API (reelix_setup), while the turning mark shows."""
    import threading
    result = {}

    def work():
        try:
            result["done"] = api.call("POST", "/api/reelix/setup", {"password": state["password"]}, timeout=300).get("done", [])
        except Problem as e:
            result["problem"] = str(e)
    job = threading.Thread(target=work, daemon=True)
    job.start()
    term.waiting("Setting up Reelix ...", lambda: True if not job.is_alive() else None, wait)
    if "problem" in result:
        term.warn(f"Reelix is not set up yet: {result['problem']}")
        term.note("Starboard tries again when you run ./install.sh --start-apps. Reelix's own pages also work: sign in "
                  "as admin with your Starboard password.")
        return
    for line in result.get("done", []):
        term.ok(line)
    term.note("Reelix's own pages are there if you need them: sign in as admin with your Starboard password.")


def found_when_settled(api, term, wait, expected, most=120):
    """The apps Starboard finds on this computer, once the apps just started have answered: each opens its port a
    while after it starts (Radarr and Sonarr can take over a minute). It looks again until every one it can
    recognise is there, or after most seconds, and then takes what it has."""
    began = time.time()

    def settled():
        found = api.call("GET", "/api/discover")
        items = found.get("items", [])
        waiting_for = set(expected) & set(found.get("known", [])) - {i["key"] for i in items}
        return items if not waiting_for or time.time() - began >= most else None
    return term.waiting("Waiting for the apps to answer, to add them to Starboard ...", settled, max(wait, 0.01) * 2.5)


def start_with_installer(api, term, state, choice, wait, asked=False):
    """Starboard has no Docker access: ./install.sh --start-apps downloads and starts the apps, while the step shows
    a turning mark and the time. Then the apps it finds are added to Starboard, so the dashboard shows them."""
    if not asked and not term.yes_no("Start the apps now? They are downloaded first, which can take a few minutes.", True):
        term.say("Start them later from the Starboard folder with:  ./install.sh --start-apps")
        return True
    import subprocess
    import tempfile
    folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as log:
        job = subprocess.Popen([os.path.join(folder, "install.sh"), "--start-apps"], cwd=folder, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=subprocess.STDOUT)
        code = term.waiting("Downloading and starting the apps ...", job.poll, wait)
        log.seek(0)
        lines = [line.rstrip() for line in log.read().splitlines() if line.strip() and not line.startswith("==")]
    if code == 0:
        term.ok(lines[-1] if lines else f"All {len(choice['apps'])} apps are running.")
    else:
        term.warn("The apps did not all start. The last lines Docker wrote:")
        for line in lines[-8:]:
            # Docker's lines can hold long addresses with no spaces: cut those too, so nothing passes the edge.
            for part in textwrap.wrap(line, max(term.width - 8, 20), break_on_hyphens=False) or [""]:
                term.say(f"    {part}")
        term.last_error = "The apps did not all start.\n" + "\n".join(lines[-12:])
        term.failed("Some apps did not start.", "The apps did not all start.")
        again = term.choose("What do you want to do?", ["Try again (recommended)", "Carry on without them: start them "
                            "later with ./install.sh --start-apps"], 1, help_key="apps")
        if again == 0:
            return start_with_installer(api, term, state, choice, wait, asked=True)
        if not any(not line.startswith("0 of") for line in lines if " of " in line and "apps are running" in line):
            term.text("Press Enter to carry on")
            return True
    if "reelix" in choice["apps"]:
        set_up_reelix(api, term, state, wait)
    try:
        items = found_when_settled(api, term, wait, choice["apps"])
        if items:
            added = api.call("POST", "/api/discover/add", {"items": items})
            term.ok(f"Added {len(items)} {'app' if len(items) == 1 else 'apps'} to Starboard.")
            if added.get("missing_keys"):
                term.note("Still without an API key: " + ", ".join(added["missing_keys"]) + ". Add them in Starboard, "
                          "Settings, Manage apps.")
        # Apps that have not answered yet: Starboard adds them itself as they do, for up to 30 minutes.
        later = api.call("POST", "/api/stack/adopt", {}).get("keys", [])
        if later:
            term.note(f"{len(later)} more {'app is' if len(later) == 1 else 'apps are'} still starting. Starboard adds "
                      "them to your apps as they answer.")
    except Problem as e:
        term.warn(f"The apps could not be added to Starboard: {e}. Add them in Settings, Manage apps, Search for new apps.")
    term.text("Press Enter to carry on")
    return True


def step_hours(api, term, state):
    if state.get("start") == "restore":
        return False  # the backup brought its own download hours
    last = state.get("hours", {})
    term.heading(title("hours"), num(title("hours")))
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


def pool_command(args):
    """The pool helper, through sudo: sudo asks for the computer's password itself, so Starboard never sees it."""
    p = subprocess.run(["sudo", POOL_HELPER, "--json", *args], stdout=subprocess.PIPE, text=True)
    try:
        data = json.loads(p.stdout or "{}")
    except ValueError:
        raise Problem("the pool helper did not answer") from None
    if isinstance(data, dict) and data.get("error"):
        raise Problem(data["error"])
    if p.returncode not in (0, 1):
        raise Problem("sudo did not run the pool helper")
    return data


def _size(n):
    from .pool_helper import human
    return human(n)


def step_drives(api, term, state):
    """Your drives (DASH-87): make a pool from the drives, keep or erase each, and choose a backup drive. Only shown
    when the pool helper is installed. Every change is planned and checked by the helper, then done with sudo."""
    run = state.get("pool_run") or pool_command
    if state.get("storage", {}).get("key", "pool") != "pool":
        return False
    term.heading(title("drives"), num(title("drives")))
    try:
        listing = run(["drives"])
    except Problem as e:
        term.warn(f"The pool helper did not answer ({e}). Make the pool later on System, Storage, Pool.")
        return True
    pool = [d for d in listing if d["use"] == "pool"]
    free = [d for d in listing if d["use"] == "free"]
    if pool:
        state["pool_dir"] = "/mnt/pool"
        term.ok(f"The pool is at /mnt/pool, with {len(pool)} drives.")
    if not free:
        term.note("There is no other drive to add. Add drives later on System, Storage, Pool.")
        return True
    name = lambda d: f"{d['model'] or d['name']} {_size(d['size'])}, serial ends {d['ends'] or 'unknown'}"  # noqa: E731
    term.note(f"Starboard found {len(free)} drives besides the system drive and any drive in use. A pool joins "
              "drives into one folder for your media; each drive stays readable on its own. Type ? for help.")
    if term.choose("Make a pool from your drives now?" if not pool else "Add drives to the pool now?",
                   ["Yes (recommended)", "No: later, on System, Storage, Pool"], help_key="pool") == 1:
        return True
    biggest_empty = max((d for d in free if not d.get("files")), key=lambda d: d["size"], default=None)
    spare = biggest_empty if len(free) >= 3 and not pool else None
    picked = term.choose_many("Which drives make the pool?",
                              [(name(d), f"{_size(d['files'])} of files" if d.get("files") else "empty") for d in free],
                              [i for i, d in enumerate(free) if d is not spare], help_key="pool")
    chosen = [free[i] for i in picked]
    keep = {d["by_id"]: term.yes_no(f"Keep the files on {name(d)}?", True, help_key="pool") if d.get("files") else False
            for d in chosen}
    rest = [d for d in free if d not in chosen]
    biggest = max([d["size"] for d in chosen + pool] or [0])
    backup = None
    if rest:
        options = [(f"Parity on {name(d)}", "one drive protects the whole pool") for d in rest if d["size"] >= biggest]
        parity_ok = [d for d in rest if d["size"] >= biggest]
        options += [(f"Copy on {name(d)}", "a full copy of your media folder") for d in rest]
        options.append(("No backup drive", "add one later on System, Storage, Pool"))
        pick = term.choose("Use one of the other drives as a backup drive?", options, 1, help_key="backup")
        if pick < len(parity_ok):
            backup = ("parity", parity_ok[pick])
        elif pick < len(options) - 1:
            backup = ("copy", rest[pick - len(parity_ok)])
    erase = [d for d in chosen if not keep[d["by_id"]]] + ([backup[1]] if backup and (backup[0] == "parity" or not backup[1].get("files")) else [])
    rows = [("Pool", "/mnt/pool from " + ", ".join(d["model"] or d["name"] for d in chosen + pool))]
    rows += [("Keep", name(d) + ": files stay as they are") for d in chosen if keep[d["by_id"]]]
    rows += [("Erase", name(d) + ", then ext4") for d in erase]
    if backup:
        rows.append(("Parity" if backup[0] == "parity" else "Copy", name(backup[1]) + ", checked every night at 02:00"))
    rows.append(("Saved first", "/etc/fstab, in /var/lib/starboard-pool/saved"))
    term.card("Check before anything changes", rows)
    term.note("Nothing has changed yet. The pool helper checks each drive again just before it changes it.")
    confirm = {}
    if erase:
        term.warn(f"This erases {len(erase)} drive{'s' if len(erase) > 1 else ''}. To confirm, type the end of each serial number.")
        for d in erase:
            while True:
                typed = term.text(f"Last 4 characters of the serial number of {d['model'] or d['name']} ({d['ends']})")
                if re.sub(r"[^A-Za-z0-9]", "", typed).upper() == d["ends"]:
                    confirm[d["by_id"]] = d["ends"]
                    break
                term.note(f"That is not {d['ends']}. Type it as it is on the drive's label, or q to stop.")
    if not term.yes_no("Make these changes now? sudo asks for this computer's password", False, help_key="pool"):
        term.note("Nothing was changed. Make the pool later on System, Storage, Pool.")
        return True
    jobs = [(d, "pool") for d in chosen] + ([(backup[1], backup[0])] if backup else [])
    try:
        for d, role in jobs:
            args = ["plan", "add", d["by_id"], "--as", role] + (["--erase"] if d["by_id"] in confirm else [])
            if role == "copy":
                args += ["--folders", "media"]
            plan = run(args)
            done = run(["apply", plan["id"]] + (["--confirm", f"{d['by_id']}={confirm[d['by_id']]}"] if d["by_id"] in confirm else []))
            for s in done.get("steps", []):
                (term.ok if s["state"] == "done" else term.warn)(s["say"])
    except Problem as e:
        term.warn(f"The pool helper stopped: {e}. Drives already done stay done; see System, Storage, Pool.")
        return True
    state["pool_dir"] = "/mnt/pool"
    if len(chosen) + len(pool) >= 2 and term.yes_no("Balance the files across the drives now? It can take hours, "
                                                    "at low priority", False, help_key="balance"):
        try:
            plan = run(["plan", "balance"])
            term.say("  " + plan["steps"][0]["say"])
            if plan.get("moves"):
                run(["apply", plan["id"]])
                term.ok("Balanced.")
        except Problem as e:
            term.warn(f"Balancing stopped: {e}")
    else:
        term.note("Balance later on System, Storage, Pool.")
    return True


def step_connect(api, term, state):
    """Connect your apps: Starboard's Jellyfin extras, once Jellyfin is there. Keys of apps Install apps started are
    set by Starboard itself; apps added from Move get theirs read where Docker allows."""
    config = api.call("GET", "/api/config")
    has_jellyfin = any(s["type"] == "jellyfin" for s in config["services"]) or "jellyfin" in ((state.get("choice") or {}).get("apps") or [])
    if not has_jellyfin:
        return False
    term.heading(title("extras"), num(title("extras")))
    extras = [("livetv", "Live TV channels and guide", "Free channels for Jellyfin's Live TV, with guides"),
              ("import_keep", "Bring in watch history", "From Plex, Emby or another Jellyfin"),
              ("defaults", "Defaults for every user", "Live TV opens on the Guide for everyone")]
    picked = term.choose_many("Use Starboard's Jellyfin extras?", [(t, a) for _, t, a in extras],
                              state.get("extras", [i for i, (k, _, _) in enumerate(extras) if config["extras"].get(k)]), help_key="extras",
                              allow_none=True)
    state["extras"] = picked
    api.call("PUT", "/api/config/general", {"extras": {k: i in picked for i, (k, _, _) in enumerate(extras)}})
    if 0 in picked and not env_value("STARBOARD_LIVETV_PATH"):
        folder = (state.get("choice") or {}).get("config_dir", "")
        if folder:
            state.setdefault("host", {})["livetv"] = folder.rstrip("/") + "/jellyfin/iptv"
        term.note("Live TV needs a folder Jellyfin reads; it is set up at the end, with your other changes to this computer.")
    term.ok("Saved. Change them later in Settings, Apps, Jellyfin.")
    return True


def step_alerts(api, term, state):
    """Alerts and disk health: a push service for alerts, and the disk health reports (set up at the end)."""
    term.heading(title("alerts"), num(title("alerts")))
    last = state.get("alerts", {})
    kind = term.choose("Get an alert when an app stops or a disk has a problem?",
                       [("Not now", "No alerts"), ("ntfy", "A free push service with a phone app"),
                        ("Gotify", "Your own push server"), ("A webhook", "Starboard posts to an address you choose")],
                       last.get("kind", 1), help_key="alerts")
    if kind == 0:
        api.call("PUT", "/api/config/general", {"watch": {"enabled": False}})
    else:
        url = term.text("Its address", last.get("url", "https://ntfy.sh/" if kind == 1 else ""), help_key="alerts")
        api.call("PUT", "/api/config/general", {"watch": {"enabled": True, "channel": {"kind": ["", "ntfy", "gotify", "webhook"][kind], "url": url}}})
        last["url"] = url
    last["kind"] = kind + 1
    state["alerts"] = last
    term.note("Disk health: a small script reads each disk's health report every 30 minutes, so Starboard can warn you "
              "before a disk fails. It is set up at the end and asks for this computer's password once.")
    health = term.yes_no("Check each disk's health?", state.get("host", {}).get("health", True), help_key="health")
    state.setdefault("host", {})["health"] = health
    return True


def env_value(name):
    """A value from the .env in the Starboard folder, where the installer saved it, or ""."""
    try:
        with open(".env", encoding="utf-8") as f:
            for line in f:
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def host_changes(state, data_dir):
    """What the set-up chose that changes this computer (free space for the media folder, the Live TV folder, disk
    health), saved for the Run first script to apply with ./install.sh, and shown as the command to run. The same
    options as the browser set-up (starboard/start.py)."""
    host = state.get("host") or {}
    args = start.host_args({"media": host.get("disk", "").split("=", 1)[-1], "livetv": host.get("livetv"),
                            "health": host.get("health")})
    if args:
        try:
            with open(os.path.join(data_dir, "setup-host.json"), "w", encoding="utf-8") as f:
                json.dump({"args": args}, f)
        except OSError:
            pass
    return args


def step_preset(api, term, state):
    """How much Starboard does: the same presets and words as the browser's set-up guide."""
    config = api.call("GET", "/api/config")
    keys = ["small", "balanced", "everything"]
    recommended = config.get("preset_recommended", "balanced")
    keys = [recommended] + [k for k in keys if k != recommended]  # the recommended one at the top
    HELP["preset"] = "\n\n".join(f"{config['presets'][k]}: {config['preset_about'][k]}" for k in keys)
    term.heading(title("preset"), num(title("preset")))
    term.note("How much Starboard does in the background. You can change each part later in Settings, Performance.")
    current = config["performance"].get("preset", recommended)
    current = current if current in keys else recommended
    default = keys.index(state.get("preset", recommended if current == "balanced" else current)) + 1
    picked = term.choose("How much should Starboard do?",
                         [(config["presets"][k] + (" (recommended)" if k == recommended else ""), config["preset_about"][k])
                          for k in keys], default, help_key="preset")
    api.call("PUT", "/api/config/general", {"preset": keys[picked]})
    state["preset"] = keys[picked]
    term.ok(f"{config['presets'][keys[picked]]}. Change it later in Settings, Performance.")
    return True


STEP_FUNCTIONS = [step_password, step_start, step_storage, step_apps, step_vpn, step_usenet, step_check, step_connect, step_hours,
                  step_alerts, step_preset]


def add_drives_step(available=None):
    """Your drives goes after Storage when the pool helper is installed and the pool is chosen (DASH-87)."""
    available = os.path.exists(POOL_HELPER) if available is None else available
    if available and step_drives not in STEP_FUNCTIONS:
        STEP_FUNCTIONS.insert(3, step_drives)  # after Storage, when the pool was chosen
        STEPS.insert(3, title("drives"))


def run(api, term, data_dir, port, address=""):
    if not term.fancy:
        term.say("\nStarboard set-up, in the terminal")
        term.note("Every question has a number or a word to type, and Enter takes the answer in [brackets]. "
                  "Type ? at any question for help, b to go back a step, f to send feedback, or q to stop. You can "
                  "carry on later in a browser instead.")
    state = {"data_dir": data_dir}
    api.on_error = term.record_error
    add_drives_step()
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
        args = host_changes(state, data_dir)
        if args:
            rows.append(("Changes to this computer", "./install.sh " + " ".join(args)))
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
