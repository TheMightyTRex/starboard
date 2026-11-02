"""Watching in the background: uptime history, alerts and a weekly summary. Off until it is turned on.

When on, every few minutes (5 by default) Starboard checks your apps and, when the alerts ask for it, disks,
downloads and the server backup, using the same checks the pages use. It stores only the moments an app
starts or stops answering (data/uptime.json, 8 days), and sends an alert when something changes:
- an app stops answering (twice in a row, so a restart does not alert) and when it answers again;
- a disk reports a problem or a failed health check, or a folder gets fuller than the limit;
- a download has needed attention for 30 minutes;
- the server backup failed;
- an outside address's certificate runs out within the days set (checked once a day).
A weekly summary goes out on Monday morning if it is turned on.

Alerts go to ntfy, Gotify or any webhook (a JSON post). Their token stays on the server.
"""

import json
import os
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from . import backup, services, sysinfo

KEEP = 8 * 86400


def _size(n):
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1000 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1000


# Sending ---------------------------------------------------------------------------

def send(channel, title, message, level="info"):
    """Sends one alert. Raises ValueError with words a person can act on when it fails."""
    kind, url, token = channel.get("kind"), channel.get("url", ""), channel.get("token", "")
    if kind not in ("ntfy", "gotify", "webhook") or not url:
        raise ValueError("Choose where to send alerts first")
    priority = {"info": 3, "warning": 4, "problem": 5}.get(level, 3)
    headers = {"User-Agent": "Starboard"}
    if kind == "ntfy":
        headers.update({"Title": title.encode("utf-8").decode("latin-1", "replace"), "Priority": str(priority),
                        "Tags": {"info": "information_source", "warning": "warning", "problem": "rotating_light"}[level]})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=message.encode(), headers=headers, method="POST")
    elif kind == "gotify":
        headers["Content-Type"] = "application/json"
        target = url.rstrip("/") + "/message?" + urllib.parse.urlencode({"token": token})
        req = urllib.request.Request(target, data=json.dumps({"title": title, "message": message, "priority": priority}).encode(),
                                     headers=headers, method="POST")
    else:
        headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=json.dumps({"title": title, "message": message, "level": level,
                                                           "source": "Starboard"}).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read(1000)
    except urllib.error.HTTPError as e:
        raise ValueError(f"The alert address answered with error {e.code}") from None
    except (urllib.error.URLError, OSError):
        raise ValueError("Starboard cannot reach the alert address") from None


def cert_days_left(url):
    """Days until the certificate of an https:// address runs out, or None when it is not https or unreachable."""
    parts = urllib.parse.urlparse(url)
    if parts.scheme != "https" or not parts.hostname:
        return None
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((parts.hostname, parts.port or 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=parts.hostname) as tls:
                not_after = tls.getpeercert()["notAfter"]
    except (OSError, ssl.SSLError, KeyError, ValueError):
        return None
    return int((ssl.cert_time_to_seconds(not_after) - time.time()) // 86400)


# Watching ----------------------------------------------------------------------------

class Watch:
    def __init__(self, app):
        self.app = app
        self.path = os.path.join(app.config.data_dir, "uptime.json")
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.thread = None
        self.state = self._load()

    def settings(self):
        return self.app.config.data["watch"]

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        data.setdefault("changes", {})   # app id -> [[time, "up" or "down"], ...]
        data.setdefault("down_count", {})  # app id -> checks in a row without an answer
        data.setdefault("alerted", {})   # what has been alerted and not cleared yet
        data.setdefault("since", time.time())
        return data

    def _save(self):
        tmp = self.path + ".tmp"
        with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            json.dump(self.state, f)
        os.replace(tmp, self.path)

    def start(self):
        self.ensure()

    def ensure(self):
        """Starts the thread when watching is on; a running thread is woken, and ends if watching is off."""
        if self.thread and self.thread.is_alive():
            self.wake.set()
            return
        if self.settings()["enabled"]:
            self.thread = threading.Thread(target=self._loop, name="watch", daemon=True)
            self.thread.start()

    def _loop(self):
        while True:
            w = self.settings()
            if not w["enabled"]:
                self.thread = None
                return  # watching off: no thread at all until it is turned on again
            try:
                self.tick()
            except Exception as e:  # keep watching whatever one check does
                print(f"[starboard] watch: {e}", flush=True)
            # Sleep until the next check; a change in Settings wakes it at once.
            self.wake.wait(max(60, int(w.get("every", 5)) * 60))
            self.wake.clear()

    def alert(self, key, title, message, level="problem"):
        """Sends an alert once for each key, until clear(key)."""
        if key in self.state["alerted"]:
            return
        self.state["alerted"][key] = time.time()
        channel = self.settings().get("channel") or {}
        if channel.get("kind") in ("ntfy", "gotify", "webhook"):
            try:
                send(channel, title, message, level)
            except ValueError as e:
                print(f"[starboard] alert not sent: {e}", flush=True)

    def clear(self, key, title=None, message=None):
        if self.state["alerted"].pop(key, None) and title:
            channel = self.settings().get("channel") or {}
            if channel.get("kind") in ("ntfy", "gotify", "webhook"):
                try:
                    send(channel, title, message or "", "info")
                except ValueError:
                    pass

    def tick(self):
        w = self.settings()
        on = w["alerts"]
        cfg = self.app.config.data
        name = cfg["site_name"]
        now = time.time()
        with self.lock:
            changed = False
            # Apps: record only changes; alert after two checks in a row without an answer.
            results = services.cached("status", 15, lambda: services.status_all(cfg["services"]))
            names = {s["id"]: s["name"] for s in cfg["services"]}
            for r in results:
                if r["state"] not in ("up", "down"):
                    continue
                history = self.state["changes"].setdefault(r["id"], [])
                if r["state"] == "down":
                    self.state["down_count"][r["id"]] = self.state["down_count"].get(r["id"], 0) + 1
                else:
                    self.state["down_count"][r["id"]] = 0
                confirmed = r["state"] == "up" or self.state["down_count"][r["id"]] >= 2
                if confirmed and (not history or history[-1][1] != r["state"]):
                    history.append([now, r["state"]])
                    changed = True
                app_name = names.get(r["id"], r["id"])
                if on.get("apps_down") and r["state"] == "down" and confirmed:
                    self.alert(f"down:{r['id']}", f"{app_name} is not responding", f"{name}: {r.get('message') or app_name + ' did not answer'}.")
                elif r["state"] == "up":
                    self.clear(f"down:{r['id']}", f"{app_name} is answering again", f"{name}: {app_name} is back.")
            for app_id in list(self.state["changes"]):
                kept = [c for c in self.state["changes"][app_id] if c[0] > now - KEEP]
                # Keep the last change before the window, so the start of the window has a known state.
                older = [c for c in self.state["changes"][app_id] if c[0] <= now - KEEP]
                self.state["changes"][app_id] = older[-1:] + kept
                if app_id not in names:
                    del self.state["changes"][app_id]
                    changed = True

            # Disks: health reports and how full each folder is.
            health = sysinfo.disk_health() if sysinfo.smart_dir() else {}
            self.app.disk_temps.record(health.get("disks", []))  # keeps the 30-day temperature history going
            if on.get("disk_problem"):
                for d in health.get("disks", []):
                    key = f"disk:{d['serial'] or d['device']}"
                    if d.get("passed") is False or d.get("problems"):
                        words = ", ".join(f"{p['name']} {p['value']}" for p in d.get("problems", [])) or "failed its health check"
                        self.alert(key, f"{d['model']} needs attention", f"{name}: {d['model']} ({d['device']}): {words}.")
                    else:
                        self.clear(key)
            limit = int(on.get("disk_full", 0) or 0)
            if limit:
                for d in sysinfo.snapshot(self.app.disks).get("disks", []):
                    if d.get("missing") or not d.get("total"):
                        continue
                    pct = round(d["used"] / d["total"] * 100)
                    key = f"full:{d['label']}"
                    if pct >= limit:
                        self.alert(key, f"{d['label']} is {pct}% full", f"{name}: {d['label']} has {_size(d['free'])} free.", "warning")
                    elif pct < limit - 2:
                        self.clear(key)

            # Downloads that have needed attention for 30 minutes.
            if on.get("download_stuck"):
                queue = services.cached("queue", 10, lambda: services.queue(cfg["services"]))
                stuck = self.state.setdefault("stuck_since", {})
                seen = set()
                for item in queue.get("items", []):
                    if not item.get("problem"):
                        continue
                    key = f"{item.get('service_name')}|{item.get('title')}"
                    seen.add(key)
                    stuck.setdefault(key, now)
                    if now - stuck[key] >= 1800:
                        self.alert(f"stuck:{key}", "A download needs attention",
                                   f"{name}: {item.get('title')} in {item.get('service_name')}. " + " ".join(item.get("messages") or []), "warning")
                for key in list(stuck):
                    if key not in seen:
                        del stuck[key]
                        self.clear(f"stuck:{key}")

            # The server backup.
            if on.get("backup_failed"):
                status = (backup.server_status().get("status") or {})
                key = f"backup:{status.get('started')}"
                if status.get("status") == "failed":
                    self.alert(key, "The server backup failed", f"{name}: {status.get('summary') or 'see System, Backup and restore'}.")

            # Certificates, once a day.
            days = int(on.get("cert_days", 0) or 0)
            if days and now - self.state.get("certs_checked", 0) > 86400:
                self.state["certs_checked"] = now
                for s in cfg["services"]:
                    left = cert_days_left(s.get("outside_link", "")) if s.get("enabled", True) else None
                    key = f"cert:{s['id']}"
                    if left is not None and left <= days:
                        self.alert(key, f"{s['name']}'s certificate runs out in {left} days",
                                   f"{name}: renew the certificate for {s['outside_link']}.", "warning")
                    elif left is not None:
                        self.clear(key)

            # Weekly summary: Monday, after 09:00, once.
            today = datetime.now()
            week = today.strftime("%G-%V")
            if w.get("weekly") and today.weekday() == 0 and today.hour >= 9 and self.state.get("weekly_sent") != week:
                self.state["weekly_sent"] = week
                self._weekly(name, cfg)
            self._save()

    def _weekly(self, name, cfg):
        channel = self.settings().get("channel") or {}
        lines = []
        rows = self.uptime(cfg["services"])
        worst = sorted((r for r in rows.values() if r["pct7"] is not None), key=lambda r: r["pct7"])
        down = [r for r in worst if r["pct7"] < 100]
        lines.append(f"Apps: {len(rows) - len(down)} of {len(rows)} answered all week." if rows else "Apps: no history yet.")
        for r in down[:5]:
            lines.append(f"- {r['name']}: {r['pct7']}% ({r['downs7']} {'time' if r['downs7'] == 1 else 'times'} not answering)")
        disks = sysinfo.disk_health().get("disks", [])
        if disks:
            bad = [d for d in disks if d.get("passed") is False or d.get("problems")]
            lines.append(f"Disks: {len(disks) - len(bad)} of {len(disks)} healthy." + (" Check: " + ", ".join(d["model"] for d in bad) if bad else ""))
        for d in sysinfo.snapshot(self.app.disks).get("disks", []):
            if d.get("total"):
                lines.append(f"- {d['label']}: {round(d['used'] / d['total'] * 100)}% full")
        if channel.get("kind") in ("ntfy", "gotify", "webhook"):
            try:
                send(channel, f"{name}: your week", "\n".join(lines), "info")
            except ValueError as e:
                print(f"[starboard] weekly summary not sent: {e}", flush=True)

    # The pages ---------------------------------------------------------------------

    def uptime(self, service_list):
        """For each app: answering % over 24 hours and 7 days, times it stopped, and 48 half-hour slots."""
        now = time.time()
        since = self.state.get("since", now)
        out = {}
        for s in service_list:
            changes = self.state["changes"].get(s["id"], [])
            if not changes:
                out[s["id"]] = {"name": s["name"], "pct24": None, "pct7": None, "downs7": 0, "slots": [], "last_down": None}
                continue

            def share(start):
                start = max(start, changes[0][0], since)
                if start >= now:
                    return None
                up, state, t = 0.0, None, start
                for when, st in changes:
                    if when <= start:
                        state = st
                        continue
                    if state == "up":
                        up += when - t
                    t, state = when, st
                if state == "up":
                    up += now - t
                return round(up / (now - start) * 100, 1)

            def state_at(t):
                st = None
                for when, s2 in changes:
                    if when > t:
                        break
                    st = s2
                return st

            slots = []
            for i in range(48):  # oldest first, each the worst state seen in that half hour
                a, b = now - (48 - i) * 1800, now - (47 - i) * 1800
                inside = [s2 for when, s2 in changes if a < when <= b]
                states = set(inside + [state_at(a)])
                slots.append("down" if "down" in states else "up" if "up" in states else "")
            downs = [c for c in changes if c[1] == "down" and c[0] > now - 7 * 86400]
            out[s["id"]] = {"name": s["name"], "pct24": share(now - 86400), "pct7": share(now - 7 * 86400),
                            "downs7": len(downs), "slots": slots, "last_down": downs[-1][0] if downs else None}
        return out
