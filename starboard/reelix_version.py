"""Which exact Reelix Starboard installed (DASH-419).

The fork's images have moving tags (lite, full) and, since 15 November 2026, fixed version tags that are never moved:
<edition>-<Reelix version>-trex.<build>, such as lite-0.8.7-trex.1 or full-0.8.7-trex.2. Each image is labelled with
what it is (io.github.themightytrex.reelix.tag, .edition, org.opencontainers.image.version and .revision), so the
running container names its exact build even when Compose asked for a moving tag.

After Starboard installs Reelix, switches its version, updates it or goes back, it notes the running build in
reelix-installed.json beside the set-up files: the current one and the last 20 before it, each with when and how. It
reads one container and its image from Docker, only at those moments; nothing runs on a timer.

An image built before the version tags (no tag label) is noted by its version and digest; exact_image() then gives the
digest, which also names one build exactly.
"""

import datetime as dt
import json
import os
import re
import urllib.parse

from . import containers, logs

FILE = "reelix-installed.json"
KEEP = 20
LABEL_TAG = "io.github.themightytrex.reelix.tag"
LABEL_EDITION = "io.github.themightytrex.reelix.edition"
LABEL_VERSION = "org.opencontainers.image.version"
LABEL_REVISION = "org.opencontainers.image.revision"
VERSION_TAG = re.compile(r"^(lite|full)-(\d+\.\d+\.\d+)-trex\.(\d+)$")
HOW = {"install": "Installed", "switch": "Switched version", "update": "Updated", "back": "Went back",
       "seen": "Found running"}  # seen: started some other way, such as install.sh --start-apps


def parse_tag(tag):
    """(edition, version, build) for lite-0.8.7-trex.1, or None for any other tag."""
    m = VERSION_TAG.match(tag or "")
    return (m.group(1), m.group(2), int(m.group(3))) if m else None


def describe(ref, image):
    """What an image is, from its reference (as Compose names it) and Docker's image inspect: the edition, Reelix
    version, fixed version tag, commit and digest. Values the image does not say are empty."""
    labels = ((image or {}).get("Config") or {}).get("Labels") or {}
    reg, repo, tag = containers.parse_ref(ref)
    vtag = labels.get(LABEL_TAG, "") if parse_tag(labels.get(LABEL_TAG)) else ""
    if not vtag and parse_tag(tag):
        vtag = tag  # pinned to a version tag in the Compose file
    from . import stack
    edition = labels.get(LABEL_EDITION, "") if labels.get(LABEL_EDITION) in ("lite", "full") else ""
    edition = edition or (parse_tag(vtag) or ("",))[0] or (stack.edition_of(ref) or "")
    name = f"{reg}/{repo}" if reg != "registry-1.docker.io" else repo
    digest = next((d.split("@", 1)[1] for d in (image or {}).get("RepoDigests") or []
                   if "@" in d and d.split("@", 1)[0].lower().endswith(repo.lower())), "")
    return {"image": ref, "repository": name, "edition": edition,
            "version": labels.get(LABEL_VERSION, "") or (parse_tag(vtag) or ("", ""))[1],
            "tag": vtag, "revision": labels.get(LABEL_REVISION, ""), "digest": digest,
            "image_id": (image or {}).get("Id", "")}


def exact_image(entry):
    """The reference that names this one build: repository:<version tag>, else repository@<digest>, else None."""
    if not entry:
        return None
    if entry.get("tag"):
        return f"{entry['repository']}:{entry['tag']}"
    if entry.get("digest"):
        return f"{entry['repository']}@{entry['digest']}"
    return None


def running(docker=None, name="reelix"):
    """describe() for the container called reelix, or None when there is none."""
    docker = docker or containers.docker
    filters = urllib.parse.quote(json.dumps({"name": [f"^/{name}$"]}), safe="")
    listed = docker("GET", f"/containers/json?all=1&filters={filters}")
    c = next((c for c in listed or [] if (c.get("Names") or [""])[0].lstrip("/") == name), None)
    if not c or str(c.get("Image", "")).startswith("sha256:"):
        return None
    image = docker("GET", f"/images/{urllib.parse.quote(c['ImageID'], safe='')}/json")
    return describe(c["Image"], image)


def read(data_dir):
    """{"current": entry or None, "history": [older entries, newest first]}."""
    try:
        with open(os.path.join(data_dir, FILE), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {"current": data.get("current") if isinstance(data.get("current"), dict) else None,
                    "history": [e for e in data.get("history") or [] if isinstance(e, dict)][:KEEP]}
    except (OSError, ValueError):
        pass
    return {"current": None, "history": []}


def record(data_dir, entry, how, now=None):
    """Notes `entry` as the Reelix now installed, when it is a different build from the one noted before (a new
    image ID, digest or version tag). Returns the entry noted, or None when nothing changed."""
    if how not in HOW:
        raise ValueError(f"Unknown way of installing: {how}")
    data = read(data_dir)
    now_entry = {**entry, "how": how,
                 "at": (now or dt.datetime.now(dt.timezone.utc)).replace(microsecond=0).isoformat()}
    before = data["current"]
    if before and all(before.get(k) == entry.get(k) for k in ("image_id", "digest", "tag", "image")):
        return None
    history = ([before] if before else []) + data["history"]
    path = os.path.join(data_dir, FILE)
    with open(path + ".new", "w", encoding="utf-8") as f:
        json.dump({"current": now_entry, "history": history[:KEEP]}, f, indent=1)
    os.replace(path + ".new", path)
    return now_entry


def note(data_dir, how, docker=None):
    """Reads the running Reelix and records it. Never raises: noting is a record, and must not stop an install or an
    update. Returns the entry noted, or None."""
    try:
        entry = running(docker)
        if not entry:
            return None
        noted = record(data_dir, entry, how)
        if noted:
            logs.event("info", "reelix", f"{HOW[how]}: Reelix {label(noted)}")
        return noted
    except Exception as e:  # noqa: BLE001  Docker away, a full disk: the install itself went on
        logs.event("warning", "reelix", f"Starboard could not note which Reelix is installed: {e}")
        return None


def label(entry):
    """In words: "full-0.8.7-trex.1", or "0.8.7 (Lite, sha256:abc123456789)" for a build without a version tag."""
    if not entry:
        return "not known"
    if entry.get("tag"):
        return entry["tag"]
    bits = [entry.get("version") or "an unknown version"]
    extra = ", ".join(x for x in ((entry.get("edition") or "").capitalize(), (entry.get("digest") or "")[:19]) if x)
    return f"{bits[0]} ({extra})" if extra else bits[0]


def note_when_started(data_dir, how, wait=3600, sleep=None):
    """note() once the apps Install apps started have finished starting (stack.job), in a short-lived thread."""
    import threading
    import time
    from . import stack
    pause = sleep or time.sleep

    def run():
        began = time.time()
        while not stack.job(data_dir).get("finished"):
            if time.time() - began > wait:
                return
            pause(5)
        note(data_dir, how)
    t = threading.Thread(target=run, name="reelix-version", daemon=True)
    t.start()
    return t
