"""Moving Jellyfin's metadata out of its settings folder (DASH-431). Owner, 14 November 2026: "Move the metadata and
make sure its set properly for new installs".

Jellyfin watches its own settings folder, so a large metadata store there (150,881 folders on the owner's server) used
up the computer's folder-watch limit before Films and TV, and real-time monitoring failed. New installs keep it in
CONFIG_DIR/jellyfin-metadata, mounted at /metadata (stack.py, app_setup.jellyfin_first_run). An install made before is
moved the same way, as the owner's server was by hand on 14 November 2026 (watches 261,889 to 2,074):

1. check: Jellyfin is Starboard's (in data/stack/compose.yaml) and has not been moved;
2. stop Jellyfin (60 seconds to finish what it is doing);
3. move data/metadata to CONFIG_DIR/jellyfin-metadata, entry by entry (a rename on the same disk, so quick);
4. leave a link at the old address, data/metadata pointing to /metadata: Jellyfin's database keeps many pictures by
   their full old address (after the hand move, every sampled episode picture was not found until the link was
   added), and the link adds no watches;
5. MetadataPath /metadata in system.xml (a copy of it kept beside it), and the /metadata volume in compose.yaml (the
   file before kept as compose.yaml.before-<time>);
6. start Jellyfin and wait for it to answer;
7. count its folder watches, look for watcher errors in its log, and ask for a few posters to show they still load.

If a step before the start fails, what was moved goes back, the files are put back and Jellyfin starts as it was.
Nothing is deleted: the old folder becomes the link only once it is empty. Runs when Starboard takes Jellyfin over
(after the takeover) or when the person asks, in Settings, Jellyfin."""
import datetime as dt
import json
import os
import re
import shutil
import threading
import time
import urllib.parse

from . import containers, logs, stack

NAME = "jellyfin"
STEPS = [("check", "Checking Jellyfin"), ("stop", "Stopping Jellyfin"), ("move", "Moving its pictures and details"),
         ("link", "Leaving a link at the old address"), ("settings", "Telling Jellyfin where they are"),
         ("start", "Starting Jellyfin"), ("watches", "Counting its folder watches")]
WATCH_COUNT = ("n=0; for f in /proc/[0-9]*/fdinfo/*; do c=$(grep -c '^inotify' \"$f\" 2>/dev/null) && n=$((n+c)); done; "
               "echo \"$n $(cat /proc/sys/fs/inotify/max_user_watches)\"")


def _paths(data_dir):
    """(config dir on the computer, Jellyfin's settings folder, the new metadata folder, puid, pgid)."""
    env = stack.env_values(data_dir)
    cfg = str(env.get("CONFIG_DIR") or "").rstrip("/")
    if not cfg.startswith("/") or ".." in cfg:
        raise ValueError("Install apps has not set the settings folder, so Starboard cannot move Jellyfin's metadata")
    uid, gid = str(env.get("PUID") or "1000"), str(env.get("PGID") or "1000")
    uid, gid = (uid, gid) if uid.isdigit() and gid.isdigit() else ("1000", "1000")
    return cfg, f"{cfg}/jellyfin", f"{cfg}/jellyfin-metadata", uid, gid


def _inspect(name):
    try:
        return containers.docker("GET", f"/containers/{urllib.parse.quote(name, safe='')}/json") or {}
    except containers.DockerError:
        return None


def status(data_dir, name=NAME):
    """{moved, can_move, why, where}: whether Jellyfin's metadata is outside its settings folder already."""
    try:
        with open(os.path.join(stack.folder(data_dir), "compose.yaml"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        text = ""
    in_compose = bool(stack._service_block(text, "jellyfin"))
    info = _inspect(name) if containers.available() else None
    mounted = any(m.get("Destination") == "/metadata" for m in (info or {}).get("Mounts") or [])
    moved = stack.has_jellyfin_metadata(text) or mounted
    why = ("" if in_compose and info is not None and not moved else
           "It is already outside Jellyfin's settings folder" if moved else
           "Starboard does not run Jellyfin here (it is not in Install apps)" if not in_compose else
           "Starboard has no access to Docker here" if not containers.available() else "Jellyfin is not on this computer")
    return {"moved": moved, "can_move": not why, "why": why, "where": "/metadata" if moved else "/config/data/metadata"}


# The job ------------------------------------------------------------------------------------------------------------

_job = {}
_lock = threading.Lock()


def job():
    with _lock:
        return json.loads(json.dumps(_job)) if _job else {}


def _step(step, state, detail=""):
    with _lock:
        for t in _job["tasks"]:
            if t["id"] == step:
                t.update(state=state, detail=str(detail)[:300])
        if state == "working":
            _job["now"] = next(t["label"] for t in _job["tasks"] if t["id"] == step)


def start(data_dir, services=None, name=NAME, project=None, helper=None, wait=None, after=None):
    """Starts the move in the background; returns the job, followed by the page's task dialog."""
    with _lock:
        if _job and not _job.get("finished"):
            raise ValueError("Jellyfin's metadata is already being moved")
        _job.clear()
        _job.update(started=time.time(), finished=False, ok=None, now="", notes=[], error="", log="",
                    tasks=[{"id": k, "label": label, "state": "waiting", "detail": ""} for k, label in STEPS])

    def work():
        try:
            notes = move(data_dir, services, name=name, project=project, helper=helper, wait=wait)
            with _lock:
                _job.update(finished=True, ok=True, notes=notes, now="", title="Jellyfin's metadata is moved",
                            text=" ".join(n.rstrip(".") + "." for n in notes))
        except Exception as e:  # noqa: BLE001  any failure ends the job with words
            logs.event("error", "jellyfin", f"Moving Jellyfin's metadata did not finish: {e}")
            with _lock:
                for t in _job["tasks"]:
                    if t["state"] == "working":
                        t["state"] = "failed"
                    elif t["state"] == "waiting":
                        t["state"] = "skipped"
                _job.update(finished=True, ok=False, error=str(e)[:400], now="", title="Jellyfin's metadata was not moved",
                            text=str(e)[:400])
        if after:
            after(job())
    threading.Thread(target=work, name="jellyfin-metadata", daemon=True).start()
    return job()


def _run(helper, folder, script, binds):
    code, text = (helper or containers._helper)(folder, script, binds)
    return code, text.strip()


def move(data_dir, services=None, name=NAME, project=None, helper=None, wait=None):
    """The move itself, step by step (above). Returns lines of what was done; raises ValueError."""
    q = containers._quote
    project = project or stack.PROJECT
    host = stack.host_folder(data_dir)
    if not host:
        raise ValueError("Starboard cannot see where its apps' Compose file is on the computer")
    if _job:
        _step("check", "working")
    st = status(data_dir, name)
    if not st["can_move"]:
        raise ValueError(st["why"])
    cfg, jf, md, uid, gid = _paths(data_dir)
    old, link = f"{jf}/data/metadata", f"{jf}/data/metadata"
    compose_path = os.path.join(stack.folder(data_dir), "compose.yaml")
    with open(compose_path, encoding="utf-8") as f:
        compose_before = f.read()
    compose_after = stack.add_jellyfin_metadata(compose_before)  # refused here, before anything stops, if it cannot
    binds = [f"{cfg}:{cfg}"]
    code, text = _run(helper, host, f"[ -d {q(jf)} ] && [ -f {q(jf + '/system.xml')} ] && echo ok", binds)
    if code != 0:
        raise ValueError(f"Starboard did not find Jellyfin's settings in {jf}")
    if _job:
        _step("check", "done", f"Its settings are in {jf}")
        _step("stop", "working")
    code, text = _run(helper, host, f"docker stop -t 60 {q(name)} 2>&1", [])
    if code != 0:
        raise ValueError(f"Jellyfin did not stop: {text[-200:]}")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    started_again = False
    try:
        if _job:
            _step("stop", "done")
            _step("move", "working")
        # Entry by entry, so a part-way failure can put each one back. A link there already (moved by hand before
        # its Compose file had the volume) is kept.
        script = (f"set -e; mkdir -p {q(md)}; "
                  f"if [ -d {q(old)} ] && [ ! -L {q(old)} ]; then "
                  f"  if [ -n \"$(ls -A {q(md)})\" ]; then echo 'The new folder {md} is not empty'; exit 3; fi; "
                  f"  for e in {q(old)}/* {q(old)}/.[!.]*; do [ -e \"$e\" ] || [ -L \"$e\" ] || continue; mv \"$e\" {q(md)}/; done; "
                  f"  rmdir {q(old)}; fi; "
                  f"chown {uid}:{gid} {q(md)}; du -sm {q(md)} | cut -f1; find {q(md)} -type d | wc -l")
        code, text = _run(helper, host, script, binds)
        if code != 0:
            raise ValueError(f"The move did not finish: {text[-200:]}")
        size, folders = (text.split() + ["0", "0"])[-2:]
        if _job:
            _step("move", "done", f"About {size} MB in {int(folders):,} folders, now in {md}")
            _step("link", "working")
        code, text = _run(helper, host, f"set -e; [ -L {q(link)} ] || ln -s /metadata {q(link)}; chown -h {uid}:{gid} {q(link)}", binds)
        if code != 0:
            raise ValueError(f"The link was not made: {text[-200:]}")
        if _job:
            _step("link", "done", f"{link} points to /metadata, so pictures saved by their old address still show")
            _step("settings", "working")
        xml = f"{jf}/system.xml"
        script = (f"set -e; cp -p {q(xml)} {q(xml + '.before-' + stamp)}; "
                  f"if grep -q '<MetadataPath' {q(xml)}; then "
                  f"sed -i -e 's#<MetadataPath>[^<]*</MetadataPath>#<MetadataPath>/metadata</MetadataPath>#' "
                  f"-e 's#<MetadataPath */>#<MetadataPath>/metadata</MetadataPath>#' {q(xml)}; "
                  f"else sed -i 's#</ServerConfiguration>#  <MetadataPath>/metadata</MetadataPath>\\n</ServerConfiguration>#' {q(xml)}; fi; "
                  f"grep -c '<MetadataPath>/metadata</MetadataPath>' {q(xml)}")
        code, text = _run(helper, host, script, binds)
        if code != 0 or not text.strip().endswith("1"):
            raise ValueError(f"MetadataPath was not set in system.xml: {text[-200:]}")
        backup = compose_path + f".before-{stamp}"
        shutil.copy2(compose_path, backup)
        with open(compose_path + ".new", "w", encoding="utf-8") as f:
            f.write(compose_after)
        os.chmod(compose_path + ".new", 0o644)
        os.replace(compose_path + ".new", compose_path)
        if _job:
            _step("settings", "done", "MetadataPath is /metadata, and Jellyfin has the /metadata volume")
            _step("start", "working")
        code, text = _run(helper, host, f"docker compose -p {q(project)} --env-file .env -f compose.yaml up -d {q('jellyfin')} 2>&1 | tail -n 5; "
                                        f"docker inspect -f '{{{{.State.Running}}}}' {q(name)}", [])
        if code != 0 or not text.strip().endswith("true"):
            raise ValueError(f"Jellyfin did not start with the new folder: {text[-200:]}")
        started_again = True
    except Exception:
        if not started_again:
            _put_back(helper, host, binds, old, md, jf, stamp, compose_path, compose_before, name, project)
        raise
    up = _wait_answer(services, wait)
    if _job:
        _step("start", "done" if up else "failed", "It answers" if up else "It is running but did not answer within 3 minutes")
        _step("watches", "working")
    notes = [f"Jellyfin's pictures and details are in {md}, outside its settings folder"]
    watches = check_watches(name, helper, host, since=int(time.time()) - 600, wait=wait)
    notes.append(watches["said"])
    posters = check_posters(services)
    if posters:
        notes.append(posters)
    if _job:
        _step("watches", "done" if watches["ok"] else "failed", watches["said"])
    logs.event("info", "jellyfin", "Moved Jellyfin's metadata out of its settings folder. " + " ".join(notes[1:]))
    return notes


def _put_back(helper, host, binds, old, md, jf, stamp, compose_path, compose_before, name, project):
    """A step failed before Jellyfin started again: everything back as it was, and Jellyfin started."""
    q = containers._quote
    script = (f"if [ -L {q(old)} ]; then rm {q(old)}; fi; "  # only the link Starboard made, never a folder
              f"if [ ! -e {q(old)} ] && [ -d {q(md)} ]; then mkdir -p {q(old)}; "
              f"for e in {q(md)}/* {q(md)}/.[!.]*; do [ -e \"$e\" ] || continue; mv \"$e\" {q(old)}/; done; fi; "
              f"[ -f {q(jf + '/system.xml.before-' + stamp)} ] && cp -p {q(jf + '/system.xml.before-' + stamp)} {q(jf + '/system.xml')}; true")
    try:
        _run(helper, host, script, binds)
        with open(compose_path, "w", encoding="utf-8") as f:
            f.write(compose_before)
        _run(helper, host, f"docker start {q(name)} 2>&1 || docker compose -p {q(project)} --env-file .env -f compose.yaml up -d jellyfin 2>&1", [])
    except Exception as e:  # noqa: BLE001  said in the log; the error that stopped the move is the one shown
        logs.error("jellyfin", f"Putting Jellyfin back after the move stopped did not finish: {e}", e)


def _wait_answer(services, wait=None):
    svc = next((s for s in services or [] if s.get("type") == "jellyfin"), None)
    if not svc:
        return True
    from . import app_setup
    until = time.monotonic() + (180 if wait is None else wait)
    while True:
        try:
            app_setup._call(svc["url"], "GET", "/System/Info/Public")
            return True
        except Exception:  # noqa: BLE001  not answering yet
            if time.monotonic() >= until:
                return False
            time.sleep(3)


def check_watches(name=NAME, helper=None, host=None, since=None, wait=None):
    """Jellyfin's folder watches, counted inside its container, with the computer's limit, and any watcher errors
    in its log since `since`. {ok, watches, limit, errors, said}."""
    q = containers._quote
    time.sleep(30 if wait is None else min(wait, 30))  # Jellyfin sets its watches up a little after it answers
    script = (f"docker exec {q(name)} sh -c {q(WATCH_COUNT)}; "
              f"docker logs {'--since ' + str(int(since)) + ' ' if since else ''}{q(name)} 2>&1 | grep -c -i -E 'inotify|error watching|watcher' || true")
    try:
        if not host:
            raise containers.DockerError("no folder for the helper")
        code, text = _run(helper, host, script, [])
    except containers.DockerError as e:
        return {"ok": False, "watches": None, "limit": None, "errors": None, "said": f"Starboard could not count its watches ({e})"}
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if len(nums) < 3:
        return {"ok": False, "watches": None, "limit": None, "errors": None, "said": "Starboard could not count its watches"}
    watches, limit, errors = nums[0], nums[1], nums[2]
    ok = watches < limit * 0.5 and errors == 0
    said = (f"Jellyfin watches {watches:,} folders; the computer allows {limit:,}" +
            (", with no watcher errors in its log" if not errors else f", and its log has {errors} watcher errors"))
    return {"ok": ok, "watches": watches, "limit": limit, "errors": errors, "said": said}


def check_posters(services, sample=8):
    """Asks Jellyfin for a few posters, as the dashboard would; words, or "" when it cannot be asked."""
    from . import app_setup
    svc = next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("api_key")), None)
    if not svc:
        return ""
    h = {"X-Emby-Token": svc["api_key"]}
    try:
        items = (app_setup._call(svc["url"], "GET", f"/Items?Recursive=true&ImageTypes=Primary&Limit={sample}"
                                 "&IncludeItemTypes=Movie,Series,Episode&SortBy=Random", headers=h) or {}).get("Items") or []
    except Exception:  # noqa: BLE001
        return ""
    if not items:
        return ""
    found = 0
    import urllib.request
    for it in items:
        try:
            req = urllib.request.Request(svc["url"].rstrip("/") + f"/Items/{urllib.parse.quote(str(it.get('Id')))}/Images/Primary?maxHeight=60",
                                         headers=h)
            with urllib.request.urlopen(req, timeout=20) as r:  # Jellyfin's own address, from Starboard's apps  # nosec B310
                found += r.status == 200
        except Exception:  # noqa: BLE001
            pass
    return f"{found} of {len(items)} sampled posters load"
