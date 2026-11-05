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
import sys
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


class Terminal:
    """Questions and answers. ask and secret are replaceable, so the tests can answer."""

    def __init__(self, out=sys.stdout, ask=input, secret=getpass.getpass):
        self.out, self._ask, self._secret = out, ask, secret

    def say(self, text=""):
        print(text, file=self.out, flush=True)

    def heading(self, text):
        self.say(f"\n== {text}")

    def _read(self, prompt, help_key):
        while True:
            answer = self._ask(prompt).strip()
            if answer.lower() in ("q", "quit"):
                raise Stop()
            if answer == "?":
                self.say(HELP.get(help_key, "There is no more help for this question.") if help_key else
                         "There is no more help for this question.")
                continue
            return answer

    def choose(self, question, options, default=1, help_key=None):
        """Numbered options; returns the index (0-based)."""
        self.say(f"\n{question}")
        for i, text in enumerate(options, 1):
            self.say(f"  {i}. {text}")
        while True:
            answer = self._read(f"Your choice [{default}]: ", help_key) or str(default)
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            self.say(f"Type a number from 1 to {len(options)}, ? for help or q to stop.")

    def choose_many(self, question, options, defaults, help_key=None):
        """Numbered options, several at once (1,3,4); returns the indexes chosen."""
        self.say(f"\n{question} Type the numbers, separated by commas.")
        for i, text in enumerate(options, 1):
            self.say(f"  {i}. {text}")
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
        answer = self._secret(f"{question} (nothing shows as you type): ")
        if answer.strip().lower() == "q":
            raise Stop()
        return answer


def sign_in(api, term, data_dir):
    """The first password, with the setup code read from the data folder, or the existing password."""
    token_file = os.path.join(data_dir, "setup-token")
    if os.path.exists(token_file):
        with open(token_file) as f:
            token = f.read().strip()
        term.heading("Your password")
        term.say("Choose the password for Starboard. You use it to sign in from any device. No setup code is needed:")
        term.say("you are on the server itself. Type ? for help.")
        while True:
            first = term.hidden("Choose a password, 10 characters or more")
            if first.strip() == "?":
                term.say(HELP["password"])
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
            term.say("Password saved. You are signed in.")
            return first
    term.heading("Sign in")
    term.say("Starboard already has a password. Type it to carry on (forgotten it? Stop with q and run ./reset-password.sh).")
    for _ in range(5):
        password = term.hidden("Your Starboard password")
        try:
            api.call("POST", "/api/login", {"password": password})
            term.say("Signed in.")
            return password
        except Problem as e:
            term.say(f"Starboard said: {e}")
    raise Problem("Too many wrong passwords. Run this again later")


def choose_apps(api, term):
    """Returns (the Install apps choice, the apps' names), or None to install nothing."""
    overview = api.call("GET", "/api/stack")
    groups = overview["groups"]
    term.heading("Your media server")
    if term.choose("Install the apps for your media server now?",
                   ["Yes (recommended)", "No: I have my apps already, or I will add them later in the browser"],
                   help_key="groups") == 1:
        return None
    picked = term.choose_many("What do you want?", [f"{g['name']}: {g['about']}" for g in groups],
                              [i for i, g in enumerate(groups) if g["default"]], help_key="groups")
    keys = {groups[i]["key"] for i in picked}
    apps = [a for a in overview["apps"] if set(a["groups"]) & keys and not a["installed"]]
    chosen = [a for a in apps if a["default"]]
    if not apps:
        term.say("Every app for that is running already. Nothing to install.")
        return None
    if chosen:
        term.say("\nThese apps would be installed: " + ", ".join(a["name"] for a in chosen) +
                 f" (about {sum(a['memory'] for a in chosen)} MB of memory).")
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
    term.heading("Your VPN")
    term.say("Some of the VPN providers below have affiliate links in Starboard's help. If you sign up through one, the")
    term.say("provider pays a small amount towards Starboard's development, at no extra cost to you.")
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
    term.heading("Check before anything changes")
    term.say("Install: " + ", ".join(names or choice["apps"]))
    term.say(f"Media folder: {choice['data_dir']}")
    term.say(f"Settings folder: {choice['config_dir']}")
    for line in preview.get("moved", []):
        term.say(line)
    if not term.yes_no("Write the apps' files now?", True):
        term.say("Nothing written.")
        return False
    written = api.call("POST", "/api/stack/write", choice)
    if not written.get("can_start"):
        term.say("Written. Starboard cannot start apps itself, because it has no full Docker access. Start them with:")
        term.say(f"  {written['command']}")
        return True
    if not term.yes_no("Start the apps now? They are downloaded first, which can take a few minutes.", True):
        term.say(f"Start them later with:  {written['command']}")
        return True
    api.call("POST", "/api/stack/start", {"password": password})
    term.say("Downloading and starting the apps ...")
    while True:
        time.sleep(wait)
        job = api.call("GET", "/api/stack/job")
        if job.get("finished"):
            break
    if job.get("ok"):
        term.say(f"All {len(choice['apps'])} apps are running.")
        return True
    term.say("The apps did not all start. The last lines Docker wrote:")
    for line in (job.get("log") or "").strip().splitlines()[-12:]:
        term.say(f"  {line}")
    return False


def download_hours(api, term):
    term.heading("Download hours")
    term.say("Downloading uses most of your internet connection while it runs, so other devices can slow down.")
    term.say("Downloading at night keeps the day free.")
    if term.choose("When should downloads run?", ["Only at set hours (recommended)", "At any time"], help_key="hours") == 1:
        api.call("PUT", "/api/config/general", {"download_hours": {"enabled": False}})
        return None
    while True:
        start = term.text("From, as an hour from 0 to 23", "1", help_key="hours")
        end = term.text("Until, as an hour from 0 to 23", "7", help_key="hours")
        try:
            api.call("PUT", "/api/config/general", {"download_hours": {"enabled": True, "start": int(start), "end": int(end)}})
            term.say(f"Downloads run from {int(start):02d}:00 to {int(end):02d}:00. Change it later in Settings, General.")
            return int(start), int(end)
        except (ValueError, Problem) as e:
            term.say(f"That did not work: {e}. Type whole hours, such as 1 and 7.")


def run(api, term, data_dir, port, address=""):
    term.say("\nStarboard set-up, in the terminal")
    term.say("Every question has a number or a word to type, and Enter takes the answer in [brackets].")
    term.say("Type ? at any question for help, or q to stop. You can carry on later in a browser instead.")
    password = sign_in(api, term, data_dir)
    picked = choose_apps(api, term)
    if picked:
        install_apps(api, term, picked[0], password, picked[1])
    download_hours(api, term)
    term.heading("Done")
    term.say(f"On this computer:  http://localhost:{port}")
    if address:
        term.say(f"On your phone or other computers:  http://{address}:{port}")
    term.say("Everything here can be changed later in Starboard's Settings. To run these questions again:")
    term.say(f"  python3 -m starboard.terminal_setup --port {port}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Set Starboard up in the terminal.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("STARBOARD_PORT", "8095")))
    parser.add_argument("--data", default="data", help="Starboard's data folder (default: ./data)")
    parser.add_argument("--address", default="", help="This computer's address on the home network, to show at the end")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        print("Stopped: this needs a terminal to type in. Finish set-up in a browser instead.", file=sys.stderr)
        return 2
    term = Terminal()
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
