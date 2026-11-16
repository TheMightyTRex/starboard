#!/usr/bin/env python3
"""Stage D of the end-to-end update test (DASH-418), inside its sealed Docker, from the Starboard folder there.

Starboard's own update code (update_runs, containers, reelix_updates) updates real containers started by Docker
Compose. Only the question "does the registry have a newer build?" is answered here (the registry is local, over
plain HTTP, which Starboard never asks); pulling, the settings copy, starting, the health check and the way back are
Starboard's own. Then Install all updates (DASH-454): three apps as one batch, one updating, one that cannot start
going back by itself while the rest carry on, and one big change held back. Prints PASS or FAIL lines; exits with
the number of failures."""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from starboard import containers, reelix_updates, stack, update_batch, update_runs  # noqa: E402

REG = "127.0.0.1:5000"
FAILED = 0
HOME = os.path.expanduser("~/e2e-apps")


def say(ok, words):
    global FAILED
    print(("PASS " if ok else "FAIL ") + words, flush=True)
    FAILED += 0 if ok else 1


def sh(*cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(cmd)} ended with {r.returncode}: {(r.stderr or r.stdout).strip()[-400:]}")
    return r


def push_app(version, broken=False, name="e2e-app"):
    """A tiny web app answering its version, pushed as REG/<name>:latest."""
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "Dockerfile"), "w") as f:
        f.write("FROM busybox:1.37\n" + (
            'CMD ["sh", "-c", "echo this made-up version cannot start; exit 1"]\n' if broken else
            f'RUN mkdir -p /www && echo {version} > /www/index.html\nCMD ["httpd", "-f", "-p", "8080", "-h", "/www"]\n'))
    sh("docker", "build", "-q", "-t", "e2e-build:app", d)
    publish("e2e-build:app", f"{REG}/{name}:latest")


def publish(local, ref):
    """Pushes `local` as `ref` to the registry, then points this computer's `ref` back where it was: on a server
    the tag moves only when Starboard pulls the new version (a running container whose tag moved shows only its
    image id, which Starboard leaves alone)."""
    before = sh("docker", "image", "inspect", "-f", "{{.Id}}", ref, check=False).stdout.strip()
    sh("docker", "tag", local, ref)
    sh("docker", "push", "-q", ref)
    if before:
        sh("docker", "tag", before, ref)


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


def batch_stage():
    """Install all updates: e2e-a updates, e2e-b's new version cannot start and goes back by itself, e2e-c's is a
    big change and is held back; one at a time, in order, with a copy of each one's settings first."""
    names = ("e2e-a", "e2e-b", "e2e-c")
    os.makedirs(f"{HOME}/batch", exist_ok=True)
    services = "".join(f"  {n}:\n    image: {REG}/{n}:latest\n    container_name: {n}\n    ports: ['127.0.0.1:{18610 + i}:8080']\n"
                       f"    volumes: ['./{n}:/config']\n    restart: unless-stopped\n" for i, n in enumerate(names))
    with open(f"{HOME}/batch/compose.yaml", "w") as f:
        f.write("services:\n" + services)
    for n in names:
        os.makedirs(f"{HOME}/batch/{n}", exist_ok=True)
        with open(f"{HOME}/batch/{n}/settings.xml", "w") as f:
            f.write(f"<settings>{n}</settings>\n")
        push_app("1", name=n)
    sh("docker", "compose", "-p", "e2e-batch", "up", "-d", "--quiet-pull", cwd=f"{HOME}/batch")
    time.sleep(2)
    say(all(answer(18610 + i) == "1" for i in range(3)), "three apps run version 1")
    app = App([{"id": n, "name": n, "type": "link", "url": f"http://127.0.0.1:{18610 + i}", "enabled": True} for i, n in enumerate(names)])
    containers._check_one = lambda c: {"latest": "2", "update": True, "unknown": False, "big_change": c.get("name") == "e2e-c"}
    containers.check(app.config.data["services"])
    push_app("2", name="e2e-a")
    push_app("2", broken=True, name="e2e-b")
    push_app("2", name="e2e-c")
    plan = update_batch.plan(app)
    say([i["target"] for i in plan["items"]] == ["app:e2e-a", "app:e2e-b"] and [h["target"] for h in plan["held"]] == ["app:e2e-c"],
        f"the plan: {[i['target'] for i in plan['items']]}, held back {[h['target'] for h in plan['held']]}")
    started = time.time()
    batch = wait_run(app, update_batch.start(app, by="you"), limit=900)
    v = update_batch.view(app, batch["id"])
    states = {i["target"]: i["state"] for i in v["items"]}
    say(states == {"app:e2e-a": "done", "app:e2e-b": "went-back", "app:e2e-c": "held"},
        f"Install all updates: {states}, {v['said']} ({time.time() - started:.0f} s)")
    runs = {r["target"]: r for r in update_runs.recent(app) if r["kind"] == "app"}
    a, b = runs.get("app:e2e-a"), runs.get("app:e2e-b")
    say(bool(a and b and a["finished"] and b["started"] >= a["finished"]), "one at a time: e2e-b started after e2e-a had finished")
    time.sleep(3)
    say([answer(18610 + i) for i in range(3)] == ["2", "1", "1"], "e2e-a answers 2, e2e-b went back to 1, e2e-c was not touched")
    say(all(os.path.exists(f"{HOME}/batch/{n}-before-update.tgz") for n in ("e2e-a", "e2e-b")), "each update copied its settings first")
    say(v["state"] == "some-updated" and "Went back by itself: e2e-b" in v["said"] and "Held back for you: e2e-c" in v["said"], f"it says how it went: {v['said']}")
    sh("docker", "compose", "-p", "e2e-batch", "down", cwd=f"{HOME}/batch", check=False)


def reelix_stage():
    lite = f"ghcr.io/themightytrex/reelix:{os.environ.get('REELIX_FROM') or 'lite'}"  # REELIX_FROM: a version tag to start from
    to = os.environ.get("REELIX_TO", "")
    try:
        sh("docker", "pull", "-q", lite)
    except RuntimeError as e:
        say(False, f"Reelix's published image could not be pulled: {e}")
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
    say(healthy, f"Reelix Lite ({lite.rsplit(':', 1)[1]}, the published image) answers healthy")
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
        publish(f"ghcr.io/themightytrex/reelix:{to}", f"{REG}/reelix:lite")
        said = reelix_updates.run(app.config, app.data_dir)
        say("healthy" in said, f"Reelix updated to {to}: {said}")
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "Dockerfile"), "w") as f:
        f.write('FROM alpine:3.21\nCMD ["sh", "-c", "echo this made-up Reelix cannot start; sleep 3600"]\n')
    sh("docker", "build", "-q", "-t", "e2e-build:reelix", d)
    publish("e2e-build:reelix", f"{REG}/reelix:lite")
    started = time.time()
    said = reelix_updates.run(app.config, app.data_dir)
    say("went back" in said, f"a Reelix that does not answer went back by itself: {said} ({time.time() - started:.0f} s)")
    say(os.path.exists(f"{HOME}/reelix/reelix-before-update.tgz"), "Reelix's settings were copied first (reelix-before-update.tgz)")
    say(healthy_within(base, 120, time.sleep), "Reelix answers healthy again on the version before")
    sh("docker", "compose", "-p", "e2e-reelix", "down", cwd=f"{HOME}/reelix", check=False)


if __name__ == "__main__":
    for stage in (app_stage, batch_stage, reelix_stage):
        if stage is reelix_stage and os.environ.get("REELIX", "1") != "1":
            print("Reelix: not run (REELIX=0)")
            continue
        try:
            stage()
        except Exception as e:  # noqa: BLE001  one stage that stops is a failure; the next still runs
            say(False, f"{stage.__name__} stopped: {e}")
    print(json.dumps({"failed": FAILED}))
    sys.exit(FAILED)
