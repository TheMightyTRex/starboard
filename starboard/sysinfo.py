"""Load, memory, uptime and free space, read from /proc without extra privileges."""

import os
import shutil


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
