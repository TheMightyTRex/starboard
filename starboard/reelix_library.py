"""Reelix's naming and background work pace (DASH-188, DASH-200), set by the set-up and changed in Settings, Reelix,
Naming and pace. Both are Reelix admin settings: the set-up uses the admin sign-in it already has; Settings asks for
the Reelix password each time (reelix_admin.py).

Naming: Reelix's own default season folder is "Season {season:00}", which gave "Season 06" on the owner's server.
Jellyfin, Plex and most people expect "Season 6", so the set-up sets "Season {season}". Reelix's other defaults
already follow the usual film and series layout and are left alone.

Pace: how hard Reelix works in the background (scans, refreshes, housekeeping). A small server gets Light, so
Reelix leaves memory and processor for playing; Balanced and Everything get Reelix's own Normal.
"""
SEASON_FOLDER = "Season {season}"
PACES = ("normal", "relaxed", "light", "minimal")
PACE_FOR_PRESET = {"small": "light", "balanced": "normal", "everything": "normal"}
PACE_WORDS = {"normal": "Normal: as fast as Reelix likes", "relaxed": "Relaxed: a little slower, for a busy server",
              "light": "Light: slower, for a small server", "minimal": "Minimal: only what must run"}
# The formats Settings may change; the rest of Reelix's naming settings are kept as they are.
FORMATS = ("movie_folder_format", "movie_file_format", "series_folder_format", "season_folder_format",
           "standard_episode_format")


def set_up(admin, preset):
    """The set-up's naming and pace. Returns lines of what was done."""
    done = []
    _, naming = admin.call("GET", "/settings/naming")
    if isinstance(naming, dict) and naming.get("season_folder_format") != SEASON_FOLDER:
        admin.call("PUT", "/settings/naming", {**naming, "season_folder_format": SEASON_FOLDER})
        done.append("Reelix names season folders Season 1, Season 2 and so on")
    pace = PACE_FOR_PRESET.get(preset, "normal")
    _, current = admin.call("GET", "/system/background-work")
    if (current or {}).get("pace") != pace:
        admin.call("PUT", "/system/background-work", {"pace": pace})
        done.append(f"Reelix's background work: {PACE_WORDS[pace].split(':')[0]}")
    return done


def state(reelix):
    """What Settings shows: the formats, an example of each and the pace."""
    _, naming = reelix.call("GET", "/settings/naming")
    _, preview = reelix.call("GET", "/naming/preview")
    _, pace = reelix.call("GET", "/system/background-work")
    return {"naming": {k: (naming or {}).get(k, "") for k in FORMATS}, "preview": preview or {},
            "pace": (pace or {}).get("pace", "normal"), "paces": [{"value": p, "label": PACE_WORDS[p]} for p in PACES]}


def _merged(reelix, changes):
    _, naming = reelix.call("GET", "/settings/naming")
    out = dict(naming or {})
    for k in FORMATS:
        if k in (changes or {}):
            v = str(changes[k]).strip()
            if not v or len(v) > 300 or any(c in v for c in "\r\n"):
                raise ValueError("Each format is one line of up to 300 characters")
            out[k] = v
    return out


def preview(reelix, changes):
    """Examples for formats not saved yet, with any problems Reelix finds in them."""
    _, out = reelix.call("POST", "/naming/preview", _merged(reelix, changes))
    return out or {}


def save(reelix, changes, pace=None):
    """Saves the formats (only when Reelix finds no problem in them) and the pace."""
    merged = _merged(reelix, changes)
    check = preview(reelix, changes)
    if check.get("errors"):
        raise ValueError("; ".join(f"{e.get('field', '').replace('_', ' ')}: {e.get('message', '')}" for e in check["errors"]))
    reelix.call("PUT", "/settings/naming", merged)
    if pace is not None:
        if pace not in PACES:
            raise ValueError("Choose Normal, Relaxed, Light or Minimal")
        reelix.call("PUT", "/system/background-work", {"pace": pace})
    return state(reelix)
