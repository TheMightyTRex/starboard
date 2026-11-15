"""Update Starboard from its own page (DASH-417): Update now in Settings, Updates, and, when activated, automatic
Starboard updates in quiet hours. Both run the same update.sh as a person on the server would, so the backup, the
health check and the way back are the same.

How it runs:
- In Docker (the installer's usual way), Starboard starts a short-lived helper container that outlives Starboard's
  own restart. It runs as the owner of the Starboard folder (the uid and gid of its data folder, checked against the
  git checkout before anything happens), never as root, with the Docker socket's group so it can run docker compose,
  and the host's network so update.sh can ask Starboard whether it answers.
- The helper's image is starboard-updater, made once on this computer from the pinned docker:cli image Starboard
  already uses, with bash and git added when the image is made (UPDATER_DOCKERFILE). Nothing is installed when an
  update runs. update.sh needs no Python inside it (it uses wget when python3 is not there).
- Without Docker (./install.sh --native), Starboard runs update.sh with systemd-run --user, so it lives outside
  Starboard's own service and survives its restart.

Progress: update.sh's lines go to data/self-update.log, written whole again after each line, so the log is still
there when update.sh goes back and puts the backup of data/ in place. The page reads it through
GET /api/self-update and reconnects while Starboard restarts. data/self-update.json holds who started the update,
from which version to which, and how it ended. The automatic update does not try a version again after it failed,
until someone chooses Update now.
"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess  # nosec B404: systemd-run only, with a fixed list of arguments
import tarfile
import threading
import time

from . import containers, logs

STATE = "self-update.json"
LOG = "self-update.log"
STALE = 60 * 60  # an update that has said nothing for an hour has stopped
RELEASE = re.compile(r"^v\d+\.\d+\.\d+$")
UPDATER_DOCKERFILE = (f"FROM {containers.HELPER_IMAGE}\n"
                      "RUN apk add --no-cache bash git\n"
                      'LABEL starboard.updater-image="1"\n')
UPDATER_IMAGE = "starboard-updater:" + hashlib.sha256(UPDATER_DOCKERFILE.encode()).hexdigest()[:12]

# The steps the page shows, in order, and the update.sh lines that start each (its "== " lines).
STEPS = [("checking", "Checking for the new version"), ("backing-up", "Backing up your settings"),
         ("downloading", "Getting the new version"), ("building", "Building it"),
         ("restarting", "Restarting Starboard"), ("answering", "Checking that it answers")]
STARTS = [(re.compile(r"^== (Preparing the update|Fetching releases|What changed)"), "checking"),
          (re.compile(r"^== Backing up your settings"), "backing-up"),
          (re.compile(r"^== Installing "), "downloading"),
          (re.compile(r"^== Building "), "building"),
          (re.compile(r"^== Restarting Starboard"), "restarting"),
          (re.compile(r"^== Checking that Starboard answers"), "answering")]

# The script the helper runs. The version and the folder come in as environment variables, never in the script.
WRAPPER = r"""set -u
cd "$STARBOARD_FOLDER" || exit 1
log=data/self-update.log
tmp="$(mktemp)"
write() { cp "$tmp" "$log.new" 2>/dev/null && mv -f "$log.new" "$log" 2>/dev/null; return 0; }
say() { printf '%s\n' "$1" >> "$tmp"; write; }
run() {
  if [ ! -f update.sh ] || [ ! -d .git ]; then
    echo "Stopped: this Starboard was not installed with the installer, so it updates as the ready-made image's help says"; return 1
  fi
  if [ "$(stat -c %u .git)" != "$(id -u)" ]; then
    echo "Stopped: the Starboard folder belongs to another user, so it cannot be updated from the page. Run ./update.sh on the server"; return 1
  fi
  bash ./update.sh --to "$STARBOARD_UPDATE_TO"
}
say "== Preparing the update"
run 2>&1 | while IFS= read -r line; do say "$line"; done
code=${PIPESTATUS[0]}
say "@@ finished $code"
rm -f "$tmp"
exit "$code"
"""

_lock = threading.Lock()


class Refused(Exception):
    """Starboard cannot start an update now; the message says why, in words for the page."""


# The record and the log -------------------------------------------------------------------------------------------

def _path(data_dir, name):
    return os.path.join(data_dir, name)


def load(data_dir):
    try:
        with open(_path(data_dir, STATE), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save(data_dir, data):
    tmp = _path(data_dir, STATE) + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, _path(data_dir, STATE))


def read_log(data_dir, limit=64 * 1024):
    try:
        with open(_path(data_dir, LOG), "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - limit))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def parse(text):
    """What update.sh's lines say: the step it is on, each step's state, and how it ended.

    outcome is None while it runs, then "updated", "up-to-date", "went-back" (the new version did not start and the
    one before is back), "refused" (it stopped before changing anything, such as for changed files) or "failed"."""
    order = [k for k, _ in STEPS]
    at, going_back, outcome, reason, back_to, to, code = None, False, None, "", "", "", None
    for line in text.splitlines():
        line = line.rstrip()
        for pattern, key in STARTS:
            if pattern.match(line) and not going_back:
                if at is None or order.index(key) >= order.index(at):
                    at = key
        if m := re.match(r"^== Updated to (\S+)", line):
            outcome, to = "updated", m.group(1)
        elif m := re.match(r"^== The new version did not start\. Going back to (\S+)", line):
            going_back, back_to = True, m.group(1)
            reason = "The new version did not answer within a minute of starting"
        elif m := re.match(r"^Back on (\S+) with your settings restored", line):
            outcome, back_to = "went-back", m.group(1)
        elif line.startswith("Starboard is still not starting"):
            outcome, reason = "failed", "Starboard did not start again after going back"
        elif line.startswith("Already up to date"):
            outcome = "up-to-date"
        elif line.startswith("Stopped: "):
            reason = line[len("Stopped: "):].strip()
        elif m := re.match(r"^Available: (\S+)", line):
            to = to or m.group(1)
        elif m := re.match(r"^@@ finished (\d+)", line):
            code = int(m.group(1))
    if code is not None and outcome is None:
        if code == 0:
            outcome = "updated"
        else:
            # Stopped before the new version was put in place: nothing changed.
            outcome = "refused" if at in (None, "checking", "backing-up") and not going_back else "failed"
            reason = reason or "update.sh stopped without saying why"
    steps = []
    for key, label in STEPS:
        if outcome in ("updated", "up-to-date"):
            state = "done"
        elif at is None:
            state = "waiting"
        else:
            i, here = order.index(key), order.index(at)
            state = "done" if i < here else ("now" if i == here else "waiting")
            if i == here and outcome in ("refused", "failed", "went-back"):
                state = "stopped"
        steps.append({"key": key, "label": label, "state": state})
    return {"at": at, "going_back": going_back and outcome is None, "outcome": outcome, "reason": reason,
            "back_to": back_to, "to": to, "finished": code is not None, "code": code, "steps": steps}


# Rules -------------------------------------------------------------------------------------------------------------

def version_key(v):
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", str(v or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def newer(tag, version):
    a, b = version_key(tag), version_key(version)
    return bool(a and b and a > b)


def in_quiet_hours(cfg_data, now):
    """Starboard's download hours when they are set, otherwise 01:00 to 06:00: the same quiet hours as Reelix's
    automatic update and plug-in jobs (plugin_life._in_quiet_hours)."""
    hours = (cfg_data or {}).get("download_hours") or {}
    start, end = (int(hours.get("start", 1)), int(hours.get("end", 6))) if hours.get("enabled") else (1, 6)
    h = now.hour
    return start <= h < end if start < end else (h >= start or h < end)


def last_said(record, data_dir=None):
    """When the running update last wrote a line (its log's time), or when it started."""
    t = record.get("touched") or record.get("started") or 0
    if data_dir:
        try:
            t = max(t, os.path.getmtime(_path(data_dir, LOG)))
        except OSError:
            pass
    return t


def running(record, now=None, data_dir=None):
    """True while an update is under way (and has not gone quiet for an hour)."""
    now = now or time.time()
    return record.get("state") == "running" and now - last_said(record, data_dir) < STALE


def automatic_decision(cfg_data, now, latest, current, record):
    """What the automatic update does now: ("update", tag) or ("wait", the reason in words)."""
    if not cfg_data.get("starboard_auto_update"):
        return "wait", "Automatic Starboard updates are deactivated"
    if not in_quiet_hours(cfg_data, now):
        return "wait", "Waiting for the quiet hours"
    if not latest or not RELEASE.match(latest) or not newer(latest, current):
        return "wait", "Starboard is up to date"
    if record.get("skip") == latest:
        return "wait", f"{latest} did not install last time, so it waits for Update now in Settings, Updates"
    if running(record, now.timestamp()):
        return "wait", "An update is already running"
    return "update", latest


# Where and as whom it runs -----------------------------------------------------------------------------------------

def in_docker():
    return os.path.exists("/.dockerenv")


def plan(data_dir, root):
    """How this Starboard can update itself: a dict with "how" ("docker" or "native"), the Starboard folder on the
    computer, and for Docker the user, group and the Docker socket's group. Raises Refused when it cannot."""
    if in_docker():
        if not containers.available():
            raise Refused("Starboard has no Docker access, so it cannot update itself. Run ./update.sh on the server")
        from . import stack
        found = stack.host_folder(data_dir)
        if not found or not found.endswith("/stack"):
            raise Refused("Starboard could not find its own folder on the server. Run ./update.sh on the server")
        data_src = found[:-len("/stack")]
        if os.path.basename(data_src) != "data":
            raise Refused("This Starboard was not installed with the installer, so it updates as the ready-made image's help says")
        st = os.stat(data_dir)
        if st.st_uid == 0:
            raise Refused("Starboard's folder belongs to root, and Starboard never updates as root. Run ./update.sh on the server")
        return {"how": "docker", "folder": os.path.dirname(data_src), "uid": st.st_uid, "gid": st.st_gid,
                "socket_gid": os.stat(containers.socket_path()).st_gid}
    if not (shutil.which("systemd-run") and shutil.which("bash") and shutil.which("git")):
        raise Refused("This computer has no systemd-run, bash or git for Starboard to update with. Run ./update.sh on the server")
    git = os.path.join(root, ".git")
    if not os.path.isdir(git) or not os.path.isfile(os.path.join(root, "update.sh")):
        raise Refused("This Starboard was not installed with the installer, so it cannot update itself here")
    if os.stat(git).st_uid != os.getuid():
        raise Refused("The Starboard folder belongs to another user. Run ./update.sh on the server as that user")
    return {"how": "native", "folder": root}


def helper_body(p, to, image=UPDATER_IMAGE):
    """The helper container: the folder at the same path (so docker compose sees what it would see on the server),
    the Docker socket with its group, the host's network for the health check, removed by Docker when it ends."""
    return {"Image": image, "Cmd": ["bash", "-c", WRAPPER], "WorkingDir": p["folder"], "User": f"{p['uid']}:{p['gid']}",
            "Env": [f"STARBOARD_UPDATE_TO={to}", f"STARBOARD_FOLDER={p['folder']}", "HOME=/tmp"],
            "Labels": {"starboard.updater": "1", "starboard.self-update": "1"},
            "HostConfig": {"Binds": [f"{containers.socket_path()}:/var/run/docker.sock", f"{p['folder']}:{p['folder']}"],
                           "GroupAdd": [str(p["socket_gid"])], "NetworkMode": "host", "AutoRemove": True,
                           "SecurityOpt": ["no-new-privileges:true"]}}


def native_command(p, to, unit):
    return ["systemd-run", "--user", "--collect", "--quiet", f"--unit={unit}", f"--setenv=STARBOARD_UPDATE_TO={to}",
            f"--setenv=STARBOARD_FOLDER={p['folder']}", "bash", "-c", WRAPPER]


def _build_updater():
    """Makes the starboard-updater image once on this computer (bash and git on the pinned docker:cli image)."""
    try:
        containers.docker("GET", f"/images/{UPDATER_IMAGE}/json")
        return
    except containers.DockerError:
        pass
    try:
        containers.ensure_image()  # DASH-438: the updater is built on the pinned helper, downloaded first if missing
    except containers.DockerError as e:
        raise Refused(str(e)) from None
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo("Dockerfile")
        info.size = len(UPDATER_DOCKERFILE)
        tar.addfile(info, io.BytesIO(UPDATER_DOCKERFILE.encode()))
    c = containers._UnixConnection(600)
    try:
        c.request("POST", f"/build?t={UPDATER_IMAGE}&rm=1&forcerm=1", body=buf.getvalue(), headers={"Content-Type": "application/x-tar"})
        r = c.getresponse()
        out = r.read(4 * 1024 * 1024).decode("utf-8", "replace")
    except OSError as e:
        raise Refused(f"The updater could not be made: {e}") from None
    finally:
        c.close()
    if r.status >= 400 or '"error"' in out:
        said = re.findall(r'"error"\s*:\s*"([^"]*)"', out)
        raise Refused(f"The updater could not be made: {(said[-1] if said else out[-200:]).strip()}")


def launch(p, to):
    """Starts update.sh where it outlives Starboard's restart. Returns at once."""
    if p["how"] == "native":
        subprocess.run(native_command(p, to, f"starboard-self-update-{int(time.time())}"), check=True, timeout=30,  # nosec B603
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return
    _build_updater()
    cid = containers.docker("POST", f"/containers/create?name=starboard-self-update-{int(time.time() * 1000)}", helper_body(p, to))["Id"]
    containers.docker("POST", f"/containers/{cid}/start")


# Starting, finishing, and the page ---------------------------------------------------------------------------------

def start(app, to, by="you"):
    """Starts an update to the release `to` (vX.Y.Z, newer than this version). by is "you", "automatic" or "api"
    (an API key with the updates scope, DASH-424)."""
    if not RELEASE.match(str(to or "")):
        raise Refused("Only a release, such as v0.18.0, can be installed from here")
    if not newer(to, app.version):
        raise Refused(f"{to} is not newer than the version you have, {app.version}. To go back, run ./update.sh --to on the server")
    with _lock:
        record = load(app.data_dir)
        if running(record, data_dir=app.data_dir):
            raise Refused("An update is already running. Wait for it to finish")
        p = plan(app.data_dir, getattr(app, "root", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        now = time.time()
        if by in ("you", "api"):
            record.pop("skip", None)  # Update now (or the API, DASH-424) tries again a version the automatic update stopped trying
        record.update({"state": "running", "by": by, "from": app.version, "to": to, "started": now, "touched": now,
                       "finished": None, "outcome": None, "reason": "", "how": p["how"]})
        save(app.data_dir, record)
        with open(os.open(_path(app.data_dir, LOG), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            f.write("== Preparing the update\n")
    logs.event("info", "updates", f"Starboard update to {to} started ({ {'automatic': 'automatic', 'api': 'from the API'}.get(by, 'Update now')})")
    try:
        launch(p, to)
    except (Refused, containers.DockerError, OSError, subprocess.SubprocessError) as e:
        with _lock:
            record.update({"state": "refused", "finished": time.time(), "outcome": "refused", "reason": str(e)[:300]})
            if by == "automatic":
                record["skip"] = to
            save(app.data_dir, record)
        logs.event("error", "updates", f"Starboard update to {to} could not start: {e}")
        raise Refused(str(e)) from None
    _follow(app)
    return status(app)


WORDS = {
    "updated": ("Starboard is updated", "Starboard {to} is installed and answering."),
    "up-to-date": ("Starboard is up to date", "You already have {to}."),
    "went-back": ("The update did not work, so Starboard went back", "Starboard went back to {back_to}, with your settings as they were. {reason}."),
    "refused": ("Starboard was not updated", "{reason}."),
    "failed": ("The update stopped", "{reason}. See System, Logs, or run ./update.sh on the server."),
}


def plain_reason(reason):
    """update.sh's reasons, said for the page and the alert."""
    if reason.startswith("files in this folder have been changed"):
        return ("Files in the Starboard folder have been changed since it was installed, so nothing was updated. On the "
                "server, keep your changes elsewhere, then run git checkout -- . in the Starboard folder, and choose Update now again")
    return reason[:1].upper() + reason[1:]


def words(outcome, record, parsed):
    title, text = WORDS.get(outcome, WORDS["failed"])
    vals = {"to": record.get("to") or parsed.get("to") or "the new version", "back_to": parsed.get("back_to") or "v" + str(record.get("from") or ""),
            "reason": plain_reason(parsed.get("reason") or record.get("reason") or "update.sh stopped without saying why").rstrip(".")}
    return title, text.format(**vals)


def finish(app, record=None, parsed=None):
    """Once update.sh has ended: records how, writes a log line and an alert either way. Returns the record."""
    with _lock:
        record = record if record is not None else load(app.data_dir)
        if record.get("state") != "running":
            return record
        parsed = parsed or parse(read_log(app.data_dir))
        stale = not parsed["finished"] and time.time() - last_said(record, app.data_dir) >= STALE
        if not parsed["finished"] and not stale:
            return record
        outcome = parsed["outcome"] if parsed["finished"] else "failed"
        if stale:
            parsed = dict(parsed, reason="The update said nothing for an hour")
        record.update({"state": outcome, "outcome": outcome, "finished": time.time(), "reason": parsed["reason"]})
        if parsed["back_to"]:
            record["back_to"] = parsed["back_to"]
        if outcome in ("refused", "failed", "went-back"):
            record["skip"] = record.get("to")  # the automatic update does not try it again until Update now
        save(app.data_dir, record)
    title, text = words(outcome, record, parsed)
    ok = outcome in ("updated", "up-to-date")
    logs.event("info" if ok else "error", "updates", f"{title}: {text}")
    watch = getattr(app, "watch", None)
    if watch:
        try:
            watch.alert(f"starboard-update:{record.get('to')}:{int(record.get('started') or 0)}", title, text, "info" if ok else "problem")
        except Exception as e:  # noqa: BLE001  the alert is a help, never a stop
            logs.error("updates", f"The update alert was not sent: {e}", e)
    return record


def _follow(app):
    """While an update runs, one thread looks at its log every 10 seconds, so it is finished and alerted even with
    no page open. It ends with the update (and starts again after Starboard's restart, from App)."""
    def loop():
        while True:
            time.sleep(10)
            record = load(app.data_dir)
            if record.get("state") != "running":
                return
            parsed = parse(read_log(app.data_dir))
            if parsed["finished"] or not running(record, data_dir=app.data_dir):
                finish(app, record, parsed)
                return
    threading.Thread(target=loop, name="self-update", daemon=True).start()


def resume(app):
    """At Starboard's start: an update that was running (Starboard restarted in the middle of it) is followed again."""
    if load(app.data_dir).get("state") == "running":
        _follow(app)


def status(app):
    """For the page: what is set, whether Update now can be offered, and the running or last update."""
    record = finish(app)
    parsed = parse(read_log(app.data_dir)) if record.get("state") else None
    latest = app.latest_release()
    can, why = True, ""
    try:
        plan(app.data_dir, getattr(app, "root", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Refused as e:
        can, why = False, str(e)
    except OSError as e:
        can, why = False, f"Starboard could not check its folder: {e}"
    out = {"current": app.version, "latest": latest, "newer": bool(latest and newer(latest, app.version)),
           "can": can, "why": why, "automatic": bool(app.config.data.get("starboard_auto_update")),
           "skip": record.get("skip"), "running": running(record, data_dir=app.data_dir)}
    if record.get("state"):
        out["update"] = {k: record.get(k) for k in ("state", "by", "from", "to", "started", "finished", "outcome", "back_to")}
        out["update"]["steps"] = parsed["steps"]
        out["update"]["going_back"] = parsed["going_back"]
        out["update"]["lines"] = [ln for ln in read_log(app.data_dir).splitlines() if not ln.startswith("@@")][-40:]
        if record.get("state") != "running":
            out["update"]["title"], out["update"]["text"] = words(record.get("outcome"), record, parsed)
    return out


def automatic(app, now=None):
    """The automatic update's job (jobs.py, starboardupdate): one look, and an update when one is due."""
    import datetime as dt
    now = now or dt.datetime.now()
    record = finish(app)
    action, said = automatic_decision(app.config.data, now, app.latest_release(), app.version, record)
    if action != "update":
        return said
    try:
        start(app, said, by="automatic")
    except Refused as e:
        with _lock:
            record = load(app.data_dir)
            if not running(record, data_dir=app.data_dir):
                record["skip"] = said  # not tried again until Update now
                save(app.data_dir, record)
        logs.event("error", "updates", f"The automatic Starboard update did not start: {e}")
        watch = getattr(app, "watch", None)
        if watch:
            watch.alert(f"starboard-update:{said}:refused", "Starboard was not updated", f"{e}.")
        return f"The update to {said} did not start: {e}"
    return f"Installing {said}; Starboard restarts in a moment"


def job(app):
    """The running or last update in the shape the pages' task dialog follows (settings.js, taskJob): each step with
    its state, what is happening now, and the result at the end."""
    s = status(app)
    u = s.get("update")
    if not u:
        return {"tasks": [], "finished": True, "ok": None, "notes": ["No update has run from this page yet"]}
    states = {"done": "done", "now": "working", "waiting": "waiting", "stopped": "failed"}
    finished = u["state"] != "running"
    tasks = []
    for step in u["steps"]:
        state = states[step["state"]]
        if finished and state in ("waiting", "working") and u["outcome"] not in ("updated", "up-to-date"):
            state = "skipped"
        tasks.append({"id": step["key"], "label": step["label"], "state": state})
    if u["going_back"] or u.get("outcome") == "went-back":
        back = u.get("back_to") or ("v" + str(u.get("from") or ""))
        tasks.append({"id": "going-back", "label": f"Going back to {back}",
                      "state": "done" if u.get("outcome") == "went-back" else "failed" if finished else "working"})
    working = next((t for t in tasks if t["state"] == "working"), None)
    now = ""
    if working and not finished:
        now = working["label"]
        if working["id"] in ("restarting", "answering", "going-back"):
            now += ". Starboard is away for about a minute; this reconnects by itself"
    out = {"tasks": tasks, "finished": finished, "now": now, "to": u.get("to"), "from": u.get("from"),
           "outcome": u.get("outcome"), "log": "\n".join(u.get("lines") or [])}
    if finished:
        out["ok"] = True if u["outcome"] in ("updated", "up-to-date") else None if u["outcome"] == "went-back" else False
        out["title"], out["text"] = u.get("title"), u.get("text")
        out["notes"] = [u.get("text") or ""]
    return out
