#!/usr/bin/env python3
"""Stage D of the end-to-end update test (DASH-418), inside its sealed Docker, from the Starboard folder there.

Starboard's own update code (update_runs, containers, reelix_updates) updates real containers started by Docker
Compose. Only the question "does the registry have a newer build?" is answered here (the registry is local, over
plain HTTP, which Starboard never asks); pulling, the settings copy, starting, the health check and the way back are
Starboard's own. Prints PASS or FAIL lines; exits with the number of failures."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from starboard import containers, reelix_updates, stack, update_runs  # noqa: E402

REG = "127.0.0.1:5000"
FAILED = 0
HOME = os.path.expanduser("~/e2e-apps")


def say(ok, words):
    global FAILED
    print(("PASS " if ok else "FAIL ") + words, flush=True)
    FAILED += 0 if ok else 1


def sh(*cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)


def push_app(version, broken=False):
    """A tiny web app answering its version, pushed as REG/e2e-app:latest."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "Dockerfile"), "w") as f:
        f.write("FROM alpine:3.21\n" + (
            'CMD ["sh", "-c", "echo this made-up version cannot start; exit 1"]\n' if broken else
            f'RUN mkdir -p /www && echo {version} > /www/index.html\nCMD ["httpd", "-f", "-p", "8080", "-h", "/www"]\n'))
    sh("docker", "build", "-q", "-t", f"{REG}/e2e-app:latest", d)
    sh("docker", "push", "-q", f"{REG}/e2e-app:latest")


def answer(port, path="/"):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=3) as r:
            return r.read().decode().strip()
    except OSError:
        return ""


class App:
    def __init__(self, services):
        self.data_dir = tempfile.mkdtemp()
        self.config = type("C", (), {"data": {"services": services}})()
        self.version = "e2e"
        self.watch = None

    def latest_release(self):
        return None


def wait_run(app, run, limit=600):
    until = time.time() + limit
    while time.time() < until:
        r = update_runs.get(app, run["id"])
        if r["state"] != "running":
            return r
        time.sleep(3)
    return update_runs.get(app, run["id"])


def app_stage():
    os.makedirs(f"{HOME}/app/config", exist_ok=True)
    with open(f"{HOME}/app/config/settings.xml", "w") as f:
        f.write("<settings>kept</settings>\n")
    with open(f"{HOME}/app/compose.yaml", "w") as f:
        f.write(f"services:\n  e2e:\n    image: {REG}/e2e-app:latest\n    container_name: e2e\n    ports: ['127.0.0.1:18600:8080']\n"
                "    volumes: ['./config:/config']\n    restart: unless-stopped\n")
    push_app("1")
    sh("docker", "compose", "-p", "e2e", "up", "-d", "--quiet-pull", cwd=f"{HOME}/app")
    time.sleep(2)
    say(answer(18600) == "1", "the app runs version 1")
    app = App([{"id": "e2e", "name": "e2e", "type": "link", "url": "http://127.0.0.1:18600", "enabled": True}])
    containers._check_one = lambda c: {"latest": "2", "update": True, "unknown": False, "big_change": False}
    containers.check(app.config.data["services"])

    push_app("2")
    started = time.time()
    r = wait_run(app, update_runs.start(app, "app:e2e", by="automatic"))
    steps = {s["id"]: s for s in r["steps"]}
    say(r["state"] == "updated", f"the app updated to version 2 ({r['state']}: {r['said']}) in {time.time() - started:.0f} s")
    say(answer(18600) == "2", "it answers as version 2")
    say(steps.get("backup", {}).get("state") == "done" and os.path.exists(f"{HOME}/app/e2e-before-update.tgz"),
        f"a copy of its settings was made first: {steps.get('backup', {}).get('detail')}")
    listed = sh("tar", "tzf", f"{HOME}/app/e2e-before-update.tgz", check=False).stdout
    say("config/settings.xml" in listed, "the copy holds its settings")

    push_app("3", broken=True)
    containers.check(app.config.data["services"])  # the next look finds it (an update clears the last look)
    started = time.time()
    r = wait_run(app, update_runs.start(app, "app:e2e", by="automatic"))
    say(r["state"] == "went-back", f"a version that cannot start went back by itself ({r['state']}: {r['said']}) in {time.time() - started:.0f} s")
    time.sleep(3)
    say(answer(18600) == "2", "it answers as version 2 again")
    sh("docker", "compose", "-p", "e2e", "down", cwd=f"{HOME}/app", check=False)


def reelix_stage():
    lite = "ghcr.io/themightytrex/reelix:lite"
    to = os.environ.get("REELIX_TO", "")
    try:
        sh("docker", "pull", "-q", lite)
    except subprocess.CalledProcessError as e:
        say(False, f"Reelix's published image could not be pulled: {e.stderr.strip()[-200:]}")
        return
    sh("docker", "tag", lite, f"{REG}/reelix:lite")
    sh("docker", "push", "-q", f"{REG}/reelix:lite")
    os.makedirs(f"{HOME}/reelix/config", exist_ok=True)
    with open(f"{HOME}/reelix/compose.yaml", "w") as f:
        f.write(f"services:\n  reelix:\n    image: {REG}/reelix:lite\n    container_name: reelix\n    ports: ['127.0.0.1:18700:7700']\n"
                "    volumes: ['./config:/config']\n    restart: unless-stopped\n")
    sh("docker", "compose", "-p", "e2e-reelix", "up", "-d", "--quiet-pull", cwd=f"{HOME}/reelix")
    base = "http://127.0.0.1:18700"
    healthy = reelix_updates._healthy(base, 120, time.sleep)
    say(healthy, "Reelix Lite (the published image) answers healthy")
    if not healthy:
        print(sh("docker", "logs", "--tail", "20", "reelix", check=False).stdout)
        return
    app = App([{"id": "rx", "name": "Reelix", "type": "link", "icon": "reelix", "url": base, "enabled": True}])
    stack.reelix_url = lambda data_dir: base
    containers._check_one = lambda c: {"latest": "newer", "update": True, "unknown": False, "big_change": False}
    reelix_updates.HEALTHY_WITHIN = 90
    healthy_within = reelix_updates._healthy
    reelix_updates._healthy = lambda base, wait=90, sleep=time.sleep: healthy_within(base, wait, sleep)  # 90 s, not 5 minutes
    if to:
        sh("docker", "pull", "-q", f"ghcr.io/themightytrex/reelix:{to}")
        sh("docker", "tag", f"ghcr.io/themightytrex/reelix:{to}", f"{REG}/reelix:lite")
        sh("docker", "push", "-q", f"{REG}/reelix:lite")
        said = reelix_updates.run(app.config, app.data_dir)
        say("healthy" in said, f"Reelix updated to {to}: {said}")
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "Dockerfile"), "w") as f:
        f.write('FROM alpine:3.21\nCMD ["sh", "-c", "echo this made-up Reelix cannot start; sleep 3600"]\n')
    sh("docker", "build", "-q", "-t", f"{REG}/reelix:lite", d)
    sh("docker", "push", "-q", f"{REG}/reelix:lite")
    started = time.time()
    said = reelix_updates.run(app.config, app.data_dir)
    say("went back" in said, f"a Reelix that does not answer went back by itself: {said} ({time.time() - started:.0f} s)")
    say(os.path.exists(f"{HOME}/reelix/reelix-before-update.tgz"), "Reelix's settings were copied first (reelix-before-update.tgz)")
    say(healthy_within(base, 120, time.sleep), "Reelix answers healthy again on the version before")
    sh("docker", "compose", "-p", "e2e-reelix", "down", cwd=f"{HOME}/reelix", check=False)


if __name__ == "__main__":
    app_stage()
    if os.environ.get("REELIX", "1") == "1":
        reelix_stage()
    else:
        print("Reelix: not run (REELIX=0)")
    print(json.dumps({"failed": FAILED}))
    sys.exit(FAILED)
