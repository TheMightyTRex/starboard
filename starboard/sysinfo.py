"""Load, memory, uptime and free space, read from /proc without extra privileges."""

import os
import shutil
import time


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def snapshot(disk_paths):
    load = _read("/proc/loadavg").split()
    mem = {}
    for line in _read("/proc/meminfo").splitlines():
        name, _, rest = line.partition(":")
        if rest.strip():
            mem[name] = int(rest.split()[0]) * 1024
    uptime = _read("/proc/uptime").split()
    disks = []
    for label, path in disk_paths:
        try:
            usage = shutil.disk_usage(path)
            disks.append({"label": label, "total": usage.total, "used": usage.used, "free": usage.free})
        except OSError:
            disks.append({"label": label, "missing": True})
    return {
        "cpus": os.cpu_count(),
        "load": [float(x) for x in load[:3]] if load else [],
        "memory": {"total": mem.get("MemTotal", 0), "available": mem.get("MemAvailable", 0)},
        "uptime_seconds": float(uptime[0]) if uptime else None,
        "disks": disks,
    }


def disk_paths_from_env():
    """STARBOARD_DISKS="Media=/disks/media,System=/disks/root"; nothing is shown when it is not set."""
    raw = os.environ.get("STARBOARD_DISKS", "")
    pairs = []
    for part in raw.split(","):
        label, sep, path = part.partition("=")
        if sep and label.strip() and path.strip():
            pairs.append((label.strip()[:40], path.strip()))
    return pairs


# Monitor ---------------------------------------------------------------------
# Raw counters only; the page works out rates between two readings, so the server keeps no state.

def _cpu_times():
    cores, total = [], None
    for line in _read("/proc/stat").splitlines():
        if not line.startswith("cpu"):
            continue
        parts = line.split()
        values = [int(x) for x in parts[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        pair = [sum(values), idle]
        if parts[0] == "cpu":
            total = pair
        else:
            cores.append(pair)
    return total, cores


def _cpu_model():
    for line in _read("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return ""


SKIP_IFACE = ("lo", "veth", "docker", "br-", "virbr", "tailscale", "tun", "wg")


def _net_counters():
    out = {}
    for line in _read("/proc/net/dev").splitlines()[2:]:
        name, _, rest = line.partition(":")
        name = name.strip()
        if not name or name.startswith(SKIP_IFACE):
            continue
        fields = rest.split()
        out[name] = [int(fields[0]), int(fields[8])]
    return out


def _disk_counters():
    import re
    out = {}
    for line in _read("/proc/diskstats").splitlines():
        f = line.split()
        if len(f) > 9 and re.match(r"^(sd[a-z]+|nvme\d+n\d+|vd[a-z]+|mmcblk\d+)$", f[2]):
            out[f[2]] = [int(f[5]) * 512, int(f[9]) * 512]
    return out


def _temperatures():
    temps = []
    base = "/sys/class/hwmon"
    try:
        chips = sorted(os.listdir(base))
    except OSError:
        return temps
    for chip in chips:
        folder = os.path.join(base, chip)
        name = _read(os.path.join(folder, "name")).strip() or chip
        try:
            files = sorted(os.listdir(folder))
        except OSError:
            continue
        for f in files:
            if f.startswith("temp") and f.endswith("_input"):
                raw = _read(os.path.join(folder, f)).strip()
                if raw.lstrip("-").isdigit():
                    label = _read(os.path.join(folder, f.replace("_input", "_label"))).strip() or name
                    temps.append({"chip": name, "label": label, "c": round(int(raw) / 1000, 1)})
    return temps[:24]


def monitor():
    total, cores = _cpu_times()
    mem = {}
    for line in _read("/proc/meminfo").splitlines():
        name, _, rest = line.partition(":")
        if rest.strip():
            mem[name] = int(rest.split()[0]) * 1024
    load = _read("/proc/loadavg").split()
    uptime = _read("/proc/uptime").split()
    return {
        "time": time.time(),
        "cpu": {"model": _cpu_model(), "threads": os.cpu_count(), "total": total, "cores": cores,
                "load": [float(x) for x in load[:3]] if load else []},
        "memory": {"total": mem.get("MemTotal", 0), "available": mem.get("MemAvailable", 0),
                   "cached": mem.get("Cached", 0) + mem.get("Buffers", 0),
                   "swap_total": mem.get("SwapTotal", 0), "swap_free": mem.get("SwapFree", 0)},
        "net": _net_counters(),
        "disks": _disk_counters(),
        "temps": _temperatures(),
        "uptime_seconds": float(uptime[0]) if uptime else None,
    }


# Network -----------------------------------------------------------------------

def interfaces():
    """Each network interface with its IPv4 address (ioctl, no extra privileges) and its counters."""
    import fcntl
    import socket
    import struct
    counters = _net_counters()
    out = []
    for _, name in socket.if_nameindex():
        if name.startswith(SKIP_IFACE):
            continue
        address = ""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                packed = fcntl.ioctl(s.fileno(), 0x8915, struct.pack("256s", name[:15].encode()))  # SIOCGIFADDR
                address = socket.inet_ntoa(packed[20:24])
        except OSError:
            pass
        state = _read(f"/sys/class/net/{name}/operstate").strip()
        speed = _read(f"/sys/class/net/{name}/speed").strip()
        out.append({"name": name, "address": address, "state": state or "unknown",
                    "speed_mbps": int(speed) if speed.lstrip("-").isdigit() and int(speed) > 0 else None,
                    "received": counters.get(name, [0, 0])[0], "sent": counters.get(name, [0, 0])[1]})
    return out


# Disk health -------------------------------------------------------------------
# Reads smartctl's JSON reports (smartctl -x -j) from a folder that a job on the host writes, so Starboard
# itself needs no access to the disks. STARBOARD_SMART_DIR says where; nothing is shown when it is not set.

WATCH = {5: "Reallocated sectors", 196: "Reallocation events", 197: "Sectors waiting to be checked",
         198: "Unreadable sectors", 187: "Uncorrectable errors", 188: "Command timeouts",
         199: "Cable (CRC) errors", 10: "Spin-up retries", 184: "End-to-end errors"}


def smart_dir():
    return os.environ.get("STARBOARD_SMART_DIR", "")


def disk_health():
    import glob
    import json
    folder = smart_dir()
    if not folder or not os.path.isdir(folder):
        return {"configured": False, "disks": [], "events": []}
    files = sorted(set(glob.glob(os.path.join(folder, "current", "*.json"))) or set(glob.glob(os.path.join(folder, "*.json"))))
    disks = []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if "smart_status" not in d and "model_name" not in d:
            continue
        attrs = {a.get("id"): a for a in (d.get("ata_smart_attributes") or {}).get("table", [])}
        problems = [{"name": label, "value": attrs[i]["raw"]["value"]}
                    for i, label in WATCH.items() if i in attrs and attrs[i].get("raw", {}).get("value", 0) > 0]
        nvme = d.get("nvme_smart_health_information_log") or {}
        if nvme.get("media_errors"):
            problems.append({"name": "Media errors", "value": nvme["media_errors"]})
        log = d.get("ata_smart_self_test_log") or {}
        tests = (log.get("extended") or {}).get("table") or (log.get("standard") or {}).get("table") or []
        if not tests:  # NVMe disks keep their own log
            tests = [{"type": {"string": t.get("self_test_code", {}).get("string", "")},
                      "status": {"string": t.get("self_test_result", {}).get("string", "")},
                      "lifetime_hours": t.get("power_on_hours")}
                     for t in (d.get("nvme_self_test_log") or {}).get("table") or []]
        last_test = tests[0] if tests else None
        disks.append({
            "model": d.get("model_name") or d.get("model_family") or "Disk",
            "serial": d.get("serial_number", ""),
            "device": (d.get("device") or {}).get("name", ""),
            "capacity": (d.get("user_capacity") or {}).get("bytes"),
            "passed": (d.get("smart_status") or {}).get("passed"),
            "temperature": (d.get("temperature") or {}).get("current"),
            "temperature_limit": (d.get("temperature") or {}).get("op_limit_max"),
            "hours": (d.get("power_on_time") or {}).get("hours"),
            "problems": problems,
            "last_test": {"type": last_test.get("type", {}).get("string", ""),
                          "result": last_test.get("status", {}).get("string", ""),
                          "hours": last_test.get("lifetime_hours")} if last_test else None,
            "checked": os.path.getmtime(path),
        })
    events = []
    for name in ("events.log", "alerts.log"):
        lines = _read(os.path.join(folder, name)).splitlines()
        events.extend(line for line in lines if line.strip())
    events.sort(reverse=True)
    return {"configured": True, "disks": disks, "events": events[:40]}


# History -------------------------------------------------------------------------
# One reading a minute for the last 24 hours, kept in memory and saved to the data folder every 10 minutes,
# so the System charts can look back. About 1,440 small readings; nothing leaves the server.

class History:
    INTERVAL = 60
    KEEP = 24 * 3600

    def __init__(self, data_dir):
        import collections
        import threading
        self.path = os.path.join(data_dir, "history.json")
        self.points = collections.deque()
        self.lock = threading.Lock()
        self._load()
        self._previous = monitor()
        self._last_save = time.time()
        threading.Thread(target=self._run, daemon=True).start()

    def _load(self):
        import json
        try:
            with open(self.path, encoding="utf-8") as f:
                saved = json.load(f)
            cutoff = time.time() - self.KEEP
            self.points.extend(p for p in saved if isinstance(p, dict) and p.get("t", 0) > cutoff)
        except (OSError, ValueError):
            pass

    def _save(self):
        import json
        tmp = self.path + ".tmp"
        with self.lock:
            data = list(self.points)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
        os.replace(tmp, self.path)

    @staticmethod
    def _busy(now, before):
        if not now or not before:
            return 0.0
        total = now[0] - before[0]
        return max(0.0, 100 * (1 - (now[1] - before[1]) / total)) if total > 0 else 0.0

    def sample(self):
        now = monitor()
        prev, self._previous = self._previous, now
        dt = max(1.0, now["time"] - prev["time"])

        def rate(key, index):
            a = sum(v[index] for v in now[key].values())
            b = sum(v[index] for v in prev[key].values())
            return max(0.0, (a - b) / dt)

        temps = now["temps"]
        pkg = next((t["c"] for t in temps if any(k in t["label"].lower() for k in ("package", "tctl", "tdie"))), None)
        if pkg is None and temps:
            pkg = temps[0]["c"]
        mem = now["memory"]
        point = {
            "t": round(now["time"]),
            "cpu": round(self._busy(now["cpu"]["total"], prev["cpu"]["total"]), 1),
            "mem": round(100 * (mem["total"] - mem["available"]) / mem["total"], 1) if mem["total"] else 0,
            "load": now["cpu"]["load"][0] if now["cpu"]["load"] else 0,
            "rx": round(rate("net", 0)), "tx": round(rate("net", 1)),
            "read": round(rate("disks", 0)), "write": round(rate("disks", 1)),
            "temp": pkg,
        }
        with self.lock:
            self.points.append(point)
            cutoff = time.time() - self.KEEP
            while self.points and self.points[0]["t"] < cutoff:
                self.points.popleft()

    def _run(self):
        while True:
            time.sleep(self.INTERVAL)
            try:
                self.sample()
                if time.time() - self._last_save > 600:
                    self._save()
                    self._last_save = time.time()
            except Exception as e:  # keep recording whatever one reading does
                print(f"[starboard] History reading failed: {e}", flush=True)

    def get(self, hours):
        cutoff = time.time() - hours * 3600
        with self.lock:
            points = [p for p in self.points if p["t"] >= cutoff]
        # At most 360 points: average neighbours together for the longer ranges.
        step = max(1, -(-len(points) // 360))
        if step == 1:
            return points
        out = []
        for i in range(0, len(points), step):
            chunk = points[i:i + step]
            merged = {"t": chunk[-1]["t"]}
            for key in ("cpu", "mem", "load", "rx", "tx", "read", "write", "temp"):
                values = [p[key] for p in chunk if p.get(key) is not None]
                merged[key] = round(sum(values) / len(values), 1) if values else None
            out.append(merged)
        return out
