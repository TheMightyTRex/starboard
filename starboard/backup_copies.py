"""Copies off this computer (DASH-380, owner, 13 November 2026: "Start working on all the recommended plugins", the
stack comparison's recommendation 5): after each Full without media backup, Starboard copies the new encrypted file to
one other place and keeps only the newest N there, so a failed disk, a theft or a fire does not take every copy (the
3-2-1 rule: three copies, two kinds of storage, one somewhere else).

The other place, chosen in System, Backup and restore, Copies off this computer:
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
import socket
import threading
import time

from . import folders, full_backup

KINDS = ("off", "disk", "smb", "nfs", "rclone")
SETTINGS = "backup-copies.json"
SECRET = "backup-copies-secret.json"
STATUS = "backup-copies-status.json"
WORK = "backup-copy-work"
RCLONE_IMAGE = "rclone/rclone:1.75.2@sha256:2687085f718d3c628f7fdfb77c52a1d344332aed543110bb88088f2c70d43eb5"
KEEP_DEFAULT = 5
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


def settings(data_dir):
    s = _read(os.path.join(data_dir, SETTINGS), {})
    kind = s.get("kind") if s.get("kind") in KINDS else "off"
    return {"kind": kind, "folder": str(s.get("folder") or ""), "smb": str(s.get("smb") or ""), "smb_user": str(s.get("smb_user") or ""),
            "nfs": str(s.get("nfs") or ""), "remote": str(s.get("remote") or ""),
            "keep": max(1, min(int(s.get("keep") or KEEP_DEFAULT), 50))}


def secrets(data_dir):
    s = _read(os.path.join(data_dir, SECRET), {})
    return {"smb_password": str(s.get("smb_password") or ""), "rclone_config": str(s.get("rclone_config") or "")}


def public(data_dir):
    """What the page shows: the settings, whether each secret is set (never the secret), and the last copy."""
    sec = secrets(data_dir)
    return {**settings(data_dir), "smb_password_set": bool(sec["smb_password"]), "rclone_config_set": bool(sec["rclone_config"]),
            "status": status(data_dir), "where": where(settings(data_dir)), "kinds": list(KINDS)}


def where(s):
    """The other place in a few words, for the page and the log."""
    return {"off": "", "disk": s["folder"], "smb": s["smb"], "nfs": s["nfs"], "rclone": s["remote"]}.get(s["kind"], "")


def remote_names(config):
    return re.findall(r"^\s*\[([^\]\n]{1,63})\]\s*$", config or "", re.M)


def check(data_dir, incoming):
    """Checks what the page sent; returns (settings, secrets) to keep, or raises ValueError with a sentence."""
    old, sec = settings(data_dir), secrets(data_dir)
    kind = str(incoming.get("kind") or "off")
    if kind not in KINDS:
        raise ValueError("Choose where the copies go")
    try:
        given = incoming.get("keep")
        keep = old["keep"] if given in (None, "") else int(given)
    except (TypeError, ValueError):
        raise ValueError("Keep the newest: give a number from 1 to 50") from None
    if not 1 <= keep <= 50:
        raise ValueError("Keep the newest: give a number from 1 to 50")
    new = {**old, "kind": kind, "keep": keep}
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
    return new, sec


def save(data_dir, new, sec):
    _write(os.path.join(data_dir, SETTINGS), new)
    _write(os.path.join(data_dir, SECRET), sec, private=True)


# Status -------------------------------------------------------------------------------------------------------------

def status(data_dir):
    return _read(os.path.join(data_dir, STATUS), {"state": "none"})


def _say(data_dir, **kw):
    now = status(data_dir)
    now.update(kw)
    _write(os.path.join(data_dir, STATUS), now)


# Running a copy -------------------------------------------------------------------------------------------------------

def _backup_folder(data_dir):
    saved = full_backup.saved_key(data_dir)
    target = (full_backup.status(data_dir).get("target") or (saved or {}).get("folder") or full_backup.default_folder(data_dir) or "")
    try:
        return folders.tidy(target) if target else ""
    except ValueError:
        return ""


def _helper(script, binds, image=None, network="none", volumes=(), timeout=7200):
    """A short-lived helper container (the backup helper, or rclone's image for a cloud remote): (exit code, output)."""
    from . import containers
    image = image or containers.HELPER_IMAGE
    if image == RCLONE_IMAGE:
        try:
            containers.docker("POST", f"/images/create?fromImage={RCLONE_IMAGE.split('@')[0].split(':')[0]}&tag={RCLONE_IMAGE.split('@')[1]}", raw=True, timeout=600)
        except containers.DockerError:
            pass  # it may be here already; the create below says if it is not
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


def _run(data_dir, source, test=False):
    """Copies source (a full backup's path on this computer) to the other place and prunes there. With test, writes and
    removes a small file instead and counts the backups there. Returns one sentence."""
    from . import stack
    s, sec = settings(data_dir), secrets(data_dir)
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
            script = (f"mkdir -p {_q(inner)} && touch {_q(inner)}/.starboard-test && rm -f {_q(inner)}/.starboard-test && "
                      + count.format(inner=_q(inner)))
        else:
            # A .part is never a backup: one left by a copy that was cut off goes first, as in the backup folder.
            script = (f"mkdir -p {_q(inner)} && find {_q(inner)} -maxdepth 1 -name 'starboard-full-*.starboard.part' -delete && "
                      f"cp {_q(src)} {_q(inner)}/{_q(name + '.part')} && "
                      f"[ \"$(wc -c < {_q(src)})\" = \"$(wc -c < {_q(inner)}/{_q(name + '.part')})\" ] || {{ echo 'The copy is not the same size'; exit 4; }}; "
                      f"mv {_q(inner)}/{_q(name + '.part')} {_q(inner)}/{_q(name)} && chmod 600 {_q(inner)}/{_q(name)}{own} && "
                      + _prune_script(inner, s["keep"]) + " && " + count.format(inner=_q(inner)))
        try:
            code, said = _helper(script, binds, volumes=volumes)
        finally:
            for v in volumes:
                _let_go(v)
    else:
        code, said = _rclone(data_dir, s, sec, binds, src if source else "", name, test)
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
    conf = os.path.join(work, "rclone.conf")
    fd = os.open(conf, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(sec["rclone_config"])
    os.chmod(conf, 0o666)  # rclone runs as root in its container and may write it back; the folder stays Starboard's only
    remote = s["remote"]
    base = remote if remote.endswith((":", "/")) else remote + "/"
    rc = "rclone --config /c/rclone.conf --contimeout 30s --timeout 5m --retries 3"
    prune = (f"{rc} lsf --files-only {_q(remote)} | grep -E {_q(BACKUP_GLOB)} | sort -r | tail -n +{int(s['keep']) + 1} | "
             f"while read -r old; do {rc} deletefile {_q(base)}\"$old\" || exit 5; done")
    count = f"echo COUNT $({rc} lsf --files-only {_q(remote)} | grep -cE {_q(BACKUP_GLOB)})"
    if test:
        script = f"{rc} mkdir {_q(remote)} && {rc} lsf --max-depth 1 {_q(remote)} >/dev/null && {count}"
    else:
        script = f"{rc} copyto {_q(src)} {_q(base + name)} && {prune} && {count}"
    script = f"{script}; code=$?; chmod 666 /c/rclone.conf 2>/dev/null; exit $code"
    try:
        code, said = _helper(script, binds + [f"{os.path.dirname(host)}/{WORK}:/c"], image=RCLONE_IMAGE, network="bridge")
        try:
            with open(conf, encoding="utf-8") as f:
                after = f.read()
            if after.strip() and after != sec["rclone_config"]:
                save(data_dir, settings(data_dir), {**sec, "rclone_config": after})
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
    """Called at the end of each full backup, in its own thread. Never raises: a failed copy is said on the page and in
    the log, and the backup itself stays good."""
    from . import logs
    if settings(data_dir)["kind"] == "off":
        return
    full_backup._say(data_dir, step="Copying it off this computer")
    _copy(data_dir, file_path)
    s = status(data_dir)
    logs.event("info" if s.get("state") == "done" else "warning", "backup", f"Copy off this computer: {s.get('said') or s.get('error')}")


def _copy(data_dir, file_path):
    _say(data_dir, state="running", started=time.time(), finished=None, file=file_path, where=where(settings(data_dir)), error="", said="")
    try:
        said = _run(data_dir, file_path)
        _say(data_dir, state="done", finished=time.time(), said=said)
    except Exception as e:  # noqa: BLE001 - whatever stops it, the page says what
        _say(data_dir, state="failed", finished=time.time(), error=str(e) or e.__class__.__name__)


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


def copy_now(data_dir):
    """Copy the newest full backup now, in the background; refused while a backup or a copy runs."""
    from . import containers
    if not containers.available():
        raise CopyError("Starboard needs Docker access to make copies")
    if settings(data_dir)["kind"] == "off":
        raise CopyError("Choose where the copies go first")
    source = newest(data_dir)
    if not source:
        raise CopyError("There is no full backup to copy yet. Make one first")
    if not full_backup._lock.acquire(blocking=False):
        raise CopyError("A backup is being made already: it is copied when it finishes")

    def go():
        try:
            _copy(data_dir, source)
        finally:
            full_backup._lock.release()
    _say(data_dir, state="running", started=time.time(), finished=None, file=source, error="", said="")
    threading.Thread(target=go, name="backup-copy", daemon=True).start()
    return status(data_dir)


def test(data_dir):
    from . import containers
    if not containers.available():
        raise CopyError("Starboard needs Docker access to make copies")
    if not _lock.acquire(blocking=False):
        raise CopyError("A test is running already")
    try:
        return _run(data_dir, "", test=True)
    finally:
        _lock.release()


def forget(data_dir):
    """Copies stop: the settings go back to Off and the kept passwords go. Copies already made stay where they are."""
    save(data_dir, {**settings(data_dir), "kind": "off"}, {"smb_password": "", "rclone_config": ""})
