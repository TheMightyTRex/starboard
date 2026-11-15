#!/usr/bin/env python3
"""The update smoke test (DASH-424, with DASH-423): an example plug-in updated from one version to the next and back,
over real HTTP, with Starboard's own update code. Run by tools/check-api.sh; nothing real is touched.

A stand-in for the plug-in's container answers on this computer (/health, /update/before, /update/after) for
whichever version is "running"; Starboard's Docker Compose call is replaced by switching the stand-in's version.
The manifest is an example plug-in's from the starboard-plugins repository (Line speed) when it is there, otherwise
a made-up one, given:

1. version 2.0.0 with an update object: a before and an after step, a health wait, and a settings migration that
   renames a setting, removes one and gives another a new default (taken only where the old default was kept). The update must run each step, move the
   settings, and Roll back must put them back as they were.
2. version 3.0.0, whose health check answers 500. The update must go back to the version before by itself, with
   the settings as they were, and tell the old version it can start again.

    python3 tools/update_smoke.py           # STARBOARD_PLUGINS: where starboard-plugins is (optional)
"""
import copy
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from starboard import plugin_cards, plugin_life, plugin_update, plugins_admin as pa  # noqa: E402

RUNNING = {"version": None}
CALLS = []


class StandIn(BaseHTTPRequestHandler):
    def _answer(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            CALLS.append(("health", RUNNING["version"]))
            return self._answer(500 if RUNNING["version"] == "3.0.0" else 200, {"ok": RUNNING["version"] != "3.0.0"})
        self._answer(404, {})

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        CALLS.append((self.path, RUNNING["version"], body))
        if self.path in ("/update/before", "/update/after"):
            return self._answer(200, {"ok": True, "said": f"{self.path.rsplit('/', 1)[1]} done on {RUNNING['version']}"})
        self._answer(404, {})

    def log_message(self, *a):
        pass


def example():
    """Line speed's manifest from starboard-plugins, or a made-up one like it."""
    for d in (os.environ.get("STARBOARD_PLUGINS") or "", os.path.join(ROOT, "..", "starboard-plugins"), os.path.expanduser("~/src/starboard-plugins")):
        path = os.path.join(d, "line-speed", "starboard-plugin.json")
        if d and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f), "Line speed from starboard-plugins"
    return ({"manifest_version": 1, "id": "line-speed", "name": "Line speed", "version": "1.0.0", "description": "A made-up plug-in",
             "author": "TheMightyTRexUK", "licence": "MIT", "homepage": "https://github.com/TheMightyTRex/starboard-plugins",
             "support_url": "https://github.com/TheMightyTRex/starboard-plugins/issues", "starboard_api": ">=1.1 <2.0", "permissions": ["network:lan"], "health": "/health",
             "containers": [{"name": "main", "image": "ghcr.io/example/line-speed@sha256:" + "0" * 64, "port": 8080, "network": "lan", "volumes": ["data"]}],
             "settings": [{"key": "hour", "label": "Test at", "type": "number", "default": 4},
                          {"key": "megabytes", "label": "Test size", "type": "number", "default": 25}]}, "a made-up plug-in")


def versions(base, port):
    v1 = copy.deepcopy(base)
    v1["version"] = "1.0.0"
    v1["containers"][0]["port"] = port
    v1["settings"] = [s for s in v1["settings"] if s["key"] in ("hour", "megabytes")] + [
        {"key": "server", "label": "Test server", "type": "text", "default": "nearest"}]
    v1["update"] = {"before": {"path": "/update/before", "time_limit_seconds": 10}, "after": {"path": "/update/after", "time_limit_seconds": 10}}
    v2 = copy.deepcopy(v1)
    v2["version"] = "2.0.0"
    v2["settings"] = [{**s, "key": "size_mb"} if s["key"] == "megabytes" else s for s in v1["settings"] if s["key"] != "server"]
    v2["settings"] = [{**s, "default": 3} if s["key"] == "hour" else s for s in v2["settings"]]
    v2["update"] = {**v1["update"], "health_wait_seconds": 10,
                    "migrations": [{"version": "2.0.0", "rename": {"megabytes": "size_mb"}, "remove": ["server"], "defaults": {"hour": 3}}]}
    v2["changes"] = [{"version": "2.0.0", "changed": ["Test size is now Size in MB", "Tests at 03:00 unless you chose a time"],
                      "removed": ["Test server: it always uses the nearest"]}]
    v3 = copy.deepcopy(v2)
    v3["version"] = "3.0.0"
    v3["changes"] = [{"version": "3.0.0", "fixed": ["A made-up fix whose health check fails"]}] + v2["changes"]
    return v1, v2, v3


def main():
    server = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("UPDATE_SMOKE_PORT", "0"))), StandIn)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    base, source = example()
    v1, v2, v3 = versions(base, port)
    failed = []

    def expect(what, ok, detail=""):
        print(f"  {'ok' if ok else 'FAILED'}  {what}" + (f": {detail}" if detail and not ok else ""))
        if not ok:
            failed.append(what)

    def compose(data_dir, pid, command, helper=None):  # Docker Compose, replaced: the stand-in runs the version on disk
        m = pa._read(os.path.join(pa.folder(data_dir, pid), "manifest.json")) or {}
        RUNNING["version"] = m.get("version") if command.startswith("up") else None
        return True, ""

    print(f"Update smoke test: {source}, stand-in on 127.0.0.1:{port}")
    with tempfile.TemporaryDirectory() as d, \
            mock.patch.object(pa, "_compose_run", side_effect=compose), \
            mock.patch.object(pa, "host_path", side_effect=lambda dd, pid: os.path.join(dd, "plugins", pid)), \
            mock.patch.object(plugin_cards, "_host", side_effect=lambda pid, main, wake=True: "127.0.0.1"), \
            mock.patch.object(plugin_update, "HEALTH_EVERY", 1):
        pid = v1["id"]
        pa.install(d, v1, os.path.join(d, "media"), dev=True)
        pa.save_settings(d, pid, {"hour": 4, "megabytes": 50, "server": "nearest"})
        pa.enable(d, pid)
        where = pa.folder(d, pid)

        def settings():
            return pa._read(os.path.join(where, "settings.json"))

        def version():
            return pa._read(os.path.join(where, "manifest.json"))["version"]

        print("1. 1.0.0 to 2.0.0, with a settings migration")
        before = plugin_update.preview(v1, v2)
        expect("What is new is shown before the update", [v["version"] for v in before["whats_new"]] == ["2.0.0"], before)
        steps = []
        r = plugin_update.update_safely(d, pid, v2, os.path.join(d, "media"), dev=True, progress=lambda *a: steps.append(f"{a[0]} {a[1]}"))
        expect("it is updated", r["outcome"] == "updated" and version() == "2.0.0" and RUNNING["version"] == "2.0.0", r)
        expect("the before step ran on 1.0.0", ("/update/before", "1.0.0", {"from": "1.0.0", "to": "2.0.0"}) in CALLS, CALLS)
        expect("the health check was asked of 2.0.0", ("health", "2.0.0") in CALLS)
        expect("the after step ran on 2.0.0", any(c[0] == "/update/after" and c[1] == "2.0.0" and c[2]["outcome"] == "updated" for c in CALLS if len(c) == 3))
        # 4 was 1.0.0's default, so it takes 2.0.0's new one; 50 MB was chosen, so it is kept under its new key.
        expect("the settings moved: renamed, removed, and a new default", settings() == {"hour": 3, "size_mb": 50}, settings())
        expect("What is new shows after the update", (plugin_life.whats_new(d, pid) or {}).get("to") == "2.0.0")
        CALLS.clear()
        r = plugin_update.rollback_safely(d, pid, os.path.join(d, "media"))
        expect("Roll back goes to 1.0.0", r["outcome"] == "rolled-back" and version() == "1.0.0" and RUNNING["version"] == "1.0.0", r)
        expect("Roll back puts the settings back as they were", settings() == {"hour": 4, "megabytes": 50, "server": "nearest"}, settings())
        expect("the version brought back hears it can start again", any(c[0] == "/update/after" and c[2].get("outcome") == "rolled_back" for c in CALLS if len(c) == 3))
        plugin_update.update_safely(d, pid, v2, os.path.join(d, "media"), dev=True)

        print("2. 2.0.0 to 3.0.0, whose health check fails")
        CALLS.clear()
        r = plugin_update.update_safely(d, pid, v3, os.path.join(d, "media"), dev=True)
        expect("the update went back by itself", r["outcome"] == "went-back" and version() == "2.0.0" and RUNNING["version"] == "2.0.0", r)
        expect("it said why", "health check" in r["said"], r["said"])
        expect("the settings are as they were on 2.0.0", settings() == {"hour": 3, "size_mb": 50}, settings())
        expect("2.0.0 heard it can start again", any(c[0] == "/update/after" and c[1] == "2.0.0" and c[2].get("outcome") == "rolled_back"
                                                     for c in CALLS if len(c) == 3), CALLS)
        expect("What is new still shows 2.0.0, not the version that did not work", (plugin_life.whats_new(d, pid) or {}).get("to") == "2.0.0",
               plugin_life.whats_new(d, pid))
        with open(os.path.join(d, "logs", "audit.jsonl"), encoding="utf-8") as f:
            audit = f.read()
        expect("the audit log has each change", all(w in audit for w in ("plugin_updated", "plugin_rolled_back", "plugin_update_rolled_back")))
    server.shutdown()
    print("FAILED" if failed else "All passed", len(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
