"""Choose the episode (owner, 12 November 2026: "I have a lot of messages 'Episodes are not part of the series'").

Reelix numbers episodes as TMDB does; many releases use the broadcast or TVDB numbers, so a file named S02E13 can be
TMDB's episode 12, or a special. Reelix then refuses it with "Episodes are not part of the series". Downloads offers
Choose the episode: Starboard asks Reelix which files the download has and the series' episodes, guesses each file's
episode (its title in the file name first, then the same number counted from the end of the season), and imports
the file to the episode you confirm, through Reelix's own manual import. Nothing is guessed silently: you see the
guess, whether you already have that episode, and can choose another or remove the download instead."""
import re
import urllib.parse

from . import services

SXE = re.compile(r"[Ss](\d{1,2})[ ._-]?[Ee](\d{1,3})")


def fold(text):
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _episodes(reelix, series_id):
    got = services._api(reelix, f"/series/{int(series_id)}/episodes", timeout=20) or []
    eps = got.get("episodes", got) if isinstance(got, dict) else got
    return sorted(({"id": e["id"], "season": e.get("season_number") or 0, "number": e.get("episode_number") or 0,
                    "title": e.get("title") or "", "have": bool(e.get("has_file"))} for e in eps if e.get("id")),
                  key=lambda e: (e["season"] == 0, e["season"], e["number"]))


def guess(name, episodes):
    """The likeliest episode for a file name: an episode title found in the name (the longest), else the same
    season with the number counted from the season's end (a broadcast season with more parts than TMDB's), else
    the season's last episode."""
    folded = fold(name)
    titled = [e for e in episodes if len(fold(e["title"])) >= 5 and fold(e["title"]) in folded]
    if titled:
        return max(titled, key=lambda e: len(fold(e["title"])))["id"], True
    m = SXE.search(name or "")
    if not m:
        return None, False
    season, number = int(m.group(1)), int(m.group(2))
    same = [e for e in episodes if e["season"] == season]
    exact = next((e for e in same if e["number"] == number), None)
    if exact:
        return exact["id"], False
    if same:
        return same[-1]["id"], False
    return None, False


def options(reelix, download_id):
    """{series: {id, title}, files: [{path, name, guess, guess_words}], episodes: [...]} for one download."""
    if not re.match(r"^[A-Za-z0-9_.:-]{1,128}$", download_id or ""):
        raise ValueError("Not a download")
    preview = services._api(reelix, "/manualimport?" + urllib.parse.urlencode({"download_id": download_id}), timeout=60) or []
    media = next((f.get("media") for f in preview if (f.get("media") or {}).get("kind") == "series"), None)
    if not media:
        raise LookupError("Reelix does not know which series this download is")
    episodes = _episodes(reelix, media["id"])
    by_id = {e["id"]: e for e in episodes}
    files = []
    for f in preview:
        g, sure = guess(f.get("relative_path") or f.get("path"), episodes)
        e = by_id.get(g)
        files.append({"path": f.get("path"), "name": f.get("relative_path") or f.get("path"), "guess": g, "sure": sure,
                      "guess_words": f"Season {e['season']}, episode {e['number']}: {e['title']}" if e else "",
                      "rejections": f.get("rejections") or []})
    return {"series": {"id": media["id"], "title": media.get("title") or ""}, "files": files, "episodes": episodes}


def apply(reelix, download_id, choices):
    """Imports each chosen file to its episodes. choices: [{path, episode_ids}]. Returns how many were sent."""
    if not re.match(r"^[A-Za-z0-9_.:-]{1,128}$", download_id or ""):
        raise ValueError("Not a download")
    preview = services._api(reelix, "/manualimport?" + urllib.parse.urlencode({"download_id": download_id}), timeout=60) or []
    by_path = {f.get("path"): f for f in preview}
    series = next((f.get("media") for f in preview if (f.get("media") or {}).get("kind") == "series"), None)
    if not series:
        raise LookupError("Reelix does not know which series this download is")
    known = {e["id"] for e in _episodes(reelix, series["id"])}
    files = []
    for c in choices or []:
        f = by_path.get(c.get("path"))
        ids = [int(i) for i in c.get("episode_ids") or [] if str(i).isdigit() and int(i) in known]
        if not f or not ids:
            continue
        files.append({"path": f["path"], "series_id": series["id"], "episode_ids": ids, "quality": f.get("quality"),
                      "languages": f.get("languages") or [], "release_group": f.get("release_group"), "download_id": download_id})
    if not files:
        raise ValueError("Choose an episode for at least one file")
    services._api(reelix, "/manualimport", method="POST", body={"files": files, "import_mode": "auto"}, timeout=60)
    services.forget("queue")
    return {"sent": len(files)}
