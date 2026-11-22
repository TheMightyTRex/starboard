"""Hardware transcoding check (DASH-515): which encoder Jellyfin can use, and why one cannot.

Only when someone presses Test now on System, Overview: nothing runs at rest. Starboard runs a 2 second synthetic
clip (ffmpeg's own test picture, written to nowhere) through Jellyfin's own ffmpeg, with Docker's exec on the Jellyfin
container, as the user Jellyfin itself runs as, so a missing device or permission shows exactly as it would for a
film. Read-only: no media is opened, nothing is written, no setting is changed. One check at a time.
"""

import re
import shlex
import threading
import time

from . import containers

JELLYFIN_FFMPEG = "/usr/lib/jellyfin-ffmpeg/ffmpeg"
DRI_DIR = "/dev/dri"  # the tests point these at a folder of their own
SYS_DRM = "/sys/class/drm"
TEST_SECONDS = 2
STEP_TIMEOUT = 25  # seconds, per test; ffmpeg is also stopped inside the container by `timeout`
MAX_NODES = 4
VENDORS = {"0x8086": "intel", "0x1002": "amd", "0x10de": "nvidia"}
NAMES = {"vaapi": "VAAPI", "qsv": "Intel Quick Sync", "nvenc": "NVIDIA NVENC", "software": "Software (the processor)"}
ENCODER_NAMES = {"vaapi": "h264_vaapi", "qsv": "h264_qsv", "nvenc": "h264_nvenc", "software": "libx264"}

_lock = threading.Lock()
_last = {"result": None}


class CheckError(Exception):
    """Something that stops the whole check, in words for the owner."""


# What runs inside the container ---------------------------------------------------------------------------------

PROBE = r"""
F=%(jf)s; [ -x "$F" ] || F=$(command -v ffmpeg 2>/dev/null)
echo "FFMPEG=$F"
[ -n "$F" ] || exit 0
echo "VERSION=$("$F" -version 2>&1 | head -n 1)"
echo "DRI=$([ -d %(dri)s ] && echo yes || echo no)"
for n in %(dri)s/renderD*; do
  [ -e "$n" ] || continue
  b=$(basename "$n")
  if [ -r "$n" ] && [ -w "$n" ]; then a=ok; else a=denied; fi
  echo "NODE=$n gid=$(stat -c %%g "$n" 2>/dev/null) access=$a vendor=$(cat %(sys)s/$b/device/vendor 2>/dev/null)"
done
echo "NVIDIA=$(ls %(dri)s/../nvidiactl %(dri)s/../nvidia0 2>/dev/null | tr '\n' ' ')"
echo "GROUPS=$(id -G 2>/dev/null)"
"$F" -hide_banner -encoders 2>/dev/null | grep -oE 'h264_(vaapi|qsv|nvenc)|libx264' | sort -u | sed 's/^/ENC=/'
"""

FFMPEG_BASE = "{f} -hide_banner -nostdin -loglevel error -threads 2 -f lavfi -i testsrc2=size=1280x720:rate=30 -t " + str(TEST_SECONDS)

def _command(kind, ffmpeg, node=""):
    """The test for one encoder, as a shell line. The hardware ones put the device before the input, as ffmpeg needs."""
    f = shlex.quote(ffmpeg)
    base = FFMPEG_BASE.format(f=f)
    # The device is opened before the input, as ffmpeg needs
    pre = f"{f} -hide_banner -nostdin -loglevel error -threads 2"
    tail = f"-f lavfi -i testsrc2=size=1280x720:rate=30 -t {TEST_SECONDS}"
    if kind in ("vaapi", "qsv"):
        init = f"-init_hw_device vaapi=va:{shlex.quote(node)}"
        if kind == "qsv":
            init += " -init_hw_device qsv=qs@va -filter_hw_device qs"
            filt = "-vf format=nv12,hwupload=extra_hw_frames=64 -c:v h264_qsv"
        else:
            init += " -filter_hw_device va"
            filt = "-vf format=nv12,hwupload -c:v h264_vaapi"
        line = f"{pre} {init} {tail} {filt} -f null -"
    elif kind == "nvenc":
        line = f"{base} -c:v h264_nvenc -f null -"
    else:
        line = f"{base} -c:v libx264 -preset ultrafast -f null -"
    return f"timeout {STEP_TIMEOUT} {line} 2>&1"


# Finding the Jellyfin container and its user -------------------------------------------------------------------------

def _simple(text):
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def find_container(services, listing):
    """The Jellyfin container: the one named in Jellyfin's settings, else one called jellyfin."""
    names = [c["name"] for c in listing]
    for s in services:
        if s.get("type") == "jellyfin":
            if s.get("container") in names:
                return s["container"]
            for n in names:
                if _simple(n) in (_simple(s.get("id")), _simple(s.get("name"))):
                    return n
    for n in names:
        if _simple(n) == "jellyfin":
            return n
    return None


def run_user(info):
    """The user Jellyfin's own processes run as. LinuxServer's image starts as root and runs Jellyfin as abc
    (PUID and PGID); other images set a user. Nothing set: the container's default."""
    conf = info.get("Config") or {}
    if conf.get("User"):
        return conf["User"]
    env = dict(e.split("=", 1) for e in conf.get("Env") or [] if "=" in e)
    return "abc" if "PUID" in env else ""


def _strip(text):
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text or "").replace("\r", "")


def docker_exec(name, user, script, timeout=STEP_TIMEOUT + 10):
    """Runs a shell script in a running container and returns (exit code, output)."""
    body = {"AttachStdout": True, "AttachStderr": True, "Tty": True, "Cmd": ["sh", "-c", script]}
    if user:
        body["User"] = user
    made = containers.docker("POST", f"/containers/{name}/exec", body)
    out = containers.docker("POST", f"/exec/{made['Id']}/start", {"Detach": False, "Tty": True}, raw=True, timeout=timeout)
    state = containers.docker("GET", f"/exec/{made['Id']}/json") or {}
    return state.get("ExitCode", 1), _strip((out or b"").decode("utf-8", "replace"))


# Reading the answers --------------------------------------------------------------------------------------------

def parse_probe(text):
    p = {"ffmpeg": "", "version": "", "dri": False, "nodes": [], "nvidia": "", "groups": [], "encoders": set()}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("FFMPEG="):
            p["ffmpeg"] = line[7:].strip()
        elif line.startswith("VERSION="):
            p["version"] = line[8:].strip()[:120]
        elif line.startswith("DRI="):
            p["dri"] = line[4:] == "yes"
        elif line.startswith("NODE="):
            m = re.match(r"NODE=(\S+/renderD\d+) gid=(\d*) access=(\w+) vendor=(\S*)", line)
            if m:
                p["nodes"].append({"path": m.group(1), "gid": m.group(2), "ok": m.group(3) == "ok", "vendor": VENDORS.get(m.group(4), "")})
        elif line.startswith("NVIDIA="):
            p["nvidia"] = line[7:].strip()
        elif line.startswith("GROUPS="):
            p["groups"] = line[7:].split()
        elif line.startswith("ENC="):
            p["encoders"].add(line[4:])
    p["nodes"] = p["nodes"][:MAX_NODES]
    return p


NOISE = re.compile(r"shader cache|terminating thread|task finished|nothing was written|error while opening encoder|"
                   r"could not open encoder|error sending frames|^\s*$", re.I)


def clean(text):
    """ffmpeg's answer without the lines that are always there (a shader cache warning, its closing lines)."""
    return "\n".join(x.strip() for x in _strip(text).splitlines() if x.strip() and not NOISE.search(x))


def _last_line(text):
    lines = clean(text).splitlines()
    return "\n".join(x[:200] for x in lines[:2])


def explain(kind, output, probe, node=None, container=""):
    """Why a test failed, and the fix, in plain words: (why, fix)."""
    low = clean(output).lower()
    where = f"in the {container} container" if container else "in Jellyfin's container"
    if kind in ("vaapi", "qsv"):
        if not probe["dri"] or not probe["nodes"]:
            return ("Jellyfin cannot see a graphics chip: there is no /dev/dri " + where + ".",
                    "Pass the graphics chip to Jellyfin. In Install apps, choose the graphics chip, or add the line "
                    "/dev/dri:/dev/dri under devices for Jellyfin in compose.yaml, then recreate the container. "
                    "If this computer has no graphics chip of its own, software conversion is the only choice.")
        if "no usable encoding" in low or "function not implemented" in low or "unsupported" in low and kind == "vaapi":
            vendor = (node or {}).get("vendor")
            if vendor == "nvidia":
                return ("This graphics chip is an NVIDIA one, and VAAPI cannot encode on it.", "Use NVENC with the NVIDIA driver, or software conversion.")
            return ("The graphics driver started, but this chip cannot encode H.264 video through VAAPI. Older chips cannot.",
                    "Use software conversion, or a newer graphics chip. If the chip is recent, update Jellyfin's image so its driver is current.")
        if node and not node["ok"] or "permission denied" in low:
            gid = (node or {}).get("gid") or "the number shown by ls -n /dev/dri"
            return (f"Jellyfin's user may not open {(node or {}).get('path', 'the graphics device')}.",
                    f"Add the device's group to Jellyfin: under group_add in compose.yaml add \"{gid}\" (the group that owns "
                    "/dev/dri/renderD128 on the server), then recreate the container.")
        if kind == "qsv" and ("unknown encoder" in low or "no such file" in low and "qsv" in low):
            return ("This Jellyfin build has no Quick Sync support.", "Use VAAPI instead, or update Jellyfin's image.")
        if kind == "qsv" and ("mfx" in low or "qsv" in low or "unsupported" in low or "device creation failed" in low):
            return ("Quick Sync did not start on this chip. It needs an Intel graphics chip and its media driver.",
                    "Use VAAPI, which works on Intel and AMD, or update Jellyfin's image so its media driver is current.")
        if "va_opendriver" in low or "failed to initialise vaapi" in low or "failed to initialize vaapi" in low or "no va display" in low \
                or "libva" in low or "init_hw_device" in low or "vaapi" in low:
            return ("The graphics driver inside Jellyfin could not start for this chip. The driver is missing or too old.",
                    "Update Jellyfin's image (Settings, Updates). A very new chip may need a newer image than the one installed. "
                    "On AMD, the image needs the Mesa driver; on Intel, the media driver.")
    if kind == "nvenc":
        if not probe["nvidia"]:
            return ("No NVIDIA card is passed to Jellyfin " + where + ".",
                    "Install the NVIDIA Container Toolkit on the server, then give Jellyfin the card: runtime: nvidia and the "
                    "variable NVIDIA_VISIBLE_DEVICES=all, and recreate the container. Without an NVIDIA card, use VAAPI or software.")
        if "libcuda" in low or "cannot load" in low or "no nvenc capable" in low or "driver" in low:
            return ("Jellyfin sees the NVIDIA card but its driver is not available inside the container.",
                    "Install or update the NVIDIA driver and the NVIDIA Container Toolkit on the server, restart Docker, then "
                    "recreate Jellyfin with runtime: nvidia.")
    if "unknown encoder" in low or "encoder not found" in low:
        return ("This Jellyfin build does not include that encoder.", "Update Jellyfin's image, or use another encoder.")
    if "timed out" in low or low.strip() == "":
        return ("The test did not finish in time.", "Try again when the server is less busy. If it keeps happening, Jellyfin's container may be short of memory.")
    return ("The test failed.", "Details: " + (_last_line(output) or "no message from ffmpeg") + ". Copy this into a support request if it does not make sense.")


def _step(result, kind, ok, device="", seconds=None, why="", fix="", detail=""):
    result["encoders"].append({"key": kind, "name": NAMES[kind], "encoder": ENCODER_NAMES[kind], "status": "works" if ok else "fails",
                               "device": device, "seconds": seconds, "why": why, "fix": fix, "detail": detail})


def _skip(result, kind, why, fix=""):
    result["encoders"].append({"key": kind, "name": NAMES[kind], "encoder": ENCODER_NAMES[kind], "status": "skipped",
                               "device": "", "seconds": None, "why": why, "fix": fix, "detail": ""})


def summarise(result):
    works = [e for e in result["encoders"] if e["status"] == "works"]
    hardware = [e for e in works if e["key"] != "software"]
    if hardware:
        names = ", ".join(dict.fromkeys(e["name"] for e in hardware))
        return "ok", f"Hardware conversion works: {names}. In Jellyfin, Dashboard, Playback, Transcoding, choose it so films use it."
    if works:
        return "software", ("Only software conversion works. Jellyfin can convert video with the processor, which is slower and uses more "
                            "power. The reasons for each hardware choice are below.")
    return "none", "No encoder worked. Jellyfin cannot convert video here, so anything that needs conversion will not play."


# The check ------------------------------------------------------------------------------------------------------

def check(services, *, listing=None, inspect=None, exec_fn=None, clock=time.monotonic):
    """The whole check. listing, inspect and exec_fn are for tests; by default they use Docker."""
    if not _lock.acquire(blocking=False):
        raise CheckError("A check is already running. Wait for it to finish")
    try:
        if exec_fn is None and not containers.available():
            raise CheckError("Starboard cannot reach Docker, so it cannot run a test inside Jellyfin. Turn Docker control on in the installer (./install.sh --docker)")
        try:
            listing = listing if listing is not None else containers.containers(light=True)
        except containers.DockerError as e:
            raise CheckError(str(e)) from None
        name = find_container(services, listing)
        if not name:
            raise CheckError("Starboard could not find Jellyfin's container. Add Jellyfin in Settings, Apps, and give its container name if it is not called jellyfin")
        try:
            info = (inspect or (lambda n: containers.docker("GET", f"/containers/{n}/json")))(name) or {}
        except containers.DockerError as e:
            raise CheckError(str(e)) from None
        if not (info.get("State") or {}).get("Running", True):
            raise CheckError("Jellyfin's container is not running. Start Jellyfin, then test again")
        user = run_user(info)
        run = exec_fn or (lambda script: docker_exec(name, user, script))
        result = {"container": name, "user": user or "the container's default", "clip": f"{TEST_SECONDS} second test picture, written to nowhere",
                  "encoders": [], "checked_at": int(time.time())}
        try:
            code, text = run(PROBE % {"jf": shlex.quote(JELLYFIN_FFMPEG), "dri": shlex.quote(DRI_DIR), "sys": shlex.quote(SYS_DRM)})
        except containers.DockerError as e:
            raise CheckError(f"Docker would not run the test inside Jellyfin: {e}") from None
        probe = parse_probe(text)
        if not probe["ffmpeg"]:
            raise CheckError("Jellyfin's container has no ffmpeg that Starboard can find (looked for /usr/lib/jellyfin-ffmpeg/ffmpeg)")
        result["ffmpeg"] = probe["version"]
        result["devices"] = [{"path": n["path"], "vendor": n["vendor"], "usable": n["ok"]} for n in probe["nodes"]]
        started = clock()

        def attempt(kind, node=None):
            t = clock()
            try:
                code, out = run(_command(kind, probe["ffmpeg"], node["path"] if node else ""))
            except containers.DockerError as e:
                code, out = 1, f"timed out or Docker said: {e}"
            took = round(clock() - t, 1)
            if code == 0:
                _step(result, kind, True, node["path"] if node else "", took)
            else:
                why, fix = explain(kind, out, probe, node, name)
                _step(result, kind, False, node["path"] if node else "", took, why, fix, _last_line(out))

        for kind in ("vaapi", "qsv"):
            if f"h264_{kind}" not in probe["encoders"]:
                if kind == "qsv" and probe["nodes"] and not any(n["vendor"] == "intel" for n in probe["nodes"]):
                    _skip(result, kind, "Quick Sync is for Intel graphics chips; this computer's is not Intel.")
                else:
                    _skip(result, kind, "This Jellyfin build does not include that encoder.", "Update Jellyfin's image.")
                continue
            if not probe["nodes"]:
                why, fix = explain(kind, "", probe, None, name)
                _step(result, kind, False, "", None, why, fix)
                continue
            if kind == "qsv":
                nodes = [n for n in probe["nodes"] if n["vendor"] == "intel"]
                if not nodes:
                    _skip(result, kind, "Quick Sync is for Intel graphics chips; this computer's is not Intel.")
                    continue
            else:
                nodes = probe["nodes"]
            before = len(result["encoders"])
            for n in nodes:
                attempt(kind, n)
                if result["encoders"][-1]["status"] == "works":
                    break
            # one row for the encoder: the one that worked, else the first that failed
            rows = result["encoders"][before:]
            keep = next((r for r in rows if r["status"] == "works"), rows[0])
            result["encoders"][before:] = [keep]
        if "h264_nvenc" in probe["encoders"] or probe["nvidia"]:
            attempt("nvenc")
        else:
            why, fix = explain("nvenc", "", probe, None, name)
            _skip(result, "nvenc", "No NVIDIA card is passed to Jellyfin.", fix)
        attempt("software")
        result["seconds"] = round(clock() - started, 1)
        result["state"], result["summary"] = summarise(result)
        _last["result"] = result
        return result
    finally:
        _lock.release()


def last():
    """The last result of this run of Starboard, or None: kept in memory only, so nothing is stored at rest."""
    return _last["result"]
