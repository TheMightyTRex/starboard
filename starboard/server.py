"""The web server: static pages, the JSON API and the security rules around both."""

import base64
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

from . import start as how_to_start
from . import places  # location and keyboard, both set-ups' first questions (DASH-259)
from . import library  # the Library and Search from Reelix (DASH-163, DASH-162)
from . import access, auth, backup, helpdocs, setup_left, reelix_admin, reelix_move, reelix_setup, reelix_waiting, requests_route, tasklist, takeover, usenet_move, changes, containers, copyset, discovery, icons, jobs, listening, livetv, logs, migrate, pool, posters, releases, schedule, services, stack, sysinfo, uxnotes, watch
from .config import GENERAL_RIGHTS, Config, ConfigError, general_right, new_setup_token, same_server, validate_service

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
COOKIE = "starboard_session"
MAX_BODY = 64 * 1024

PUBLIC_PAGES = {"/login.html", "/setup.html"}
PUBLIC_PREFIXES = ("/css/", "/js/", "/fonts/", "/icons/")
PUBLIC_FILES = {"/favicon.svg", "/icon-app.svg", "/manifest.webmanifest"}



def _snaglist_style():
    """Snaglist (Settings, General, Testing) sets its styles with one <style> in its own shadow root. Its hash lets
    exactly that stylesheet in, so the policy still refuses every other inline style."""
    try:
        with open(os.path.join(WEB, "js", "snaglist.js"), encoding="utf-8") as f:
            css = re.search(r"const CSS_TEXT = `([^`\\$]*)`;", f.read())
    except OSError:
        return ""
    return f" 'sha256-{base64.b64encode(hashlib.sha256(css.group(1).encode()).digest()).decode()}'" if css else ""


SECURITY_HEADERS = {
    "Content-Security-Policy": (
        f"default-src 'self'; img-src 'self' data: https:; style-src 'self'{_snaglist_style()}; script-src 'self'; "
        "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    # Other sites cannot load Starboard's files into their pages. The Live TV logos are the exception (iptv()):
    # Jellyfin's pages may show them from another address. No Cross-Origin-Embedder-Policy: it would block the
    # cover pictures that search results load from other sites.
    "Cross-Origin-Resource-Policy": "same-origin",
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


# Links to the styles, scripts, icons and font inside pages, scripts and styles. Each gets ?v= and the linked file's
# own hash when it is served, so the browser can keep that file for a year and ask for it again only when it changes.
_LINK = re.compile(rb"(?<![\w.])((?:/|\.\./)(?:css|js|icons|fonts)/[\w.-]+\.(?:css|js|svg|woff2))(?=[#\"')])")


def _versioned(full, data, depth=0):
    """data with each link to a file under web/ given ?v=<that file's hash>, and the files it depends on."""
    deps = {}

    def tag(match):
        link = match.group(1).decode()
        target = os.path.realpath(os.path.join(os.path.dirname(full), link) if link.startswith("..") else os.path.join(WEB, link.lstrip("/")))
        if not target.startswith(WEB + os.sep) or not os.path.isfile(target) or depth > 2:
            return match.group(1)
        version = static_file(target, depth + 1)[2].strip('"')
        deps[target] = version
        return match.group(1) + b"?v=" + version.encode()

    return _LINK.sub(tag, data), deps


def static_file(full, depth=0):
    """(bytes, gzip bytes or None, ETag, content type) for a file under web/, read and compressed once and kept
    until the file, or a file it links to, changes. The whole web folder is well under a megabyte."""
    st = os.stat(full)
    key = (st.st_mtime_ns, st.st_size)
    with _static_lock:
        hit = _static.get(full)
    if hit and hit[0] == key and all(static_file(d, depth + 1)[2].strip('"') == v for d, v in hit[2].items()):
        return hit[1]
    with open(full, "rb") as f:
        data = f.read()
    kind = mimetypes.guess_type(full)[0] or "application/octet-stream"
    text = kind.startswith("text/") or kind in ("application/javascript", "image/svg+xml", "application/manifest+json")
    deps = {}
    if text:
        kind += "; charset=utf-8"
        if full.endswith((".html", ".js", ".css")):
            data, deps = _versioned(full, data, depth)
    # Only the compressed copy is kept when there is one; the rare browser without gzip gets it unpacked.
    packed = gzip.compress(data, 9) if text and len(data) > 1024 else None
    tag = '"' + hashlib.sha256(data).hexdigest()[:20] + '"'
    value = (None if packed else data, packed, tag, kind)
    with _static_lock:
        _static[full] = (key, value, deps)
    return value


# Endings a home router or the computer itself gives a name: myserver.local, myserver.lan and so on.
HOME_ENDINGS = ("local", "lan", "home", "home.arpa", "localdomain", "internal")
# The first password is chosen once: two requests at the same moment cannot both choose it.
FIRST_PASSWORD_LOCK = threading.Lock()

class App:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.config = Config(data_dir)
        self.uxnotes = uxnotes.UxNotes(data_dir)
        self._feedback_keys = {}  # Snaglist's key -> the session it was given to
        self._feedback_lock = threading.Lock()
        self.log = logs.start(data_dir, lambda: self.config.data["logs"], lambda: [self.config.data.get("site_name", "")])
        self.sessions = auth.Sessions(data_dir)
        if os.path.exists(os.path.join(data_dir, "reset-password")):
            self._reset_password(data_dir)
        self.limits = auth.RateLimit()
        self.version = read_version()
        self.config.version = self.version  # saved settings copies record the version (DASH-109)
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
        from . import recovery  # after an unexpected shutdown: one check at start (DASH-88)
        if os.environ.get("STARBOARD_RECOVERY", "1") != "0":
            recovery.start(self)
        self.watch = watch.Watch(self)
        if os.environ.get("STARBOARD_WATCH", "1") != "0":
            self.watch.start()
            watch.keep_vpn_apps()  # apps on the VPN rejoin it after it restarts (12 November 2026)
        self.jobs = jobs.Jobs(self)
        from . import plugin_life  # plug-in events and jobs (DASH-330): nothing runs until a plug-in asks
        plugin_life.listen(self.data_dir)
        services.ON_CHANGE = plugin_life.emit
        self.plugin_clock = plugin_life.Clock(self.data_dir, self.config)
        from . import plugin_watch  # idle stop and health for every plug-in (DASH-357)
        plugin_watch.DATA_DIR = self.data_dir
        self.plugin_idle = plugin_watch.Watcher(self.data_dir)
        if os.environ.get("STARBOARD_JOBS", "1") != "0":
            self.jobs.ensure()
            self.plugin_clock.ensure()
            self.plugin_idle.ensure()
            threading.Thread(target=_move_livetv, args=(self,), name="livetv-move", daemon=True).start()
            # DASH-253: titles a move into Reelix could not match; asleep while there are none.
            reelix_waiting.start(self.data_dir, lambda: library.reelix_of(self.config.data["services"]))
        self.importing = None  # the watch history import that is running, if any
        self.import_result = None
        self.import_lock = threading.Lock()
        self.download_links = {}  # one-time links for server backup downloads: token: (file name, until)
        self.listening_busy = None  # reading listening progress, if it is running
        self.listening_read = None
        self.schedule = schedule.Schedule(self.config)
        if os.environ.get("STARBOARD_SCHEDULE", "1") != "0":
            self.schedule.start()
        from .config import prune_saved
        prune_saved(os.path.join(data_dir, "backups"), self.config.data.get("backup_keep_versions", 5))  # DASH-109
        from . import backup_schedule  # DASH-17: a thread only while Weekly or Nightly is chosen
        self.backup_schedule = backup_schedule.Scheduler(self)
        if os.environ.get("STARBOARD_SCHEDULE", "1") != "0":
            self.backup_schedule.ensure()
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

    MAX_FEEDBACK_KEYS = 100

    def feedback_key(self, token):
        """A key for Snaglist's reports, good while the session it was given to is."""
        with self._feedback_lock:
            for k, t in list(self._feedback_keys.items()):
                if t == token:
                    return k
            while len(self._feedback_keys) >= self.MAX_FEEDBACK_KEYS:
                self._feedback_keys.pop(next(iter(self._feedback_keys)))
            key = secrets.token_urlsafe(24)
            self._feedback_keys[key] = token
            return key

    def feedback_key_valid(self, key):
        token = self._feedback_keys.get(key) if key else None
        return bool(token) and self.sessions.valid(token, self.session_version)

    def host_allowed(self, name):
        if not name or name in ("localhost",) or name.endswith(".localhost") or name in self.allowed_hosts:
            return True
        try:
            ipaddress.ip_address(name)
            return True
        except ValueError:
            pass
        # The machine's own name, alone or with a home-network ending. Not any name that starts with it, which a
        # web page could point at this server (DNS rebinding), such as raspberrypi.attacker.example.
        if self.machine_name and name in {self.machine_name} | {f"{self.machine_name}.{end}" for end in HOME_ENDINGS}:
            return True
        return any(name.endswith("." + h) for h in self.allowed_hosts if h.startswith("."))

    def listen_host(self):
        if self.forced_host:
            return self.forced_host
        return "0.0.0.0" if self.config.data.get("network_access", True) else "127.0.0.1"  # the home network, by the person's choice (Settings, Security)  # nosec B104

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
        """The day's reading of used space, if not taken yet (no thread of its own). Also notes that Starboard is
        still running, for the check after an unexpected shutdown (DASH-88)."""
        from . import recovery
        recovery.heartbeat(self.data_dir)
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
                with urllib.request.urlopen(req, timeout=6) as resp:  # a fixed https address  # nosec B310
                    self._latest["tag"] = newest_tag(t.get("name", "") for t in json.loads(resp.read(500000)))
            except (OSError, ValueError):
                pass
            return self._latest["tag"]


def newest_tag(names):
    """The highest vX.Y.Z among tag names (test builds such as v0.5.0-dev.1 are left out)."""
    found = [(tuple(int(x) for x in m.groups()), n) for n in names if (m := re.match(r"^v(\d+)\.(\d+)\.(\d+)$", n or ""))]
    return max(found)[1] if found else None


def newer(tag, version):
    """True when tag (vX.Y.Z) is a later version than version (X.Y.Z)."""
    def key(v):
        m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", str(v or ""))
        return tuple(int(x) for x in m.groups()) if m else None
    a, b = key(tag), key(version)
    return bool(a and b and a > b)


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


KEEP_ALIVE_IDLE = 10  # seconds a kept-alive connection waits for the browser's next request


def add_found(app, items):
    """Adds apps that Search for new apps found. Each one's API key is read from its own settings file through
    Docker when asked and possible; otherwise it is added without one, to fill in later."""
    if not isinstance(items, list) or not items:
        raise ValueError("Choose the apps to add")
    cfg = app.config
    added, missing_keys = [], []
    for it in items[:60]:
        if not isinstance(it, dict) or it.get("key") not in discovery.CATALOGUE:
            continue
        name, kind, _, _, needs_key, background = discovery.CATALOGUE[it["key"]]
        url = str(it.get("url", ""))
        if not re.match(r"^http://127\.0\.0\.1:\d{2,5}$", url):
            continue  # only what discovery itself found on this computer
        key = discovery.read_key(it["key"], str(it.get("container", ""))) if it.get("read_key") else None
        if it["key"] == "nzbget" and not key and url == stack.app_url(app.data_dir, "nzbget", 6789):
            key = stack.nzbget_key(app.data_dir)  # the sign-in Install apps made up, only for the NZBGet it set up
        if it["key"] == "sabnzbd" and not key and url == stack.app_url(app.data_dir, "sabnzbd", stack.SABNZBD_PORT):
            key = stack.sabnzbd_key(app.data_dir)  # the API key Install apps made up, only for the SABnzbd it set up
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


ADOPT_FOR = 1800  # seconds Starboard keeps looking for the apps Install apps started


def adopt_started_apps(app, keys, after_job=True, wait=5.0):
    """After Install apps started its apps: adds them to Starboard as each one answers, so they reach the dashboard
    even when the person has left the page. An app opens its port a while after it starts (with every app starting
    at once on a small server, Radarr took over 4 minutes), so it keeps looking for up to 30 minutes. What is still
    to add is kept in data/stack/adopt.json, so a restart of Starboard (the installer rebuilds it at the end of the
    set-up) carries on where it was (resume_adopting)."""
    keys = sorted(set(keys) & set(discovery.CATALOGUE))
    if not keys:
        return
    stack.want_adopted(app.data_dir, keys, time.time() + ADOPT_FOR)
    threading.Thread(target=_adopt, args=(app, after_job, wait), name="adopt-apps", daemon=True).start()


def reelix_after_start(app, password):
    """Once the apps Install apps started are running, sets Reelix up (reelix_setup), if it was among them. The password
    is the one just checked; it is used for these calls and dropped when they finish. A Reelix set up before gets
    Jellyfin and Audiobookshelf when Starboard has their keys (DASH-156, reelix_sites.after_install)."""
    if not reelix_setup.read_setup(app.data_dir):
        from . import app_setup, reelix_sites
        # No Reelix: Jellyfin's and Audiobookshelf's first runs still happen (DASH-179, DASH-180).
        try:
            groups = set(stack.chosen_groups(app.data_dir) or [])
            from . import setup_answers
            done = app_setup.first_runs(app.config, app.data_dir, password, groups) + setup_answers.apply_usenet(app.data_dir)
            if done:
                logs.event("info", "install apps", "; ".join(done))
        except (OSError, ValueError) as e:
            logs.event("warning", "install apps", f"Jellyfin and Audiobookshelf are not set up yet: {e}")
        reelix_sites.after_install(app, password)
        app.jobs.ensure()  # VPN port forwarding starts once Gluetun and qBittorrent have their keys (DASH-233)
        return

    def run():
        began = time.time()
        while not stack.job().get("finished"):
            if time.time() - began > 3600:
                return
            time.sleep(5)
        try:
            done = reelix_setup.set_up(app.config, app.data_dir, password, qbit=reelix_setup.qbit_lasting_password(), nzbget=reelix_setup.nzbget_ready())
            services.forget()
            logs.event("info", "install apps", "Reelix set up: " + "; ".join(done))
            app.jobs.ensure()  # VPN port forwarding starts once Gluetun and qBittorrent have their keys (DASH-233)
        except reelix_setup.ReelixError as e:
            logs.event("warning", "install apps", f"Reelix is not set up yet: {e}")
    threading.Thread(target=run, name="reelix-setup", daemon=True).start()


def _installer_started_since(app, since):
    try:
        return os.path.getmtime(os.path.join(stack.folder(app.data_dir), "started-at")) >= since
    except OSError:
        return False


MOVED_BY_REELIX = ("radarr", "sonarr", "lidarr", "bookshelf", "prowlarr", "seerr")  # what Reelix's migrator reads


def typed_secrets(given):
    """The hidden keys typed in the move's preview (DASH-128): {source: {"indexer:3:apiKey": value}}, or flat
    {"indexer:3:apiKey": value} for every app. Empty values are dropped; never logged."""
    out = {}
    for k, v in list((given if isinstance(given, dict) else {}).items())[:200]:
        if isinstance(v, dict):
            mine = {str(a)[:100]: str(b)[:500] for a, b in list(v.items())[:200] if b}
            if mine:
                out[str(k)[:40]] = mine
        elif v:
            out[str(k)[:100]] = str(v)[:500]
    return out


def after_takeover(app, password, p, sab_ini):
    """Once Starboard's stack runs with the apps it took over: SABnzbd's servers into NZBGet, Reelix's download apps
    by their names on Starboard's stack (gluetun when they run through the VPN), and the apps on the dashboard. The
    password (just checked) signs in to Reelix and is dropped when this finishes. Returns notes for the page. `tasks`
    (the dialog's list, DASH-252) hears each of these steps."""
    def finish(ok, tasks=None):
        mark = tasks or tasklist.Tasks()
        if not ok:
            return ["Nothing was changed: the old apps run again as they were"]
        notes = []
        apps = p["choice"]["apps"]
        vpn = "gluetun" in apps
        if sab_ini and "nzbget" in apps:
            mark.start("usenet", now="Moving the Usenet servers into NZBGet")
            try:
                moved = usenet_move.write_to_nzbget(reelix_setup.nzbget_rpc(stack.nzbget_key(app.data_dir)),
                                                    usenet_move.parse_sab_servers(sab_ini))
                notes.append(f"Moved {moved} Usenet {'server' if moved == 1 else 'servers'} from SABnzbd to NZBGet")
            except (reelix_setup.ReelixError, OSError, ValueError) as e:
                notes.append(f"SABnzbd's servers did not move into NZBGet ({e}). Add them in NZBGet, Settings, News-servers")
                mark.fail("usenet", notes[-1])
            if mark.state("usenet") == "working":
                mark.done("usenet", notes[-1])
        base = stack.reelix_url(app.data_dir)
        if base and "reelix" in apps:
            mark.start("reelix", now="Waiting for Reelix to answer, then connecting it to the download apps")
            try:
                reelix_setup.wait_until_up(base)
                if "nzbget" in apps:
                    creds = reelix_setup.nzbget_ready()(app.data_dir)
                    notes += reelix_setup.switch_usenet(base, password, "nzbget", "gluetun" if vpn else "nzbget", creds=creds)
                elif "sabnzbd" in apps and sab_ini:
                    # DASH-128: a SABnzbd that stays hides its key from the old apps, so Reelix gets it from
                    # sabnzbd.ini, read before SABnzbd stopped, with the port SABnzbd listens on.
                    notes += reelix_setup.switch_usenet(base, password, "sabnzbd", "gluetun" if vpn else "sabnzbd",
                                                        sab_key=usenet_move.sab_api_key(sab_ini),
                                                        sab_port=usenet_move.sab_port(sab_ini))
                admin = reelix_move._admin(base, password)
                for c in admin.call("GET", "/downloadclients")[1] or []:
                    want = "gluetun" if vpn and c.get("implementation") in ("qbittorrent", "nzbget", "sabnzbd") else None
                    if want and (c.get("settings") or {}).get("host") != want:
                        body = {f: c.get(f) for f in ("implementation", "name", "enabled", "priority", "tags")}
                        body["settings"] = {**(c.get("settings") or {}), "host": want}
                        admin.call("PUT", f"/downloadclients/{c['id']}", body)
                        notes.append(f"Reelix now reaches {c.get('name')} at {want}")
            except (reelix_setup.ReelixError, OSError, ValueError) as e:
                notes.append(f"Reelix's download apps are not changed yet ({e}). Check them in Starboard: Settings, Reelix, Download apps")
                mark.fail("reelix", notes[-1])
            if mark.state("reelix") == "working":
                mark.done("reelix")
        mark.start("dashboard", now="Updating your dashboard")
        # DASH-119: a Bazarr taken over still points at the old Radarr and Sonarr; it now points at Reelix, with its
        # own key (from the dashboard) and Starboard's manager key.
        if "bazarr" in apps and "reelix" in apps:
            from . import app_setup
            svcs = app.config.data["services"]
            bkey = next((s.get("api_key") for s in svcs if s["type"] == "bazarr" and s.get("api_key")), None) or stack.bazarr_key(app.data_dir)
            rkey = next((s.get("api_key") for s in svcs if s.get("icon") == "reelix" and s["type"] == "link" and s.get("api_key")), None)
            burl = stack.app_url(app.data_dir, "bazarr", 6767)
            if bkey and rkey and burl:
                try:
                    notes += app_setup.bazarr_connect(burl, bkey, rkey)
                except app_setup.AppSetupError as e:
                    notes.append(f"Bazarr does not point at Reelix yet: {e}")
        services.forget()
        adopt_started_apps(app, [t["key"] for t in p["take"]] + ["reelix", "nzbget"], after_job=False)
        for r in p["replace"]:
            # Entries added before Starboard marked them (no icon or container) are known by their type or name.
            def theirs(s, r=r):
                kinds = {r["key"], r["name"]} | ({"readarr"} if r["key"] == "bookshelf" else set())
                if s.get("icon") == "reelix":  # Reelix's own entries use the radarr and sonarr types too
                    return False
                return (s.get("icon") in kinds or s.get("container") == r["name"] or s.get("type") in kinds
                        or s.get("name", "").strip().lower() in {r["name"].lower(), r["app"].lower()})
            for s in [s for s in app.config.data["services"] if theirs(s)]:
                app.config.remove_service(s["id"])
                notes.append(f"Took {s['name']} off your apps")
        # DASH-192: Seerr kept beside Reelix runs on Starboard's stack now, so it can be pointed at Reelix.
        route = requests_route.read(app.data_dir)
        if route and not route.get("applied"):
            applied, said = requests_route.apply(app.config, app.data_dir, route["choice"])
            requests_route.save(app.data_dir, route["choice"], applied, said)
            notes += said
        mark.done("dashboard")
        logs.event("info", "take over", "; ".join(notes) or "Took over your apps")
        return notes
    return finish


def remove_entries(app, keys_and_names):
    """Takes the dashboard entries of apps Reelix replaced off the dashboard (DASH-191): matched by their icon, type,
    container or name, never Reelix's own entries (which use the radarr and sonarr types too). Returns notes."""
    notes = []
    for key, name, label in keys_and_names:
        kinds = {key, name} | ({"readarr"} if key == "bookshelf" else set())
        for s in [s for s in app.config.data["services"] if s.get("icon") != "reelix" and (
                s.get("icon") in kinds or s.get("container") == name or s.get("type") in kinds
                or s.get("name", "").strip().lower() in {name.lower(), label.lower()})]:
            app.config.remove_service(s["id"])
            notes.append(f"Took {s['name']} off your apps")
    return notes


def after_install_change(app, password, plan, sab_ini, by_installer=None, sab_from_installer=False):
    """Once the changed apps run: adds the new ones to the dashboard, takes away the ones removed, and when the Usenet
    app changed, moves SABnzbd's servers into NZBGet and swaps Reelix's download app. The password (just checked) is
    used for Reelix's sign-in and dropped when this finishes."""
    def run():
        began = time.time()
        ini = sab_ini
        if by_installer:
            while not _installer_started_since(app, by_installer):
                if time.time() - began > 3600:
                    return
                time.sleep(5)
            if sab_from_installer and not ini:
                copy = os.path.join(stack.folder(app.data_dir), "sab-servers.ini")
                try:
                    with open(copy, encoding="utf-8", errors="replace") as f:
                        ini = f.read(1_000_000)
                except OSError:
                    ini = None
                finally:
                    try:
                        os.remove(copy)  # it holds the Usenet passwords: kept no longer than needed
                    except OSError:
                        pass
        else:
            while not stack.job().get("finished"):
                if time.time() - began > 3600:
                    return
                time.sleep(5)
            if not stack.job().get("ok"):
                return
        notes = []
        cfg = app.config
        for key in plan["remove"]:
            for s in [s for s in cfg.data["services"] if s.get("icon") == key or s.get("container") == key]:
                cfg.remove_service(s["id"])
                notes.append(f"Took {s['name']} off your apps")
        before, after = plan["usenet"]
        vpn = "gluetun" in plan["choice"]["apps"]
        if after and after != before:
            try:
                if after == "nzbget":
                    creds = reelix_setup.nzbget_ready()(app.data_dir)
                    if ini:
                        moved = usenet_move.write_to_nzbget(reelix_setup.nzbget_rpc(stack.nzbget_key(app.data_dir)),
                                                            usenet_move.parse_sab_servers(ini))
                        notes.append(f"Moved {moved} Usenet {'server' if moved == 1 else 'servers'} from SABnzbd to NZBGet")
                    if "reelix" in plan["choice"]["apps"]:
                        notes += reelix_setup.switch_usenet(stack.reelix_url(app.data_dir), password, "nzbget", "gluetun" if vpn else "nzbget", creds=creds)
                elif "reelix" in plan["choice"]["apps"]:
                    sab_key = stack.sabnzbd_key(app.data_dir) or discovery.read_key("sabnzbd", "sabnzbd")
                    notes += reelix_setup.switch_usenet(stack.reelix_url(app.data_dir), password, "sabnzbd", "gluetun" if vpn else "sabnzbd", sab_key=sab_key)
                    notes.append("Add your Usenet servers in SABnzbd, Config, Servers: they are not moved from NZBGet")
            except (reelix_setup.ReelixError, OSError, ValueError) as e:
                notes.append(f"Switching the Usenet app is not finished: {e}")
        if "dispatcharr" in plan["add"] and password:  # an add-on (DASH-228): its admin and a key for Starboard
            from . import app_setup
            notes += app_setup.dispatcharr_first_run(cfg, app.data_dir, password)
        services.forget()
        adopt_started_apps(app, plan["add"], after_job=False)
        logs.event("info", "your install", "; ".join(notes) or "Your install changed")
        with open(os.path.join(stack.folder(app.data_dir), "change-result.json"), "w", encoding="utf-8") as f:
            json.dump({"notes": notes, "finished": time.time()}, f)
    threading.Thread(target=run, name="install-change", daemon=True).start()


def resume_adopting(app):
    """At start: carries on adding the apps a set-up started, if there are any left (see adopt_started_apps)."""
    if stack.adopting(app.data_dir):
        threading.Thread(target=_adopt, args=(app, False, 5.0), name="adopt-apps", daemon=True).start()


_ADOPTING = threading.Lock()  # one thread adds started apps at a time; a second one would only repeat its work
_CHANGING = threading.Lock()  # writing the set-up file and starting it, one request at a time


def _adopt(app, after_job, wait):
    if not _ADOPTING.acquire(blocking=False):
        return  # the running one reads data/stack/adopt.json each round, so it picks up the new apps
    try:
        _adopt_run(app, after_job, wait)
    finally:
        _ADOPTING.release()


def _adopt_run(app, after_job, wait):
    if after_job:
        began = time.time()
        while not stack.job().get("finished"):
            if time.time() - began > 3600:
                return
            time.sleep(wait)
        if not stack.job().get("ok"):
            # Some may still run: look for those, the rest are started again by hand.
            pass
    while True:
        want = stack.adopting(app.data_dir)
        if not want:
            return
        keys, until = want
        try:
            items = discovery.search(app.config.data["services"])["items"]
        except Exception:  # discovery is best effort; the person can still add them by hand
            items = []
        fresh = [i for i in items if i["key"] in keys and not i.get("already")]
        if fresh:
            try:
                added = add_found(app, [{**i, "read_key": i.get("can_read_key", False)} for i in fresh])
                logs.event("info", "install apps", f"Added to Starboard as they answered: {', '.join(added['added'])}")
            except Exception as e:  # noqa: BLE001  (logged; the person can add them in Manage apps)
                logs.event("warning", "install apps", f"Could not add the new apps to Starboard: {e}")
        there = {i["key"] for i in items if i["key"] in keys}
        left = [k for k in keys if k not in there]
        if not left or time.time() >= until:
            stack.want_adopted(app.data_dir, [], 0)
            if left:
                logs.event("info", "install apps", f"Not answering after 30 minutes, so not added: {', '.join(left)}. "
                           "Add them in Settings, Manage apps, Search for new apps.")
            return
        stack.want_adopted(app.data_dir, left, until)
        time.sleep(wait)


def _move_livetv(app):
    """Live TV moves into its plug-in once, a little after start (DASH-285): livetv_move.py says when it does not."""
    import time
    from . import livetv_move
    time.sleep(20)  # Docker and the network are up, and the first pages answered
    try:
        media = (stack.env_values(app.data_dir).get("DATA_DIR") or "").rstrip("/")
        media_dir = f"{media}/media" if media else "/nonexistent-media-folder"
        said = livetv_move.move(app.config, app.data_dir, media_dir, app.jobs.self_url(), log=lambda line: logs.event("info", "live tv", line))
        if said:
            logs.event("info", "live tv", said)
            app.jobs.ensure()
        elif containers.available():
            # Built-in plug-ins follow Starboard's update: their files are written again and active ones restarted.
            from . import plugins_admin
            again = plugins_admin.refresh_builtins(app.data_dir, media_dir, app.config.data["services"])
            again += [n for n in plugins_admin.upgrade_all(app.data_dir, app.config.data["services"]) if n not in again]
            if again:
                logs.event("info", "plug-ins", f"Started again with this version of Starboard: {', '.join(again)}")
    except Exception as e:  # Live TV carries on inside Starboard
        logs.error("live tv", f"Live TV stays in Starboard for now: {e}", e)


def restart_app(service):
    """Restarts the container an app runs in; for one whose network others share (Gluetun), those too, after it, so
    they join its new network. Returns the sentence to show. Raises ValueError in words for the page."""
    if not containers.available():
        raise ValueError("Starboard has no access to Docker here, so it cannot restart apps")
    found = containers.match(service, [{"name": c["name"], "service": ""} for c in containers.containers(light=True)])
    if not found:
        raise ValueError(f"Starboard cannot find the container {service['name']} runs in. Choose it under Container in Edit")
    name = found["name"]
    after = containers.sharers(name)
    try:
        containers.restart(name)
        for other in after:
            containers.restart(other)
    except containers.DockerError as e:
        raise ValueError(f"{service['name']} did not restart: {e}") from None
    services.forget()
    said = f"{service['name']} restarted" + (f", then {', '.join(after)}, which use its network" if after else "")
    logs.event("info", "apps", said)
    return said


class Handler(BaseHTTPRequestHandler):
    # HTTP/1.1 keeps the connection open for the page's styles, scripts and API calls, so a page costs one
    # connection and one thread instead of about 15 (a page took a third of the processor time in testing).
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True  # without it, small answers on a kept-alive connection wait 40 ms
    timeout = 30  # an idle or slow connection is closed after 30 seconds, so it cannot hold a thread for ever

    def send_error(self, code, message=None, explain=None):
        """Python's own error answers (a method Starboard does not handle, a broken request) carry the same
        security headers as every other answer, and close the connection."""
        self.close_connection = True
        body = (message or self.responses.get(code, ("Error",))[0]).encode("latin-1", "replace")
        self.send_response(code, message)
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD" and code >= 200 and code not in (204, 304):
            self.wfile.write(body)

    def handle(self):
        """One request, then more on the same connection while the browser keeps it open. Between requests the
        connection waits only KEEP_ALIVE_IDLE seconds, so idle connections do not hold threads."""
        self.close_connection = True
        self.handle_one_request()
        while not self.close_connection:
            self.connection.settimeout(KEEP_ALIVE_IDLE)
            self.handle_one_request()
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
        if any("\r" in str(v) or "\n" in str(v) for v in (extra or {}).values()) or "\n" in content_type:
            # Python's server does not refuse a line break in a header, which would let a value add headers of its own.
            status, body, content_type, extra = 500, b"A header held a line break", "text/plain; charset=utf-8", None
        self.send_response(status)
        for k, v in SECURITY_HEADERS.items():
            if k not in (extra or {}):  # a response may set a stricter or different policy of its own
                self.send_header(k, v)
        if self.is_https():
            self.send_header("Strict-Transport-Security", "max-age=31536000")
        self.send_header("Content-Type", content_type.replace("\r", "").replace("\n", ""))
        self.send_header("Content-Length", str(len(body)))
        if getattr(self, "close_connection", False) and getattr(self, "request_version", "") == "HTTP/1.1":
            self.send_header("Connection", "close")  # so the browser does not send another request on it
        for k, v in (extra or {}).items():
            self.send_header(k, str(v).replace("\r", "").replace("\n", ""))  # never a line break (refused above too)
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

    def with_changes(self, result):
        """Marks the apps whose changelog Starboard can read, and notes a newer version since the last look."""
        changes.observe(self.app.config.data_dir, result.get("items", []))
        return result

    def error(self, status, message, **extra):
        self.json(status, {"error": message, **extra})

    def body(self, limit=MAX_BODY):
        length = self.content_length()
        if length > limit:
            raise ValueError("That request is too large")
        raw = self.rfile.read(length) if length else b"{}"
        self._body_read = True
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
        if path == "/api/styles.css":
            # Plug-in styles' colours, open before sign-in too: the sign-in page uses the style you chose, and the file
            # holds only colours Starboard checked and wrote itself (DASH-284).
            from . import plugins_admin
            return self.send(200, plugins_admin.styles_css(self.app.data_dir).encode(), "text/css; charset=utf-8", {"Cache-Control": "no-cache"})
        if path.startswith("/api/v1/") or path == "/api/v1":  # the public API, with its own keys (DASH-274)
            from . import api_v1
            return api_v1.handle(self, "GET", path)
        if path.startswith("/api/"):
            return self.api("GET", path)
        if path.startswith("/iptv/"):
            return self.iptv(path)
        return self.static(path)

    def iptv(self, path):
        """For Jellyfin, with no sign-in, only while Live TV is on: channel logos and Pluto stream links."""
        from . import livetv_move  # the plug-in builds the files, Starboard still serves them (DASH-285)
        if not (self.app.config.data["extras"].get("livetv") or livetv_move.plugin_active(self.app.data_dir)):
            return self.send(404, b"", "text/plain; charset=utf-8")
        m = re.match(r"^/iptv/logos/([A-Za-z0-9._-]{1,80}\.png)$", path)
        if m:
            found = livetv.logo_file(m.group(1))
            if not found:
                return self.send(404, b"", "text/plain; charset=utf-8")
            with open(found, "rb") as f:
                return self.send(200, f.read(), "image/png", {"Cache-Control": "max-age=86400", "Cross-Origin-Resource-Policy": "cross-origin"})
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
        if path.startswith("/api/v1/") or path == "/api/v1":  # keys, not the browser's session: no Origin check
            from . import api_v1
            self.close_connection = True  # its body is not read
            return api_v1.handle(self, method, path)
        if not self.same_origin():
            self.close_connection = True  # its body was not read, so the connection cannot carry another request
            return self.error(403, "Blocked: this request did not come from the dashboard")
        self._body_read = False
        try:
            self.api(method, path)
        finally:
            # A body nobody read would be taken for the next request on a kept-alive connection: read and drop a
            # small one, and close the connection after a large one.
            raw = (self.headers.get("Content-Length") or "0").strip()
            if not self._body_read and raw not in ("", "0"):
                if raw.isdigit() and int(raw) <= MAX_BODY and not self.close_connection:
                    self.rfile.read(int(raw))
                else:
                    self.close_connection = True

    def static(self, path):
        if "/." in path or "\\" in path:  # no dot-dot or hidden files: the sign-in check reads the path as given
            return self.send(404, b"Not found", "text/plain; charset=utf-8")
        if path == "/":
            path = "/dashboard.html"  # the landing page (DASH-239)
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
        # A link with ?v= and this file's own hash never changes, so the browser keeps it for a year and does not
        # ask again (pages link to their files that way). Anything else, pages included, is no-cache with an ETag:
        # the browser asks each time and gets "304 Not Modified" until the file changes.
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        fixed = query.get("v", [""])[0] == tag.strip('"')
        extra = {"Cache-Control": "public, max-age=31536000, immutable" if fixed else "no-cache", "ETag": tag, "Vary": "Accept-Encoding"}
        if path == "/upgrade.html" or path in setup_left.PANEL_PAGES:
            # The upgrade guide and the Still to set up steps also open in a slide-out on Starboard's own pages (a frame
            # from this address only; other sites still cannot frame them). Set before
            # the 304 answer too, or a page the browser already has keeps the old refusal.
            extra["Content-Security-Policy"] = SECURITY_HEADERS["Content-Security-Policy"].replace("frame-ancestors 'none'", "frame-ancestors 'self'")
            extra["X-Frame-Options"] = "SAMEORIGIN"
        if self.headers.get("If-None-Match") == tag:
            return self.send(304, b"", kind, extra)
        if packed and self.accepts_gzip():
            data = packed
            extra["Content-Encoding"] = "gzip"
        elif data is None:
            data = gzip.decompress(packed)
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
                "chosen": stack.chosen_keys(app.data_dir) or [],  # the apps in Starboard's own set-up files (DASH-173)
                "existing_media": media, "drives": sysinfo.pool_candidates(app.data_dir),
                "servers": [{"key": i["key"], "name": i["name"]} for i in found
                            if i["key"] in ("plex", "emby", "jellyfin", "audiobookshelf", "sonarr", "radarr", "lidarr")],
                "takeover": self.found_to_take_over(),  # DASH-249: what Moving over says moves, and where
                "written": os.path.exists(os.path.join(stack.folder(app.data_dir), "compose.yaml")),
                "defaults": {"config_dir": f"{base}/media-stack/config", "data_dir": data_dir, "puid": os.getuid() or 1000,
                             "pgid": os.getgid() or 1000, "tz": places.saved(app.data_dir).get("tz") or os.environ.get("TZ") or "Etc/UTC"}}

    def found_to_take_over(self):
        """Apps running here from the person's own Compose file (takeover.found): each with its name and whether Reelix
        takes its place, so Install apps' Moving over step can say what moves into Reelix and what Starboard takes over
        (DASH-249)."""
        try:
            here = [c for c in takeover.found() if c["running"]]
        except containers.DockerError:
            return []
        names = {k: a["name"] for k, a in stack.APPS.items()}
        out = []
        for c in here:
            key = c["key"]
            if key not in stack.APPS:
                continue  # a database: it moves with its app
            out.append({"key": key, "name": names[key], "container": c["name"],
                        "into_reelix": key in MOVED_BY_REELIX,
                        "replaced": key in stack.REPLACED_BY_REELIX})
        return out

    def outside_apps(self):
        """Catalogue apps running from the person's own Compose file, not yet taken over (DASH-250)."""
        try:
            return sorted({c["key"] for c in takeover.found()
                           if c["running"] and c["key"] in stack.APPS and c["key"] not in stack.REPLACED_BY_REELIX})
        except containers.DockerError:
            return []

    def requests_offer(self, route):
        """DASH-192: whether to ask Keep Seerr or Reelix's own requests, the choice made, and the message to send."""
        svcs = self.app.config.data["services"]
        seerr = requests_route.seerr_entry(svcs)
        try:
            outside = any(c["key"] == "seerr" and c["running"] for c in takeover.found())
        except containers.DockerError:
            outside = False
        here = bool(seerr or outside or "seerr" in (stack.chosen_keys(self.app.data_dir) or []))
        reelix = next((s for s in svcs if s.get("icon") == "reelix" and s["type"] == "link"), None)
        if not (here and reelix):
            return None  # asked only while Seerr runs beside Reelix
        address = (reelix or {}).get("outside_link") or (reelix or {}).get("link") or (reelix or {}).get("url") or ""
        seerr_address = (seerr or {}).get("outside_link") or (seerr or {}).get("link") or (seerr or {}).get("url") or ""
        choice = (route or {}).get("choice")
        return {"choice": choice, "recommended": requests_route.RECOMMENDED, "applied": bool((route or {}).get("applied")),
                "notes": (route or {}).get("notes") or [],
                "messages": {c: requests_route.message(c, address, seerr_address) for c in requests_route.CHOICES}}

    def arr_addresses(self):
        """Where Starboard reaches Radarr and Sonarr itself (their dashboard entries), for the ids of titles that did
        not match (DASH-253)."""
        out = {}
        for s in self.app.config.data["services"]:
            if s.get("icon") != "reelix" and s["type"] in ("radarr", "sonarr") and s.get("url"):
                out.setdefault(s["type"], []).append(s["url"])
        return out

    def move_review(self, last):
        """DASH-190: after a move, what to look at: sites held off (Activate), sites Reelix has no definition for,
        and titles that did not move (Add by hand), with the waiting list's titles marked."""
        if not last or not last.get("apps"):
            return None
        waiting = {(w["source"], w["key"]) for w in reelix_waiting.read(self.app.data_dir)}
        no_site, titles, other = [], [], []
        for a in last["apps"]:
            for i in a.get("not_moved") or []:
                why = str(i.get("why") or "")
                if i.get("category") == "indexer":
                    no_site.append({"app": a["app"], "name": i.get("name"), "why": why,
                                    "no_definition": "no definition" in why or "aren't supported" in why})
                elif i.get("category") in ("movie", "series", "author", "artist"):
                    titles.append({"app": a["app"], "name": i.get("name"), "kind": i.get("category"), "why": why,
                                   "waiting": (a["app"], i.get("key") or "") in waiting})
                else:
                    other.append({"app": a["app"], "name": i.get("name"), "category": i.get("category"), "why": why})
        return {"held": last.get("held_sites") or [], "held_count": int(last.get("held") or 0), "sites": no_site,
                "titles": titles[:300], "titles_count": len(titles), "other": other[:100]}

    def takeover_defaults(self):
        """The folders a takeover offers first: the same as Install apps (stack_overview)."""
        host = stack.host_folder(self.app.data_dir)
        base = os.path.dirname(os.path.dirname(os.path.dirname(host))) if host else "/srv"
        media = stack.existing_media()
        data_dir = os.path.commonpath([m["path"] for m in media]) if media else f"{base}/media"
        return {"config_dir": f"{base}/media-stack/config", "data_dir": data_dir if data_dir not in ("/", "") else f"{base}/media"}

    _upgrade = {}

    def upgrade_summary(self):
        """Asked for on every page, and it changes only when the version finished or the set-up does: kept until then."""
        d = self.app.config.data
        key = (d.get("last_version", ""), self.app.version, self.app.needs_setup)
        if Handler._upgrade.get("key") != key:
            p = releases.pending(key[0], key[1], not key[2])
            Handler._upgrade = {"key": key, "value": {"from": p["from"], "to": p["to"], "wizard": p["wizard"], "count": len(p["review"])}}
        return Handler._upgrade["value"]

    CHANGES_STACK = {"/api/install/change", "/api/downloads/vpn", "/api/noip", "/api/stack/write", "/api/stack/start", "/api/reelix/edition",
                     "/api/takeover/start", "/api/takeover/rollback", "/api/takeover/clear", "/api/takeover/clear-away"}

    def api(self, method, path):
        if method == "POST" and path in self.CHANGES_STACK:
            # Writing the set-up file and starting it, one request at a time: two at once could start a half-written file.
            if not _CHANGING.acquire(blocking=False):
                return self.json(409, {"error": "Another change to your apps is being made. Try again in a moment"})
            try:
                return self._api(method, path)
            finally:
                _CHANGING.release()
        return self._api(method, path)

    def _api(self, method, path):
        app = self.app
        fresh = "fresh=1" in urllib.parse.urlparse(self.path).query  # "Check again": skip the shared answers
        if method != "GET":
            services.forget()  # a change (an app added, a setting saved) makes the shared answers out of date
        try:
            # Open routes
            if path == "/api/session" and method == "GET":
                signed_in = self.signed_in()
                from . import plugins_admin
                return self.json(200, {
                    "signed_in": signed_in, "needs_setup": app.needs_setup,
                    # DASH-238: until the first set-up has finished, pages show only the set-up wizard.
                    "first_setup": bool(app.config.data.get("first_setup_pending")) if signed_in else None,
                    "site_name": app.config.data["site_name"], "design": app.config.data["design"],
                    "own_colours": app.config.data.get("own_colours", "teal"),
                    # Not told to people who have not signed in.
                    "version": app.version if signed_in else None,
                    "server_name": app.config.data["server_name"] if signed_in else None,
                    "infinite_scroll": app.config.data.get("infinite_scroll", True) if signed_in else None,
                    "repo": app.repo if signed_in and re.match(r"^[\w.-]+/[\w.-]+$", app.repo or "") else None,
                    # Only what is already known (no call to GitHub here): the footer's "Upgrade available".
                    "latest": app._latest["tag"] if signed_in else None,
                    "upgrade": self.upgrade_summary() if signed_in else None,
                    "ux_notes": bool(signed_in and app.config.data.get("ux_notes")),
                    # The plug-ins added: their menu items show only then (owner, 12 November 2026).
                    "plugins": plugins_admin.added(app.data_dir) if signed_in else [],
                })
            if path == "/api/feedback" and method == "POST":
                # Snaglist sends without cookies, so the key it was given while signed in stands in for them.
                if not (app.config.data.get("ux_notes") and app.feedback_key_valid(self.headers.get("X-Starboard-Feedback", ""))):
                    return self.error(401, "Sign in again, then send the report")
                return self.json(200, {"id": app.uxnotes.add_report(self.body(uxnotes.MAX_REPORT))["id"]})
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
            if path.startswith("/api/radio/review") or path in ("/api/radio/preview", "/api/radio/add-link"):
                # Settings, Radio: the library review and a show from a link, with the manager key (DASH-212)
                from . import radio_review
                return radio_review.route(self, method, path)
            if path.startswith("/api/library/radio-import"):
                # Radio shows already on disk (owner, 10 November 2026), through Reelix's radio review and search.
                from . import own_details, radio_import
                try:
                    if path == "/api/library/radio-import" and method == "GET":
                        out = radio_import.status(app.config)
                        # Your own details for a show with no match (DASH-322), when Reelix has the route (RFX-90).
                        out["own"] = bool(out.get("waiting")) and own_details.available(app.config)
                        return self.json(200, out)
                    body = self.body()
                    if path == "/api/library/radio-import/scan" and method == "POST":
                        return self.json(200, radio_import.scan(app.config, body.get("start", 0)))
                    if path == "/api/library/radio-import/run" and method == "POST":
                        follow = str(body.get("follow") or radio_import.DEFAULT_FOLLOW)
                        out = own_details.run(app.config, "radio", None, body.get("items"), lambda rest: radio_import.run(app.config, rest, follow))
                        setup_left.forget()
                        logs.event("info", "library", f"Brought in {out['added']} radio shows from disk" + (f"; {len(out['errors'])} problems" if out["errors"] else ""))
                        return self.json(200, out)
                except (ValueError, TypeError) as e:
                    return self.error(400, str(e))
                return self.error(404, "Not found")
            if path.startswith("/api/library/import"):
                # DASH-186: films and series already on disk, through Reelix's own library import.
                from . import media_import, own_details
                try:
                    if path == "/api/library/import" and method == "GET":
                        tab = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("tab", [""])[0]
                        found = media_import.folders(app.config, tab)
                        # Your own details for a folder with no match (DASH-322), when Reelix has the route (RFX-90).
                        own = any(f["waiting"] for f in found) and tab in own_details.KINDS and own_details.available(app.config)
                        return self.json(200, {"folders": found, "own": own})
                    body = self.body()
                    scan, run = media_import.scanner(str(body.get("tab") or ""))  # audiobooks, books and music (DASH-282)
                    if path == "/api/library/import/scan" and method == "POST":
                        return self.json(200, scan(app.config, body.get("root"), body.get("start", 0)))
                    if path == "/api/library/import/run" and method == "POST":
                        if body.get("leave"):  # folders left out: not counted again (10 November 2026)
                            media_import.leave_out(app.config, [str(p) for p in body["leave"]][:500])
                            setup_left.forget()
                        if not body.get("items"):
                            return self.json(200, {"added": 0, "errors": []})
                        out = own_details.run(app.config, str(body.get("tab") or ""), body.get("root"), body.get("items"),
                                              lambda rest: run(app.config, body.get("root"), rest))
                        setup_left.forget()  # Still to set up counts the folders again
                        logs.event("info", "library", f"Brought in {out['added']} from disk" + (f"; {len(out['errors'])} problems" if out["errors"] else ""))
                        return self.json(200, out)
                except (media_import.ImportError_, ValueError, TypeError) as e:
                    return self.error(400, str(e))
                return self.error(404, "Not found")
            if path.startswith("/api/ondemand/history"):  # Discover, On demand history (DASH-324)
                from . import library as _lib, ondemand_history
                reelix = _lib.reelix_of(app.config.data["services"])
                try:
                    if path == "/api/ondemand/history" and method == "GET":
                        kind = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("kind", ["all"])[0]
                        return self.json(200, ondemand_history.listing(app.data_dir, reelix, kind))
                    body = self.body()
                    if path == "/api/ondemand/history/want" and method == "POST":
                        if not reelix:
                            return self.error(409, "Add Reelix in Settings, Manage apps, with its key")
                        out = ondemand_history.want(app.data_dir, reelix, str(body.get("kind", "")), str(body.get("id", "")))
                        logs.event("info", "library", f"On demand history: {out['said']}")
                        return self.json(200, out)
                    if path == "/api/ondemand/history/forget" and method == "POST":
                        return self.json(200, ondemand_history.forget(app.data_dir, str(body.get("id", ""))[:40]))
                except LookupError as e:
                    return self.error(404, str(e))
                except (ValueError, services.ServiceError) as e:
                    return self.error(400, str(e))
                return self.error(404, "Not found")
            if path.startswith("/api/library/"):  # the Library and Search, from Reelix (starboard/library.py)
                return library.handle(self, method, path)

            cfg = app.config
            if path == "/api/held" or path.startswith("/api/held/"):  # Held downloads, with the manager key (DASH-210)
                from . import held
                return held.route(self, method, path)
            if path.startswith("/api/reelix/sites/"):  # Search the sites directly, with the manager key (DASH-213)
                from . import reelix_search
                return reelix_search.route(self, method, path)
            if path.startswith("/api/reelix/admin/"):  # Reelix's admin settings, password each time (reelix_admin.py)
                return reelix_admin.route(self, method, path)
            if path == "/api/config" and method == "GET":
                return self.json(200, cfg.public())
            if path == "/api/config/general" and method == "PUT":
                before = cfg.data.get("network_access", True)
                # Each key has its right (DASH-278); a signed-in person holds every right. An API key (DASH-274) will
                # be checked with config.allowed(its right, this right) before anything is saved, and an unknown key
                # refused; from a page, keys Starboard does not know are left out, as they always were.
                incoming = {k: v for k, v in self.body().items() if k in GENERAL_RIGHTS}
                general_right(incoming)
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
                    if "backup_schedule" in incoming:
                        app.backup_schedule.ensure()
                if app.history:
                    app.history.ensure()
                app.usage.ensure()
                if cfg.data.get("network_access", True) != before and app.on_network_change:
                    # Answer first, then move the listener.
                    threading.Timer(0.5, app.on_network_change).start()
                return self.json(200, cfg.public())
            if path == "/api/feedback/key" and method == "GET":
                if not cfg.data.get("ux_notes"):
                    return self.error(404, "Activate Send feedback in Settings, General first")
                return self.json(200, {"key": app.feedback_key(self.token())})
            if path.startswith("/api/ux-notes"):
                if not cfg.data.get("ux_notes"):
                    return self.error(404, "Activate Send feedback in Settings, General first")
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
            if path == "/api/services/sign-in" and method == "POST":
                # A download app's sign-in that Install apps made up (DASH-184): shown only after the Starboard
                # password, and only for qBittorrent and NZBGet, whose key is the user name and password.
                body = self.body()
                self.check_password(body)
                s = next((x for x in app.config.data["services"] if x.get("id") == body.get("id")), None)
                if s and s.get("type") == "qbittorrent" and stack.qbittorrent_password(app.data_dir):
                    user, password = "admin", stack.qbittorrent_password(app.data_dir)  # its key is an API key
                elif s and s.get("type") == "nzbget" and ":" in (s.get("api_key") or ""):
                    user, _, password = s["api_key"].partition(":")
                else:
                    return self.error(404, "Starboard has no sign-in for that app")
                logs.event("info", "security", f"Showed {s['name']}'s sign-in")
                return self.json(200, {"user": user, "password": password})
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
            if path == "/api/pictures" and method == "GET":  # Settings, Performance, Pictures (12 November 2026)
                from . import picture_cache
                return self.json(200, picture_cache.stats(cfg.data_dir))
            if path == "/api/pictures/clear" and method == "POST":
                from . import picture_cache
                gone = picture_cache.clear(cfg.data_dir)
                logs.event("info", "starboard", f"Picture cache cleared: {gone} pictures")
                return self.json(200, {"cleared": gone, **picture_cache.stats(cfg.data_dir)})
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
            if path == "/api/services/read-keys" and method == "POST":
                # The set-up's keys step: each missing key read from the app's own files (owner, 10 November 2026).
                # Starboard reads them itself with Docker access; without it (the safe default), the set-up helper on
                # the server reads them and hands them over (data/stack/keys-request, keys-found.json).
                reader = None if containers.available() else (
                    discovery.helper_reader(stack.folder(app.data_dir)) if stack.starter_waiting(app.data_dir) else (lambda key, name: None))
                out = discovery.read_missing_keys(cfg, reader)
                services.forget()
                if out["found"]:
                    logs.event("info", "settings", "Keys read for " + ", ".join(out["found"]))
                return self.json(200, {**out, "config": cfg.public()})
            m = re.match(r"^/api/services/([a-z0-9-]+)(/options|/restart)?$", path)
            if m:
                service = cfg.service(m.group(1))
                if not service:
                    return self.error(404, "That app is not in your list")
                if m.group(2) and method == "GET":
                    return self.json(200, services.options(service))
                if m.group(2) == "/restart" and method == "POST":  # Manage apps, Restart (owner, 12 November 2026)
                    return self.json(200, {"said": restart_app(service)})
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
            if path == "/api/issues" or path.startswith("/api/issues/"):
                from . import issues  # DASH-208: issues people report, from Reelix
                try:
                    if path == "/api/issues" and method == "GET":
                        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                        return self.json(200, issues.listing(cfg.data["services"], (q.get("status") or ["open"])[0]))
                    m = re.match(r"^/api/issues/(\d{1,10})(?:/(comment|resolve|reopen))?$", path)
                    if m and method == "GET" and not m.group(2):
                        return self.json(200, issues.one(cfg.data["services"], m.group(1)))
                    if m and method == "POST" and m.group(2):
                        out = issues.act(cfg.data["services"], m.group(1), m.group(2), self.body().get("message", ""))
                        logs.event("info", "issues", f"{m.group(2)} on an issue about {out['title']}")
                        return self.json(200, out)
                except ValueError as e:
                    return self.error(400, str(e))
                except services.ServiceError as e:
                    return self.error(502, f"Reelix said no: {e}")
                return self.error(404, "Not found")
            if path == "/api/reelix-history/keep" and method == "PUT":  # History, how much to keep (12 November 2026)
                from . import activity
                days = int(self.body().get("days") or 0)
                if days not in activity.KEEP_CHOICES:
                    return self.error(400, "Choose how long to keep history from the list")
                cfg.data["history_keep_days"] = days
                cfg.save()
                return self.json(200, {"keep_days": days})
            if path == "/api/reelix-history/delete" and method == "POST":  # Delete history
                import datetime as _dt
                from . import activity
                now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                said = activity.delete_history(cfg.data["services"], cfg.data, now)
                cfg.save()
                logs.event("info", "history", said)
                return self.json(200, {"said": said})
            if path in ("/api/reelix-history", "/api/reelix-history/refused", "/api/reelix-history/refused/take-off"):
                from . import activity  # DASH-159: History and the refused list, from Reelix
                try:
                    q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                    page = int((q.get("page") or ["1"])[0] or 1)
                    if path == "/api/reelix-history" and method == "GET":
                        return self.json(200, activity.history(cfg.data["services"], (q.get("which") or ["all"])[0], page, cfg.data))
                    if path == "/api/reelix-history/refused" and method == "GET":
                        return self.json(200, activity.refused(cfg.data["services"], page))
                    if method == "POST":
                        said = activity.take_off(cfg.data["services"], int(self.body().get("id") or 0))
                        logs.event("info", "history", said)
                        return self.json(200, {"said": said})
                except ValueError as e:
                    return self.error(400, str(e))
                except services.ServiceError as e:
                    return self.error(502, f"Reelix said no: {e}")
            if path.startswith("/api/dispatcharr"):  # Settings, Apps, Dispatcharr (DASH-228)
                from . import dispatcharr
                try:
                    if path == "/api/dispatcharr" and method == "GET":
                        return self.json(200, dispatcharr.state(cfg, app.data_dir))
                    if path == "/api/dispatcharr/connect" and method == "POST":
                        body = self.body()
                        self.check_password(body)  # the Starboard password is Dispatcharr's admin password (DASH-234)
                        done = dispatcharr.connect(cfg, app.data_dir, str(body.get("password", "")))
                    elif path == "/api/dispatcharr" and method == "PUT":
                        out = dispatcharr.save(cfg, app.data_dir, self.body())
                        done = out["done"]
                    elif path == "/api/dispatcharr/channels" and method == "POST":
                        out = dispatcharr.make_channels(cfg, app.data_dir)
                        done = out["done"]
                    elif path == "/api/dispatcharr/jellyfin" and method == "POST":
                        dispatcharr._app(cfg)  # a key first: no Dispatcharr to add without one
                        done = [dispatcharr.connect_jellyfin(cfg, app.data_dir) or "Jellyfin has Dispatcharr's tuner and guide already"]
                    else:
                        return self.error(405, "Method not allowed")
                    for line in done:
                        logs.event("info", "dispatcharr", line)
                    services.forget()
                    return self.json(200, {"done": done, "state": dispatcharr.state(cfg, app.data_dir)})
                except PasswordProblem as e:
                    return self.error(e.status, e.message, reason="password")
                except ValueError as e:
                    return self.error(400, str(e))
                except dispatcharr.DispatcharrError as e:
                    return self.error(502, str(e))
            if path == "/api/tdarr" and method in ("GET", "PUT"):  # Settings, Apps, Tdarr (DASH-306)
                from . import tdarr
                try:
                    if method == "GET":
                        return self.json(200, tdarr.state(cfg))
                    out = tdarr.save(cfg, self.body())
                    for line in out["done"]:
                        logs.event("info", "tdarr", line)
                    return self.json(200, out)
                except ValueError as e:
                    return self.error(400, str(e))
                except services.ServiceError as e:
                    return self.error(502, str(e))
            if path == "/api/wanted/detail" and method == "GET":  # DASH-305: one wanted film or episode in full
                from . import wanted
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    return self.json(200, wanted.detail(cfg.data["services"], q.get("kind", [""])[0], int(q.get("id", ["0"])[0] or 0),
                                                        q.get("series", [""])[0]))
                except ValueError as e:
                    return self.error(400, str(e))
                except services.ServiceError as e:
                    return self.error(502, str(e))
            if path in ("/api/wanted", "/api/wanted/search"):
                from . import wanted  # DASH-207: Missing and Below the quality wanted, from Reelix
                try:
                    if method == "GET":
                        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                        return self.json(200, wanted.listing(cfg.data["services"], q.get("which", ["missing"])[0],
                                                             q.get("kind", ["movie"])[0], int(q.get("page", ["1"])[0] or 1)))
                    if method == "POST":
                        b = self.body()
                        said = wanted.search(cfg.data["services"], str(b.get("which", "")), str(b.get("kind", "")), b.get("ids"))
                        logs.event("info", "wanted", said)
                        return self.json(200, {"said": said})
                except ValueError as e:
                    return self.error(400, str(e))
                except services.ServiceError as e:
                    return self.error(502, f"Reelix said no: {e}")
            if path == "/api/queue" and method == "GET":
                return self.json(200, services.cached("queue", 10, lambda: services.queue(cfg.data["services"]), fresh))
            if path == "/api/queue/action" and method == "POST":
                data = self.body()
                service = cfg.service(str(data.get("service", "")))
                radio = next((r for r in services.reelix_native(cfg.data["services"]) if service and r["id"] == service["id"]), None)
                if not service or (service["type"] not in ("sonarr", "radarr", "lidarr", "readarr") and not radio) \
                        or not str(data.get("id", "")).isdigit():
                    return self.error(400, "Choose a download in Reelix, Sonarr, Radarr, Lidarr or Readarr")
                if radio:  # the Reelix link entry: a radio download, through Reelix's own queue
                    services.radio_queue_action(radio, int(data["id"]), str(data.get("action", "")))
                else:
                    services.queue_action(service, int(data["id"]), str(data.get("action", "")), cfg.data["services"])
                logs.event("info", "downloads", f"{data.get('action')} for a download in {service['name']}")
                return self.json(200, {"ok": True})
            if path in ("/api/containers", "/api/containers/check", "/api/containers/update"):
                if not containers.available():
                    return self.json(200, {"available": False, "items": [], "containers": []})
                ordered = cfg.data["services"]
                if path == "/api/containers" and method == "GET":
                    return self.json(200, self.with_changes(containers.apps(ordered)))
                if path == "/api/containers/check" and method == "POST":
                    return self.json(200, self.with_changes(containers.check(ordered)))
                if path == "/api/containers/update" and method == "POST":
                    ids = self.body().get("ids")
                    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                        return self.error(400, "Choose the apps to update")
                    return self.json(200, self.with_changes(containers.update(ordered, ids)))
            # What is new in an app, from its own changelog (Reelix): before an update and after one.
            if path == "/api/app-changes/notices" and method == "GET":
                return self.json(200, {"notices": changes.notices(cfg.data_dir)})
            if path == "/api/app-changes/seen" and method == "POST":
                changes.seen(cfg.data_dir, str(self.body().get("app", "")))
                return self.json(200, {"ok": True})
            if path == "/api/app-changes" and method == "GET":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                wanted = q.get("app", [""])[0]
                notice = next((n for n in changes.notices(cfg.data_dir) if n["app"] == wanted), None)
                image = notice and notice["image"]
                if not image:
                    service = cfg.service(wanted)
                    found = service and containers.available() and containers.match(service, containers.containers())
                    image = found and found["image"]
                if not image:
                    return self.error(404, "Starboard cannot find this app's container")
                try:
                    return self.json(200, changes.between(image, q.get("from", [""])[0], q.get("to", [""])[0]))
                except ValueError as e:
                    return self.error(400, str(e))
                except OSError:
                    return self.error(502, "Starboard could not download the changelog. Try again later")
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
            if path == "/api/setup/start" and method == "GET":
                # How to start, for both set-ups: the same answers and help, recommended from what is here.
                return self.json(200, how_to_start.options(cfg.data["services"], app.data_dir))
            if path == "/api/setup/place" and method == "GET":
                # Where you are and Your keyboard, for both set-ups: the same lists, recommended from the last answer,
                # what the Run first script chose, then this computer's own (DASH-259).
                found = places.computer_from_env()
                handover, saved = how_to_start.handover(app.data_dir), places.saved(app.data_dir)
                # Left out of both set-ups when the Run first script asked both just before (WIZARD.md: ask nothing
                # the app can find out); asked again on a later run, with the saved answer recommended.
                answered = not saved and handover.get("tz") and handover.get("keyboard") in places.KEYBOARD_IDS
                return self.json(200, {**places.options(found, saved or handover), "answered": bool(answered)})
            if path == "/api/setup/place" and method == "POST":
                choice = places.save(app.data_dir, self.body())
                return self.json(200, {**choice, "change": places.change(choice, places.computer_from_env())})
            if path == "/api/setup/storage" and method == "GET":
                # Storage, for both set-ups: the main disk, a separate disk or a pool, with the folder for each.
                base = self.stack_overview()["defaults"]["data_dir"]
                return self.json(200, how_to_start.storage(base, sysinfo.pool_candidates(app.data_dir), pool.status().get("set_up")))
            if path == "/api/setup/host" and method in ("GET", "POST"):
                # The set-up's changes to this computer (free space for the media folder, the Live TV folder, disk
                # health): saved for ./install.sh, which the Run first script runs, or the person runs once.
                target = os.path.join(app.data_dir, "setup-host.json")
                if method == "POST":
                    args = how_to_start.host_args(self.body())
                    with open(target, "w", encoding="utf-8") as f:
                        json.dump({"args": args}, f)
                    return self.json(200, {"args": args, "command": "./install.sh " + " ".join(args) if args else "",
                                           "starter": stack.starter_waiting(app.data_dir)})
                try:
                    with open(target, encoding="utf-8") as f:
                        args = json.load(f).get("args", [])
                except (OSError, ValueError):
                    args = []
                return self.json(200, {"args": args, "command": "./install.sh " + " ".join(args) if args else "",
                                       "starter": stack.starter_waiting(app.data_dir)})
            if path == "/api/setup/host/apply" and method == "POST":
                # Make the change now (owner, 10 November 2026): the Run first window on the server makes the set-up's
                # change to the computer when Starboard leaves a request, after the Starboard password here.
                self.check_password(self.body())
                if not stack.starter_waiting(app.data_dir):
                    raise ValueError("The Run first window on the server is closed, so run the command there instead")
                if not os.path.exists(os.path.join(app.data_dir, "setup-host.json")):
                    raise ValueError("There is no change to make")
                folder = stack.folder(app.data_dir)
                os.makedirs(folder, exist_ok=True)
                for name in ("host-progress.json", "host.log"):
                    try:
                        os.remove(os.path.join(folder, name))
                    except OSError:
                        pass
                with open(os.path.join(folder, "host-request"), "w", encoding="utf-8") as f:
                    f.write(f"{time.time():.3f}\n")
                logs.event("info", "settings", "Asked the Run first window to make the set-up's change to the server")
                return self.json(200, {"state": "waiting"})
            if path == "/api/setup/host/progress" and method == "GET":
                folder = stack.folder(app.data_dir)
                try:
                    with open(os.path.join(folder, "host-progress.json"), encoding="utf-8") as f:
                        progress = json.load(f)
                except (OSError, ValueError):
                    progress = {"state": "waiting" if os.path.exists(os.path.join(folder, "host-request")) else "idle"}
                try:
                    with open(os.path.join(folder, "host.log"), encoding="utf-8", errors="replace") as f:
                        log = f.read()[-8000:]
                except OSError:
                    log = ""
                return self.json(200, {**{k: progress.get(k) for k in ("state", "n", "of", "name")}, "log": log,
                                       "window": stack.starter_waiting(app.data_dir)})
            if path == "/api/discover" and method == "GET":
                return self.json(200, discovery.search(cfg.data["services"]))
            if path == "/api/discover/add" and method == "POST":
                return self.json(200, self.add_found(self.body().get("items")))
            if path == "/api/stack" and method == "GET":
                return self.json(200, self.stack_overview())
            if path == "/api/stack/install" and method == "POST":
                # Basics, Full install or Everything: the apps (with what they need), groups and answers, for both set-ups.
                overview = self.stack_overview()
                # Apps of Starboard's own install stay in the choice even while running (VM test F4): left out, the
                # compose file written next would drop them, and starting it (--remove-orphans) would stop them.
                own = set(stack.chosen_keys(app.data_dir) or [])
                installed = {a["key"] for a in overview["apps"] if a["installed"]} - own
                body = self.body()
                return self.json(200, stack.install_choice(str(body.get("install", "")), installed,
                                                           usenet=str(body.get("usenet") or "nzbget")))
            if path == "/api/install" and method == "GET":
                # Settings, Your install: what runs now, and the three installs with what each adds or takes away.
                now = stack.current_choice(app.data_dir)
                names = {k: a["name"] for k, a in stack.APPS.items()}
                out = {"written": bool(now), "installs": [], "usenet_apps": [{"key": k, "name": names[k]} for k in stack.USENET_APPS],
                       "editions": stack.reelix_editions(), "can_start": bool(stack.host_folder(app.data_dir) and containers.available()),
                       "starter": stack.starter_waiting(app.data_dir), "command": "cd ~/starboard && ./install.sh --start-apps"}
                outside = self.outside_apps() if now else []
                out["outside"] = [names[k] for k in outside]  # DASH-250: running from the person's own Compose file
                if now:
                    usenet = next((k for k in stack.USENET_APPS if k in now["apps"]), None)
                    current = stack.which_install(now["apps"], now["reelix_edition"])
                    out["current"] = {"install": current, "apps": [names.get(k, k) for k in now["apps"]],
                                      "reelix_edition": now["reelix_edition"] if "reelix" in now["apps"] else None,
                                      "usenet": usenet, "memory": sum(stack.APPS[k].get("memory", 100) for k in now["apps"])}
                    for key, spec in stack.INSTALLS.items():
                        try:
                            plan = stack.plan_change(app.data_dir, install=key, usenet=usenet, outside=outside)
                        except ValueError as e:
                            out["installs"].append({"key": key, "name": spec["name"], "about": spec["about"], "error": str(e)})
                            continue
                        out["installs"].append({"key": key, "name": spec["name"], "about": spec["about"],
                                                "add": [names[k] for k in plan["add"]], "remove": [names[k] for k in plan["remove"]],
                                                "outside": [names[k] for k in plan["outside"]],
                                                "reelix_edition": plan["choice"]["reelix_edition"],
                                                "memory": sum(stack.APPS[k].get("memory", 100) for k in plan["choice"]["apps"])})
                try:
                    with open(os.path.join(stack.folder(app.data_dir), "change-result.json"), encoding="utf-8") as f:
                        out["last_change"] = json.load(f)
                except (OSError, ValueError):
                    pass
                return self.json(200, out)
            if path == "/api/downloads/settings" and method == "GET":
                # DASH-226: Settings, Downloads. The VPN without its key or password, and the Usenet servers by address.
                choice = stack.current_choice(app.data_dir) or {}
                vpn = choice.get("vpn") or {}
                keys = set(choice.get("apps") or [])
                usenet = "nzbget" if "nzbget" in keys else "sabnzbd" if "sabnzbd" in keys else ""
                servers = []
                try:
                    if usenet == "nzbget" and stack.nzbget_key(app.data_dir):
                        rpc = reelix_setup.nzbget_rpc(stack.nzbget_key(app.data_dir), base=stack.app_url(app.data_dir, "nzbget", 6789) or "http://127.0.0.1:6789",
                                                      wait=0, timeout=5)
                        servers = [o["Value"] for o in rpc("config") or [] if re.match(r"^Server\d+\.Host$", o.get("Name", "")) and o.get("Value")]
                except (reelix_setup.ReelixError, OSError, ValueError):
                    servers = []
                return self.json(200, {"vpn": {"on": "gluetun" in keys, "provider": vpn.get("provider", ""), "type": vpn.get("type", "wireguard"),
                                               "countries": vpn.get("countries", ""), "has_secret": bool(vpn.get("wireguard_private_key") or vpn.get("openvpn_password"))},
                                       "usenet": {"app": {"nzbget": "NZBGet", "sabnzbd": "SABnzbd"}.get(usenet, ""), "servers": servers},
                                       "docker": containers.available()})
            if path == "/api/downloads/usenet" and method == "POST":
                from . import setup_answers
                body = self.body()
                setup_answers.save_usenet(app.data_dir, setup_answers.clean_usenet(body.get("server")))
                done = setup_answers.apply_usenet(app.data_dir)
                logs.event("info", "downloads", "; ".join(done) or "Usenet server saved")
                return self.json(200, {"said": "; ".join(done) or "Saved. Starboard adds it to the Usenet app when it runs"})
            if path == "/api/noip" and method == "GET":
                from . import noip  # the No-IP updater (DASH-170)
                return self.json(200, noip.status(app.data_dir))
            if path == "/api/noip" and method == "POST":
                # A new DDNS key or password, into data/stack/noip.env; then the updater starts again with it.
                from . import noip
                body = self.body()
                self.check_password(body)
                noip.save(app.data_dir, body.get("username"), body.get("ddns_password"), body.get("hostnames"))
                logs.event("info", "network", "No-IP sign-in changed")
                try:
                    return self.json(200, {"started": self.start_stack(), "said": "Saved. The No-IP updater is starting again with it"})
                except ValueError:
                    return self.json(200, {"started": None, "command": "cd ~/starboard && ./install.sh --start-apps",
                                           "said": "Saved. Run the command on the server to start the updater with it"})
            if path == "/api/downloads/vpn" and method == "POST":
                # New VPN details: written into the set-up files, then Gluetun is started again with them. A key or
                # password left empty keeps the one there is.
                body = self.body()
                self.check_password(body)
                choice = stack.current_choice(app.data_dir)
                if not choice or "gluetun" not in (choice.get("apps") or []):
                    raise ValueError("Your install has no VPN. Add one in Settings, Your install")
                old = choice.get("vpn") or {}
                typed = {k: str(v).strip() for k, v in (body.get("vpn") or {}).items() if k in stack.VPN_ENV.values()}
                new = {**old, **{k: v for k, v in typed.items() if v or k in ("countries",)}}
                choice = {**choice, "vpn": new, "own_ports": stack.compose_ports(app.data_dir)}
                built = stack.build(choice)
                own = stack.own_services(app.data_dir)
                if own:
                    built = {**built, "compose": built["compose"].rstrip() + "\n" + "".join(own)}
                stack.write(app.data_dir, built)
                logs.event("info", "downloads", f"VPN details changed ({new.get('provider', '')})")
                try:
                    return self.json(200, {"started": self.start_stack(), "said": "Saved. Gluetun is starting again with the new details"})
                except ValueError:
                    return self.json(200, {"started": None, "command": "cd ~/starboard && ./install.sh --start-apps",
                                           "said": "Saved. Run the command on the server to start Gluetun with them"})
            if path == "/api/install/change" and method == "POST":
                # Change to another install, Usenet app or Reelix: rewrite the set-up file and start the apps.
                body = self.body()
                self.check_password(body)
                plan = stack.plan_change(app.data_dir, install=body.get("install") or None,
                                         usenet=body.get("usenet") or None, edition=body.get("reelix_edition") or None,
                                         outside=self.outside_apps())
                if not (plan["add"] or plan["remove"] or (plan["reelix"] and plan["reelix"][0] != plan["reelix"][1])):
                    raise ValueError("That is what runs already")
                job = stack.job()
                if job and not job.get("finished"):
                    raise ValueError("The apps are already starting. Wait until they finish, then change your install")
                sab_ini = usenet_move.read_sab_ini() if plan["usenet"][0] == "sabnzbd" and plan["usenet"][1] == "nzbget" else None
                built = stack.build(plan["choice"])
                if plan["own"]:  # apps added by hand stay in the file, so they are not removed
                    built = {**built, "compose": built["compose"].rstrip() + "\n" + "".join(plan["own"])}
                stack.write(app.data_dir, built)
                logs.event("info", "your install", f"Changing: adding {', '.join(plan['add']) or 'nothing'}; "
                                                   f"taking away {', '.join(plan['remove']) or 'nothing'}")
                try:
                    started = self.start_stack()
                except ValueError:
                    # No Docker access and no Run first window: the person runs the command, and the installer marks
                    # data/stack/started-at when the apps are up. The follow-up waits for that (for an hour at most).
                    moving = plan["usenet"][0] == "sabnzbd" and plan["usenet"][1] == "nzbget" and not sab_ini
                    if moving:  # the installer copies SABnzbd's settings for the server move
                        open(os.path.join(stack.folder(app.data_dir), "want-sab-servers"), "w").close()
                    after_install_change(app, body.get("password", ""), plan, sab_ini, by_installer=time.time(),
                                         sab_from_installer=moving)
                    return self.json(200, {"started": None, "command": "cd ~/starboard && ./install.sh --start-apps",
                                           "add": plan["add"], "remove": plan["remove"]})
                after_install_change(app, body.get("password", ""), plan, sab_ini)
                return self.json(200, {"started": started, "add": plan["add"], "remove": plan["remove"],
                                       "sab_servers": len(usenet_move.parse_sab_servers(sab_ini)) if sab_ini else 0})
            if path == "/api/setup/left" and method == "GET":
                # DASH-185: what is left to set up
                return self.json(200, setup_left.left(app.config, app.data_dir))
            if path == "/api/setup/left/ignore" and method == "POST":
                # Ignore, or bring back, in the set-up wizard (DASH-289)
                body = self.body()
                try:
                    setup_left.ignore(app.data_dir, str(body.get("key", "")), body.get("ignore", True) is not False)
                except ValueError as e:
                    return self.json(400, {"error": str(e)})
                return self.json(200, setup_left.left(app.config, app.data_dir))
            if path == "/api/setup/left/done" and method == "POST":
                # Done on a guided step (DASH-230, DASH-231)
                body = self.body()
                try:
                    setup_left.mark_done(app.data_dir, str(body.get("key", "")))
                except ValueError as e:
                    return self.json(400, {"error": str(e)})
                return self.json(200, setup_left.left(app.config, app.data_dir))
            if path == "/api/stack/existing-usenet" and method == "GET":
                # DASH-247: the servers of a SABnzbd already running, by address only, for the Usenet step to name.
                running = next((c["name"] for c in takeover.found() if c["key"] == "sabnzbd" and c["running"]), None) \
                    if containers.available() else None
                ini = usenet_move.read_sab_ini(running) if running else None
                hosts = [s.get("host") for s in usenet_move.parse_sab_servers(ini or "") if s.get("host")]
                return self.json(200, {"app": "SABnzbd" if hosts else None, "hosts": hosts})
            if path == "/api/stack/existing-vpn" and method == "GET":
                return self.json(200, {"vpn": takeover.existing_vpn()})  # DASH-132: never the key or password
            if path == "/api/stack/preview" and method == "POST":
                preview = takeover.fill_vpn({k: v for k, v in self.body().items() if k != "own_ports"})
                built = stack.build({**preview, "own_ports": stack.compose_ports(app.data_dir)})
                return self.json(200, {**{k: built[k] for k in ("compose", "env_shown", "folders", "moved", "later")}, "hooks": sorted(built["hooks"])})
            if path == "/api/setup/nordvpn-key" and method == "POST":
                # DASH-233: the key goes back to the set-up's key field, as if typed; Starboard keeps nothing here.
                from . import setup_answers
                try:
                    key, address = setup_answers.nordvpn_key(self.body().get("token"))
                    return self.json(200, {"ok": True, "key": key, "address": address,
                                           "message": "NordVPN sent your WireGuard key. It is in the key field."})
                except ValueError as e:
                    return self.json(200, {"ok": False, "message": str(e)})
            if path in ("/api/setup/test-tmdb", "/api/setup/test-usenet") and method == "POST":
                # The set-up's Test buttons (DASH-178, DASH-183): nothing is kept.
                from . import setup_answers
                body = self.body()
                try:
                    if path.endswith("tmdb"):
                        setup_answers.test_tmdb(body.get("key"))
                        return self.json(200, {"ok": True, "message": setup_answers.WORDS["tmdb"]["ok"]})
                    setup_answers.test_usenet(body.get("server"))
                    return self.json(200, {"ok": True, "message": setup_answers.WORDS["usenet"]["ok"]})
                except ValueError as e:
                    return self.json(200, {"ok": False, "message": str(e)})
            if path == "/api/stack/write" and method == "POST":
                choice = self.body()
                # Writing decides which apps the next start keeps (it removes the rest), so the password again.
                self.check_password(choice)
                choice = takeover.fill_vpn({k: v for k, v in choice.items() if k not in ("password", "own_ports")})
                choice["own_ports"] = stack.compose_ports(app.data_dir)  # running Install apps again keeps the ports
                from . import setup_answers
                try:  # the new answers are checked before anything is written (DASH-178, DASH-183, DASH-189)
                    setup_answers.clean_tmdb(choice.get("tmdb"))
                    setup_answers.clean_language(choice.get("language", "English"))
                    setup_answers.clean_usenet(choice.get("usenet_server"))
                except ValueError as e:
                    return self.error(400, str(e))
                if "graphics" not in choice:  # Jellyfin uses the graphics chip when this computer has one (DASH-82)
                    choice = {**choice, "graphics": stack.graphics_chip()}
                built = stack.build(choice)
                own = stack.own_services(app.data_dir)  # apps added by hand stay, so starting does not remove them
                if own:
                    built = {**built, "compose": built["compose"].rstrip() + "\n" + "".join(own)}
                stack.write(app.data_dir, built)
                stack.note_reelix(app.data_dir, choice, built)  # what the Reelix set-up needs once the apps run
                setup_answers.save_usenet(app.data_dir, choice.get("usenet_server"))  # written into the Usenet app once it runs
                host = stack.host_folder(app.data_dir)
                return self.json(200, {"host_folder": host, "can_start": bool(host and containers.available()),
                                       "starter": stack.starter_waiting(app.data_dir),
                                       "command": "cd ~/starboard && ./install.sh --start-apps",
                                       "moved": built["moved"], "later": built["later"]})
            if path == "/api/stack/start" and method == "POST":
                start_body = self.body()
                self.check_password(start_body)  # starting containers changes the computer: the password again
                started = self.start_stack()
                adopt_started_apps(app, stack.chosen_keys(app.data_dir))
                reelix_after_start(app, start_body.get("password", ""))
                return self.json(200, started)
            if path == "/api/reelix/editions" and method == "GET":
                # Reelix or Reelix with YouTube and Spotify downloads: for both set-ups and Settings, Reelix.
                image = stack.reelix_in_stack(app.data_dir)
                return self.json(200, {"editions": stack.reelix_editions(), "image": image,
                                       "needs_setup": bool(reelix_setup.read_setup(app.data_dir)),
                                       "current": stack.edition_of(image), "can_switch": bool(image),
                                       "can_start": bool(stack.host_folder(app.data_dir) and containers.available()),
                                       "starter": stack.starter_waiting(app.data_dir),
                                       "command": "cd ~/starboard && ./install.sh --start-apps"})
            if path == "/api/reelix/edition" and method == "POST":
                # Switch Reelix between the two versions, either way: a new image, the same settings folder.
                body = self.body()
                self.check_password(body)
                old, new = stack.switch_reelix(app.data_dir, str(body.get("edition", "")))
                logs.event("info", "reelix", f"Reelix changed from {old} to {new}")
                try:
                    started = self.start_stack()
                except ValueError:
                    return self.json(200, {"image": new, "started": None, "command": "cd ~/starboard && ./install.sh --start-apps"})
                return self.json(200, {"image": new, "started": started})
            if path == "/api/reelix/setup" and method == "POST":
                # The terminal set-up, after the installer started the apps: Reelix's admin account with Starboard's
                # password (used for these calls only), a manager key for Starboard, folders, qBittorrent, the dashboard.
                body = self.body()
                self.check_password(body)
                done = reelix_setup.set_up(app.config, app.data_dir, body["password"],
                                           qbit=reelix_setup.qbit_lasting_password(), nzbget=reelix_setup.nzbget_ready())
                services.forget()
                logs.event("info", "install apps", "Reelix set up: " + "; ".join(done))
                return self.json(200, {"done": done})
            if path == "/api/stack/adopt" and method == "POST":
                # The terminal set-up started the apps through the installer: Starboard adds them as they answer.
                adopt_started_apps(app, stack.chosen_keys(app.data_dir), after_job=False)
                return self.json(200, {"keys": (stack.adopting(app.data_dir) or ([], 0))[0]})
            if path == "/api/stack/starting" and method == "GET":
                # The apps page calls an app that does not answer "still starting", not "not responding", for a while
                # after the apps start: on a small server some take minutes to answer the first time.
                since = stack.seconds_since_start(app.data_dir)
                return self.json(200, {"starting": since is not None and since < stack.STARTING_FOR})
            if path == "/api/stack/job" and method == "GET":
                return self.json(200, stack.job(app.data_dir))
            # Taking over apps someone runs from their own Compose file (Settings, Your install; takeover.py)
            if path == "/api/takeover" and method == "GET":
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                route = requests_route.read(app.data_dir)
                out = {"record": takeover.read_record(app.data_dir), "job": takeover.job(),
                       "moved": reelix_move.moved(app.data_dir), "docker": containers.available(),
                       "can_start": bool(stack.host_folder(app.data_dir) and containers.available()),
                       "defaults": self.takeover_defaults(), "requests": self.requests_offer(route),
                       "waiting": reelix_waiting.read(app.data_dir)[:200], "waiting_count": len(reelix_waiting.read(app.data_dir))}
                try:
                    out["leftovers"] = takeover.leftovers(app.data_dir)
                except (ValueError, containers.DockerError):
                    out["leftovers"] = None
                out["cleared"] = takeover.cleared(app.data_dir)[-20:]
                try:
                    p = takeover.plan(app.data_dir, q.get("install", ["full"])[0], q.get("usenet", ["nzbget"])[0],
                                      config_dir=q.get("config_dir", [out["defaults"]["config_dir"]])[0],
                                      media_dir=q.get("media_dir", [out["defaults"]["data_dir"]])[0],
                                      keep_apps=("seerr",) if (route or {}).get("choice") == "seerr" else ())
                    out["plan"] = takeover.summary(p)
                    out["plan"]["unmoved"] = [r["name"] for r in p["replace"] if r["by"] == "Reelix" and r["name"] not in out["moved"]
                                              and r["key"] in MOVED_BY_REELIX]  # Profilarr and the like have nothing to move
                    out["plan"]["unmoved_apps"] = [r["app"] for r in p["replace"] if r["name"] in out["plan"]["unmoved"]]
                except (ValueError, containers.DockerError) as e:
                    out["error"] = str(e)
                return self.json(200, out)
            if path == "/api/takeover/start" and method == "POST":
                body = self.body()
                self.check_password(body)
                host = stack.host_folder(app.data_dir)
                if not host or not containers.available():
                    raise ValueError("Starboard needs Docker access to take over your apps")
                if stack.job().get("started") and not stack.job().get("finished"):
                    raise ValueError("The apps are already starting. Wait until they finish")
                route = requests_route.read(app.data_dir)
                p = takeover.plan(app.data_dir, str(body.get("install") or "full"), str(body.get("usenet") or "nzbget"),
                                  config_dir=body.get("config_dir"), media_dir=body.get("media_dir"),
                                  keep_apps=("seerr",) if (route or {}).get("choice") == "seerr" else ())
                unmoved = [r["app"] for r in p["replace"] if r["by"] == "Reelix" and r["name"] not in reelix_move.moved(app.data_dir)
                           and r["key"] in MOVED_BY_REELIX]
                if unmoved and not body.get("unmoved_ok"):
                    raise ValueError("Move " + ", ".join(unmoved) + " into Reelix first (Settings, Reelix, Move your apps "
                                     "into Reelix), or tick that you do not need them moved")
                app.config.update_general({"setup_guide_done": True})  # a takeover counts as set up (DASH-238)
                # SABnzbd's settings: its servers for NZBGet, or its key for Reelix when SABnzbd stays (DASH-128).
                kept_sab = next((c["name"] for c in p["take"] if c["key"] == "sabnzbd"), None)
                sab_ini = usenet_move.read_sab_ini() if p["sab"] else usenet_move.read_sab_ini(kept_sab) if kept_sab else None
                logs.event("info", "take over", "Taking over " + ", ".join(t["name"] for t in p["take"]) +
                           "; stopping " + (", ".join(r["name"] for r in p["replace"]) or "nothing"))
                return self.json(200, takeover.start(app.data_dir, host, p, after_takeover(app, body.get("password", ""), p, sab_ini)))
            if path == "/api/takeover/rollback" and method == "POST":
                body = self.body()
                self.check_password(body)
                host = stack.host_folder(app.data_dir)
                if not host or not containers.available():
                    raise ValueError("Starboard needs Docker access to roll back")
                logs.event("info", "take over", "Rolling back: the old apps start again from their own Compose files")
                def after(ok):
                    services.forget()
                    return ["Your old apps run again as they were before the takeover"] if ok else \
                        ["Rolling back did not finish. See the log below, and the help topic Take over the apps you already run"]
                return self.json(200, takeover.roll_back(app.data_dir, host, after))
            if path == "/api/takeover/clear" and method == "POST":
                body = self.body()
                self.check_password(body)
                takeover.clear(app.data_dir)
                logs.event("info", "take over", "Kept the takeover: the rollback point was moved aside")
                return self.json(200, {"cleared": True})
            if path == "/api/takeover/job" and method == "GET":
                return self.json(200, takeover.job())
            if path == "/api/takeover/clear-away" and method == "POST":
                # DASH-191: once the takeover is kept, stop and remove the apps Reelix replaced, their settings
                # folders into the holding folder (never deleted here), and their entries off the dashboard.
                body = self.body()
                self.check_password(body)
                host = stack.host_folder(app.data_dir)
                if not host or not containers.available():
                    raise ValueError("Starboard needs Docker access to clear away your old apps")
                names = [str(n) for n in body.get("names") or []][:30]

                def after(ok, items, tasks):
                    tasks.start("dashboard", now="Updating your dashboard")
                    gone = [it for i, it in enumerate(items) if tasks.state(f"app-{i}") != "failed"]
                    keys = {it["name"]: takeover.catalogue_key(it["name"]) or it["name"] for it in gone}
                    notes = remove_entries(app, [(keys[it["name"]], it["name"], it["app"]) for it in gone])
                    services.forget()
                    tasks.done("dashboard")
                    notes = [f"Cleared away {', '.join(it['app'] for it in gone)}"] + notes if gone else notes
                    logs.event("info", "take over", "; ".join(notes) or "Cleared away nothing")
                    return notes
                logs.event("info", "take over", "Clearing away " + ", ".join(names))
                return self.json(200, takeover.clear_away(app.data_dir, host, names, after))
            if path == "/api/requests-route" and method == "POST":
                # DASH-192: keep Seerr beside Reelix, or use Reelix's own requests.
                body = self.body()
                choice = str(body.get("choice") or "")
                if choice not in requests_route.CHOICES:
                    raise ValueError("Choose Reelix's own requests or Keep Seerr")
                applied, notes = requests_route.apply(app.config, app.data_dir, choice)
                requests_route.save(app.data_dir, choice, applied, notes)
                services.forget()
                logs.event("info", "requests", f"Requests: {'Reelix' if choice == 'reelix' else 'Seerr'}. " + "; ".join(notes))
                return self.json(200, self.requests_offer(requests_route.read(app.data_dir)))
            if path == "/api/reelix/waiting" and method == "GET":
                items = reelix_waiting.read(app.data_dir)
                return self.json(200, {"items": items[:200], "count": len(items)})
            if path == "/api/reelix/waiting/retry" and method == "POST":
                # DASH-253: Try again now (the background retry also runs every six hours and when a TMDB key is added).
                reelix = library.reelix_of(app.config.data["services"])
                if not reelix:
                    raise ValueError("Reelix is not on your apps with its API key yet")
                done = reelix_waiting.try_again(app.data_dir, reelix)
                items = reelix_waiting.read(app.data_dir)
                return self.json(200, {**done, "items": items[:200], "count": len(items)})
            if path == "/api/reelix/waiting/forget" and method == "POST":
                reelix_waiting.forget(app.data_dir, str(self.body().get("key") or ""))
                items = reelix_waiting.read(app.data_dir)
                return self.json(200, {"items": items[:200], "count": len(items)})
            # Moving the old apps into Reelix (Settings, Reelix; reelix_move.py)
            if path == "/api/reelix/move" and method == "GET":
                out = {"job": reelix_move.job(), "last": reelix_move.last_result(app.data_dir),
                       "needs_setup": bool(reelix_setup.read_setup(app.data_dir))}
                try:
                    out["sources"] = [reelix_move.public(s) for s in reelix_move.sources()]
                    conf = reelix_move.qbit_conf()  # DASH-251: the user name qBittorrent's own settings file gives
                    out["qbittorrent_user"] = conf["user"]
                    out["qbittorrent"] = conf
                except (ValueError, containers.DockerError) as e:
                    out["error"] = str(e)
                out["review"] = self.move_review(out["last"])
                return self.json(200, out)
            if path == "/api/reelix/move/preview" and method == "POST":
                body = self.body()
                self.check_password(body)
                typed = typed_secrets(body.get("secrets"))
                return self.json(200, {"apps": reelix_move.preview(stack.reelix_url(app.data_dir), body["password"],
                                                                    reelix_move.sources(), typed)})
            if path == "/api/reelix/move/run" and method == "POST":
                body = self.body()
                self.check_password(body)
                typed = typed_secrets(body.get("secrets"))
                qpw = str(body.get("qbittorrent_password") or "")
                conf = reelix_move.qbit_conf() if qpw else {"user": None, "ban_minutes": 60}
                quser = conf["user"] or "admin"
                if qpw:
                    state = reelix_move.qbit_sign_in(qpw, user=quser)
                    if state != "ok":  # DASH-251: said under the qBittorrent field, including a ban after wrong tries
                        return self.json(400, {"error": reelix_move.qbit_problem(state, quser, conf["ban_minutes"]),
                                               "field": "qbittorrent", "state": state})
                # DASH-129: through the VPN when qBittorrent runs on another container's network (Docker says), or,
                # when Docker cannot say, when Gluetun is chosen or runs here.
                through = reelix_move.qbit_through_vpn()
                vpn = "gluetun" in (stack.chosen_keys(app.data_dir) or []) or bool(through) or (through is None and any(
                    c["key"] == "gluetun" for c in takeover.found() if c["running"]))
                logs.event("info", "reelix", "Moving the old apps into Reelix")
                return self.json(200, reelix_move.start(app.data_dir, body["password"], typed, hold=bool(body.get("hold", True)),
                                                        qbit_password=qpw or None, qbit_host="gluetun" if vpn else "qbittorrent",
                                                        qbit_user_name=quser, lookup_urls=self.arr_addresses()))
            if path == "/api/reelix/move/job" and method == "GET":
                return self.json(200, reelix_move.job())
            if path == "/api/reelix/move/activate" and method == "POST":
                # DASH-190: activate the sites held after the move, one or all.
                body = self.body()
                self.check_password(body)
                ids = body.get("ids")
                changed = reelix_move.activate(app.data_dir, body["password"],
                                               None if ids is None else [int(i) for i in ids if str(i).isdigit()])
                logs.event("info", "reelix", f"Activated {changed} held {'site' if changed == 1 else 'sites'} to search")
                return self.json(200, {"changed": changed, "review": self.move_review(reelix_move.last_result(app.data_dir))})
            if path == "/api/reelix/indexers" and method == "POST":
                # The indexers held after the move: switched on when the old apps are no longer searching.
                body = self.body()
                self.check_password(body)
                admin = reelix_move._admin(stack.reelix_url(app.data_dir), body["password"])
                changed = reelix_move.set_indexers(admin, bool(body.get("on")))
                return self.json(200, {"changed": changed})
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
            if path == "/api/help" and method == "GET":
                # A help centre article for the help slide-out, as data (helpdocs.py).
                page = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("page", [""])[0]
                try:
                    return self.json(200, helpdocs.article(page))
                except helpdocs.HelpError as e:
                    return self.json(400 if not helpdocs.PAGE.match(page) else 502, {"error": str(e), "url": helpdocs.HELP_CENTRE})
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
            if path == "/api/downloads/now" and method == "POST":
                # DASH-171: one item downloads now, outside download hours; everything else stays paused.
                b = self.body()
                kind, item_id = str(b.get("kind", "")), str(b.get("id", ""))
                if kind not in ("movie", "episode") or not item_id.isdigit():
                    return self.error(400, "Choose a film or an episode")
                reelix = services.reelix_native(cfg.data["services"])
                if not reelix:
                    return self.error(400, "Add Reelix in Settings, Manage apps, with its key")
                try:
                    services._api(reelix[0], "/search", method="POST", body={"kind": kind, "ids": [int(item_id)]})
                except services.ServiceError as e:
                    return self.error(502, f"Reelix said no: {e}")
                title = str(b.get("title", ""))[:200]
                if cfg.data["download_hours"]["enabled"]:
                    app.schedule.allow({"kind": kind, "id": int(item_id), "title": title})
                logs.event("info", "download hours", f"Download now: {title or kind}")
                return self.json(200, {"said": f"Reelix is searching for {title or 'it'} now. It downloads as soon as it is found, outside your download hours"
                                       if cfg.data["download_hours"]["enabled"] else f"Reelix is searching for {title or 'it'} now"})
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
            if path == "/api/queue/episodes" and method in ("GET", "POST"):  # Choose the episode (12 November 2026)
                from . import episode_fix
                from .library import reelix_of  # not "library": that name is the module the whole handler uses
                reelix = reelix_of(cfg.data["services"])
                if not reelix:
                    return self.error(409, "Add Reelix in Settings, Manage apps first")
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                download_id = (qs.get("download_id") or [""])[0]
                try:
                    if method == "GET":
                        return self.json(200, episode_fix.options(reelix, download_id))
                    out = episode_fix.apply(reelix, download_id, self.body().get("choices"))
                    logs.event("info", "reelix", f"Chose the episode for {out['sent']} file(s) of download {download_id}")
                    return self.json(200, out)
                except LookupError as e:
                    return self.error(404, str(e))
                except ValueError as e:
                    return self.error(400, str(e))
                except services.ServiceError as e:
                    return self.error(502, f"Reelix did not answer: {e}")
            m = re.match(r"^/api/transfer/([A-Za-z0-9_-]{1,64})/resume-unpacking$", path)
            if m and method == "POST":  # DASH-304: unpacking and folder scanning on again; downloading is left alone
                s = cfg.service(m.group(1))
                if not s or s["type"] != "nzbget":
                    return self.error(404, "No NZBGet with that id")
                try:
                    services.nzbget(s, "resumepost")
                    services.nzbget(s, "resumescan")
                except services.ServiceError as e:
                    return self.error(502, str(e))
                services.forget("transfer")
                logs.event("info", "downloads", f"{s['name']}: unpacking and folder scanning resumed")
                return self.json(200, {"said": f"{s['name']} is unpacking again"})
            if path == "/api/transfer" and method == "GET":
                return self.json(200, services.cached("transfer", 5, lambda: services.transfer(cfg.data["services"]), fresh))
            if path == "/api/numbers" and method == "GET":
                return self.json(200, {"items": services.cached("numbers", 60, lambda: services.numbers(cfg.data["services"]), fresh)})
            if path == "/api/requests" and method == "GET":
                pending = "pending=1" in urllib.parse.urlparse(self.path).query
                return self.json(200, services.cached(f"requests-{pending}", 20, lambda: services.requests(cfg.data["services"], pending), fresh))
            m = re.match(r"^/api/requests/(\d{1,10})/(approve|decline|retry)$", path)
            if m and method == "POST":
                services.request_action(cfg.data["services"], m.group(1), m.group(2), str(self.body().get("reason") or ""))
                services.forget()
                return self.json(200, services.requests(cfg.data["services"]))
            if path == "/api/jobs" and method == "GET":
                from . import plugin_life  # plug-ins' jobs are listed with the server's (DASH-330)
                return self.json(200, {**backup.jobs_status(), "plugin_jobs": plugin_life.jobs(app.data_dir)})
            m = re.match(r"^/api/jobs/([a-z][a-z0-9-]{0,30})$", path)
            if m and method == "POST":
                from . import plugin_life
                backup.request_job(m.group(1))
                return self.json(200, {**backup.jobs_status(), "plugin_jobs": plugin_life.jobs(app.data_dir)})
            if path == "/api/recent" and method == "GET":
                return self.json(200, services.cached("recent", 300, lambda: services.recent(cfg.data["services"]), fresh))
            if path == "/api/jellyfin" and method == "GET":
                return self.json(200, services.cached("jellyfin", 20, lambda: services.jellyfin(cfg.data["services"]), fresh))
            if path == "/api/health" and method == "GET":
                return self.json(200, services.cached("health", 300, lambda: services.health(cfg.data["services"], stack.chosen_keys(app.data_dir), app.data_dir), fresh))
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
            if path == "/api/pool" and method == "GET":
                return self.json(200, pool.status())
            if path == "/api/pool/ask" and method == "POST":
                data = self.body()
                if data.get("action") == "drives":
                    return self.json(200, {"request": pool.ask("drives")})
                fields = pool.plan_request(data, cfg.data.get("download_hours"))
                return self.json(200, {"request": pool.ask("plan", **fields)})
            if path == "/api/pool/answer" and method == "GET":
                rid = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("id", [""])[0]
                found = pool.answer(rid)
                return self.json(200, found if found else {"waiting": True})
            if path == "/api/pool/apply" and method == "POST":
                data = self.body()
                self.check_password(data)  # every change to a drive needs the password again (TheMightyTRexUK, 5 Nov 2026)
                fields = pool.apply_request(data)
                logs.event("info", "pool", "Asked the pool helper to carry out a checked plan")
                return self.json(200, {"request": pool.ask("apply", **fields)})
            if path == "/api/pool/stop" and method == "POST":
                return self.json(200, {"request": pool.ask("stop")})
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
            if path == "/api/system/recovery" and method == "GET":  # after an unexpected shutdown (DASH-88)
                from . import recovery
                return self.json(200, {"report": recovery.report(app.data_dir)})
            if path == "/api/system/recovery/dismiss" and method == "POST":
                from . import recovery
                recovery.dismiss(app.data_dir)
                return self.json(200, {"report": None})
            if path == "/api/cleanup" and method == "GET":  # System, Clean up (DASH-77)
                from . import cleanup, full_backup
                busy = full_backup.status(app.data_dir).get("state") == "running"
                return self.json(200, cleanup.summary(app.data_dir, busy))
            if path == "/api/cleanup/hold" and method == "POST":
                from . import cleanup, full_backup
                busy = full_backup.status(app.data_dir).get("state") == "running"
                moved = cleanup.hold(app.data_dir, [str(i) for i in (self.body().get("ids") or [])][:200], busy)
                logs.event("info", "clean up", f"Moved {len(moved)} to the holding folder: " + "; ".join(moved))
                return self.json(200, {"moved": moved, **cleanup.summary(app.data_dir, busy)})
            if path == "/api/cleanup/put-back" and method == "POST":
                from . import cleanup
                where = cleanup.put_back(app.data_dir, str(self.body().get("id", "")))
                logs.event("info", "clean up", f"Put back from the holding folder: {os.path.basename(where)}")
                return self.json(200, cleanup.summary(app.data_dir))
            if path == "/api/cleanup/delete" and method == "POST":
                # Delete for good: only from the holding folder, only when the person asks, with their password
                # (owner rule: Starboard never deletes for good by itself).
                from . import cleanup
                data = self.body()
                self.check_password(data)
                freed = cleanup.delete_for_good(app.data_dir, str(data.get("id", "")))
                logs.event("warning", "clean up", f"Deleted for good from the holding folder, {freed} bytes, by the owner")
                return self.json(200, {"freed": freed, **cleanup.summary(app.data_dir)})
            if path == "/api/space-history" and method == "GET":
                return self.json(200, {"on": cfg.data["performance"].get("space_log", True), "days": app.space.get()})
            if path == "/api/version" and method == "GET":
                return self.json(200, {"current": app.version, "latest": app.latest_release(), "repo": app.repo,
                                       "since": (cfg.data.get("version_since") or {}).get("since")})
            if path.startswith("/api/backup/schedule"):  # Scheduled backups (DASH-17)
                from . import backup_schedule, full_backup
                if path == "/api/backup/schedule" and method == "GET":
                    return self.json(200, app.backup_schedule.status())
                if path == "/api/backup/schedule/key" and method == "POST":
                    # Kept so a scheduled copy can be made with nobody there: the key made from the password, never the password.
                    data = self.body()
                    self.check_password(data)
                    try:
                        full_backup.save_key(app.data_dir, str(data.get("backup_password") or ""), str(data.get("folder") or ""),
                                             bool(data.get("pictures")))
                    except (full_backup.BackupError, ValueError) as e:
                        return self.error(400, str(e))
                    logs.event("info", "backup", "The key for scheduled full backups was saved")
                    return self.json(200, app.backup_schedule.status())
                if path == "/api/backup/schedule/forget" and method == "POST":
                    self.check_password(self.body())
                    full_backup.forget_key(app.data_dir)
                    logs.event("info", "backup", "The key for scheduled full backups was removed")
                    return self.json(200, app.backup_schedule.status())
            if path.startswith("/api/backup/full"):  # Full without media (DASH-260)
                from . import backup_schedule, full_backup
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    if path == "/api/backup/full" and method == "GET":
                        try:
                            full_backup._aes()
                            can = ""
                        except full_backup.BackupError as e:
                            can = str(e)
                        return self.json(200, {"status": full_backup.status(app.data_dir), "folder": full_backup.default_folder(app.data_dir),
                                               "cannot": can, "installed": bool(stack.env_values(app.data_dir).get("CONFIG_DIR")),
                                               "docker": containers.available(), "starboard": full_backup.sizes(app.data_dir),
                                               "keep": backup_schedule.keep_for(app.backup_schedule.mode())})
                    if path == "/api/backup/full/sizes" and method == "GET":
                        return self.json(200, {"apps": full_backup.app_sizes(app.data_dir), "starboard": full_backup.sizes(app.data_dir)})
                    if path == "/api/backup/full/found" and method == "GET":
                        return self.json(200, {"found": full_backup.found(q.get("folder", [""])[0])})
                    if path == "/api/backup/full" and method == "POST":
                        data = self.body()
                        self.check_password(data)
                        full_backup.start(app.data_dir, app.version, str(data.get("backup_password") or ""), str(data.get("folder") or ""),
                                          bool(data.get("pictures")), cfg.data.get("site_name", ""),
                                          keep=backup_schedule.keep_for(app.backup_schedule.mode()))
                        logs.event("info", "backup", "Full backup started")
                        return self.json(202, {"status": full_backup.status(app.data_dir)})
                    if path == "/api/backup/full/restore" and method == "POST":
                        data = self.body()
                        self.check_password(data)
                        out = full_backup.restore(app.data_dir, str(data.get("file") or ""), str(data.get("backup_password") or ""))
                        raw = out["settings"] or {}
                        count = backup.restore(cfg, {"format": backup.FORMAT, "schema": raw.get("schema"), "services": raw.get("services") or [],
                                                     "settings": {k: raw[k] for k in backup.GENERAL_KEYS + backup.OTHER_KEYS if k in raw}})
                        logs.event("info", "backup", f"Full backup restored ({count} apps, {len(out['apps'])} app folders)")
                        choice = stack.current_choice(app.data_dir)
                        return self.json(200, {"apps": count, "folders": out["apps"], "config": cfg.public(), "install": choice,
                                               "header": out["header"]})
                except full_backup.BackupError as e:
                    return self.error(400, str(e))
                except ValueError as e:
                    return self.error(400, str(e))
            if path == "/api/backup/settings" and method == "POST":
                self.check_password(self.body())
                return self.json(200, backup.export(cfg, app.version, app.data_dir))
            if path == "/api/backup/restore" and method == "POST":
                data = self.body(limit=2 * 1024 * 1024)
                self.check_password(data)
                count = backup.restore(cfg, data.get("backup"))
                saved = data.get("backup") or {}
                backup.restore_logo_choices(app.data_dir, saved.get("logos"))
                plugins_missing = backup.restore_plugin_settings(app.data_dir, saved.get("plugins"))
                logs.event("info", "backup", f"Settings restored from a file ({count} apps)")
                # DASH-268: on a rebuilt server, the set-ups bring the backup's apps back (Storage, then Check).
                return self.json(200, {"apps": count, "config": cfg.public(), "plugins_missing": plugins_missing,
                                       "install": backup.apps_to_bring_back(data.get("backup"), app.data_dir)})
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
                from . import backup_schedule
                backup.request_server_backup(bool(self.body().get("with_prompt")), keep=backup_schedule.keep_for(app.backup_schedule.mode()))
                return self.json(200, backup.server_status())
            if path == "/api/password" and method == "POST":
                return self.change_password()
            if path in ("/api/locations", "/api/locations/chosen") and method == "GET":  # settings pattern 4 (DASH-310)
                from . import locations
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                app_name = q.get("app", ["host"])[0]
                try:
                    if path.endswith("chosen"):
                        return self.json(200, {"path": locations.chosen(app_name, q.get("host", [""])[0], data_dir=app.data_dir)})
                    host_defaults = None
                    if app_name == "host":
                        d = self.takeover_defaults()
                        from . import full_backup
                        host_defaults = {"media": d["data_dir"], "config": d["config_dir"], "backups": full_backup.default_folder(app.data_dir)}
                    return self.json(200, locations.describe(app_name, q.get("path", [""])[0], q.get("for", [""])[0],
                                                             host_defaults=host_defaults, data_dir=app.data_dir))
                except ValueError as e:
                    return self.error(400, str(e))
            if path in ("/api/folders", "/api/folders/check") and method == "GET":  # the folder picker (DASH-240)
                from . import folders
                where = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("path", [""])[0]
                if path.endswith("check"):
                    return self.json(200, folders.check(where))
                try:
                    return self.json(200, folders.browse(where))
                except LookupError as e:
                    return self.error(404, str(e))
            if path == "/api/app-logs" and method == "GET":  # App logs on System, Logs (DASH-223): in place of Dozzle
                from . import app_logs
                return self.json(200, app_logs.listing())
            ml = re.match(r"^/api/app-logs/([A-Za-z0-9][A-Za-z0-9_.-]{0,63})$", path)
            if ml and method == "GET":
                from . import app_logs
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                try:
                    return self.json(200, app_logs.lines(ml.group(1), q.get("tail", ["300"])[0], q.get("find", [""])[0],
                                                         words=[app.config.data.get("site_name", ""), app.config.data.get("server_name", ""), socket.gethostname()]))
                except LookupError as e:
                    return self.error(404, str(e))
            if path == "/api/styles" and method == "GET":  # styles from plug-ins that are on (DASH-284)
                from . import plugins_admin
                return self.json(200, {"styles": plugins_admin.styles(app.data_dir)})
            if path.startswith("/api/plugins"):  # Settings, Plug-ins (DASH-149)
                return self.plugins_route(method, path)
            if path == "/api/keys" and method == "GET":  # API keys (DASH-274): never their secrets
                from . import api_v1
                return self.json(200, {"keys": api_v1.list_keys(app.data_dir), "scopes": api_v1.SCOPES, "rights": api_v1.RIGHTS},
                                 {"Cache-Control": "no-store"})
            if path == "/api/keys" and method == "POST":
                from . import api_v1
                body = self.body()
                self.check_password(body)
                key, item = api_v1.create_key(app.data_dir, body.get("name"), body.get("right", "read"), body.get("scopes"),
                                              body.get("expires_days", 90))
                logs.event("info", "security", f"API key made: {item['name']}")
                return self.json(200, {"key": key, "item": item}, {"Cache-Control": "no-store"})
            m = re.match(r"^/api/keys/([0-9a-f]{6})$", path)
            if m and method == "DELETE":
                from . import api_v1
                if not api_v1.revoke_key(app.data_dir, m.group(1)):
                    return self.error(404, "No key with that id")
                logs.event("info", "security", "API key revoked")
                return self.json(200, {"keys": api_v1.list_keys(app.data_dir)})
            if path == "/api/sessions/end-all" and method == "POST":
                # The password again (DASH-280), as changing it asks: a stolen session cannot lock everyone out.
                self.check_password(self.body())
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
        except reelix_setup.ReelixError as e:  # Reelix answered with a problem, or not at all: said as it is
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

    def plugins_route(self, method, path):
        """Settings, Plug-ins (DASH-149): add (password), enable, disable, remove (password), Stop all, settings."""
        from . import plugins_admin as pa
        app = self.app
        media = (stack.env_values(app.data_dir).get("DATA_DIR") or "").rstrip("/")
        media = f"{media}/media" if media else "/nonexistent-media-folder"
        from . import plugin_life
        if path == "/api/plugins" and method == "GET":
            from . import livetv_move
            added = {p["id"] for p in pa.listing(app.data_dir)}
            built = [{**pa.summary(m, []), "added": m["id"] in added,
                      "why_not": livetv_move.can_run(app.data_dir) if m["id"] == livetv_move.PID else ""}
                     for m in pa.builtins().values()]
            updates = plugin_life.updates_known(app.data_dir)  # from catalogues already read; nothing fetched here
            from . import plugin_watch
            listed = pa.listing(app.data_dir)
            well = plugin_watch.health(app.data_dir, listed)  # asked now, at most once a minute each (DASH-357)
            return self.json(200, {"plugins": [{**p, "update": updates.get(p["id"]), "health": well.get(p["id"]),
                                                "resting": plugin_watch.resting(app.data_dir, p["id"])} for p in listed], "builtin": built,
                                   "wanted": pa.wanted_from_setup(app.config, {p["id"] for p in listed})})
        if path == "/api/plugins/wanted" and method == "POST":  # Not now on a plug-in chosen in the set-up (DASH-399)
            said = pa.drop_wanted(app.config, str(self.body().get("id") or ""))
            return self.json(200, {"said": said})
        if path == "/api/plugins/jobs" and method == "GET":  # System, Jobs: every plug-in's jobs (DASH-330)
            return self.json(200, {"jobs": plugin_life.jobs(app.data_dir)})
        mj = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/jobs/([a-z][a-z0-9-]{0,30})$", path)
        if mj and method == "POST":
            try:
                if not any(j["plugin"] == mj.group(1) and j["job"] == mj.group(2) and j["enabled"] for j in plugin_life.jobs(app.data_dir)):
                    return self.error(409, "Turn the plug-in on first")
                threading.Thread(target=plugin_life.run_job, args=(app.data_dir, mj.group(1), mj.group(2)), name="plugin-job", daemon=True).start()
            except LookupError as e:
                return self.error(404, str(e))
            return self.json(200, {"said": "Started", "jobs": plugin_life.jobs(app.data_dir)})
        mu = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/(update|rollback)$", path)
        if mu and method == "POST":
            # Update to a newer version (from a catalogue, checked by SHA-256, or from an address), keeping the one
            # before for Roll back; or Roll back. Both need the password, as adding does. preview: what is new.
            pid, what = mu.groups()
            if not any(p["id"] == pid for p in pa.listing(app.data_dir)):
                return self.error(404, "No plug-in with that id")
            body = self.body()
            try:
                if what == "rollback":
                    self.check_password(body)
                    said = plugin_life.rollback(app.data_dir, pid, media, services=app.config.data["services"])
                else:
                    known = plugin_life.updates_known(app.data_dir).get(pid)
                    if body.get("address"):
                        manifest = pa.fetch_manifest(body["address"])
                    elif known:
                        manifest = pa.fetch_manifest(known["manifest"], sha256=known.get("sha256", ""))
                    else:
                        return self.error(404, "No newer version is known. Open the Catalogue to look again, or give an address")
                    if body.get("preview"):
                        old = pa._read(os.path.join(pa.folder(app.data_dir, pid), "manifest.json"), {}) or {}
                        return self.json(200, {**pa.summary(manifest), "new_permissions": plugin_life.new_permissions(old, manifest),
                                               "changelog": (known or {}).get("changelog", ""), "from": old.get("version")})
                    self.check_password(body)
                    said = plugin_life.update(app.data_dir, pid, manifest, media, services=app.config.data["services"],
                                              note="" if body.get("address") else (known or {}).get("changelog", ""))
            except LookupError as e:
                return self.error(404, str(e))
            logs.event("info", "plug-ins", said)
            app.plugin_clock.ensure()
            app.plugin_idle.ensure()
            return self.json(200, {"said": said, "plugins": pa.listing(app.data_dir)})
        mw = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/whats-new-seen$", path)
        if mw and method == "POST":
            # Got it on What is new (DASH-393): kept on the server, so it is not shown again on any device.
            if not any(p["id"] == mw.group(1) for p in pa.listing(app.data_dir)):
                return self.error(404, "No plug-in with that id")
            plugin_life.whats_new_seen(app.data_dir, mw.group(1))
            return self.json(200, {"said": "Marked as seen"})
        if path == "/api/plugins/catalogue" and method == "GET":
            # The Catalogue page (DASH-318): the Starboard plug-ins collection, each marked when already added.
            have = {p["id"] for p in pa.added(app.data_dir)}
            cats, items = pa.catalogue(app.config)
            return self.json(200, {"catalogues": cats, "plugins": [{**e, "added": e["id"] in have} for e in items]})
        if path == "/api/plugins/catalogues" and method == "POST":
            # Catalogue sources added from a link (owner, 12 November 2026). Adding one installs nothing.
            body = self.body()
            try:
                if body.get("action") == "remove":
                    pa.remove_source(app.config, str(body.get("url") or ""))
                    return self.json(200, {"said": "Catalogue removed. Plug-ins you added from it stay"})
                got = pa.add_source(app.config, str(body.get("url") or ""))
            except LookupError as e:
                return self.error(404, str(e))
            except ValueError as e:
                return self.error(400, str(e))
            return self.json(200, {"said": f"{got['name']} added, with {len(got['items'])} plug-ins"})
        if path == "/api/plugins/add-builtin" and method == "POST":
            # A plug-in that ships inside Starboard, such as Live TV (DASH-285): the password, then added and active.
            from . import livetv_move
            body = self.body()
            self.check_password(body)
            pid = str(body.get("id", ""))
            if pid not in pa.builtins():
                return self.error(404, "Not a plug-in built into Starboard")
            if pid == livetv_move.PID:
                why = livetv_move.can_run(app.data_dir)
                if why:
                    raise ValueError(f"Live TV cannot run as a plug-in here: {why}. It keeps running inside Starboard")
                item = livetv_move.add(app.config, app.data_dir, media, app.jobs.self_url())
                with app.config.lock:
                    app.config.data["extras"]["livetv"] = False
                    app.config.save()
            else:
                item = pa.install(app.data_dir, pa.builtins()[pid], media, builtin=True)
            logs.event("info", "plug-ins", f"Added {item['name']}, built into Starboard")
            return self.json(200, {"plugin": item, "plugins": pa.listing(app.data_dir)})
        if path in ("/api/plugins/preview", "/api/plugins/add", "/api/plugins/test") and method == "POST":
            from . import plugin_tester
            body = self.body()
            listed = None
            if body.get("catalogue_id"):  # from a catalogue (DASH-330): its newest fitting version, checked by SHA-256
                listed = next((e for e in pa.catalogue(app.config)[1] if e["id"] == body["catalogue_id"] and e.get("manifest")), None)
                if not listed:
                    return self.error(404, "That plug-in has no version for this Starboard in the catalogue")
            manifest = (pa.parse(body["manifest"]) if body.get("manifest") else
                        pa.fetch_manifest(listed["manifest"], sha256=listed.get("sha256", "")) if listed else pa.fetch_manifest(body.get("address")))
            if path.endswith("test"):  # the plug-in tester: every issue, accessibility always (DASH-284)
                return self.json(200, plugin_tester.report(manifest, dev=bool(body.get("dev"))))
            if path.endswith("preview"):
                return self.json(200, {**pa.summary(manifest), "test": plugin_tester.report(manifest)})
            self.check_password(body)
            if not plugin_tester.report(manifest)["ok"]:
                raise ValueError("This plug-in has errors. Test it to see them")
            item = pa.install(app.data_dir, manifest, media)
            if item["id"] in pa.FROM_SETUP.values():  # chosen in the set-up and now added: no more offer (DASH-399)
                pa.drop_wanted(app.config, item["id"])
            logs.event("info", "plug-ins", f"Added {item['name']} {item['version']}")
            return self.json(200, {"plugin": item, "plugins": pa.listing(app.data_dir)})
        if path == "/api/plugins/cards" and method == "GET":  # plug-in cards for the dashboard
            from . import plugin_cards
            return self.json(200, {"cards": plugin_cards.available(app.data_dir)})
        mc = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/cards/([A-Za-z0-9_-]{1,40})$", path)
        if mc and method == "GET":
            from . import plugin_cards
            try:
                return self.json(200, plugin_cards.answer(app.data_dir, mc.group(1), mc.group(2)))
            except LookupError as e:
                return self.error(404, str(e))
        mf = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/custom/([a-z][a-z0-9_]{0,40})/file$", path)
        if mf and method == "POST":  # a file chosen beside a plug-in screen's add box, streamed through (DASH-359)
            from . import plugin_custom
            length = self.content_length()
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            name, item = q.get("name", [""])[0], q.get("id", [""])[0]
            if not 0 < length <= plugin_custom.MAX_UPLOAD:
                self.close_connection = True
                return self.error(400, "Choose a file up to 60 MB")
            try:
                out = plugin_custom.upload(app.data_dir, mf.group(1), mf.group(2), name, length, self.rfile, item)
                self._body_read = True
            except LookupError as e:
                self.close_connection = True
                return self.error(404, str(e))
            except ValueError as e:
                self.close_connection = True
                return self.error(400, str(e))
            if out.get("said"):
                logs.event("info", "plug-ins", f"{mf.group(1)}: {out['said']}")
            return self.json(200, out)
        mx = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/custom/([a-z][a-z0-9_]{0,40})$", path)
        if mx and method in ("GET", "POST"):  # a plug-in's own screen, drawn by Starboard (11 November 2026)
            from . import plugin_custom
            try:
                out = plugin_custom.call(app.data_dir, mx.group(1), mx.group(2), self.body() if method == "POST" else None)
            except LookupError as e:
                return self.error(404, str(e))
            except ValueError as e:
                return self.error(400, str(e))
            if method == "POST" and out.get("said"):
                logs.event("info", "plug-ins", f"{mx.group(1)}: {out['said']}")
            return self.json(200, out)
        if path == "/api/plugins/stop-all" and method == "POST":
            stopped = pa.stop_all(app.data_dir)
            logs.event("info", "plug-ins", f"Deactivated every plug-in ({len(stopped)})")
            return self.json(200, {"stopped": stopped, "plugins": pa.listing(app.data_dir)})
        ma = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/actions/([A-Za-z0-9_-]{1,40})$", path)
        if ma and method == "POST":  # a button from the plug-in's manifest, such as Run Live TV now
            from . import plugin_cards
            try:
                return self.json(200, plugin_cards.action(app.data_dir, ma.group(1), ma.group(2)))
            except LookupError as e:
                return self.error(404, str(e))
        m = re.match(r"^/api/plugins/([a-z0-9-]{3,40})/(enable|disable|remove|settings)$", path)
        if not m or not any(p["id"] == m.group(1) for p in pa.listing(app.data_dir)):
            return self.error(404, "No plug-in with that id")
        pid, what = m.groups()
        if what == "settings" and method == "PUT":
            return self.json(200, {"settings": pa.save_settings(app.data_dir, pid, self.body().get("settings") or {})})
        if method != "POST":
            return self.error(405, "Not allowed")
        if what == "remove":
            self.check_password(self.body())
            pa.uninstall(app.data_dir, pid)
            logs.event("info", "plug-ins", f"Removed {pid}; its folder is kept in data/plugins/.removed")
        elif what == "enable":
            pa.enable(app.data_dir, pid, services=app.config.data["services"])
        else:
            pa.disable(app.data_dir, pid)
        app.plugin_clock.ensure()  # jobs start or stop with their plug-in
        app.plugin_idle.ensure()  # and idle stop with a when_needed one (DASH-357)
        return self.json(200, {"plugins": pa.listing(app.data_dir)})

    def start_stack(self):
        """Starts the apps in data/stack: through Docker when Starboard has access, else through the Run first window
        when it is open. Raises ValueError when neither can, so the page shows the one command instead."""
        app = self.app
        host = stack.host_folder(app.data_dir)
        env_file = os.path.join(stack.folder(app.data_dir), ".env")
        if os.path.exists(env_file) and not (host and containers.available()) and stack.starter_waiting(app.data_dir):
            logs.event("info", "install apps", "Asked the Run first window to start the apps in data/stack")
            return stack.start_via_starter(app.data_dir)
        if not host or not containers.available() or not os.path.exists(env_file):
            raise ValueError("Starboard cannot start apps here. Run the command instead")
        with open(env_file) as f:
            logs.event("info", "install apps", "Starting the apps in data/stack")
            return stack.start(host, f.read())

    def add_found(self, items):
        return add_found(self.app, items)

    # Watch history import --------------------------------------------------------------

    def start_import(self, data):
        """Reads history from a Plex server, an Emby or Jellyfin server, or a file already in data/imports."""
        app = self.app
        kind = str(data.get("kind", ""))
        url = str(data.get("url", "")).strip().rstrip("/")
        secret = str(data.get("token", "")).strip()
        if kind in ("plex", "emby", "jellyfin") and not re.match(r"^https?://[^\s/]+(/\S*)?$", url):
            return self.error(400, "Enter the server's address, starting with http:// or https://")
        if url:
            from . import outside  # the server Starboard is told to read from (DASH-279)
            try:
                outside.check_url(url)
            except ValueError as e:
                return self.error(400, str(e))
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
        if url:
            from . import outside  # the server Starboard is told to read from (DASH-279)
            try:
                outside.check_url(url)
            except ValueError as e:
                return self.error(400, str(e))
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
            return self.error(400, "That history file is larger than 80 MB")
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
        self._body_read = not left
        if left:
            app.importing = None
            self.close_connection = True
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
        with FIRST_PASSWORD_LOCK:
            if not app.needs_setup or not app.setup_token:  # another request chose it while this one was checked
                return self.error(409, "A password is already set. Sign in instead")
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
    resume_adopting(app)
    server = BoundedServer((host, port), handler)
    server.daemon_threads = True
    return server, app
