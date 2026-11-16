#!/usr/bin/env python3
"""Tries Connect a cloud service (DASH-452) for real, with Docker and rclone's pinned image, against throwaway local
stand-ins only: no real cloud account is used or made.  python3 tools/try-cloud-connect.py /mnt/pool/build-cache/dash-446-try

- WebDAV: rclone serve webdav with a user name and password, through the wizard's keys step (rclone config create
  --obscure), the folder list, the test, Save, a real copy of a made-up backup and Test connection; then a wrong
  password, to see the words.
- SFTP: rclone serve sftp with a user name and password, the same steps.
- S3: rclone serve s3 with an access key (MinIO's images are no longer free to download), the same steps, with a bucket
  made first.
- Complete in this browser: rclone authorize for Dropbox and Google Drive in the helper, with the sign-in pointed at
  tests/oauth_stand_in.py (rclone takes auth_url and token_url). Starboard reads the sign-in link, the "browser" (this
  script) allows it and pastes back the address it ends on, and rclone's listener swaps the code for the token. Then a
  refusal at the sign-in page, closing part way (the helper must be gone), and an address from another sign-in.
- Complete on the phone is tested against the stand-in in tests/test_cloud_connect.py (it needs no helper).
Every container is removed at the end. The scratch folder must be under one of Starboard's usual places (/mnt...).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from starboard import backup_copies as bc, cloud_connect as cc, stack  # noqa: E402
from tests.oauth_stand_in import StandIn  # noqa: E402

GATEWAY = subprocess.run(["docker", "network", "inspect", "bridge", "-f", "{{(index .IPAM.Config 0).Gateway}}"],
                         capture_output=True, text=True).stdout.strip()
BASE_PORT = int(os.environ.get("CLOUD_TRY_PORT", "39901"))  # the stand-ins listen on this port and the next three
CAPS = ["--memory", "3g", "--memory-swap", "3g", "--cpus", "4"]
results = []


def say(ok, what, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + what + (f": {detail}" if detail and not ok else ""), flush=True)


def docker(*args):
    return subprocess.run(["docker", *args], capture_output=True, text=True)


def wait_for(fn, limit=60):
    until = time.time() + limit
    while time.time() < until:
        if fn():
            return True
        time.sleep(0.5)
    return False


def keys_journey(data, sid, values, folder, label, wrong=None):
    """The wizard's steps for a keys service, then a real copy and Test connection on the saved place."""
    s = cc.start(data, sid)
    cc.details(s["id"], values)
    say(cc.current()["state"] == "signed-in", f"{label}: rclone made the remote from the details")
    conf = cc._session["config"]
    secret = values.get("pass") or values.get("secret_access_key")
    if sid in ("webdav", "sftp"):  # rclone obscures passwords; an S3 secret key is kept as given, in Starboard's own folder only
        say(secret not in conf, f"{label}: the password is kept obscured, never as entered")
    got = cc.folders(s["id"])
    say(isinstance(got["folders"], list), f"{label}: the folder list", str(got))
    t = cc.test(s["id"], folder)["test"]
    say(t["ok"] and all(x["done"] for x in t["steps"]), f"{label}: write, read back and remove", json.dumps(t))
    cc.save(data, s["id"], 2)
    names = [f"starboard-full-2026-11-0{i}-030000.starboard" for i in range(1, 4)]
    for n in names:
        said = bc._run(data, os.path.join(SCRATCH, "backups", n))
    say("keeps 2" in said, f"{label}: three real copies, the newest 2 kept", said)
    tested = bc.test(data)
    say(tested["ok"] and tested["count"] == 2, f"{label}: Test connection on the saved place", json.dumps(tested))
    if wrong:
        s = cc.start(data, sid)
        try:
            cc.details(s["id"], {**values, **wrong})
            t = cc.test(s["id"], folder)["test"]
            say(not t["ok"] and "SIGNIN" not in t["error"], f"{label}: a wrong password says so in words", t.get("error", ""))
            print("   ", t.get("error"))
        except cc.CloudError as e:
            say(True, f"{label}: a wrong password is refused: {e}")
        cc.cancel()


def browser_journey(data, svc, sid, label):
    cc.TEST_HOOK = {"authorize": {sid: {"auth_url": f"{svc.base}/authorize", "token_url": f"{svc.base}/token",
                                        "client_id": "standin", "client_secret": "standin"}}, "hosts": (GATEWAY,)}
    s = cc.start(data, sid, "browser")
    ok = wait_for(lambda: cc.current()["state"] in ("link", "failed"), 120)
    now = cc.current()
    say(ok and now["state"] == "link", f"{label}: Starboard read the sign-in link from rclone", json.dumps(now))
    if now["state"] != "link":
        return
    link = now["link"]
    say(link.startswith(svc.base + "/authorize?"), f"{label}: the link is the service's own sign-in page")
    # The person signs in and selects Allow: the service sends the browser to 127.0.0.1:53682, which does not load here.
    req = urllib.request.Request(link + "&allow=1")

    class NoFollow(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(NoFollow).open(req, timeout=10)
        ended = ""
    except urllib.error.HTTPError as e:
        ended = e.headers.get("Location", "")
    say(ended.startswith("http://127.0.0.1:53682/") or ended.startswith("http://localhost:53682/"), f"{label}: the sign-in ends on rclone's address", ended)
    try:
        cc.answer(s["id"], "http://127.0.0.1:53682/?state=SomeoneElse123&code=x")
        say(False, f"{label}: an address from another sign-in is refused")
    except ValueError:
        say(True, f"{label}: an address from another sign-in is refused")
    cc.answer(s["id"], ended)
    ok = wait_for(lambda: cc.current()["state"] in ("signed-in", "failed"), 60)
    say(ok and cc.current()["state"] == "signed-in", f"{label}: rclone swapped the code for the token", json.dumps(cc.current()))
    if cc.current()["state"] == "signed-in":
        conf = cc._session["config"]
        say(f"type = {cc.RCLONE_TYPE[sid]}" in conf and '"access_token":"standin-' in conf, f"{label}: the remote's config holds the token")
        say(("scope = drive.file" in conf) == (sid == "drive"), f"{label}: Google Drive asks for its own files only")
    say(not docker("ps", "-aq", "--filter", "label=starboard.cloud-signin=1").stdout.strip(), f"{label}: the sign-in helper is gone")
    cc.cancel()


def main(scratch):
    global SCRATCH
    SCRATCH = scratch
    data = tempfile.mkdtemp(prefix="sb-cloud-data-", dir=scratch)
    os.makedirs(os.path.join(scratch, "backups"), exist_ok=True)
    for i in range(1, 4):
        with open(os.path.join(scratch, "backups", f"starboard-full-2026-11-0{i}-030000.starboard"), "wb") as f:
            f.write(os.urandom(128 * 1024))
    for d in ("webdav", "sftp", "s3"):
        os.makedirs(os.path.join(scratch, d), exist_ok=True)
        os.chmod(os.path.join(scratch, d), 0o777)
    env = {"PUID": str(os.getuid()), "PGID": str(os.getgid())}
    uid = f"{os.getuid()}:{os.getgid()}"
    started = []
    try:
        with mock.patch.object(stack, "env_values", lambda d: env), mock.patch.object(stack, "host_folder", lambda d: os.path.join(data, "stack")):
            # WebDAV
            docker("run", "-d", "--rm", *CAPS, "--name", "sb452-webdav", "--user", uid, "-p", f"{GATEWAY}:{BASE_PORT}:8080",
                   "-v", f"{scratch}/webdav:/d", bc.RCLONE_IMAGE, "serve", "webdav", "/d", "--addr", ":8080", "--user", "alex", "--pass", "made-up pass 1")
            started.append("sb452-webdav")
            # SFTP
            docker("run", "-d", "--rm", *CAPS, "--name", "sb452-sftp", "--user", uid, "-e", "HOME=/tmp", "-e", "XDG_CACHE_HOME=/tmp", "-p", f"{GATEWAY}:{BASE_PORT + 1}:2022",
                   "-v", f"{scratch}/sftp:/d", bc.RCLONE_IMAGE, "serve", "sftp", "/d", "--addr", ":2022", "--user", "sam", "--pass", "made-up-pass-2")
            started.append("sb452-sftp")
            # S3: rclone's own S3 server (MinIO's images are no longer free to download, 16 November 2026)
            docker("run", "-d", "--rm", *CAPS, "--name", "sb452-s3", "--user", uid, "-e", "HOME=/tmp", "-p", f"{GATEWAY}:{BASE_PORT + 2}:8080",
                   "-v", f"{scratch}/s3:/data", bc.RCLONE_IMAGE, "serve", "s3", "/data", "--addr", ":8080",
                   "--auth-key", "madeupaccess,made-up-secret-3")
            started.append("sb452-s3")
            time.sleep(4)
            os.makedirs(os.path.join(scratch, "s3", "backups"), exist_ok=True)  # the bucket, as made at the service first
            keys_journey(data, "webdav", {"url": f"http://{GATEWAY}:{BASE_PORT}/", "vendor": "other", "user": "alex", "pass": "made-up pass 1"},
                         "starboard-backups", "WebDAV", wrong={"pass": "not the password"})
            keys_journey(data, "sftp", {"host": GATEWAY, "port": str(BASE_PORT + 1), "user": "sam", "pass": "made-up-pass-2"},
                         "starboard-backups", "SFTP", wrong={"pass": "not the password"})
            keys_journey(data, "s3", {"endpoint": f"http://{GATEWAY}:{BASE_PORT + 2}", "region": "", "access_key_id": "madeupaccess",
                                      "secret_access_key": "made-up-secret-3"}, "backups/starboard", "S3 (rclone serve s3)",
                         wrong={"secret_access_key": "not-the-secret"})
            listed = sorted(os.listdir(os.path.join(scratch, "webdav", "starboard-backups")))
            say(listed == ["starboard-full-2026-11-02-030000.starboard", "starboard-full-2026-11-03-030000.starboard"],
                "WebDAV: the files at the stand-in are the newest 2 backups, nothing else", str(listed))
            # Complete in this browser, against the stand-in sign-in service
            svc = StandIn(GATEWAY, BASE_PORT + 3).start()
            try:
                browser_journey(data, svc, "dropbox", "Dropbox, in this browser")
                browser_journey(data, svc, "drive", "Google Drive, in this browser")
                # Refused at the sign-in page
                svc.mode = "deny"
                cc.TEST_HOOK = {"authorize": {"dropbox": {"auth_url": f"{svc.base}/authorize", "token_url": f"{svc.base}/token",
                                                          "client_id": "standin", "client_secret": "standin"}}, "hosts": (GATEWAY,)}
                s = cc.start(data, "dropbox", "browser")
                wait_for(lambda: cc.current()["state"] == "link", 120)
                state = cc._session.get("auth_state", "")
                try:
                    cc.answer(s["id"], f"http://localhost:53682/?state={state}&error=access_denied")
                except cc.CloudError as e:
                    say("did not allow" in str(e), "A refusal at the sign-in page says so", str(e))
                say(wait_for(lambda: not docker("ps", "-aq", "--filter", "label=starboard.cloud-signin=1").stdout.strip(), 20),
                    "After a refusal the helper is gone")
                svc.mode = "approve"
                # Closing part way
                s = cc.start(data, "dropbox", "browser")
                wait_for(lambda: cc.current()["state"] == "link", 120)
                running = docker("ps", "-q", "--filter", "label=starboard.cloud-signin=1").stdout.strip()
                say(bool(running), "While signing in, the helper runs")
                inspect = docker("inspect", running).stdout if running else ""
                cc.cancel()
                say(wait_for(lambda: not docker("ps", "-aq", "--filter", "label=starboard.cloud-signin=1").stdout.strip(), 20),
                    "Closing part way removes the helper")
                say(bool(json.loads(inspect or "[]")) and "53682" not in json.dumps((json.loads(inspect or "[{}]") or [{}])[0].get("HostConfig", {}).get("PortBindings") or {}),
                    "No port of the helper is published on this computer")
            finally:
                svc.stop()
                cc.cancel()
    finally:
        if not all(results):
            for name in started:
                print(f"--- {name} said:\n" + "\n".join((docker("logs", "--tail", "15", name).stderr or "").splitlines()[-15:]))
        for name in started:
            docker("rm", "-f", name)
        mine = docker("ps", "-a", "--format", "{{.Names}}").stdout.split()
        leftover = [n for n in mine if n.startswith(("sb452-", "starboard-cloud-signin-"))]
        say(not leftover, "Nothing left running", " ".join(leftover))
    print(f"{sum(results)} of {len(results)} passed")
    print("PASS" if all(results) else "FAIL")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(os.path.abspath(sys.argv[1])))
