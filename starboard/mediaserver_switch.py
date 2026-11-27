"""The switch wizard's plan (DASH-565, owner, 26 November 2026): before a person changes media server, what would move,
what cannot, what keeps working, what needs pointing at the new server, and which plug-ins would wait. It asks the new
server to answer first and changes nothing: the change itself is `mediaserver.choose`, with its 24 hour way back.

Three ways to switch, chosen on the first step:
  "own"    import your own media: point the new server at the same folders (nothing is copied from the old server)
  "migrate" migrate from the old server: libraries, users and what was watched, as far as the new server can take them
  "fresh"  start fresh: the new server begins empty

Imported only when the wizard is opened."""

from . import mediaserver, plugin_systems

MODES = {
    "own": "Import your own media",
    "migrate": "Migrate from your old media server",
    "fresh": "Start fresh",
}

MEDIA = ("jellyfin", "plex", "emby")

# What no switch can carry across, said plainly (nothing here is lost: the old server keeps it while it stays added).
CANNOT_MOVE = [
    "Collections and playlists you made in the old media server",
    "Posters, artwork and metadata you edited by hand (the new server fetches its own)",
    "Live TV settings, tuners and recordings",
    "Each media server's own plug-ins and their settings",
    "Sign-in passwords: people are made again in the new server, or sign in with their own accounts",
]

# Things that keep working because they write to the same folders, not to the media server.
UNAFFECTED = [
    "Your download apps (qBittorrent, NZBGet, SABnzbd): they write to your media folders, not to the media server",
    "Reelix and the other apps that save into your media folders",
    "Your files: nothing is moved, copied or deleted by the switch",
]


def _present_after(data, target):
    """The systems present once `target` is the media server: every app and every other media server kept as it is, except
    that only the target counts as a media server (a plug-in that needs Jellyfin waits when Jellyfin is not the one used)."""
    have = {s for s in plugin_systems.present_in((data or {}).get("services")) if s not in MEDIA}
    if target:
        have.add(target)
    return have


def plugin_rows(listed, data, target):
    """Plug-ins that name a system they need: [{"name", "id", "state": "works" or "waiting", "tag", "why"}], from the
    plug-ins listed (plugins_admin.listing). A plug-in that needs nothing is not a dependant and is left out."""
    after = _present_after(data, target)
    rows = []
    for p in listed or []:
        info = p.get("system") or {}
        if not info.get("tag") or p.get("media_server"):
            continue
        judged = plugin_systems.judge(info, after)
        rows.append({"name": p.get("name") or p.get("id"), "id": p.get("id"), "tag": info.get("tag", ""),
                     "state": "works" if judged.get("ok") else "waiting",
                     "why": "" if judged.get("ok") else judged.get("reason", "")})
    return sorted(rows, key=lambda r: (r["state"] != "waiting", r["name"].lower()))


def feature_rows(target):
    """The parts of Starboard and the apps around it that talk to the media server, each marked after the switch:
    "works" (the new server answers it), "waiting" (the new server cannot do it yet, so it says Needs and waits), or
    "repoint" (it keeps its own link to the old server and needs pointing at the new one)."""
    cls = mediaserver.ADAPTERS.get(target)
    has = set(cls.capabilities) if cls else set()
    name = cls.name if cls else "the new media server"

    def cap(needed, why_missing):
        return ("works", "") if needed in has else ("waiting", why_missing)
    rows = []
    for title, needed, missing in (
            ("Play in your media server (Library)", "play", f"{name} cannot give Starboard a Play link yet, so Play is not drawn"),
            ("Watched and not watched (Library)", "watched", f"{name} cannot set watched yet, so it is not drawn"),
            ("Live TV channels and the TV channel plug-in", "live_tv", "Live TV is Jellyfin only, so it waits"),
            ("The media server's own plug-ins and their updater", "own_plugins", "Those are Jellyfin's own, so they wait"),
            ("Watch history import", "history_import", "Importing history into it is Jellyfin only so far"),
            ("User defaults for everyone", "user_defaults", "That is Jellyfin only so far")):
        state, why = cap(needed, missing)
        rows.append({"name": title, "state": state, "why": why})
    rows.append({"name": "Dashboard panel, Activity and System", "state": "works", "why": f"They ask {name} once it is in use"})
    rows.append({"name": "Library refresh after an import", "state": "works", "why": f"Starboard asks {name} to scan"})
    for title, why in (
            ("Reelix's own link to the media server", "Reelix keeps the address it was given: point it at the new server in Settings, Reelix"),
            ("Seerr (requests)", "Seerr keeps its own link to the media server: point it at the new server in Seerr"),
            ("On demand", "It plays through the media server it was set up with: open its settings and choose the new one"),
            ("Remote access forwarding", "A forward that sends outside visitors to the old server's port needs the new server's port")):
        rows.append({"name": title, "state": "repoint", "why": why})
    return rows


def plan(data, target, mode, listed=None, data_dir=None):
    """What the switch to `target` would do, in `mode`, as plain data for the wizard. Asks the new server to answer
    (mediaserver.check); never raises for a server that does not answer; changes nothing."""
    if mode not in MODES:
        raise ValueError("Choose how to switch: import your own media, migrate, or start fresh")
    if target and target not in mediaserver.ADAPTERS:
        raise LookupError("Starboard does not have that media server")
    before = mediaserver.active_id(data)
    out = {"mode": mode, "mode_name": MODES[mode], "from": before, "to": target,
           "from_name": mediaserver.ADAPTERS[before].name if before else "", "to_name": mediaserver.ADAPTERS[target].name if target else "None",
           "same": target == before, "check": None, "moves": [], "cannot_move": list(CANNOT_MOVE),
           "unaffected": list(UNAFFECTED), "plugins": plugin_rows(listed, data, target), "features": feature_rows(target) if target else [],
           "import_history": False, "migration": None}
    if target and target != before:
        out["check"] = mediaserver.check(data, target)
    if target and mode != "fresh" and (target != before or mode == "own"):
        from . import media_migrate  # read from both servers (GET only) so the wizard can name each library and person
        out["migration"] = media_migrate.preview(data, before, target, mode, data_dir)
    got = out["migration"] or {}
    problem = [f"Starboard could not read everything first: {got['problem']}"] if got.get("problem") else []
    if mode == "own":
        n = sum(1 for x in got.get("libraries", []) if x["action"] == "add")
        out["moves"] = [(f"{n} {'library' if n == 1 else 'libraries'} added to {out['to_name']}, reading your media folders: " + ", ".join(x["name"] for x in got["libraries"] if x["action"] == "add"))
                        if n else f"{out['to_name'] or 'The new media server'} reads the same media folders: add them as libraries in {out['to_name']}",
                        "Nothing is copied from the old media server, and your files are not touched"]
    elif mode == "migrate":
        libs = [x for x in got.get("libraries", []) if x["action"] == "add"]
        if libs:
            out["moves"].append(f"Libraries added to {out['to_name']}, from the same folders: " + ", ".join(x["name"] for x in libs[:8]))
        elif got.get("libraries"):
            out["moves"].append(f"Libraries: {out['to_name']} has them all already")
        people = [x for x in got.get("users", []) if x["action"] == "add"]
        if target == "plex":
            out["moves"].append("People: Plex accounts belong to plex.tv, so Starboard cannot make them. Invite each person from Plex")
        else:
            out["moves"].append(f"People made in {out['to_name']}: " + (", ".join(x["name"] for x in people[:8]) if people else "nobody (they are there already)")
                                + ". Each has a password nobody knows, so you set one in its dashboard")
        from .media_migrate import history_how
        how = got.get("history") or history_how(before, target)
        out["moves"].append("What was watched and where each person stopped: " + how["says"])
        out["import_history"] = target == "jellyfin"
    else:
        out["moves"] = [f"{out['to_name'] or 'No media server'} starts empty: add its libraries yourself", "The old media server stays added with its own settings"]
    out["moves"] = problem + out["moves"]
    if not target:
        out["moves"] = ["No media server is in use: the dashboard panel, Library's Play and Watched and Activity's now playing are not drawn"]
    return out
