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

MANIFEST_VERSION = 1
API_VERSION = "1.12.0"  # 1.12 (13 November 2026, DASH-410): a container may run as the media folder's owner (user "media") to add files in the media folders it mounts, which Starboard makes for it; a custom screen's item may have a link (opened in a new tab) and its own words for its state (state_label), and its add box may take only a file (file_only)  # 1.11 (13 November 2026, DASH-401 and DASH-402): four more events (request.available, download.failed, disk.nearly_full, update.available) for a notifications plug-in, and readonly on a custom screen with folds, so a table of figures has no tick boxes or Activate buttons  # 1.10 (13 November 2026, DASH-393): optional changes, the plug-in's own changelog by version (Added, Changed, Fixed and the rest), shown as What is new on its State after an update or a Roll back; older plug-ins without it still work  # 1.9 (13 November 2026): a container on the vpn network may set publish, so its port goes on Gluetun for the home network  # 1.8 (13 November 2026, DASH-359): a custom screen may fold its items into sections with a table each (layout folds, columns, filters, cells), select several (bulk_ids), add a guide to an item (attach, detach), show notices with progress; a card may be a guide  # 1.7 (13 November 2026, DASH-361): a custom screen may have sub menus, items and bulk switches placed in them  # 1.6 (12 November 2026, owner): permissions reelix:key and usenet:servers, handed over as run/reelix.json and run/usenet.json  # 1.5 (12 November 2026, DASH-307): settings may have a group, each its own section; a choice may be {value, label}  # 1.4 (12 November 2026, DASH-330): required settings and setup_required, notices, events, jobs, card refresh_minutes  # 1.3 (12 November 2026): a folder setting is a folder inside the media folders the plug-in mounts, chosen with the location picker  # 1.2 (12 November 2026): styles may also set card, button, border, tab, header, side menu and chip styles  # 1.1 (11 November 2026): styles may set more colours, heading font and weight, focus width
ID = r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$"
SEMVER = r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$"
DIGEST_IMAGE = r"^[a-z0-9.-]+(:\d+)?(/[a-z0-9._-]+)+@sha256:[0-9a-f]{64}$"
TAG_IMAGE = r"^[a-z0-9.-]+(:\d+)?(/[a-z0-9._-]+)+(:[A-Za-z0-9._-]{1,128})?$"
SPDX = r"^[A-Za-z0-9.+-]{2,40}$"

# What each permission means, in the words people read before install (PS1), and its risk.
PERMISSIONS = {
    "apps:read": ("See your apps and whether they answer", "low", "apps"),
    "downloads:read": ("See what is downloading", "low", "downloads"),
    "media:read": ("See your films, series and books (the media folder, read only, and the library)", "medium", "media"),
    "system:read": ("See processor, memory and disks", "low", "system"),
    "network:lan": ("Reach other computers on your home network", "medium", None),
    "network:vpn": ("Run inside your VPN connection", "medium", None),
    "jellyfin:key": ("Use Jellyfin's API key, kept by Starboard", "high", None),
    "reelix:key": ("Use Reelix's API key, kept by Starboard", "high", None),  # API 1.6
    "usenet:servers": ("Use your news server's address and sign-in, from NZBGet or SABnzbd", "high", None),  # API 1.6
    "appearance:styles": ("Add styles to Display: colours, corners, a font and shadows, checked for accessibility", "low", None),
}
NETWORKS = {"default": None, "lan": "network:lan", "vpn": "network:vpn"}
SETTING_TYPES = ("text", "number", "switch", "choice", "address", "secret", "folder", "list", "custom")
CARD_TYPES = ("stat", "list", "status", "guide")  # guide: what is on now (API 1.8, DASH-359)
CARD_FORMATS = ("number", "bytes", "percent", "duration", "date")
DEFAULT_MEMORY, DEFAULT_CPUS, CEILING_MEMORY, CEILING_CPUS = 128, 0.25, 512, 1.0

TOP = {"manifest_version", "id", "name", "version", "description", "author", "licence", "homepage", "support_url",
       "starboard_api", "containers", "permissions", "resources", "settings", "cards", "health", "actions", "needs", "styles",
       "setup_required", "notices", "events", "jobs", "changes"}
REQUIRED = TOP - {"resources", "settings", "cards", "health", "actions", "needs", "styles", "containers",
                  "setup_required", "notices", "events", "jobs", "changes"}
CONTAINER = {"name", "image", "port", "network", "volumes", "env", "start", "idle_stop_minutes", "user", "command", "publish"}
# Plug-ins that ship inside Starboard (plugins/<id>/ in its own folder): they may run Starboard's own image
# ("image": "starboard") with a command, and Live TV may use the Live TV folder the installer gave ("iptv").
BUILTIN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins")
BUILTIN_VOLUMES = {"iptv"}
SETTING = {"key", "label", "type", "hint", "default", "min", "max", "unit", "choices", "restart", "item", "required", "group"}
CARD = {"id", "title", "type", "path", "format", "label", "example", "refresh_minutes"}
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
          "update.available": ("apps:read", "When an update is ready for Starboard, an app or a plug-in")}
JOB = {"id", "label", "path", "daily", "every_hours", "at_start", "time_limit_minutes", "quiet_hours"}
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
    least = 0 if m.get("styles") else 1  # a plug-in with only styles runs nothing (DASH-284)
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
                out.append("styles need the permission appearance:styles, so people see it before adding")
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
        if "command" in c and not (builtin and isinstance(c["command"], list) and all(isinstance(x, str) for x in c["command"])):
            out.append(f"{where}: only plug-ins built into Starboard may set a command")
        if image == "starboard" and not builtin:
            out.append(f"{where}: only plug-ins built into Starboard may run Starboard's own image")
        elif image != "starboard" and (not isinstance(image, str) or not (re.match(DIGEST_IMAGE, image) or (dev and re.match(TAG_IMAGE, image)))):
            out.append(f"{where}: image must be pinned by digest (name@sha256:...)" + ("" if dev else "; development mode allows a tag"))
        if "port" in c and not (isinstance(c["port"], int) and 1 <= c["port"] <= 65535):
            out.append(f"{where}: port must be a number from 1 to 65535")
        net = c.get("network", "default")
        # publish (plug-in API 1.8, 13 November 2026): a container on the VPN whose port the home network must reach,
        # such as On demand's streams for a Roku, which Jellyfin hands the stream's address to play itself.
        if "publish" in c and not (isinstance(c["publish"], bool) and (not c["publish"] or (net == "vpn" and c.get("port")))):
            out.append(f"{where}: publish is true or false, and true only for a container on the vpn network with a port")
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
            elif v != "data" and not re.match(r"^media/[A-Za-z0-9._-]{1,60}$", str(v)):
                out.append(f"{where}: volumes may be data, media:ro or media/<one folder>, not {v}")
        env = c.get("env") or {}
        if not isinstance(env, dict) or any(not re.match(r"^[A-Z][A-Z0-9_]{0,60}$", str(k)) or not isinstance(v, (str, int, bool)) for k, v in env.items()):
            out.append(f"{where}: env must map UPPER_CASE names to plain values")
        user = c.get("user")
        if user == "media":  # API 1.12 (DASH-410): the media folder's owner, so files it adds belong to the person
            if not any(isinstance(v, str) and re.match(r"^media/[A-Za-z0-9._-]{1,60}$", v) for v in c.get("volumes") or []):
                out.append(f"{where}: user media is only for a container that mounts media/<one folder>")
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
            when = [k for k in ("daily", "every_hours", "at_start") if k in j]
            if len(when) != 1:
                out.append(f"{where}: give one of daily (a time such as 03:30), every_hours or at_start")
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
    for i, a in enumerate(m.get("actions") or []):
        if not isinstance(a, dict) or set(a) - ACTION or not a.get("label") or not re.match(r"^/[A-Za-z0-9/_-]{1,80}$", str(a.get("path", ""))):
            out.append(f"actions[{i}]: needs a label and a path on the plug-in")
    if "health" in m and not re.match(r"^/[A-Za-z0-9/_.-]{0,80}$", str(m["health"])):
        out.append("health must be a path on the plug-in, such as /health")
    for name, r in (m.get("resources") or {}).items():
        if name not in names or not isinstance(r, dict) or set(r) - {"memory", "cpus"}:
            out.append(f"resources.{name}: name a container and give memory (MB) and cpus")
        elif r.get("memory", 0) > CEILING_MEMORY or r.get("cpus", 0) > CEILING_CPUS:
            out.append(f"resources.{name}: at most {CEILING_MEMORY} MB and {CEILING_CPUS} processor")
    out += check_changes(m.get("changes"))
    if m.get("needs") is not None and not (isinstance(m["needs"], list) and all(re.match(r"^[a-z0-9-]{2,30}$", str(n)) for n in m["needs"])):
        out.append("needs must list app names such as jellyfin")
    return out


def permission_words(manifest):
    """[{permission, words, risk}] for the screen people see before install (PS1)."""
    return [{"permission": p, "words": PERMISSIONS[p][0], "risk": PERMISSIONS[p][1]} for p in manifest.get("permissions") or []]


# The install warning (owner, 12 November 2026): every permission and folder in plain words, grouped as what the
# plug-in can see, change and reach, and what it runs. Nothing here is left out to make it look safer.
SEES = {"apps:read": "Your apps and whether they answer", "downloads:read": "What is downloading",
        "media:read": "Your library: films, series, music and books", "system:read": "Processor, memory and disk use",
        "jellyfin:key": "Everything in Jellyfin: your library, the people who use it and what each one watched",
        "reelix:key": "Everything in Reelix: what you follow, your download sites and its search",
        "usenet:servers": "Your news server's address, user name and password (the Usenet account you pay for)"}
CHANGES = {"jellyfin:key": "Anything in Jellyfin: it gets Jellyfin's API key, which can change users, libraries and settings",
           "reelix:key": "Anything in Reelix: it gets Reelix's API key, which can add, search for and remove what you follow",
           "usenet:servers": "It can download from your news server with your account, using some of its connections",
           "appearance:styles": "How Starboard looks, through styles in Display (checked for accessibility first)"}
REACHES = {"network:lan": "Other computers on your home network, and the internet",
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
    change = []
    if containers:
        change.append("Its own folder in Starboard's data (data/plugins/" + str(manifest.get("id")) + ")")
    change += [f"Files in your media folder under {v.split('/', 1)[1]}" for v in sorted(vols) if v.startswith("media/")]
    if any(c.get("user") == "media" for c in containers):  # API 1.12
        change.append("It runs as the owner of your media folder, so the files it adds there are yours to move or delete")
    if "iptv" in vols:
        change.append("The Live TV folder Jellyfin reads")
    change += [CHANGES[p] for p in perms if p in CHANGES]
    reach = [REACHES[p] for p in perms if p in REACHES]
    if containers and not reach:
        reach.append("Only Starboard: it has no way out to your network or the internet")
    res = manifest.get("resources") or {}
    runs = []
    for c in containers:
        r = res.get(c.get("name")) or {}
        runs.append(f"{c.get('image')}, up to {int(r.get('memory', DEFAULT_MEMORY))} MB of memory and "
                    f"{float(r.get('cpus', DEFAULT_CPUS)):g} of a processor core"
                    + (", started only when needed" if c.get("start") == "when_needed" else ", always running"))
    for j in manifest.get("jobs") or []:
        if isinstance(j, dict):
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


def compose(manifest, plugin_dir, media_dir, host=None, media_user=None):
    """The Compose file Starboard writes for a plug-in, with the hardened defaults the plug-in cannot change (PS2 to
    PS5). `plugin_dir` is data/plugins/<id> on the host; `media_dir` the media folder. `host`, for a plug-in built
    into Starboard: {"image": Starboard's own image, "user": "uid:gid", "iptv": the Live TV folder}. `media_user`:
    the media folder's owner as "uid:gid", for a container with user "media" (API 1.12); 1000:1000 when unknown."""
    host = host or {}
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
                  "    read_only: true", "    tmpfs:", "      - /tmp:size=64m", "    cap_drop:", "      - ALL",
                  "    security_opt:", "      - no-new-privileges:true", f"    user: {json.dumps(user)}",
                  "    pids_limit: 64", f"    mem_limit: {int(r.get('memory', DEFAULT_MEMORY))}m", f"    cpus: {float(r.get('cpus', DEFAULT_CPUS))}",
                  "    labels:", f"      starboard.plugin: {json.dumps(pid)}"]
        if c.get("start") == "when_needed":
            lines.append(f"      starboard.idle_stop_minutes: \"{int(c.get('idle_stop_minutes') or 15)}\"")
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
        vols = []
        for v in c.get("volumes") or []:
            if v == "data":
                vols.append(f"{plugin_dir}/data/{c['name']}:/data")
            elif v == "media:ro":
                vols.append(f"{media_dir}:/media:ro")
            elif v == "iptv":
                if not host.get("iptv"):
                    raise ValueError("The installer gave Starboard no Live TV folder (./install.sh asks)")
                vols.append(f"{host['iptv']}:/iptv")
            else:
                vols.append(f"{media_dir}/{v.split('/', 1)[1]}:/{v}")
        # settings.json, its own API key (P8) and, with jellyfin:key, Jellyfin's address and key: one folder, so a
        # saved setting reaches it at once and any container user can read it (DASH-357). Owner-only on the host.
        vols.append(f"{plugin_dir}/run:/run/starboard:ro")
        lines += ["    volumes:"] + [f"      - {json.dumps(v)}" for v in vols]
        env = {**({"TZ": host["tz"]} if host.get("tz") else {}), **{k: str(v) for k, v in (c.get("env") or {}).items()}, "STARBOARD_API": "http://starboard:8095/api/v1/",
               "STARBOARD_API_KEY_FILE": "/run/starboard/key"}
        lines += ["    environment:"] + [f"      {k}: {json.dumps(v)}" for k, v in sorted(env.items())]
    if networks:
        # Its own network, which reaches nothing outside; Starboard joins it so the plug-in can call the API (PS5).
        lines += ["networks:", f"  plugin-{pid}:", f"    name: plugin-{pid}", "    internal: true"]
        if "lan" in networks:
            lines += ["  lan:", "    driver: bridge"]
    return "\n".join(lines) + "\n"


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
                              "patternProperties": {"^[a-z_]+$": {"type": "string", "pattern": "^#[0-9a-fA-F]{6}$"}}}},
        "required": sorted(REQUIRED),
        "properties": {
            "manifest_version": {"const": 1}, "id": {"type": "string", "pattern": ID}, "name": {"type": "string", "maxLength": 40},
            "version": {"type": "string", "pattern": SEMVER}, "description": {"type": "string", "maxLength": 200},
            "author": {"type": "string", "maxLength": 60}, "licence": {"type": "string", "pattern": SPDX},
            "homepage": {"type": "string", "pattern": "^https://"}, "support_url": {"type": "string", "pattern": "^https://"},
            "starboard_api": {"type": "string"}, "health": {"type": "string", "pattern": "^/"},
            "permissions": {"type": "array", "items": {"enum": sorted(PERMISSIONS)}, "uniqueItems": True},
            "needs": {"type": "array", "items": {"type": "string"}},
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
                "properties": {"name": {"type": "string"}, "image": {"type": "string", "pattern": DIGEST_IMAGE},
                               "port": {"type": "integer", "minimum": 1, "maximum": 65535}, "network": {"enum": sorted(NETWORKS)}, "publish": {"type": "boolean"},
                               "volumes": {"type": "array", "items": {"type": "string"}}, "env": {"type": "object"},
                               "start": {"enum": ["always", "when_needed"]}, "idle_stop_minutes": {"type": "integer"},
                               "user": {"type": "string", "pattern": r"^([1-9]\d{0,5}:\d{1,6}|media)$"}}}},
            "resources": {"type": "object", "additionalProperties": {"type": "object", "additionalProperties": False,
                                                                      "properties": {"memory": {"type": "integer", "maximum": CEILING_MEMORY},
                                                                                     "cpus": {"type": "number", "maximum": CEILING_CPUS}}}},
            "settings": {"type": "array", "items": {"type": "object", "required": ["key", "label", "type"],
                                                    "properties": {"type": {"enum": list(SETTING_TYPES)}, "required": {"type": "boolean"},
                                                                   "group": {"type": "string", "maxLength": 40},
                                                                   "choices": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"anyOf": [
                                                                       {"type": "string"}, {"type": "object", "required": ["value", "label"], "additionalProperties": False,
                                                                        "properties": {"value": {"type": "string"}, "label": {"type": "string", "maxLength": 60}}}]}}]}}}},
            "cards": {"type": "array", "items": {"type": "object", "required": ["type", "path"],
                                                 "properties": {"type": {"enum": list(CARD_TYPES)}, "format": {"enum": list(CARD_FORMATS)},
                                                                "refresh_minutes": {"type": "integer", "minimum": 1, "maximum": 1440}}}},
            # API 1.4 (DASH-330)
            "setup_required": {"type": "boolean"},
            "notices": {"type": "array", "items": {"enum": sorted(NOTICES)}, "uniqueItems": True},
            "events": {"type": "array", "items": {"enum": sorted(EVENTS)}, "uniqueItems": True},
            "jobs": {"type": "array", "maxItems": 8, "items": {
                "type": "object", "additionalProperties": False, "required": ["id", "label", "path"],
                "properties": {"id": {"type": "string", "pattern": "^[a-z][a-z0-9-]{0,30}$"}, "label": {"type": "string", "maxLength": 60},
                               "path": {"type": "string", "pattern": "^/"}, "daily": {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"},
                               "every_hours": {"type": "integer", "minimum": 1, "maximum": 168}, "at_start": {"const": True},
                               "time_limit_minutes": {"type": "integer", "minimum": 1, "maximum": 120}, "quiet_hours": {"type": "boolean"}}}},
            "actions": {"type": "array", "items": {"type": "object", "required": ["label", "path"]}},
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
            if v == "media:ro":
                out.append("/media")
            elif isinstance(v, str) and re.match(r"^media/[A-Za-z0-9._-]{1,60}$", v):
                out.append("/" + v)
    return sorted(set(out))
