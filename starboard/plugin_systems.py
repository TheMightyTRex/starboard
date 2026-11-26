"""The system a plug-in needs (API 1.19, DASH-567): a tag such as "Jellyfin only", "Plex or Emby" or "Needs Reelix".

A manifest names it in `requires`, a list of needs, each a system ("jellyfin"), alternatives joined with "or"
("plex or emby") and, for one system, optionally "only" ("jellyfin only"). Older manifests say nothing, so it is
worked out from what they already ask for: jellyfin:key, jellyfin:metadata and jellyfin:libraries mean Jellyfin,
reelix:key means Reelix and usenet:servers means SABnzbd or NZBGet. An explicit `requires` wins, and an empty one
says it needs nothing.

Starboard shows the tag in words on the Catalogue, a plug-in's page, Manage and Ready to update, and says why when the
system is not there ("Needs Jellyfin, which this Starboard does not use"). It never stops or fails a plug-in for it:
a plug-in whose system has gone away says it is waiting. Nothing here reads a file or the network."""

import re

# id: (name as people read it, kind). "media server" ones are alternatives for the one place in Starboard a media
# server fills (DASH-565); the rest are apps Starboard knows.
SYSTEMS = {
    "jellyfin": ("Jellyfin", "media server"), "plex": ("Plex", "media server"), "emby": ("Emby", "media server"),
    "reelix": ("Reelix", "app"), "qbittorrent": ("qBittorrent", "app"), "sabnzbd": ("SABnzbd", "app"),
    "nzbget": ("NZBGet", "app"), "sonarr": ("Sonarr", "app"), "radarr": ("Radarr", "app"), "lidarr": ("Lidarr", "app"),
    "readarr": ("Readarr", "app"), "prowlarr": ("Prowlarr", "app"), "bazarr": ("Bazarr", "app"),
    "audiobookshelf": ("Audiobookshelf", "app"), "kavita": ("Kavita", "app"), "calibre-web": ("Calibre-Web", "app"),
    "navidrome": ("Navidrome", "app"), "gluetun": ("Gluetun", "app"), "slskd": ("Soulseek (slskd)", "app"),
    "tdarr": ("Tdarr", "app"), "seerr": ("Seerr", "app"), "dispatcharr": ("Dispatcharr", "app"),
}
MAX_NEEDS = 4
NEED = re.compile(r"^([a-z][a-z0-9-]{1,29})((?: or [a-z][a-z0-9-]{1,29}){0,5})( only)?$")

# What older manifests already ask for, and the system each means (a need: alternatives in a tuple).
FROM_PERMISSIONS = {
    "jellyfin:key": ("jellyfin",), "jellyfin:metadata": ("jellyfin",), "jellyfin:libraries": ("jellyfin",),
    "reelix:key": ("reelix",), "usenet:servers": ("sabnzbd", "nzbget"),
}


def parse_need(text):
    """One need as (alternatives, only), or None when it is not in the form: "jellyfin", "jellyfin only", "plex or emby"."""
    m = NEED.match(text.strip()) if isinstance(text, str) else None
    if not m:
        return None
    alts = (m.group(1), *[a for a in m.group(2).split(" or ") if a])
    only = bool(m.group(3))
    if only and len(alts) != 1:
        return None
    if len(set(alts)) != len(alts):
        return None
    return alts, only


def problems(requires):
    """Sentences for a bad `requires`, empty when it is fine (called by plugins.check)."""
    if not isinstance(requires, list) or len(requires) > MAX_NEEDS:
        return [f"requires must list up to {MAX_NEEDS} needs, such as \"jellyfin\", \"jellyfin only\" or \"plex or emby\" (API 1.19)"]
    out = []
    seen = set()
    for i, text in enumerate(requires):
        got = parse_need(text)
        if not got:
            out.append(f"requires[{i}] must be a system, \"a system only\" or systems joined with or, such as \"plex or emby\"")
            continue
        for s in got[0]:
            if s not in SYSTEMS:
                out.append(f"requires[{i}]: {s} is not a system Starboard knows. Use one of: " + ", ".join(sorted(SYSTEMS)))
        if got[0] in seen:
            out.append(f"requires[{i}]: {' or '.join(got[0])} is listed twice")
        seen.add(got[0])
    return out


def needs(thing):
    """The needs of a manifest or a catalogue entry: [(alternatives, only)], and where they came from ("manifest" for
    an explicit `requires`, "permissions" when worked out from them, "" when it needs nothing named)."""
    if isinstance(thing, dict) and isinstance(thing.get("requires"), list):
        got = [parse_need(t) for t in thing["requires"]]
        return [g for g in got if g and all(s in SYSTEMS for s in g[0])], "manifest"
    found = []
    for p in (thing.get("permissions") if isinstance(thing, dict) else None) or []:
        alts = FROM_PERMISSIONS.get(p) if isinstance(p, str) else None
        if alts and (alts, False) not in found:  # several permissions for one system are one need
            found.append((alts, False))
    return found, ("permissions" if found else "")


def _name(system):
    return SYSTEMS[system][0]


def _alts(alts):
    return " or ".join(_name(a) for a in alts)


def tag_part(need):
    """One need in words: "Jellyfin only", "Plex or Emby", "Needs Reelix". A lone media server is always "only": it is
    the one media server the plug-in works with."""
    alts, only = need
    if len(alts) > 1:
        return _alts(alts) if all(SYSTEMS[a][1] == "media server" for a in alts) else f"Needs {_alts(alts)}"
    if only or SYSTEMS[alts[0]][1] == "media server":
        return f"{_name(alts[0])} only"
    return f"Needs {_name(alts[0])}"


def present_in(services, extra=()):
    """The systems this Starboard has: an enabled service with an address (by its type, or by its icon, which names
    Reelix and the apps added as a link), and any `extra` ids (an active media server plug-in, DASH-565)."""
    have = set(extra)
    for s in services or []:
        if not isinstance(s, dict) or s.get("enabled", True) is False or not s.get("url"):
            continue
        for key in (s.get("type"), s.get("icon")):
            if key in SYSTEMS:
                have.add(key)
    return have


def describe(thing, present=None):
    """{"tag", "needs": [{"systems": [{"id", "name"}], "only", "tag", "present"}], "from", "ok", "reason"}.
    `present` is a set of system ids (present_in) or None when not known (a preview before anything is read): then
    "ok" is None and there is no reason. "tag" is "" for a plug-in that needs nothing named."""
    found, came = needs(thing)
    rows = [{"systems": [{"id": a, "name": _name(a)} for a in alts], "only": only, "tag": tag_part((alts, only)), "present": None}
            for alts, only in found]
    tags = [r["tag"] if i == 0 else r["tag"].replace("Needs ", "needs ", 1) for i, r in enumerate(rows)]
    return judge({"tag": ", ".join(tags), "needs": rows, "from": came, "ok": None, "reason": ""}, present)


def judge(info, present):
    """The same answer with each need marked present or not, and "ok" and the plain reason, for a set of present
    systems. A copy: the answer given is not changed. Without `present` it is returned as it was."""
    if present is None or not isinstance(info, dict):
        return info
    rows = [{**r, "present": any(s["id"] in present for s in r["systems"])} for r in info.get("needs") or []]
    gone = [r for r in rows if not r["present"]]
    out = {**info, "needs": rows, "ok": not gone, "reason": reason(gone) if gone else ""}
    out["waiting"] = waiting_words(out)
    return out


def reason(rows):
    """The plain reason: "Needs Jellyfin, which this Starboard does not use". Several are joined with ", and", and
    alternatives say either: "Needs Jellyfin, and either Plex or Emby, which this Starboard does not use"."""
    names = [" or ".join(s["name"] for s in r["systems"]) for r in rows]
    if len(names) > 1:
        names = [f"either {n}" if " or " in n else n for n in names]
    return f"Needs {', and '.join(names)}, which this Starboard does not use"


def waiting_words(info):
    """What an installed plug-in says when its system is not there: it is not stopped, and it is not failing."""
    if info.get("ok") is False:
        why = info["reason"]
        return f"Waiting: {why[:1].lower()}{why[1:]}. It is not stopped and keeps its settings, and carries on when that system is there."
    return ""
