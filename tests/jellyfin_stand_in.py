"""A stand-in for Jellyfin's plug-in API (DASH-404): repositories, packages, installed plug-ins, their settings,
scheduled tasks and restart, answering like Jellyfin 12.4. Used by tests/test_jellyfin_plugins.py and by the example
server (tools/screenshots/example_server.py), so no real Jellyfin is ever changed. Plug-ins installed here wait for a
restart, as in Jellyfin, and become active when Restart is called."""
import threading
import urllib.parse

KEY = "made-up"


class StandIn:
    def __init__(self, version="12.4.0", plugins=None, repos=None):
        self.lock = threading.Lock()
        self.version = version
        self.pending = False
        self.repos = list(repos if repos is not None else [{"Name": "Jellyfin Stable", "Url": "https://repo.jellyfin.org/files/plugin/manifest.json", "Enabled": True}])
        self.plugins = list(plugins or [])
        self.config = {}
        self.tasks = [{"Id": "t-guide", "Key": "RefreshGuide", "Name": "Refresh Guide", "Category": "Live TV", "Triggers": []}]
        self.calls = []

    # Packages each repository offers, by repository address
    OFFERS = {
        "https://repo.jellyfin.org/files/plugin/manifest.json": {"Playback Reporting": ("5c534381-91a3-43cb-907a-35aa02eb9d2c", "19.0.0.0"),
                                                                 "Trakt": ("4fe3201e-d6ae-4f2e-8917-e12bda571281", "31.0.0.0")},
        "https://raw.githubusercontent.com/TheIntroDB/jellyfin-plugin/main/manifest.json": {"TheIntroDB": ("c9e41b95-63e4-45e2-9db6-b83df21ae5e7", "1.3.1.0")},
        "https://intro-skipper.org/manifest.json": {"Intro Skipper": ("c83d86bb-a1e0-4c35-a113-e2101cf4ee6b", "1.10.11.24"),
                                                    "SkipMe.db": ("b2a63e62-0ac5-4575-9ad2-2c7534ccb83d", "0.1.16.0")},
        "https://raw.githubusercontent.com/danieladov/JellyfinPluginManifest/master/manifest.json": {"Merge Versions": ("f21bbed8-3a97-4d8b-88b2-48aaa65427cb", "12.0.1.0")},
    }
    TASKS = {"Intro Skipper": [("IntroSkipperDetectSegmentsTask", "Detect and Analyze Media Segments")],
             "Merge Versions": [("MergeMoviesTask", "Merge All Movies"), ("MergeEpisodesTask", "Merge All Episodes")]}

    def _plugin(self, pid):
        return next((p for p in self.plugins if p["Id"] == pid), None)

    def handle(self, method, path, body=None, headers=None):
        """(status, answer) for one request. Wrong key: 401, as Jellyfin."""
        if (headers or {}).get("Authorization") != f'MediaBrowser Token="{KEY}"':
            return 401, None
        route, _, query = path.partition("?")
        q = dict(urllib.parse.parse_qsl(query))
        with self.lock:
            self.calls.append((method, route))
            if method == "GET" and route == "/System/Info":
                return 200, {"Version": self.version, "ServerName": "Harbour", "HasPendingRestart": self.pending, "CanSelfRestart": True}
            if method == "GET" and route == "/Plugins":
                return 200, [dict(p) for p in self.plugins]
            if method == "GET" and route == "/Repositories":
                return 200, [dict(r) for r in self.repos]
            if method == "POST" and route == "/Repositories":
                self.repos = [dict(r) for r in body or []]
                return 204, None
            if method == "POST" and route.startswith("/Packages/Installed/"):
                name = urllib.parse.unquote(route.rsplit("/", 1)[1])
                offer = (self.OFFERS.get(q.get("repositoryUrl", "")) or {}).get(name)
                enabled = any(r["Url"] == q.get("repositoryUrl") and r.get("Enabled", True) for r in self.repos)
                if not offer or not enabled or offer[0] != q.get("assemblyGuid"):
                    return 404, {"message": "Package not found"}
                guid, version = offer
                self.plugins.append({"Name": name, "Version": version, "Id": guid.replace("-", ""), "Status": "Restart", "CanUninstall": True})
                self.pending = True
                return 204, None
            parts = route.strip("/").split("/")
            if method == "POST" and len(parts) == 4 and parts[0] == "Plugins" and parts[3] in ("Enable", "Disable"):
                p = self._plugin(parts[1])
                if not p:
                    return 404, None
                p["Status"] = "Restart" if parts[3] == "Enable" else "Disabled"
                p["_after"] = "Active" if parts[3] == "Enable" else "Disabled"
                self.pending = True
                return 204, None
            if len(parts) == 3 and parts[0] == "Plugins" and parts[2] == "Configuration":
                if method == "GET":
                    return 200, dict(self.config.get(parts[1]) or {"AutoDetectIntros": True, "MaxParallelism": 2, "ProcessPriority": "BelowNormal"})
                self.config[parts[1]] = dict(body or {})
                return 204, None
            if method == "GET" and route == "/ScheduledTasks":
                return 200, [dict(t) for t in self.tasks]
            if method == "POST" and len(parts) == 3 and parts[0] == "ScheduledTasks" and parts[2] == "Triggers":
                t = next((t for t in self.tasks if t["Id"] == parts[1]), None)
                if not t:
                    return 404, None
                t["Triggers"] = list(body or [])
                return 204, None
            if method == "POST" and route == "/System/Restart":
                self.restart()
                return 204, None
        return 404, None

    def restart(self):
        """Pending plug-ins become active, and their scheduled tasks appear."""
        for p in self.plugins:
            if p["Status"] == "Restart":
                p["Status"] = p.pop("_after", "Active")
                for key, name in self.TASKS.get(p["Name"], []):
                    if not any(t["Key"] == key for t in self.tasks):
                        self.tasks.append({"Id": f"t-{key}", "Key": key, "Name": name, "Category": p["Name"],
                                           "Triggers": [{"Type": "IntervalTrigger", "IntervalTicks": 24 * 36_000_000_000}]})
        self.pending = False
