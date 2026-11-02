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


FS_NAMES = {"fuse.mergerfs": "mergerfs", "fuseblk": "NTFS", "ntfs3": "NTFS", "ntfs": "NTFS", "vfat": "FAT32",
            "exfat": "exFAT", "fuse.sshfs": "SSHFS", "nfs4": "NFS", "nfs": "NFS", "cifs": "SMB", "zfs": "ZFS",
            "fuse.shfs": "Unraid", "overlay": "overlay"}


def filesystem(path):
    """The filesystem a folder lives on, from the mount table (the longest mount point that holds it)."""
    best, kind = "", ""
    real = os.path.realpath(path)
    for line in _read("/proc/self/mountinfo").splitlines():
        left, _, right = line.partition(" - ")
        fields = left.split()
        if len(fields) < 5 or not right:
            continue
        point = fields[4].replace("\\040", " ")
        if (real == point or real.startswith(point.rstrip("/") + "/")) and len(point) >= len(best):
            best, kind = point, right.split()[0]
    return FS_NAMES.get(kind, kind)


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
            disks.append({"label": label, "total": usage.total, "used": usage.used, "free": usage.free,
                          "filesystem": filesystem(path)})
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


# Per-app use -----------------------------------------------------------------------------
# Optional: the host's cgroup files mounted read-only (STARBOARD_CGROUP, the installer asks). Each container's
# processor time and memory are two small files; names come from Docker when Starboard has Docker access,
# otherwise the container's short ID is shown.

_names = {"at": 0, "map": {}}


def cgroup_dir():
    return os.environ.get("STARBOARD_CGROUP", "")


def _container_names():
    if time.time() - _names["at"] > 300:
        _names["at"] = time.time()
        try:
            from . import containers
            if containers.available():
                _names["map"] = {c["id"]: c["name"] for c in containers.containers(light=True)}
        except Exception:
            pass
    return _names["map"]


def app_usage():
    if not cgroup_dir():
        return None
    base = os.path.join(cgroup_dir(), "system.slice")
    try:
        entries = os.listdir(base)
    except OSError:
        return None
    names = _container_names()
    out = []
    for d in entries:
        if not (d.startswith("docker-") and d.endswith(".scope")):
            continue
        cid = d[7:-6]
        stat = dict(line.split() for line in _read(os.path.join(base, d, "cpu.stat")).splitlines() if " " in line)
        mem = _read(os.path.join(base, d, "memory.current")).strip()
        out.append({"name": names.get(cid, cid[:12]), "cpu_usec": int(stat.get("usage_usec", 0)), "memory": int(mem or 0)})
    return out


def monitor(apps=True):
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
        "apps": app_usage() if apps else None,
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
            # The drive's own recent temperature log (SCT), newest last, when it keeps one.
            "sct": _sct(d),
        })
    events = []
    for name in ("events.log", "alerts.log"):
        lines = _read(os.path.join(folder, name)).splitlines()
        events.extend(line for line in lines if line.strip())
    events.sort(reverse=True)
    requests = os.path.join(folder, "requests")
    return {"configured": True, "disks": disks, "events": events[:40], "devices": _devices(folder),
            "can_read": os.path.isdir(requests) and os.access(requests, os.W_OK),
            "reading": os.path.exists(os.path.join(requests, "read"))}


def _sct(d):
    h = d.get("ata_sct_temperature_history") or {}
    temps = [t for t in (h.get("table") or []) if isinstance(t, (int, float))]
    if not temps:
        return None
    return {"minutes": h.get("logging_interval_minutes") or 1, "temps": temps[-96:]}


def _devices(folder):
    """Drives and partitions from lsblk.json, which the SMART job saves: which are mounted, and their file systems."""
    import json
    try:
        with open(os.path.join(folder, "lsblk.json"), encoding="utf-8") as f:
            tree = json.load(f).get("blockdevices") or []
    except (OSError, ValueError):
        return None
    out = []
    for disk in tree:
        if disk.get("type") != "disk":
            continue
        parts = []
        for part in disk.get("children") or [disk]:
            mounts = [m for m in (part.get("mountpoints") or []) if m]
            parts.append({"name": part.get("name"), "size": part.get("size"), "fs": part.get("fstype") or "",
                          "label": part.get("label") or "", "mounted": mounts[:3]})
        out.append({"name": disk.get("name"), "model": (disk.get("model") or "").strip(), "serial": disk.get("serial") or "",
                    "size": disk.get("size"), "parts": parts})
    return out


def request_disk_read():
    folder = smart_dir()
    try:
        with open(os.path.join(folder, "requests", "read"), "w"):
            pass
    except OSError:
        raise ValueError("Starboard cannot ask for a reading: the SMART job's requests folder is not writable") from None


class DiskTemps:
    """Each disk's temperature once an hour for 30 days (data/disk-temps.json), recorded whenever disk health is read:
    by the Disk health page, or by watching in the background. About 720 numbers per disk."""
    KEEP = 30 * 86400

    def __init__(self, data_dir):
        import threading
        self.path = os.path.join(data_dir, "disk-temps.json")
        self.lock = threading.Lock()

    def _load(self):
        import json
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def record(self, disks):
        import json
        now = time.time()
        with self.lock:
            data = self._load()
            changed = False
            for d in disks:
                key = d.get("serial") or d.get("device")
                if not key or d.get("temperature") is None:
                    continue
                rows = data.setdefault(key, [])
                if not rows or now - rows[-1][0] >= 3000:
                    rows.append([round(now), d["temperature"]])
                    data[key] = [r for r in rows if r[0] > now - self.KEEP]
                    changed = True
            if changed:
                tmp = self.path + ".tmp"
                with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
                    json.dump(data, f)
                os.replace(tmp, self.path)

    def get(self):
        with self.lock:
            return self._load()


# What is using the space -------------------------------------------------------------
# On demand only (a button on System, Storage): walks each folder's top-level folders once and keeps the answer in
# data/usage.json. A file with several hard links (a seeding torrent that is also in the library) counts once.

class Usage:
    def __init__(self, data_dir):
        import threading
        self.path = os.path.join(data_dir, "usage.json")
        self.lock = threading.Lock()
        self.running = False

    def get(self):
        import json
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        data["running"] = self.running
        return data

    def start(self, disks):
        import threading
        with self.lock:
            if self.running:
                return
            self.running = True
        threading.Thread(target=self._scan, args=(disks,), name="usage", daemon=True).start()

    def _scan(self, disks):
        import json
        started = time.time()
        out = {"started": started, "folders": []}
        seen = set()
        try:
            for label, root in disks:
                entries = []
                try:
                    tops = sorted(os.scandir(root), key=lambda e: e.name.lower())
                except OSError:
                    continue
                for top in tops:
                    total = 0
                    if top.is_symlink():
                        continue
                    if top.is_file():
                        st = top.stat(follow_symlinks=False)
                        total = st.st_blocks * 512
                    else:
                        for base, dirs, files in os.walk(top.path):
                            for name in files:
                                try:
                                    st = os.lstat(os.path.join(base, name))
                                except OSError:
                                    continue
                                if st.st_nlink > 1:
                                    key = (st.st_dev, st.st_ino)
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                total += st.st_blocks * 512
                    entries.append({"name": top.name, "bytes": total})
                entries.sort(key=lambda e: e["bytes"], reverse=True)
                out["folders"].append({"label": label, "items": entries[:30]})
            out["finished"] = time.time()
            tmp = self.path + ".tmp"
            with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
                json.dump(out, f)
            os.replace(tmp, self.path)
        finally:
            self.running = False


# History -------------------------------------------------------------------------
# One reading a minute for the last 24 hours, kept in memory and saved to the data folder every 10 minutes,
# so the System charts can look back. About 1,440 small readings; nothing leaves the server.

class History:
    """Readings for the System charts. Off, or less often, in Settings, Performance: the thread runs only while
    it is on, and ends when it is turned off (after saving)."""
    KEEP = 24 * 3600

    def __init__(self, data_dir, settings=None):
        import collections
        import threading
        self.path = os.path.join(data_dir, "history.json")
        self.points = collections.deque()
        self.lock = threading.Lock()
        self.settings = settings or (lambda: {"history": True, "history_every": 60})
        self.wake = threading.Event()
        self.thread = None
        self._load()
        self._previous = None
        self._last_save = time.time()
        self.ensure()

    @property
    def INTERVAL(self):
        return int(self.settings().get("history_every", 60))

    def ensure(self):
        import threading
        if not self.settings().get("history", True):
            self.wake.set()  # a running thread notices and ends
            return
        if self.thread and self.thread.is_alive():
            self.wake.set()
            return
        self._previous = monitor(apps=False)
        self.thread = threading.Thread(target=self._run, name="history", daemon=True)
        self.thread.start()

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
        now = monitor(apps=False)  # the charts need the whole server, not each app
        prev, self._previous = self._previous or now, now
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
            self.wake.wait(self.INTERVAL)
            self.wake.clear()
            if not self.settings().get("history", True):
                self._save()
                self.thread = None
                return
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


def self_usage():
    """Starboard's own memory and processor use, and its threads, for Settings, Performance."""
    import threading
    status = {}
    for line in _read("/proc/self/status").splitlines():
        k, _, v = line.partition(":")
        status[k] = v.strip()
    stat = _read("/proc/self/stat").rsplit(")", 1)[-1].split()
    ticks = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
    cpu_seconds = (int(stat[11]) + int(stat[12])) / ticks if len(stat) > 12 else 0
    started = float(stat[19]) / ticks if len(stat) > 19 else 0
    boot = float((_read("/proc/uptime").split() or ["0"])[0])
    alive = max(1.0, boot - started)
    names = sorted(t.name for t in threading.enumerate())
    return {"memory": int(status.get("VmRSS", "0 kB").split()[0]) * 1024, "cpu_seconds": round(cpu_seconds, 1),
            "running_seconds": int(alive), "cpu_percent": round(cpu_seconds / alive * 100, 3), "threads": names}
