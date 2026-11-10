"""Settings, Reelix, Picture quality in full (DASH-196, design agreed by the owner on 10 November 2026).

Three layers, as agreed:
- A, choose a level: Reelix's video quality profiles as choices, HD-1080p recommended. The level chosen is the one new
  films and series use (the same setting as before, saved through reelix_basics).
- B, what a level does, in words: which qualities it accepts, where it stops upgrading, which extras it prefers and
  which it never takes, the largest file, and whether it upgrades.
- C, under Advanced settings, change a level: its qualities best first, each ticked or not, with a Stop upgrading here
  line; extras as Prefer, Neutral or Never instead of scores; upgrades; and the largest file.

Reelix keeps each quality row as it is (a single quality, or a group of them), worst first, and marks where upgrades
stop with the quality's number or the group's. Starboard keeps every row exactly as Reelix sent it and only changes its
order, its tick and the stop line, so groups and anything Starboard does not show survive a save."""

# Reelix's video qualities (reelix-parser model.rs): the name Reelix writes, its number, and plain words.
VIDEO = [
    ("Unknown", 0, "Unknown"), ("WORKPRINT", 1, "Workprint"), ("CAM", 2, "Cam copy"), ("TELESYNC", 3, "Telesync"),
    ("TELECINE", 4, "Telecine"), ("REGIONAL", 5, "Regional"), ("DVDSCR", 6, "DVD screener"), ("SDTV", 7, "SD TV"),
    ("DVD", 8, "DVD"), ("DVD-R", 9, "DVD-R"), ("WEBDL-480p", 10, "480p web"), ("WEBRip-480p", 11, "480p web rip"),
    ("Bluray-480p", 12, "480p Blu-ray"), ("Bluray-576p", 13, "576p Blu-ray"), ("HDTV-720p", 14, "720p TV"),
    ("WEBDL-720p", 15, "720p web"), ("WEBRip-720p", 16, "720p web rip"), ("Bluray-720p", 17, "720p Blu-ray"),
    ("HDTV-1080p", 18, "1080p TV"), ("WEBDL-1080p", 19, "1080p web"), ("WEBRip-1080p", 20, "1080p web rip"),
    ("Bluray-1080p", 21, "1080p Blu-ray"), ("Remux-1080p", 22, "1080p remux"), ("HDTV-2160p", 23, "4K TV"),
    ("WEBDL-2160p", 24, "4K web"), ("WEBRip-2160p", 25, "4K web rip"), ("Bluray-2160p", 26, "4K Blu-ray"),
    ("Remux-2160p", 27, "4K remux"), ("BR-DISK", 28, "Blu-ray disc"), ("Raw-HD", 29, "Raw HD"),
]
QUALITY_ID = {name: number for name, number, _ in VIDEO}
WORDS = {name: words for name, _, words in VIDEO}
# Reelix's built-in levels, in plain words (reelix-db quality_profiles.rs). Others show their own name.
LEVELS = {
    "HD-1080p": ("HD", "1080p, the usual choice for a television."),
    "Ultra-HD": ("Best", "4K, about four times the space of HD."),
    "HD-720p": ("Small screens", "720p, for phones, tablets and saving space."),
    "HD-720p/1080p": ("HD or smaller", "720p or 1080p, whichever comes first."),
    "SD": ("Lowest", "Standard definition, the smallest files."),
    "Any": ("Anything", "Any quality at all, the first one found."),
}
RECOMMENDED = "HD-1080p"
CHOICES = ("prefer", "neutral", "never")
PREFER, NEVER = 100, -10000  # scores Starboard writes for a new Prefer or Never; existing scores of that kind are kept


def _key(item):
    """A row's key for the page: g<group id> for a group, q<quality number> for a single quality."""
    if item.get("items"):
        return f"g{item.get('id')}"
    return f"q{QUALITY_ID.get(item.get('quality'), -1)}"


def _stop_id(item):
    """The number Reelix's cutoff uses for a row: the group's id, or the quality's number."""
    return int(item["id"]) if item.get("items") else QUALITY_ID.get(item.get("quality"), -1)


def _label(item):
    if item.get("items"):
        return item.get("name") or ", ".join(WORDS.get(q, q) for q in item["items"])
    return WORDS.get(item.get("quality"), item.get("quality") or "Unknown")


def _choice(score):
    score = int(score or 0)
    return "prefer" if score > 0 else "never" if score < 0 else "neutral"


def describe(profile, formats):
    """B: one profile in words, and its rows for C (best first)."""
    items = profile.get("items") or []
    best_first = list(reversed(items))
    names = {f["id"]: f.get("name", "") for f in formats}
    scores = {int(i["format_id"]): int(i.get("score", 0)) for i in profile.get("format_items") or []}
    stop = next((i for i in best_first if _stop_id(i) == profile.get("cutoff")), None)
    accepts = [_label(i) for i in best_first if i.get("allowed")]
    prefers = [names[f] for f, s in scores.items() if s > 0 and f in names]
    never = [names[f] for f, s in scores.items() if s < 0 and f in names]
    largest = profile.get("max_size_mb")
    if largest:
        never.append(f"files over {round(largest / 1000, 1):g} GB")
    title, line = LEVELS.get(profile.get("name", ""), (profile.get("name", ""), ""))
    return {
        "id": profile["id"], "name": profile.get("name", ""), "title": title, "line": line,
        "recommended": profile.get("name") == RECOMMENDED,
        "accepts": accepts, "stops_at": _label(stop) if stop and profile.get("upgrade_allowed") else "",
        "prefers": prefers, "never": never, "upgrades": bool(profile.get("upgrade_allowed")),
        "rows": [{"key": _key(i), "label": _label(i), "allowed": bool(i.get("allowed"))} for i in best_first],
        "stop": _key(stop) if stop else None,
        "extras": [{"id": f["id"], "name": f.get("name", ""), "choice": _choice(scores.get(f["id"]))} for f in formats],
        "largest_gb": round(largest / 1000, 1) if largest else None,
    }


def state(reelix):
    _, profiles = reelix.call("GET", "/qualityprofiles")
    _, formats = reelix.call("GET", "/customformats")
    _, req = reelix.call("GET", "/settings/requests")
    video = [p for p in profiles or [] if p.get("family", "video") == "video"]
    formats = [f for f in formats or [] if isinstance(f, dict) and "id" in f]
    recommended = next((p["id"] for p in video if p.get("name") == RECOMMENDED), video[0]["id"] if video else None)
    chosen = (((req or {}).get("movie") or {}).get("profile_id")) or recommended
    return {"levels": [describe(p, formats) for p in video], "chosen": chosen}


def change(profile, changes):
    """C: the profile with the person's changes, checked. Raises ValueError with the fix, in words."""
    if not isinstance(changes, dict):
        raise ValueError("Nothing to save")
    out = dict(profile)
    rows = {_key(i): i for i in profile.get("items") or []}
    if "order" in changes:
        order = [k for k in changes.get("order") or [] if isinstance(k, str)]
        keys = [k for k in order if k != "stop"]
        if sorted(keys) != sorted(rows) or len(keys) != len(set(keys)):
            raise ValueError("The list of qualities changed while you were working on it. Reload the page and try again")
        allowed = changes.get("allowed") or {}
        best_first = []
        for k in keys:
            row = dict(rows[k])
            if k in allowed:
                row["allowed"] = bool(allowed[k])
            best_first.append(row)
        if not any(r["allowed"] for r in best_first):
            raise ValueError("Tick at least one quality")
        # Stop upgrading here: upgrades stop at the first ticked row under the line.
        at = order.index("stop") if "stop" in order else 0
        below = [r for r, k in zip(best_first, keys) if order.index(k) > at and r["allowed"]]
        if not below:
            raise ValueError("Move Stop upgrading here above at least one ticked quality")
        out["items"] = list(reversed(best_first))
        out["cutoff"] = _stop_id(below[0])
    if "upgrades" in changes:
        out["upgrade_allowed"] = bool(changes["upgrades"])
    if "extras" in changes:
        extras = changes.get("extras") or {}
        old = {int(i["format_id"]): int(i.get("score", 0)) for i in profile.get("format_items") or []}
        new = dict(old)
        for fid, choice in extras.items():
            if choice not in CHOICES or not str(fid).lstrip("-").isdigit():
                raise ValueError("Choose Prefer, Neutral or Never for each extra")
            fid, was = int(fid), old.get(int(fid), 0)
            new[fid] = (was if was > 0 else PREFER) if choice == "prefer" else (was if was < 0 else NEVER) if choice == "never" else 0
        out["format_items"] = [{"format_id": f, "score": s} for f, s in sorted(new.items()) if s]
    if "largest_gb" in changes:
        gb = changes.get("largest_gb")
        if gb in (None, ""):
            out["max_size_mb"] = None
        else:
            try:
                gb = float(gb)
            except (TypeError, ValueError):
                raise ValueError("Write the largest file in GB, such as 20") from None
            if not 0.1 <= gb <= 500:
                raise ValueError("Write a size between 0.1 and 500 GB")
            out["max_size_mb"] = int(round(gb * 1000))
    return out


def save(reelix, pid, changes):
    """Saves C's changes to one level; returns the new state and what was done, in words."""
    if not str(pid).isdigit():
        raise ValueError("Choose a level first")
    _, profile = reelix.call("GET", f"/qualityprofiles/{int(pid)}")
    if not profile or profile.get("family", "video") != "video":
        raise ValueError("That level is not in Reelix any more. Reload the page")
    reelix.call("PUT", f"/qualityprofiles/{int(pid)}", change(profile, changes))
    title = LEVELS.get(profile.get("name", ""), (profile.get("name", ""),))[0]
    return {**state(reelix), "done": [f"{title} saved in Reelix"]}


def choose(reelix, pid):
    """A: the level new films and series use."""
    from . import reelix_basics
    reelix_basics.save(reelix, {"profile": str(pid)})
    out = state(reelix)
    level = next((lvl for lvl in out["levels"] if lvl["id"] == int(pid)), None)
    return {**out, "done": [f"New films and series use {level['title'] if level else 'that level'}"]}


def recommended_for_new(reelix):
    """At set-up: new films and series use HD-1080p when no level is chosen yet. Returns what was done, in words."""
    _, req = reelix.call("GET", "/settings/requests")
    req = dict(req or {})
    if all((req.get(kind) or {}).get("profile_id") for kind in ("movie", "series")):
        return []
    _, profiles = reelix.call("GET", "/qualityprofiles")
    hd = next((p for p in profiles or [] if p.get("name") == RECOMMENDED and p.get("family", "video") == "video"), None)
    if not hd:
        return []
    for kind in ("movie", "series"):
        if not (req.get(kind) or {}).get("profile_id"):
            req[kind] = {**(req.get(kind) or {}), "profile_id": hd["id"]}
    reelix.call("PUT", "/settings/requests", req)
    return ["New films and series use HD (1080p)"]
