"""Location and keyboard, the first questions of every set-up (DASH-259), and where the symbols are when the
keyboard layout set does not match the keyboard (DASH-112).

One source for the words and the lists: the browser set-up reads them from /api/setup/place, the terminal set-up
imports them, and the Run first script, which arrives on its own through curl, has a copy between its "places"
lines (tests/test_places.py checks the copy matches bash_block()).

A location is a country with its time zone (one line for each zone in a country with several). Each suggests a
keyboard and a system language. A keyboard is an XKB layout and variant: on Debian, Ubuntu, Linux Mint and
Raspberry Pi OS the console takes its keymap from the same setting (/etc/default/keyboard), which
`localectl set-x11-keymap` writes. 13 November 2026.
"""

import os
import re
import subprocess  # nosec B404: only localectl and timedatectl, read only, on the computer itself

# (id, what the person sees, XKB layout, XKB variant)
KEYBOARDS = [
    ("gb", "UK", "gb", ""),
    ("us", "US", "us", ""),
    ("ie", "Irish", "ie", ""),
    ("gb-mac", "Apple UK", "gb", "mac"),
    ("us-mac", "Apple US", "us", "mac"),
    ("us-intl", "US international (accents with ' and \")", "us", "intl"),
    ("de", "German", "de", ""),
    ("fr", "French", "fr", ""),
    ("es", "Spanish", "es", ""),
    ("it", "Italian", "it", ""),
    ("pt", "Portuguese", "pt", ""),
    ("nl", "Dutch", "nl", ""),
    ("be", "Belgian", "be", ""),
    ("ch", "Swiss German", "ch", ""),
    ("ch-fr", "Swiss French", "ch", "fr"),
    ("se", "Swedish", "se", ""),
    ("no", "Norwegian", "no", ""),
    ("dk", "Danish", "dk", ""),
    ("fi", "Finnish", "fi", ""),
    ("pl", "Polish", "pl", ""),
    ("ca", "Canadian French", "ca", ""),
]

# (what the person sees, time zone, keyboard id, system language). UK first: Starboard's own home.
LOCATIONS = [
    ("United Kingdom", "Europe/London", "gb", "en_GB.UTF-8"),
    ("Ireland", "Europe/Dublin", "ie", "en_IE.UTF-8"),
    ("United States, Eastern", "America/New_York", "us", "en_US.UTF-8"),
    ("United States, Central", "America/Chicago", "us", "en_US.UTF-8"),
    ("United States, Mountain", "America/Denver", "us", "en_US.UTF-8"),
    ("United States, Pacific", "America/Los_Angeles", "us", "en_US.UTF-8"),
    ("Canada, Eastern", "America/Toronto", "us", "en_CA.UTF-8"),
    ("Canada, Atlantic", "America/Halifax", "us", "en_CA.UTF-8"),
    ("Canada, Pacific", "America/Vancouver", "us", "en_CA.UTF-8"),
    ("Australia, Sydney", "Australia/Sydney", "us", "en_AU.UTF-8"),
    ("Australia, Perth", "Australia/Perth", "us", "en_AU.UTF-8"),
    ("New Zealand", "Pacific/Auckland", "us", "en_NZ.UTF-8"),
    ("South Africa", "Africa/Johannesburg", "us", "en_ZA.UTF-8"),
    ("India", "Asia/Kolkata", "us", "en_IN.UTF-8"),
    ("Germany", "Europe/Berlin", "de", "de_DE.UTF-8"),
    ("Austria", "Europe/Vienna", "de", "de_AT.UTF-8"),
    ("France", "Europe/Paris", "fr", "fr_FR.UTF-8"),
    ("Spain", "Europe/Madrid", "es", "es_ES.UTF-8"),
    ("Italy", "Europe/Rome", "it", "it_IT.UTF-8"),
    ("Portugal", "Europe/Lisbon", "pt", "pt_PT.UTF-8"),
    ("Netherlands", "Europe/Amsterdam", "us-intl", "nl_NL.UTF-8"),
    ("Belgium", "Europe/Brussels", "be", "nl_BE.UTF-8"),
    ("Switzerland", "Europe/Zurich", "ch", "de_CH.UTF-8"),
    ("Sweden", "Europe/Stockholm", "se", "sv_SE.UTF-8"),
    ("Norway", "Europe/Oslo", "no", "nb_NO.UTF-8"),
    ("Denmark", "Europe/Copenhagen", "dk", "da_DK.UTF-8"),
    ("Finland", "Europe/Helsinki", "fi", "fi_FI.UTF-8"),
    ("Poland", "Europe/Warsaw", "pl", "pl_PL.UTF-8"),
    ("Other: Coordinated Universal Time", "Etc/UTC", "us", "C.UTF-8"),
]

KEYBOARD_IDS = {k[0] for k in KEYBOARDS}
TZ_RE = re.compile(r"^[A-Za-z0-9_+/-]{1,40}$")

# DASH-112: where six symbols really are on each kind of keyboard when the US layout is set (the usual default on
# a new server). The keys are named by what is printed on them. UK first; Irish keyboards are the same as UK.
# To check on a real keyboard of each kind (the UK one was checked against the XKB tables).
SYMBOLS = ["|", "\\", "#", "~", "@", '"']
WRONG_LAYOUT = {
    "gb": {"|": "Shift and the key marked # ~ (beside Enter)",
           "\\": "the key marked # ~ (beside Enter)",
           "#": "Shift and 3 (the key marked £)",
           "~": "Shift and the key marked ` ¬ (left of 1)",
           "@": "Shift and 2 (the key marked \")",
           '"': "Shift and the key marked ' @ (left of the # ~ key)"},
    "de": {"|": "Shift and the key marked # ' (beside Enter)",
           "\\": "the key marked # ' (beside Enter)",
           "#": "Shift and 3 (the key marked §)",
           "~": "Shift and the key marked ^ ° (left of 1)",
           "@": "Shift and 2 (the key marked \")",
           '"': "Shift and the key marked Ä"},
    "fr": {"|": "Shift and the key marked * µ (beside Enter)",
           "\\": "the key marked * µ (beside Enter)",
           "#": "Shift and the key marked 3 \"",
           "~": "Shift and the key marked ² (left of the & 1 key)",
           "@": "Shift and the key marked 2 é",
           '"': "Shift and the key marked ù %"},
    "es": {"|": "Shift and the key marked Ç (beside Enter)",
           "\\": "the key marked Ç (beside Enter)",
           "#": "Shift and 3 (the key marked ·)",
           "~": "Shift and the key marked º ª (left of 1)",
           "@": "Shift and 2 (the key marked \")",
           '"': "Shift and the key marked ´ ¨ (right of Ñ)"},
    "it": {"|": "Shift and the key marked ù § (beside Enter)",
           "\\": "the key marked ù § (beside Enter)",
           "#": "Shift and 3 (the key marked £)",
           "~": "Shift and the key marked \\ | (left of 1)",
           "@": "Shift and 2 (the key marked \")",
           '"': "Shift and the key marked à ° (right of ò)"},
}
WRONG_LAYOUT["ie"] = WRONG_LAYOUT["gb"]

SET_IT_RIGHT = ("To set the right layout: run the Run first script again and choose your keyboard, or type "
                "sudo localectl set-x11-keymap gb (with your keyboard's code in place of gb, such as ie, de or fr), "
                "then sudo setupcon.")


def keyboard(kid):
    return next((k for k in KEYBOARDS if k[0] == kid), None)


def location_of(tz):
    return next((p for p in LOCATIONS if p[1] == tz), None)


def keyboard_for(layout, variant=""):
    """The keyboard id for an XKB layout and variant, or "" when it is not in the list."""
    found = next((k for k in KEYBOARDS if k[2] == layout and k[3] == (variant or "")), None)
    return found[0] if found else ""


def symbols_help(kid):
    """Where the symbols are on this keyboard when the US layout is set, in lines of words. Empty when the layout is
    US already, or the keyboard is not one in the table yet."""
    where = WRONG_LAYOUT.get(kid)
    if not where:
        return []
    name = keyboard(kid)[1]
    return [f"On a {name} keyboard with the US layout set, the symbols are not where they are marked:"] + \
        [f"{s} is {where[s]}" for s in SYMBOLS]


def read_computer(run=None):
    """The time zone and keyboard this computer has now, read only: {"tz", "layout", "variant", "keyboard"}.
    In Starboard's container there is no localectl, so only TZ (from .env) is known there."""
    run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False).stdout)  # nosec B603
    found = {"tz": "", "layout": "", "variant": "", "keyboard": ""}
    try:
        found["tz"] = run(["timedatectl", "show", "-p", "Timezone", "--value"]).strip()
    except (OSError, subprocess.SubprocessError):
        pass
    if not found["tz"]:
        try:
            with open("/etc/timezone", encoding="utf-8") as f:
                found["tz"] = f.read().strip()
        except OSError:
            found["tz"] = ""
    try:
        status = run(["localectl", "status"])
    except (OSError, subprocess.SubprocessError):
        status = ""
    m = re.search(r"X11 Layout:\s*(\S+)", status)
    if m:
        found["layout"] = m.group(1).split(",")[0]
    m = re.search(r"X11 Variant:\s*(\S+)", status)
    if m:
        found["variant"] = m.group(1).split(",")[0]
    found["keyboard"] = keyboard_for(found["layout"], found["variant"])
    if not TZ_RE.match(found["tz"] or ""):
        found["tz"] = ""
    return found


def recommended(found, handover=None):
    """The recommended location (a time zone) and keyboard id: what the Run first script chose, then what the
    computer has (a US layout counts only when the location suggests it, as it is the default nobody chose), then
    the location's suggestion. Never a guess: with nothing found, the computer's time zone stays."""
    handover = handover if isinstance(handover, dict) else {}
    tz = handover.get("tz") if TZ_RE.match(str(handover.get("tz") or "")) else (found.get("tz") or os.environ.get("TZ") or "Etc/UTC")
    place = location_of(tz)
    kid = handover.get("keyboard") if handover.get("keyboard") in KEYBOARD_IDS else ""
    have = found.get("keyboard") or ""
    if not kid:
        if have and have != "us":
            kid = have
        elif place:
            kid = place[2]
        else:
            kid = have or "us"
    return tz, kid


def options(found=None, handover=None):
    """Both lists, the recommended one first in each and saying so, for both set-ups."""
    found = found if found is not None else {"tz": os.environ.get("TZ", ""), "keyboard": ""}
    tz, kid = recommended(found, handover)
    places = [{"tz": p[1], "title": p[0], "keyboard": p[2], "recommended": p[1] == tz} for p in LOCATIONS]
    if not any(p["recommended"] for p in places):  # a time zone not in the list: keep it, first
        places.insert(0, {"tz": tz, "title": f"Keep this computer's time zone ({tz})", "keyboard": kid, "recommended": True})
    places.sort(key=lambda p: not p["recommended"])
    boards = [{"id": k[0], "title": k[1], "layout": k[2], "variant": k[3], "recommended": k[0] == kid,
               "symbols": symbols_help(k[0])} for k in KEYBOARDS]
    boards.sort(key=lambda b: not b["recommended"])
    return {"tz": tz, "keyboard": kid, "locations": places, "keyboards": boards, "symbols": SYMBOLS, "set_it_right": SET_IT_RIGHT,
            "found": {"tz": found.get("tz", ""), "keyboard": found.get("keyboard", "")}}


def clean(choice):
    """The person's answer, checked: {"tz", "keyboard"}. Raises ValueError with words to act on."""
    choice = choice if isinstance(choice, dict) else {}
    tz = str(choice.get("tz") or "")
    if not TZ_RE.match(tz) or ".." in tz:
        raise ValueError("Choose where you are from the list")
    kid = str(choice.get("keyboard") or "")
    if kid not in KEYBOARD_IDS:
        raise ValueError("Choose your keyboard from the list")
    return {"tz": tz, "keyboard": kid}


def host_args(choice, found):
    """./install.sh options that change this computer to match, when it does not already."""
    args = []
    if choice.get("tz") and choice["tz"] != found.get("tz"):
        args += ["--timezone", choice["tz"]]
    if choice.get("keyboard") and choice["keyboard"] != found.get("keyboard"):
        args += ["--keyboard", choice["keyboard"]]
    return args


def bash_block():
    """The lists as bash arrays, for the Run first script's copy (between its "places" lines)."""
    def q(s):
        return "'" + s.replace("'", "'\\''") + "'"
    lines = ["# places: start (written from starboard/places.py by bash_block(); change that file, then copy it here)"]
    lines.append("PLACE_TITLE=(" + " ".join(q(p[0]) for p in LOCATIONS) + ")")
    lines.append("PLACE_TZ=(" + " ".join(q(p[1]) for p in LOCATIONS) + ")")
    lines.append("PLACE_KB=(" + " ".join(q(p[2]) for p in LOCATIONS) + ")")
    lines.append("PLACE_LANG=(" + " ".join(q(p[3]) for p in LOCATIONS) + ")")
    lines.append("KB_ID=(" + " ".join(q(k[0]) for k in KEYBOARDS) + ")")
    lines.append("KB_TITLE=(" + " ".join(q(k[1]) for k in KEYBOARDS) + ")")
    lines.append("KB_LAYOUT=(" + " ".join(q(k[2]) for k in KEYBOARDS) + ")")
    lines.append("KB_VARIANT=(" + " ".join(q(k[3]) for k in KEYBOARDS) + ")")
    lines.append("# Where the symbols are with the US layout set, by keyboard: one line each, | between the six (DASH-112).")
    lines.append("declare -A KB_SYMBOLS=(" + " ".join(
        f"[{kid}]={q('|'.join(WRONG_LAYOUT[kid][s].replace('|', '¦') for s in SYMBOLS))}" for kid in sorted(WRONG_LAYOUT)) + ")")
    lines.append("# places: end")
    return "\n".join(lines) + "\n"


SAVED = "setup-place.json"


def computer_from_env():
    """What Starboard in its container knows of this computer: the time zone (TZ, which the installer sets from the
    computer's) and the keyboard the installer read (STARBOARD_HOST_KEYBOARD)."""
    kid = os.environ.get("STARBOARD_HOST_KEYBOARD", "")
    tz = os.environ.get("TZ", "")
    return {"tz": tz if TZ_RE.match(tz) else "", "keyboard": kid if kid in KEYBOARD_IDS else ""}


def saved(data_dir):
    """The answer the set-up saved, or {}."""
    import json
    try:
        with open(os.path.join(data_dir, SAVED), encoding="utf-8") as f:
            return clean(json.load(f))
    except (OSError, ValueError, TypeError):
        return {}


def save(data_dir, choice):
    import json
    choice = clean(choice)
    tmp = os.path.join(data_dir, SAVED + ".new")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(choice, f)
    os.replace(tmp, os.path.join(data_dir, SAVED))
    return choice


def change(choice, found):
    """What the set-up's change to this computer holds for the location and keyboard: only what differs."""
    return {"timezone": choice["tz"] if choice["tz"] != found.get("tz") else "",
            "keyboard": choice["keyboard"] if found.get("keyboard") and choice["keyboard"] != found["keyboard"] else ""}
