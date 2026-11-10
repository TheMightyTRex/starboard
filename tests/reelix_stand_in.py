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
        # Reelix's own naming defaults (reelix-import naming/mod.rs) and background pace.
        self.naming = {"rename_files": True, "replace_illegal_characters": True, "colon_replacement": "dash",
                       "movie_folder_format": "{Movie CleanTitle} ({Release Year})",
                       "movie_file_format": "{Movie CleanTitle} ({Release Year}) [{Quality Full}]",
                       "series_folder_format": "{Series TitleYear}", "season_folder_format": "Season {season:00}",
                       "specials_folder_format": "Specials",
                       "standard_episode_format": "{Series TitleYear} - S{season:00}E{episode:00} - {Episode CleanTitle}",
                       "daily_episode_format": "", "anime_episode_format": "", "multi_episode_style": "prefixed_range",
                       "max_file_name_bytes": 255, "max_path_bytes": 4096}
        self.pace = "normal"
        self.backups = [{"name": "reelix-2026-11-08.zip", "kind": "scheduled", "size_bytes": 5 * 10 ** 6, "created_at": "2026-11-08T03:00:00Z", "version": "0.9.0"}]
        self.backup_settings = {"interval_days": 7, "retention": 5}
        self.tasks_run = []
        self.direct = {"enabled": False, "output_dir": "/config/downloads", "ffmpeg": "ffmpeg", "yt_dlp": "yt-dlp", "spotify_credentials": ""}
        self.direct_queue = []
        self.spotify = {"connected": False, "username": None, "credentials_path": "", "pending": False, "error": None}
        self.other = {"/settings/mediamanagement": {"import_mode": "hardlink_or_copy", "minimum_free_space_mb": 100, "extra_file_extensions": ["srt"],
                                                   "delete_empty_folders": False, "recycle_bin_path": None},
                      "/settings/books": {"write_metadata": True, "metadata_language": "en"}, "/settings/music": {"write_tags": True}}
        self.folders = {"/rootfolders": [{"id": 1, "path": "/data/media/movies", "media_kind": "movie", "free_space": 10 ** 12, "accessible": True}],
                        "/bookrootfolders": [], "/musicrootfolders": [], "/radio/rootfolders": []}
        self.users = [{"id": 1, "username": "admin", "display_name": "admin", "auth_source": "local", "permissions": 1},
                      {"id": 2, "username": "sam", "display_name": "Sam", "auth_source": "jellyfin", "permissions": (1 << 5) | (1 << 6) | (1 << 13)}]
        self.metadata = {"tmdb_api_key": None, "tmdb_read_token": None, "language": "en-GB", "region": "GB"}
        self.request_settings = {"movie": {"profile_id": 1, "root_folder_id": None, "tags": []}, "series": {"profile_id": 1, "root_folder_id": None, "tags": []},
                                 "default_permissions": (1 << 5) | (1 << 6) | (1 << 13), "auto_approve_movie": False, "auto_approve_series": False}
        q = lambda name, allowed=True: {"quality": name, "allowed": allowed}  # noqa: E731
        self.profiles = [
            {"id": 1, "name": "HD-1080p", "language": "English", "upgrade_allowed": True, "cutoff": 21,
             "items": [q("HDTV-720p", False), q("WEBDL-720p"), q("HDTV-1080p", False),
                       {"id": 1000, "name": "WEB 1080p", "items": ["WEBDL-1080p", "WEBRip-1080p"], "allowed": True},
                       q("Bluray-1080p"), q("WEBDL-2160p", False), q("Bluray-2160p", False)],
             "format_items": [{"format_id": 1, "score": 50}, {"format_id": 4, "score": -10000}],
             "min_format_score": 0, "cutoff_format_score": 0, "max_size_mb": 20000},
            {"id": 2, "name": "Ultra-HD", "language": "English", "upgrade_allowed": True, "cutoff": 26,
             "items": [q("WEBDL-1080p", False), q("Bluray-1080p", False), q("WEBDL-2160p"), q("Bluray-2160p"), q("Remux-2160p", False)],
             "format_items": [{"format_id": 2, "score": 100}], "min_format_score": 0, "cutoff_format_score": 0},
            {"id": 3, "name": "Music", "family": "music", "language": None, "items": [], "cutoff": 0, "upgrade_allowed": False}]
        self.formats = [{"id": 1, "name": "HEVC (smaller files)", "specifications": []}, {"id": 2, "name": "HDR", "specifications": []},
                        {"id": 3, "name": "English audio", "specifications": []}, {"id": 4, "name": "3D", "specifications": []}]
        self.calls = []

    def preview(self, naming):
        """Example names from the formats, as Reelix's /naming/preview does, with a brace problem as an error."""
        sample = {"Movie CleanTitle": "The Zone of Interest", "Release Year": "2023", "Quality Full": "Bluray-1080p",
                  "Series TitleYear": "Ghosts (2021)", "Episode CleanTitle": "Ghost Hunter", "season:00": "06",
                  "season": "6", "episode:00": "01"}
        out, errors = {}, []
        for field, key in (("movie_folder_format", "movie_folder"), ("movie_file_format", "movie_file"),
                           ("series_folder_format", "series_folder"), ("season_folder_format", "season_folder"),
                           ("standard_episode_format", "standard_episode")):
            text = naming.get(field, "")
            if text.count("{") != text.count("}"):
                errors.append({"field": field, "message": "unbalanced braces"})
            for k, v in sample.items():
                text = text.replace("{" + k + "}", v)
            out[key] = text
        return {**out, "multi_episode": "", "daily_episode": "", "anime_episode": "", "errors": errors}

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
        if path == "/downloads/settings":
            if method == "PUT":
                self.direct = body
            return 200, self.direct, None
        if path == "/downloads/health":
            return 200, [{"tool": "yt-dlp", "available": True, "detail": ""}, {"tool": "ffmpeg", "available": True, "detail": ""}], None
        if path == "/downloads/spotify":
            return 200, self.spotify, None
        if path == "/downloads/spotify/login":
            self.spotify["pending"] = True
            return 200, {"auth_url": "https://accounts.spotify.com/authorize?made-up", "automatic": False}, None
        if path == "/downloads/spotify/login/finish":
            self.spotify.update(connected=True, username="sam", pending=False)
            return 200, self.spotify, None
        if path == "/downloads/preview":
            return 200, {"title": "A made-up album", "items": ["One", "Two"], "truncated": False}, None
        if path == "/downloads":
            if method == "POST":
                self.direct_queue.append({"id": len(self.direct_queue) + 1, "request": body, "state": "queued", "progress": None, "message": "",
                                          "output_dir": self.direct["output_dir"], "created_at": 0, "updated_at": 0})
                return 201, self.direct_queue[-1], None
            return 200, self.direct_queue, None
        if path == "/system/backups":
            if method == "POST":
                self.backups.append({"name": "reelix-now.zip", "kind": "manual", "size_bytes": 1000, "created_at": "2026-11-09T20:00:00Z"})
            return 200, {"backups": self.backups, "settings": self.backup_settings, "backup_dir": "/config/backups", "pending_restore": None}, None
        if path == "/system/backups/settings":
            self.backup_settings = body
            return 200, body, None
        if path.startswith("/system/logs"):
            return 200, {"file": "reelix.log", "entries": [{"time": "2026-11-09T20:00:00Z", "level": "warn", "target": "x", "message": "A made-up warning"}],
                         "truncated": False}, None
        if path == "/system/tasks":
            return 200, [{"kind": "refresh_library", "name": "Refresh the library", "enabled": True, "running": False, "last_run": None, "next_run": None}], None
        if path.startswith("/system/jobs"):
            return 200, [], None
        if path.startswith("/system/tasks/") and path.endswith("/run"):
            self.tasks_run.append(path.split("/")[3])
            return 202, {"job_id": 1}, None
        if path in self.other:
            if method == "PUT":
                self.other[path] = body
            return 200, self.other[path], None
        base = "/" + "/".join(path.strip("/").split("/")[:-1]) if path.rstrip("/").split("/")[-1].isdigit() else path
        if base in self.folders:
            if method == "POST":
                item = {"id": next(self.ids) + 100, "path": body["path"], "media_kind": body.get("media_kind"), "kind": body.get("kind"), "accessible": True}
                self.folders[base].append(item)
                return 201, item, None
            if method == "DELETE":
                self.folders[base] = [f for f in self.folders[base] if f["id"] != int(path.rsplit("/", 1)[1])]
                return 204, None, None
            return 200, self.folders[base], None
        if path == "/users":
            return 200, self.users, None
        if path.startswith("/users/"):
            u = next((x for x in self.users if x["id"] == int(path.rsplit("/", 1)[1])), None)
            if method == "PUT" and u:
                u["permissions"] = body["permissions"]
            return 200, u, None
        if path == "/settings/metadata":
            if method == "PUT":
                self.metadata = {**self.metadata, **body}
            return 200, self.metadata, None
        if path == "/settings/requests":
            if method == "PUT":
                self.request_settings = {**self.request_settings, **body}
            return 200, self.request_settings, None
        if path == "/qualityprofiles":
            return 200, self.profiles, None
        if path == "/customformats":
            return 200, self.formats, None
        if path.startswith("/qualityprofiles/") and method == "GET":
            pid = int(path.rsplit("/", 1)[1])
            found = next((p for p in self.profiles if p["id"] == pid), None)
            return (200, found, None) if found else (404, {"error": "not found"}, None)
        if path.startswith("/qualityprofiles/") and method == "PUT":
            pid = int(path.rsplit("/", 1)[1])
            self.profiles = [body if p["id"] == pid else p for p in self.profiles]
            return 200, body, None
        if path == "/settings/naming":
            if method == "PUT":
                self.naming = {**self.naming, **body}
            return 200, self.naming, None
        if path == "/naming/preview":
            return 200, self.preview(body if method == "POST" else self.naming), None
        if path == "/system/background-work":
            if method == "PUT":
                if body.get("pace") not in ("normal", "relaxed", "light", "minimal"):
                    return 400, {"error": "invalid", "message": "unknown pace"}, None
                self.pace = body["pace"]
            return 200, {"pace": self.pace}, None
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
