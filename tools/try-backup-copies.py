#!/usr/bin/env python3
"""Tries Copies off this computer (DASH-380) for real, with Docker, against scratch folders and a local stand-in, never
real backups or shares: python3 tools/try-backup-copies.py /mnt/pool/build-cache/dash-380-try

- Six made-up full backups (random bytes with Starboard's names) in <scratch>/backups.
- Another disk: copied to <scratch>/usb, keeping 3; a file that is not a backup is left alone there.
- A cloud remote: rclone's own image serves <scratch>/cloud over WebDAV on the Docker bridge (the stand-in), and the
  copy goes there through rclone, keeping 2. Then a remote that does not answer, to see the words.
- Test on both.
The scratch folder must be under one of Starboard's usual places (/mnt, /srv...). Nothing is removed afterwards, so the
results can be looked at; move the scratch folder to the holding folder when done.
"""
import os
import subprocess
import sys
import tempfile
import time
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from starboard import backup_copies as bc, stack  # noqa: E402

# Docker's own bridge gateway, read at run time: the stand-in listens there so rclone's helper can reach it.
GATEWAY = subprocess.run(["docker", "network", "inspect", "bridge", "-f", "{{(index .IPAM.Config 0).Gateway}}"],
                         capture_output=True, text=True).stdout.strip()
PORT = 39881


def main(scratch):
    data = tempfile.mkdtemp(prefix="sb-copies-data-")
    for d in ("backups", "usb", "cloud"):
        os.makedirs(os.path.join(scratch, d), exist_ok=True)
    os.chmod(os.path.join(scratch, "cloud"), 0o777)
    names = [f"starboard-full-2026-11-0{i}-030000.starboard" for i in range(1, 7)]
    for n in names:
        with open(os.path.join(scratch, "backups", n), "wb") as f:
            f.write(os.urandom(256 * 1024))
    with open(os.path.join(scratch, "usb", "holiday-photos.zip"), "wb") as f:
        f.write(b"not a backup")
    env = {"PUID": str(os.getuid()), "PGID": str(os.getgid())}
    ok = True
    with mock.patch.object(stack, "env_values", lambda d: env), mock.patch.object(stack, "host_folder", lambda d: os.path.join(data, "stack")):
        bc.save(data, {**bc.settings(data), "kind": "disk", "folder": os.path.join(scratch, "usb"), "keep": 3}, bc.secrets(data))
        print("disk test:", bc.test(data))
        for n in names:
            said = bc._run(data, os.path.join(scratch, "backups", n))
        print("disk copy:", said)
        there = sorted(os.listdir(os.path.join(scratch, "usb")))
        print("  in usb:", there)
        ok &= there == ["holiday-photos.zip"] + names[-3:]

        stand_in = subprocess.run(["docker", "run", "-d", "--rm", "--name", "sb-copies-standin", "--user", f"{os.getuid()}:{os.getgid()}",
                                   "-p", f"{GATEWAY}:{PORT}:8080", "-v", f"{os.path.join(scratch, 'cloud')}:/cloud", bc.RCLONE_IMAGE,
                                   "serve", "webdav", "/cloud", "--addr", ":8080"], capture_output=True, text=True)
        if stand_in.returncode:
            print("the stand-in did not start:", stand_in.stderr)
            return 1
        try:
            time.sleep(2)
            conf = f"[standin]\ntype = webdav\nurl = http://{GATEWAY}:{PORT}\nvendor = other\n"
            new, sec = bc.check(data, {"kind": "rclone", "remote": "standin:starboard", "rclone_config": conf, "keep": 2})
            bc.save(data, new, sec)
            print("rclone test:", bc.test(data))
            for n in names[-3:]:
                said = bc._run(data, os.path.join(scratch, "backups", n))
            print("rclone copy:", said)
            there = sorted(os.listdir(os.path.join(scratch, "cloud", "starboard")))
            print("  in cloud:", there)
            ok &= there == names[-2:]
            ok &= not os.path.exists(os.path.join(data, bc.WORK, "rclone.conf"))
        finally:
            subprocess.run(["docker", "stop", "sb-copies-standin"], capture_output=True)
        new, sec = bc.check(data, {"kind": "rclone", "remote": "standin:starboard", "rclone_config": conf.replace(str(PORT), "1"), "keep": 2})
        bc.save(data, new, sec)
        try:
            bc.test(data)
            ok = False
        except bc.CopyError as e:
            print("a remote that does not answer:", e)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/mnt/pool/build-cache/dash-380-try"))
