"""Starboard's settings from the terminal (DASH-90), for a server with no desktop and nothing else to open a browser on.

    ./settings.sh            (or: python3 -m starboard.terminal_settings --port 8095)

The same look and rules as the terminal set-up (the design system's TERMINAL.md): a heading box, numbered answers
with the recommended one first, the menu on the bottom line (b Back, ? Help, f Feedback, q Stop), help over the
step, and plain lines for screen readers (--plain or STARBOARD_PLAIN=1). It signs in with the Starboard password and
changes every setting through Starboard's own API on this computer, never its files, so Starboard checks each change
as it does from a page.

It starts with the automatic update settings: whether Starboard looks for new versions, whether Reelix installs its
own updates, and how to update Starboard or go back to an earlier version (./update.sh, which this does not run for
you: it restarts Starboard). Other sections follow the same pattern. 13 November 2026.
"""

import argparse
import os
import subprocess  # nosec B404: git tag only, read only, in Starboard's own folder
import sys

from .terminal_setup import HELP, HELP_PAGES, Api, Back, Problem, Stop, Terminal, env_value, fingerprint

HELP.update({
    "settings": "Each part of Starboard's settings that can be changed here. Everything here can also be changed in "
                "Starboard's Settings pages from a browser. Type q to close the settings at any time; nothing changes "
                "until you choose it.",
    "updates": "Look for new versions: Starboard checks GitHub once a day and says on Settings, Updates and in the "
               "side menu when a new version is out. It never installs one by itself. Reelix installs its own updates: "
               "once a day at most, Starboard installs a new Reelix, saving its settings first, and goes back to the "
               "version before if the new one is not healthy. Update Starboard with ./update.sh in the Starboard "
               "folder; ./update.sh --to and a version goes back to that version, restoring the settings it saved.",
    "settings-password": "The password you chose for Starboard, the one you sign in with from a browser. Forgotten "
                         "it? Stop with q and run ./reset-password.sh in the Starboard folder.",
})
HELP_PAGES.update({"updates": "topics/update-starboard.html", "settings": "topics/find-a-setting.html",
                   "settings-password": "topics/reset-a-forgotten-password.html"})

ON, OFF = "Active", "Inactive"


def releases(folder=".", run=None):
    """The newest Starboard versions on this computer (git tags), newest first, at most five."""
    run = run or (lambda cmd: subprocess.run(cmd, cwd=folder, capture_output=True, text=True, timeout=10, check=False).stdout)  # nosec B603
    try:
        tags = run(["git", "tag", "--sort=-v:refname", "--list", "v*"]).split()
    except (OSError, subprocess.SubprocessError):
        tags = []
    return tags[:5]


def sign_in(api, term):
    term.heading("Sign in")
    term.note("Type your Starboard password, the one you sign in with from a browser.")
    for _ in range(5):
        password = term.hidden("Your Starboard password", help_key="settings-password")
        term.typed.add(fingerprint(password))  # never in a feedback report
        try:
            api.call("POST", "/api/login", {"password": password})
            term.ok("Signed in.")
            return
        except Problem as e:
            term.note(f"Starboard said: {e}")
    raise Problem("Too many wrong passwords. Run this again later")


def automatic_updates(api, term, version, folder="."):
    """One page: what is set now, then one change at a time, each saved through the API as soon as it is chosen."""
    while True:
        cfg = api.call("GET", "/api/config")
        check, reelix = cfg.get("update_check", True) is not False, bool(cfg.get("reelix_auto_update"))
        has_reelix = any(s.get("icon") == "reelix" or s.get("type") == "reelix" for s in cfg.get("services", []))
        term.heading("Automatic updates")
        term.card("Now", [("Starboard", version or "unknown version"),
                          ("Look for new versions", ON if check else OFF),
                          ("Reelix installs its own updates", (ON if reelix else OFF) if has_reelix else "No Reelix yet"),
                          ("Your apps", "Updated from Apps, Updates, when you choose")])
        # Nothing to change is the recommended answer, first, so Enter never changes a setting by mistake.
        options = [("Done: back to the settings (recommended)", "Nothing changes."),
                   ("Look for new Starboard versions: " + ("deactivate" if check else "activate"),
                    "Starboard says when a new version is out. It never installs one by itself."),
                   ("Update Starboard or go back to an earlier version", "The command to run, with the versions on this computer.")]
        if has_reelix:
            options.insert(2, ("Reelix installs its own updates: " + ("deactivate" if reelix else "activate"),
                               "Once a day at most, with its settings saved first and a way back."))
        term.can_back = True
        picked = term.choose("What do you want to change?", options, 1, help_key="updates")
        name = options[picked][0]
        if name.startswith("Done"):
            return
        if name.startswith("Look for new"):
            api.call("PUT", "/api/config/general", {"update_check": not check})
            term.ok(f"Look for new versions is now {(OFF if check else ON).lower()}.")
        elif name.startswith("Reelix"):
            api.call("PUT", "/api/config/general", {"reelix_auto_update": not reelix})
            term.ok(f"Reelix installing its own updates is now {(OFF if reelix else ON).lower()}.")
        else:
            tags = releases(folder)
            rows = [("Update to the newest", "./update.sh"), ("Only check", "./update.sh --check")]
            rows += [(f"Go back to {t}" if i else f"Install {t} again", f"./update.sh --to {t}") for i, t in enumerate(tags)]
            term.card("In the Starboard folder", rows)
            term.note("Each one saves Starboard's settings first and restarts Starboard, so this window signs out. "
                      "If the new version does not start, it goes back to the one you had.")
        term.text("Press Enter to carry on", help_key="updates")


def run(api, term, version, folder="."):
    sign_in(api, term)
    while True:
        term.can_back = False
        term.heading("Settings")
        term.note("Starboard's settings from the terminal. More parts come here over time; all of them are also in "
                  "Starboard's Settings pages.")
        picked = term.choose("Which settings?", [("Automatic updates (recommended)", "Whether Starboard and Reelix update, and going back"),
                                                ("Close the settings", "")], 1, help_key="settings")
        if picked == 1:
            break
        try:
            automatic_updates(api, term, version, folder)
        except Back:
            continue
    term.finish()
    term.say("Closed. Run ./settings.sh again at any time.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Change Starboard's settings in the terminal.")
    parser.add_argument("--port", type=int, default=int(os.environ.get("STARBOARD_PORT") or env_value("STARBOARD_PORT") or 8095))
    parser.add_argument("--plain", action="store_true", help="Plain lines with no boxes, colour or redrawing, for a screen reader")
    args = parser.parse_args(argv)
    if not sys.stdin.isatty():
        print("Stopped: this needs a terminal to type in. Change the settings in a browser instead.", file=sys.stderr)
        return 2
    plain = bool(args.plain or os.environ.get("STARBOARD_PLAIN"))
    term = Terminal(fancy=False if plain else None)
    term.watch_size()
    term.plain_asked = plain
    term.where = "Terminal settings"
    from .server import read_version
    try:
        return run(Api(args.port), term, read_version())
    except Stop:
        term.finish()
        term.say("\nClosed. Nothing else was changed.")
        return 1
    except Problem as e:
        term.finish()
        term.say(f"\nStopped: {e}")
        return 1
    except (KeyboardInterrupt, EOFError):
        term.finish()
        term.say("\nClosed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
