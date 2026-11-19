"""Copies off this computer (DASH-380, owner, 13 November 2026: "Start working on all the recommended plugins", the
stack comparison's recommendation 5): after each Full without media backup, Starboard copies the new encrypted file to
one other place and keeps only the newest N there, so a failed disk, a theft or a fire does not take every copy (the
3-2-1 rule: three copies, two kinds of storage, one somewhere else).

The other place, chosen in Settings, General, Backup and restore, Copies off this computer:
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


def settings(data_dir):
    s = _read(os.path.join(data_dir, SETTINGS), {})
    kind = s.get("kind") if s.get("kind") in KINDS else "off"
    return {"kind": kind, "folder": str(s.get("folder") or ""), "smb": str(s.get("smb") or ""), "smb_user": str(s.get("smb_user") or ""),
            "nfs": str(s.get("nfs") or ""), "remote": str(s.get("remote") or ""),
            "keep": max(1, min(int(s.get("keep") or KEEP_DEFAULT), 50)),
            # Connect a cloud service (DASH-452): which service the wizard connected ("" for a remote pasted by hand),
            # and how the person last signed in (browser or phone), offered first next time.
            "service": str(s.get("service") or "") if kind == "rclone" else "", "signin_way": str(s.get("signin_way") or ""),
            # Detailed log for backup connections (owner, 19 November 2026): off unless chosen.
            "detailed_log": bool(s.get("detailed_log"))}


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


def secrets(data_dir):
    s = _read(os.path.join(data_dir, SECRET), {})
    return {"smb_password": str(s.get("smb_password") or ""), "rclone_config": str(s.get("rclone_config") or "")}


def public(data_dir):
    """What the page shows: the settings, whether each secret is set (never the secret), and the last copy."""
    sec = secrets(data_dir)
    s = settings(data_dir)
    return {**s, "smb_password_set": bool(sec["smb_password"]), "rclone_config_set": bool(sec["rclone_config"]),
            "status": status(data_dir), "where": where(s), "where_words": where_words(s), "service_name": _service_name(s),
            "kinds": list(KINDS), "tested": tested(data_dir)}


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
    if name and s["remote"].startswith("starboard-cloud:"):
        return f"{name}, {s['remote'].split(':', 1)[1] or 'the top folder'}"
    return where(s)


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
        if remote != old["remote"] or config:
            new["service"] = ""  # pasted by hand: no longer the wizard's service
    return new, sec


def save(data_dir, new, sec):
    before = settings(data_dir)
    if (before["kind"], where(before)) != (new.get("kind"), where({**before, **new})):
        _write(os.path.join(data_dir, STATUS), {"state": "none"})  # the last copy was to the other place (DASH-452)
    _write(os.path.join(data_dir, SETTINGS), new)
    _write(os.path.join(data_dir, SECRET), sec, private=True)


# Status -------------------------------------------------------------------------------------------------------------

def status(data_dir):
    return _read(os.path.join(data_dir, STATUS), {"state": "none"})


def tested(data_dir):
    """The last Test connection for the place set up now, or None (a test of another place does not count)."""
    t = _read(os.path.join(data_dir, TESTED), {})
    return t if t and t.get("where") == where(settings(data_dir)) and t.get("kind") == settings(data_dir)["kind"] else None


def save_test(data_dir, result):
    s = settings(data_dir)
    _write(os.path.join(data_dir, TESTED), {**result, "where": where(s), "kind": s["kind"], "at": result.get("at") or time.time()})


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
        script = f"{rc} copyto {_q(src)} {_q(base + name)} && {prune} && {count}"
    script = f"{script}; code=$?; chown {owner} /c/rclone.conf 2>/dev/null; chmod 600 /c/rclone.conf 2>/dev/null; exit $code"
    try:
        code, said = _helper(script, binds + [f"{os.path.dirname(host)}/{WORK}:/c"], image=RCLONE_IMAGE, network="bridge",
                             timeout=TEST_LIMIT + 30 if test else 7200)
        log_detail(data_dir, f"{'Test connection' if test else 'Copy'} to {remote}", said, code)
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


def newest_size(data_dir):
    """The size of the newest full backup, for the room check, or None."""
    path = newest(data_dir)
    try:
        return os.path.getsize(path) if path else None
    except OSError:
        return None


def test(data_dir):
    """Test connection (DASH-452, owner, 16 November 2026: "Can you add a test button to items to check they are connected
    ok?"): reach the place, write a small file, read it back, remove it, check there is room for the newest backup and,
    for a cloud service, that the sign-in still works. The result is kept, so the page shows it when opened again."""
    from . import cloud_connect, containers
    if not containers.available():
        raise CopyError("Starboard needs Docker access to make copies")
    s = settings(data_dir)
    if s["kind"] == "off":
        raise CopyError("Choose where the copies go first")
    if not _lock.acquire(blocking=False):
        raise CopyError("A test is running already")
    try:
        try:
            code, said = _run(data_dir, "", test=True)
        except CopyError as e:
            code, said = 1, str(e)
        signin = "oauth" if s["kind"] == "rclone" and s["service"] in ("drive", "onedrive", "dropbox") else ""
        result = cloud_connect.read_test(said, code, None, newest_size(data_dir), signin=signin)
        if result["ok"]:
            m = re.search(r"COUNT (\d+)", said)
            result["count"] = int(m.group(1)) if m else None
        save_test(data_dir, result)
        return tested(data_dir)
    finally:
        _lock.release()


def forget(data_dir):
    """Copies stop: the settings go back to Off and the kept passwords go. Copies already made stay where they are."""
    save(data_dir, {**settings(data_dir), "kind": "off", "service": ""}, {"smb_password": "", "rclone_config": ""})
    try:
        os.remove(os.path.join(data_dir, TESTED))
    except OSError:
        pass
