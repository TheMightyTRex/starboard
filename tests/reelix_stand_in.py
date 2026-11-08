"""A stand-in for Reelix's admin API, written from the API's behaviour (no Reelix code): sign-in and sign-out with
the x-reelix-request header, the provider kinds with schemas, test, save and remove, the search settings and site
counters. Used by tests/test_reelix_admin.py and by the help centre's example server (made-up data only, where
any password is taken: any_password=True).

    state = StandIn(password="...")
    status, answer = state.handle(method, path_after_api_v1, body, headers)
"""
import copy
import itertools
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FLAGS = [
    {"name": "enable_rss", "label": "Enable RSS", "type": "bool", "required": False, "default": True, "help": "Use this indexer for RSS sync", "advanced": False},
    {"name": "enable_automatic_search", "label": "Enable automatic search", "type": "bool", "required": False, "default": True, "advanced": False},
    {"name": "minimum_seeders", "label": "Minimum seeders", "type": "number", "required": False, "default": 1, "advanced": True},
]


def _site(impl, name, privacy, description, language="en-US", extra=()):
    return {"schema": {"implementation": impl, "name": name, "description": description, "info_url": "https://example.invalid/",
                       "fields": [{"name": "base_url", "label": "Site URL", "type": "url", "required": False,
                                   "default": "https://example.invalid/", "advanced": False}, *extra, *FLAGS]},
            "protocol": "torrent", "privacy": privacy, "language": language, "source": "definition"}


ACCOUNT = [{"name": "username", "label": "Username", "type": "text", "required": True, "advanced": False},
           {"name": "password", "label": "Password", "type": "secret", "required": True, "advanced": False}]
SCHEMAS = {
    "indexers": [
        {"schema": {"implementation": "torznab", "name": "Torznab", "description": "Any Torznab-compatible torrent indexer or proxy",
                    "fields": [{"name": "base_url", "label": "URL", "type": "url", "required": True, "advanced": False},
                               {"name": "api_key", "label": "API key", "type": "secret", "required": False, "advanced": False},
                               {"name": "categories", "label": "Categories", "type": "list", "required": False, "default": [2000, 5000], "advanced": False},
                               *FLAGS]}, "protocol": "torrent", "privacy": None, "language": None, "source": "builtin"},
        {"schema": {"implementation": "newznab", "name": "Newznab", "description": "Any Newznab-compatible Usenet indexer",
                    "fields": [{"name": "base_url", "label": "URL", "type": "url", "required": True, "advanced": False},
                               {"name": "api_key", "label": "API key", "type": "secret", "required": True, "advanced": False},
                               *FLAGS]}, "protocol": "usenet", "privacy": None, "language": None, "source": "builtin"},
        _site("definition:internetarchive", "Internet Archive", "public", "Internet Archive is a non-profit digital library of free books, films and music"),
        _site("definition:1337x", "1337x", "public", "1337x is a Public torrent site that offers verified torrent downloads",
              extra=[{"name": "sort", "label": "Sort requested from site", "type": "select", "required": False, "default": "time",
                      "options": [{"value": "time", "label": "created"}, {"value": "seeders", "label": "seeders"}], "advanced": False}]),
        _site("definition:eztv", "EZTV", "public", "EZTV is a Public torrent site for TV shows"),
        _site("definition:yts", "YTS", "public", "YTS is a Public torrent site specialising in HD movies of small size"),
        _site("definition:thepiratebay", "The Pirate Bay", "public", "The Pirate Bay is a Public BitTorrent site"),
        _site("definition:limetorrents", "LimeTorrents", "public", "LimeTorrents is a Public general torrent index"),
        _site("definition:torrentproject2", "TorrentProject2", "public", "TorrentProject2 is a Public torrent meta-search engine"),
        _site("definition:uindex", "Uindex", "public", "Uindex is a Public Torrent Tracker for MOVIES / TV / MUSIC / GENERAL"),
        _site("definition:examplehd", "Example HD", "private", "Example HD is a Private Torrent Tracker for HD films", extra=ACCOUNT),
        _site("definition:examplebooks", "Example Books", "semi-private", "Example Books is a Semi-Private tracker for books", extra=ACCOUNT),
        _site("definition:examplefr", "Exemple FR", "public", "Exemple is a FRENCH Public tracker", language="fr-FR"),
    ],
    "mediaservers": [
        {"schema": {"implementation": "jellyfin", "name": "Jellyfin", "description": "Library refresh, availability sync and watch history",
                    "fields": [{"name": "url", "label": "URL", "type": "url", "required": True, "placeholder": "http://jellyfin:8096", "advanced": False},
                               {"name": "api_key", "label": "API key", "type": "secret", "required": True, "advanced": False}]},
         "source": "builtin"},
        {"schema": {"implementation": "audiobookshelf", "name": "Audiobookshelf", "description": "Scans the matching Audiobookshelf library after audiobook imports",
                    "fields": [{"name": "url", "label": "URL", "type": "url", "required": True, "advanced": False},
                               {"name": "api_key", "label": "API token", "type": "secret", "required": True, "advanced": False},
                               {"name": "ebooks", "label": "Ebooks", "type": "bool", "required": False, "default": False, "advanced": False}]},
         "source": "builtin"},
    ],
    "downloadclients": [
        {"schema": {"implementation": "qbittorrent", "name": "qBittorrent", "description": "Torrents",
                    "fields": [{"name": "host", "label": "Host", "type": "text", "required": True, "advanced": False},
                               {"name": "port", "label": "Port", "type": "number", "required": True, "default": 8080, "advanced": False},
                               {"name": "password", "label": "Password", "type": "secret", "required": False, "advanced": False}]},
         "protocol": "torrent", "source": "builtin"},
    ],
    "notifications": [],
    "importlists": [],
}
SECRET_TYPES = {"secret"}


class StandIn:
    def __init__(self, password="example-password", user="admin", any_password=False):
        self.password, self.user, self.any_password = password, user, any_password
        self.lock = threading.Lock()
        self.sessions, self.logins, self.logouts = set(), 0, 0
        self.ids = itertools.count(1)
        self.items = {k: [] for k in SCHEMAS}
        self.search = {"rss_interval_minutes": 15, "allow_private_addresses": False, "flaresolverr_url": None, "proxy": None}
        self.calls = []

    def schema(self, kind, impl):
        return next((s["schema"] for s in SCHEMAS[kind] if s["schema"]["implementation"] == impl), None)

    def masked(self, kind, item):
        out = copy.deepcopy(item)
        schema = self.schema(kind, item["implementation"]) or {"fields": []}
        for f in schema["fields"]:
            if f["type"] in SECRET_TYPES and out["settings"].get(f["name"]):
                out["settings"][f["name"]] = "********"
        return out

    def add(self, kind, implementation, name, settings, enabled=True, **extra):
        item = {"id": next(self.ids), "kind": kind[:-1], "implementation": implementation,
                "implementation_name": (self.schema(kind, implementation) or {}).get("name", implementation), "name": name,
                "enabled": enabled, "priority": 25, "tags": [], "settings": settings, "error": None,
                "status": {"failure_count": 0, "disabled_until": None, "last_failure_reason": None} if kind == "indexers" else None,
                "created_at": "2026-11-08T20:00:00Z", "updated_at": "2026-11-08T20:00:00Z", **extra}
        self.items[kind].append(item)
        return item

    def handle(self, method, path, body=None, headers=None):
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.calls.append((method, path))
        cookie = headers.get("cookie", "")
        signed = any(f"reelix_session={s}" in cookie for s in self.sessions)
        if path == "/auth/login" and method == "POST":
            if body.get("username") != self.user or (body.get("password") != self.password and not (self.any_password and body.get("password"))):
                return 401, {"error": "unauthorized", "message": "invalid username or password"}, None
            self.logins += 1
            token = f"s{self.logins}"
            self.sessions.add(token)
            return 200, {"user": {"username": self.user}}, f"reelix_session={token}; Path=/; HttpOnly"
        if not signed:
            return 401, {"error": "unauthorized", "message": "sign in"}, None
        if method != "GET" and not headers.get("x-reelix-request"):
            return 403, {"error": "csrf", "message": "missing x-reelix-request"}, None
        if path == "/auth/logout" and method == "POST":
            self.logouts += 1
            for s in list(self.sessions):
                if f"reelix_session={s}" in cookie:
                    self.sessions.discard(s)
            return 204, None, "reelix_session=; Max-Age=0; Path=/"
        if path == "/settings/indexers":
            if method == "PUT":
                self.search = {**self.search, **{k: body.get(k) for k in self.search if k in body}}
            return 200, self.search, None
        if path == "/indexers/stats":
            return 200, [{"indexer_id": i["id"], "name": i["name"], "enabled": i["enabled"], "queries": 12 + i["id"],
                          "rss_queries": 40, "grabs": i["id"] % 4, "failures": 1 if i["status"]["failure_count"] else 0,
                          "avg_response_ms": 900 + 100 * i["id"], "status": i["status"]} for i in self.items["indexers"]], None
        if path == "/indexers/definitions/status":
            return 200, {"loaded": len(SCHEMAS["indexers"]) - 2, "last_sync": "2026-11-08T06:00:00Z", "last_error": None, "syncing": False}, None
        parts = path.strip("/").split("/")
        kind = parts[0]
        if kind not in SCHEMAS:
            return 404, {"error": "not_found", "message": "no such route"}, None
        if parts[1:] == ["schema"]:
            return 200, SCHEMAS[kind], None
        if parts[1:] == [] and method == "GET":
            return 200, [self.masked(kind, i) for i in self.items[kind]], None
        if parts[1:] == [] and method == "POST":
            if "blocked" in json.dumps(body.get("settings", {})):
                return 400, {"error": "invalid", "message": "blocked address: 192.168.1.9"}, None
            return 201, self.masked(kind, self.add(kind, body["implementation"], body["name"], dict(body.get("settings") or {}),
                                                   enabled=body.get("enabled", True))), None
        if parts[1:] == ["test"] or (len(parts) == 3 and parts[2] == "test"):
            settings = (body or {}).get("settings") or {}
            ok = "fails" not in json.dumps(settings) and "fails" not in json.dumps(body or {})
            return 200, {"ok": ok, "message": None if ok else "connection: could not reach the site",
                         "checks": [{"name": "connection", "ok": ok, "message": None if ok else "could not reach the site"}]}, None
        if len(parts) == 2 and parts[1].isdigit():
            item = next((i for i in self.items[kind] if i["id"] == int(parts[1])), None)
            if not item:
                return 404, {"error": "not_found", "message": "no such provider"}, None
            if method == "DELETE":
                self.items[kind].remove(item)
                return 204, None, None
            if method == "PUT":
                settings = {k: (item["settings"].get(k) if v == "********" else v) for k, v in (body.get("settings") or {}).items()}
                item.update({"name": body["name"], "enabled": body.get("enabled", True), "priority": body.get("priority", 25),
                             "settings": settings})
                return 200, self.masked(kind, item), None
        return 404, {"error": "not_found", "message": "no such route"}, None


def serve(state, prefix=""):
    """Runs the stand-in on a free port on this computer; returns (server, base address)."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _do(self, method):
            path = self.path.split("?")[0]
            if not path.startswith(prefix + "/api/v1"):
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            with state.lock:
                status, answer, cookie = state.handle(method, path[len(prefix) + 7:], body, dict(self.headers))
            raw = json.dumps(answer).encode() if answer is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self._do("GET")

        def do_POST(self):
            self._do("POST")

        def do_PUT(self):
            self._do("PUT")

        def do_DELETE(self):
            self._do("DELETE")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}{prefix}"
