"""A made-up Dispatcharr and Jellyfin for DASH-228, answering in the shapes their own code gives (Dispatcharr's
apps/accounts, apps/m3u, apps/epg and apps/channels views; Jellyfin's /System/Configuration/livetv and /LiveTv).
Used as an opener (it has .open(request, timeout)), by the unit tests and by the example server. Nothing is fetched.
"""
import io
import json
import threading
import urllib.error
import urllib.parse


class _Answer(io.BytesIO):
    def __init__(self, status, payload):
        super().__init__(b"" if payload is None else json.dumps(payload).encode())
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class StandIn:
    """Dispatcharr on any host but `jellyfin_host`; Jellyfin on that one. `calls` keeps (method, path, body)."""

    def __init__(self, jellyfin_host="jellyfin.example", allow_setup=True, admin_password=None, streams=0, prefix=""):
        self.lock = threading.Lock()
        self.prefix = prefix  # Dispatcharr's address ends in this (the example server's /dispatcharr)
        self.jellyfin_host = jellyfin_host
        self.allow_setup = allow_setup
        self.admin = None if admin_password is None else ("admin", admin_password)
        self.key = None
        self.playlists, self.guides, self.channels = [], [], []
        self.streams = list(range(1, streams + 1))  # stream ids, once a playlist is read
        self.tuners, self.listings = [], []
        self.calls = []
        self.refreshed = 0

    # an opener ------------------------------------------------------------------------------------------------
    def open(self, req, timeout=None):
        url = urllib.parse.urlsplit(req.full_url)
        body = json.loads(req.data) if req.data else None
        method = req.get_method()
        headers = {k.lower(): v for k, v in req.header_items()}
        with self.lock:
            self.calls.append((method, url.path + (f"?{url.query}" if url.query else ""), body))
            if url.hostname == self.jellyfin_host:
                status, payload = self._jellyfin(method, url.path, body)
            else:
                path = url.path[len(self.prefix):] if self.prefix and url.path.startswith(self.prefix) else url.path
                status, payload = self._dispatcharr(method, path, dict(urllib.parse.parse_qsl(url.query)), body, headers)
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "made up", {}, io.BytesIO(json.dumps(payload).encode()))
        return _Answer(status, payload)

    # Dispatcharr ----------------------------------------------------------------------------------------------
    def _signed_in(self, headers):
        if self.key and headers.get("x-api-key") == self.key:
            return True
        return headers.get("authorization") == "Bearer made-up-access"

    def _dispatcharr(self, method, path, query, body, headers):
        if path == "/api/accounts/initialize-superuser/":
            if method == "GET":
                return 200, {"superuser_exists": bool(self.admin)} if self.admin else \
                    {"superuser_exists": False, "client_ip": "172.18.0.5", "setup_allowed": self.allow_setup}
            if self.admin:
                return 400, {"error": "A superuser already exists"}
            if not self.allow_setup:
                return 403, {"error": "Setup not allowed from this address", "client_ip": "172.18.0.5", "setup_allowed": False}
            self.admin = (body["username"], body["password"])
            return 200, {"superuser_exists": True}
        if path == "/api/accounts/token/" and method == "POST":
            if (body.get("username"), body.get("password")) != self.admin:
                return 401, {"detail": "No active account found with the given credentials"}
            return 200, {"access": "made-up-access", "refresh": "made-up-refresh"}
        if not self._signed_in(headers):
            return 401, {"detail": "Authentication credentials were not provided."}
        if path == "/api/accounts/api-keys/" and method == "GET":
            return 200, {"key": self.key}
        if path == "/api/accounts/api-keys/generate/" and method == "POST":
            self.key = "made-up-dispatcharr-key"
            return 201, {"key": self.key, "user": {"id": 1, "username": "admin"}}
        for prefix, items in (("/api/m3u/accounts/", self.playlists), ("/api/epg/sources/", self.guides)):
            if path == prefix:
                if method == "GET":
                    return 200, list(items)
                item = {**body, "id": len(items) + 1, "status": "idle", "last_message": ""}
                item.pop("password", None)
                items.append(item)
                return 201, item
            if path.startswith(prefix) and method == "PATCH":
                item = next((i for i in items if i["id"] == int(path[len(prefix):].strip("/"))), None)
                if not item:
                    return 404, {"detail": "Not found."}
                item.update({k: v for k, v in body.items() if k != "password"})
                return 200, item
        if path.startswith("/api/m3u/refresh/") and method == "POST":
            self.refreshed += 1
            return 202, {"success": True}
        if path == "/api/channels/streams/" and method == "GET":
            mine = self.streams if self.playlists else []
            size = int(query.get("page_size") or 50)
            return 200, {"count": len(mine), "next": None, "previous": None,
                         "results": [{"id": i, "name": f"Stream {i}", "m3u_account": 1} for i in mine[:size]]}
        if path == "/api/channels/channels/" and method == "GET":
            size = int(query.get("page_size") or 50)
            return 200, {"count": len(self.channels), "results": self.channels[:size]}
        if path == "/api/channels/channels/from-stream/bulk/" and method == "POST":
            for n, sid in enumerate(body["stream_ids"], start=1):
                self.channels.append({"id": n, "name": f"Stream {sid}", "channel_number": n})
            return 202, {"task_id": "made-up-task", "stream_count": len(body["stream_ids"]), "status": "started"}
        return 404, {"detail": "Not found."}

    # Jellyfin -------------------------------------------------------------------------------------------------
    def _jellyfin(self, method, path, body):
        if path == "/System/Configuration/livetv":
            return 200, {"TunerHosts": list(self.tuners), "ListingProviders": list(self.listings)}
        if path == "/LiveTv/TunerHosts" and method == "POST":
            tuner = {**body, "Id": f"tuner{len(self.tuners) + 1}"}
            self.tuners.append(tuner)
            return 200, tuner
        if path == "/LiveTv/ListingProviders" and method == "POST":
            self.listings = [g for g in self.listings if g.get("Path") != body.get("Path")]
            listing = {**body, "Id": body.get("Id") or f"guide{len(self.listings) + 1}"}
            self.listings.append(listing)
            return 200, listing
        if path == "/ScheduledTasks":
            return 200, [{"Id": "refresh-guide", "Key": "RefreshGuide"}]
        if path.startswith("/ScheduledTasks/Running/"):
            return 204, None
        return 404, {"message": "made up: no such route"}
