"""Host alerts (DASH-556): alerts when the server itself is struggling.

Each is off until it is switched on with a limit and a time:
- the processor's temperature, how busy the processor is, how much memory is in use, how full a folder is, and how
  fast the drives read and write, each when it stays over its limit for the chosen time;
- the server's outside address changing (the No-IP updater's, and each VPN's), without ever saying the address;
- a container stopping with an error or dying (a container stopped on purpose, or resting, is not an alert).

It costs nothing while every one is off: no thread runs. While at least one is on, one thread wakes a minute and
makes one cheap read of /proc and /sys (sysinfo.monitor, the same read the System charts use), one read of the
folders' space when that rule is on, and one Docker list when the container rule is on. The outside address is looked
at every 10 minutes, only when its rule is on. Nothing is sent to any other server: the addresses come from the
No-IP updater's own log and from Gluetun's own status, which Starboard already reads. The alerts go through
Watch.alert, so they reach the places the alerts already reach, once until they clear.
"""
import json
import threading
import time

from . import logs, sysinfo

# rule: (the words of the alert, unit, lowest limit, highest limit, what is read)
RULES = {
    "cpu_temp": ("The processor is too hot", "°C", 40, 110),
    "load": ("The processor is too busy", "%", 50, 100),
    "memory": ("Memory is nearly full", "%", 50, 99),
    "disk_space": ("A folder is nearly full", "%", 50, 99),
    "disk_rate": ("The disks are working hard", "MB/s", 10, 5000),
}
SWITCHES = ("address", "container")
MINUTES = (1, 5, 10, 15, 30, 60, 120)
EVERY = 60  # seconds between readings
ADDRESS_EVERY = 600


def clean(incoming, current):
    """The host settings from what a person sent, with the reason when it is wrong."""
    from .config import ConfigError
    out = json.loads(json.dumps(current))
    for key, value in incoming.items():
        if key not in RULES and key not in SWITCHES:
            continue
        if not isinstance(value, dict):
            raise ConfigError("Send each host alert as an object")
        mine = out.setdefault(key, {})
        if "on" in value:
            mine["on"] = bool(value["on"])
        if key in RULES:
            lo, hi = RULES[key][2], RULES[key][3]
            if "limit" in value:
                limit = int(value["limit"])
                if not lo <= limit <= hi:
                    raise ConfigError(f"Choose a limit from {lo} to {hi} {RULES[key][1]}")
                mine["limit"] = limit
            if "minutes" in value:
                minutes = int(value["minutes"])
                if minutes not in MINUTES:
                    raise ConfigError("Choose how long from the list")
                mine["minutes"] = minutes
    return out


def processor_temperature(temps):
    pkg = next((t["c"] for t in temps if any(k in t["label"].lower() for k in ("package", "tctl", "tdie"))), None)
    return pkg if pkg is not None else (temps[0]["c"] if temps else None)


class Hold:
    """Over a limit for a chosen time: a value counts only once it has stayed over for `minutes`."""

    def __init__(self):
        self.since = None

    def over(self, now, above, minutes):
        """True when it has stayed over long enough. Coming back under, with a small gap, starts again."""
        if not above:
            self.since = None
            return False
        if self.since is None:
            self.since = now
        return now - self.since >= minutes * 60 - 1


class HostWatch:
    def __init__(self, app):
        self.app = app
        self.thread = None
        self.wake = threading.Event()
        self.holds = {k: Hold() for k in RULES}
        self.before = None
        self.addresses = {}
        self.address_at = 0
        self.running = None

    def rules(self):
        return (self.app.config.data.get("watch") or {}).get("host") or {}

    def any_on(self):
        return any((v or {}).get("on") for v in self.rules().values())

    def ensure(self):
        """Starts the thread when a rule is on, and lets it end when none is: nothing at rest otherwise."""
        if self.thread and self.thread.is_alive():
            self.wake.set()
            return
        if self.any_on():
            self.before = None
            self.thread = threading.Thread(target=self._loop, name="host-alerts", daemon=True)
            self.thread.start()

    def _loop(self):
        while True:
            if not self.any_on():
                self.thread = None
                return
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001  keep watching whatever one reading does
                logs.event("warning", "alert", f"A host reading failed: {e}")
            self.wake.wait(EVERY)
            self.wake.clear()

    # One reading ----------------------------------------------------------------

    def tick(self, now=None, reading=None):
        now = time.time() if now is None else now
        rules = self.rules()
        seen = {}
        want_reading = any((rules.get(k) or {}).get("on") for k in ("cpu_temp", "load", "memory", "disk_rate"))
        if want_reading:
            m = reading if reading is not None else sysinfo.monitor(apps=False)
            prev, self.before = self.before, m
            if (rules.get("cpu_temp") or {}).get("on"):
                seen["cpu_temp"] = processor_temperature(m["temps"])
            if (rules.get("memory") or {}).get("on") and m["memory"]["total"]:
                seen["memory"] = 100 * (m["memory"]["total"] - m["memory"]["available"]) / m["memory"]["total"]
            if prev:
                if (rules.get("load") or {}).get("on") and m["cpu"]["total"] and prev["cpu"]["total"]:
                    total = m["cpu"]["total"][0] - prev["cpu"]["total"][0]
                    if total > 0:
                        seen["load"] = max(0.0, 100 * (1 - (m["cpu"]["total"][1] - prev["cpu"]["total"][1]) / total))
                if (rules.get("disk_rate") or {}).get("on"):
                    dt = max(1.0, m["time"] - prev["time"])
                    moved = sum(sum(v) for v in m["disks"].values()) - sum(sum(v) for v in prev["disks"].values())
                    seen["disk_rate"] = max(0.0, moved / dt / 1e6)
        full = []
        if (rules.get("disk_space") or {}).get("on"):
            for d in sysinfo.snapshot(self.app.disks).get("disks", []):
                if not d.get("missing") and d.get("total"):
                    full.append((d["label"], 100 * d["used"] / d["total"]))
            seen["disk_space"] = max((p for _, p in full), default=None)
        name = self.app.config.data["site_name"]
        for key, value in seen.items():
            rule = rules[key]
            title, unit = RULES[key][0], RULES[key][1]
            if value is None:
                continue
            limit = rule["limit"]
            hold = self.holds[key]
            if hold.over(now, value >= limit, rule["minutes"]):
                what = f"{value:.0f}{'' if unit == '%' else ' '}{unit}, over the limit of {limit}{'' if unit == '%' else ' '}{unit}"
                if key == "disk_space":
                    worst = max(full, key=lambda x: x[1])[0]
                    what = f"{worst} is {value:.0f}% full, over the limit of {limit}%"
                self._alert(f"host:{key}", title, f"{name}: {what} for {self._words(rule['minutes'])}.", "warning")
            elif value < limit - (1 if unit == "%" or unit == "°C" else 0):
                self._clear(f"host:{key}", f"{title}: back to normal", f"{name}: it is under the limit again.")
        for key in RULES:  # a rule that was switched off, or has no reading, no longer holds an alert
            if key not in seen:
                self.holds[key].since = None
                self._clear(f"host:{key}")
        if (rules.get("address") or {}).get("on"):
            if now - self.address_at >= ADDRESS_EVERY:
                self.address_at = now
                self.check_address(name)
        else:
            self.addresses, self.address_at = {}, 0
        if (rules.get("container") or {}).get("on"):
            self.check_containers(name)
        else:
            self.running = None

    @staticmethod
    def _words(minutes):
        return "1 minute" if minutes == 1 else f"{minutes} minutes" if minutes < 60 else ("an hour" if minutes == 60 else f"{minutes // 60} hours")

    def _alert(self, key, title, message, level, again=False):
        watch = self.app.watch
        with watch.lock:
            if again:
                watch.state["alerted"].pop(key, None)  # each change is told, however long since the last
            if watch.alert(key, title, message, level):
                watch._save()

    def _clear(self, key, title=None, message=None):
        watch = self.app.watch
        with watch.lock:
            if watch.clear(key, title, message):
                watch._save()

    # The outside address ----------------------------------------------------------

    def outside_addresses(self):
        """{who: address} from what Starboard already reads: the No-IP updater's log and each Gluetun's status."""
        found = {}
        cfg = self.app.config.data
        try:
            from . import noip
            n = noip.status(self.app.data_dir)
            if n.get("installed") and n.get("address"):
                found["The No-IP updater"] = n["address"]
        except Exception:  # noqa: BLE001  not installed, or Docker does not answer
            pass
        from . import services
        for s in cfg.get("services") or []:
            if s.get("type") == "gluetun" and s.get("enabled", True) and s.get("url"):
                try:
                    ip = services.vpn_one(s).get("ip")
                except Exception:  # noqa: BLE001
                    ip = ""
                if ip:
                    found[s["name"]] = ip
        return found

    def check_address(self, name, found=None):
        found = self.outside_addresses() if found is None else found
        for who, address in found.items():
            before = self.addresses.get(who)
            if before and before != address:
                key = f"host:address:{who}"
                self._alert(key, f"The outside address changed ({who})", f"{name}: the address {who} shows to the internet is "
                            "not the one it showed before. The address itself is not sent in alerts.", "warning", again=True)
            self.addresses[who] = address

    # Containers --------------------------------------------------------------------

    def check_containers(self, name, listed=None):
        """A container that was running and has stopped with an error or died. Stopped on purpose (exit code 0), resting
        or removed is not an alert."""
        from . import containers
        if listed is None:
            if not containers.available():
                return
            try:
                listed = containers.docker("GET", "/containers/json?all=1")
            except containers.DockerError:
                return
        now_running = {}
        for c in listed:
            n = (c.get("Names") or ["?"])[0].lstrip("/")
            now_running[n] = (c.get("State"), c.get("Status") or "")
        was = self.running
        self.running = {n for n, (state, _) in now_running.items() if state == "running"}
        if was is None:
            return
        for n in was - self.running:
            state, status = now_running.get(n, (None, ""))
            if state is None:
                continue  # removed
            failed = state == "dead" or ("Exited (" in status and "Exited (0)" not in status)
            if failed:
                self._alert(f"host:container:{n}", f"{n} stopped", f"{name}: the container {n} stopped: {status[:80]}.", "problem")
        for n in self.running:
            self._clear(f"host:container:{n}", f"{n} is running again", f"{name}: the container {n} is back.")
