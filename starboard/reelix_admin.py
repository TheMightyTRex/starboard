"""Reelix's admin settings from Starboard (DASH-154): sign in for one change, then sign out again.

Starboard keeps only Reelix's manager key. Reelix's providers (sites to search, download apps, media servers,
notifications and import lists) and its search settings need Reelix's admin rights, and an admin key could run any
command through Reelix's Custom Script notifier. So each change here signs in to Reelix with the admin password the
person has just typed (the `x-reelix-request` header Reelix wants for cookie sign-ins), makes the change, and signs
out again. Nothing of the sign-in is kept: not the password, not the session.

The forms come from Reelix itself: `/{kind}/schema` describes each kind of setting, so a field Reelix adds shows in
Starboard without a Starboard release. Starboard sends back only fields the schema names, with the kind of value the
schema gives. The schema list for sites to search is large (580 sites, about 2 MB), so the browser gets a slim list
(name, kind, public or not, language), kept here for 10 minutes, and asks for one site's fields when it is chosen.

Only Reelix's documented HTTP API is used; no Reelix code is copied (Reelix is GPL-3.0, Starboard MIT).
8 November 2026.
"""
import re
import threading
import time
import urllib.parse

from . import reelix_setup, reelix_sites, stack

KINDS = {
    "indexers": "Sites to search",
    "downloadclients": "Download apps",
    "mediaservers": "Media servers",
    "notifications": "Notifications",
    "importlists": "Import lists",
}
CATALOGUE_FOR = 600  # seconds a slim schema list is kept, then dropped (lightweight rule)
_cache = {}
_cache_lock = threading.Lock()


class WrongPassword(Exception):
    pass


def base_url(data_dir, services):
    """Reelix's address: the one Install apps gave it, or else the Reelix entry on the dashboard (a Reelix the person
    added by hand). The dialog shows this address, so the person sees where the password goes."""
    from . import stack
    url = stack.reelix_url(data_dir)
    if url:
        return url
    for s in services:
        if s.get("icon") == "reelix" and s.get("type") == "link" and s.get("url"):
            return str(s["url"]).rstrip("/")
    for s in services:
        if s.get("icon") == "reelix" and s.get("url"):
            return re.sub(r"/(radarr|sonarr|readarr|lidarr)/?$", "", str(s["url"]).rstrip("/"))
    return None


class Visit:
    """Signed in to Reelix as an admin for one change: `with Visit(base, password) as reelix: reelix.call(...)`.
    Signs out on the way out, whatever happened."""

    def __init__(self, base, password, user=reelix_setup.ADMIN, opener=None):
        if not base:
            raise ValueError("Starboard does not know where Reelix is. Add Reelix in Settings, Manage apps first")
        if not password:
            raise WrongPassword("Enter your Reelix password")
        self.base, self.password, self.user, self.opener = base, password, user or reelix_setup.ADMIN, opener
        self.session = None

    def __enter__(self):
        self.session = reelix_setup.Session(self.base, opener=self.opener)
        try:
            self.session.call("POST", "/auth/login", {"username": self.user, "password": self.password, "remember_me": False})
        except reelix_setup.ReelixError as e:
            if " 401 " in f" {e} " or "said 401" in str(e) or "said 403" in str(e):
                raise WrongPassword(f"Reelix did not accept that password for its user {self.user}") from None
            raise
        finally:
            self.password = None  # used once, then gone
        return self.session

    def __exit__(self, *exc):
        try:
            self.session.call("POST", "/auth/logout", ok=(200, 204, 401))
        except reelix_setup.ReelixError:
            pass  # the session ends on its own; nothing is kept here either way
        self.session = None
        return False


def _slim(kind, entry):
    s = entry.get("schema") or {}
    out = {"implementation": s.get("implementation"), "name": s.get("name") or s.get("implementation"),
           "description": s.get("description") or "", "source": entry.get("source")}
    for k in ("protocol", "privacy", "language"):
        if entry.get(k):
            out[k] = entry[k]
    if s.get("info_url"):
        out["info_url"] = s["info_url"]
    if kind != "indexers":
        out["fields"] = s.get("fields") or []  # short lists: the fields come with them
    return out


def catalogue(reelix, kind, base=""):
    """What can be added for this kind: the slim list, from Reelix's schema (kept for CATALOGUE_FOR seconds)."""
    now = time.time()
    key = (base or reelix.base, kind)
    with _cache_lock:
        for k in [k for k, (t, _) in _cache.items() if now - t > CATALOGUE_FOR]:
            del _cache[k]
        if key in _cache:
            return _cache[key][1]
    _, raw = reelix.call("GET", f"/{kind}/schema", timeout=60)
    slim = [_slim(kind, e) for e in raw or [] if isinstance(e, dict)]
    slim.sort(key=lambda x: (x.get("source") != "builtin", str(x["name"]).lower()))
    with _cache_lock:
        _cache[key] = (now, slim)
    return slim


def forget_catalogues():
    with _cache_lock:
        _cache.clear()


def schema_of(reelix, kind, implementation):
    """One implementation's full schema (its fields), or ValueError when Reelix has no such thing."""
    _, raw = reelix.call("GET", f"/{kind}/schema", timeout=60)
    for e in raw or []:
        s = (e or {}).get("schema") or {}
        if s.get("implementation") == implementation:
            return {**_slim(kind, e), "fields": s.get("fields") or []}
    raise ValueError(f"Reelix has nothing called {implementation} in {KINDS.get(kind, kind)}")


MASK = re.compile(r"^\*{3,}$|^•{3,}$")


def clean_settings(fields, settings, editing=False):
    """Only the fields the schema names, each as the kind of value the schema gives. A secret left as Reelix's mask
    (or empty, when editing) is sent back as it came, so Reelix keeps the saved one."""
    settings = settings if isinstance(settings, dict) else {}
    out, problems = {}, []
    for f in fields:
        name, kind = f.get("name"), f.get("type")
        if not name or name not in settings:
            continue
        v = settings[name]
        if v is None or v == "":
            if f.get("required") and not (editing and kind == "secret"):
                problems.append(f"{f.get('label') or name} is needed")
            if editing and kind == "secret":
                continue
            out[name] = None if kind in ("number", "select") else ([] if kind in ("list", "multi_select") else "")
            continue
        try:
            if kind == "bool":
                out[name] = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "on", "yes")
            elif kind == "number":
                n = float(v)
                out[name] = int(n) if n.is_integer() else n
            elif kind in ("list", "multi_select"):
                items = v if isinstance(v, list) else [x.strip() for x in re.split(r"[,\n]", str(v)) if x.strip()]
                out[name] = [int(x) if re.fullmatch(r"-?\d+", str(x)) else str(x) for x in items][:200]
            elif kind == "select":
                allowed = {str(o.get("value")): o.get("value") for o in f.get("options") or []}
                if allowed and str(v) not in allowed:
                    problems.append(f"{f.get('label') or name}: choose one of the choices")
                    continue
                out[name] = allowed.get(str(v), v)
            elif kind == "url":
                text = str(v).strip()
                if not re.match(r"^https?://[^\s/]+", text):
                    problems.append(f"{f.get('label') or name}: enter an address starting http:// or https://")
                    continue
                out[name] = text[:2000]
            elif kind == "secret" and MASK.match(str(v)):
                continue  # Reelix keeps the saved secret
            else:
                out[name] = str(v)[:4000]
        except (TypeError, ValueError):
            problems.append(f"{f.get('label') or name}: enter a number")
    if problems:
        raise ValueError(". ".join(problems))
    return out


def provider_body(schema, item, editing=False):
    name = str(item.get("name") or schema["name"]).strip()[:100]
    if not name:
        raise ValueError("Give it a name")
    priority = item.get("priority", 25)
    try:
        priority = max(1, min(50, int(priority)))
    except (TypeError, ValueError):
        priority = 25
    return {"implementation": schema["implementation"], "name": name, "enabled": bool(item.get("enabled", True)),
            "priority": priority, "tags": [int(t) for t in item.get("tags") or [] if str(t).isdigit()][:20],
            "settings": clean_settings(schema["fields"], item.get("settings"), editing)}


def listing(reelix, kind):
    """What Reelix has for this kind (secrets masked by Reelix), with each site's counters and state for indexers."""
    _, items = reelix.call("GET", f"/{kind}")
    items = [i for i in items or [] if isinstance(i, dict)]
    out = {"items": items}
    if kind == "indexers":
        try:
            _, stats = reelix.call("GET", "/indexers/stats")
            by_id = {s.get("indexer_id"): s for s in stats or []}
            for i in items:
                s = by_id.get(i.get("id")) or {}
                i["stats"] = {k: s.get(k) for k in ("queries", "rss_queries", "grabs", "failures", "avg_response_ms")}
        except reelix_setup.ReelixError:
            pass
        try:
            _, status = reelix.call("GET", "/indexers/definitions/status")
            out["definitions"] = {k: status.get(k) for k in ("loaded", "last_sync", "last_error", "syncing")}
        except reelix_setup.ReelixError:
            pass
    return out


def find(items, provider_id):
    return next((i for i in items if str(i.get("id")) == str(provider_id)), None)


def test(reelix, kind, item):
    schema = schema_of(reelix, kind, str(item.get("implementation", "")))
    editing = bool(item.get("id"))
    body = provider_body(schema, item, editing)
    if editing:
        body["id"] = int(item["id"])  # Reelix fills masked secrets in from the saved one
    _, result = reelix.call("POST", f"/{kind}/test", body, timeout=60, ok=(200, 201, 400, 422))
    return result if isinstance(result, dict) else {"ok": False, "message": "Reelix gave no answer to the test"}


def save(reelix, kind, item):
    schema = schema_of(reelix, kind, str(item.get("implementation", "")))
    if item.get("id"):
        _, have = reelix.call("GET", f"/{kind}")
        old = find(have or [], item["id"])
        if not old:
            raise ValueError("Reelix no longer has that one. Load the page again")
        body = provider_body(schema, item, editing=True)
        merged = {**(old.get("settings") or {}), **body["settings"]}
        # Masked secrets go back as Reelix sent them, which Reelix reads as "keep the saved one".
        body["settings"] = merged
        _, saved = reelix.call("PUT", f"/{kind}/{int(item['id'])}", body)
    else:
        _, saved = reelix.call("POST", f"/{kind}", provider_body(schema, item))
    return saved


def remove(reelix, kind, provider_id):
    reelix.call("DELETE", f"/{kind}/{int(provider_id)}", ok=(200, 204))


# The route -------------------------------------------------------------------------------------------------------

_ROUTE = re.compile(r"^/api/reelix/admin/(?P<kind>[a-z]+)/(?P<action>[a-z-]+)$")


def route(handler, method, path):
    """POST /api/reelix/admin/{kind}/{open|schema|test|save|remove} and /api/reelix/admin/search/{open|vpn}, with the
    Reelix password in the body (never in the address). Answers through the handler. A wrong password counts
    towards Starboard's own limit on password attempts."""
    app = handler.app
    m = _ROUTE.match(path)
    if method == "GET" and path == "/api/reelix/admin/about":
        return handler.json(200, about(app))
    if method != "POST" or not m:
        return handler.error(404, "Not found")
    kind, action = m.group("kind"), m.group("action")
    if kind not in KINDS and kind not in ("search", "library", "basics", "quality", "radio", "form", "folders", "people", "system", "direct"):
        return handler.error(404, "Starboard does not change that part of Reelix")
    body = handler.body()
    address = handler.client_address_text()
    if not app.limits.attempt(address):
        return handler.error(429, "Too many attempts. Wait 15 minutes and try again", reason="password")
    base = base_url(app.data_dir, app.config.data["services"])
    try:
        with Visit(base, str(body.get("password") or ""), str(body.get("user") or reelix_setup.ADMIN)) as reelix:
            app.limits.clear(address)
            out = _act(app, reelix, base, kind, action, body)
    except WrongPassword as e:
        return handler.error(401, str(e), reason="password")
    return handler.json(200, out)


def _act(app, reelix, base, kind, action, body):
    from . import logs
    if kind == "direct":  # YouTube and Spotify in the full version (DASH-216, 217)
        from . import reelix_direct as rd
        acts = {"open": lambda: rd.state(reelix), "save": lambda: rd.save(reelix, body.get("on"), body.get("folder")),
                "spotify-start": lambda: rd.spotify_start(reelix), "spotify-finish": lambda: rd.spotify_finish(reelix, body.get("address")),
                "spotify-off": lambda: rd.spotify_disconnect(reelix), "preview": lambda: rd.preview(reelix, body),
                "queue": lambda: rd.queue(reelix), "start": lambda: rd.start(reelix, body),
                "change": lambda: rd.change(reelix, body.get("id"), str(body.get("what", "")))}
        if action not in acts:
            raise ValueError("Not something Starboard does")
        out = acts[action]()
        if out.get("done"):
            logs.event("info", "reelix", out["done"])
        return out
    if kind == "system":  # Reelix's backups, logs and tasks in System (DASH-201, 202, 203)
        from . import reelix_system as rs
        acts = {"backups": lambda: rs.backups(reelix), "backup-now": lambda: rs.backup_now(reelix),
                "backup-settings": lambda: rs.backup_settings(reelix, body.get("every"), body.get("keep")),
                "restore": lambda: rs.restore(reelix, body.get("name")), "logs": lambda: rs.logs(reelix, str(body.get("level", "")), body.get("lines")),
                "tasks": lambda: rs.tasks(reelix), "run-task": lambda: rs.run_task(reelix, body.get("task"))}
        if action not in acts:
            raise ValueError("Not something Starboard does")
        out = acts[action]()
        if out.get("done"):
            logs.event("info", "reelix", out["done"])
        return out
    if kind == "form":  # Information, Files, Requests, Books, Music (DASH-193, 195, 197)
        from . import reelix_forms
        if action == "open":
            return reelix_forms.open_form(reelix, str(body.get("name", "")))
        if action == "save":
            out = reelix_forms.save_form(reelix, str(body.get("name", "")), body.get("values") or {})
            logs.event("info", "reelix", f"{out['title']} saved")
            return out
        raise ValueError("Not something Starboard does")
    if kind == "folders":  # library folders after set-up (DASH-194)
        from . import reelix_folders
        if action == "open":
            return reelix_folders.listing(reelix)
        if action in ("add", "remove"):
            out = reelix_folders.change(reelix, action, body)
            logs.event("info", "reelix", out["done"])
            return out
        raise ValueError("Not something Starboard does")
    if kind == "people":  # users and roles (DASH-199)
        from . import reelix_people
        if action == "open":
            return reelix_people.listing(reelix)
        if action == "role":
            out = reelix_people.set_role(reelix, body.get("id"), str(body.get("role", "")))
            logs.event("info", "reelix", out["done"])
            return out
        raise ValueError("Not something Starboard does")
    if kind == "basics":  # the basic settings (DASH-226)
        from . import reelix_basics, setup_answers
        if action == "open":
            return reelix_basics.state(reelix)
        if action == "test-tmdb":
            setup_answers.test_tmdb(body.get("tmdb"))
            return {"ok": True, "message": setup_answers.WORDS["tmdb"]["ok"]}
        if action == "save":
            out = reelix_basics.save(reelix, body.get("changes"))
            for line in out["done"]:
                logs.event("info", "reelix", line)
            return out
        raise ValueError("Not something Starboard does")
    if kind == "quality":  # Picture quality in full (DASH-196)
        from . import reelix_quality
        if action == "open":
            return reelix_quality.state(reelix)
        if action in ("choose", "save"):
            out = reelix_quality.choose(reelix, body.get("id")) if action == "choose" else reelix_quality.save(reelix, body.get("id"), body.get("changes"))
            for line in out["done"]:
                logs.event("info", "reelix", line)
            return out
        raise ValueError("Not something Starboard does")
    if kind == "radio":  # point Reelix's radio at Audiobookshelf's Radio library (radio import, 10 November 2026)
        from . import radio_import
        if action == "connect":
            out = radio_import.connect(reelix, app.config)
            for line in out["done"]:
                logs.event("info", "reelix", line)
            return out
        raise ValueError("Not something Starboard does")
    if kind == "library":  # naming and background pace (DASH-188, DASH-200)
        from . import reelix_library
        if action == "open":
            return reelix_library.state(reelix)
        if action == "preview":
            return reelix_library.preview(reelix, body.get("naming"))
        if action == "save":
            out = reelix_library.save(reelix, body.get("naming"), body.get("pace"))
            logs.event("info", "reelix", "Naming and background work saved")
            return out
        raise ValueError("Not something Starboard does")
    if kind == "search":
        if action == "open":
            return reelix_sites.search_state(reelix, app.data_dir)
        if action in ("vpn", "private"):
            done = (reelix_sites.set_vpn(reelix, app.data_dir, bool(body.get("on"))) if action == "vpn"
                    else reelix_sites.set_private(reelix, bool(body.get("on"))))
            logs.event("info", "reelix", done)
            return {"done": done, **reelix_sites.search_state(reelix, app.data_dir)}
        raise ValueError("Not something Starboard does")
    if action == "open":
        out = listing(reelix, kind)
        out["catalogue"] = catalogue(reelix, kind, base)
        if kind == "indexers":
            out["suggested"] = [i for i, _, _ in reelix_sites.SUGGESTED]
        if kind == "mediaservers":
            out["offers"] = reelix_sites.media_server_offers(app.config.data["services"], app.data_dir, out["items"])
            if out["items"]:
                from . import setup_left
                setup_left.record(app.data_dir, media_servers=True)
        if kind == "downloadclients":  # DASH-257: the ones that differ from Starboard's set-up, for Repair
            from . import download_repair
            out["repair"] = download_repair.needs(app.data_dir, out["items"])
        return out
    if action == "schema":
        return schema_of(reelix, kind, str(body.get("implementation", "")))
    item = body.get("item") if isinstance(body.get("item"), dict) else {}
    if action == "test":
        return test(reelix, kind, item)
    if action == "save":
        saved = save(reelix, kind, item)
        logs.event("info", "reelix", f"{KINDS[kind]}: saved {saved.get('name') if isinstance(saved, dict) else item.get('name')}")
        return {"saved": saved, **listing(reelix, kind)}
    if action == "remove":
        remove(reelix, kind, body.get("id"))
        logs.event("info", "reelix", f"{KINDS[kind]}: removed one ({body.get('id')})")
        return listing(reelix, kind)
    if action == "connect" and kind == "mediaservers":
        done = reelix_sites.connect_media_servers(reelix, app.config.data["services"], app.data_dir,
                                                  only=str(body.get("app") or "") or None)
        for line in done:
            logs.event("info", "reelix", line)
        if any(line.startswith("Connected") for line in done):
            from . import setup_left
            setup_left.record(app.data_dir, media_servers=True)
        return {"done": done, **listing(reelix, kind),
                "offers": reelix_sites.media_server_offers(app.config.data["services"], app.data_dir, listing(reelix, kind)["items"])}
    if action == "repair" and kind == "downloadclients":
        from . import download_repair
        done = download_repair.repair(reelix, app.data_dir)
        for line in done:
            logs.event("info", "reelix", line)
        out = listing(reelix, kind)
        return {"done": done, **out, "repair": download_repair.needs(app.data_dir, out["items"])}
    if action == "add-sites" and kind == "indexers":
        done = reelix_sites.add_sites(reelix, reelix_sites.clean_choice(body.get("sites")))
        for line in done:
            logs.event("info", "reelix", line)
        return {"done": done, **listing(reelix, kind)}
    raise ValueError("Not something Starboard does")


def about(app):
    """What the Settings, Reelix page needs before the password: where Reelix is, and what Starboard could connect."""
    from . import stack
    base = base_url(app.data_dir, app.config.data["services"])
    host = urllib.parse.urlparse(base).netloc if base else None
    return {"address": host, "installed_here": bool(stack.reelix_url(app.data_dir)),
            "vpn": reelix_sites.vpn_available(app.data_dir), "kinds": KINDS,
            "edition": stack.edition_of(stack.reelix_in_stack(app.data_dir)),
            "media_keys": [k for k in ("jellyfin", "audiobookshelf")
                           if any(s.get("type") == k and s.get("api_key") for s in app.config.data["services"])]}
