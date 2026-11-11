"""Change match (owner, 11 November 2026: "override a match of any media manually"). Reelix cannot change what an item
is matched to, so Starboard does it in three steps: remove the item from Reelix (its files stay where they are), add the
chosen match pointing at the same folder, and, if that fails, put the old match back.

Films and series: matched on TMDB, brought back with Reelix's library import. Radio: a show on Reelix's radio sources,
following as before. Audiobooks and books: the author, matched on Open Library, brought back with the book import and
following only the books already there."""
import os
import urllib.parse

from . import services


def _api(reelix, path, method="GET", body=None, timeout=60):
    return services._api(reelix, path, method=method, body=body, timeout=timeout)


def search(reelix, tab, q):
    """What the item could be matched to: [{key, title, year, detail, image}]."""
    q = str(q or "").strip()[:120]
    if len(q) < 2:
        return []
    if tab in ("films", "tv"):
        rows = _api(reelix, f"/{'movies' if tab == 'films' else 'series'}/lookup?{urllib.parse.urlencode({'term': q})}") or []
        return [{"key": str(r["tmdb_id"]), "title": r.get("title"), "year": r.get("year"), "detail": (r.get("overview") or "")[:160],
                 "image": r.get("poster") or "", "in_library": bool(r.get("in_library"))} for r in rows[:12] if r.get("tmdb_id")]
    if tab == "radio":
        rows = _api(reelix, f"/radio/search?{urllib.parse.urlencode({'q': q})}", timeout=90) or []
        return [{"key": f"{r['provider']}:{r['external_id']}", "title": r.get("title"), "year": None,
                 "detail": r.get("station_name") or r.get("author") or "", "image": r.get("image") or r.get("artwork_url") or "",
                 "in_library": bool(r.get("show_id"))} for r in rows[:12] if r.get("provider") and r.get("external_id")]
    if tab in ("audiobooks", "books"):
        rows = _api(reelix, f"/authors/lookup?{urllib.parse.urlencode({'term': q})}") or []
        return [{"key": r["openlibrary_id"], "title": r.get("name"), "year": None,
                 "detail": ", ".join(x for x in (f"best known for {r['top_work']}" if r.get("top_work") else "",
                                                 f"{r['work_count']} works" if r.get("work_count") else "") if x),
                 "image": r.get("image") or "", "in_library": bool(r.get("author_id"))} for r in rows[:12] if r.get("openlibrary_id")]
    raise ValueError("Change match works for films, series, radio, audiobooks and books")


def _root_for(roots, path):
    best = None
    for r in roots or []:
        p = str(r.get("path") or "").rstrip("/")
        if p and (path == p or path.startswith(p + "/")) and (not best or len(p) > len(best["path"])):
            best = r
    return best


def change(reelix, tab, item_id, key):
    """Moves the item to the chosen match. Returns {"said": sentence, "id": the new id (or None)}."""
    item_id = int(item_id)
    key = str(key or "").strip()
    if not key:
        raise ValueError("Choose what it really is")
    if tab in ("films", "tv"):
        kind = "movies" if tab == "films" else "series"
        old = _api(reelix, f"/{kind}/{item_id}") or {}
        path, old_tmdb = old.get("path"), old.get("tmdb_id")
        if not path:
            raise ValueError("Reelix gave no folder for it")
        if str(old_tmdb) == key:
            return {"said": "That is already its match", "id": item_id}
        root = _root_for(_api(reelix, "/rootfolders"), path)
        if not root:
            raise ValueError("Its folder is not in one of Reelix's library folders")
        profile = old.get("quality_profile_id")

        def add(tmdb):
            out = _api(reelix, "/libraryimport", method="POST", timeout=300, body={
                "root_folder_id": root["id"], "search_on_add": False,
                "items": [{"path": path, "tmdb_id": int(tmdb), "quality_profile_id": profile}]}) or {}
            return (out.get("added") or [None])[0], out.get("errors") or []
        _api(reelix, f"/{kind}/{item_id}?delete_files=false", method="DELETE")  # the files stay
        new_id, errors = add(key)
        if errors or not new_id:
            back, _ = add(old_tmdb) if old_tmdb else (None, None)
            raise ValueError(f"Reelix would not take the new match ({(errors or [{}])[0].get('message', 'no reason given')}). "
                             + ("The old match is back." if back else "Bring it in again from Library."))
        return {"said": f"Now matched to TMDB {key}. Reelix is reading its files", "id": new_id if isinstance(new_id, int) else None}
    if tab == "radio":
        old = _api(reelix, f"/radio/shows/{item_id}") or {}
        provider, _, ext = key.partition(":")
        if f"{old.get('provider')}:{old.get('external_id')}" == key:
            return {"said": "That is already its match", "id": item_id}
        body = {"provider": provider, "external_id": ext, "follow": old.get("follow") or "all", "monitored": old.get("monitored", True)}
        if old.get("root_folder_id"):
            body["root_folder_id"] = old["root_folder_id"]
        _api(reelix, f"/radio/shows/{item_id}", method="DELETE")  # its files in the library stay
        try:
            show = _api(reelix, "/radio/shows", method="POST", body=body) or {}
        except services.ServiceError as e:
            _api(reelix, "/radio/shows", method="POST", body={**body, "provider": old.get("provider"), "external_id": old.get("external_id")})
            raise ValueError(f"Reelix would not take the new match ({e}). The old match is back.") from None
        if str(show.get("id", "")).isdigit():
            try:
                _api(reelix, f"/radio/shows/{int(show['id'])}/search", method="POST", body={})
            except services.ServiceError:
                pass
        return {"said": f"Now matched to {show.get('title') or 'the show you chose'}. Reelix is searching for its episodes",
                "id": show.get("id")}
    if tab in ("audiobooks", "books"):
        book = _api(reelix, f"/books/{item_id}") or {}
        author = _api(reelix, f"/authors/{book.get('author_id')}") or {}
        fmt = "audiobook" if tab == "audiobooks" else "ebook"
        path = author.get("audio_path") if fmt == "audiobook" else author.get("path")
        if not path:
            raise ValueError("Reelix gave no folder for this author")
        roots = _api(reelix, "/bookrootfolders") or []
        root = _root_for([r for r in roots if r.get("kind") == fmt], path)
        if not root:
            raise ValueError("The author's folder is not in one of Reelix's book folders")
        profiles = _api(reelix, f"/qualityprofiles?kind={fmt}") or []
        field = "audio_quality_profile_id" if fmt == "audiobook" else "quality_profile_id"
        old_ol = author.get("openlibrary_id")

        def add(ol):
            out = _api(reelix, "/bookimport", method="POST", timeout=300, body={"root_folder_id": root["id"], "items": [
                {"path": path, "openlibrary_id": ol, "monitor": "existing", field: author.get(field) or (profiles[0]["id"] if profiles else None)}]}) or {}
            return (out.get("added") or [None])[0], out.get("errors") or []
        _api(reelix, f"/authors/{author['id']}?delete_files=false", method="DELETE")  # the files stay
        new_id, errors = add(key)
        if errors or not new_id:
            back, _ = add(old_ol) if old_ol else (None, None)
            raise ValueError(f"Reelix would not take the new author ({(errors or [{}])[0].get('message', 'no reason given')}). "
                             + ("The old match is back." if back else "Bring the folder in again from Library."))
        return {"said": f"The folder {os.path.basename(path)} is now matched to Open Library {key}. Reelix is reading its books",
                "id": None}
    raise ValueError("Change match works for films, series, radio, audiobooks and books")
