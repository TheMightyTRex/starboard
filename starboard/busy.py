"""What is using the processor now (DASH-558; owner, 23 November 2026, from a look at Monitee's process monitoring).

The heaviest containers and processes by processor and memory, for System, Overview, Busy now. Read only, and only
when the page is opened or Check again is pressed: nothing runs at rest and nothing is kept. It never stops, signals
or changes anything.

How it reads, in order of cost:
- Processor and memory of each container from the host's cgroup files (STARBOARD_CGROUP, the installer's
  "Show each app's processor and memory use" option): two small files per container, read twice about a second apart.
- Without them, with Docker access, Docker's own one-shot statistics, one small call a container, a few at a time,
  each with a time limit and all of them within a deadline.
- Processes from /proc, read twice about a second apart. A Starboard that runs in a container sees only its own
  processes there, so it says so and shows the containers; one that runs on the server itself sees them all.
Every figure is a share of the whole processor, as the Monitor page shows it.
"""
import concurrent.futures as cf
import os
import re
import threading
import time

from . import containers, discovery, sysinfo

TOP = 8              # rows in each list
GAP = 1.0            # seconds between the two readings
DEADLINE = 8.0       # seconds for the whole reading, Docker's statistics included
DOCKER_TIMEOUT = 3   # seconds for one container's statistics
MAX_PIDS = 4000      # processes read at most, so a runaway machine cannot make this long

_lock = threading.Lock()


class Busy(Exception):
    """A reading is already running."""


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _hz():
    try:
        return os.sysconf("SC_CLK_TCK")
    except (AttributeError, ValueError, OSError):
        return 100


# Processes -------------------------------------------------------------------------------------------------------

def _procs():
    """{pid: (name, cpu ticks, resident bytes)} from /proc/<pid>/stat. A process that goes while it is read is skipped."""
    out = {}
    try:
        page = os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, ValueError, OSError):
        page = 4096
    try:
        names = [n for n in os.listdir("/proc") if n.isdigit()][:MAX_PIDS]
    except OSError:
        return out
    for n in names:
        try:
            with open(f"/proc/{n}/stat", "rb") as f:
                raw = f.read(2048).decode("utf-8", "replace")
        except OSError:
            continue
        head, _, rest = raw.rpartition(")")
        fields = rest.split()
        if len(fields) < 22 or "(" not in head:
            continue
        try:
            out[int(n)] = (head.partition("(")[2][:40], int(fields[11]) + int(fields[12]), int(fields[21]) * page)
        except ValueError:
            continue
    return out


def _container_of(pid):
    """The Docker container id a process runs in, from its cgroup, or ''."""
    try:
        with open(f"/proc/{pid}/cgroup", encoding="utf-8", errors="replace") as f:
            text = f.read(2048)
    except OSError:
        return ""
    m = re.search(r"docker[-/]([0-9a-f]{64})", text)
    return m.group(1) if m else ""


def _sees_the_host():
    """True when /proc is the server's own: its first process is not Starboard's container start."""
    try:
        with open("/proc/1/cmdline", "rb") as f:
            first = f.read(200).replace(b"\0", b" ").decode("utf-8", "replace")
    except OSError:
        return False
    return not re.search(r"starboard|python|tini|docker-init|dumb-init|sh -c", first)


# Containers ------------------------------------------------------------------------------------------------------

def _cgroup_sample():
    """{container id: (cpu microseconds, memory bytes)} from the host's cgroup files, or None without them."""
    base = os.path.join(sysinfo.cgroup_dir() or "/nonexistent", "system.slice")
    try:
        entries = os.listdir(base)
    except OSError:
        return None
    out = {}
    for d in entries:
        if not (d.startswith("docker-") and d.endswith(".scope")):
            continue
        where = os.path.join(base, d)
        try:
            stat = dict(line.split() for line in sysinfo._read(os.path.join(where, "cpu.stat")).splitlines() if " " in line)
            mem = int(sysinfo._read(os.path.join(where, "memory.current")).strip() or 0)
            inactive = dict(line.split() for line in sysinfo._read(os.path.join(where, "memory.stat")).splitlines() if " " in line)
            out[d[7:-6]] = (int(stat.get("usage_usec", 0)), max(0, mem - int(inactive.get("inactive_file", 0))))
        except (OSError, ValueError):
            continue
    return out


def _docker_one(cid):
    """One container's counters from Docker's one-shot statistics: (container cpu, all cpu, memory bytes), or None."""
    try:
        s = containers.docker("GET", f"/containers/{cid}/stats?stream=false&one-shot=true", timeout=DOCKER_TIMEOUT)
        cpu = s["cpu_stats"]
        mem = s["memory_stats"]
        inactive = (mem.get("stats") or {}).get("inactive_file", (mem.get("stats") or {}).get("total_inactive_file", 0))
        return (int(cpu["cpu_usage"]["total_usage"]), int(cpu["system_cpu_usage"]), max(0, int(mem.get("usage", 0)) - int(inactive)))
    except (containers.DockerError, KeyError, TypeError, ValueError):
        return None


def _docker_sample(running, deadline):
    """{container id: counters} for every running container, a few at a time, each with a time limit; and how many
    did not answer before the deadline."""
    pool = cf.ThreadPoolExecutor(8)
    jobs = {pool.submit(_docker_one, cid): cid for cid, _ in running}
    done, late = cf.wait(jobs, timeout=max(0.5, deadline - time.monotonic()))
    out = {jobs[j]: j.result() for j in done if j.result()}
    for j in late:
        j.cancel()
    pool.shutdown(wait=False, cancel_futures=True)
    return out, len(late)


# What Starboard thinks it is -------------------------------------------------------------------------------------

def _think(name, services):
    """A short note on what a container is, from what Starboard knows: its apps, its plug-ins, itself."""
    if not name:
        return ""
    if name == os.environ.get("HOSTNAME") or name.startswith("starboard"):
        return "Starboard itself"
    for s in services:
        if s.get("container") == name or (_norm(s.get("name", "")) and _norm(s.get("name", "")) == _norm(name)):
            return f"{s.get('name')}, one of your apps in Starboard"
    if name.startswith("plugin-"):
        return "A plug-in's container"
    flat = _norm(name)
    for key, row in discovery.CATALOGUE.items():
        if _norm(key) in flat:
            return f"{row[0]}, not added to Starboard yet"
    return "Not one of Starboard's apps"


def _think_process(name, services):
    flat = _norm(name)
    if len(flat) < 4:
        return ""
    for s in services:
        if _norm(s.get("name", "")) and (_norm(s["name"]) in flat or flat in _norm(s["name"])):
            return f"{s['name']}, one of your apps in Starboard"
    for key, row in discovery.CATALOGUE.items():
        if _norm(key) in flat or flat in _norm(key):
            return f"{row[0]}, not added to Starboard yet"
    return ""


# The reading -----------------------------------------------------------------------------------------------------

def read(services, gap=GAP):
    """The busiest containers and processes right now. Raises Busy when another reading is running."""
    if not _lock.acquire(blocking=False):
        raise Busy("A reading is already running. Wait a moment, then try again")
    try:
        return _read(services or [], gap)
    finally:
        _lock.release()


def _read(services, gap):
    started = time.monotonic()
    cores = os.cpu_count() or 1
    hz = _hz()
    names = sysinfo._container_names() if containers.available() else {}
    host = _sees_the_host()
    p1 = _procs()
    c1 = _cgroup_sample()
    notes = []
    box = []  # (name, cpu share, memory)
    source = None
    running = []
    d1 = {}
    if c1 is None and containers.available():
        # Docker's one-shot statistics, read twice a second apart: each call is quick, so a few run at once, within the deadline.
        try:
            running = [(c["Id"], (c["Names"] or ["/"])[0].lstrip("/")) for c in containers.docker("GET", "/containers/json", timeout=DOCKER_TIMEOUT)]
        except containers.DockerError:
            running = []
        d1, _ = _docker_sample(running, started + DEADLINE / 2)
        source = "docker"
    elif c1 is not None:
        source = "cgroup"
    t1 = time.monotonic()
    wait = gap - (time.monotonic() - t1)
    if wait > 0 and (source or host):
        time.sleep(wait)
    t2 = time.monotonic()
    span = max(0.2, t2 - t1)
    if source == "cgroup":
        c2 = _cgroup_sample() or {}
        for cid, (usec, mem) in c2.items():
            before = c1.get(cid)
            share = max(0.0, (usec - before[0]) / (span * 1e6 * cores) * 100) if before else 0.0
            box.append((names.get(cid, cid[:12]), share, mem))
    elif source == "docker":
        d2, late = _docker_sample(running, started + DEADLINE)
        for cid, name in running:
            if cid in d1 and cid in d2:
                used, system = d2[cid][0] - d1[cid][0], d2[cid][1] - d1[cid][1]
                box.append((name, max(0.0, 100.0 * used / system) if system > 0 else 0.0, d2[cid][2]))
        if len(box) < len(running):
            notes.append(f"{len(running) - len(box)} of {len(running)} containers did not answer in time and are left out")
    elif not containers.available():
        notes.append("Docker access is off, so the containers are not listed. The installer's option for Docker access adds them")
    p2 = _procs() if host else {}
    rows = []
    if host:
        for pid, (name, ticks, rss) in p2.items():
            before = p1.get(pid)
            share = max(0.0, (ticks - before[1]) / (span * hz * cores) * 100) if before else 0.0
            rows.append({"pid": pid, "name": name, "cpu": share, "memory": rss})
        busiest = sorted(rows, key=lambda r: (-r["cpu"], -r["memory"]))[:TOP]
        biggest = sorted(rows, key=lambda r: -r["memory"])[:TOP]
        keep = {r["pid"]: r for r in busiest + biggest}
        rows = sorted(keep.values(), key=lambda r: (-r["cpu"], -r["memory"]))[:TOP + 4]
        for r in rows:
            cid = _container_of(r["pid"])
            r["container"] = names.get(cid, cid[:12]) if cid else ""
            r["note"] = _think(r["container"], services) if r["container"] else (
                "Starboard itself" if r["pid"] == os.getpid() else _think_process(r["name"], services))
    else:
        notes.append("Starboard runs in a container, so it can read only its own processes, not the server's. "
                     "The containers show what the server is doing")
    box.sort(key=lambda c: (-c[1], -c[2]))
    top = {c[0]: c for c in box[:TOP]}
    for c in sorted(box, key=lambda c: -c[2])[:TOP // 2]:  # the biggest in memory too, even when quiet
        top.setdefault(c[0], c)
    listed = sorted(top.values(), key=lambda c: (-c[1], -c[2]))[:TOP + 4]
    return {"at": time.time(), "seconds": round(time.monotonic() - started, 2), "span": round(span, 2), "cores": cores,
            "memory_total": _memory_total(), "source": source, "host": host, "notes": notes, "containers_total": len(box),
            "containers": [{"name": n, "cpu": round(s, 2), "memory": m, "note": _think(n, services)} for n, s, m in listed],
            "processes": [{**r, "cpu": round(r["cpu"], 2)} for r in rows], "processes_total": len(p2)}


def _memory_total():
    for line in sysinfo._read("/proc/meminfo").splitlines():
        if line.startswith("MemTotal:"):
            try:
                return int(line.split()[1]) * 1024
            except (IndexError, ValueError):
                return 0
    return 0
