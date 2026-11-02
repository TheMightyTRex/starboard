"""The web server: static pages, the JSON API and the security rules around both."""

import json
import mimetypes
import os
import posixpath
import ipaddress
import re
import socket
import threading
import time
import urllib.parse
import urllib.request
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import auth, backup, containers, icons, schedule, services, sysinfo
from .config import Config, ConfigError, new_setup_token, validate_service

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


class App:
    def __init__(self, data_dir):
        self.config = Config(data_dir)
        self.sessions = auth.Sessions(data_dir)
        self.limits = auth.RateLimit()
        self.version = read_version()
        self.disks = sysinfo.disk_paths_from_env()
        self.history = sysinfo.History(data_dir) if os.environ.get("STARBOARD_HISTORY", "1") != "0" else None
        self.schedule = schedule.Schedule(self.config)
        if os.environ.get("STARBOARD_SCHEDULE", "1") != "0":
            self.schedule.start()
        self.repo = os.environ.get("STARBOARD_REPO", "")  # "owner/name" for the update check; optional
        self.trust_proxy = os.environ.get("STARBOARD_TRUST_PROXY", "") == "1"
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
            print(f"[starboard] First run. Open the dashboard and enter this setup code: {self.setup_token}", flush=True)

    @staticmethod
    def _remove_setup_token(data_dir):
        try:
            os.remove(os.path.join(data_dir, "setup-token"))
        except FileNotFoundError:
            pass

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

    @property
    def needs_setup(self):
        return not self.config.data["auth"].get("password_hash")

    @property
    def session_version(self):
        return self.config.data["auth"].get("session_version", 1)

    def latest_release(self):
        """Asks GitHub for the newest release tag at most every 6 hours. Off when STARBOARD_REPO is not set."""
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
                    f"https://api.github.com/repos/{self.repo}/releases/latest",
                    headers={"Accept": "application/vnd.github+json", "User-Agent": "Starboard"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    self._latest["tag"] = json.loads(resp.read(200000)).get("tag_name")
            except (OSError, ValueError):
                pass
            return self._latest["tag"]


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
    server_version = "Starboard"
    sys_version = ""
    app: App = None  # set by make_server

    # Plumbing ----------------------------------------------------------

    def log_message(self, fmt, *args):
        # Keep logs free of query strings (search terms) and cookies.
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            return
        print(f"[starboard] {self.command} {path} {args[1] if len(args) > 1 else ''}", flush=True)

    def client_address_text(self):
        if self.app.trust_proxy:
            forwarded = self.headers.get("X-Forwarded-For", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def is_https(self):
        return self.app.trust_proxy and self.headers.get("X-Forwarded-Proto", "") == "https"

    def send(self, status, body=b"", content_type="application/json; charset=utf-8", extra=None):
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

    def error(self, status, message):
        self.json(status, {"error": message})

    def body(self, limit=MAX_BODY):
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise ValueError("That request is too large")
        raw = self.rfile.read(length) if length else b"{}"
        data = json.loads(raw or b"{}")
        if not isinstance(data, dict):
            raise ValueError("Send a JSON object")
        return data

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

    def do_GET(self):
        if self.local_only_refused():
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/healthz":
            return self.send(200, b"ok", "text/plain; charset=utf-8")
        if path.startswith("/api/"):
            return self.api("GET", path)
        return self.static(path)

    def do_POST(self):
        self.mutating("POST")

    def do_PUT(self):
        self.mutating("PUT")

    def do_DELETE(self):
        self.mutating("DELETE")

    def mutating(self, method):
        if self.local_only_refused():
            return
        path = urllib.parse.urlparse(self.path).path
        if not path.startswith("/api/"):
            return self.error(405, "Not allowed")
        if not self.same_origin():
            return self.error(403, "Blocked: this request did not come from the dashboard")
        self.api(method, path)

    def static(self, path):
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
        with open(full, "rb") as f:
            data = f.read()
        kind = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml", "application/manifest+json"):
            kind += "; charset=utf-8"
        extra = {"Cache-Control": "no-cache"}  # small files on a home network; updates show at once
        if path in ("/favicon.svg", "/icon-app.svg"):
            # The logo switches colours for dark mode with its own small style block, and runs nothing.
            extra["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        self.send(200, data, kind, extra)

    def api(self, method, path):
        app = self.app
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
                })
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
                cfg.update_general(self.body())
                if cfg.data.get("network_access", True) != before and app.on_network_change:
                    # Answer first, then move the listener.
                    threading.Timer(0.5, app.on_network_change).start()
                return self.json(200, cfg.public())
            if path == "/api/network" and method == "GET":
                return self.json(200, app.network_info(self.client_address[0]))
            if path == "/api/services" and method == "POST":
                service_id = cfg.upsert_service(self.body())
                return self.json(200, {"id": service_id, "config": cfg.public()})
            if path == "/api/services/order" and method == "POST":
                cfg.reorder_services(self.body().get("ids", []))
                return self.json(200, cfg.public())
            if path == "/api/services/test" and method == "POST":
                incoming = self.body()
                stored = cfg.service(incoming.get("id", "")) if incoming.get("id") else None
                if stored and not incoming.get("api_key"):
                    incoming["api_key"] = stored.get("api_key", "")
                candidate = validate_service(incoming)
                candidate["id"] = candidate.get("id") or "test"
                return self.json(200, services.check(candidate))
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
                    return self.json(200, cfg.public())
            if path == "/api/status" and method == "GET":
                return self.json(200, {"items": services.status_all(cfg.data["services"])})
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
                return self.json(200, services.app_updates(cfg.data["services"]))
            if path == "/api/queue" and method == "GET":
                return self.json(200, services.queue(cfg.data["services"]))
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
            if path == "/api/schedule" and method == "GET":
                return self.json(200, app.schedule.status())
            if path == "/api/schedule" and method == "POST":
                return self.json(200, app.schedule.act(str(self.body().get("action", ""))))
            if path == "/api/calendar" and method == "GET":
                return self.json(200, services.calendar(cfg.data["services"], cfg.data["upcoming_days"]))
            if path == "/api/health" and method == "GET":
                return self.json(200, services.health(cfg.data["services"]))
            if path == "/api/history" and method == "GET":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                hours = {"1": 1, "6": 6, "24": 24}.get(q.get("hours", ["1"])[0], 1)
                return self.json(200, {"hours": hours, "interval": sysinfo.History.INTERVAL,
                                       "points": app.history.get(hours) if app.history else []})
            if path == "/api/monitor" and method == "GET":
                return self.json(200, sysinfo.monitor())
            if path == "/api/interfaces" and method == "GET":
                return self.json(200, {"items": sysinfo.interfaces()})
            if path == "/api/disk-health" and method == "GET":
                return self.json(200, sysinfo.disk_health())
            if path == "/api/system" and method == "GET":
                return self.json(200, sysinfo.snapshot(app.disks))
            if path == "/api/version" and method == "GET":
                return self.json(200, {"current": app.version, "latest": app.latest_release(), "repo": app.repo})
            if path == "/api/backup/settings" and method == "POST":
                self.check_password(self.body())
                return self.json(200, backup.export(cfg, app.version))
            if path == "/api/backup/restore" and method == "POST":
                data = self.body(limit=2 * 1024 * 1024)
                self.check_password(data)
                count = backup.restore(cfg, data.get("backup"))
                return self.json(200, {"apps": count, "config": cfg.public()})
            if path == "/api/backup/saved" and method == "GET":
                return self.json(200, {"items": backup.saved_copies(cfg)})
            if path == "/api/backup/restore-saved" and method == "POST":
                data = self.body()
                self.check_password(data)
                count = backup.restore_saved(cfg, str(data.get("name", "")))
                return self.json(200, {"apps": count, "config": cfg.public()})
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
            return self.error(e.status, e.message)
        except (ConfigError, ValueError) as e:
            return self.error(400, str(e))
        except OSError:
            return self.error(404, "That file is not there any more")
        except services.ServiceError as e:
            return self.error(502, str(e))
        except containers.DockerError as e:
            return self.error(502, str(e))

    def icon(self, service_id):
        service = self.app.config.service(service_id)
        found = icons.get(service, os.path.join(self.app.config.data_dir, "icons")) if service else None
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

    def first_password(self):
        app = self.app
        if not app.needs_setup:
            return self.error(409, "A password is already set. Sign in instead")
        address = self.client_address_text()
        if app.limits.blocked(address):
            return self.error(429, "Too many attempts. Wait 15 minutes and try again")
        data = self.body()
        if not app.setup_token or not auth.hmac.compare_digest(str(data.get("token", "")).strip(), app.setup_token):
            app.limits.fail(address)
            return self.error(403, "The setup code is not right. Find it in the installer's output or the server log")
        password = str(data.get("password", ""))
        problem = auth.password_problem(password)
        if problem:
            return self.error(400, problem)
        if "site_name" in data:
            app.config.update_general({"site_name": data["site_name"]})
        app.config.data["auth"]["password_hash"] = auth.hash_password(password)
        app.config.save()
        app.setup_token = None
        App._remove_setup_token(app.config.data_dir)
        return self.json(200, {"ok": True}, self.new_session(bool(data.get("remember"))))

    def login(self):
        app = self.app
        address = self.client_address_text()
        if app.limits.blocked(address):
            return self.error(429, "Too many attempts. Wait 15 minutes and try again")
        data = self.body()
        if app.needs_setup or not auth.check_password(str(data.get("password", "")), app.config.data["auth"]["password_hash"]):
            app.limits.fail(address)
            return self.error(401, "That password is not right")
        app.limits.clear(address)
        return self.json(200, {"ok": True}, self.new_session(bool(data.get("remember"))))

    def check_password(self, data):
        """Downloading or restoring settings needs the password again: the file holds API keys."""
        app = self.app
        address = self.client_address_text()
        if app.limits.blocked(address):
            raise PasswordProblem(429, "Too many attempts. Wait 15 minutes and try again")
        if not auth.check_password(str(data.get("password", "")), app.config.data["auth"]["password_hash"]):
            app.limits.fail(address)
            raise PasswordProblem(401, "That password is not right")

    def change_password(self):
        app = self.app
        address = self.client_address_text()
        if app.limits.blocked(address):
            return self.error(429, "Too many attempts. Wait 15 minutes and try again")
        data = self.body()
        if not auth.check_password(str(data.get("current", "")), app.config.data["auth"]["password_hash"]):
            app.limits.fail(address)
            return self.error(401, "Your current password is not right")
        new = str(data.get("new", ""))
        problem = auth.password_problem(new)
        if problem:
            return self.error(400, problem)
        app.config.data["auth"]["password_hash"] = auth.hash_password(new)
        app.config.data["auth"]["session_version"] = app.session_version + 1
        app.config.save()
        remember = app.sessions.remembered(self.token())
        app.sessions.end_all()
        return self.json(200, {"ok": True}, self.new_session(remember))


def make_server(host, port, data_dir_or_app):
    app = data_dir_or_app if isinstance(data_dir_or_app, App) else App(data_dir_or_app)
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server, app
