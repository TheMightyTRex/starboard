"""Bring in media already on disk (DASH-186): films and series in a library folder that Reelix does not know yet,
for a new install whose media was never run by Radarr or Sonarr. Uses Reelix's own library import with Starboard's
manager key (Reelix's "manage library" permission, so no admin password): list the folders, look up the best match
for each in batches of 25, then import the ones you keep. Nothing is downloaded or moved: Reelix adds each film or
series for the folder it is already in and scans its files. Books and music use Reelix's book and music import,
which this does not cover yet."""
import json
import urllib.error
import urllib.parse
import urllib.request

KINDS = {"movie": "films", "series": "tv"}
BATCH = 25


class ImportError_(Exception):
    pass


def _reelix(cfg):
    s = next((x for x in cfg.data["services"] if x.get("icon") == "reelix" and x["type"] == "link" and x.get("api_key")), None)
    if not s:
        raise ImportError_("Reelix is not on your apps with its key yet")
    return s["url"].rstrip("/") + "/api/v1", s["api_key"]


def _call(cfg, method, path, body=None, timeout=60):
    base, key = _reelix(cfg)
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Api-Key": key, "Accept": "application/json", "Content-Type": "application/json",
                                          "User-Agent": "Starboard", "X-Reelix-Request": "1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # Reelix's address from Starboard's own apps  # nosec B310
            raw = r.read(20_000_000)
    except urllib.error.HTTPError as e:
        try:
            message = json.loads(e.read(4000)).get("message")
        except ValueError:
            message = None
        raise ImportError_(message or f"Reelix answered {e.code}") from None
    except (urllib.error.URLError, OSError):
        raise ImportError_("Starboard could not reach Reelix") from None
    return json.loads(raw) if raw else None


def folders(cfg, tab):
    """The library folders for films or series, each with how many sub-folders Reelix does not know yet."""
    want = {v: k for k, v in KINDS.items()}.get(tab)
    if not want:
        return []
    return [{"id": f["id"], "path": f["path"], "waiting": len(f.get("unmapped_folders") or [])}
            for f in _call(cfg, "GET", "/rootfolders") or [] if f.get("media_kind") == want and f.get("accessible", True)]


def _slim(c):
    return {"path": c["folder"]["path"], "name": c["folder"]["name"], "title": c.get("parsed_title"), "year": c.get("parsed_year"),
            "files": c.get("file_count", 0), "size": c.get("size", 0), "problem": c.get("lookup_error"),
            "matches": [{"tmdb_id": m.get("tmdb_id"), "title": m.get("title"), "year": m.get("year")}
                        for m in (c.get("suggestions") or [])[:5] if m.get("tmdb_id")]}


def scan(cfg, root_id, start=0):
    """One page of folders (25), each with Reelix's best matches, and how many there are in all."""
    root_id = int(root_id)
    listed = _call(cfg, "GET", f"/libraryimport/scan?{urllib.parse.urlencode({'root_folder_id': root_id, 'lookup': 'false'})}") or []
    page = listed[int(start):int(start) + BATCH]
    matched = _call(cfg, "POST", "/libraryimport/match", {"root_folder_id": root_id, "paths": [c["folder"]["path"] for c in page]}) if page else []
    return {"total": len(listed), "start": int(start), "items": [_slim(c) for c in matched or []]}


def run(cfg, root_id, items):
    """Imports the kept folders with Reelix's first film and series quality profile. Returns {added, errors}."""
    root_id = int(root_id)
    keep = [{"path": str(i["path"]), "tmdb_id": int(i["tmdb_id"])} for i in items or [] if i.get("tmdb_id")]
    if not keep:
        raise ImportError_("Choose a match for at least one folder")
    profiles = [p for p in _call(cfg, "GET", "/qualityprofiles") or [] if p.get("family", "video") == "video"]
    if not profiles:
        raise ImportError_("Reelix has no film and series quality profile")
    body = {"root_folder_id": root_id, "search_on_add": False,
            "items": [{**i, "quality_profile_id": profiles[0]["id"]} for i in keep]}
    out = _call(cfg, "POST", "/libraryimport", body, timeout=300) or {}
    return {"added": len(out.get("added") or []), "errors": [{"path": e.get("path"), "message": e.get("message")} for e in out.get("errors") or []]}
