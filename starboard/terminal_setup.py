"""Set Starboard up in the terminal, for a server with no desktop and no other device to hand (DASH-86).

Run by ./install.sh --terminal once Starboard is running, or by hand from the Starboard folder:
    python3 -m starboard.terminal_setup --port 8095

It asks the same questions as the browser, one at a time, as plain numbered lines: no full-screen menus, so it
works over SSH and with a screen reader. Enter takes the recommended answer, ? shows help and q stops. It talks
to Starboard's own API on this computer, so every answer is checked exactly as the browser's would be, and
nothing changes until you confirm. Passwords and VPN keys are typed hidden and never written to the screen.
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
}


class Stop(Exception):
    """The person typed q."""


class Problem(Exception):
    """Starboard said no: the message is Starboard's own, for the person."""


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


class Terminal:
    """Questions and answers. ask and secret are replaceable, so the tests can answer.

    In a terminal at least 60 characters wide, headings are boxed with a progress bar below, summaries are cards,
    and finished steps are ticked. Colour only adds to the words: every mark has words after it, and recommended
    answers say so. With --plain, TERM=dumb or output that is not a terminal, it prints plain numbered lines, which
    suit a screen reader (one reads box characters aloud). NO_COLOR keeps the boxes without colour."""

    def __init__(self, out=sys.stdout, ask=input, secret=getpass.getpass, fancy=None, colour=None, width=None):
        self.out, self._ask, self._secret = out, ask, secret
        self.width = min(width or shutil.get_terminal_size((80, 24)).columns, 78)
        tty = hasattr(out, "isatty") and out.isatty()
        self.fancy = (tty and os.environ.get("TERM") != "dumb") if fancy is None else fancy
        self.fancy = self.fancy and self.width >= 60
        self.colour = self.fancy and not os.environ.get("NO_COLOR") if colour is None else colour and self.fancy

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

    def say(self, text=""):
        print(text, file=self.out, flush=True)

    def heading(self, text, step=None):
        if not self.fancy:
            self.say(f"\n== Starboard | {text}" + (f" (step {step} of {len(STEPS)})" if step else ""))
            return
        inner = self.width - 4
        right = f"step {step} of {len(STEPS)}" if step else ""
        # "Starboard | Your password": the product name in bold, then the step, then the count on the right.
        left = f"Starboard | {text}"
        gap = max(inner - len(left) - len(right) - 2, 1)
        self.say("")
        self.say(self.dim("┌" + "─" * (inner + 2) + "┐"))
        self.say(self.dim("│") + "  " + self._c("1", "Starboard") + self.dim(" | ") + self.accent(text) + " " * gap
                 + self.dim(right) + "  " + self.dim("│"))
        self.say(self.dim("└" + "─" * (inner + 2) + "┘"))
        if step:
            bar = self.width - 12
            done = round(bar * (step - 1) / len(STEPS))
            pct = f"{round(100 * (step - 1) / len(STEPS)):>3}%"
            self.say("  " + self._c("36", "█" * done) + self.dim("░" * (bar - done)) + "  " + self.dim(pct))

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

    def _prompt(self, text):
        return f"  {self.accent('›')} {text}" if self.fancy else text

    def _read(self, prompt, help_key):
        while True:
            answer = self._ask(self._prompt(prompt)).strip()
            if answer.lower() in ("q", "quit"):
                raise Stop()
            if answer == "?":
                self.note(HELP.get(help_key, "There is no more help for this question.") if help_key else
                          "There is no more help for this question.")
                continue
            return answer

    def _options(self, options, defaults):
        """Options are text, or (name, about) pairs set in two columns."""
        name_w = max((len(o[0]) for o in options if isinstance(o, tuple)), default=0) + 2
        for i, o in enumerate(options, 1):
            text = f"{o[0]}: {o[1]}" if isinstance(o, tuple) else o
            if not self.fancy:
                self.say(f"  {i}. {text}")
                continue
            mark = self.accent("●") if i - 1 in defaults else " "
            if isinstance(o, tuple):  # the about column wraps under itself, inside the width
                about = textwrap.wrap(o[1], self.width - 8 - name_w) or [""]
                text = o[0].ljust(name_w) + self.dim(about[0])
                text += "".join("\n" + " " * (8 + name_w) + self.dim(more) for more in about[1:])
            text = re.sub(r"\(recommended[^)]*\)", lambda m: self.good(m.group(0)), text)
            self.say(f"  {mark} {self.accent(str(i).rjust(2))}  {text}")

    def choose(self, question, options, default=1, help_key=None):
        """Numbered options; returns the index (0-based)."""
        self.say(f"\n  {question}" if self.fancy else f"\n{question}")
        self._options(options, {default - 1})
        while True:
            answer = self._read(f"Your choice [{default}]: ", help_key) or str(default)
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            self.say(f"Type a number from 1 to {len(options)}, ? for help or q to stop.")

    def choose_many(self, question, options, defaults, help_key=None):
        """Numbered options, several at once (1,3,4); returns the indexes chosen."""
        lead = "  " if self.fancy else ""
        self.say(f"\n{lead}{question} Type the numbers, separated by commas.")
        self._options(options, set(defaults))
        shown = ",".join(str(i + 1) for i in defaults)
        while True:
            answer = self._read(f"Your choice [{shown}]: ", help_key) or shown
            parts = [p.strip() for p in answer.replace(" ", ",").split(",") if p.strip()]
            if parts and all(p.isdigit() and 1 <= int(p) <= len(options) for p in parts):
                return sorted({int(p) - 1 for p in parts})
            self.say(f"Type numbers from 1 to {len(options)}, such as 1,2, or ? for help, or q to stop.")

    def yes_no(self, question, default=True, help_key=None):
        while True:
            answer = self._read(f"{question} [{'Y/n' if default else 'y/N'}]: ", help_key).lower()
            if not answer:
                return default
            if answer[0] in "yn":
                return answer[0] == "y"
            self.say("Type y for yes or n for no.")

    def text(self, question, default="", help_key=None):
        shown = f" [{default}]" if default else ""
        return self._read(f"{question}{shown}: ", help_key) or default

    def hidden(self, question):
        """Typed without showing it. Empty is allowed: the caller decides."""
        answer = self._secret(self._prompt(f"{question} (nothing shows as you type): "))
        if answer.strip().lower() == "q":
            raise Stop()
        return answer

    def waiting(self, text, check, wait):
        """Shows a turning mark and the time taken until check() returns something, then returns it."""
        began, turn = time.time(), 0
        while True:
            result = check()
            if result is not None:
                if self.fancy:
                    self.out.write("\r" + " " * (self.width - 1) + "\r")
                return result
            if self.fancy:
                secs = int(time.time() - began)
                self.out.write(f"\r  {self.accent('◐◓◑◒'[turn % 4])} {text} {self.dim(f'{secs // 60} min {secs % 60:02d} s')}")
                self.out.flush()
                turn += 1
            time.sleep(wait)


def sign_in(api, term, data_dir):
    """The first password, with the setup code read from the data folder, or the existing password."""
    token_file = os.path.join(data_dir, "setup-token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read().strip()
        term.heading("Your password", 1)
        term.note("Choose the password for Starboard. You use it to sign in from any device. No setup code is needed: "
                  "you are on the server itself. Type ? for help.")
        while True:
            first = term.hidden("Choose a password, 10 characters or more")
            if first.strip() == "?":
                term.note(HELP["password"])
                continue
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
            return first
    term.heading("Sign in", 1)
    term.note("Starboard already has a password. Type it to carry on (forgotten it? Stop with q and run ./reset-password.sh).")
    for _ in range(5):
        password = term.hidden("Your Starboard password")
        try:
            api.call("POST", "/api/login", {"password": password})
            term.ok("Signed in.")
            return password
        except Problem as e:
            term.say(f"Starboard said: {e}")
    raise Problem("Too many wrong passwords. Run this again later")


def choose_apps(api, term):
    """Returns (the Install apps choice, the apps' names), or None to install nothing."""
    overview = api.call("GET", "/api/stack")
    groups = overview["groups"]
    term.heading("Your media server", 2)
    if term.choose("Install the apps for your media server now?",
                   ["Yes (recommended)", "No: I have my apps already, or I will add them later in the browser"],
                   help_key="groups") == 1:
        return None
    picked = term.choose_many("What do you want?", [(g["name"], g["about"]) for g in groups],
                              [i for i, g in enumerate(groups) if g["default"]], help_key="groups")
    keys = {groups[i]["key"] for i in picked}
    apps = [a for a in overview["apps"] if set(a["groups"]) & keys and not a["installed"]]
    chosen = [a for a in apps if a["default"]]
    if not apps:
        term.say("Every app for that is running already. Nothing to install.")
        return None
    if chosen:
        term.card("These apps would be installed", [("Apps", ", ".join(a["name"] for a in chosen)),
                                                    ("Memory", f"about {sum(a['memory'] for a in chosen):,} MB")])
    if not chosen or term.choose("Install these?", ["Yes (recommended)", "Let me choose app by app"], help_key="apps") == 1:
        chosen = []
        for a in apps:
            about = f" ({a['notes']})" if a["notes"] else ""
            if term.yes_no(f"Install {a['name']}{about}?", a["default"], help_key="apps"):
                chosen.append(a)
    if not chosen:
        term.say("No apps chosen. Nothing to install.")
        return None
    d = overview["defaults"]
    term.say("")
    data_dir = term.text("Media folder, for films, series, books and downloads", d["data_dir"], help_key="folders")
    config_dir = term.text("Settings folder, for each app's own settings", d["config_dir"], help_key="folders")
    choice = {"apps": [a["key"] for a in chosen], "data_dir": data_dir, "config_dir": config_dir,
              "puid": d["puid"], "pgid": d["pgid"], "tz": d["tz"]}
    if any(a["key"] == "gluetun" for a in chosen):
        choice["vpn"] = choose_vpn(term)
    return choice, [a["name"] for a in chosen]


def choose_vpn(term):
    term.heading("Your VPN", 3)
    term.note("Some of the VPN providers below have affiliate links in Starboard's help. If you sign up through one, the "
              "provider pays a small amount towards Starboard's development, at no extra cost to you.")
    pick = term.choose("Which VPN provider do you have?", [n for _, n in VPNS] + ["Another one that Gluetun supports"],
                       help_key="vpn")
    if pick < len(VPNS):
        provider = VPNS[pick][0]
    else:
        provider = term.text("Its name, as Gluetun's list writes it (for example: mullvad)", help_key="vpn").lower()
    kind = ["wireguard", "openvpn"][term.choose("How should it connect?", ["WireGuard (recommended: faster)", "OpenVPN"],
                                                help_key="vpn")]
    vpn = {"provider": provider, "type": kind, "countries": term.text("Countries to connect through (Enter for any)", "")}
    if kind == "wireguard":
        vpn["wireguard_private_key"] = term.hidden("WireGuard private key, from your provider")
        vpn["wireguard_addresses"] = term.text("WireGuard address from your provider, ending in /32", help_key="vpn")
    else:
        vpn["openvpn_user"] = term.text("OpenVPN user name, from your provider", help_key="vpn")
        vpn["openvpn_password"] = term.hidden("OpenVPN password")
    return vpn


def install_apps(api, term, choice, password, names=None, wait=2.0):
    """Shows what will be written, writes it once confirmed, and starts the apps when Starboard may."""
    while True:
        try:
            preview = api.call("POST", "/api/stack/preview", choice)
            break
        except Problem as e:
            term.say(f"Starboard said: {e}")
            if "folder" in str(e).lower():
                choice["data_dir"] = term.text("Media folder", choice["data_dir"], help_key="folders")
                choice["config_dir"] = term.text("Settings folder", choice["config_dir"], help_key="folders")
            elif "vpn" in str(e).lower() or "wireguard" in str(e).lower() or "openvpn" in str(e).lower():
                choice["vpn"] = choose_vpn(term)
            else:
                return False
    term.heading("Check before anything changes", 4)
    rows = [("Install", ", ".join(names or choice["apps"])), ("Media folder", choice["data_dir"]),
            ("Settings folder", choice["config_dir"])]
    if choice.get("vpn"):
        rows.append(("VPN", f"{dict(VPNS).get(choice['vpn']['provider'], choice['vpn']['provider'])}, "
                            f"{'WireGuard' if choice['vpn']['type'] == 'wireguard' else 'OpenVPN'}"))
    term.card("What will change", rows)
    for line in preview.get("moved", []):
        term.warn(line)
    if not term.yes_no("Write the apps' files now?", True):
        term.say("Nothing written.")
        return False
    written = api.call("POST", "/api/stack/write", choice)
    if not written.get("can_start"):
        term.ok(f"{len(choice['apps'])} apps written.")
        term.note("Starboard cannot start apps itself, because it has no full Docker access. Start them with:")
        term.say(f"  {written['command']}")
        return True
    if not term.yes_no("Start the apps now? They are downloaded first, which can take a few minutes.", True):
        term.say(f"Start them later with:  {written['command']}")
        return True
    term.ok(f"{len(choice['apps'])} apps written.")
    api.call("POST", "/api/stack/start", {"password": password})
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
    return False


def download_hours(api, term):
    term.heading("Download hours", 5)
    term.note("Downloading uses most of your internet connection while it runs, so other devices can slow down. "
              "Downloading at night keeps the day free.")
    if term.choose("When should downloads run?", ["Only at set hours (recommended)", "At any time"], help_key="hours") == 1:
        api.call("PUT", "/api/config/general", {"download_hours": {"enabled": False}})
        return None
    while True:
        start = term.text("From, as an hour from 0 to 23", "1", help_key="hours")
        end = term.text("Until, as an hour from 0 to 23", "7", help_key="hours")
        try:
            api.call("PUT", "/api/config/general", {"download_hours": {"enabled": True, "start": int(start), "end": int(end)}})
            term.ok(f"Download hours: {int(start):02d}:00 to {int(end):02d}:00. Change them later in Settings, General.")
            return int(start), int(end)
        except (ValueError, Problem) as e:
            term.say(f"That did not work: {e}. Type whole hours, such as 1 and 7.")


def run(api, term, data_dir, port, address=""):
    term.say("\n" + term.accent("Starboard set-up, in the terminal") if term.fancy else "\nStarboard set-up, in the terminal")
    term.note("Every question has a number or a word to type, and Enter takes the answer in [brackets]. "
              "Type ? at any question for help, or q to stop. You can carry on later in a browser instead.")
    password = sign_in(api, term, data_dir)
    picked = choose_apps(api, term)
    if picked:
        install_apps(api, term, picked[0], password, picked[1])
    download_hours(api, term)
    rows = [("On this computer", f"http://localhost:{port}")]
    if address:
        rows.append(("On your other devices", f"http://{address}:{port}"))
    rows.append(("Ask these again", f"python3 -m starboard.terminal_setup --port {port}"))
    term.card("Starboard is ready", rows, colour="32")
    term.note("Everything here can be changed later in Starboard's Settings.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Set Starboard up in the terminal.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("STARBOARD_PORT", "8095")))
    parser.add_argument("--data", default="data", help="Starboard's data folder (default: ./data)")
    parser.add_argument("--address", default="", help="This computer's address on the home network, to show at the end")
    parser.add_argument("--plain", action="store_true", help="Plain lines with no boxes or colour, for a screen reader")
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
        term.say(f"\nStopped: {e}" if isinstance(e, Problem) else "\nStopped.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
