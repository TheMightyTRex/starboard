#!/usr/bin/env python3
"""Tries Bring in media (DASH-455) for real, with Docker, against scratch folders and stand-in shares, never real media
or real shares: flock /mnt/pool/build-cache/heavy.lock python3 tools/try-bring-in-shares.py /mnt/pool/build-cache/dash-455-try

- Made-up media (random bytes with media names) in <scratch>/share-src: films, a series, an album, junk and a sample.
- An SMB stand-in: Alpine's Samba in a container, sharing that folder writable on the server's side, so only
  Starboard's read-only mount protects it. Starboard browses it, looks inside, checks names and copies into
  <scratch>/media through its short-lived helper, at low priority. Then it tries to write through the same read-only
  mount, which must fail.
- An NFS stand-in, when this computer's kernel can serve one in a container (it needs privileges); otherwise it says so.
- A cloud service: rclone's own image serves the same folder over WebDAV as a stand-in, kept as a OneDrive source's
  remote; Starboard lists it, copies it down to the staging folder with rclone, brings it in, and the staging folder
  goes to the holding folder on the media disk. No real cloud account is used.
- After each: every file at the source has the same size, time and contents as before.
Containers are capped (--memory 3g --memory-swap 3g --cpus 4) and stopped at the end. Nothing is removed, so the results
can be looked at; move the scratch folder to the holding folder when done.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import time
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from starboard import bring_in as b, folders, media_import, stack  # noqa: E402

CAPS = ["--memory", "3g", "--memory-swap", "3g", "--cpus", "4"]
SMB = "sb-bring-in-smb"
NFS = "sb-bring-in-nfs"


def tree(root):
    out = {}
    for here, _, files in os.walk(root):
        for f in files:
            p = os.path.join(here, f)
            st = os.stat(p)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns, hashlib.sha1(fh.read()).hexdigest())
    return out


def made_up(src):
    files = {"Films/Harbour.Lights.2019.1080p/Harbour.Lights.2019.1080p.mkv": 3_000_000,
             "Films/Harbour.Lights.2019.1080p/Harbour.Lights.2019.1080p.en.srt": 2000,
             "Films/Harbour.Lights.2019.1080p/Sample/sample.mkv": 10_000,
             "Films/The Long Field (2021)/The Long Field (2021).mkv": 2_000_000,
             "TV/Copper Valley/Season 1/Copper.Valley.S01E01.mkv": 1_000_000,
             "TV/Copper Valley/Season 1/Copper.Valley.S01E02.mkv": 1_000_000,
             "Music/Midnight Garden/First Light/01 Morning.flac": 400_000,
             "Thumbs.db": 100, "notes.txt": 100}
    for rel, size in files.items():
        p = os.path.join(src, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.exists(p):
            with open(p, "wb") as f:
                f.write(os.urandom(size))
    os.system(f"chmod -R a+rwX {src}")  # writable on the server's side: only the read-only mount protects it


def ip_of(name):
    out = subprocess.run(["docker", "inspect", "-f", "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}", name], capture_output=True, text=True).stdout
    return (out.split() or [""])[0]


class Lookup:
    def __call__(self, cfg, method, path, body=None, timeout=60):
        known = {"Harbour Lights 2019": ("Harbour Lights", 2019), "The Long Field 2021": ("The Long Field", 2021), "Copper Valley": ("Copper Valley", 2018)}
        if "lookup" in path:
            import urllib.parse
            term = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)["term"][0]
            return [{"tmdb_id": 1, "title": known[term][0], "year": known[term][1]}] if term in known else []
        return [] if path.endswith("rootfolders") else {}


def bring(scratch, data, source, label):
    """One whole run against a share: browse, look, check, copy. Returns True when it all held."""
    src = os.path.join(scratch, "share-src")
    media = os.path.join(scratch, f"media-{label}")
    os.makedirs(os.path.join(media, "media"), exist_ok=True)
    before = tree(src)
    ok = True
    b.save_sources(data, [source], media=media)
    s = b.settings(data)["sources"][0]
    top = b.share_browse(data, s["id"], "")
    print(f"{label}: folders at the top:", [f["name"] for f in top["folders"]])
    ok &= {"Films", "TV", "Music"} <= {f["name"] for f in top["folders"]}
    sizes = b.share_sizes(data, s["id"], "")
    print(f"{label}: sizes:", {k: (v["size"], v["kinds"]) for k, v in sizes.items()})
    look = b.look(data, s["id"])
    print(f"{label}: found:", look["found"])
    ok &= look["found"].get("films", {}).get("titles") == 2 and look["found"].get("series", {}).get("titles") == 1
    b.build_plan(data)
    with mock.patch.object(media_import, "_call", Lookup()), mock.patch.object(media_import, "_reelix", lambda cfg: ("x", "k")):
        b.check_names(None, data)
        b._say(data, state="running", phase="starting", paused=False)
        b._run(None, data, wait=0)
    job = b.status(data)
    print(f"{label}: job:", {k: job.get(k) for k in ("state", "error", "files_done", "files_total")})
    ok &= job.get("state") == "done"
    want = ["media/movies/Harbour Lights (2019)/Harbour Lights (2019).mkv", "media/movies/Harbour Lights (2019)/Harbour Lights (2019).en.srt",
            "media/movies/The Long Field (2021)/The Long Field (2021).mkv", "media/tv/Copper Valley (2018)/Season 01/Copper Valley - S01E01.mkv",
            "media/music/Midnight Garden/First Light/01 Morning.flac"]
    for rel in want:
        there = os.path.isfile(os.path.join(media, rel))
        ok &= there
        if not there:
            print("  missing:", rel)
    ok &= not any(n.endswith(".starboard-part") for _, _, fs in os.walk(media) for n in fs)
    # Write through the same read-only mount: it must be refused.
    code, said = b._helper("touch /r/written-by-starboard 2>&1; echo CODE $?", [("share", s, "/r")], data_dir=data)
    refused = "CODE 0" not in said
    print(f"{label}: writing through the mount:", "refused" if refused else "ALLOWED", said.strip().splitlines()[-1:])
    ok &= refused and not os.path.exists(os.path.join(src, "written-by-starboard"))
    after = tree(src)
    print(f"{label}: source unchanged:", after == before)
    ok &= after == before
    b.finish(data)
    return ok


def main(scratch):
    os.makedirs(scratch, exist_ok=True)
    src = os.path.join(scratch, "share-src")
    made_up(src)
    data = tempfile.mkdtemp(prefix="sb-bring-in-data-")
    env = {"PUID": str(os.getuid()), "PGID": str(os.getgid())}
    ok = True
    with mock.patch.object(stack, "env_values", lambda d: env), mock.patch.object(folders, "ROOTS", (os.path.dirname(scratch.rstrip("/")),) + folders.ROOTS):
        script = ("apk add --no-cache samba >/dev/null && adduser -D -H sam && printf 'made-up-pass\\nmade-up-pass\\n' | smbpasswd -a -s sam && "
                  "printf '[global]\\nmap to guest = never\\n[media]\\npath = /share\\nread only = no\\nvalid users = sam\\nforce user = root\\n' > /etc/samba/smb.conf && "
                  "exec smbd -F --no-process-group --debug-stdout")
        subprocess.run(["docker", "rm", "-f", SMB], capture_output=True)
        r = subprocess.run(["docker", "run", "-d", "--name", SMB, *CAPS, "-v", f"{src}:/share", "alpine:3.20", "sh", "-c", script], capture_output=True, text=True)
        if r.returncode:
            print("the SMB stand-in did not start:", r.stderr)
            return 1
        try:
            for _ in range(60):
                if "smbd version" in subprocess.run(["docker", "logs", SMB], capture_output=True, text=True).stdout + \
                        subprocess.run(["docker", "logs", SMB], capture_output=True, text=True).stderr:
                    break
                time.sleep(1)
            time.sleep(2)
            ip = ip_of(SMB)
            print("SMB stand-in at", ip)
            if not ip:
                print("the SMB stand-in stopped:", subprocess.run(["docker", "logs", "--tail", "20", SMB], capture_output=True, text=True).stderr[-1500:])
                return 1
            # The same mount by hand first, so Docker's whole answer shows when it fails.
            subprocess.run(["docker", "volume", "rm", "sb-bring-in-probe"], capture_output=True)
            mk = subprocess.run(["docker", "volume", "create", "-d", "local", "-o", "type=cifs", "-o", f"device=//{ip}/media", "-o",
                                 f"o=addr={ip},vers=3.0,ro,uid={os.getuid()},gid={os.getgid()},username=sam,password=made-up-pass", "sb-bring-in-probe"],
                                capture_output=True, text=True)
            probe = subprocess.run(["docker", "run", "--rm", "--memory", "256m", "-v", "sb-bring-in-probe:/r:ro", "alpine:3.20", "ls", "/r"],
                                   capture_output=True, text=True)
            print("probe mount:", mk.returncode, probe.returncode, (probe.stdout + probe.stderr).strip()[-800:])
            subprocess.run(["docker", "volume", "rm", "sb-bring-in-probe"], capture_output=True)
            ok &= bring(scratch, data, {"kind": "smb", "address": f"//{ip}/media", "user": "sam", "password": "made-up-pass", "path": ""}, "smb")
        finally:
            subprocess.run(["docker", "stop", SMB], capture_output=True)
            subprocess.run(["docker", "rm", SMB], capture_output=True)
        # NFS: Alpine's kernel NFS server in a container needs privileges and this computer's nfsd module; tried, and said if it cannot.
        subprocess.run(["docker", "rm", "-f", NFS], capture_output=True)
        nfs = ("apk add --no-cache nfs-utils >/dev/null && echo '/export *(rw,fsid=0,no_subtree_check,insecure,no_root_squash)' > /etc/exports && "
               "mount -t nfsd nfsd /proc/fs/nfsd && rpcbind && exportfs -ra && rpc.nfsd -N 3 8 && rpc.mountd -N 3 && echo 'READY AND WAITING' && exec sleep 3600")
        r = subprocess.run(["docker", "run", "-d", "--name", NFS, "--privileged", *CAPS, "-v", f"{src}:/export", "alpine:3.20", "sh", "-c", nfs],
                           capture_output=True, text=True)
        if r.returncode:
            print("NFS stand-in: could not start:", r.stderr.strip()[:300])
        else:
            try:
                ready = False
                for _ in range(40):
                    logs = subprocess.run(["docker", "logs", NFS], capture_output=True, text=True)
                    if "READY AND WAITING" in logs.stdout + logs.stderr:
                        ready = True
                        break
                    if "exited" in subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", NFS], capture_output=True, text=True).stdout:
                        break
                    time.sleep(1)
                if ready:
                    ip = ip_of(NFS)
                    print("NFS stand-in at", ip)
                    ok &= bring(scratch, data, {"kind": "nfs", "address": f"{ip}:/", "path": ""}, "nfs")
                else:
                    print("NFS stand-in: not ready on this computer:", (logs.stdout + logs.stderr).strip().splitlines()[-3:])
            finally:
                subprocess.run(["docker", "stop", NFS], capture_output=True)
                subprocess.run(["docker", "rm", NFS], capture_output=True)
        ok &= cloud(scratch, data)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


def cloud(scratch, data):
    """OneDrive's place, with a WebDAV stand-in behind it (rclone serve webdav on the Docker bridge)."""
    from starboard import backup_copies, cloud_sources
    src = os.path.join(scratch, "share-src")
    media = os.path.join(scratch, "media-cloud")
    os.makedirs(os.path.join(media, "media"), exist_ok=True)
    gateway = subprocess.run(["docker", "network", "inspect", "bridge", "-f", "{{(index .IPAM.Config 0).Gateway}}"], capture_output=True, text=True).stdout.strip()
    port = 39885
    subprocess.run(["docker", "rm", "-f", "sb-bring-in-webdav"], capture_output=True)
    r = subprocess.run(["docker", "run", "-d", "--name", "sb-bring-in-webdav", *CAPS, "--user", f"{os.getuid()}:{os.getgid()}", "-p", f"{gateway}:{port}:8080",
                        "-v", f"{src}:/cloud:ro", backup_copies.RCLONE_IMAGE, "serve", "webdav", "/cloud", "--addr", ":8080", "--read-only"],
                       capture_output=True, text=True)
    if r.returncode:
        print("the WebDAV stand-in did not start:", r.stderr)
        return False
    ok = True
    before = tree(src)
    try:
        time.sleep(2)
        b.save_sources(data, [{"kind": "onedrive", "path": "/"}], media=media)
        secrets = b._secrets(data)
        secrets["cloud:onedrive"] = f"[starboard-cloud]\ntype = webdav\nurl = http://{gateway}:{port}\nvendor = other\n"
        b._write(data, "secret.json", secrets, private=True)
        top = cloud_sources.browse(data, "onedrive", "")
        print("cloud: folders at the top:", [f["name"] for f in top["folders"]])
        ok &= {"Films", "TV", "Music"} <= {f["name"] for f in top["folders"]}
        look = b.look(data, b.settings(data)["sources"][0]["id"])
        print("cloud: found:", look["found"])
        b.build_plan(data)
        with mock.patch.object(media_import, "_call", Lookup()), mock.patch.object(media_import, "_reelix", lambda cfg: ("x", "k")):
            b.check_names(None, data)
            b._say(data, state="running", phase="starting", paused=False)
            b._run(None, data, wait=0)
        job = b.status(data)
        print("cloud: job:", {k: job.get(k) for k in ("state", "error", "files_done", "files_total")})
        ok &= job.get("state") == "done"
        ok &= os.path.isfile(os.path.join(media, "media/movies/Harbour Lights (2019)/Harbour Lights (2019).mkv"))
        report = b.report(data)
        print("cloud: staging went to", report["holding"])
        ok &= bool(report["holding"]) and os.path.isdir(report["holding"]) and not os.path.exists(os.path.join(media, ".starboard-bring-in"))
        b.finish(data)
    finally:
        subprocess.run(["docker", "stop", "sb-bring-in-webdav"], capture_output=True)
        subprocess.run(["docker", "rm", "sb-bring-in-webdav"], capture_output=True)
    ok &= tree(src) == before
    print("cloud: source unchanged:", tree(src) == before)
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/pool/build-cache/dash-455-try"))
