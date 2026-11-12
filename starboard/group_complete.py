"""Complete collections and series (owner, 12 November 2026: "Audiobook series needs completing, like the collections;
an Add missing button when you open the collection").

- Films, Collections: Reelix's own collections (GET /collections) list every film in each TMDB collection, with the
  ones in the library. A banner counts them all; the missing ones show as outlines; Add missing adds them to Reelix
  with the collection's own quality and folder.
- Audiobooks, Series: Reelix's books carry no series, so the series come from Audiobookshelf (its series and the
  books in each, with their numbers). The books you do not have come from Audible's public catalogue (searched by
  the series' name, only books whose series is exactly that name), kept a week. Add missing looks each one up in
  Reelix (Open Library) by title and author and adds it as an audiobook.

Every answer is kept (an hour for your own apps, a week for Audible), so a page view costs nothing extra."""
import json
import re
import urllib.parse
import urllib.request

from . import services

AUDIBLE = "https://api.audible.co.uk/1.0/catalog/products"
KEEP_OWN, KEEP_AUDIBLE = 3600, 7 * 86400


def fold(text):
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower().replace("&", "and"))


def _num(seq):
    try:
        return float(str(seq).split("-")[0])
    except (TypeError, ValueError):
        return 9999.0


# Films --------------------------------------------------------------------------------------------------------

def collections(reelix):
    """{folded name: {name, id, profile, folder, films: [{tmdb_id, title, year, poster, have, in_reelix}]}}."""
    def ask():
        out = {}
        for c in services._api(reelix, "/collections", timeout=20) or []:
            films = [{"tmdb_id": m.get("tmdb_id"), "title": m.get("title") or "", "year": m.get("year"), "poster": m.get("poster") or "",
                      "have": bool(m.get("has_file")), "in_reelix": bool(m.get("movie_id"))} for m in c.get("movies") or []]
            films.sort(key=lambda f: (f["year"] or 9999, f["title"]))
            out[fold(c.get("title"))] = {"name": c.get("title") or "", "id": c.get("id"), "profile": c.get("quality_profile_id"),
                                         "folder": c.get("root_folder_id"), "films": films}
        return out
    return services.cached("complete:collections", KEEP_OWN, ask)


# Audiobooks ---------------------------------------------------------------------------------------------------

def _abs(all_services):
    return next((s for s in all_services if s.get("type") == "audiobookshelf" and s.get("url") and s.get("api_key")), None)


def _abs_get(svc, path):
    req = urllib.request.Request(svc["url"].rstrip("/") + path, headers={"Authorization": f"Bearer {svc['api_key']}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:  # the owner's own Audiobookshelf  # nosec B310
        return json.loads(r.read(16 * 1024 * 1024) or b"{}")


def abs_series(all_services):
    """{folded name: {name, books: [{title, author, seq, key}]}} from Audiobookshelf's book libraries."""
    svc = _abs(all_services)
    if not svc:
        return {}

    def ask():
        out = {}
        for lib in (_abs_get(svc, "/api/libraries").get("libraries") or []):
            if lib.get("mediaType") != "book":
                continue
            page = 0
            while page < 20:
                got = _abs_get(svc, f"/api/libraries/{lib['id']}/series?limit=100&page={page}")
                for s in got.get("results") or []:
                    books = []
                    for b in s.get("books") or []:
                        md = (b.get("media") or {}).get("metadata") or {}
                        m = re.search(r"#\s*([\d.]+)", md.get("seriesName") or "")
                        books.append({"title": md.get("title") or "", "author": md.get("authorName") or "",
                                      "seq": b.get("sequence") or (m.group(1) if m else ""),
                                      "key": fold(md.get("title")) + "|" + fold((md.get("authorName") or "").split(",")[0])})
                    books.sort(key=lambda x: _num(x["seq"]))
                    out[fold(s.get("name"))] = {"name": s.get("name") or "", "books": books}
                if (page + 1) * 100 >= int(got.get("total") or 0):
                    break
                page += 1
        return out
    return services.cached("complete:abs-series", KEEP_OWN, ask)


def audible_series(name, opener=None):
    """Every book Audible lists in the series called exactly `name`: [{title, seq, author, asin}], numbered order."""
    def ask():
        q = urllib.parse.urlencode({"keywords": name, "response_groups": "series,product_desc,contributors", "num_results": 50,
                                    "products_sort_by": "Relevance"})
        req = urllib.request.Request(f"{AUDIBLE}?{q}", headers={"User-Agent": services.USER_AGENT, "Accept": "application/json"})
        with (opener or urllib.request.build_opener()).open(req, timeout=20) as r:  # a fixed address  # nosec B310
            got = json.loads(r.read(4 * 1024 * 1024) or b"{}")
        seen, out = set(), []
        for p in got.get("products") or []:
            for s in p.get("series") or []:
                if fold(s.get("title")) != fold(name):
                    continue
                key = s.get("sequence") or p.get("asin")
                if key in seen:
                    continue
                seen.add(key)
                out.append({"title": p.get("title") or "", "seq": s.get("sequence") or "", "asin": p.get("asin") or "",
                            "author": ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:2])})
        return sorted(out, key=lambda b: _num(b["seq"]))
    try:
        return services.cached(f"complete:audible:{fold(name)}", KEEP_AUDIBLE, ask)
    except Exception:  # noqa: BLE001 - Audible busy or away: the series shows what you have
        return []


def audible_known(name):
    """Audible's list for a series when it is already kept, else None (the Series page never waits on Audible)."""
    import time
    hit = services._cache.get(f"complete:audible:{fold(name)}")
    return hit[1] if hit and time.monotonic() - hit[0] < KEEP_AUDIBLE else None


def banners(tab, found, reelix, all_services):
    """Completes the Collections and Series banners: every film in a collection, and each series' books with the
    missing ones Audible lists (when already kept)."""
    from .library import poster_allowed, small

    def pic(url):
        url = small(url or "")
        return f"/api/library/lookup-poster?src={urllib.parse.quote(url, safe='')}" if url and poster_allowed(url) else ""
    if tab == "films":
        cols = collections(reelix)
        for g in found:
            c = cols.get(fold(g["name"]))
            if not c:
                continue
            films = c["films"]
            years = [str(f["year"]) for f in films if f["year"]]
            g.update(count=len(films), have=sum(1 for f in films if f["have"]),
                     years=(years[0] if years[0] == years[-1] else f"{years[0]} to {years[-1]}") if years else g.get("years", ""),
                     films=[{"title": f["title"], "year": str(f["year"] or ""), "have": f["have"], "poster": pic(f["poster"])} for f in films[:6]])
    elif tab in ("audiobooks", "books"):
        series = abs_series(all_services)
        for g in found:
            s = series.get(fold(g["name"]))
            if not s:
                continue
            known = audible_known(s["name"]) or []
            have_seq = {_num(b["seq"]) for b in s["books"] if b["seq"]}
            extra = [a for a in known if not (a["seq"] and _num(a["seq"]) in have_seq)]
            g.update(count=len(s["books"]) + len(extra), have=len(s["books"]))
    return found


def tag_audiobooks(index, all_services):
    """Gives each audiobook in the index the Audiobookshelf series it belongs to (matched by title and author), so the
    Series page and an opened series work. Changes only this copy of the index."""
    series = abs_series(all_services)
    if not series:
        return index
    by_book = {}
    for s in series.values():
        for b in s["books"]:
            by_book.setdefault(b["key"], []).append(s["name"])
            by_book.setdefault(b["key"].split("|")[0] + "|", []).append(s["name"])
    for e in index["items"]:
        author = fold((e.get("au") or e.get("m") or "").split(",")[0])
        names = by_book.get(fold(e.get("t")) + "|" + author) or by_book.get(fold(e.get("t")) + "|")
        if names:
            e["g"] = sorted(set((e.get("g") or []) + names))
    return index


# Both ---------------------------------------------------------------------------------------------------------

def detail(reelix, all_services, tab, name):
    """One collection or series, complete: {name, total, have, items: [{title, year or seq, have, poster, key}],
    missing: n, source}. Films from Reelix; audiobooks from Audiobookshelf and Audible."""
    if tab == "films":
        c = collections(reelix).get(fold(name))
        if not c:
            return None
        items = [{"title": f["title"], "when": str(f["year"] or ""), "have": f["have"], "wanted": f["in_reelix"] and not f["have"],
                  "poster": f["poster"], "key": f"tmdb:{f['tmdb_id']}"} for f in c["films"] if f["tmdb_id"]]
        source = "TMDB, through Reelix"
    elif tab in ("audiobooks", "books"):  # books share the series (12 November 2026)
        s = abs_series(all_services).get(fold(name))
        if not s:
            return None
        have = {(_num(b["seq"]), fold(b["title"])) for b in s["books"]}
        have_seq = {_num(b["seq"]) for b in s["books"] if b["seq"]}
        items = [{"title": b["title"], "when": f"Book {b['seq']}" if b["seq"] else "", "have": True, "wanted": False, "poster": "",
                  "key": "", "author": b["author"]} for b in s["books"]]
        for a in audible_series(s["name"]):
            if (a["seq"] and _num(a["seq"]) in have_seq) or any(fold(a["title"]) == t for _, t in have):
                continue
            items.append({"title": a["title"], "when": f"Book {a['seq']}" if a["seq"] else "", "have": False, "wanted": False,
                          "poster": "", "key": f"audible:{a['asin']}", "author": a["author"]})
        items.sort(key=lambda i: _num(i["when"].replace("Book ", "")))
        source = "Audiobookshelf, and Audible for the books you do not have"
    else:
        return None
    missing = [i for i in items if not i["have"] and not i["wanted"]]
    return {"name": name, "total": len(items), "have": sum(1 for i in items if i["have"]), "missing": len(missing), "items": items,
            "source": source}


def add_missing(data_dir, reelix, all_services, tab, name):
    """Adds every missing film or audiobook to Reelix. Returns {added: [titles], failed: [titles]}."""
    from . import library
    d = detail(reelix, all_services, tab, name)
    if not d:
        raise LookupError("That collection or series is not known")
    added, failed = [], []
    if tab == "films":
        c = collections(reelix)[fold(name)]
        choice = {"profile_id": c["profile"], "folder_id": c["folder"], "search": True}
        for i in d["items"]:
            if i["have"] or i["wanted"]:
                continue
            try:
                library.add(data_dir, reelix, "films", i["key"], {k: v for k, v in choice.items() if v})
                added.append(i["title"])
            except Exception:  # noqa: BLE001 - one film failing does not stop the rest
                failed.append(i["title"])
    else:
        for i in d["items"]:
            if i["have"] or i["wanted"]:
                continue
            try:
                rows = services._api(reelix, "/books/lookup", {"term": f"{i['title']} {i.get('author', '')}".strip()}, timeout=20) or []
                work = next((r.get("openlibrary_work_id") for r in rows if fold(r.get("title")) == fold(i["title"])), None) \
                    or (rows[0].get("openlibrary_work_id") if rows else None)
                if not work:
                    raise LookupError
                library.add(data_dir, reelix, "books", f"olw:{work}", {"formats": ["ebook" if tab == "books" else "audiobook"], "search": True})
                added.append(i["title"])
            except Exception:  # noqa: BLE001
                failed.append(i["title"])
    services.forget("complete:collections")
    return {"added": added, "failed": failed}
