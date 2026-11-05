#!/usr/bin/env python3
"""starboard-pool: the root helper behind System, Storage, Pool and the terminal set-up's Your drives step (DASH-87).

Starboard never runs as root. This one file, standard library only, is installed by deploy/install-pool.sh as
/usr/local/bin/starboard-pool and runs as root: from a systemd .path unit when Starboard drops a request in
FOLDER/requests (the only place Starboard may write), from a nightly timer, or from the terminal with sudo.

  starboard-pool drives                        list the drives and what each is used for
  starboard-pool plan add DRIVE --as pool|parity|copy [--erase] [--folders a,b]
  starboard-pool plan remove DRIVE             take a drive out (its files go to the other drives first)
  starboard-pool plan balance                  work out which folders to move
  starboard-pool apply PLAN [--confirm DRIVE=1234]   do a plan made in the last 15 minutes
  starboard-pool stop                          stop a balance or a take-out between two folders
  starboard-pool status                        the pool, its drives, backup drives and the last job
  starboard-pool nightly                       the backup drives' check (SnapRAID) and copy (rsync)
  starboard-pool serve FOLDER                  answer Starboard's requests (run by the .path unit)

Rules it never breaks: it never offers or touches the system drive or a drive in RAID, LVM or ZFS; it erases a
drive only when the request carries the end of that drive's serial number; it changes only the lines between its
own markers in /etc/fstab and only a snapraid.conf it wrote; a pool it did not make is shown, never changed; every
change is planned first (a dry run) and the plan is refused if a drive changed since. Starboard asks for the
person's password before it sends anything that changes a drive.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time

VERSION = 1
BEGIN = "# starboard-pool begin: written by Starboard's pool helper; change these lines on System, Storage, Pool"
END = "# starboard-pool end"
SNAP_HEAD = "# Written by Starboard's pool helper (starboard-pool). Change it on System, Storage, Pool."
PLAN_MINUTES = 15
SYSTEM_MOUNTS = ("/", "/boot", "/boot/efi", "/home", "/var", "/usr", "/srv", "/opt")
MEMBER_FS = {"linux_raid_member": "RAID", "LVM2_member": "LVM", "zfs_member": "ZFS", "crypto_LUKS": "encryption",
             "bcache": "bcache", "ceph": "Ceph"}
KEEPABLE = {"ext4", "ext3", "ext2", "xfs", "btrfs", "ntfs", "ntfs3", "exfat", "vfat"}
POOL_OPTIONS = ("defaults,allow_other,category.create=mfs,moveonenospc=true,func.getattr=newest,cache.files=off,"
                "dropcacheonclose=true,fsname=starboard-pool,nofail")
MOUNT_OPTIONS = "defaults,nofail,x-systemd.device-timeout=30s"
ACTIONS = {"drives", "plan", "apply", "stop", "status"}
REQUEST_MAX = 64 * 1024
UNIT_DEPTH = 3          # media/tv/Series: the folder that moves as one piece when balancing
RECENT = 3600           # folders changed in the last hour are left where they are (downloads still being written)
TOLERANCE = 0.05        # balanced when every drive is within 5 percentage points of the same fill
SPEED = 80 * 1024 ** 2  # bytes a second, for the time a balance should take


class Refused(Exception):
    """A plan or request that the helper will not carry out, in words for the person."""


def now():
    return time.time()


def human(n):
    """Sizes as Starboard's pages show them (common.js formatBytes): 1024 to a step, one decimal from GB."""
    n = float(n or 0)
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024
        i += 1
    return f"{n:.1f} {units[i]}" if i >= 3 else f"{n:.0f} {units[i]}"


def write_json(path, data, mode=0o644):
    """Write by renaming a new file into place: never through a link someone planted, never half written."""
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    tmp = os.path.join(folder, f".{os.path.basename(path)}.{secrets.token_hex(4)}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


class Host:
    """Everything the helper touches on the computer, in one place, so tests can point it at a temporary folder and
    record commands instead of running them."""

    def __init__(self, root="/", exchange=None, run=None, lsblk=None, mounts=None):
        j = lambda *p: os.path.join(root, *[x.lstrip("/") for x in p])  # noqa: E731
        self.root = root
        # Files the helper edits, where they are on this computer (under root in the tests).
        self.fstab = j("/etc/fstab")
        self.snapraid_conf = j("/etc/snapraid.conf")
        self.state = j("/var/lib/starboard-pool")
        self.docker_dropin = j("/etc/systemd/system/docker.service.d/starboard-pool.conf")
        # Mount points as the computer sees them; real() gives where they are on disk in the tests.
        self.disks_dir = "/mnt/disks"
        self.backup_dir = "/mnt/backup"
        self.parity_dir = "/mnt/parity"
        self.pool = "/mnt/pool"
        self.exchange = exchange
        self._run = run
        self._lsblk = lsblk
        self._mounts = mounts
        self.log = []

    def real(self, path):
        return path if self.root == "/" else os.path.join(self.root, path.lstrip("/"))

    # Commands -----------------------------------------------------------------------------------------------
    def run(self, *cmd, check=True, timeout=None):
        self.log.append(list(cmd))
        if self._run:
            return self._run(list(cmd))
        p = subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout)
        if check and p.returncode != 0:
            raise Refused(f"{cmd[0]} stopped with an error: {(p.stderr or p.stdout).strip()[-400:]}")
        return p.stdout

    def lsblk(self):
        if self._lsblk is not None:
            return self._lsblk() if callable(self._lsblk) else self._lsblk
        out = subprocess.run(["lsblk", "-J", "-b", "-o", "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINTS,LABEL,UUID,MODEL,"
                              "SERIAL,TRAN,ROTA,RM"], capture_output=True, text=True, check=True).stdout
        return json.loads(out)

    def mounts(self):
        """{mount point: (source, file system type)} from /proc/self/mounts."""
        if self._mounts is not None:
            return self._mounts() if callable(self._mounts) else self._mounts
        out = {}
        with open("/proc/self/mounts", encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    out[parts[1].replace("\\040", " ")] = (parts[0], parts[2])
        return out

    def by_id(self, kname):
        """The stable name of a drive, /dev/disk/by-id/..., which does not change between starts as sda and sdb can."""
        folder = os.path.join(self.root, "dev/disk/by-id")
        best = ""
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return ""
        rank = ("ata-", "nvme-eui", "nvme-", "scsi-", "usb-", "virtio-", "wwn-")
        for n in names:
            if "-part" in n:
                continue
            if os.path.basename(os.path.realpath(os.path.join(folder, n))) == kname:
                if not best or next((i for i, r in enumerate(rank) if n.startswith(r)), 9) < \
                        next((i for i, r in enumerate(rank) if best.startswith(r)), 9):
                    best = n
        return "/dev/disk/by-id/" + best if best else ""

    def statvfs(self, path):
        try:
            s = os.statvfs(self.real(path))
        except OSError:
            return None
        return {"size": s.f_blocks * s.f_frsize, "free": s.f_bavail * s.f_frsize,
                "used": (s.f_blocks - s.f_bfree) * s.f_frsize}

    # State --------------------------------------------------------------------------------------------------
    def config(self):
        return read_json(os.path.join(self.state, "pool.json"), {"version": VERSION, "drives": [], "copy_folders": [],
                                                                 "check_at": "02:00", "delete_limit": 5})

    def save_config(self, cfg):
        write_json(os.path.join(self.state, "pool.json"), cfg, 0o600)

    def publish(self, name, data):
        """Results for Starboard: written where it reads them, readable, never writable by it."""
        if self.exchange:
            write_json(os.path.join(self.exchange, "status", name), data)


# Drives -----------------------------------------------------------------------------------------------------

def _walk(dev):
    yield dev
    for c in dev.get("children") or []:
        yield from _walk(c)


def drives(host):
    """Every whole drive, what is on it and what it may be used for. Each has 'use' (system, pool, parity, copy,
    other pool, in use, free) and, when it cannot be offered, 'blocked' in words."""
    cfg = host.config()
    ours = {d["by_id"]: d for d in cfg["drives"]}
    handmade = handmade_pool(host)
    out = []
    for dev in host.lsblk().get("blockdevices") or []:
        if dev.get("type") != "disk" or dev.get("name", "").startswith(("loop", "zram", "sr", "fd")):
            continue
        parts = []
        mounted, member, system = [], "", False
        for d in _walk(dev):
            for m in d.get("mountpoints") or []:
                if not m:
                    continue
                mounted.append(m)
                if m in SYSTEM_MOUNTS or m == "[SWAP]" or m.startswith("/boot"):
                    system = True
            if d.get("fstype") in MEMBER_FS:
                member = MEMBER_FS[d["fstype"]]
            if d is not dev and d.get("type") == "part":
                parts.append({"name": d.get("name"), "path": d.get("path") or "/dev/" + d.get("name", ""),
                              "size": d.get("size"), "fs": d.get("fstype") or "", "label": d.get("label") or "",
                              "uuid": d.get("uuid") or "", "mounted": [m for m in d.get("mountpoints") or [] if m]})
            if d.get("type") in ("lvm", "raid0", "raid1", "raid5", "raid6", "raid10", "crypt"):
                member = member or "LVM or RAID"
        if not parts and dev.get("fstype"):
            parts.append({"name": dev["name"], "path": dev.get("path") or "/dev/" + dev["name"], "size": dev.get("size"),
                          "fs": dev.get("fstype") or "", "label": dev.get("label") or "", "uuid": dev.get("uuid") or "",
                          "mounted": [m for m in dev.get("mountpoints") or [] if m], "whole": True})
        bid = host.by_id(dev["name"])
        serial = (dev.get("serial") or "").strip()
        item = {"name": dev["name"], "path": dev.get("path") or "/dev/" + dev["name"], "by_id": bid,
                "model": (dev.get("model") or "").strip(), "serial": serial, "ends": ends(serial, bid),
                "size": int(dev.get("size") or 0), "tran": dev.get("tran") or "", "rotational": bool(dev.get("rota")),
                "removable": bool(dev.get("rm")), "parts": parts, "mounted": mounted}
        if bid in ours:
            o = ours[bid]
            item.update(use=o["role"], label=o["label"], mount=o["mount"])
            st = host.statvfs(o["mount"])
            if st:
                item.update(used=st["used"], free=st["free"], fs_size=st["size"])
        elif system:
            item.update(use="system", blocked="This is the system drive, which Starboard never offers")
        elif member:
            item.update(use="in use", blocked=f"Part of {member}, which Starboard leaves alone")
        elif any(b == m or b.startswith(m.rstrip("/") + "/") for m in mounted for b in handmade.get("branches", [])):
            item.update(use="other pool", blocked="Part of a pool made outside Starboard, which Starboard only shows")
        elif not bid:
            item.update(use="in use", blocked="Starboard cannot find a stable name for this drive in /dev/disk/by-id")
        else:
            item["use"] = "free"
            item["files"] = sum(p["size"] or 0 for p in parts if p["fs"])
            if mounted:
                st = host.statvfs(mounted[0])
                if st:
                    item.update(used=st["used"], free=st["free"], fs_size=st["size"])
        out.append(item)
    return out


def ends(serial, bid=""):
    """The last 4 letters or numbers of the serial number, which the person types to confirm an erase."""
    text = re.sub(r"[^A-Za-z0-9]", "", serial or "") or re.sub(r"[^A-Za-z0-9]", "", os.path.basename(bid or ""))
    return text[-4:].upper()


def fingerprint(d):
    raw = json.dumps([d["by_id"], d["size"], [(p["name"], p["fs"], p["uuid"]) for p in d["parts"]]], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def find(host, ident, listing=None):
    for d in listing if listing is not None else drives(host):
        if ident in (d["by_id"], d["name"], d["path"], d.get("label")) or (d["by_id"] and ident == os.path.basename(d["by_id"])):
            return d
    raise Refused(f"There is no drive called {ident}")


# fstab and the pool -----------------------------------------------------------------------------------------

def read_fstab(host):
    try:
        with open(host.fstab, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        text = ""
    lines = text.splitlines()
    if BEGIN in lines:
        a = lines.index(BEGIN)
        if END not in lines[a:]:
            raise Refused("/etc/fstab has the start of Starboard's lines but not the end; put it right by hand first")
        b = lines.index(END, a)
        return lines[:a], lines[a + 1:b], lines[b + 1:]
    return lines, [], []


def handmade_pool(host):
    """A mergerfs pool made outside Starboard (such as a server set up by hand): its mount point and branches."""
    before, _, after = read_fstab(host)
    for line in before + after:
        f = line.split()
        if len(f) >= 3 and not line.lstrip().startswith("#") and f[2] in ("fuse.mergerfs", "mergerfs"):
            return {"mount": f[1], "branches": [b for b in f[0].split(":") if b]}
    for point, (src, kind) in host.mounts().items():
        if kind == "fuse.mergerfs" and "starboard-pool" not in src and point != host.pool:
            return {"mount": point, "branches": []}
    return {}


def fstab_block(host, cfg):
    lines = []
    for d in cfg["drives"]:
        if d.get("own_line"):
            lines.append(f"UUID={d['uuid']} {d['mount']} {d['fs']} {MOUNT_OPTIONS} 0 2")
    branches = [d["mount"] for d in cfg["drives"] if d["role"] == "pool"]
    if branches:
        smallest = min(d.get("size") or 0 for d in cfg["drives"] if d["role"] == "pool")
        keep = max(min(50 * 1000 ** 3, int(smallest * 0.02)), 64 * 1024 ** 2)
        lines.append(f"{':'.join(branches)} {host.pool} fuse.mergerfs {POOL_OPTIONS},minfreespace={keep // 1024 ** 2}M 0 0")
    return lines


def write_fstab(host, cfg):
    """Replace only Starboard's own block: saved first, written to a new file, checked, then renamed into place."""
    before, _, after = read_fstab(host)
    block = fstab_block(host, cfg)
    lines = before + ([BEGIN] + block + [END] if block else []) + after
    text = "\n".join(lines).rstrip("\n") + "\n"
    save_copy(host, host.fstab)
    tmp = host.fstab + ".starboard-new"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    if host.root == "/":
        p = subprocess.run(["findmnt", "--verify", "--tab-file", tmp], capture_output=True, text=True)
        if p.returncode != 0 and "error" in (p.stdout + p.stderr).lower():
            os.unlink(tmp)
            raise Refused("The new /etc/fstab did not pass its check, so nothing was changed: " + p.stdout.strip()[-300:])
    os.chmod(tmp, 0o644)
    os.replace(tmp, host.fstab)
    return block


def save_copy(host, path):
    if os.path.exists(path):
        folder = os.path.join(host.state, "saved")
        os.makedirs(folder, mode=0o700, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
        shutil.copy2(path, os.path.join(folder, f"{os.path.basename(path)}.{stamp}"))


def snapraid_text(cfg, host):
    parity = [d for d in cfg["drives"] if d["role"] == "parity"]
    data = [d for d in cfg["drives"] if d["role"] == "pool"]
    if not parity or not data:
        return ""
    lines = [SNAP_HEAD]
    names = ("parity", "2-parity", "3-parity")
    for n, d in enumerate(parity[:3]):
        lines.append(f"{names[n]} {d['mount']}/snapraid.parity")
    lines.append(f"content {host.state}/snapraid.content")
    for d in data[:2]:
        lines.append(f"content {d['mount']}/.snapraid.content")
    for d in data:
        lines.append(f"data {d['label']} {d['mount']}/")
    lines += ["exclude /lost+found/", "exclude *.unrecoverable", "exclude *.!qB", "exclude *.part", "exclude /.Trash-*/",
              "exclude /torrents/", "exclude /usenet/incomplete/", "autosave 500"]
    return "\n".join(lines) + "\n"


def write_snapraid(host, cfg):
    text = snapraid_text(cfg, host)
    if os.path.exists(host.snapraid_conf):
        with open(host.snapraid_conf, encoding="utf-8") as f:
            if not f.read().startswith(SNAP_HEAD):
                raise Refused("/etc/snapraid.conf was not written by Starboard, so Starboard leaves it alone")
        save_copy(host, host.snapraid_conf)
        if not text:
            os.replace(host.snapraid_conf, os.path.join(host.state, "saved", "snapraid.conf.unused"))
            return
    if text:
        tmp = host.snapraid_conf + ".starboard-new"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, host.snapraid_conf)


# Plans ------------------------------------------------------------------------------------------------------

def next_label(cfg, role):
    stem = {"pool": "disk", "parity": "parity", "copy": "copy"}[role]
    used = {d["label"] for d in cfg["drives"]}
    n = 1
    while f"{stem}{n}" in used:
        n += 1
    return f"{stem}{n}"


def tools(host):
    have = lambda name: bool(shutil.which(name)) if host.root == "/" else True  # noqa: E731
    return {t: have(t) for t in ("mergerfs", "rsync", "sgdisk", "mkfs.ext4", "wipefs", "snapraid", "mergerfs.balance")}


def plan_add(host, ident, role, erase=False, folders=()):
    if role not in ("pool", "parity", "copy"):
        raise Refused("A drive can be added to the pool, or as a parity or copy drive")
    if handmade_pool(host):
        raise Refused("This computer has a pool made outside Starboard. Starboard shows it, but does not change it")
    cfg = host.config()
    listing = drives(host)
    d = find(host, ident, listing)
    if d["use"] != "free":
        raise Refused(d.get("blocked") or f"{d['model'] or d['name']} is already used as {d['use']}")
    t = tools(host)
    need = ["mergerfs"] if role == "pool" else []
    need += ["snapraid"] if role == "parity" else []
    need += ["rsync"] if role == "copy" else []
    need += ["sgdisk", "mkfs.ext4", "wipefs"] if erase else []
    missing = [n for n in need if not t[n]]
    if missing:
        raise Refused("Install these first: " + ", ".join(missing) + " (for example: sudo apt install " +
                      " ".join({"mkfs.ext4": "e2fsprogs", "sgdisk": "gdisk", "wipefs": "util-linux"}.get(m, m) for m in missing) + ")")
    keepable = [p for p in d["parts"] if p["fs"] in KEEPABLE]
    if not erase and not keepable:
        raise Refused("This drive has no files to keep, so it has to be erased and prepared to be used")
    if not erase and len(keepable) > 1:
        raise Refused("This drive has more than one partition with files; Starboard only keeps a drive with one")
    if role == "parity":
        biggest = max([x.get("size", 0) for x in cfg["drives"] if x["role"] == "pool"] or [0])
        if d["size"] < biggest:
            raise Refused(f"A parity drive must be at least as big as the biggest pool drive ({human(biggest)})")
        if not erase:
            raise Refused("A parity drive is always erased first: parity needs a whole drive to itself")
    if erase and any(fstab_has(host, p) for p in d["parts"]):
        raise Refused("/etc/fstab already mounts this drive. Take that line out first, or the computer may wait for it at start")
    if role == "pool" and not any(x["role"] == "pool" for x in cfg["drives"]) and os.path.isdir(host.real(host.pool)) \
            and not os.path.ismount(host.real(host.pool)) and os.listdir(host.real(host.pool)):
        raise Refused(f"{host.pool} already has files in it. Move them first, so the pool does not hide them")
    label = next_label(cfg, role)
    base = {"pool": host.disks_dir, "parity": host.parity_dir, "copy": host.backup_dir}[role]
    steps, entry = [], {"by_id": d["by_id"], "serial": d["serial"], "role": role, "label": label, "size": d["size"],
                        "model": d["model"]}
    name = f"{d['model'] or 'Drive'} {human(d['size'])}, serial ends {d['ends']}"
    if erase:
        part = d["by_id"] + "-part1"
        if d["mounted"]:
            steps.append({"do": "unmount", "say": f"Unmount {name} from {', '.join(d['mounted'])}", "points": d["mounted"]})
        steps.append({"do": "erase", "say": f"Erase {name} and make one ext4 partition labelled {label}",
                      "danger": True, "by_id": d["by_id"], "label": label, "part": part,
                      "commands": [f"wipefs -a {d['by_id']}", f"sgdisk --zap-all {d['by_id']}",
                                   f"sgdisk -n 1:0:0 -t 1:8300 -c 1:{label} {d['by_id']}",
                                   f"mkfs.ext4 -F -L {label} -m 0 {'-T largefile4 ' if role != 'copy' else ''}{part}"]})
        entry.update(fs="ext4", mount=f"{base}/{label}", own_line=True)
    else:
        p = keepable[0]
        entry.update(fs=p["fs"], uuid=p["uuid"])
        line = fstab_has(host, p)
        if line:
            entry.update(mount=line, own_line=False)
            steps.append({"do": "note", "say": f"Keep the files: use {name} where it is mounted now, {line}"})
        else:
            entry.update(mount=f"{base}/{label}", own_line=True)
            if p["mounted"]:
                steps.append({"do": "unmount", "say": f"Unmount it from {', '.join(p['mounted'])}", "points": p["mounted"]})
            steps.append({"do": "note", "say": f"Keep the files on {name} ({p['fs']}, {human(p['size'])})"})
        if p["fs"] in ("ntfs", "ntfs3", "exfat", "vfat"):
            steps.append({"do": "note", "say": f"It stays {p['fs'].upper()}. ext4 copes better with power cuts; "
                                               "the help says how to change it later"})
    if entry.get("own_line"):
        steps.append({"do": "mount", "say": f"Mount it at {entry['mount']} by its ID, with nofail, so the computer "
                                             "still starts if it is missing", "mount": entry["mount"],
                      "commands": [f"fstab: UUID=… {entry['mount']} {entry['fs']} {MOUNT_OPTIONS} 0 2"]})
    pool_drives = [x for x in cfg["drives"] if x["role"] == "pool"]
    if role == "pool":
        total = sum(x.get("size", 0) for x in pool_drives)
        if pool_drives:
            steps.append({"do": "branch", "say": f"Add it to the pool. {host.pool} grows from "
                          f"{human(total)} to {human(total + d['size'])}. Files already in the pool stay where they are"})
        else:
            steps.append({"do": "branch", "say": f"Make the pool at {host.pool} from this drive"})
            steps.append({"do": "protect", "say": "Make Docker wait for the pool, and lock the empty folder under it, "
                          "so the apps never run against an empty folder"})
    if role == "parity" or (role == "pool" and any(x["role"] == "parity" for x in cfg["drives"])):
        steps.append({"do": "snapraid", "say": "Write /etc/snapraid.conf for the new drive; the next nightly check takes longer"})
    if role == "parity":
        steps.append({"do": "note", "say": f"The first check starts tonight at {cfg['check_at']} and can take many hours"})
    if role == "copy":
        entry["folders"] = list(folders) or ["media"]
        steps.append({"do": "note", "say": "Copy " + ", ".join(entry["folders"]) + f" from the pool every night at "
                      f"{cfg['check_at']}; files deleted in the pool move to a dated .removed folder on it, never erased"})
    steps.append({"do": "note", "say": "Save a copy of /etc/fstab (and /etc/snapraid.conf) first, in "
                                      "/var/lib/starboard-pool/saved"})
    return save_plan(host, {"action": "add", "drive": d, "entry": entry, "erase": erase, "steps": steps,
                            "fingerprints": {d["by_id"]: fingerprint(d)}})


def fstab_has(host, part):
    """Where an fstab line outside Starboard's block already mounts this partition, if one does."""
    before, _, after = read_fstab(host)
    for line in before + after:
        f = line.split()
        if len(f) >= 2 and not line.lstrip().startswith("#"):
            if f[0] in (f"UUID={part['uuid']}", part["path"]) or (part.get("label") and f[0] == f"LABEL={part['label']}"):
                return f[1]
    return ""


def save_plan(host, plan):
    plan.update(id=secrets.token_hex(6), made=now(), expires=now() + PLAN_MINUTES * 60,
                erases=[s["by_id"] for s in plan["steps"] if s["do"] == "erase"])
    write_json(os.path.join(host.state, "plans", plan["id"] + ".json"), plan, 0o600)
    public = {k: v for k, v in plan.items() if k not in ("fingerprints",)}
    host.publish(f"plans/{plan['id']}.json", public)
    return public


def plan_remove(host, ident):
    cfg = host.config()
    d = next((x for x in cfg["drives"] if ident in (x["by_id"], x["label"], os.path.basename(x["by_id"]))), None)
    if not d:
        raise Refused("That drive is not in Starboard's pool or a backup drive")
    steps, moves = [], []
    if d["role"] == "pool":
        others = [x for x in cfg["drives"] if x["role"] == "pool" and x is not d]
        if not others:
            raise Refused("This is the only drive in the pool. Add another drive first, so its files have somewhere to go")
        branches = {x["mount"]: host.statvfs(x["mount"]) or {"size": x["size"], "used": 0, "free": x["size"]} for x in cfg["drives"] if x["role"] == "pool"}
        moves = drain_moves(host, d["mount"], branches)
        size = sum(m["bytes"] for m in moves)
        steps.append({"do": "drain", "say": f"Move {human(size)} in {len(moves)} folders from {d['label']} to the other "
                      f"pool drives, about {duration(size)}. The pool shows every file in the same place throughout"})
        steps.append({"do": "branch", "say": f"Take {d['label']} out of the pool"})
        if any(x["role"] == "parity" for x in cfg["drives"]):
            steps.append({"do": "snapraid", "say": "Take it out of /etc/snapraid.conf; the next check rebuilds the parity"})
    elif d["role"] == "parity":
        steps.append({"do": "snapraid", "say": f"Stop using {d['label']} for parity. The pool is not protected until "
                      "another parity drive is added"})
    else:
        steps.append({"do": "note", "say": f"Stop copying to {d['label']}. The copy already on it stays"})
    if d.get("own_line"):
        steps.append({"do": "unmount", "say": f"Unmount {d['mount']} and take its line out of /etc/fstab. The drive "
                      "is not erased", "points": [d["mount"]]})
    steps.append({"do": "note", "say": "Save a copy of /etc/fstab first, in /var/lib/starboard-pool/saved"})
    drive = next((x for x in drives(host) if x["by_id"] == d["by_id"]), None)
    return save_plan(host, {"action": "remove", "entry": d, "moves": moves, "steps": steps,
                            "fingerprints": {d["by_id"]: fingerprint(drive)} if drive else {}})


def duration(nbytes):
    secs = nbytes / SPEED
    if secs < 90:
        return "a minute"
    if secs < 5400:
        return f"{round(secs / 60)} minutes"
    return f"{round(secs / 3600)} hours"


# Balancing --------------------------------------------------------------------------------------------------

def units(branch, depth=UNIT_DEPTH):
    """The pieces that move as one: each folder UNIT_DEPTH levels down (media/tv/Series), and any loose file above
    that level. {relative path: (bytes on disk, newest change)}."""
    out = {}
    branch = branch.rstrip("/")
    for top, dirs, files in os.walk(branch):
        rel = os.path.relpath(top, branch)
        parts = [] if rel == "." else rel.split(os.sep)
        if not parts:
            dirs[:] = [x for x in dirs if x not in ("lost+found", ".snapraid") and not x.startswith((".Trash", ".removed"))]
        for name in files:
            if not parts and name.startswith((".snapraid", "snapraid.")):
                continue
            try:
                st = os.lstat(os.path.join(top, name))
            except OSError:
                continue
            key = os.path.join(*parts[:depth]) if len(parts) >= depth else os.path.join(*parts, name)
            size, newest = out.get(key, (0, 0))
            out[key] = (size + st.st_blocks * 512, max(newest, st.st_mtime))
    return out


def balance_moves(host, branches, tolerance=TOLERANCE, now_=None, recent=RECENT):
    """branches: {mount: {"size", "used"}}. Greedy: take the biggest piece from the fullest drive that fits on the
    emptiest without pushing it over the target, until every drive is within the tolerance."""
    now_ = now_ or now()
    used = {b: s["used"] for b, s in branches.items()}
    size = {b: s["size"] for b, s in branches.items()}
    total_size = sum(size.values()) or 1
    target = sum(used.values()) / total_size
    real = host.real if host else (lambda p: p)
    pieces = {b: units(real(b)) for b in branches}
    taken = {b: set(pieces[b]) & set().union(*(set(pieces[o]) for o in branches if o != b)) for b in branches}
    moves = []
    for _ in range(100000):
        fill = {b: used[b] / size[b] for b in branches if size[b]}
        src = max(fill, key=fill.get)
        dst = min(fill, key=fill.get)
        if fill[src] - target <= tolerance and target - fill[dst] <= tolerance:
            break
        room = min((target - fill[dst]) * size[dst] + tolerance * size[dst] / 2, (fill[src] - target) * size[src] + tolerance * size[src] / 2)
        best = None
        for rel, (nbytes, newest) in pieces[src].items():
            if rel in taken[src] or now_ - newest < recent or nbytes <= 0 or nbytes > room:
                continue
            if os.path.exists(os.path.join(real(dst), rel)):
                continue
            if best is None or nbytes > best[1]:
                best = (rel, nbytes)
        if not best:
            break
        rel, nbytes = best
        moves.append({"from": src, "to": dst, "path": rel, "bytes": nbytes, "mtime": pieces[src][rel][1]})
        del pieces[src][rel]
        used[src] -= nbytes
        used[dst] += nbytes
    return moves, {b: {"size": size[b], "before": branches[b]["used"], "after": used[b]} for b in branches}


def drain_moves(host, mount, branches):
    """Every piece on one drive, each to whichever other pool drive has the most room then."""
    free = {b: s["size"] - s["used"] - (64 * 1024 ** 2) for b, s in branches.items() if b != mount}
    moves = []
    for rel, (nbytes, newest) in sorted(units(host.real(mount)).items(), key=lambda kv: -kv[1][0]):
        dst = max(free, key=free.get)
        if free[dst] < nbytes:
            raise Refused(f"The other pool drives do not have room for {rel} ({human(nbytes)}). Add a drive first")
        moves.append({"from": mount, "to": dst, "path": rel, "bytes": nbytes, "mtime": newest})
        free[dst] -= nbytes
    return moves


def plan_balance(host, pause=(), engine="starboard"):
    cfg = host.config()
    pool = [x for x in cfg["drives"] if x["role"] == "pool"]
    if len(pool) < 2:
        raise Refused("A pool needs two drives or more to balance")
    if engine == "mergerfs.balance" and not tools(host)["mergerfs.balance"]:
        raise Refused("mergerfs.balance is not installed. Starboard's own balancer needs nothing extra")
    branches = {x["mount"]: host.statvfs(x["mount"]) or {"size": x["size"], "used": 0} for x in pool}
    moves, sides = balance_moves(host, branches)
    total = sum(m["bytes"] for m in moves)
    label = {x["mount"]: x["label"] for x in pool}
    steps = [{"do": "note", "say": "Nothing needs moving: the drives are within 5% of each other" if not moves else
              f"Move {human(total)} in {len(moves)} folders, about {duration(total)} at low priority"}]
    if engine == "mergerfs.balance":
        steps.append({"do": "note", "say": "Run mergerfs.balance instead of Starboard's balancer: it moves single "
                      "files, so a series can end up spread over several drives"})
    return save_plan(host, {"action": "balance", "engine": engine, "moves": moves, "pause": list(pause),
                            "drives": [{"label": label[b], "mount": b, **s} for b, s in sides.items()],
                            "steps": steps, "fingerprints": {}})


# Applying ---------------------------------------------------------------------------------------------------

def load_plan(host, plan_id):
    if not re.fullmatch(r"[0-9a-f]{12}", plan_id or ""):
        raise Refused("That is not a plan")
    plan = read_json(os.path.join(host.state, "plans", plan_id + ".json"))
    if not plan:
        raise Refused("That plan is not there any more; check again")
    if plan["expires"] < now():
        raise Refused(f"That check is more than {PLAN_MINUTES} minutes old; check again")
    if plan.get("done"):
        raise Refused("That plan has already been carried out")
    return plan


def verify(host, plan, confirm):
    """Before anything is written: the drives are as they were in the check, and every erase is confirmed."""
    listing = drives(host)
    for bid, fp in plan["fingerprints"].items():
        d = next((x for x in listing if x["by_id"] == bid), None)
        if not d or fingerprint(d) != fp:
            raise Refused("The drive changed since the check, so nothing was done. Check again")
    for bid in plan["erases"]:
        d = next(x for x in listing if x["by_id"] == bid)
        typed = re.sub(r"[^A-Za-z0-9]", "", str((confirm or {}).get(bid, ""))).upper()
        if not typed or typed != d["ends"]:
            raise Refused(f"To erase {d['model'] or d['name']}, type the last 4 characters of its serial number, {d['ends']}")


class Job:
    """Progress that Starboard and the terminal can read, and that survives a power cut (DASH-88 reads it)."""

    def __init__(self, host, plan, out=None):
        self.host, self.plan, self.out = host, plan, out
        self.data = {"id": plan["id"], "action": plan["action"], "state": "running", "started": now(), "steps": [],
                     "moved": 0, "of": len(plan.get("moves") or [])}
        self.save()

    def save(self):
        write_json(os.path.join(self.host.state, "jobs", "current.json"), self.data, 0o600)
        self.host.publish("job.json", self.data)

    def step(self, say, state="done"):
        self.data["steps"].append({"say": say, "state": state, "at": now()})
        self.save()
        if self.out:
            mark = {"done": "✔", "failed": "✖", "skipped": "-"}.get(state, "·")
            print(f"  {mark} {say}", file=self.out, flush=True)

    def finish(self, state, say=""):
        self.data.update(state=state, finished=now(), result=say)
        self.save()


def stop_requested(host):
    return os.path.exists(os.path.join(host.state, "stop"))


def apply(host, plan_id, confirm=None, out=None):
    os.makedirs(host.state, mode=0o700, exist_ok=True)
    lock = open(os.path.join(host.state, "lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise Refused("Another pool job is running. Wait for it to finish, or stop it") from None
    plan = load_plan(host, plan_id)
    verify(host, plan, confirm)
    plan["done"] = now()
    write_json(os.path.join(host.state, "plans", plan_id + ".json"), plan, 0o600)
    try:
        os.unlink(os.path.join(host.state, "stop"))
    except FileNotFoundError:
        pass
    job = Job(host, plan, out)
    try:
        {"add": apply_add, "remove": apply_remove, "balance": apply_balance}[plan["action"]](host, plan, job)
    except Exception as e:  # noqa: BLE001 - every failure is reported in words, and the job is marked failed
        job.step(str(e) if isinstance(e, Refused) else f"Stopped with an error: {e}", "failed")
        job.finish("failed", str(e))
        raise
    finally:
        publish_status(host)
        lock.close()
    if job.data["state"] == "running":
        job.finish("done")
    return job.data


def apply_add(host, plan, job):
    cfg = host.config()
    e = dict(plan["entry"])
    for s in plan["steps"]:
        if s["do"] == "unmount":
            for p in s["points"]:
                host.run("umount", p)
            job.step(s["say"])
        elif s["do"] == "erase":
            host.run("wipefs", "-a", e["by_id"])
            host.run("sgdisk", "--zap-all", e["by_id"])
            host.run("sgdisk", "-n", "1:0:0", "-t", "1:8300", "-c", f"1:{e['label']}", e["by_id"])
            host.run("udevadm", "settle", check=False)
            wait_for(host, s["part"])
            host.run("mkfs.ext4", "-F", "-q", "-L", e["label"], "-m", "0", *(["-T", "largefile4"] if e["role"] != "copy" else []), s["part"])
            host.run("udevadm", "settle", check=False)
            e["uuid"] = host.run("blkid", "-s", "UUID", "-o", "value", s["part"]).strip() if host.root == "/" else "TEST-UUID-" + e["label"]
            job.step(s["say"])
    if e.get("own_line"):
        os.makedirs(host.real(e["mount"]), exist_ok=True)
    cfg["drives"].append(e)
    write_fstab(host, cfg)
    if e.get("own_line"):
        host.run("systemctl", "daemon-reload", check=False)
        host.run("mount", e["mount"])
        job.step(f"Mounted at {e['mount']}")
    host.save_config(cfg)
    if e["role"] == "pool":
        pool_branches(host, cfg, add=e["mount"])
        job.step(f"Added to the pool at {host.pool}")
        if any(s["do"] == "protect" for s in plan["steps"]):
            protect(host)
            job.step("Docker now waits for the pool, and the empty folder under it is locked")
    if any(s["do"] == "snapraid" for s in plan["steps"]):
        write_snapraid(host, cfg)
        job.step("Wrote /etc/snapraid.conf")
    if e["role"] in ("parity", "copy"):
        host.run("systemctl", "enable", "--now", "starboard-pool-nightly.timer", check=False)
        job.step(f"The nightly {'check' if e['role'] == 'parity' else 'copy'} is set for {cfg['check_at']}")


def wait_for(host, path, seconds=30):
    if host.root != "/":
        return
    for _ in range(seconds * 2):
        if os.path.exists(path):
            return
        time.sleep(0.5)
    raise Refused(f"{path} did not appear after the drive was prepared")


def pool_branches(host, cfg, add=None, remove=None):
    """Change the pool while it is in use, through mergerfs's control file, or mount it if it is not mounted."""
    if host.root != "/":
        host.run("pool", "+" + add if add else "-" + remove)
        return
    if os.path.ismount(host.pool):
        ctl = os.path.join(host.pool, ".mergerfs")
        os.setxattr(ctl, "user.mergerfs.branches", (f"+>{add}" if add else f"-{remove}").encode())
    elif add:
        os.makedirs(host.pool, exist_ok=True)
        host.run("chattr", "+i", host.pool, check=False)
        host.run("systemctl", "daemon-reload", check=False)
        host.run("mount", host.pool)


def protect(host):
    os.makedirs(os.path.dirname(host.docker_dropin), exist_ok=True)
    with open(host.docker_dropin, "w", encoding="utf-8") as f:
        f.write(f"# Written by Starboard's pool helper: the apps never start against an empty {host.pool}.\n"
                f"[Unit]\nRequiresMountsFor={host.pool}\n")
    host.run("systemctl", "daemon-reload", check=False)


def move_piece(host, m, job):
    """Copy one folder to the emptier drive, check the copy, then remove it from the fuller one."""
    src = os.path.join(host.real(m["from"]), m["path"])
    dst = os.path.join(host.real(m["to"]), m["path"])
    if not os.path.exists(src):
        return "gone"
    if os.path.exists(dst):
        return "there"
    st = units_newest(src)
    if st > m["mtime"] + 1:
        return "changed"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    isdir = os.path.isdir(src)
    a, b = (src + "/", dst + "/") if isdir else (src, dst)
    try:
        host.run("rsync", "-aHAX", "--numeric-ids", a, b)
        left = host.run("rsync", "-aHAXn", "--numeric-ids", "--itemize-changes", a, b)
    except Exception:
        shutil.rmtree(dst, ignore_errors=True) if isdir else _unlink(dst)
        raise
    if (left or "").strip():
        shutil.rmtree(dst, ignore_errors=True) if isdir else _unlink(dst)
        return "changed"
    shutil.rmtree(src) if isdir else os.unlink(src)
    return "moved"


def _unlink(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def units_newest(path):
    if not os.path.isdir(path):
        return os.lstat(path).st_mtime
    newest = 0
    for top, _, files in os.walk(path):
        for f in files:
            try:
                newest = max(newest, os.lstat(os.path.join(top, f)).st_mtime)
            except OSError:
                pass
    return newest


def in_pause(windows, when=None):
    t = (when or datetime.datetime.now()).strftime("%H:%M")
    for a, b in windows or []:
        if (a <= t < b) if a <= b else (t >= a or t < b):
            return True
    return False


def run_moves(host, plan, job):
    skipped = 0
    for m in plan["moves"]:
        if stop_requested(host):
            job.step(f"Stopped. {job.data['moved']} of {len(plan['moves'])} folders moved; they stay moved", "skipped")
            job.finish("stopped")
            return False
        while in_pause(plan.get("pause")):
            job.data["paused"] = True
            job.save()
            time.sleep(60)
            if stop_requested(host):
                break
        job.data.pop("paused", None)
        job.data["current"] = m["path"]
        job.save()
        result = move_piece(host, m, job)
        if result == "moved":
            job.data["moved"] += 1
        else:
            skipped += 1
    job.data.pop("current", None)
    job.step(f"Moved {job.data['moved']} folders" + (f"; left {skipped} where they were, because they changed "
                                                       "or were already on the other drive" if skipped else ""))
    return True


def apply_balance(host, plan, job):
    if plan.get("engine") == "mergerfs.balance":
        host.run("mergerfs.balance", "-p", "2", host.pool)
        job.step("mergerfs.balance finished")
        return
    run_moves(host, plan, job)


def apply_remove(host, plan, job):
    cfg = host.config()
    e = next(x for x in cfg["drives"] if x["by_id"] == plan["entry"]["by_id"])
    if e["role"] == "pool":
        if not run_moves(host, plan, job):
            return
        left = units(host.real(e["mount"]))
        if left:
            raise Refused(f"{len(left)} folders are still on {e['label']} (they changed while moving). Take it out again")
        pool_branches(host, cfg, remove=e["mount"])
        job.step(f"Took {e['label']} out of the pool")
    cfg["drives"] = [x for x in cfg["drives"] if x["by_id"] != e["by_id"]]
    if e["role"] in ("pool", "parity") and (os.path.exists(host.snapraid_conf)):
        write_snapraid(host, cfg)
        cfg["force_empty"] = e["role"] == "pool"
        job.step("Updated /etc/snapraid.conf")
    write_fstab(host, cfg)
    host.save_config(cfg)
    if e.get("own_line"):
        host.run("umount", e["mount"], check=False)
        job.step(f"Unmounted {e['mount']}; the drive is not erased")


# Nightly ----------------------------------------------------------------------------------------------------

def nightly(host, out=None):
    cfg = host.config()
    report = {"at": now(), "results": []}
    parity = [d for d in cfg["drives"] if d["role"] == "parity"]
    if parity and os.path.exists(host.snapraid_conf):
        diff = subprocess.run(["snapraid", "diff"], capture_output=True, text=True)
        removed = int((re.search(r"(\d+) removed", diff.stdout) or [0, 0])[1])
        files = int((re.search(r"(\d+) equal", diff.stdout) or [0, 0])[1]) + removed
        limit = cfg.get("delete_limit", 5)
        if files and removed * 100 / files > limit:
            report["results"].append({"what": "parity", "state": "skipped",
                                      "say": f"{removed} files were deleted since the last check, more than {limit}%. "
                                             "The check did not run, so they can still be got back. Check the pool, then run it from Starboard"})
        else:
            cmd = ["nice", "-n", "19", "ionice", "-c", "3", "snapraid", "sync"] + (["--force-empty"] if cfg.get("force_empty") else [])
            p = subprocess.run(cmd, capture_output=True, text=True)
            ok = p.returncode == 0
            if ok and cfg.get("force_empty"):
                cfg.pop("force_empty")
                host.save_config(cfg)
            if ok and datetime.date.today().weekday() == 6:
                subprocess.run(["nice", "-n", "19", "ionice", "-c", "3", "snapraid", "scrub", "-p", "8", "-o", "10"],
                               capture_output=True, text=True)
            report["results"].append({"what": "parity", "state": "done" if ok else "failed",
                                      "say": "Every file is protected" if ok else (p.stderr or p.stdout).strip()[-300:]})
    for d in [d for d in cfg["drives"] if d["role"] == "copy"]:
        stamp = datetime.date.today().isoformat()
        bad = 0
        for folder in d.get("folders") or []:
            src = os.path.join(host.pool, folder.strip("/"))
            if not os.path.isdir(src):
                continue
            dst = os.path.join(d["mount"], folder.strip("/"))
            os.makedirs(dst, exist_ok=True)
            p = subprocess.run(["nice", "-n", "19", "ionice", "-c", "3", "rsync", "-aH", "--delete", "--backup",
                                f"--backup-dir={d['mount']}/.removed/{stamp}/{folder.strip('/')}", src + "/", dst + "/"],
                               capture_output=True, text=True)
            bad += p.returncode not in (0, 24)
        report["results"].append({"what": d["label"], "state": "failed" if bad else "done",
                                  "say": "Copied" if not bad else f"{bad} folders did not copy completely"})
    write_json(os.path.join(host.state, "nightly.json"), report, 0o600)
    host.publish("nightly.json", report)
    return report


# Status and requests ----------------------------------------------------------------------------------------

def status(host):
    cfg = host.config()
    listing = drives(host)
    pool = host.statvfs(host.pool) if os.path.ismount(host.real(host.pool)) or host.root != "/" else None
    return {"version": VERSION, "at": now(), "managed": bool(cfg["drives"]), "pool": host.pool,
            "mounted": bool(pool), "space": pool, "handmade": handmade_pool(host), "drives": listing,
            "check_at": cfg["check_at"], "tools": tools(host), "nightly": read_json(os.path.join(host.state, "nightly.json")),
            "job": read_json(os.path.join(host.state, "jobs", "current.json"))}


def publish_status(host):
    try:
        host.publish("status.json", status(host))
    except Exception as e:  # noqa: BLE001
        host.publish("status.json", {"version": VERSION, "at": now(), "error": str(e)})


def read_request(path):
    """One request file from Starboard's folder: a regular file, not a link, small, and a known action."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as f:
        if not os.path.isfile(path) or os.fstat(f.fileno()).st_size > REQUEST_MAX:
            raise Refused("That request is too large")
        data = json.loads(f.read(REQUEST_MAX))
    if not isinstance(data, dict) or data.get("action") not in ACTIONS:
        raise Refused("Starboard asked for something the pool helper does not do")
    if not re.fullmatch(r"[0-9a-f]{8,32}", str(data.get("id", ""))):
        raise Refused("That request has no proper ID")
    return data


def handle(host, req):
    act = req["action"]
    if act in ("drives", "status"):
        return status(host)
    if act == "plan":
        kind = req.get("kind")
        if kind == "add":
            return plan_add(host, str(req.get("drive", "")), str(req.get("as", "")), bool(req.get("erase")),
                            [str(x) for x in req.get("folders") or []][:20])
        if kind == "remove":
            return plan_remove(host, str(req.get("drive", "")))
        if kind == "balance":
            pause = [[str(a), str(b)] for a, b in (req.get("pause") or [])][:4]
            return plan_balance(host, pause, "mergerfs.balance" if req.get("engine") == "mergerfs.balance" else "starboard")
        raise Refused("Starboard asked for a plan the pool helper does not make")
    if act == "apply":
        plan = load_plan(host, str(req.get("plan", "")))
        confirm = {str(k): str(v) for k, v in (req.get("confirm") or {}).items()}
        verify(host, plan, confirm)  # refuse at once, before starting a job in the background
        start_job(host, plan["id"], confirm)
        return {"started": plan["id"]}
    if act == "stop":
        open(os.path.join(host.state, "stop"), "w").close()
        return {"stopping": True}
    raise Refused("Unknown request")


def start_job(host, plan_id, confirm):
    """Long jobs run in their own systemd unit at low priority, so the request is answered straight away."""
    write_json(os.path.join(host.state, "confirm", plan_id + ".json"), confirm, 0o600)
    if host.root != "/":
        return apply(host, plan_id, confirm)
    subprocess.run(["systemd-run", f"--unit=starboard-pool-job-{plan_id}", "--collect", "--quiet",
                    "-p", "Nice=19", "-p", "IOSchedulingClass=idle", sys.executable, os.path.abspath(__file__),
                    "run-job", plan_id], check=True)


def serve(host):
    folder = os.path.join(host.exchange, "requests")
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not name.endswith(".json") or name.startswith("."):
            continue
        rid = re.sub(r"[^0-9a-f]", "", name[:-5])[:32] or "unknown"
        try:
            req = read_request(path)
            answer = {"ok": True, "result": handle(host, req)}
        except Refused as e:
            answer = {"ok": False, "error": str(e)}
        except Exception as e:  # noqa: BLE001
            answer = {"ok": False, "error": f"The pool helper stopped with an error: {e}"}
        finally:
            _unlink(path)
        answer["at"] = now()
        host.publish(f"answers/{rid}.json", answer)
    publish_status(host)


# Terminal ---------------------------------------------------------------------------------------------------

def print_plan(plan, out=sys.stdout):
    print(f"Plan {plan['id']} (dry run: nothing has changed yet). It can be carried out for {PLAN_MINUTES} minutes:", file=out)
    for n, s in enumerate(plan["steps"], 1):
        print(f"  {n}. {'ERASES: ' if s.get('danger') else ''}{s['say']}", file=out)
        for c in s.get("commands") or []:
            print(f"       {c}", file=out)
    for m in (plan.get("moves") or [])[:20]:
        print(f"       {os.path.basename(m['from'])} to {os.path.basename(m['to'])}: {m['path']} ({human(m['bytes'])})", file=out)
    if len(plan.get("moves") or []) > 20:
        print(f"       and {len(plan['moves']) - 20} more", file=out)


def main(argv=None):
    p = argparse.ArgumentParser(prog="starboard-pool", description="Starboard's drive pool helper (runs as root).")
    p.add_argument("--json", action="store_true", help="answer in JSON, for Starboard's terminal set-up")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("drives")
    sub.add_parser("status")
    pl = sub.add_parser("plan")
    pl.add_argument("kind", choices=["add", "remove", "balance"])
    pl.add_argument("drive", nargs="?", default="")
    pl.add_argument("--as", dest="role", default="pool", choices=["pool", "parity", "copy"])
    pl.add_argument("--erase", action="store_true")
    pl.add_argument("--folders", default="")
    pl.add_argument("--engine", default="starboard", choices=["starboard", "mergerfs.balance"])
    ap = sub.add_parser("apply")
    ap.add_argument("plan")
    ap.add_argument("--confirm", action="append", default=[], help="DRIVE=the last 4 characters of its serial number")
    rj = sub.add_parser("run-job")
    rj.add_argument("plan")
    sub.add_parser("stop")
    sub.add_parser("nightly")
    sv = sub.add_parser("serve")
    sv.add_argument("folder")
    a = p.parse_args(argv)
    if os.geteuid() != 0:
        print("Run with sudo: the pool helper changes drives, so it runs as root", file=sys.stderr)
        return 2
    exchange = a.folder if a.cmd == "serve" else read_json("/var/lib/starboard-pool/exchange.json", {}).get("folder")
    host = Host(exchange=exchange)
    os.makedirs(host.state, mode=0o700, exist_ok=True)
    try:
        if a.cmd in ("drives", "status"):
            result = status(host) if a.cmd == "status" else drives(host)
            if a.json:
                print(json.dumps(result))
            else:
                for d in (result if a.cmd == "drives" else result["drives"]):
                    print(f"{d['name']:<8} {d['model'][:22]:<22} {human(d['size']):>9}  ends {d['ends'] or '????'}  "
                          f"{d.get('blocked') or d['use']}")
        elif a.cmd == "plan":
            plan = (plan_add(host, a.drive, a.role, a.erase, [f for f in a.folders.split(",") if f]) if a.kind == "add"
                    else plan_remove(host, a.drive) if a.kind == "remove" else plan_balance(host, engine=a.engine))
            print(json.dumps(plan)) if a.json else print_plan(plan)
        elif a.cmd in ("apply", "run-job"):
            confirm = dict(c.split("=", 1) for c in a.confirm if "=" in c)
            if a.cmd == "run-job":
                confirm = read_json(os.path.join(host.state, "confirm", a.plan + ".json"), {})
            listing = drives(host)
            confirm = {find(host, k, listing)["by_id"] if not k.startswith("/dev/disk/by-id/") else k: v for k, v in confirm.items()}
            result = apply(host, a.plan, confirm, None if a.json or a.cmd == "run-job" else sys.stdout)
            if a.json:
                print(json.dumps(result))
        elif a.cmd == "stop":
            open(os.path.join(host.state, "stop"), "w").close()
            print("Stopping after the folder being moved now")
        elif a.cmd == "nightly":
            nightly(host)
        elif a.cmd == "serve":
            serve(host)
    except Refused as e:
        print(json.dumps({"error": str(e)}) if a.json else f"Stopped: {e}", file=sys.stdout if a.json else sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
