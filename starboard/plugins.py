"""Plug-ins (DASH-149), first part: the manifest, its check, the permissions people approve, and the Compose file
Starboard writes for a plug-in with its hardened defaults. The design is in PLUGIN-SYSTEM-DESIGN (DASH-272); the
rules are P1 to P17 and PS1 to PS11 in the developer best practice.

A plug-in is containers, a manifest (starboard-plugin.json), optional settings and cards, and an API key limited to
what the person approved. It never adds code to Starboard's pages, never gets the Docker socket, privileged mode,
the host network, devices, or any folder but its own.
"""
import json
import os
import re

from . import app_logs

MANIFEST_VERSION = 1
API_VERSION = "1.24.0"  # 1.24 (27 November 2026, DASH-572): the permission power:hold, so a plug-in such as UPS and power may hold Starboard's heavy automatic jobs and downloads while on battery with POST /api/v1/plugin/hold (it ends by itself after 10 minutes unless renewed), and the time setting type, one time of day such as 22:00. 1.22 (27 November 2026, DASH-603): starboard_tested and capabilities (named optional parts, GET /api/v1/ lists them). 1.21 (27 November 2026, DASH-589): needs_plugins, the plug-ins a plug-in needs, and switch, the setting that turns a plug-in on and off; switching off or turning off a plug-in asks first and turns off the plug-ins that need it. 1.20 (26 November 2026, DASH-590): first_sign_in, a password Starboard made for an app plug-in and shows once on its page, so the app does not start with a default one everybody knows. 1.19 (25 November 2026, DASH-567): requires, the system a plug-in needs, as a tag ("Jellyfin only", "Plex or Emby", "Needs Reelix") shown on the Catalogue, the plug-in page, Manage and Ready to update; older manifests get it from the permissions they ask for (plugin_systems.py). 1.18 was left to DASH-572 and became 1.24, the next additive version  # 1.17 (20 November 2026): the sparkline card, one small line a series with the latest, lowest and highest value in words, for a plug-in such as Advanced dashboard's response times; the permission alerts:send, so a plug-in may raise and clear alerts with POST /api/v1/plugin/alerts, sent once until cleared through the same channel, events and log as Starboard's own  # 1.16 (19 November 2026): custom pages may answer for one menu (partial), open a slide-out to choose several (picker, browse, pick), draw cards (layout cards, hints) and show a picture on a row (image), told by X-Starboard-Can; the disk.changed event, sent when the pool helper finishes a job (issue #187); a plug-in is turned on when installed; plain text add boxes; STARBOARD_HOME_ADDRESS for a published lan container  # 1.15 (15 November 2026): containers built from a zip (build, DASH-414), Jellyfin libraries (jellyfin_libraries, DASH-430), and the permission library:holding with the media:holding volume, so a plug-in such as Library clean-up can move films and series into the holding folder inside the media folder (media/.holding/<plug-in id>) and put them back, never deleting, with restore on a custom screen item drawn as Put back (DASH-406); and titles on a card, a title for each card size, each short enough for one line in that size (DASH-443); the list of what it added is in docs/help/developers/api-changelog.md  # 1.14 (14 November 2026, owner: "allow a card to set its refresh time with 10s being the quickest time"): a card may say how often the dashboard asks it, refresh_seconds from 10 to 3600, in the manifest and, to change it from a setting, in its answer; Starboard never asks a card more often than every 10 seconds, and the catalogue may mark an entry recommended; a small logo (logo: file and alt, DASH-428), cards drawn with a grey band holding the logo, the name, a status chip and when it last updated (status, status_label and updated in the answer); a job on a schedule from its settings (a schedule setting: every day, week or month at a time, DASH-432); the permission jellyfin:metadata with the jellyfin-metadata volume (DASH-432); update tools (DASH-424): an update object with a before and an after step Starboard calls with time limits, a health wait after which a version that does not answer is rolled back by itself, and settings migrations (rename, remove, new defaults) kept for Roll back, and What is new shown before an update from the new version's changes  # 1.13 (13 November 2026, DASH-411): app plug-ins, a whole app such as Jellystat with its database: publish on the lan network with network:port (Starboard chooses a free port on the home network, host_port is the one it tries first), tmpfs, data mounted at a path (data:/path, data/<folder>:/path), env values from {secret:name} and {jellyfin:url} or {jellyfin:key}, resources pids, and adopt, which copies an app you already have into the plug-in  # 1.12 (13 November 2026, DASH-410): a container may run as the media folder's owner (user "media") to add files in the media folders it mounts, which Starboard makes for it; a custom screen's item may have a link (opened in a new tab) and its own words for its state (state_label), and its add box may take only a file (file_only)  # 1.11 (13 November 2026, DASH-401 and DASH-402): four more events (request.available, download.failed, disk.nearly_full, update.available) for a notifications plug-in, and readonly on a custom screen with folds, so a table of figures has no tick boxes or Turn on buttons  # 1.10 (13 November 2026, DASH-393): optional changes, the plug-in's own changelog by version (Added, Changed, Fixed and the rest), shown as What is new on its State after an update or a Roll back; older plug-ins without it still work  # 1.9 (13 November 2026): a container on the vpn network may set publish, so its port goes on Gluetun for the home network  # 1.8 (13 November 2026, DASH-359): a custom screen may fold its items into sections with a table each (layout folds, columns, filters, cells), select several (bulk_ids), add a guide to an item (attach, detach), show notices with progress; a card may be a guide  # 1.7 (13 November 2026, DASH-361): a custom screen may have sub menus, items and bulk switches placed in them  # 1.6 (12 November 2026, owner): permissions reelix:key and usenet:servers, handed over as run/reelix.json and run/usenet.json  # 1.5 (12 November 2026, DASH-307): settings may have a group, each its own section; a choice may be {value, label}  # 1.4 (12 November 2026, DASH-330): required settings and setup_required, notices, events, jobs, card refresh_minutes  # 1.3 (12 November 2026): a folder setting is a folder inside the media folders the plug-in mounts, chosen with the location picker  # 1.2 (12 November 2026): styles may also set card, button, border, tab, header, side menu and chip styles  # 1.1 (11 November 2026): styles may set more colours, heading font and weight, focus width  # 1.23 (27 November 2026, DASH-585 and DASH-604): replaces_or_adds, one line saying what the plug-in replaces or adds to, shown on the Catalogue card, the install warning, the plug-in page and Manage; and icon, one icon from Starboard's set for the plug-in's tab in Settings, Plug-ins, checked against the set. 1.22 (27 November 2026, DASH-603): starboard_tested and capabilities (named optional parts, GET /api/v1/ lists them). 1.21 (27 November 2026, DASH-589): needs_plugins, the plug-ins a plug-in needs, and switch, the setting that turns a plug-in on and off; switching off or turning off a plug-in asks first and turns off the plug-ins that need it. 1.20 (26 November 2026, DASH-590): first_sign_in, a password Starboard made for an app plug-in and shows once on its page, so the app does not start with a default one everybody knows. 1.19 (25 November 2026, DASH-567): requires, the system a plug-in needs, as a tag ("Jellyfin only", "Plex or Emby", "Needs Reelix") shown on the Catalogue, the plug-in page, Manage and Ready to update; older manifests get it from the permissions they ask for (plugin_systems.py). 1.18 is left to DASH-572  # 1.17 (20 November 2026): the sparkline card, one small line a series with the latest, lowest and highest value in words, for a plug-in such as Advanced dashboard's response times; the permission alerts:send, so a plug-in may raise and clear alerts with POST /api/v1/plugin/alerts, sent once until cleared through the same channel, events and log as Starboard's own  # 1.16 (19 November 2026): custom pages may answer for one menu (partial), open a slide-out to choose several (picker, browse, pick), draw cards (layout cards, hints) and show a picture on a row (image), told by X-Starboard-Can; the disk.changed event, sent when the pool helper finishes a job (issue #187); a plug-in is turned on when installed; plain text add boxes; STARBOARD_HOME_ADDRESS for a published lan container  # 1.15 (15 November 2026): containers built from a zip (build, DASH-414), Jellyfin libraries (jellyfin_libraries, DASH-430), and the permission library:holding with the media:holding volume, so a plug-in such as Library clean-up can move films and series into the holding folder inside the media folder (media/.holding/<plug-in id>) and put them back, never deleting, with restore on a custom screen item drawn as Put back (DASH-406); and titles on a card, a title for each card size, each short enough for one line in that size (DASH-443); the list of what it added is in docs/help/developers/api-changelog.md  # 1.14 (14 November 2026, owner: "allow a card to set its refresh time with 10s being the quickest time"): a card may say how often the dashboard asks it, refresh_seconds from 10 to 3600, in the manifest and, to change it from a setting, in its answer; Starboard never asks a card more often than every 10 seconds, and the catalogue may mark an entry recommended; a small logo (logo: file and alt, DASH-428), cards drawn with a grey band holding the logo, the name, a status chip and when it last updated (status, status_label and updated in the answer); a job on a schedule from its settings (a schedule setting: every day, week or month at a time, DASH-432); the permission jellyfin:metadata with the jellyfin-metadata volume (DASH-432); update tools (DASH-424): an update object with a before and an after step Starboard calls with time limits, a health wait after which a version that does not answer is rolled back by itself, and settings migrations (rename, remove, new defaults) kept for Roll back, and What is new shown before an update from the new version's changes  # 1.13 (13 November 2026, DASH-411): app plug-ins, a whole app such as Jellystat with its database: publish on the lan network with network:port (Starboard chooses a free port on the home network, host_port is the one it tries first), tmpfs, data mounted at a path (data:/path, data/<folder>:/path), env values from {secret:name} and {jellyfin:url} or {jellyfin:key}, resources pids, and adopt, which copies an app you already have into the plug-in  # 1.12 (13 November 2026, DASH-410): a container may run as the media folder's owner (user "media") to add files in the media folders it mounts, which Starboard makes for it; a custom screen's item may have a link (opened in a new tab) and its own words for its state (state_label), and its add box may take only a file (file_only)  # 1.11 (13 November 2026, DASH-401 and DASH-402): four more events (request.available, download.failed, disk.nearly_full, update.available) for a notifications plug-in, and readonly on a custom screen with folds, so a table of figures has no tick boxes or Turn on buttons  # 1.10 (13 November 2026, DASH-393): optional changes, the plug-in's own changelog by version (Added, Changed, Fixed and the rest), shown as What is new on its State after an update or a Roll back; older plug-ins without it still work  # 1.9 (13 November 2026): a container on the vpn network may set publish, so its port goes on Gluetun for the home network  # 1.8 (13 November 2026, DASH-359): a custom screen may fold its items into sections with a table each (layout folds, columns, filters, cells), select several (bulk_ids), add a guide to an item (attach, detach), show notices with progress; a card may be a guide  # 1.7 (13 November 2026, DASH-361): a custom screen may have sub menus, items and bulk switches placed in them  # 1.6 (12 November 2026, owner): permissions reelix:key and usenet:servers, handed over as run/reelix.json and run/usenet.json  # 1.5 (12 November 2026, DASH-307): settings may have a group, each its own section; a choice may be {value, label}  # 1.4 (12 November 2026, DASH-330): required settings and setup_required, notices, events, jobs, card refresh_minutes  # 1.3 (12 November 2026): a folder setting is a folder inside the media folders the plug-in mounts, chosen with the location picker  # 1.2 (12 November 2026): styles may also set card, button, border, tab, header, side menu and chip styles  # 1.1 (11 November 2026): styles may set more colours, heading font and weight, focus width
ID = r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$"
SEMVER = r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$"
DIGEST_IMAGE = r"^[a-z0-9.-]+(:\d+)?(/[a-z0-9._-]+)+@sha256:[0-9a-f]{64}$"
TAG_IMAGE = r"^[a-z0-9.-]+(:\d+)?(/[a-z0-9._-]+)+(:[A-Za-z0-9._-]{1,128})?$"
SPDX = r"^[A-Za-z0-9.+-]{2,40}$"

# What each permission means, in the words people read before install (PS1), and its risk.
PERMISSIONS = {
    "apps:read": ("Your apps and whether they answer", "low", "apps"),
    "downloads:read": ("What is downloading", "low", "downloads"),
    "media:read": ("Your films, series and books (the media folder, read only, and the library)", "medium", "media"),
    "system:read": ("Processor, memory and disks", "low", "system"),
    "network:lan": ("Reach other computers on your home network", "medium", None),
    "network:vpn": ("Run inside your VPN connection", "medium", None),
    "jellyfin:key": ("Use Jellyfin's API key, kept by Starboard", "high", None),
    "reelix:key": ("Use Reelix's API key, kept by Starboard", "high", None),  # API 1.6
    "usenet:servers": ("Use your news server's address and sign-in, from NZBGet or SABnzbd", "high", None),  # API 1.6
    # API 1.13 (DASH-411): an app plug-in's own web page, opened on the home network at a port Starboard chooses
    "network:port": ("Open its own web page on your home network, at a port Starboard chooses", "medium", None),
    "appearance:styles": ("Add styles to Display: colours, corners, a font and shadows, checked for accessibility", "low", None),
    # API 1.14 (DASH-432): Jellyfin's metadata folder (/metadata on new installs, DASH-431), mounted only with this
    "jellyfin:metadata": ("Read and change Jellyfin's metadata folder: the posters, photos and details Jellyfin saved", "medium", None),
    # API 1.15 (DASH-430): libraries Starboard adds to Jellyfin for the plug-in, named in jellyfin_libraries
    "jellyfin:libraries": ("Have Starboard add its own libraries to Jellyfin, for folders it fills in your media folder", "medium", None),
    # API 1.15 (DASH-406): the media folder, read and write, to move films and series into its holding folder and back
    "library:holding": ("Move films and series from your library into the holding folder in your media folder, and put them back", "high", None),
    # API 1.17: raise and clear alerts with POST /api/v1/plugin/alerts, the one write a plug-in's read-only key may do
    "alerts:send": ("Send alerts through Starboard, to where it sends its own (ntfy, Gotify, a webhook, and plug-ins that pass them on)", "low", None),
    # API 1.24 (DASH-572): hold Starboard's heavy automatic jobs and downloads while on battery, with POST /api/v1/plugin/hold
    "power:hold": ("Ask Starboard to hold its heavy jobs and downloads, for example while the computer runs on battery", "low", None),
    # DASH-565: the media server slot. A plug-in that fills it answers for Starboard's dashboard panel, Library, Activity
    # and System. Only plug-ins that ship inside Starboard may ask for it so far (third-party ones: a later step).
    "slot:media-server": ("Be Starboard's media server: answer for the dashboard panel, Library, Activity and System, using the address and key kept in Settings, Apps", "high", None),
}
NETWORKS = {"default": None, "lan": "network:lan", "vpn": "network:vpn"}
SETTING_TYPES = ("text", "number", "switch", "choice", "address", "secret", "folder", "list", "custom", "schedule", "time")  # schedule: API 1.14; time: API 1.24
CARD_TYPES = ("stat", "list", "status", "guide", "sparkline")  # guide: what is on now (API 1.8, DASH-359); sparkline: API 1.17
CARD_FORMATS = ("number", "bytes", "percent", "duration", "date")
DEFAULT_MEMORY, DEFAULT_CPUS, CEILING_MEMORY, CEILING_CPUS = 128, 0.25, 512, 1.0
# API 1.13 (DASH-411): an app plug-in (one with network:port) may ask for more, for an app such as Tdarr converting a
# film, which Docker would stop part way at 512 MB. Shown before install like any limit; the rest figure is what counts.
APP_CEILING_MEMORY, APP_CEILING_CPUS = 2048, 4.0

TOP = {"manifest_version", "id", "name", "version", "description", "author", "licence", "homepage", "support_url",
       "starboard_api", "containers", "permissions", "resources", "settings", "cards", "health", "actions", "needs", "styles",
       "setup_required", "notices", "events", "jobs", "changes", "adopt", "logo", "update", "jellyfin_libraries", "requires", "first_sign_in", "needs_plugins", "switch", "starboard_tested", "capabilities", "replaces_or_adds", "icon"}
REQUIRED = TOP - {"resources", "settings", "cards", "health", "actions", "needs", "styles", "containers",
                  "setup_required", "notices", "events", "jobs", "changes", "adopt", "logo", "update", "jellyfin_libraries", "requires", "first_sign_in", "needs_plugins", "switch", "starboard_tested", "capabilities", "replaces_or_adds", "icon"}
CONTAINER = {"name", "image", "port", "network", "volumes", "env", "start", "idle_stop_minutes", "user", "command", "publish",
             "host_port", "tmpfs", "entrypoint", "files", "build"}
# API 1.23 (DASH-585): one plain line on what a plug-in replaces or adds to ("Adds to Jellyfin: ...", "Replaces Starboard's
# own ...", "Stands alone"), shown before install and on the plug-in's page.
NOTE_MAX = 140


def note_problems(value, name="replaces_or_adds"):
    """What is wrong with a one-line note, in words; [] when it is fine."""
    if not isinstance(value, str) or not 0 < len(value.strip()) <= NOTE_MAX:
        return [f"{name} must be one line of text, up to {NOTE_MAX} characters"]
    if re.search(r"[\r\n<>`]", value):
        return [f"{name} must be plain text on one line, with no tags or back quotes"]
    return []


def clean_note(value):
    """A note as the catalogue shows it: the text when it passes note_problems, else ''."""
    return value.strip() if isinstance(value, str) and not note_problems(value) else ""


# API 1.23 (DASH-604): the icon names Starboard's set has (web/icons/sprite.svg), read once the first time one is checked.
_icon_names = None


def icon_names():
    global _icon_names
    if _icon_names is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "icons", "sprite.svg")
        try:
            with open(path, encoding="utf-8") as f:
                _icon_names = frozenset(re.findall(r'<symbol[^>]* id="i-([a-z0-9-]+)"', f.read()))
        except OSError:
            _icon_names = frozenset()
    return _icon_names


def clean_icon(value):
    """The icon name when it is in Starboard's set, else '' (the menu then draws the puzzle piece)."""
    return value if isinstance(value, str) and value in icon_names() else ""


# API 1.15 (DASH-414): a container whose image Starboard builds from the Dockerfile in the plug-in's zip file, for a
# private plug-in with no registry. Its image is always local/<id>:<version>, so one plug-in can never name another's.
# Only a plug-in installed or updated from a zip may have one (plugin_zip.py); from an address it is refused.
def built_image(manifest):
    return f"local/{manifest.get('id')}:{manifest.get('version')}"


def builds(manifest):
    """The containers Starboard builds from the zip's Dockerfile (API 1.15)."""
    return [c for c in (manifest.get("containers") or []) if isinstance(c, dict) and c.get("build") is True] if isinstance(manifest, dict) else []


# API 1.15 (DASH-430): Jellyfin libraries a plug-in fills, such as On demand's films and series. Starboard adds them
# to Jellyfin with real-time monitoring turned off unless the plug-in needs it (Jellyfin watching a folder costs one
# of the computer's folder watches for every folder in it), and keeps that choice on every start and update.
JELLYFIN_LIBRARY = {"name", "type", "folder", "realtime_monitor"}
LIBRARY_TYPES = {"movies": "movies", "tvshows": "tvshows", "music": "music", "books": "books", "homevideos": "homevideos",
                 "musicvideos": "musicvideos", "mixed": ""}  # mixed: Jellyfin's films and series together (no type)
MAX_LIBRARIES = 4
# API 1.13 (DASH-411): what an app plug-in needs. A path inside the container (for tmpfs and data:<path>), never
# Starboard's own /run/starboard, and values in env that Starboard fills in when it writes the Compose file.
INSIDE = r"^/(?!run/starboard(/|$))(?!.*(^|/)\.\.(/|$))[A-Za-z0-9._/-]{1,100}$"
DATA_AT = r"^data(/[a-z0-9][a-z0-9._-]{0,39})?:(/[A-Za-z0-9._/-]{1,100})$"
FILLED = re.compile(r"\{(secret:[a-z][a-z0-9_]{0,29}|jellyfin:url|jellyfin:key)\}")
MAX_PIDS, MAX_TMPFS = 1024, 6


def _unknown_hole(text):
    """True when a {secret...} or {jellyfin...} is left that Starboard does not fill in: one is there when a } comes
    after the first {secret or {jellyfin. Looked at once, from the start, so a long value of "{secret{secret..." is
    no slower to check than a short one (code scanning, 13 November 2026: the pattern it replaces backtracked)."""
    starts = [i for i in (text.find("{secret"), text.find("{jellyfin")) if i >= 0]
    return bool(starts) and "}" in text[min(starts):]
# Plug-ins that ship inside Starboard (plugins/<id>/ in its own folder): they may run Starboard's own image
# ("image": "starboard") with a command, and Live TV may use the Live TV folder the installer gave ("iptv").
BUILTIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
BUILTIN_VOLUMES = {"iptv"}
SETTING = {"key", "label", "type", "hint", "default", "min", "max", "unit", "choices", "restart", "item", "required", "group"}
# A card's own refresh time (API 1.14, owner 14 November 2026): 10 seconds is the quickest, an hour the slowest.
REFRESH_MIN, REFRESH_MAX = 10, 3600
CARD = {"id", "title", "titles", "type", "path", "format", "label", "example", "refresh_minutes", "refresh_seconds"}
# A title for each card size (API 1.15, DASH-443, owner 15 November 2026: "different titles for each type of card and
# cap the max number of characters for each type", "only to go on one line per card"). Each cap is the most
# characters of a wide, realistic title that fit on one line beside the logo, with the band's status chip and time,
# at the default text size and the narrowest desktop width that size is shown at (measured in the real dashboard
# styles, DASH-443). A size left out uses the card's title, under the plug-in's name, as before.
CARD_SIZES = ("small", "medium", "half", "wide", "full")
# Measured (DASH-443) with the widest of ten realistic titles in the heading's font (600 16px Atkinson Hyperlegible
# Next): small 147 pixels at 1101 wide, the chip and time under it; medium 228 pixels at 1101, the chip and time under
# it (beside a chip with words only 2 characters fit); half 184, wide 344 at 1101 and full 349 at 768, each beside a
# chip with words and the time ("Converting", "38 seconds ago").
CARD_TITLE_MAX = {"small": 17, "medium": 28, "half": 22, "wide": 43, "full": 45}


def card_title_problems(card):
    """What is wrong with a card's titles (API 1.15): [(what, fix)], each title on one line in its size."""
    if "titles" not in card:
        return []
    titles = card["titles"]
    sizes = ", ".join(CARD_SIZES)
    if not isinstance(titles, dict) or not titles:
        return [("titles must be an object with a title for one or more sizes: " + sizes,
                 'Write it as {"small": "Short title", "half": "A longer title"}')]
    out = []
    for size, text in titles.items():
        if size not in CARD_TITLE_MAX:
            out.append((f"titles has an unknown size {str(size)[:20]}", f"Use only {sizes}"))
        elif not isinstance(text, str) or not text.strip():
            out.append((f"the {size} title must be words", "Give it a title, or leave the size out to use the card's title"))
        elif re.search(r"[\x00-\x1f\x7f]", text):
            out.append((f"the {size} title has a line break or a control character", "Write it as one line of plain words"))
        elif len(text) > CARD_TITLE_MAX[size]:
            out.append((f"the {size} title is {len(text)} characters, and a {size} card has room for {CARD_TITLE_MAX[size]} on one line",
                        f"Shorten it to {CARD_TITLE_MAX[size]} characters or fewer"))
    return out
# API 1.4 (DASH-330, from Stremio and Jellyfin): notices shown before install, events a plug-in hears, and jobs Starboard
# runs for it. Each event needs the read permission that already covers what it tells.
NOTICES = {"p2p": "Shares files with other people over the internet, which can show your internet address",
           "adult": "Has adult content"}
EVENTS = {"item.added": ("media:read", "When something new arrives in your library"),
          "download.finished": ("downloads:read", "When a download finishes"),
          "app.down": ("apps:read", "When one of your apps stops answering"),
          "app.up": ("apps:read", "When one of your apps answers again"),
          "playback.started": ("media:read", "When someone starts playing something"),
          # API 1.11 (DASH-401): what a notifications plug-in sends on, each from a check Starboard already makes
          "request.available": ("media:read", "When something someone asked for is ready to watch"),
          "download.failed": ("downloads:read", "When a download stops with a problem"),
          "disk.nearly_full": ("system:read", "When a disk is nearly full"),
          "update.available": ("apps:read", "When an update is ready for Starboard, an app or a plug-in"),
          # API 1.16 (owner, 19 November 2026): every pool job the root helper finishes, however it was asked for, so
          # an erase you did not start is never silent (issue #187, accepted risk with an alert).
          "disk.changed": ("system:read", "When a disk is erased, added to the pool or taken out of it")}
JOB = {"id", "label", "path", "daily", "every_hours", "at_start", "schedule", "time_limit_minutes", "quiet_hours"}
# A schedule from the plug-in's settings (API 1.14, DASH-432): a setting of type schedule, which the person sets to
# every day, every week on a day, or every month on a date, at a time. A month without that date runs on its last day.
SCHEDULE_EVERY = ("day", "week", "month")
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
TIME = r"^([01]\d|2[0-3]):[0-5]\d$"
# Jellyfin's metadata folder (API 1.14, DASH-432): read and write, or read only, at /metadata in the container.
JELLYFIN_METADATA = ("jellyfin-metadata", "jellyfin-metadata:ro")
# The media folder, read and write, at /media (API 1.15, DASH-406): only with library:holding. A move into the holding
# folder must stay inside one mount to be a rename (a move between two mounts is a copy, then a delete), so the
# holding folder is inside the media folder: media/.holding/<plug-in id>/, keeping the folders each item was in.
MEDIA_HOLDING = "media:holding"
ACTION = {"id", "label", "path", "confirm"}
# API 1.10 (DASH-393): the plug-in's changelog in the manifest, in Keep a Changelog's types, so Starboard can say what
# is new after an update without fetching anything. Kept short: 20 versions, 20 lines a type, 300 characters a line.
CHANGE_TYPES = ("added", "changed", "deprecated", "removed", "fixed", "security")
CHANGE = {"version", "date"} | set(CHANGE_TYPES)


def _range_ok(spec, version=API_VERSION):
    """True when `version` is inside a range such as ">=1.0 <2.0" (only >=, >, <=, < and = are used)."""
    def parts(v):
        return tuple(int(x) for x in (v.split("-")[0].split(".") + ["0", "0"])[:3])
    have = parts(version)
    for clause in str(spec).split():
        m = re.match(r"^(>=|<=|>|<|=)?(\d+(?:\.\d+){0,2})$", clause)
        if not m:
            return False
        op, want = m.group(1) or "=", parts(m.group(2))
        if not {">=": have >= want, "<=": have <= want, ">": have > want, "<": have < want, "=": have == want}[op]:
            return False
    return True


def check(manifest, dev=False, builtin=False):
    """Every problem with a manifest, as plain sentences; an empty list when it can be installed. `dev`: development
    mode, which allows images without a digest (P17)."""
    out = []
    m = manifest if isinstance(manifest, dict) else {}
    if not isinstance(manifest, dict):
        return ["The manifest must be a JSON object"]
    for k in sorted(set(m) - TOP):
        out.append(f"Unknown field {k}")
    for k in sorted(REQUIRED - set(m)):
        out.append(f"Missing field {k}")
    if m.get("manifest_version") not in (None, MANIFEST_VERSION):
        out.append(f"manifest_version must be {MANIFEST_VERSION}")
    for key, pattern, words in (("id", ID, "3 to 40 lower case letters, numbers and hyphens"), ("version", SEMVER, "a version such as 1.2.0"),
                                ("licence", SPDX, "an SPDX licence id such as MIT")):
        if key in m and not (isinstance(m[key], str) and re.match(pattern, m[key])):
            out.append(f"{key} must be {words}")
    for key, limit in (("name", 40), ("description", 200), ("author", 60)):
        if key in m and not (isinstance(m[key], str) and 0 < len(m[key].strip()) <= limit):
            out.append(f"{key} must be text of up to {limit} characters")
    if "replaces_or_adds" in m:
        out += note_problems(m["replaces_or_adds"])
    if "icon" in m and not clean_icon(m["icon"]):
        out.append("icon must be the name of one icon in Starboard's set, such as bell or tv (see the plug-in manifest reference)")
    for key in ("homepage", "support_url"):
        if key in m and not (isinstance(m[key], str) and re.match(r"^https://\S+$", m[key])):
            out.append(f"{key} must be an https address")
    if "starboard_api" in m:
        if not isinstance(m["starboard_api"], str) or not all(re.match(r"^(>=|<=|>|<|=)?\d+(\.\d+){0,2}$", c) for c in m["starboard_api"].split()):
            out.append("starboard_api must be a range such as >=1.0 <2.0")
        elif not _range_ok(m["starboard_api"]):
            out.append(f"It needs Starboard's API {m['starboard_api']}; this Starboard has {API_VERSION}")
    perms = m.get("permissions", [])
    if not isinstance(perms, list) or any(p not in PERMISSIONS for p in perms):
        out.append("permissions must be a list from: " + ", ".join(PERMISSIONS))
        perms = []
    containers = m.get("containers", [])
    # DASH-565: a media server that comes with Starboard runs inside it, so it has no container; for now only those may ask
    # for the slot (third-party media server plug-ins, with containers, are a later step)
    slot = "slot:media-server" in perms
    if slot and not builtin:
        out.append("Only a plug-in that comes with Starboard can be the media server for now")
    least = 0 if (m.get("styles") or (slot and builtin)) else 1  # only styles, or a built-in media server, runs nothing (DASH-284, DASH-565)
    if not (isinstance(containers, list) and least <= len(containers) <= 4):
        out.append("containers must list one to four containers" + (" (none for a plug-in with only styles)" if not least else ""))
        containers = []
    styles = m.get("styles")
    if styles is not None:
        from . import plugin_styles
        if not (isinstance(styles, list) and 1 <= len(styles) <= 32):
            out.append("styles must list one to 32 styles (API 1.2; 16 before)")
        else:
            if "appearance:styles" not in perms:
                out.append("styles need the permission appearance:styles, so people are told before adding")
            ids = [st.get("id") for st in styles if isinstance(st, dict)]
            if len(ids) != len(set(ids)):
                out.append("Each style needs its own id")
            for i, st in enumerate(styles):
                for issue in plugin_styles.check_style(st, f"styles[{i}]"):
                    if issue["severity"] == "error":
                        out.append(f"{issue['where']}: {issue['what']}")
    names = set()
    for i, c in enumerate(containers or []):
        where = f"containers[{i}]"
        if not isinstance(c, dict):
            out.append(f"{where} must be an object")
            continue
        for k in sorted(set(c) - CONTAINER):
            out.append(f"{where}: unknown field {k}")
        name = c.get("name")
        if not (isinstance(name, str) and re.match(r"^[a-z0-9][a-z0-9-]{0,20}$", name)) or name in names:
            out.append(f"{where}: name must be short, lower case and different from the others")
        names.add(name)
        image = c.get("image")
        # API 1.13 (DASH-411): an app plug-in may start its image another way, such as a LinuxServer image without its
        # s6 start-up, which needs root. The image is the plug-in's own choice anyway, so this adds no reach.
        for key in ("command", "entrypoint"):
            if key in c and not (isinstance(c[key], list) and 1 <= len(c[key]) <= 20
                                 and all(isinstance(x, str) and 0 < len(x) <= 300 for x in c[key])):
                out.append(f"{where}: {key} must be a list of one to 20 words, such as [\"python3\", \"app.py\"]")
        files = c.get("files")
        if files is not None and not (isinstance(files, dict) and 1 <= len(files) <= 4 and all(
                isinstance(k, str) and re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$", k) and isinstance(v, str) and len(v) <= 16384
                for k, v in files.items())):
            out.append(f"{where}: files maps up to four file names to their text (16 KB each), written once into its data folder")
        elif files and not any(isinstance(v, str) and (v == "data" or re.match(DATA_AT, v) and v.startswith("data:")) for v in c.get("volumes") or []):
            out.append(f"{where}: files need a data folder (data or data:<path>) to be written into")
        if "build" in c and c["build"] is not True:
            out.append(f"{where}: build is true or left out")
        if c.get("build") is True:  # API 1.15 (DASH-414)
            if image != built_image(m):
                out.append(f"{where}: a container built from the zip's Dockerfile has the image {built_image(m)} (local/<id>:<version>)")
        elif image == "starboard" and not builtin:
            out.append(f"{where}: only plug-ins built into Starboard may run Starboard's own image")
        elif image != "starboard" and (not isinstance(image, str) or not (re.match(DIGEST_IMAGE, image) or (dev and re.match(TAG_IMAGE, image)))):
            out.append(f"{where}: image must be pinned by digest (name@sha256:...)" + ("" if dev else "; development mode allows a tag"))
        if "port" in c and not (isinstance(c["port"], int) and 1 <= c["port"] <= 65535):
            out.append(f"{where}: port must be a number from 1 to 65535")
        net = c.get("network", "default")
        # publish (plug-in API 1.8, 13 November 2026): a container on the VPN whose port the home network must reach,
        # such as On demand's streams for a Roku, which Jellyfin hands the stream's address to play itself.
        # API 1.13 (DASH-411): on the lan network too, for an app's own web page; that needs network:port.
        if "publish" in c and not (isinstance(c["publish"], bool) and (not c["publish"] or (net in ("vpn", "lan") and c.get("port")))):
            out.append(f"{where}: publish is true or false, and true only for a container on the vpn or lan network with a port")
        elif c.get("publish") and net == "lan" and "network:port" not in perms:
            out.append(f"{where}: publish on the lan network needs the permission network:port")
        if "host_port" in c and not (isinstance(c["host_port"], int) and not isinstance(c["host_port"], bool)
                                     and 1024 <= c["host_port"] <= 65535 and c.get("publish") and net == "lan"):
            out.append(f"{where}: host_port is a port from 1024 to 65535, only with publish on the lan network")
        tmp = c.get("tmpfs")
        if tmp is not None and not (isinstance(tmp, list) and len(tmp) <= MAX_TMPFS
                                    and all(isinstance(t, str) and re.match(INSIDE, t) and t != "/tmp" for t in tmp)):  # nosec B108: refuses /tmp, uses none
            out.append(f"{where}: tmpfs lists up to {MAX_TMPFS} folders inside the container, such as /var/run/postgresql")
        if net not in NETWORKS:
            out.append(f"{where}: network must be default, lan or vpn")
        elif NETWORKS[net] and NETWORKS[net] not in perms:
            out.append(f"{where}: network {net} needs the permission {NETWORKS[net]}")
        for v in c.get("volumes") or []:
            if v == "media:ro":
                if "media:read" not in perms:
                    out.append(f"{where}: the media folder needs the permission media:read")
            elif v in BUILTIN_VOLUMES and builtin:
                pass
            elif isinstance(v, str) and re.match(DATA_AT, v):  # API 1.13: its own data folder at the path the app expects
                at = v.split(":", 1)[1]
                if not re.match(INSIDE, at) or at in ("/", "/tmp", "/media"):  # nosec B108: a list of refused paths
                    out.append(f"{where}: {v} must mount its data at a folder of its own, such as /config")
            elif v in JELLYFIN_METADATA:  # API 1.14 (DASH-432)
                if "jellyfin:metadata" not in perms:
                    out.append(f"{where}: {v} needs the permission jellyfin:metadata")
            elif v == MEDIA_HOLDING:  # API 1.15 (DASH-406)
                if "library:holding" not in perms:
                    out.append(f"{where}: {v} needs the permission library:holding")
            elif isinstance(v, str) and re.match(r"^media/[A-Za-z0-9._-]{1,60}:ro$", v):
                pass  # API 1.13: one media folder, read only: less than media/<one folder>, so no permission
            elif v != "data" and not re.match(r"^media/[A-Za-z0-9._-]{1,60}$", str(v)):
                out.append(f"{where}: volumes may be data, data:/path, data/<folder>:/path, media:ro, media:holding or media/<one folder>, not {v}")
        env = c.get("env") or {}
        if not isinstance(env, dict) or any(not re.match(r"^[A-Za-z][A-Za-z0-9_]{0,60}$", str(k)) or not isinstance(v, (str, int, bool)) for k, v in env.items()):
            out.append(f"{where}: env must map names (letters, numbers and _, such as TZ or serverIP since API 1.13) to plain values")
        else:  # API 1.13: values Starboard fills in. Jellyfin's address and key only with jellyfin:key
            for k, v in env.items():
                for hole in FILLED.findall(str(v)) if isinstance(v, str) else []:
                    if hole.startswith("jellyfin:") and "jellyfin:key" not in perms:
                        out.append(f"{where}: env {k} uses {{{hole}}}, which needs the permission jellyfin:key")
                if isinstance(v, str) and _unknown_hole(FILLED.sub("", v)):
                    out.append(f"{where}: env {k} has a {{...}} Starboard does not know; use {{secret:name}}, {{jellyfin:url}} or {{jellyfin:key}}")
        user = c.get("user")
        if user == "media":  # API 1.12 (DASH-410): the media folder's owner, so files it adds belong to the person
            if not any(isinstance(v, str) and (re.match(r"^media/[A-Za-z0-9._-]{1,60}$", v) or v in ("jellyfin-metadata", MEDIA_HOLDING))
                       for v in c.get("volumes") or []):
                out.append(f"{where}: user media is only for a container that mounts media/<one folder>, media:holding or jellyfin-metadata")
        elif user is not None and (not isinstance(user, str) or not re.match(r"^\d{1,6}:\d{1,6}$", user) or user.split(":")[0] == "0"):
            out.append(f"{where}: user must be a non-root uid:gid such as 1000:1000, or media")
        if c.get("start", "always") not in ("always", "when_needed"):
            out.append(f"{where}: start must be always or when_needed")
    for i, s in enumerate(m.get("settings") or []):
        where = f"settings[{i}]"
        if not isinstance(s, dict) or not re.match(r"^[a-z][a-z0-9_]{0,40}$", str(s.get("key", ""))) or not s.get("label"):
            out.append(f"{where}: needs a key (lower_case) and a label")
            continue
        for k in sorted(set(s) - SETTING):
            out.append(f"{where}: unknown field {k}")
        if s.get("type") not in SETTING_TYPES:
            out.append(f"{where}: type must be one of {', '.join(SETTING_TYPES)}")
        if s.get("type") == "custom" and not re.match(r"^/[A-Za-z0-9/_-]{1,80}$", str(s.get("choices", ""))):
            out.append(f"{where}: a custom setting names the path that gives its choices")
        if "group" in s and not (isinstance(s["group"], str) and 0 < len(s["group"].strip()) <= 40):  # API 1.5
            out.append(f"{where}: group must be text of up to 40 characters")
        if s.get("type") == "choice":
            raw = s.get("choices")
            if not isinstance(raw, list) or not raw or not all(
                    isinstance(c, str) or (isinstance(c, dict) and set(c) <= {"value", "label"} and isinstance(c.get("value"), str)
                                           and isinstance(c.get("label"), str) and 0 < len(c["label"]) <= 60) for c in raw):
                out.append(f"{where}: choices must be a list of values, or of {{value, label}} with a label of up to 60 characters")
        if s.get("type") == "time" and "default" in s and not (isinstance(s["default"], str) and re.match(TIME, s["default"])):  # API 1.24
            out.append(f"settings[{i}]: default needs a time such as 22:00")
        if s.get("type") == "schedule" and "default" in s and schedule_problem(s["default"]):  # API 1.14
            out.append(f"settings[{i}]: default {schedule_problem(s['default'])}")
        if s.get("type") == "folder" and not media_mounts(m):  # API 1.3, owner's choice A (12 November 2026)
            out.append(f"{where}: a folder setting needs a container that mounts media:ro or media/<one folder>; "
                       "the folder is chosen inside it")
    if "setup_required" in m and not isinstance(m["setup_required"], bool):
        out.append("setup_required must be true or false")
    for i, s in enumerate(m.get("settings") or []):
        if isinstance(s, dict) and "required" in s and not isinstance(s["required"], bool):
            out.append(f"settings[{i}]: required must be true or false")
    notices = m.get("notices")
    if notices is not None and not (isinstance(notices, list) and all(n in NOTICES for n in notices)):
        out.append("notices must list from: " + ", ".join(NOTICES))
    events = m.get("events")
    if events is not None:
        if not (isinstance(events, list) and all(e in EVENTS for e in events)):
            out.append("events must list from: " + ", ".join(EVENTS))
        elif not containers:
            out.append("events need a container to send them to")
        else:
            for e in events:
                if EVENTS[e][0] not in perms:
                    out.append(f"the event {e} needs the permission {EVENTS[e][0]}")
    jobs = m.get("jobs")
    if jobs is not None:
        if not (isinstance(jobs, list) and len(jobs) <= 8):
            out.append("jobs must list up to eight jobs")
            jobs = []
        if jobs and not containers:
            out.append("jobs need a container to run in")
        ids = set()
        for i, j in enumerate(jobs or []):
            where = f"jobs[{i}]"
            if not isinstance(j, dict):
                out.append(f"{where} must be an object")
                continue
            for k in sorted(set(j) - JOB):
                out.append(f"{where}: unknown field {k}")
            if not re.match(r"^[a-z][a-z0-9-]{0,30}$", str(j.get("id", ""))) or j.get("id") in ids or not j.get("label"):
                out.append(f"{where}: needs its own id (lower case) and a label")
            ids.add(j.get("id"))
            if not re.match(r"^/[A-Za-z0-9/_-]{1,80}$", str(j.get("path", ""))):
                out.append(f"{where}: needs a path on the plug-in")
            when = [k for k in ("daily", "every_hours", "at_start", "schedule") if k in j]
            if len(when) != 1:
                out.append(f"{where}: give one of daily (a time such as 03:30), every_hours, at_start or schedule (a schedule setting's key)")
            elif "schedule" in j and not any(isinstance(s, dict) and s.get("key") == j["schedule"] and s.get("type") == "schedule"
                                             for s in m.get("settings") or []):
                out.append(f"{where}: schedule must name one of its settings of type schedule")
            elif "daily" in j and not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", str(j["daily"])):
                out.append(f"{where}: daily must be a time such as 03:30")
            elif "every_hours" in j and not (isinstance(j["every_hours"], int) and 1 <= j["every_hours"] <= 168):
                out.append(f"{where}: every_hours must be a whole number from 1 to 168")
            elif "at_start" in j and j["at_start"] is not True:
                out.append(f"{where}: at_start must be true")
            limit = j.get("time_limit_minutes", 10)
            if not (isinstance(limit, int) and 1 <= limit <= 120):
                out.append(f"{where}: time_limit_minutes must be from 1 to 120")
            if "quiet_hours" in j and not isinstance(j["quiet_hours"], bool):
                out.append(f"{where}: quiet_hours must be true or false")
    for i, card in enumerate(m.get("cards") or []):
        if isinstance(card, dict) and "refresh_minutes" in card and not (isinstance(card["refresh_minutes"], int) and 1 <= card["refresh_minutes"] <= 1440):
            out.append(f"cards[{i}]: refresh_minutes must be from 1 to 1440")
        if isinstance(card, dict) and "refresh_seconds" in card and not (
                isinstance(card["refresh_seconds"], int) and not isinstance(card["refresh_seconds"], bool)
                and REFRESH_MIN <= card["refresh_seconds"] <= REFRESH_MAX):  # API 1.14
            out.append(f"cards[{i}]: refresh_seconds must be a whole number from {REFRESH_MIN} to {REFRESH_MAX}")
    for i, card in enumerate(m.get("cards") or []):
        where = f"cards[{i}]"
        if not isinstance(card, dict):
            out.append(f"{where} must be an object")
            continue
        for k in sorted(set(card) - CARD):
            out.append(f"{where}: unknown field {k}")
        if card.get("type") not in CARD_TYPES or not re.match(r"^/[A-Za-z0-9/_.-]{1,80}$", str(card.get("path", ""))):
            out.append(f"{where}: needs a type ({', '.join(CARD_TYPES)}) and a path on the plug-in")
        if card.get("format") and card["format"] not in CARD_FORMATS:
            out.append(f"{where}: format must be one of {', '.join(CARD_FORMATS)}")
        for what, _fix in card_title_problems(card):  # API 1.15 (DASH-443)
            out.append(f"{where}: {what}")
    for i, a in enumerate(m.get("actions") or []):
        if not isinstance(a, dict) or set(a) - ACTION or not a.get("label") or not re.match(r"^/[A-Za-z0-9/_-]{1,80}$", str(a.get("path", ""))):
            out.append(f"actions[{i}]: needs a label and a path on the plug-in")
    if "health" in m and not re.match(r"^/[A-Za-z0-9/_.-]{0,80}$", str(m["health"])):
        out.append("health must be a path on the plug-in, such as /health")
    app = "network:port" in perms
    ceiling_mem, ceiling_cpu = (APP_CEILING_MEMORY, APP_CEILING_CPUS) if app else (CEILING_MEMORY, CEILING_CPUS)
    for name, r in (m.get("resources") or {}).items():
        if name not in names or not isinstance(r, dict) or set(r) - {"memory", "cpus", "pids"}:
            out.append(f"resources.{name}: name a container and give memory (MB) and cpus")
        elif r.get("memory", 0) > ceiling_mem or r.get("cpus", 0) > ceiling_cpu:
            out.append(f"resources.{name}: at most {ceiling_mem} MB and {ceiling_cpu:g} processor"
                       + ("" if "network:port" in perms else f" ({APP_CEILING_MEMORY} MB and {APP_CEILING_CPUS:g} for an app plug-in, with network:port)"))
        elif "pids" in r and not (isinstance(r["pids"], int) and not isinstance(r["pids"], bool) and 16 <= r["pids"] <= MAX_PIDS):
            out.append(f"resources.{name}: pids is a whole number from 16 to {MAX_PIDS} (API 1.13)")
    out += check_adopt(m.get("adopt"), containers)
    out += check_libraries(m.get("jellyfin_libraries"), containers, perms)
    out += check_changes(m.get("changes"))
    if "update" in m:  # API 1.14 (DASH-424): before and after steps, the health wait and settings migrations
        from . import plugin_update
        out += plugin_update.check(m)
    if "logo" in m:  # API 1.14 (DASH-428)
        from . import plugin_logo
        out += plugin_logo.check_entry(m["logo"])
    if m.get("needs") is not None and not (isinstance(m["needs"], list) and all(re.match(r"^[a-z0-9-]{2,30}$", str(n)) for n in m["needs"])):
        out.append("needs must list app names such as jellyfin")
    if "needs_plugins" in m and not (isinstance(m["needs_plugins"], list) and len(m["needs_plugins"]) <= 10
                                     and all(isinstance(n, str) and re.match(ID, n) for n in m["needs_plugins"])):
        out.append("needs_plugins must list up to 10 plug-in ids, such as single-sign-on (API 1.21)")
    elif m.get("id") in (m.get("needs_plugins") or []):
        out.append("needs_plugins cannot list the plug-in itself")
    if "switch" in m and not any(isinstance(x, dict) and x.get("key") == m["switch"] and x.get("type") == "switch" for x in m.get("settings") or []):
        out.append("switch must be the key of one of the plug-in's own switch settings (API 1.21)")
    if "requires" in m:  # API 1.19 (DASH-567): the system it needs, as a tag
        from . import plugin_systems
        out += plugin_systems.problems(m["requires"])
    if "starboard_tested" in m and not (isinstance(m["starboard_tested"], str) and re.match(r"^\d{1,3}\.\d{1,3}$", m["starboard_tested"])):
        out.append("starboard_tested must be the newest plug-in API version you tested with, such as 1.21 (API 1.22)")
    if "capabilities" in m:  # API 1.22 (DASH-603): named optional parts, needed or used if there
        from . import plugin_capabilities
        out += plugin_capabilities.problems(m["capabilities"])
    if "first_sign_in" in m:  # API 1.20 (DASH-590): a password made for the app and shown once
        from . import plugin_first_sign_in
        out += plugin_first_sign_in.problems(m["first_sign_in"], set(secret_names(m)),
                                             {c.get("name") for c in containers if isinstance(c, dict)})
    return out


def schedule_problem(value):
    """What is wrong with a schedule setting's value (API 1.14), in words that follow its label; None when it is
    usable. {"every": "day" | "week" | "month", "time": "03:30", "day": "sunday" (week), "date": 1 to 31 (month)}."""
    if not isinstance(value, dict) or set(value) - {"every", "time", "day", "date"}:
        return "must be a schedule: every day, week or month, and a time"
    if value.get("every") not in SCHEDULE_EVERY:
        return "must say every day, every week or every month"
    if not re.match(TIME, str(value.get("time", ""))):
        return "needs a time such as 03:30"
    if value["every"] == "week" and value.get("day") not in WEEKDAYS:
        return "needs a day of the week"
    if value["every"] == "month" and not (isinstance(value.get("date"), int) and not isinstance(value.get("date"), bool)
                                          and 1 <= value["date"] <= 31):
        return "needs a date from 1 to 31"
    return None


def schedule_clean(value):
    """Only the parts the schedule uses, so a saved weekly schedule keeps no stray date."""
    keep = {"every": value["every"], "time": value["time"]}
    if value["every"] == "week":
        keep["day"] = value["day"]
    if value["every"] == "month":
        keep["date"] = value["date"]
    return keep


def schedule_words(value):
    """A schedule in words, for System, Jobs and the install warning: "Every week on Sunday at 03:30"."""
    if schedule_problem(value):
        return "Not set yet"
    if value["every"] == "day":
        return f"Every day at {value['time']}"
    if value["every"] == "week":
        return f"Every week on {value['day'].capitalize()} at {value['time']}"
    d = value["date"]
    nth = f"{d}{'th' if 11 <= d % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')}"
    return f"Every month on the {nth} at {value['time']}" + (" (the last day in shorter months)" if d > 28 else "")


def permission_words(manifest):
    """[{permission, words, risk}] for the screen people see before install (PS1)."""
    return [{"permission": p, "words": PERMISSIONS[p][0], "risk": PERMISSIONS[p][1]} for p in manifest.get("permissions") or []]


# The install warning (owner, 12 November 2026): every permission and folder in plain words, grouped as what the
# plug-in can see, change and reach, and what it runs. Nothing here is left out to make it look safer.
SEES = {"apps:read": "Your apps and whether they answer", "downloads:read": "What is downloading",
        "media:read": "Your library: films, series, music and books", "system:read": "Processor, memory and disk use",
        "jellyfin:key": "Everything in Jellyfin: your library, the people who use it and what each one watched",
        "reelix:key": "Everything in Reelix: what you follow, your download sites and its search",
        "usenet:servers": "Your news server's address, user name and password (the Usenet account you pay for)",
        "slot:media-server": "What your media server shows: its libraries, who is watching and what was added"}
CHANGES = {"slot:media-server": "Which media server Starboard shows on the dashboard, in Library and in Activity",
           "jellyfin:key": "Anything in Jellyfin: it gets Jellyfin's API key, which can change users, libraries and settings",
           "reelix:key": "Anything in Reelix: it gets Reelix's API key, which can add, search for and remove what you follow",
           "usenet:servers": "It can download from your news server with your account, using some of its connections",
           "appearance:styles": "Starboard's appearance, through styles in Display (checked for accessibility first)",
           "alerts:send": "Alerts: it can send alerts through Starboard, to where Starboard sends its own",  # API 1.17
           # API 1.24 (DASH-572)
           "power:hold": "Heavy jobs: it can ask Starboard to hold its background jobs, scheduled backups and downloads, for example "
                         "while on battery. A hold ends by itself after at most 30 minutes unless it is renewed",
           # API 1.14 (DASH-432)
           "jellyfin:metadata": "Jellyfin's metadata folder: the posters, photos and details Jellyfin saved. It can change, "
                                "replace and remove them, and Jellyfin shows what it leaves there",
           # API 1.15 (DASH-406)
           "library:holding": "Your media folder: it can move films and series into the holding folder there "
                              "(media/.holding) and put them back. It is given the whole folder to read and change, "
                              "so add only a plug-in you trust; what it moves leaves Jellyfin until it is put back"}
REACHES = {"network:lan": "Other computers on your home network, and the internet",
           "network:port": "Its own web page is open on your home network. Anyone on your home network can open it, "
                           "at this computer's address and a port Starboard chooses",
           "network:vpn": "The internet, through your VPN connection"}
NEVER = ("Docker itself, devices such as disks and graphics cards, other apps' folders and settings, or your Starboard "
         "password. Starboard never gives a plug-in these.")


def install_warning(manifest):
    perms = [p for p in manifest.get("permissions") or [] if p in PERMISSIONS]
    containers = [c for c in manifest.get("containers") or [] if isinstance(c, dict)]
    vols = {v for c in containers for v in c.get("volumes") or []}
    see = [SEES[p] for p in perms if p in SEES]
    see += [EVENTS[e][1] for e in manifest.get("events") or [] if e in EVENTS]
    if "media:ro" in vols:
        see.append("Every file in your media folder (read only)")
    elif MEDIA_HOLDING in vols:  # API 1.15
        see.append("Every file in your media folder")
    change = []
    if containers:
        change.append("Its own folder in Starboard's data (data/plugins/" + str(manifest.get("id")) + ")")
    see += [f"Files in your media folder under {v[6:-3]} (read only)" for v in sorted(vols) if v.startswith("media/") and v.endswith(":ro")]
    change += [f"Files in your media folder under {v.split('/', 1)[1]}: it can change, replace and remove them"
               for v in sorted(vols) if v.startswith("media/") and not v.endswith(":ro")]
    if any(c.get("user") == "media" for c in containers):  # API 1.12
        change.append("It runs as the owner of your media folder, so the files it adds there are yours to move or delete")
    if "iptv" in vols:
        change.append("The Live TV folder Jellyfin reads")
    change += [CHANGES[p] for p in perms if p in CHANGES and (p != "jellyfin:metadata" or "jellyfin-metadata" in vols)
               and (p != "library:holding" or MEDIA_HOLDING in vols)]
    if "jellyfin-metadata:ro" in vols and "jellyfin-metadata" not in vols:  # API 1.14: read only, so it is seen, not changed
        see.append("Jellyfin's metadata folder: the posters, photos and details Jellyfin saved (read only)")
    if library_words(manifest) and "jellyfin:libraries" in perms:  # API 1.15 (DASH-430)
        change.append(library_words(manifest))
    if manifest.get("adopt"):
        a = manifest["adopt"]
        change.append(f"Only if you choose it: a copy of the {a.get('name', 'app')} you already have, put in its own folder "
                      "(your app's own folders are read, never changed)")
    reach = [REACHES[p] for p in perms if p in REACHES]
    if containers and not reach:
        reach.append("Only Starboard: it has no way out to your network or the internet")
    res = manifest.get("resources") or {}
    runs = []
    if builds(manifest):  # API 1.15 (DASH-414): built here, from the zip's Dockerfile
        from . import plugin_zip
        runs.append(plugin_zip.build_words(manifest))
    for c in containers:
        r = res.get(c.get("name")) or {}
        runs.append(f"{c.get('image')}" + (" (built here from the zip)" if c.get("build") is True else "") + f", up to {int(r.get('memory', DEFAULT_MEMORY))} MB of memory and "
                    f"{float(r.get('cpus', DEFAULT_CPUS)):g} of a processor core"
                    + (", started only when needed" if c.get("start") == "when_needed" else ", always running"))
    for j in manifest.get("jobs") or []:
        if isinstance(j, dict):
            if "schedule" in j:  # API 1.14: the person chooses; until then, the setting's default
                s = next((s for s in manifest.get("settings") or [] if isinstance(s, dict) and s.get("key") == j["schedule"]), {})
                start = s.get("default")
                when = "on the schedule you choose in its settings" + (f" ({schedule_words(start).lower()} to start with)"
                                                                      if start and not schedule_problem(start) else "")
                runs.append(f"A job, {j.get('label', '')}, {when}" + (", only in quiet hours" if j.get("quiet_hours") else ""))
                continue
            when = (f"daily at {j['daily']}" if "daily" in j else f"every {j['every_hours']} hours" if "every_hours" in j
                    else "each time it starts")
            runs.append(f"A job, {j.get('label', '')}, {when}" + (", only in quiet hours" if j.get("quiet_hours") else ""))
    notices = [NOTICES[n] for n in manifest.get("notices") or [] if n in NOTICES]
    if manifest.get("setup_required") or any(isinstance(s, dict) and s.get("required") for s in manifest.get("settings") or []):
        notices.append("Needs setting up before it can start")
    risk = "high" if any(PERMISSIONS[p][1] == "high" for p in perms) else "medium" if any(PERMISSIONS[p][1] == "medium" for p in perms) else "low"
    return {"risk": risk, "see": see, "change": change, "reach": reach, "runs": runs, "notices": notices, "never": NEVER,
            "buttons": [a.get("label", "") for a in manifest.get("actions") or [] if isinstance(a, dict)]}


def key_scopes(manifest):
    """The API key's scopes: exactly the read permissions approved (P8)."""
    return sorted({PERMISSIONS[p][2] for p in manifest.get("permissions") or [] if PERMISSIONS[p][2]})


def check_libraries(libs, containers, perms):
    """Problems with jellyfin_libraries (API 1.15, DASH-430): [{"name": "On demand Films", "type": "movies",
    "folder": "media/on-demand/films", "realtime_monitor": false}]. The folder is in a media folder one of its
    containers mounts (media/<one folder>, read and write or read only); real-time monitoring is off unless set."""
    if libs is None:
        return []
    if not (isinstance(libs, list) and 1 <= len(libs) <= MAX_LIBRARIES):
        return [f"jellyfin_libraries must list one to {MAX_LIBRARIES} libraries"]
    out = [] if "jellyfin:libraries" in perms else ["jellyfin_libraries needs the permission jellyfin:libraries"]
    mounted = {v.split(":")[0][6:] for c in containers if isinstance(c, dict) for v in c.get("volumes") or []
               if isinstance(v, str) and re.match(r"^media/[A-Za-z0-9._-]{1,60}(:ro)?$", v)}
    names = set()
    for i, lib in enumerate(libs):
        where = f"jellyfin_libraries[{i}]"
        if not isinstance(lib, dict):
            out.append(f"{where} must be an object")
            continue
        for k in sorted(set(lib) - JELLYFIN_LIBRARY):
            out.append(f"{where}: unknown field {k}")
        name = lib.get("name")
        if not (isinstance(name, str) and 0 < len(name.strip()) <= 40 and name == name.strip()) or str(name).lower() in names:
            out.append(f"{where}: name must be text of up to 40 characters, different from its other libraries")
        names.add(str(name).lower())
        if lib.get("type") not in LIBRARY_TYPES:
            out.append(f"{where}: type must be one of {', '.join(LIBRARY_TYPES)}")
        folder = lib.get("folder")
        parts = folder.split("/") if isinstance(folder, str) else []
        if not (len(parts) >= 2 and parts[0] == "media" and len(parts) <= 4
                and all(re.match(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,59}$", p) and p not in (".", "..") for p in parts[1:])):
            out.append(f"{where}: folder must be inside one of its media folders, such as media/on-demand/films")
        elif parts[1] not in mounted:
            out.append(f"{where}: folder must be inside a media folder one of its containers mounts (media/{parts[1]})")
        if "realtime_monitor" in lib and not isinstance(lib["realtime_monitor"], bool):
            out.append(f"{where}: realtime_monitor must be true or false")
    return out


def library_words(manifest):
    """The libraries in the words of the warning before install (API 1.15)."""
    libs = [x for x in manifest.get("jellyfin_libraries") or [] if isinstance(x, dict) and x.get("name")]
    if not libs:
        return None
    off = [x["name"] for x in libs if not x.get("realtime_monitor")]
    on = [x["name"] for x in libs if x.get("realtime_monitor")]
    words = (f"Jellyfin: Starboard adds {'the library' if len(libs) == 1 else f'{len(libs)} libraries'} "
             + " and ".join(x["name"] for x in libs) + ", for folders it fills in your media folder. ")
    if off:
        words += ("Real-time monitoring is off for " + " and ".join(off) + ", as the plug-in refreshes "
                  + ("it" if len(off) == 1 else "them") + " itself. ")
    if on:
        words += "Real-time monitoring is on for " + " and ".join(on) + ". "
    return words + "They stay in Jellyfin if you remove the plug-in"


def check_adopt(adopt, containers):
    """Problems with adopt (API 1.13, DASH-411): the app you already have, which Starboard can copy into the plug-in.
    {"app": its container name, "name": what people read, "into": one of the plug-in's containers with a data folder,
    "copy": {"/folder/in/the/app": "<folder in that data folder>", ...}}. Only copied, never moved or changed."""
    if adopt is None:
        return []
    if not isinstance(adopt, dict) or set(adopt) - {"app", "name", "into", "copy", "stop"}:
        return ["adopt must be an object with app, name, into and copy"]
    out = []
    if not re.match(r"^[a-z0-9][a-z0-9_.-]{1,40}$", str(adopt.get("app", ""))):
        out.append("adopt.app must be the container name of the app people already have, such as tdarr")
    if not (isinstance(adopt.get("name"), str) and 0 < len(adopt["name"]) <= 40):
        out.append("adopt.name must be text of up to 40 characters")
    into = next((c for c in containers or [] if isinstance(c, dict) and c.get("name") == adopt.get("into")), None)
    if not into or not any(isinstance(v, str) and (v == "data" or re.match(DATA_AT, v)) for v in into.get("volumes") or []):
        out.append("adopt.into must name one of its containers that has a data folder")
    copy = adopt.get("copy")
    if not (isinstance(copy, dict) and 1 <= len(copy) <= 8 and all(
            isinstance(k, str) and re.match(INSIDE, k) and isinstance(v, str) and re.match(r"^[a-z0-9][a-z0-9._-]{0,39}$", v)
            for k, v in copy.items())):
        out.append("adopt.copy must map one to eight folders in the app to folders in the plug-in's data folder")
    if "stop" in adopt and not isinstance(adopt["stop"], bool):
        out.append("adopt.stop must be true or false")
    return out


def _fill(value, extra):
    """An env value with Starboard's holes filled (API 1.13): a secret made for this plug-in, or Jellyfin's address
    and key. A hole Starboard has nothing for yet is left empty, so nothing made up reaches the app."""
    def one(m):
        hole = m.group(1)
        if hole.startswith("secret:"):
            return str((extra.get("secrets") or {}).get(hole[7:], ""))
        jf = extra.get("jellyfin") or {}
        return str(jf.get("url" if hole == "jellyfin:url" else "api_key", ""))
    return FILLED.sub(one, value) if isinstance(value, str) else value


def published_lan(manifest):
    """The containers whose web page is opened on the home network (API 1.13): [(container, its port, preferred)]."""
    return [(c["name"], int(c["port"]), int(c.get("host_port") or c["port"])) for c in manifest.get("containers") or []
            if isinstance(c, dict) and c.get("publish") is True and c.get("network") == "lan" and isinstance(c.get("port"), int)]


def secret_names(manifest):
    """The secrets Starboard makes for a plug-in (API 1.13): every {secret:name} in its env."""
    out = set()
    for c in manifest.get("containers") or []:
        values = [*(c.get("env") or {}).values(), *(c.get("files") or {}).values()] if isinstance(c, dict) else []
        for v in values:
            out |= {h[7:] for h in FILLED.findall(str(v)) if h.startswith("secret:")}
    return sorted(out)


def compose(manifest, plugin_dir, media_dir, host=None, media_user=None, extra=None):
    """The Compose file Starboard writes for a plug-in, with the hardened defaults the plug-in cannot change (PS2 to
    PS5). `plugin_dir` is data/plugins/<id> on the host; `media_dir` the media folder. `host`, for a plug-in built
    into Starboard: {"image": Starboard's own image, "user": "uid:gid", "iptv": the Live TV folder}. `media_user`:
    the media folder's owner as "uid:gid", for a container with user "media" (API 1.12); 1000:1000 when unknown. `extra` (API 1.13):
    {"ports": {container: port on the home network}, "secrets": {name: value}, "jellyfin": {"url", "api_key"}}; and
    (API 1.14) "jellyfin_metadata": Jellyfin's metadata folder on the computer, for a container that mounts it."""
    host = host or {}
    extra = extra or {}
    problems = check(manifest, dev=True, builtin=bool(host))
    if problems:
        raise ValueError("; ".join(problems))
    pid = manifest["id"]
    if not manifest.get("containers"):
        return ""  # nothing to run: a plug-in with only styles
    res = manifest.get("resources") or {}
    lines = [f"# Written by Starboard for the plug-in {manifest['name']} {manifest['version']}. Starboard rewrites it;",
             "# change the plug-in's settings in Starboard instead.", "services:"]
    networks = set()
    for c in manifest["containers"]:
        name = f"plugin-{pid}-{c['name']}"
        r = res.get(c["name"]) or {}
        image = host.get("image") if c["image"] == "starboard" else c["image"]
        if not image:
            raise ValueError("Starboard could not find its own image for this plug-in")
        user = c.get("user") or (host.get("user") if c["image"] == "starboard" else None) or "10001:10001"
        if user == "media":
            user = media_user if media_user and re.match(r"^[1-9]\d{0,5}:\d{1,6}$", media_user) else "1000:1000"
        lines += [f"  {name}:", f"    image: {json.dumps(image)}", f"    container_name: {name}", "    restart: unless-stopped",
                  "    read_only: true", "    tmpfs:", "      - /tmp:size=64m",
                  # API 1.13: each in memory and owned by the container's own user, as an app such as PostgreSQL
                  # expects; nothing in it outlives a restart. Docker's tmpfs runs no programs, except for an image
                  # with s6, which starts its programs from /run, so a /run of its own may run them
                  *[f"      - {json.dumps(t + ':size=64m,mode=0700,uid=' + user.split(':')[0] + ',gid=' + user.split(':')[1] + (',exec' if t == '/run' else ''))}"
                    for t in c.get("tmpfs") or []], "    cap_drop:", "      - ALL",
                  "    security_opt:", "      - no-new-privileges:true", f"    user: {json.dumps(user)}",
                  f"    pids_limit: {int(r.get('pids', 64))}", f"    mem_limit: {int(r.get('memory', DEFAULT_MEMORY))}m", f"    cpus: {float(r.get('cpus', DEFAULT_CPUS))}",
                  *app_logs.compose_logging(),  # its log capped as the apps' are (DASH-451)
                  "    labels:", f"      starboard.plugin: {json.dumps(pid)}"]
        if c.get("start") == "when_needed":
            lines.append(f"      starboard.idle_stop_minutes: \"{int(c.get('idle_stop_minutes') or 15)}\"")
        if c.get("entrypoint"):
            lines.append(f"    entrypoint: {json.dumps(c['entrypoint'])}")
        if c.get("command"):
            lines.append(f"    command: {json.dumps(c['command'])}")
        if c["image"] == "starboard":  # Starboard's own image checks Starboard's port: a built-in plug-in checks its own
            path = manifest.get("health") or "/"
            lines += ["    healthcheck:", f'      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:{int(c.get("port") or 80)}{path}"]',
                      "      interval: 60s", "      timeout: 5s", "      retries: 3"]
        net = c.get("network", "default")
        if net == "lan":  # the computer itself, for apps Starboard reaches at 127.0.0.1 (Jellyfin's key, DASH-285)
            lines += ["    extra_hosts:", '      - "host.docker.internal:host-gateway"']
        if net == "vpn":  # Gluetun runs in the apps' own Compose project, so the plug-in joins its container by name
            lines += ['    network_mode: "container:gluetun"']
        else:
            lines += ["    networks:", f"      - plugin-{pid}"] + (["      - lan"] if net == "lan" else [])
            networks.add(net)
        port_out = (extra.get("ports") or {}).get(c["name"])
        if net == "lan" and c.get("publish") and port_out:  # API 1.13: its web page on the home network
            lines += ["    ports:", f"      - {json.dumps(str(int(port_out)) + ':' + str(int(c['port'])))}"]
        vols = []
        for v in c.get("volumes") or []:
            if v == "data":
                vols.append(f"{plugin_dir}/data/{c['name']}:/data")
            elif re.match(DATA_AT, v):  # API 1.13: data:/config, or data/<folder>:/app/server for an app with several
                sub, at = v.split(":", 1)
                vols.append(f"{plugin_dir}/data/{c['name']}{sub[4:]}:{at}")
            elif v == "media:ro":
                vols.append(f"{media_dir}:/media:ro")
            elif v == MEDIA_HOLDING:  # API 1.15 (DASH-406): read and write, only with library:holding (check() made sure)
                vols.append(f"{media_dir}:/media")
            elif v == "iptv":
                if not host.get("iptv"):
                    raise ValueError("The installer gave Starboard no Live TV folder (./install.sh asks)")
                vols.append(f"{host['iptv']}:/iptv")
            elif v in JELLYFIN_METADATA:  # API 1.14 (DASH-432): only with jellyfin:metadata, which check() made sure of
                where_md = extra.get("jellyfin_metadata")
                if not where_md:
                    raise ValueError("Starboard could not find Jellyfin's metadata folder. Install Jellyfin with Install apps first")
                vols.append(f"{where_md}:/metadata" + (":ro" if v.endswith(":ro") else ""))
            elif v.endswith(":ro"):  # API 1.13: one media folder, read only
                vols.append(f"{media_dir}/{v[6:-3]}:/media/{v[6:-3]}:ro")
            else:
                vols.append(f"{media_dir}/{v.split('/', 1)[1]}:/{v}")
        # settings.json, its own API key (P8) and, with jellyfin:key, Jellyfin's address and key: one folder, so a
        # saved setting reaches it at once and any container user can read it (DASH-357). Owner-only on the host.
        vols.append(f"{plugin_dir}/run:/run/starboard:ro")
        lines += ["    volumes:"] + [f"      - {json.dumps(v)}" for v in vols]
        env = {**({"TZ": host["tz"]} if host.get("tz") else {}), **{k: str(_fill(v, extra)) for k, v in (c.get("env") or {}).items()}, "STARBOARD_API": api_address(c.get("network", "default")),
               "STARBOARD_API_KEY_FILE": "/run/starboard/key",
               # DASH-482: on its own internal network a plug-in has no route to Starboard's port, so it calls the API
               # through the socket Starboard keeps in its run folder (plugin_socket); STARBOARD_API gives the paths
               "STARBOARD_API_SOCKET": API_SOCKET}
        # Its own address on the home network (owner, 19 November 2026): a plug-in that gives Jellyfin or a device an
        # address, such as Create your own TV channel, needs no one to open its page first to learn it.
        if net == "lan" and c.get("publish") and port_out and extra.get("home_ip"):
            env["STARBOARD_HOME_ADDRESS"] = f"http://{extra['home_ip']}:{int(port_out)}"
        lines += ["    environment:"] + [f"      {k}: {json.dumps(v)}" for k, v in sorted(env.items())]
    if networks:
        # Its own network, which reaches nothing outside (PS5). Starboard runs on the computer's own network and
        # cannot join it, so the plug-in calls the API through STARBOARD_API_SOCKET instead (DASH-482).
        lines += ["networks:", f"  plugin-{pid}:", f"    name: plugin-{pid}", "    internal: true"]
        if "lan" in networks:
            lines += ["  lan:", "    driver: bridge"]
    return "\n".join(lines) + "\n"



API_SOCKET = "/run/starboard/api.sock"  # DASH-482: Starboard's API for every plug-in container, whatever its network


def api_address(network):
    """Where a plug-in reaches Starboard's API over HTTP. Starboard runs on the computer's own network, so it cannot
    join a plug-in's network: a plug-in on the home network (network:lan) reaches it as host.docker.internal at
    Starboard's own port (STARBOARD_PORT, 8095 unless the owner chose another). On its own internal network or the VPN
    there is no route to Starboard, so the plug-in sends its requests to STARBOARD_API_SOCKET (DASH-482) and takes
    only the path from this address, which stays as it was for older plug-ins."""
    if network == "lan":
        return f"http://host.docker.internal:{int(os.environ.get('STARBOARD_PORT') or 8095)}/api/v1/"
    return "http://starboard:8095/api/v1/"

def check_changes(changes):
    """Problems with the optional changes list (API 1.10), as plain sentences."""
    if changes is None:
        return []
    if not (isinstance(changes, list) and 1 <= len(changes) <= 20):
        return ["changes must list one to 20 versions, newest first"]
    out, seen = [], set()
    for i, v in enumerate(changes):
        where = f"changes[{i}]"
        if not isinstance(v, dict):
            out.append(f"{where} must be an object")
            continue
        for k in sorted(set(v) - CHANGE):
            out.append(f"{where}: unknown field {k}")
        if not (isinstance(v.get("version"), str) and re.match(SEMVER, v["version"])) or v.get("version") in seen:
            out.append(f"{where}: needs its own version, such as 1.2.0")
        seen.add(v.get("version"))
        if "date" in v and not (isinstance(v["date"], str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v["date"])):
            out.append(f"{where}: date must be a date such as 2026-11-13")
        if not any(t in v for t in CHANGE_TYPES):
            out.append(f"{where}: needs at least one of {', '.join(CHANGE_TYPES)}")
        for t in CHANGE_TYPES:
            if t in v and not (isinstance(v[t], list) and 1 <= len(v[t]) <= 20
                               and all(isinstance(x, str) and 0 < len(x.strip()) <= 300 for x in v[t])):
                out.append(f"{where}: {t} must list one to 20 lines of up to 300 characters")
    return out


def write_schema(path):
    """The manifest's JSON Schema (P1), for authors and their tools; check() is what Starboard itself runs."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://starboard.invalid/plugin-manifest-1.json",
        "title": "Starboard plug-in manifest, version 1", "type": "object", "additionalProperties": False,
        "$defs": {"colours": {"type": "object", "additionalProperties": False,
                              "required": ["bg", "header", "surface", "surface_raised", "surface_sunken", "text", "text_muted", "border",
                                           "divider", "accent", "accent_text", "accent_soft", "focus"],
                              "patternProperties": {"^[a-z_]+$": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}}},
                 # API 1.14 (DASH-432): every day, every week on a day, or every month on a date, at a time
                 "schedule": {"type": "object", "additionalProperties": False, "required": ["every", "time"],
                              "properties": {"every": {"enum": list(SCHEDULE_EVERY)}, "time": {"type": "string", "pattern": TIME},
                                             "day": {"enum": list(WEEKDAYS)}, "date": {"type": "integer", "minimum": 1, "maximum": 31}},
                              "allOf": [{"if": {"properties": {"every": {"const": "week"}}}, "then": {"required": ["day"]}},
                                        {"if": {"properties": {"every": {"const": "month"}}}, "then": {"required": ["date"]}}]},
                 # API 1.14 (DASH-424): a step Starboard calls before or after an update
                 "update_step": {"type": "object", "additionalProperties": False, "required": ["path"],
                                 "properties": {"path": {"type": "string", "pattern": "^/[A-Za-z0-9/_-]{1,80}$"},
                                                "time_limit_seconds": {"type": "integer", "minimum": 5, "maximum": 300}}}},
        "required": sorted(REQUIRED),
        "properties": {
            "manifest_version": {"const": 1}, "id": {"type": "string", "pattern": ID}, "name": {"type": "string", "maxLength": 40},
            "version": {"type": "string", "pattern": SEMVER}, "description": {"type": "string", "maxLength": 200},
            "replaces_or_adds": {"type": "string", "minLength": 1, "maxLength": NOTE_MAX, "pattern": "^[^<>`\\r\\n]+$"},
            "icon": {"type": "string", "pattern": "^[a-z0-9-]+$"},
            "author": {"type": "string", "maxLength": 60}, "licence": {"type": "string", "pattern": SPDX},
            "homepage": {"type": "string", "pattern": "^https://"}, "support_url": {"type": "string", "pattern": "^https://"},
            "starboard_api": {"type": "string"}, "health": {"type": "string", "pattern": "^/"},
            "permissions": {"type": "array", "items": {"enum": sorted(PERMISSIONS)}, "uniqueItems": True},
            "needs": {"type": "array", "items": {"type": "string"}},
            # API 1.19 (DASH-567): the system it needs: "jellyfin", "jellyfin only", "plex or emby", "reelix"
            "needs_plugins": {"type": "array", "maxItems": 10, "items": {"type": "string"}},
            "switch": {"type": "string"},
            "requires": {"type": "array", "maxItems": 4, "items": {"type": "string", "pattern": r"^[a-z][a-z0-9-]{1,29}( or [a-z][a-z0-9-]{1,29}){0,5}( only)?$"}},
            # API 1.22 (DASH-603): the newest plug-in API version it was tested with, and optional parts it needs or uses by name
            "starboard_tested": {"type": "string", "pattern": r"^\d{1,3}\.\d{1,3}$"},
            "capabilities": {"type": "object", "additionalProperties": False,
                             "properties": {"needs": {"type": "array", "maxItems": 12, "items": {"type": "string", "pattern": r"^[a-z][a-z0-9-]{1,39}$"}},
                                            "uses": {"type": "array", "maxItems": 12, "items": {"type": "string", "pattern": r"^[a-z][a-z0-9-]{1,39}$"}}}},
            # API 1.20 (DASH-590): a password Starboard made for the app, shown once on the plug-in's page
            "first_sign_in": {"type": "object", "additionalProperties": False, "required": ["user", "secret", "ready_file"],
                              "properties": {"user": {"type": "string", "maxLength": 40}, "secret": {"type": "string", "pattern": r"^[a-z][a-z0-9_]{0,29}$"},
                                             "ready_file": {"type": "string", "pattern": r"^[a-z0-9][a-z0-9-]{0,20}/[A-Za-z0-9][A-Za-z0-9._-]{0,60}$"}}},
            "styles": {"type": "array", "minItems": 1, "maxItems": 32, "items": {
                "type": "object", "additionalProperties": False, "required": ["id", "name", "light", "dark"],
                "properties": {"id": {"type": "string"}, "name": {"type": "string", "maxLength": 30}, "description": {"type": "string", "maxLength": 120},
                               "radius": {"type": "integer", "minimum": 0, "maximum": 24},
                               "font": {"enum": ["hyperlegible", "system", "rounded", "serif", "mono"]},
                               "shadow": {"enum": ["none", "soft", "strong", "layered", "glow", "clay", "hairline"]},
                               # API 1.2 (12 November 2026): a full reskin
                               "card_style": {"enum": ["flat", "outlined", "elevated", "tonal"]},
                               "button_fill": {"enum": ["solid", "outline", "soft", "ghost"]}, "border_width": {"enum": [1, 2, 3]},
                               "tab_style": {"enum": ["underline", "pill", "boxed"]}, "header_style": {"enum": ["solid", "blurred", "accent_bar", "rule"]},
                               "rail_style": {"enum": ["solid", "floating", "tinted"]}, "chip_style": {"enum": ["soft", "outline"]},
                               "heading_case": {"enum": ["none", "labels"]}, "heading_tracking": {"enum": ["tight", "normal", "wide"]},
                               "primary_gradient": {"type": "boolean"},
                               "heading_font": {"enum": ["hyperlegible", "system", "rounded", "serif", "mono"]},
                               "heading_weight": {"enum": [600, 700, 800]}, "focus_width": {"type": "integer", "minimum": 3, "maximum": 5},
                               "gradient": {"enum": ["none", "linear", "radial", "mesh"]}, "gradient_angle": {"type": "integer", "minimum": 0, "maximum": 360},
                               "texture": {"enum": ["none", "dots", "grid", "lines", "grain"]}, "glass": {"type": "boolean"}, "rounded_controls": {"type": "boolean"},
                               "light": {"$ref": "#/$defs/colours"}, "dark": {"$ref": "#/$defs/colours"}}}},
            "containers": {"type": "array", "minItems": 0, "maxItems": 4, "items": {
                "type": "object", "additionalProperties": False, "required": ["name", "image"],
                "properties": {"name": {"type": "string"}, "image": {"type": "string", "pattern": DIGEST_IMAGE + "|^local/[a-z0-9-]{3,40}:[0-9A-Za-z.+-]{1,64}$"},
                               "build": {"const": True},  # API 1.15 (DASH-414): built from the zip's Dockerfile
                               "port": {"type": "integer", "minimum": 1, "maximum": 65535}, "network": {"enum": sorted(NETWORKS)}, "publish": {"type": "boolean"},
                               "volumes": {"type": "array", "items": {"type": "string"}}, "env": {"type": "object"},
                               "start": {"enum": ["always", "when_needed"]}, "idle_stop_minutes": {"type": "integer"},
                               "user": {"type": "string", "pattern": r"^([1-9]\d{0,5}:\d{1,6}|media)$"},
                               # API 1.13 (DASH-411)
                               "host_port": {"type": "integer", "minimum": 1024, "maximum": 65535},
                               "tmpfs": {"type": "array", "maxItems": MAX_TMPFS, "items": {"type": "string", "pattern": "^/"}},
                               "command": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string"}},
                               "entrypoint": {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string"}},
                               "files": {"type": "object", "minProperties": 1, "maxProperties": 4,
                                         "additionalProperties": {"type": "string", "maxLength": 16384}}}}},
            "resources": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": False,
                                                                      "properties": {"memory": {"type": "integer", "maximum": APP_CEILING_MEMORY},
                                                                                     "cpus": {"type": "number", "maximum": APP_CEILING_CPUS},
                                                                                     "pids": {"type": "integer", "minimum": 16, "maximum": MAX_PIDS}}}},
            # API 1.15 (DASH-430): Jellyfin libraries the plug-in fills
            "jellyfin_libraries": {"type": "array", "minItems": 1, "maxItems": MAX_LIBRARIES, "items": {
                "type": "object", "additionalProperties": False, "required": ["name", "type", "folder"],
                "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 40}, "type": {"enum": sorted(LIBRARY_TYPES)},
                               "folder": {"type": "string", "pattern": "^media/[A-Za-z0-9][A-Za-z0-9._ -]{0,59}(/[A-Za-z0-9][A-Za-z0-9._ -]{0,59}){0,2}$"},
                               "realtime_monitor": {"type": "boolean"}}}},
            # API 1.13 (DASH-411)
            "adopt": {"type": "object", "additionalProperties": False, "required": ["app", "name", "into", "copy"],
                      "properties": {"app": {"type": "string"}, "name": {"type": "string", "maxLength": 40}, "into": {"type": "string"},
                                     "copy": {"type": "object", "minProperties": 1, "maxProperties": 8,
                                              "additionalProperties": {"type": "string"}}, "stop": {"type": "boolean"}}},
            "settings": {"type": "array", "items": {"type": "object", "required": ["key", "label", "type"],
                                                    # API 1.14: a schedule setting's default is a schedule
                                                    "if": {"properties": {"type": {"const": "schedule"}}},
                                                    "then": {"properties": {"default": {"$ref": "#/$defs/schedule"}}},
                                                    "properties": {"type": {"enum": list(SETTING_TYPES)}, "required": {"type": "boolean"},
                                                                   "group": {"type": "string", "maxLength": 40},

                                                                   "choices": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"anyOf": [
                                                                       {"type": "string"}, {"type": "object", "required": ["value", "label"], "additionalProperties": False,
                                                                        "properties": {"value": {"type": "string"}, "label": {"type": "string", "maxLength": 60}}}]}}]}}}},
            "cards": {"type": "array", "items": {"type": "object", "required": ["type", "path"],
                                                 "properties": {"type": {"enum": list(CARD_TYPES)}, "format": {"enum": list(CARD_FORMATS)},
                                                                "refresh_minutes": {"type": "integer", "minimum": 1, "maximum": 1440},
                                                                "refresh_seconds": {"type": "integer", "minimum": REFRESH_MIN, "maximum": REFRESH_MAX},
                                                                # API 1.15 (DASH-443): a title for each size, on one line
                                                                "titles": {"type": "object", "additionalProperties": False, "minProperties": 1,
                                                                           "properties": {k: {"type": "string", "minLength": 1, "maxLength": v}
                                                                                          for k, v in CARD_TITLE_MAX.items()}}}}},
            # API 1.4 (DASH-330)
            "setup_required": {"type": "boolean"},
            "notices": {"type": "array", "items": {"enum": sorted(NOTICES)}, "uniqueItems": True},
            "events": {"type": "array", "items": {"enum": sorted(EVENTS)}, "uniqueItems": True},
            "jobs": {"type": "array", "maxItems": 8, "items": {
                "type": "object", "additionalProperties": False, "required": ["id", "label", "path"],
                "properties": {"id": {"type": "string", "pattern": "^[a-z][a-z0-9-]{0,30}$"}, "label": {"type": "string", "maxLength": 60},
                               "path": {"type": "string", "pattern": "^/"}, "daily": {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"},
                               "every_hours": {"type": "integer", "minimum": 1, "maximum": 168}, "at_start": {"const": True},
                               "schedule": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,40}$"},  # API 1.14: a schedule setting's key
                               "time_limit_minutes": {"type": "integer", "minimum": 1, "maximum": 120}, "quiet_hours": {"type": "boolean"}}}},
            "actions": {"type": "array", "items": {"type": "object", "required": ["label", "path"]}},
            # API 1.14 (DASH-428): a small logo beside the manifest, checked and cleaned by Starboard
            "logo": {"type": "object", "additionalProperties": False, "required": ["file", "alt"],
                     "properties": {"file": {"type": "string", "pattern": "^(?:[a-z0-9][a-z0-9_-]{0,29}/)?[A-Za-z0-9][A-Za-z0-9._-]{0,60}\\.(svg|png)$"},
                                    "alt": {"type": "string", "minLength": 3, "maxLength": 80}}},
            # API 1.14 (DASH-424): update tools
            "update": {"type": "object", "additionalProperties": False, "properties": {
                "before": {"$ref": "#/$defs/update_step"}, "after": {"$ref": "#/$defs/update_step"},
                "health_wait_seconds": {"type": "integer", "minimum": 10, "maximum": 600},
                "migrations": {"type": "array", "minItems": 1, "maxItems": 20, "items": {
                    "type": "object", "additionalProperties": False, "required": ["version"],
                    "properties": {"version": {"type": "string", "pattern": SEMVER},
                                   "rename": {"type": "object", "maxProperties": 20, "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,40}$"},
                                              "additionalProperties": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,40}$"}},
                                   "remove": {"type": "array", "maxItems": 20, "items": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,40}$"}},
                                   "defaults": {"type": "object", "maxProperties": 20, "propertyNames": {"pattern": "^[a-z][a-z0-9_]{0,40}$"}}}}}}},
            # API 1.10 (DASH-393)
            "changes": {"type": "array", "minItems": 1, "maxItems": 20, "items": {
                "type": "object", "additionalProperties": False, "required": ["version"],
                "properties": {"version": {"type": "string", "pattern": SEMVER}, "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                               **{t: {"type": "array", "minItems": 1, "maxItems": 20, "items": {"type": "string", "minLength": 1, "maxLength": 300}}
                                  for t in CHANGE_TYPES}}}},
        },
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=1)
        f.write("\n")


if __name__ == "__main__":
    write_schema(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin-manifest.schema.json"))


def choices(setting):
    """A choice setting's choices as [(value, words)]: a plain value is its own words (API 1.5 added labels)."""
    out = []
    for c in setting.get("choices") or []:
        if isinstance(c, dict):
            out.append((str(c.get("value", "")), str(c.get("label") or c.get("value", ""))))
        else:
            out.append((str(c), str(c)))
    return out


def media_mounts(manifest):
    """The media folders a plug-in mounts, as it sees them: /media (read only) or /media/<one folder>."""
    out = []
    for c in (manifest or {}).get("containers") or []:
        for v in c.get("volumes") or []:
            if v in ("media:ro", MEDIA_HOLDING):
                out.append("/media")
            elif isinstance(v, str) and re.match(r"^media/[A-Za-z0-9._-]{1,60}(:ro)?$", v):
                out.append("/" + v.removesuffix(":ro"))
    return sorted(set(out))
