"""Item page extras (DASH-209): Refresh, Rescan, Rename with a preview, the files with Delete this file, and the item's
own history, for films and series, from Reelix's own routes with Starboard's manager key. Books and music get Refresh,
Rescan and history through their author or artist."""
from . import services

EVENTS = {"grabbed": "Sent to download", "download_folder_imported": "Imported", "downloadFolderImported": "Imported",
          "imported": "Imported", "download_failed": "Download failed", "downloadFailed": "Download failed",
          "file_deleted": "File deleted", "movieFileDeleted": "File deleted", "episodeFileDeleted": "File deleted",
          "file_renamed": "File renamed", "movieFileRenamed": "File renamed", "episodeFileRenamed": "File renamed",
          "download_ignored": "Download ignored"}


def _kind(tab):
    if tab not in ("films", "tv"):
        raise ValueError("This is for films and series")
    return ("movies", "movie_id", "movie") if tab == "films" else ("series", "series_id", "series")


def refresh(reelix, tab, item_id, rescan=False):
    """Refresh reads the details again (and rescans); Rescan only looks at the files on disk."""
    base, _, _ = _kind(tab)
    services._api(reelix, f"/{base}/{int(item_id)}/{'rescan' if rescan else 'refresh'}", method="POST", body={})
    return "Reelix is looking at its files again" if rescan else "Reelix is reading its details again"


def files(reelix, tab, item_id):
    """The files on disk: name, size, quality and release group, with their ids for Delete this file."""
    item_id = int(item_id)
    if tab == "films":
        got = services._api(reelix, f"/movies/{item_id}/files") or []
        rows = [g.get("file") or g for g in got if isinstance(g, dict)]
    else:
        _kind(tab)
        got = services._api(reelix, "/episodefiles", {"series_id": item_id}) or []
        rows = got.get("items") if isinstance(got, dict) else got
    out = []
    for f in rows or []:
        if not isinstance(f, dict) or not f.get("id"):
            continue
        out.append({"id": int(f["id"]), "name": f.get("relative_path") or str(f.get("path") or "").rsplit("/", 1)[-1],
                    "size": int(f.get("size") or 0), "quality": f.get("quality_name") or "", "group": f.get("release_group") or "",
                    "season": f.get("season_number")})
    return sorted(out, key=lambda f: (f["season"] or 0, f["name"]))


def delete_file(reelix, tab, file_id):
    _kind(tab)
    services._api(reelix, f"/{'moviefiles' if tab == 'films' else 'episodefiles'}/{int(file_id)}", method="DELETE")
    return "The file is deleted; Reelix looks for it again only if you follow it"


def rename_preview(reelix, tab, item_id):
    """What Rename would change: each file's name now and after, only the ones that change."""
    _, key, _ = _kind(tab)
    got = services._api(reelix, "/rename/preview", {key: int(item_id)}) or []
    return [{"file_id": int(r["file_id"]), "now": r.get("existing_path") or "", "after": r.get("new_path") or ""}
            for r in got if isinstance(r, dict) and r.get("file_id") and r.get("existing_path") != r.get("new_path")]


def rename(reelix, tab, item_id, file_ids=None):
    _, _, kind = _kind(tab)
    body = {"kind": kind, "ids": [int(item_id)]}
    if file_ids:
        body["file_ids"] = [int(f) for f in file_ids][:500]
    services._api(reelix, "/rename", method="POST", body=body)
    return "Reelix is renaming the files"


def history(reelix, tab, item_id):
    """The item's own history, newest first: what was sent to download, imported, failed, renamed or deleted."""
    key = {"films": "movie_id", "tv": "series_id", "books": "book_id", "audiobooks": "book_id", "music": "artist_id"}.get(tab)
    if not key:
        raise ValueError("No history for this tab")
    got = services._api(reelix, "/history", {key: int(item_id), "page_size": 50}) or {}
    rows = got.get("items") if isinstance(got, dict) else got
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        ev = str(r.get("event_type") or "")
        ep = r.get("episode") or {}
        where = " · ".join(x for x in (r.get("indexer") or "", r.get("download_client") or "") if x)
        out.append({"date": r.get("date"), "what": EVENTS.get(ev, ev.replace("_", " ").capitalize()), "title": r.get("source_title") or "",
                    "episode": f"S{ep.get('season_number')} E{ep.get('episode_number')}" if ep.get("season_number") is not None else "",
                    "where": where})
    return out
