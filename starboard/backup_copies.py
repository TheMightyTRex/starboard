"""Copies off this computer (DASH-380, owner, 13 November 2026: "Start working on all the recommended plugins", the
stack comparison's recommendation 5): after each Full without media backup, Starboard copies the new encrypted file to
one other place and keeps only the newest N there, so a failed disk, a theft or a fire does not take every copy (the
3-2-1 rule: three copies, two kinds of storage, one somewhere else).

The other place, chosen in Settings, General, Backup/Logs, Copies off this computer:
- Another disk: a USB disk or a second disk in this computer, as a folder under the usual places (/mnt, /media...).
- A network share: SMB (Windows, a NAS) or NFS. Docker's own local volume driver mounts it for the moment of the copy,
  so no container needs extra rights, then the volume is let go (the share's files stay).
- A cloud remote with rclone: the person's own remote and its part of rclone.conf. rclone runs in a short-lived helper
  container (rclone's image, pinned by digest), the only copy that has network access.

Nothing runs between copies: no thread, no timer. A copy is made at the end of a full backup, in the backup's own
thread, or when the person chooses Copy the newest now. Each copy is checked by size after it is made. Only files
named as Starboard names full backups are ever pruned at the other place.

The passwords (the share's, rclone's config) are kept in Starboard's own folder, readable by Starboard only, and are
never in a backup (full_backup.STARBOARD_SKIP) or sent back to the browser.
"""
import json
import os
import re
import secrets as _random  # this module has its own secrets(): the share's password and rclone's config
import socket
import threading
import time

from . import folders, full_backup

KINDS = ("off", "disk", "smb", "nfs", "rclone")
SETTINGS = "backup-copies.json"
SECRET = "backup-copies-secret.json"
STATUS = "backup-copies-status.json"
TESTED = "backup-copies-test.json"  # the last Test connection, so the page shows it when opened again
WORK = "backup-copy-work"
RCLONE_IMAGE = "rclone/rclone:1.75.2@sha256:2687085f718d3c628f7fdfb77c52a1d344332aed543110bb88088f2c70d43eb5"
KEEP_DEFAULT = 5
TEST_LIMIT = 120  # Test connection: 2 minutes at most
SMB_RE = re.compile(r"^//([A-Za-z0-9.-]{1,253}|\[[0-9A-Fa-f:]+\])/([^/\s\\,]{1,80})((?:/[^/\s\\,]{1,255}){0,20})$")
NFS_RE = re.compile(r"^([A-Za-z0-9.-]{1,253}):(/[^\s,\\]{0,500})$")
REMOTE_RE = re.compile(r"^([A-Za-z0-9_.][A-Za-z0-9_. -]{0,62}):([^\s\x00]{0,500})$")
BACKUP_GLOB = r"^starboard-full-[0-9-]+(-pictures)?\.starboard$"

_lock = threading.Lock()


class CopyError(Exception):
    pass


def _q(text):
    return full_backup._q(text)


# Settings -------------------------------------------------------------------------------------------------------------

def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, dict) else default
    except (OSError, ValueError):
        return default


def _write(path, value, private=False):
    fd = os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600 if private else 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(value, f)
    os.replace(path + ".tmp", path)


MAX_PLACES = 8
KIND_WORDS = {"disk": "Folder on this server or the pool", "smb": "Network share (SMB)", "nfs": "Network share (NFS)", "rclone": "Cloud service"}
ID_RE = re.compile(r"^[a-z0-9]{1,16}$")


def _clean(d):
    """One place, as the page and the copy use it: every key there, whatever the file held."""
    kind = d.get("kind") if d.get("kind") in KINDS else "off"
    try:
        keep = max(1, min(int(d.get("keep") or KEEP_DEFAULT), 50))
    except (TypeError, ValueError):
        keep = KEEP_DEFAULT
    try:  # how many of the server's settings zips stay there (each is large): fewer than the full backups
        keep_settings = max(1, min(int(d.get("keep_settings") or 2), 50))
    except (TypeError, ValueError):
        keep_settings = 2
    return {"id": str(d.get("id") or "main")[:16], "name": str(d.get("name") or "").strip()[:60], "enabled": d.get("enabled") is not False,
            "kind": kind, "folder": str(d.get("folder") or ""), "smb": str(d.get("smb") or ""), "smb_user": str(d.get("smb_user") or ""),
            "nfs": str(d.get("nfs") or ""), "remote": str(d.get("remote") or ""), "keep": keep, "keep_settings": keep_settings,
            # Connect a cloud service (DASH-452): which service the wizard connected ("" for a remote pasted by hand),
            # and how the person last signed in (browser or phone), offered first next time.
            "service": str(d.get("service") or "") if kind == "rclone" else "", "signin_way": str(d.get("signin_way") or ""),
            "account": str(d.get("account") or "")[:100]}


def _items(raw):
    """The places, in the order they were added. A file from before several places (one flat place) is the first, id "main"."""
    if isinstance(raw.get("destinations"), list):
        out, seen = [], set()
        for d in raw["destinations"][:MAX_PLACES]:
            if isinstance(d, dict) and d.get("kind") in KINDS and d.get("kind") != "off":
                c = _clean(d)
                if c["id"] not in seen:
                    seen.add(c["id"])
                    out.append(c)
        return out
    if raw.get("kind") in KINDS and raw.get("kind") != "off":
        return [_clean({**raw, "id": "main", "enabled": True})]
    return []


def _raw_settings(data_dir):
    return _read(os.path.join(data_dir, SETTINGS), {})


def destinations(data_dir):
    return _items(_raw_settings(data_dir))


def _pick(data_dir, dest=None):
    items = destinations(data_dir)
    return next((i for i in items if i["id"] == dest), None) if dest else (items[0] if items else None)


def _id(data_dir, dest=None):
    """The id a dest argument means: itself, else the first place's, else "main"."""
    if dest:
        return dest
    first = _pick(data_dir)
    return first["id"] if first else "main"


def settings(data_dir, dest=None):
    """One place's settings (dest is its id; none means the first). Off when there is none."""
    d = _pick(data_dir, dest) or _clean({"kind": "off", "id": dest or ""})
    return {**d, "detailed_log": bool(_raw_settings(data_dir).get("detailed_log"))}


def new_id(data_dir):
    have = {i["id"] for i in destinations(data_dir)}
    while True:
        n = "d" + _random.token_hex(3)
        if n not in have:
            return n


def blank(data_dir):
    """A place not saved yet, for the form that adds one."""
    return {**_clean({"kind": "off", "id": new_id(data_dir)}), "detailed_log": False}


# Detailed log for backup connections ---------------------------------------------------------------------------------
# (owner, 19 November 2026: "Can you add a detailed log for backup connections with a setting in the backup / restore
# area"). When it is on, the words of each step (rclone's, or the share's) go to Starboard's log, area "backup
# connection": a test, a copy, and each step of connecting a cloud service. Lines that could hold a secret are left out
# here, and the log takes out keys, tokens and addresses as it does everywhere.
DETAIL_LINES = 60
_SECRETISH = re.compile(r"(?i)(\b(pass(word)?|secret|token|client_id|client_secret|access_token|refresh_token|api[_-]?key|access[_-]?key|"
                        r"account[_-]?key|key|authori[sz]ation|session|cookie)\b\s*=\s*\S|"
                        r"\"[a-z_]*(token|secret|password|key)\"\s*:|bearer\s+\S|[?&](code|state)=)")


def detailed(data_dir):
    return bool(settings(data_dir)["detailed_log"])


def set_detailed(data_dir, on):
    """Detailed log for backup connections, on or off; it changes nothing else."""
    raw = _read(os.path.join(data_dir, SETTINGS), {})
    raw["detailed_log"] = bool(on)
    _write(os.path.join(data_dir, SETTINGS), raw)
    return settings(data_dir)


def clean_lines(said):
    """The helper's words, line by line, without anything between rclone's paste markers (a sign-in token) or any line
    that names a password, key, token or sign-in code."""
    text = re.sub(r"Paste the following[\s\S]*?<---End paste", "", str(said or ""))
    text = re.sub(r"--->[\s\S]*?<---End paste", "", text)
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or _SECRETISH.search(ln):
            continue
        out.append(_MARKS.get(ln) or _marked(ln) or ln[:300])
    return out


# The helper's step markers, in words for the log.
_MARKS = {"STEP-FOLDER": "Reached the folder", "STEP-WRITE": "Wrote a small test file", "STEP-READ": "Read it back",
          "STEP-REMOVE": "Removed it"}


def _marked(ln):
    m = re.fullmatch(r"(FREE|COUNT) (\d+)", ln)
    if not m:
        return None
    n = int(m.group(2))
    return f"Free space there: {n // 1024 ** 2} MB" if m.group(1) == "FREE" else f"Full backups there: {n}"


def log_detail(data_dir, what, said, code=None):
    """When the detailed log is on: what was done, how it ended, and the helper's own words (the last DETAIL_LINES)."""
    if not data_dir or not detailed(data_dir):
        return
    from . import logs
    lines = clean_lines(said)
    logs.event("info", "backup connection", f"{what}: " + ("finished" if code in (0, None) else f"ended with code {code}")
               + f", {len(lines)} line{'s' if len(lines) != 1 else ''} of detail")
    for ln in lines[-DETAIL_LINES:]:
        logs.event("info", "backup connection", f"{what}: {ln}")


def _per_place(data_dir, name, dest):
    """One place's part of a file that keeps one part for each place ({"items": {id: part}}); the file from before
    several places (one flat part) is the first place's."""
    raw = _read(os.path.join(data_dir, name), {})
    want = _id(data_dir, dest)
    if isinstance(raw.get("items"), dict):
        got = raw["items"].get(want)
        return got if isinstance(got, dict) else None
    return raw if raw and want == "main" else None


def _set_per_place(data_dir, name, dest, value, private=False):
    path = os.path.join(data_dir, name)
    raw = _read(path, {})
    if not isinstance(raw.get("items"), dict):  # the flat file of one place becomes the first place's part
        first = (_pick(data_dir) or {}).get("id") or "main"
        raw = {"items": {first: raw} if raw else {}}
    if value is None:
        raw["items"].pop(_id(data_dir, dest), None)
    else:
        raw["items"][_id(data_dir, dest)] = value
    _write(path, raw, private=private)


def secrets(data_dir, dest=None):
    s = _per_place(data_dir, SECRET, dest) or {}
    return {"smb_password": str(s.get("smb_password") or ""), "rclone_config": str(s.get("rclone_config") or "")}


def public(data_dir, dest=None):
    """What the page shows: the settings, whether each secret is set (never the secret), and the last copy. With no dest,
    the first place's, plus every place and whether the newest backup is safe."""
    out = _public_one(data_dir, dest, settings(data_dir, dest))
    if not dest:
        out["destinations"] = [_public_one(data_dir, d["id"], settings(data_dir, d["id"])) for d in destinations(data_dir)]
        out["safe"] = safe(data_dir)
        out["max_places"] = MAX_PLACES
    return out


def _public_one(data_dir, dest, s):
    sec = secrets(data_dir, s["id"] if s["kind"] != "off" else dest)
    st = status(data_dir, s["id"]) if s["kind"] != "off" else {"state": "none"}
    word, shape = state_words(s, st)
    return {**s, "smb_password_set": bool(sec["smb_password"]), "rclone_config_set": bool(sec["rclone_config"]),
            "status": st, "where": where(s), "where_words": where_words(s), "service_name": _service_name(s),
            "kinds": list(KINDS), "tested": tested(data_dir, s["id"]) if s["kind"] != "off" else None,
            "title": title_of(s), "kind_words": KIND_WORDS.get(s["kind"], ""), "state_word": word, "shape": shape}


def title_of(s):
    """The name the person gave it, else its kind and where, in words."""
    if s.get("name"):
        return s["name"]
    if s["kind"] == "rclone":
        return _service_name(s) or "Cloud service"
    return KIND_WORDS.get(s["kind"], "Backup place")


def state_words(s, st):
    """The place's last copy in one or two words, and a shape (an icon name) so the state never rests on colour."""
    if not s.get("enabled", True):
        return "Deactivated", "minus"
    state = (st or {}).get("state")
    if state == "running":
        return "Copying", "refresh-cw"
    if state == "done" and st.get("verified", True):
        return "Copied and read back", "circle-check"
    if state == "failed":
        return "Failed", "circle-alert"
    return "Not copied yet", "circle"


def _service_name(s):
    if s["kind"] != "rclone" or not s["service"]:
        return ""
    from . import cloud_connect
    try:
        return cloud_connect.service(s["service"])["name"]
    except cloud_connect.CloudError:
        return ""


def where_words(s):
    """The other place for people: "Google Drive, starboard-backups" for a service the wizard connected."""
    name = _service_name(s)
    if name and ":" in s["remote"] and s["remote"].split(":", 1)[0].startswith("starboard-"):
        return f"{name}, {s['remote'].split(':', 1)[1] or 'the top folder'}"
    return where(s)


def where(s):
    """The other place in a few words, for the page and the log."""
    return {"off": "", "disk": s["folder"], "smb": s["smb"], "nfs": s["nfs"], "rclone": s["remote"]}.get(s["kind"], "")


def remote_names(config):
    return re.findall(r"^\s*\[([^\]\n]{1,63})\]\s*$", config or "", re.M)


def check(data_dir, incoming):
    """Checks what the page sent; returns (settings, secrets) to keep, or raises ValueError with a sentence.
    incoming["id"] names the place to change ("new" adds one); none means the first place, as before several places."""
    want = str(incoming.get("id") or "")
    if want == "new":
        if len(destinations(data_dir)) >= MAX_PLACES:
            raise ValueError(f"Starboard keeps up to {MAX_PLACES} places. Remove one first")
        old, sec = blank(data_dir), {"smb_password": "", "rclone_config": ""}
    else:
        if want and not ID_RE.match(want):
            raise ValueError("Choose a place from the list")
        if want and not _pick(data_dir, want):
            raise ValueError("That place is not in the list any more")
        old, sec = settings(data_dir, want or None), secrets(data_dir, want or None)
    kind = str(incoming.get("kind") or "off")
    if kind not in KINDS or (want == "new" and kind == "off"):
        raise ValueError("Choose where the copies go")
    try:
        given = incoming.get("keep")
        keep = old["keep"] if given in (None, "") else int(given)
    except (TypeError, ValueError):
        raise ValueError("Keep the newest: give a number from 1 to 50") from None
    if not 1 <= keep <= 50:
        raise ValueError("Keep the newest: give a number from 1 to 50")
    new = {**old, "kind": kind, "keep": keep}
    if incoming.get("keep_settings") not in (None, ""):
        try:
            new["keep_settings"] = int(incoming["keep_settings"])
        except (TypeError, ValueError):
            raise ValueError("Keep the newest server settings backups: give a number from 1 to 50") from None
        if not 1 <= new["keep_settings"] <= 50:
            raise ValueError("Keep the newest server settings backups: give a number from 1 to 50")
    if "name" in incoming:
        new["name"] = str(incoming.get("name") or "").strip()[:60]
    if "enabled" in incoming:
        new["enabled"] = bool(incoming.get("enabled"))
    if kind == "disk":
        folder = folders.tidy(incoming.get("folder") or "")
        if not folders.allowed(folder):
            raise ValueError("Choose a folder under " + ", ".join(folders.ROOTS))
        backups = _backup_folder(data_dir)
        if backups and (folder == backups or folder.startswith(backups + "/") or backups.startswith(folder + "/")):
            raise ValueError("That is the folder the full backups are made in. Choose a folder on another disk, such as a USB disk")
        new["folder"] = folder
    elif kind == "smb":
        address = str(incoming.get("smb") or "").strip().replace("\\", "/")
        if not SMB_RE.match(address):
            raise ValueError("Write the share as //computer/share, such as //192.168.1.20/backups or //nas.home/backups/starboard")
        new["smb"], new["smb_user"] = address, str(incoming.get("smb_user") or "").strip()[:100]
        if "," in new["smb_user"] or "=" in new["smb_user"]:
            raise ValueError("A user name cannot have a comma or an equals sign")
        if incoming.get("smb_password"):
            sec["smb_password"] = str(incoming["smb_password"])[:200]
    elif kind == "nfs":
        address = str(incoming.get("nfs") or "").strip()
        if not NFS_RE.match(address):
            raise ValueError("Write the share as computer:/folder, such as 192.168.1.20:/export/backups")
        new["nfs"] = address
    elif kind == "rclone":
        remote = str(incoming.get("remote") or "").strip()
        m = REMOTE_RE.match(remote)
        if not m:
            raise ValueError("Write the remote as name:folder, such as mycloud:starboard-backups")
        config = str(incoming.get("rclone_config") or "").strip()
        if config:
            if len(config) > 20000:
                raise ValueError("That rclone config is too long: paste only the part for this remote")
            sec["rclone_config"] = config + "\n"
        if m.group(1) not in remote_names(sec["rclone_config"]):
            raise ValueError(f"Paste the part of your rclone.conf that starts with [{m.group(1)}]: rclone config file shows where it is")
        new["remote"] = remote
        if remote != old["remote"] or config:
            new["service"] = ""  # pasted by hand: no longer the wizard's service
    return new, sec


def save(data_dir, new, sec, dest=None):
    """Keeps one place (new["id"], else dest, else the first, else a new one) and its secrets."""
    items = destinations(data_dir)
    pid = new.get("id") or dest or (items[0]["id"] if items else None) or new_id(data_dir)
    if new.get("kind") == "off":  # Off (as before several places) removes it
        return _remove(data_dir, pid)
    mine = _clean({**new, "id": pid})
    before = next((i for i in items if i["id"] == pid), None)
    if before is None and len(items) >= MAX_PLACES:
        raise ValueError(f"Starboard keeps up to {MAX_PLACES} places. Remove one first")
    if before is None or (before["kind"], where(before)) != (mine["kind"], where(mine)):
        _set_per_place(data_dir, STATUS, pid, {"state": "none"})  # the last copy was to another place (DASH-452)
    items = [mine if i["id"] == pid else i for i in items] if before else items + [mine]
    raw = _raw_settings(data_dir)
    _write(os.path.join(data_dir, SETTINGS), {"destinations": items, "detailed_log": bool(raw.get("detailed_log"))})
    _set_per_place(data_dir, SECRET, pid, {"smb_password": sec.get("smb_password", ""), "rclone_config": sec.get("rclone_config", "")}, private=True)
    return mine


def _remove(data_dir, pid):
    items = [i for i in destinations(data_dir) if i["id"] != pid]
    raw = _raw_settings(data_dir)
    for name in (SECRET, STATUS, TESTED):  # first, while the file may still be the flat one of a single place
        _set_per_place(data_dir, name, pid, None, private=name == SECRET)
    _write(os.path.join(data_dir, SETTINGS), {"destinations": items, "detailed_log": bool(raw.get("detailed_log"))})
    return None


def set_enabled(data_dir, dest, on):
    """Switch one place on or off: a switched-off place keeps its settings and is left out of each new backup."""
    s = _pick(data_dir, dest)
    if not s:
        raise ValueError("That place is not in the list any more")
    save(data_dir, {**s, "enabled": bool(on)}, secrets(data_dir, dest))
    return settings(data_dir, dest)


# Status -------------------------------------------------------------------------------------------------------------

def status(data_dir, dest=None):
    return _per_place(data_dir, STATUS, dest) or {"state": "none"}


def tested(data_dir, dest=None):
    """The last Test connection for the place set up now, or None (a test of another place does not count)."""
    t = _per_place(data_dir, TESTED, dest) or {}
    s = settings(data_dir, dest)
    return t if t and t.get("where") == where(s) and t.get("kind") == s["kind"] else None


def save_test(data_dir, result, dest=None):
    s = settings(data_dir, dest)
    _set_per_place(data_dir, TESTED, dest or s["id"], {**result, "where": where(s), "kind": s["kind"], "at": result.get("at") or time.time()})


def _say(data_dir, dest=None, **kw):
    now = status(data_dir, dest)
    now.update(kw)
    _set_per_place(data_dir, STATUS, dest, now)


def safe(data_dir):
    """Whether the newest full backup is safe: it counts only when every place that is activated has copied it and
    read it back. {"safe": bool, "words": one sentence, "places": [{id, title, ok, words}]}"""
    on = [d for d in destinations(data_dir) if d["enabled"]]
    try:
        newest_file = newest(data_dir)
    except Exception:  # noqa: BLE001 - without Docker the folder cannot be worked out: nothing is safe yet
        newest_file = None
    if not on:
        return {"safe": False, "words": "The newest full backup is only on this computer: no place is activated for copies", "places": []}
    rows = []
    for d in on:
        st = status(data_dir, d["id"])
        ok = bool(newest_file) and st.get("state") == "done" and st.get("file") == newest_file and st.get("verified", True)
        rows.append({"id": d["id"], "title": title_of(d), "ok": ok,
                     "words": "Copied and read back" if ok else "Copying" if st.get("state") == "running"
                     else "Failed: " + str(st.get("error") or "")[:160] if st.get("state") == "failed" else "Not copied yet"})
    if all(r["ok"] for r in rows):
        return {"safe": True, "words": f"Safe: the newest full backup was copied and read back at {len(rows)} {'place' if len(rows) == 1 else 'places'}", "places": rows}
    bad = [r["title"] for r in rows if not r["ok"]]
    return {"safe": False, "words": "Not yet safe: " + ", ".join(bad) + " has not read back the newest full backup" if len(bad) == 1
            else "Not yet safe: " + ", ".join(bad) + " have not read back the newest full backup", "places": rows}


# Running a copy -------------------------------------------------------------------------------------------------------

def _backup_folder(data_dir):
    saved = full_backup.saved_key(data_dir)
    target = (full_backup.status(data_dir).get("target") or (saved or {}).get("folder") or full_backup.default_folder(data_dir) or "")
    try:
        return folders.tidy(target) if target else ""
    except ValueError:
        return ""


def _helper(script, binds, image=None, network="none", volumes=(), timeout=7200):  # noqa: C901
    """A short-lived helper container (the backup helper, or rclone's image for a cloud remote): (exit code, output)."""
    from . import containers
    image = image or containers.HELPER_IMAGE
    if image == containers.HELPER_IMAGE:
        containers.ensure_image()  # DASH-438: downloaded first if it is missing
    elif image == RCLONE_IMAGE:
        _pull(RCLONE_IMAGE)
    body = {"Image": image, "Entrypoint": ["sh", "-c"], "Cmd": [script], "Labels": {"starboard.updater": "1"},
            "HostConfig": {"Binds": list(binds) + [f"{v}:/t" for v in volumes], "NetworkMode": network}}
    cid = containers.docker("POST", f"/containers/create?name=starboard-copy-{int(time.time() * 1000)}", body)["Id"]
    try:
        containers.docker("POST", f"/containers/{cid}/start")
        code = containers.docker("POST", f"/containers/{cid}/wait", timeout=timeout).get("StatusCode", 1)
        raw = containers.docker("GET", f"/containers/{cid}/logs?stdout=1&stderr=1&tail=200", raw=True)
    finally:
        try:
            containers.docker("DELETE", f"/containers/{cid}?force=1")
        except containers.DockerError:
            pass
    text, i = b"", 0
    while i + 8 <= len(raw):
        n = int.from_bytes(raw[i + 4:i + 8], "big")
        text += raw[i + 8:i + 8 + n]
        i += 8 + n
    return code, text.decode("utf-8", "replace")


def _pull(image):
    """rclone's pinned image, downloaded when it is not here yet."""
    from . import containers
    try:
        containers.docker("GET", f"/images/{image}/json")
        return
    except containers.DockerError:
        pass
    try:
        containers.docker("POST", f"/images/create?fromImage={image.split('@')[0].split(':')[0]}&tag={image.split('@')[1]}", raw=True, timeout=600)
    except containers.DockerError:
        pass  # the create that follows says if it is not here


def _address(host):
    """Docker's volume driver needs the share's computer as an address."""
    host = host.strip("[]")
    try:
        return socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)[0][4][0]
    except OSError:
        raise CopyError(f"Starboard could not find the computer {host} on your network") from None


def _share_volume(s, sec, env):
    """Asks Docker for a short-lived volume on the SMB or NFS share; returns its name."""
    from . import containers
    name = f"starboard-copy-{int(time.time() * 1000)}"
    if s["kind"] == "smb":
        m = SMB_RE.match(s["smb"])
        ip = _address(m.group(1))
        opts = [f"addr={ip}", "vers=3.0", f"uid={int(env.get('PUID') or 1000)}", f"gid={int(env.get('PGID') or 1000)}",
                "file_mode=0600", "dir_mode=0700"]
        if s["smb_user"]:
            opts += [f"username={s['smb_user']}", "password=" + sec["smb_password"].replace(",", ",,")]
        else:
            opts.append("guest")
        driver = {"type": "cifs", "device": f"//{ip}/{m.group(2)}{m.group(3)}", "o": ",".join(opts)}
    else:
        m = NFS_RE.match(s["nfs"])
        driver = {"type": "nfs", "device": f":{m.group(2) or '/'}", "o": f"addr={_address(m.group(1))},nfsvers=4,rw"}
    try:
        containers.docker("POST", "/volumes/create", {"Name": name, "Driver": "local", "DriverOpts": driver,
                                                      "Labels": {"starboard.updater": "1"}})
    except containers.DockerError as e:
        raise CopyError(f"Docker could not reach the share: {e}") from None
    return name


def _let_go(volume):
    """Lets go of the short-lived volume: Docker unmounts the share. The share's own files are not touched."""
    from . import containers
    try:
        containers.docker("DELETE", f"/volumes/{volume}")
    except containers.DockerError:
        pass


def _prune_script(inner, keep):
    """Keeps the newest `keep` full backups at the other place, by the date in their names; nothing else is touched."""
    return (f"ls -1 {_q(inner)} | grep -E {_q(BACKUP_GLOB)} | sort -r | tail -n +{int(keep) + 1} | "
            f"while read -r old; do rm -f {_q(inner)}/\"$old\"; done")


def _run(data_dir, source, test=False, dest=None):
    """Copies source (a full backup's path on this computer) to the other place and prunes there. With test, writes and
    removes a small file instead and counts the backups there. Returns one sentence."""
    from . import stack
    s, sec = settings(data_dir, dest), secrets(data_dir, dest)
    if s["kind"] == "off":
        raise CopyError("Choose where the copies go first")
    env = stack.env_values(data_dir)
    name = os.path.basename(source) if source else ""
    binds = []
    if source:
        root, path = full_backup._place(source)
        if not full_backup.NAME_RE.match(name):
            raise CopyError("That is not a Starboard full backup")
        binds.append(f"{root}:/s:ro")
        src = "/s" + path[len(root):]
    count = f"echo COUNT $(ls -1 {{inner}} | grep -cE {_q(BACKUP_GLOB)})"
    if s["kind"] in ("disk", "smb", "nfs"):
        volumes, inner = [], "/t"
        if s["kind"] == "disk":
            root, folder = full_backup._place(s["folder"])
            binds.append(f"{root}:/t")
            inner = "/t" + folder[len(root):]
        else:
            volumes = [_share_volume(s, sec, env)]
        own = f" && chown {int(env.get('PUID') or 1000)}:{int(env.get('PGID') or 1000)} {_q(inner)}/{_q(name)}" if s["kind"] == "disk" else ""
        if test:
            # Test connection (DASH-452): reach the folder, write a small file, read it back, remove it, then the room left.
            mark = _random.token_hex(6)
            t = f"{_q(inner)}/.starboard-test-{mark}"
            script = (f"mkdir -p {_q(inner)} && echo STEP-FOLDER && echo starboard-{mark} > {t} && echo STEP-WRITE && "
                      f"[ \"$(cat {t})\" = starboard-{mark} ] && echo STEP-READ && rm -f {t} && echo STEP-REMOVE && "
                      f"echo FREE $(( $(df -Pk {_q(inner)} | awk 'NR==2 {{print $4}}') * 1024 )) && " + count.format(inner=_q(inner)))
        else:
            # A .part is never a backup: one left by a copy that was cut off goes first, as in the backup folder.
            script = (f"mkdir -p {_q(inner)} && find {_q(inner)} -maxdepth 1 -name 'starboard-full-*.starboard.part' -delete && "
                      f"cp {_q(src)} {_q(inner)}/{_q(name + '.part')} && "
                      f"[ \"$(wc -c < {_q(src)})\" = \"$(wc -c < {_q(inner)}/{_q(name + '.part')})\" ] || {{ echo 'The copy is not the same size'; exit 4; }}; "
                      f"mv {_q(inner)}/{_q(name + '.part')} {_q(inner)}/{_q(name)} && chmod 600 {_q(inner)}/{_q(name)}{own} && "
                      + _prune_script(inner, s["keep"]) + " && " + count.format(inner=_q(inner)))
        try:
            code, said = _helper(f"timeout {TEST_LIMIT} sh -c {_q(script)}" if test else script, binds, volumes=volumes,
                                 timeout=TEST_LIMIT + 30 if test else 7200)
            log_detail(data_dir, f"{'Test connection' if test else 'Copy'} to {where(s)}", said, code)
        finally:
            for v in volumes:
                _let_go(v)
    else:
        code, said = _rclone(data_dir, s, sec, binds, src if source else "", name, test)
    if test:
        return code, said
    if code:
        raise CopyError(_plain(said, s))
    m = re.search(r"COUNT (\d+)", said)
    there = int(m.group(1)) if m else None
    if test:
        return f"Starboard can write to {where(s)}" + (f", which has {there} full {'backup' if there == 1 else 'backups'}" if there is not None else "")
    return f"Copied to {where(s)}" + (f", which keeps {there} full {'backup' if there == 1 else 'backups'}" if there is not None else "")


def _rclone(data_dir, s, sec, binds, src, name, test):
    """rclone in its own image, with the person's remote. Its config is handed over in a file in Starboard's own folder
    and read back after, as rclone may refresh a sign-in token while it works."""
    from . import stack
    host = stack.host_folder(data_dir)
    if not host:
        raise CopyError("Starboard cannot find its own folder on this computer")
    work = os.path.join(data_dir, WORK)
    os.makedirs(work, mode=0o700, exist_ok=True)
    os.chmod(work, 0o700)
    conf = os.path.join(work, "rclone.conf")
    fd = os.open(conf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(sec["rclone_config"])
    # The config holds the person's cloud sign-in, so it stays 0600 and Starboard's own. rclone runs as root in its
    # container, which can read it as it is; if rclone writes it back (a refreshed token), the script gives it back to
    # Starboard's user, 0600 again, so Starboard can read the new one and nobody else can (Bandit B103, 14 November 2026).
    owner = f"{os.getuid()}:{os.getgid()}"
    remote = s["remote"]
    base = remote if remote.endswith((":", "/")) else remote + "/"
    rc = "rclone --config /c/rclone.conf --contimeout 30s --timeout 5m --retries 3"
    prune = (f"{rc} lsf --files-only {_q(remote)} | grep -E {_q(BACKUP_GLOB)} | sort -r | tail -n +{int(s['keep']) + 1} | "
             f"while read -r old; do {rc} deletefile {_q(base)}\"$old\" || exit 5; done")
    count = f"echo COUNT $({rc} lsf --files-only {_q(remote)} | grep -cE {_q(BACKUP_GLOB)})"
    if test:
        from . import cloud_connect
        script = f"timeout {TEST_LIMIT} sh -c {_q(cloud_connect.test_script(remote, _random.token_hex(6)))}"
    else:
        # Read back (owner, 26 November 2026): after the copy, ask the cloud for the file's size and compare it with the
        # backup's own. Only then does the place count as safe.
        back = (f"[ \"$({rc} lsf --format s --files-only {_q(base + name)})\" = \"$(wc -c < {_q(src)})\" ] || "
                "{ echo 'The copy is not the same size'; exit 4; }")
        script = f"{rc} copyto {_q(src)} {_q(base + name)} && {back} && {prune} && {count}"
    script = f"{script}; code=$?; chown {owner} /c/rclone.conf 2>/dev/null; chmod 600 /c/rclone.conf 2>/dev/null; exit $code"
    try:
        code, said = _helper(script, binds + [f"{os.path.dirname(host)}/{WORK}:/c"], image=RCLONE_IMAGE, network="bridge",
                             timeout=TEST_LIMIT + 30 if test else 7200)
        log_detail(data_dir, f"{'Test connection' if test else 'Copy'} to {remote}", said, code)
        try:
            with open(conf, encoding="utf-8") as f:
                after = f.read()
            if after.strip() and after != sec["rclone_config"]:
                save(data_dir, {k: v for k, v in s.items() if k != "detailed_log"}, {**sec, "rclone_config": after}, s["id"])
        except OSError:
            pass
    finally:
        try:
            os.remove(conf)  # Starboard's own short-lived copy of the config; the kept one is in SECRET
        except OSError:
            pass
    return code, said


def _plain(said, s):
    """The helper's last words, in a sentence the page can show."""
    t = said.strip()
    low = t.lower()
    if "permission denied" in low or "access denied" in low or "eacces" in low:
        return f"Starboard was not allowed to write to {where(s)}. Check the user name, password and the folder's permissions"
    if "no such device" in low or "mount" in low and "fail" in low or "host is down" in low or "no route to host" in low:
        return f"The share {where(s)} did not answer. Check it is on and the address is right"
    if "no space left" in low:
        return f"{where(s)} is full. Keep fewer copies there, or free some space"
    if "didn't find section in config file" in low or "couldn't find" in low and "remote" in low:
        return "rclone did not find that remote in the config you pasted"
    if "connection refused" in low or "dial tcp" in low or "no such host" in low or "i/o timeout" in low:
        return f"{where(s)} did not answer. Check its address in the config and that it is on"
    if "the copy is not the same size" in low:
        return "The copy came out a different size from the backup, so it was not kept. Try again"
    return (t.splitlines() or ["The copy did not work"])[-1][:240]


def after_full(data_dir, file_path):
    """Called at the end of each full backup, in its own thread. Never raises: a failed copy is said on the page, in
    the log and as an alert that names the place, and the backup itself stays good. Every place that is activated gets
    its turn; one that fails never stops the others."""
    from . import logs
    places = [d for d in destinations(data_dir) if d["enabled"]]
    if not places:
        return
    failed = []
    for d in places:
        full_backup._say(data_dir, step=f"Copying it to {title_of(d)}")
        _copy(data_dir, file_path, d["id"])
        st = status(data_dir, d["id"])
        ok = st.get("state") == "done"
        logs.event("info" if ok else "warning", "backup", f"Copy to {title_of(d)}: {st.get('said') or st.get('error')}")
        if not ok:
            failed.append((title_of(d), st.get("error") or "it did not work"))
    if failed:
        alert(data_dir, failed, len(places))


def failures(data_dir):
    """The places whose last copy failed: [{key, title, error}], for the alerts. The key changes with each try."""
    out = []
    for d in destinations(data_dir):
        st = status(data_dir, d["id"])
        if d["enabled"] and st.get("state") == "failed":
            out.append({"key": f"backup-copy:{d['id']}:{int(st.get('started') or 0)}", "title": title_of(d), "error": str(st.get("error") or "it did not work")[:200]})
    return out


def alert(data_dir, failed, total):
    """One alert that says which places failed (area "backup", level error, so the alert channels and the page see it)."""
    from . import logs
    names = ", ".join(n for n, _ in failed)
    logs.event("error", "backup", f"Backup not safe: {len(failed)} of {total} places failed ({names}). "
               + " ".join(f"{n}: {why}." for n, why in failed)[:600])


def _copy(data_dir, file_path, dest=None):
    d = _id(data_dir, dest)
    _say(data_dir, d, state="running", started=time.time(), finished=None, file=file_path, where=where(settings(data_dir, d)), error="", said="", verified=False)
    try:
        said = _run(data_dir, file_path, dest=d)
        _say(data_dir, d, state="done", finished=time.time(), said=said, verified=True)
    except Exception as e:  # noqa: BLE001 - whatever stops it, the page says what
        _say(data_dir, d, state="failed", finished=time.time(), error=str(e) or e.__class__.__name__, verified=False)


def newest(data_dir):
    """The newest full backup in the backup folder, or None."""
    folder = _backup_folder(data_dir)
    if not folder:
        return None
    try:
        got = full_backup.found(folder)
    except full_backup.BackupError:
        return None
    return got[0]["path"] if got else None


def copy_now(data_dir, dest=None):
    """Copy the newest full backup now, in the background (to one place, or to every place that is activated);
    refused while a backup or a copy runs."""
    from . import containers
    if not containers.available():
        raise CopyError("Starboard needs Docker access to make copies")
    places = [_pick(data_dir, dest)] if dest else [d for d in destinations(data_dir) if d["enabled"]]
    if not places or places[0] is None:
        raise CopyError("Choose where the copies go first" if not dest else "That place is not in the list any more")
    source = newest(data_dir)
    if not source:
        raise CopyError("There is no full backup to copy yet. Make one first")
    if not full_backup._lock.acquire(blocking=False):
        raise CopyError("A backup is being made already: it is copied when it finishes")

    def go():
        failed = []
        try:
            for d in places:
                _copy(data_dir, source, d["id"])
                st = status(data_dir, d["id"])
                if st.get("state") != "done":
                    failed.append((title_of(d), st.get("error") or "it did not work"))
            if failed:
                alert(data_dir, failed, len(places))
        finally:
            full_backup._lock.release()
    for d in places:
        _say(data_dir, d["id"], state="running", started=time.time(), finished=None, file=source, error="", said="", verified=False)
    threading.Thread(target=go, name="backup-copy", daemon=True).start()
    return status(data_dir, places[0]["id"])


def newest_size(data_dir):
    """The size of the newest full backup, for the room check, or None."""
    path = newest(data_dir)
    try:
        return os.path.getsize(path) if path else None
    except OSError:
        return None


def test(data_dir, dest=None):
    """Test connection (DASH-452, owner, 16 November 2026: "Can you add a test button to items to check they are connected
    ok?"): reach the place, write a small file, read it back, remove it, check there is room for the newest backup and,
    for a cloud service, that the sign-in still works. The result is kept, so the page shows it when opened again."""
    from . import cloud_connect, containers
    if not containers.available():
        raise CopyError("Starboard needs Docker access to make copies")
    s = settings(data_dir, dest)
    if s["kind"] == "off":
        raise CopyError("Choose where the copies go first")
    if not _lock.acquire(blocking=False):
        raise CopyError("A test is running already")
    try:
        try:
            code, said = _run(data_dir, "", test=True, dest=s["id"])
        except CopyError as e:
            code, said = 1, str(e)
        signin = "oauth" if s["kind"] == "rclone" and s["service"] in ("drive", "onedrive", "dropbox") else ""
        result = cloud_connect.read_test(said, code, None, newest_size(data_dir), signin=signin)
        if result["ok"]:
            m = re.search(r"COUNT (\d+)", said)
            result["count"] = int(m.group(1)) if m else None
        save_test(data_dir, result, s["id"])
        return tested(data_dir, s["id"])
    finally:
        _lock.release()


def forget(data_dir, dest=None):
    """One place stops (dest), or every place when none is given: the settings go and the kept passwords go. Copies
    already made stay where they are."""
    for d in ([_pick(data_dir, dest)] if dest else destinations(data_dir)):
        if d:
            _remove(data_dir, d["id"])
