"""The web server: static pages, the JSON API and the security rules around both."""

import datetime as dt
import gzip
import hashlib
import json
import mimetypes
import os
import posixpath
import ipaddress
import re
import secrets
import socket
import threading
import time
import urllib.parse
import urllib.request
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import access, auth, backup, containers, copyset, discovery, icons, jobs, listening, livetv, logs, migrate, posters, releases, schedule, services, stack, sysinfo, uxnotes, watch
from .config import Config, ConfigError, new_setup_token, same_server, validate_service

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
COOKIE = "starboard_session"
MAX_BODY = 64 * 1024

PUBLIC_PAGES = {"/login.html", "/setup.html"}
PUBLIC_PREFIXES = ("/css/", "/js/", "/fonts/", "/icons/")
PUBLIC_FILES = {"/favicon.svg", "/icon-app.svg", "/manifest.webmanifest"}

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data: https:; style-src 'self'; script-src 'self'; "
        "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("application/manifest+json", ".webmanifest")


def read_version():
    try:
        with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


_static = {}
_static_lock = threading.Lock()


def static_file(full):
    """(bytes, gzip bytes or None, ETag, content type) for a file under web/, read and compressed once and kept
    until the file changes. The whole web folder is well under a megabyte."""
    st = os.stat(full)
    key = (st.st_mtime_ns, st.st_size)
    with _static_lock:
        hit = _static.get(full)
        if hit and hit[0] == key:
            return hit[1]
    with open(full, "rb") as f:
        data = f.read()
    kind = mimetypes.guess_type(full)[0] or "application/octet-stream"
    text = kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml", "application/manifest+json")
    if text:
        kind += "; charset=utf-8"
    packed = gzip.compress(data, 9) if text and len(data) > 1024 else None
    tag = '"' + hashlib.sha256(data).hexdigest()[:20] + '"'
    with _static_lock:
        _static[full] = (key, (data, packed, tag, kind))
    return data, packed, tag, kind


class App:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.config = Config(data_dir)
        self.uxnotes = uxnotes.UxNotes(data_dir)
        self.log = logs.start(data_dir, lambda: self.config.data["logs"], lambda: [self.config.data.get("site_name", "")])
        self.sessions = auth.Sessions(data_dir)
        if os.path.exists(os.path.join(data_dir, "reset-password")):
            self._reset_password(data_dir)
        self.limits = auth.RateLimit()
        self.version = read_version()
        since = self.config.data.get("version_since") or {}
        if since.get("version") != self.version:  # the time this version first started: About shows it
            self.config.data["version_since"] = {"version": self.version, "since": time.time()}
            self.config.save()
        self.disks = sysinfo.disk_paths_from_env()
        self.history = (sysinfo.History(data_dir, lambda: self.config.data["performance"])
                        if os.environ.get("STARBOARD_HISTORY", "1") != "0" else None)
        self.disk_temps = sysinfo.DiskTemps(data_dir)
        perf = lambda: self.config.data["performance"]  # noqa: E731
        self.usage = sysinfo.Usage(data_dir, perf, self.disks if os.environ.get("STARBOARD_USAGE", "1") != "0" else ())
        self.space = sysinfo.SpaceLog(data_dir, perf)
        if self.history:
            self.history.on_tick = self.record_space
        self.watch = watch.Watch(self)
        if os.environ.get("STARBOARD_WATCH", "1") != "0":
            self.watch.start()
        self.jobs = jobs.Jobs(self)
        if os.environ.get("STARBOARD_JOBS", "1") != "0":
            self.jobs.ensure()
        self.importing = None  # the watch history import that is running, if any
        self.import_result = None
        self.import_lock = threading.Lock()
        self.download_links = {}  # one-time links for server backup downloads: token: (file name, until)
        self.listening_busy = None  # reading listening progress, if it is running
        self.listening_read = None
        self.schedule = schedule.Schedule(self.config)
        if os.environ.get("STARBOARD_SCHEDULE", "1") != "0":
            self.schedule.start()
        self.repo = os.environ.get("STARBOARD_REPO", "")  # "owner/name" for the update check; optional
        self.trust_proxy = os.environ.get("STARBOARD_TRUST_PROXY", "") == "1"
        self.machine_name = socket.gethostname().split(".", 1)[0].lower()
        self.allowed_hosts = {h.strip().lower() for h in os.environ.get("STARBOARD_ALLOWED_HOSTS", "").split(",") if h.strip()}
        self.proxy_addresses = {"127.0.0.1", "::1", *[a.strip() for a in os.environ.get("STARBOARD_PROXY_ADDRESSES", "").split(",") if a.strip()]}
        self.port = int(os.environ.get("STARBOARD_PORT", "8095"))
        self.forced_host = os.environ.get("STARBOARD_HOST", "")  # when set, Settings cannot change the address
        self.on_network_change = None  # set by the runner in __main__
        self.setup_token = None
        self._latest = {"checked": 0, "tag": None}
        self._latest_lock = threading.Lock()
        if not self.needs_setup:
            self._remove_setup_token(data_dir)
        else:
            self.setup_token = new_setup_token(data_dir)
            print(f"[starboard] No password yet. Open the dashboard and enter this setup code: {self.setup_token}", flush=True)

    def _reset_password(self, data_dir):
        """./reset-password.sh, run on the server itself, leaves a file asking for this: no password, everyone
        signed out, and a new setup code at start-up. Apps and settings stay."""
        with self.config.lock:
            self.config.data["auth"]["password_hash"] = ""
            self.config.data["auth"]["session_version"] = self.config.data["auth"].get("session_version", 1) + 1
            self.config.save()
        self.sessions.end_all()
        self._remove_setup_token(data_dir)  # an old code from before the first password must not work again
        os.remove(os.path.join(data_dir, "reset-password"))
        logs.event("warning", "security", "The password was reset on the server. Everyone is signed out; a new setup code is in the log")

    @staticmethod
    def _remove_setup_token(data_dir):
        try:
            os.remove(os.path.join(data_dir, "setup-token"))
        except FileNotFoundError:
            pass

    def host_allowed(self, name):
        if not name or name in ("localhost",) or name.endswith(".localhost") or name in self.allowed_hosts:
            return True
        try:
            ipaddress.ip_address(name)
            return True
        except ValueError:
            pass
        first = name.split(".", 1)[0]
        return first == self.machine_name or any(name.endswith("." + h) for h in self.allowed_hosts if h.startswith("."))

    def listen_host(self):
        if self.forced_host:
            return self.forced_host
        return "0.0.0.0" if self.config.data.get("network_access", True) else "127.0.0.1"

    def network_info(self, client_ip):
        addresses = []
        try:
            # Finds the address other devices use. Connecting a UDP socket sends nothing.
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("192.0.2.1", 9))
                addresses.append(s.getsockname()[0])
        except OSError:
            pass
        return {
            "network_access": self.config.data.get("network_access", True),
            "addresses": [a for a in addresses if not a.startswith("127.")],
            "port": self.port,
            "forced_by": "STARBOARD_HOST" if self.forced_host else None,
            "you_are_on_this_computer": is_loopback(client_ip),
        }

    def record_space(self, snap=None):
        """The day's reading of used space, if not taken yet (no thread of its own)."""
        if self.disks and self.space.due():
            self.space.record((snap or sysinfo.snapshot(self.disks))["disks"])

    @property
    def needs_setup(self):
        return not self.config.data["auth"].get("password_hash")

    @property
    def session_version(self):
        return self.config.data["auth"].get("session_version", 1)

    def latest_release(self):
        """Asks GitHub for the newest version tag (what ./update.sh installs) at most every 6 hours. Off when
        STARBOARD_REPO is not set."""
        if not self.repo or not self.config.data.get("update_check", True):
            return None
        if not re.match(r"^[\w.-]+/[\w.-]+$", self.repo):
            return None
        with self._latest_lock:
            if time.time() - self._latest["checked"] < 6 * 3600:
                return self._latest["tag"]
            self._latest["checked"] = time.time()
            try:
                req = urllib.request.Request(
                    f"https://api.github.com/repos/{self.repo}/tags?per_page=100",
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "Starboard"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    self._latest["tag"] = newest_tag(t.get("name", "") for t in json.loads(resp.read(500000)))
            except (OSError, ValueError):
                pass
            return self._latest["tag"]


def newest_tag(names):
    """The highest vX.Y.Z among tag names (test builds such as v0.5.0-dev.1 are left out)."""
    found = [(tuple(int(x) for x in m.groups()), n) for n in names if (m := re.match(r"^v(\d+)\.(\d+)\.(\d+)$", n or ""))]
    return max(found)[1] if found else None


class PasswordProblem(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def is_loopback(address):
    try:
        ip = ipaddress.ip_address(address)
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        return ip.is_loopback
    except ValueError:
        return False


class Handler(BaseHTTPRequestHandler):
    timeout = 30  # an idle or slow connection is closed after 30 seconds, so it cannot hold a thread for ever
    server_version = "Starboard"
    sys_version = ""
    app: App = None  # set by make_server

    # Plumbing ----------------------------------------------------------

    def log_message(self, fmt, *args):
        # Keep logs free of query strings (search terms) and cookies.
        if not hasattr(self, "path"):
            return  # an idle connection timed out before sending a request
        path = self.path.split("?", 1)[0]
        if path == "/healthz" or path.startswith(("/css/", "/js/", "/icons/", "/fonts/", "/favicon")) or path.startswith("/api/icons/"):
            return  # files the browser loads say nothing about a problem
        status = args[1] if len(args) > 1 else ""
        if str(status) == "304":
            return
        logs.detail("request", f"{self.command} {path} {status}")

    def client_address_text(self):
        # X-Forwarded-For is believed only from the proxy itself (this computer, or STARBOARD_PROXY_ADDRESSES).
        if self.app.trust_proxy and self.client_address[0] in self.app.proxy_addresses:
            forwarded = self.headers.get("X-Forwarded-For", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def is_https(self):
        return self.app.trust_proxy and self.headers.get("X-Forwarded-Proto", "") == "https"

    def accepts_gzip(self):
        return "gzip" in (self.headers.get("Accept-Encoding") or "")

    def send(self, status, body=b"", content_type="application/json; charset=utf-8", extra=None):
        # Larger JSON answers go compressed when the browser accepts it: a few hundred microseconds of work
        # for a quarter of the bytes. Static files arrive here already compressed (see static()).
        if (len(body) > 2048 and content_type.startswith("application/json") and self.accepts_gzip()
                and "Content-Encoding" not in (extra or {})):
            body = gzip.compress(body, 5)
            extra = dict(extra or {}, **{"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
        self.send_response(status)
        for k, v in SECURITY_HEADERS.items():
            if k not in (extra or {}):  # a response may set a stricter or different policy of its own
                self.send_header(k, v)
        if self.is_https():
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def json(self, status, payload, extra=None):
        headers = {"Cache-Control": "no-store"}
        headers.update(extra or {})
        self.send(status, json.dumps(payload).encode(), extra=headers)

    def stream_file(self, path, name):
        size = os.path.getsize(path)
        self.send_response(200)
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f'attachment; filename="{name}"')
        self.end_headers()
        with open(path, "rb") as f:
            while chunk := f.read(1 << 20):
                self.wfile.write(chunk)

    def error(self, status, message, **extra):
        self.json(status, {"error": message, **extra})

    def body(self, limit=MAX_BODY):
        length = self.content_length()
        if length > limit:
            raise ValueError("That request is too large")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw or b"{}")
        if not isinstance(data, dict):
            raise ValueError("Send a JSON object")
        return data

    def content_length(self):
        """The declared body size: a whole number from 0 up, or the request is refused (never read to the end)."""
        raw = (self.headers.get("Content-Length") or "0").strip()
        if not raw.isdigit():
            self.close_connection = True
            raise ValueError("Send a Content-Length of 0 or more")
        return int(raw)

    def token(self):
        jar = cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie", ""))
        except cookies.CookieError:
            return None
        return jar[COOKIE].value if COOKIE in jar else None

    def signed_in(self):
        return self.app.sessions.valid(self.token(), self.app.session_version)

    def session_cookie(self, token, max_age):
        """max_age None makes a cookie the browser forgets when it closes (Remember me not ticked)."""
        secure = self.is_https() or self.app.config.data.get("secure_cookies")
        parts = [f"{COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Strict"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        if secure:
            parts.append("Secure")
        return "; ".join(parts)

    def same_origin(self):
        """Changes must come from this dashboard's own pages: a custom header (which forces a CORS preflight that we never
        approve) plus a matching Origin when the browser sends one."""
        if self.headers.get("X-Starboard") != "1":
            return False
        origin = self.headers.get("Origin")
        if origin:
            host = self.headers.get("X-Forwarded-Host") if self.app.trust_proxy and self.headers.get("X-Forwarded-Host") else self.headers.get("Host", "")
            return urllib.parse.urlparse(origin).netloc == host
        return True

    # Routing -----------------------------------------------------------

    def do_HEAD(self):
        self.do_GET()

    def local_only_refused(self):
        """With network access off, only this computer may connect, even if the address was overridden."""
        if self.app.config.data.get("network_access", True) or is_loopback(self.client_address[0]):
            return False
        self.send(403, b"This dashboard only accepts connections from the computer it runs on.", "text/plain; charset=utf-8")
        return True

    def host_refused(self):
        """Answers only to names it knows (an IP address, localhost, this computer's name or STARBOARD_ALLOWED_HOSTS),
        so a web page cannot reach Starboard through a domain name it controls (DNS rebinding)."""
        host = (self.headers.get("Host") or "").strip().lower()
        if host.startswith("["):
            name = host[1:host.find("]")] if "]" in host else host
        else:
            name = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
        if self.app.host_allowed(name):
            return False
        self.send(421, f"Starboard does not answer to the name {name[:80]}. Use its address, or add the name to "
                       "STARBOARD_ALLOWED_HOSTS on the server.".encode(), "text/plain; charset=utf-8")
        return True

    def do_GET(self):
        if self.local_only_refused() or self.host_refused():
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/healthz":
            return self.send(200, b"ok", "text/plain; charset=utf-8")
        if path.startswith("/api/"):
            return self.api("GET", path)
        if path.startswith("/iptv/"):
            return self.iptv(path)
        return self.static(path)

    def iptv(self, path):
        """For Jellyfin, with no sign-in, only while Live TV is on: channel logos and Pluto stream links."""
        if not self.app.config.data["extras"].get("livetv"):
            return self.send(404, b"", "text/plain; charset=utf-8")
        m = re.match(r"^/iptv/logos/([A-Za-z0-9._-]{1,80}\.png)$", path)
        if m:
            found = livetv.logo_file(m.group(1))
            if not found:
                return self.send(404, b"", "text/plain; charset=utf-8")
            with open(found, "rb") as f:
                return self.send(200, f.read(), "image/png", {"Cache-Control": "max-age=86400"})
        m = re.match(r"^/iptv/pluto/([A-Za-z0-9]{8,40})\.m3u8$", path)
        if m:
            try:
                target = livetv.pluto_url(m.group(1))
            except Exception:
                return self.send(502, b"Pluto did not start a session", "text/plain; charset=utf-8")
            return self.send(302, b"", "text/plain; charset=utf-8", {"Location": target, "Cache-Control": "no-store"})
        return self.send(404, b"", "text/plain; charset=utf-8")

    def do_POST(self):
        self.mutating("POST")

    def do_PUT(self):
        self.mutating("PUT")

    def do_DELETE(self):
        self.mutating("DELETE")

    def mutating(self, method):
        if self.local_only_refused() or self.host_refused():
            return
        path = urllib.parse.urlparse(self.path).path
        if not path.startswith("/api/"):
            return self.error(405, "Not allowed")
        if not self.same_origin():
            return self.error(403, "Blocked: this request did not come from the dashboard")
        self.api(method, path)

    def static(self, path):
        if "/." in path or "\\" in path:  # no dot-dot or hidden files: the sign-in check reads the path as given
            return self.send(404, b"Not found", "text/plain; charset=utf-8")
        if path == "/":
            path = "/index.html"
        if not path.endswith(".html") and "." not in posixpath.basename(path):
            path += ".html"
        public = path in PUBLIC_PAGES or path in PUBLIC_FILES or path.startswith(PUBLIC_PREFIXES)
        if not public:
            if self.app.needs_setup:
                return self.send(303, extra={"Location": "/setup.html"})
            if not self.signed_in():
                return self.send(303, extra={"Location": "/login.html?next=" + urllib.parse.quote(path)})
        full = os.path.realpath(os.path.join(WEB, path.lstrip("/")))
        if not full.startswith(WEB + os.sep) or not os.path.isfile(full):
            return self.send(404, b"Not found", "text/plain; charset=utf-8")
        data, packed, tag, kind = static_file(full)
        # no-cache with an ETag: the browser asks each time and gets "304 Not Modified" (no body) until the
        # file changes, so an update shows at once but pages cost almost nothing to open again.
        extra = {"Cache-Control": "no-cache", "ETag": tag, "Vary": "Accept-Encoding"}
        if self.headers.get("If-None-Match") == tag:
            return self.send(304, b"", kind, extra)
        if packed and self.accepts_gzip():
            data = packed
            extra["Content-Encoding"] = "gzip"
        if path in ("/favicon.svg", "/icon-app.svg"):
            # The logo switches colours for dark mode with its own small style block, and runs nothing.
            extra["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        self.send(200, data, kind, extra)

    def stack_overview(self):
        """What Install apps needs: the groups and apps (those already running marked), folders already used for
        media, the servers a migration could come from, and sensible defaults."""
        app = self.app
        found = discovery.search(app.config.data["services"])["items"]
        names = {re.sub(r"[^a-z0-9]", "", i["key"]) for i in found}
        if containers.available():
            try:
                names |= {re.sub(r"[^a-z0-9]", "", c["Names"][0].lower()) for c in containers.docker("GET", "/containers/json?all=1")}
            except containers.DockerError:
                pass
        installed = {k for k in stack.APPS if k in names or (k == "bookshelf" and "readarr" in names)}
        media = stack.existing_media()
        host = stack.host_folder(app.data_dir)
        base = os.path.dirname(os.path.dirname(os.path.dirname(host))) if host else "/srv"
        data_dir = os.path.commonpath([m["path"] for m in media]) if media else f"{base}/media"
        if data_dir in ("/", ""):
            data_dir = f"{base}/media"
        return {**stack.catalogue(installed), "docker": containers.available(), "can_start": bool(host and containers.available()),
                "existing_media": media, "drives": sysinfo.pool_candidates(),
                "servers": [{"key": i["key"], "name": i["name"]} for i in found
                            if i["key"] in ("plex", "emby", "jellyfin", "audiobookshelf", "sonarr", "radarr", "lidarr")],
                "written": os.path.exists(os.path.join(stack.folder(app.data_dir), "compose.yaml")),
                "defaults": {"config_dir": f"{base}/media-stack/config", "data_dir": data_dir, "puid": os.getuid() or 1000,
                             "pgid": os.getgid() or 1000, "tz": os.environ.get("TZ") or "Etc/UTC"}}

    def upgrade_summary(self):
        d = self.app.config.data
        p = releases.pending(d.get("last_version", ""), self.app.version, not self.app.needs_setup)
        return {"from": p["from"], "to": p["to"], "wizard": p["wizard"], "count": len(p["review"])}

    def api(self, method, path):
        app = self.app
        fresh = "fresh=1" in urllib.parse.urlparse(self.path).query  # "Check again": skip the shared answers
        if method != "GET":
            services.forget()  # a change (an app added, a setting saved) makes the shared answers out of date
        try:
            # Open routes
            if path == "/api/session" and method == "GET":
                signed_in = self.signed_in()
                return self.json(200, {
                    "signed_in": signed_in, "needs_setup": app.needs_setup,
                    "site_name": app.config.data["site_name"], "design": app.config.data["design"],
                    # Not told to people who have not signed in.
                    "version": app.version if signed_in else None,
                    "repo": app.repo if signed_in and re.match(r"^[\w.-]+/[\w.-]+$", app.repo or "") else None,
                    # Only what is already known (no call to GitHub here): the footer's "Upgrade available".
                    "latest": app._latest["tag"] if signed_in else None,
                    "upgrade": self.upgrade_summary() if signed_in else None,
                    "ux_notes": bool(signed_in and app.config.data.get("ux_notes")),
                })
            if path == "/api/jellyfin/detect" and method == "GET":
                if not (app.needs_setup or self.signed_in()):
                    return self.error(401, "Sign in first")
                found = migrate.detect_jellyfin()
                have = any(sv["type"] == "jellyfin" for sv in app.config.data["services"])
                return self.json(200, {"found": found, "in_apps": have})
            if path == "/api/setup" and method == "POST":
                return self.first_password()
            if path == "/api/login" and method == "POST":
                return self.login()
            if path == "/api/logout" and method == "POST":
                app.sessions.end(self.token())
                return self.json(200, {"ok": True}, {"Set-Cookie": self.session_cookie("", 0)})

            if not self.signed_in():
                return self.error(401, "Sign in first")

            cfg = app.config
            if path == "/api/config" and method == "GET":
                return self.json(200, cfg.public())
            if path == "/api/config/general" and method == "PUT":
                before = cfg.data.get("network_access", True)
                incoming = self.body()
                cfg.update_general(incoming)
                logs.event("info", "settings", f"Changed: {', '.join(sorted(incoming)) or 'nothing'}")
                if "watch" in incoming:
                    app.watch.wake.set()  # turning watching on, or changing how often, takes effect at once
                # Background work follows the settings at once: threads start when turned on and end when off.
                if os.environ.get("STARBOARD_JOBS", "1") != "0":
                    app.jobs.ensure()
                if os.environ.get("STARBOARD_WATCH", "1") != "0":
                    app.watch.ensure()
                if os.environ.get("STARBOARD_SCHEDULE", "1") != "0":
                    app.schedule.ensure()
                if app.history:
                    app.history.ensure()
                app.usage.ensure()
                if cfg.data.get("network_access", True) != before and app.on_network_change:
                    # Answer first, then move the listener.
                    threading.Timer(0.5, app.on_network_change).start()
                return self.json(200, cfg.public())
            if path.startswith("/api/ux-notes"):
                if not cfg.data.get("ux_notes"):
                    return self.error(404, "Turn on Note issues in Settings, General first")
                if path == "/api/ux-notes" and method == "GET":
                    return self.json(200, {"notes": app.uxnotes.list()})
                if path == "/api/ux-notes" and method == "POST":
                    return self.json(200, app.uxnotes.add(self.body()))
                if path == "/api/ux-notes/update" and method == "POST":
                    b = self.body()
                    return self.json(200, app.uxnotes.update(str(b.get("id", "")), b.get("status")))
                if path == "/api/ux-notes/remove" and method == "POST":
                    app.uxnotes.remove(str(self.body().get("id", "")))
                    return self.json(200, {"ok": True})
            if path == "/api/network" and method == "GET":
                return self.json(200, app.network_info(self.client_address[0]))
            if path == "/api/services" and method == "POST":
                incoming = self.body()
                service_id = cfg.upsert_service(incoming)
                logs.event("info", "apps", f"{'Changed' if incoming.get('id') else 'Added'} {str(incoming.get('name', 'an app'))[:60]}")
                return self.json(200, {"id": service_id, "config": cfg.public()})
            if path == "/api/services/order" and method == "POST":
                cfg.reorder_services(self.body().get("ids", []))
                return self.json(200, cfg.public())
            if path == "/api/services/test" and method == "POST":
                incoming = self.body()
                stored = cfg.service(incoming.get("id", "")) if incoming.get("id") else None
                if stored and not incoming.get("api_key"):
                    if not same_server(stored.get("url", ""), str(incoming.get("url", ""))):
                        return self.error(400, "The address points to a different server, so enter the API key to test it")
                    incoming["api_key"] = stored.get("api_key", "")
                candidate = validate_service(incoming)
                candidate["id"] = candidate.get("id") or "test"
                return self.json(200, services.check(candidate))
            m = re.match(r"^/api/posters/([a-z0-9-]+)/([a-z]+)/(\d{1,10})$", path)
            if m and method == "GET":
                service = cfg.service(m.group(1))
                found = posters.get(service, m.group(2), m.group(3), os.path.join(cfg.data_dir, "posters")) if service and cfg.data["show_posters"] else None
                if not found:
                    return self.send(404, b"", "text/plain; charset=utf-8", {"Cache-Control": "private, max-age=3600"})
                return self.send(200, found[0], found[1], {"Cache-Control": "private, max-age=604800"})
            m = re.match(r"^/api/icons/([a-z0-9-]+)$", path)
            if m and method == "GET":
                return self.icon(m.group(1))
            m = re.match(r"^/api/services/([a-z0-9-]+)(/options)?$", path)
            if m:
                service = cfg.service(m.group(1))
                if not service:
                    return self.error(404, "That app is not in your list")
                if m.group(2) and method == "GET":
                    return self.json(200, services.options(service))
                if not m.group(2) and method == "DELETE":
                    cfg.remove_service(service["id"])
                    logs.event("info", "apps", f"Removed {service['name']}")
                    return self.json(200, cfg.public())
            if path == "/api/status" and method == "GET":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                one = q.get("id", [""])[0]
                if q.get("recent"):  # the last checks of one app, without checking it again
                    return self.json(200, {"recent": services.recent_checks(q["recent"][0])})
                if one:
                    if not cfg.service(one):
                        return self.error(404, "No app with that ID")
                    return self.json(200, {"items": services.status_one(cfg.data["services"], one), "recent": services.recent_checks(one)})
                return self.json(200, {"items": services.cached("status", 15, lambda: services.status_all(cfg.data["services"]), fresh)})
            if path == "/api/search" and method == "GET":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("q", [""])[0]
                return self.json(200, services.search(cfg.data["services"], query))
            if path == "/api/add" and method == "POST":
                data = self.body()
                service = cfg.service(str(data.get("service", "")))
                if not service:
                    return self.error(404, "That app is not in your list")
                key = str(data.get("key", ""))
                if not re.match(r"^(tvdb|tmdb|lidarr|readarr):[\w-]{1,64}$", key):
                    return self.error(400, "That item cannot be added")
                return self.json(200, services.add(service, key, data.get("options") or {}))
            if path == "/api/outside" and method == "GET":
                return self.json(200, {"items": services.outside_all(cfg.data["services"])})
            if path == "/api/app-updates" and method == "GET":
                return self.json(200, services.cached("app-updates", 600, lambda: services.app_updates(cfg.data["services"]), fresh))
            if path == "/api/queue" and method == "GET":
                return self.json(200, services.cached("queue", 10, lambda: services.queue(cfg.data["services"]), fresh))
            if path == "/api/queue/action" and method == "POST":
                data = self.body()
                service = cfg.service(str(data.get("service", "")))
                if not service or service["type"] not in ("sonarr", "radarr", "lidarr", "readarr") or not str(data.get("id", "")).isdigit():
                    return self.error(400, "Choose a download in Sonarr, Radarr, Lidarr or Readarr")
                services.queue_action(service, int(data["id"]), str(data.get("action", "")))
                logs.event("info", "downloads", f"{data.get('action')} for a download in {service['name']}")
                return self.json(200, {"ok": True})
            if path.startswith("/api/containers"):
                if not containers.available():
                    return self.json(200, {"available": False, "items": [], "containers": []})
                ordered = cfg.data["services"]
                if path == "/api/containers" and method == "GET":
                    return self.json(200, containers.apps(ordered))
                if path == "/api/containers/check" and method == "POST":
                    return self.json(200, containers.check(ordered))
                if path == "/api/containers/update" and method == "POST":
                    ids = self.body().get("ids")
                    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                        return self.error(400, "Choose the apps to update")
                    return self.json(200, containers.update(ordered, ids))
            if path == "/api/extras" and method == "GET":
                return self.json(200, dict(app.jobs.status(), importing=app.importing, import_result=app.import_result,
                                           history=migrate.status(cfg.data_dir, cfg.data["services"])))
            m = re.match(r"^/api/extras/(livetv|import|defaults|listening)/run$", path)
            if m and method == "POST":
                app.jobs.run_soon(m.group(1), force=True)
                return self.json(200, {"ok": True})
            if path == "/api/import" and method == "POST":
                return self.start_import(self.body())
            if path == "/api/import/upload" and method == "POST":
                return self.upload_import()
            if path == "/api/import/mapping" and method == "PUT":
                migrate.set_mapping(cfg.data_dir, self.body().get("mapping") or {})
                return self.json(200, migrate.status(cfg.data_dir, cfg.data["services"]))
            if path == "/api/listening" and method == "GET":
                job = next(j for j in app.jobs.status()["jobs"] if j["key"] == "listening")
                return self.json(200, dict(listening.status(cfg.data_dir, cfg.data["services"]), job=job,
                                           reading=bool(app.listening_busy), read_result=app.listening_read))
            if path == "/api/listening/read" and method == "POST":
                return self.start_listening(self.body())
            if path == "/api/listening/mapping" and method == "PUT":
                listening.set_mapping(cfg.data_dir, self.body().get("mapping") or {})
                return self.json(200, {"ok": True})
            if path == "/api/copy-settings" and method == "GET":
                return self.json(200, {"parts": copyset.PARTS, "apps": [
                    {"id": sv["id"], "name": sv["name"], "type": sv["type"], "has_api_key": bool(sv.get("api_key"))}
                    for sv in cfg.data["services"] if sv["type"] in copyset.KINDS and sv.get("enabled", True)]})
            if path in ("/api/copy-settings/preview", "/api/copy-settings/apply") and method == "POST":
                body = self.body()
                source, target = cfg.service(str(body.get("from", ""))), cfg.service(str(body.get("to", "")))
                parts = body.get("parts") if isinstance(body.get("parts"), list) else []
                if not source or not target:
                    return self.error(400, "Choose the app to copy from and the app to copy to")
                if not parts:
                    return self.error(400, "Choose at least one part to copy")
                try:
                    if path.endswith("preview"):
                        return self.json(200, copyset.preview(source, target, parts))
                    secrets_given = body.get("secrets") if isinstance(body.get("secrets"), dict) else {}
                    result = copyset.apply(source, target, parts, {str(k): v for k, v in secrets_given.items() if isinstance(v, dict)})
                    logs.event("info", "copy", f"Copied {', '.join(parts)} from {source['name']} to {target['name']}" +
                               (f"; {len(result['problems'])} problems" if result["problems"] else ""))
                    return self.json(200, result)
                except (ValueError, services.ServiceError) as e:
                    return self.error(400, str(e))
            if path == "/api/discover" and method == "GET":
                return self.json(200, discovery.search(cfg.data["services"]))
            if path == "/api/discover/add" and method == "POST":
                return self.json(200, self.add_found(self.body().get("items")))
            if path == "/api/stack" and method == "GET":
                return self.json(200, self.stack_overview())
            if path == "/api/stack/preview" and method == "POST":
                built = stack.build(self.body())
                return self.json(200, {**{k: built[k] for k in ("compose", "env_shown", "folders", "moved", "later")}, "hooks": sorted(built["hooks"])})
            if path == "/api/stack/write" and method == "POST":
                built = stack.build(self.body())
                stack.write(app.data_dir, built)
                host = stack.host_folder(app.data_dir)
                return self.json(200, {"host_folder": host, "can_start": bool(host and containers.available()),
                                       "command": f"cd {host or '<Starboard folder>/data/stack'} && docker compose -p {stack.PROJECT} up -d",
                                       "moved": built["moved"], "later": built["later"]})
            if path == "/api/stack/start" and method == "POST":
                self.check_password(self.body())  # starting containers changes the computer: the password again
                host = stack.host_folder(app.data_dir)
                env_file = os.path.join(stack.folder(app.data_dir), ".env")
                if not host or not containers.available() or not os.path.exists(env_file):
                    raise ValueError("Starboard cannot start apps here. Run the command instead")
                with open(env_file) as f:
                    logs.event("info", "install apps", "Starting the apps in data/stack")
                    return self.json(200, stack.start(host, f.read()))
            if path == "/api/stack/job" and method == "GET":
                return self.json(200, stack.job())
            # Starboard's own log (System, Logs)
            if path == "/api/logs" and method == "GET":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                level = q.get("level", ["all"])[0]
                before = float(q.get("before", ["0"])[0] or 0) or None
                return self.json(200, {"entries": app.log.read(level if level in ("all", "problems", "detail") else "all",
                                                               q.get("q", [""])[0][:100], before),
                                       "summary": app.log.summary(), "detailed": app.log.detailed(), "settings": cfg.data["logs"],
                                       "repo": app.repo if re.match(r"^[\w.-]+/[\w.-]+$", app.repo or "") else None})
            if path == "/api/logs/download" and method == "GET":
                body = app.log.text(app.log.read("all", limit=200000)).encode()
                return self.send(200, body, "text/plain; charset=utf-8",
                                 {"Content-Disposition": f'attachment; filename="starboard-log-{time.strftime("%Y-%m-%d")}.txt"'})
            if path == "/api/logs/report" and method == "GET":
                return self.send(200, logs.report(app, app.log).encode(), "text/plain; charset=utf-8")
            if path == "/api/logs/clear" and method == "POST":
                removed = app.log.clear()
                logs.event("info", "logs", f"Logs deleted ({removed} {'day' if removed == 1 else 'days'})")
                return self.json(200, {"removed": removed})
            if path == "/api/releases" and method == "GET":
                d = cfg.data
                return self.json(200, {"current": app.version, "latest": app.latest_release(), "repo": app.repo,
                                       "pending": releases.pending(d["last_version"], app.version, not app.needs_setup),
                                       "all": list(reversed(releases.RELEASES))})
            if path == "/api/releases/seen" and method == "POST":
                cfg.update_general({"last_version": app.version})
                return self.json(200, {"ok": True})
            if path == "/api/self" and method == "GET":
                return self.json(200, sysinfo.self_usage())
            if path == "/api/uptime" and method == "GET":
                return self.json(200, {"enabled": cfg.data["watch"]["enabled"], "items": app.watch.uptime(cfg.data["services"])})
            if path == "/api/alerts/test" and method == "POST":
                watch.send(cfg.data["watch"]["channel"], f"Test from {cfg.data['site_name']}",
                           "Alerts from Starboard reach you here.", "info")
                return self.json(200, {"ok": True})
            if path == "/api/schedule" and method == "GET":
                return self.json(200, app.schedule.status())
            if path == "/api/schedule" and method == "POST":
                return self.json(200, app.schedule.act(str(self.body().get("action", ""))))
            if path == "/api/calendar" and method == "GET":
                days = cfg.data["upcoming_days"]
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    month = dt.date.fromisoformat(q.get("month", [""])[0] + "-01") if q.get("month") else None
                except ValueError:
                    return self.error(400, "Send the month as YYYY-MM")
                if month:  # a month view: its own saved answer, at most 3 kept (this month and either side)
                    start = month - dt.timedelta(days=7)
                    end = (month + dt.timedelta(days=32)).replace(day=1) + dt.timedelta(days=7)
                    key = f"calendar-month-{month:%Y-%m}"
                    with services._cache_lock:
                        months = sorted(k for k in services._cache if k.startswith("calendar-month-") and k != key)
                    if len(months) >= 3:
                        services.forget(*months[:len(months) - 2])
                    result = json.loads(json.dumps(services.cached(key, 600, lambda: services.calendar(cfg.data["services"], start=start, end=end), fresh)))
                else:
                    result = json.loads(json.dumps(services.cached(f"calendar-{days}", 600, lambda: services.calendar(cfg.data["services"], days), fresh)))
                if not cfg.data["show_posters"]:
                    for item in result["items"]:
                        item["image"] = ""
                return self.json(200, result)
            if path == "/api/access" and method == "GET":
                return self.json(200, {"items": access.summary(app)})
            if path == "/api/transfer" and method == "GET":
                return self.json(200, services.cached("transfer", 5, lambda: services.transfer(cfg.data["services"]), fresh))
            if path == "/api/numbers" and method == "GET":
                return self.json(200, {"items": services.cached("numbers", 60, lambda: services.numbers(cfg.data["services"]), fresh)})
            if path == "/api/requests" and method == "GET":
                pending = "pending=1" in urllib.parse.urlparse(self.path).query
                return self.json(200, services.cached(f"requests-{pending}", 20, lambda: services.requests(cfg.data["services"], pending), fresh))
            m = re.match(r"^/api/requests/(\d{1,10})/(approve|decline)$", path)
            if m and method == "POST":
                services.request_action(cfg.data["services"], m.group(1), m.group(2))
                services.forget()
                return self.json(200, services.requests(cfg.data["services"]))
            if path == "/api/jobs" and method == "GET":
                return self.json(200, backup.jobs_status())
            m = re.match(r"^/api/jobs/([a-z][a-z0-9-]{0,30})$", path)
            if m and method == "POST":
                backup.request_job(m.group(1))
                return self.json(200, backup.jobs_status())
            if path == "/api/recent" and method == "GET":
                return self.json(200, services.cached("recent", 300, lambda: services.recent(cfg.data["services"]), fresh))
            if path == "/api/jellyfin" and method == "GET":
                return self.json(200, services.cached("jellyfin", 20, lambda: services.jellyfin(cfg.data["services"]), fresh))
            if path == "/api/health" and method == "GET":
                return self.json(200, services.cached("health", 300, lambda: services.health(cfg.data["services"]), fresh))
            if path == "/api/history" and method == "GET":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                hours = {"1": 1, "6": 6, "24": 24}.get(q.get("hours", ["1"])[0], 1)
                interval = app.history.INTERVAL if app.history else int(cfg.data["performance"].get("history_every", 300))
                return self.json(200, {"hours": hours, "interval": interval,
                                       "points": app.history.get(hours) if app.history else []})
            if path == "/api/monitor" and method == "GET":
                return self.json(200, sysinfo.monitor())
            if path == "/api/interfaces" and method == "GET":
                return self.json(200, {"items": sysinfo.interfaces()})
            if path == "/api/disk-health/report" and method == "GET":
                name = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("file", [""])[0]
                found = sysinfo.smart_report(name)
                if not found:
                    return self.error(404, "That report is not there any more")
                with open(found, "rb") as f:
                    body = f.read(5 * 1024 * 1024)
                return self.send(200, body, "application/json", {"Content-Disposition": f'attachment; filename="smart-{name}"'})
            if path == "/api/disk-health" and method == "GET":
                result = sysinfo.disk_health()
                app.disk_temps.record(result["disks"])
                result["history"] = app.disk_temps.get()
                return self.json(200, result)
            if path == "/api/disk-health/read" and method == "POST":
                sysinfo.request_disk_read()
                return self.json(200, {"ok": True})
            if path == "/api/usage" and method == "GET":
                return self.json(200, app.usage.get())
            if path == "/api/usage" and method == "POST":
                if not app.disks:
                    return self.error(400, "Choose folders for System, Storage first (./install.sh --disk)")
                app.usage.start(app.disks)
                logs.event("info", "storage", "Started working out what uses the space")
                return self.json(200, app.usage.get())
            if path == "/api/system" and method == "GET":
                snap = sysinfo.snapshot(app.disks)
                app.record_space(snap)
                snap["pools"] = sysinfo.pools([dict(d, path=p) for (_, p), d in zip(app.disks, snap["disks"])])
                return self.json(200, snap)
            if path == "/api/space-history" and method == "GET":
                return self.json(200, {"on": cfg.data["performance"].get("space_log", True), "days": app.space.get()})
            if path == "/api/version" and method == "GET":
                return self.json(200, {"current": app.version, "latest": app.latest_release(), "repo": app.repo,
                                       "since": (cfg.data.get("version_since") or {}).get("since")})
            if path == "/api/backup/settings" and method == "POST":
                self.check_password(self.body())
                return self.json(200, backup.export(cfg, app.version))
            if path == "/api/backup/restore" and method == "POST":
                data = self.body(limit=2 * 1024 * 1024)
                self.check_password(data)
                count = backup.restore(cfg, data.get("backup"))
                logs.event("info", "backup", f"Settings restored from a file ({count} apps)")
                return self.json(200, {"apps": count, "config": cfg.public()})
            if path == "/api/backup/saved" and method == "GET":
                one = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("name", [""])[0]
                if one:
                    return self.json(200, backup.saved_detail(cfg, one))
                return self.json(200, {"items": backup.saved_copies(cfg)})
            if path == "/api/backup/saved/download" and method == "POST":
                data = self.body()
                self.check_password(data)
                logs.event("info", "backup", "A saved copy of the settings was downloaded")
                return self.json(200, backup.export_saved(cfg, str(data.get("name", "")), app.version))
            if path == "/api/backup/restore-saved" and method == "POST":
                data = self.body()
                self.check_password(data)
                count = backup.restore_saved(cfg, str(data.get("name", "")))
                logs.event("info", "backup", f"Settings restored from a saved copy ({count} apps)")
                return self.json(200, {"apps": count, "config": cfg.public()})
            if path == "/api/backup/server/link" and method == "POST":
                # Backups can be gigabytes, so the password buys a one-time link for a minute, and the browser
                # downloads it as a file (streamed in 1 MB pieces, never held in memory).
                data = self.body()
                self.check_password(data)
                if not backup.server_file(str(data.get("name", ""))):
                    return self.error(404, "That backup is not there any more")
                token = secrets.token_urlsafe(24)
                with app.import_lock:
                    app.download_links = {k: v for k, v in app.download_links.items() if v[1] > time.time()}
                    app.download_links[token] = (str(data["name"]), time.time() + 60)
                return self.json(200, {"url": f"/api/backup/server/file?link={token}"})
            if path == "/api/backup/server/file" and method == "GET":
                token = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("link", [""])[0]
                with app.import_lock:
                    name, until = app.download_links.pop(token, ("", 0))
                found = backup.server_file(name) if until > time.time() else None
                if not found:
                    return self.error(404, "That link has run out. Choose Download again")
                logs.event("info", "backup", "A server backup was downloaded")
                return self.stream_file(found, name)
            if path == "/api/backup/server" and method == "GET":
                return self.json(200, backup.server_status())
            if path == "/api/backup/server" and method == "POST":
                backup.request_server_backup(bool(self.body().get("with_prompt")))
                return self.json(200, backup.server_status())
            if path == "/api/password" and method == "POST":
                return self.change_password()
            if path == "/api/sessions/end-all" and method == "POST":
                cfg.data["auth"]["session_version"] = app.session_version + 1
                cfg.save()
                app.sessions.end_all()
                return self.json(200, {"ok": True}, {"Set-Cookie": self.session_cookie("", 0)})
            return self.error(404, "Not found")
        except PasswordProblem as e:
            return self.error(e.status, e.message, reason="password")
        except (ConfigError, ValueError) as e:
            return self.error(400, str(e))
        except OSError:
            return self.error(404, "That file is not there any more")
        except services.ServiceError as e:
            return self.error(502, str(e))
        except containers.DockerError as e:
            return self.error(502, str(e))
        except (TypeError, KeyError, AttributeError) as e:  # a request of the wrong shape, or a damaged file
            logs.error("request", f"{method} {path}: {type(e).__name__}: {e}", e)
            return self.error(400, "That request could not be used. Check what was sent")
        except Exception as e:  # anything Starboard did not expect: logged in full, so it can be reported
            logs.error("request", f"{method} {path}: {type(e).__name__}: {e}", e)
            return self.error(500, "Something went wrong. The details are in System, Logs")

    def icon(self, service_id):
        service = self.app.config.service(service_id)
        found = icons.get(service, os.path.join(self.app.config.data_dir, "icons"),
                          fetch=self.app.config.data["fetch_icons"]) if service else None
        if not found:
            return self.send(404, b"", "text/plain; charset=utf-8", {"Cache-Control": "max-age=3600"})
        data, ctype = found
        # An SVG opened on its own must not run anything: no scripts, no outside loads.
        self.send(200, data, ctype, {
            "Cache-Control": "private, max-age=86400",
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox",
        })

    # Accounts ------------------------------------------------------------

    def new_session(self, remember):
        app = self.app
        days = app.config.data["session_days"] if remember else auth.FORGET_AFTER_DAYS
        token = app.sessions.create(days, app.session_version, remember)
        return {"Set-Cookie": self.session_cookie(token, days * 86400 if remember else None)}

    def add_found(self, items):
        """Adds apps that Search for new apps found. Each one's API key is read from its own settings file
        through Docker when asked and possible; otherwise it is added without one, to fill in later."""
        if not isinstance(items, list) or not items:
            raise ValueError("Choose the apps to add")
        cfg = self.app.config
        added, missing_keys = [], []
        for it in items[:60]:
            if not isinstance(it, dict) or it.get("key") not in discovery.CATALOGUE:
                continue
            name, kind, _, _, needs_key, background = discovery.CATALOGUE[it["key"]]
            url = str(it.get("url", ""))
            if not re.match(r"^http://127\.0\.0\.1:\d{2,5}$", url):
                continue  # only what discovery itself found on this computer
            key = discovery.read_key(it["key"], str(it.get("container", ""))) if it.get("read_key") else None
            service = {"name": name, "type": kind, "url": url, "background": background, "icon": it["key"],
                       "container": str(it.get("container", "")) if it.get("container") else ""}
            if key:
                service["api_key"] = key
            cfg.upsert_service(service)
            added.append(name)
            if needs_key and not key:
                missing_keys.append(name)
        services.forget()
        return {"added": added, "missing_keys": missing_keys, "config": cfg.public()}

    # Watch history import --------------------------------------------------------------

    def start_import(self, data):
        """Reads history from a Plex server, an Emby or Jellyfin server, or a file already in data/imports."""
        app = self.app
        kind = str(data.get("kind", ""))
        url = str(data.get("url", "")).strip().rstrip("/")
        secret = str(data.get("token", "")).strip()
        if kind in ("plex", "emby", "jellyfin") and not re.match(r"^https?://[^\s/]+(/\S*)?$", url):
            return self.error(400, "Enter the server's address, starting with http:// or https://")
        if kind in ("plex", "emby", "jellyfin") and not secret:
            return self.error(400, "Enter the token or API key")
        if kind not in ("plex", "emby", "jellyfin"):
            return self.error(400, "Choose where to import from")
        with app.import_lock:
            if app.importing:
                return self.error(409, "An import is already running")
            app.importing = {"kind": kind, "started": time.time()}

        def work():
            try:
                if kind == "plex":
                    accounts = migrate.read_plex_server(url, secret)
                else:
                    accounts = migrate.read_media_server(url, secret, "Emby" if kind == "emby" else "Jellyfin")
                migrate.save_history(app.config.data_dir, {"plex": "Plex server", "emby": "Emby", "jellyfin": "Jellyfin"}[kind], accounts)
                app.importing = None
                app.import_result = {"ok": True, "message": f"Read {sum(len(v) for v in accounts.values())} films and episodes from {len(accounts)} accounts"}
            except Exception as e:  # shown on the page
                app.importing = None
                app.import_result = {"ok": False, "message": str(e)[:300]}

        threading.Thread(target=work, name="import", daemon=True).start()
        return self.json(200, {"started": True})

    def start_listening(self, data):
        """Reads listening progress from a Plex, Jellyfin, Emby or Audiobookshelf server, in the background."""
        app = self.app
        kind = str(data.get("kind", ""))
        url = str(data.get("url", "")).strip().rstrip("/")
        secret = str(data.get("token", "")).strip()
        names = {"plex": "Plex", "jellyfin": "Jellyfin", "emby": "Emby", "audiobookshelf": "Audiobookshelf"}
        if kind not in names:
            return self.error(400, "Choose where to read from")
        if not re.match(r"^https?://[^\s/]+(/\S*)?$", url):
            return self.error(400, "Enter the server's address, starting with http:// or https://")
        if not secret:
            return self.error(400, "Enter the token or API key")
        with app.import_lock:
            if app.listening_busy:
                return self.error(409, "Starboard is already reading listening progress")
            app.listening_busy = {"kind": kind, "started": time.time()}

        def work():
            try:
                if kind == "plex":
                    accounts = listening.read_plex(url, secret)
                elif kind == "audiobookshelf":
                    accounts = listening.read_abs(url, secret)
                else:
                    accounts = listening.read_media_server(url, secret, names[kind])
                listening.save_progress(app.config.data_dir, names[kind], accounts)
                books = sum(len(v) for v in accounts.values())
                app.listening_read = {"ok": True, "message": f"Read {books} {'book' if books == 1 else 'books'} from {len(accounts)} {'account' if len(accounts) == 1 else 'accounts'}"}
                logs.event("info", "listening", f"Read listening progress from {names[kind]}: {books} books")
            except Exception as e:  # shown on the page
                app.listening_read = {"ok": False, "message": str(e)[:300]}
                logs.error("listening", f"Reading listening progress failed: {e}", e)
            finally:
                app.listening_busy = None

        threading.Thread(target=work, name="listening", daemon=True).start()
        return self.json(200, {"started": True})

    def upload_import(self):
        """A Plex database file or a history file, streamed to data/imports. Up to 8 GB."""
        app = self.app
        kind = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("kind", [""])[0]
        if kind not in ("plexdb", "json"):
            return self.error(400, "Choose a Plex database file or a history file")
        length = self.content_length()
        if not 0 < length <= 8 * 1024 ** 3:
            return self.error(400, "Choose a file up to 8 GB")
        if kind == "json" and length > migrate.MAX_HISTORY_FILE:  # refused before the upload, not after it
            self.close_connection = True
            return self.error(400, "That history file is larger than 512 MB")
        with app.import_lock:  # claim the import before reading the upload, so two cannot write one file
            if app.importing:
                return self.error(409, "An import is already running")
            app.importing = {"kind": kind, "started": time.time(), "state": "uploading"}
        target = os.path.join(migrate.folder(app.config.data_dir), "upload.db" if kind == "plexdb" else "upload.json")
        with open(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as f:
            left = length
            while left:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        if left:
            app.importing = None
            return self.error(400, "The upload stopped before the end")
        app.importing = {"kind": kind, "started": time.time()}

        def work():
            try:
                accounts = migrate.read_plex_db(target) if kind == "plexdb" else migrate.read_file(target)
                migrate.save_history(app.config.data_dir, "Plex database" if kind == "plexdb" else "History file", accounts)
                app.import_result = {"ok": True, "message": f"Read {sum(len(v) for v in accounts.values())} films and episodes from {len(accounts)} accounts"}
            except Exception as e:  # shown on the page
                app.import_result = {"ok": False, "message": f"Could not read that file: {str(e)[:200]}"}
            finally:
                app.importing = None
                try:
                    os.remove(target)  # Starboard's own upload copy; the history it read is kept
                except OSError:
                    pass

        threading.Thread(target=work, name="import", daemon=True).start()
        return self.json(200, {"started": True})

    def first_password(self):
        app = self.app
        if not app.needs_setup:
            return self.error(409, "A password is already set. Sign in instead")
        address = self.client_address_text()
        if not app.limits.attempt(address):
            return self.error(429, "Too many attempts. Wait 15 minutes and try again")
        data = self.body()
        if not app.setup_token or not auth.hmac.compare_digest(str(data.get("token", "")).strip(), app.setup_token):
            return self.error(403, "The setup code is not right. Find it in the installer's output or the server log")
        password = str(data.get("password", ""))
        problem = auth.password_problem(password)
        if problem:
            return self.error(400, problem)
        if "site_name" in data:
            app.config.update_general({"site_name": data["site_name"]})
        app.config.data["auth"]["password_hash"] = auth.hash_password(password)
        app.config.data["last_version"] = app.version if re.match(r"^\d+\.\d+\.\d+$", app.version or "") else ""
        app.config.save()
        app.setup_token = None
        App._remove_setup_token(app.config.data_dir)
        app.limits.clear(address)
        return self.json(200, {"ok": True}, self.new_session(bool(data.get("remember"))))

    def login(self):
        app = self.app
        address = self.client_address_text()
        if not app.limits.attempt(address):
            return self.error(429, "Too many attempts. Wait 15 minutes and try again")
        data = self.body()
        if app.needs_setup or not auth.check_password(str(data.get("password", "")), app.config.data["auth"]["password_hash"]):
            logs.event("warning", "sign-in", "A sign-in used the wrong password")
            return self.error(401, "That password is not right")
        app.limits.clear(address)
        logs.event("info", "sign-in", "Signed in")
        return self.json(200, {"ok": True}, self.new_session(bool(data.get("remember"))))

    def check_password(self, data):
        """Downloading or restoring settings needs the password again: the file holds API keys."""
        app = self.app
        address = self.client_address_text()
        if not app.limits.attempt(address):
            raise PasswordProblem(429, "Too many attempts. Wait 15 minutes and try again")
        if not auth.check_password(str(data.get("password", "")), app.config.data["auth"]["password_hash"]):
            raise PasswordProblem(401, "That password is not right")
        app.limits.clear(address)

    def change_password(self):
        app = self.app
        address = self.client_address_text()
        if not app.limits.attempt(address):
            return self.error(429, "Too many attempts. Wait 15 minutes and try again", reason="password")
        data = self.body()
        if not auth.check_password(str(data.get("current", "")), app.config.data["auth"]["password_hash"]):
            return self.error(401, "Your current password is not right", reason="password")
        app.limits.clear(address)
        new = str(data.get("new", ""))
        problem = auth.password_problem(new)
        if problem:
            return self.error(400, problem)
        app.config.data["auth"]["password_hash"] = auth.hash_password(new)
        app.config.data["auth"]["session_version"] = app.session_version + 1
        app.config.save()
        remember = app.sessions.remembered(self.token())
        app.sessions.end_all()
        logs.event("info", "sign-in", "Password changed; other sessions signed out")
        return self.json(200, {"ok": True}, self.new_session(remember))


class BoundedServer(ThreadingHTTPServer):
    """At most 64 requests at once; more wait their turn (a home dashboard never needs more)."""
    request_queue_size = 64
    _slots = threading.BoundedSemaphore(64)

    def process_request(self, request, client_address):
        if not self._slots.acquire(timeout=10):
            self.shutdown_request(request)
            return
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def make_server(host, port, data_dir_or_app):
    app = data_dir_or_app if isinstance(data_dir_or_app, App) else App(data_dir_or_app)
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = BoundedServer((host, port), handler)
    server.daemon_threads = True
    return server, app
