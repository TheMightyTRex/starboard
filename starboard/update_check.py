"""Check for updates and What is new for every waiting update (owner, 17 November 2026), on Settings, Updates.

Check for updates asks now, with the checks Starboard already has, instead of waiting for their next look:

- Starboard: GitHub's newest version tag (App.latest_release, which otherwise looks at most every 6 hours);
- the apps and Reelix: each image's registry (containers.check, as Look for updates on Apps, Updates);
- Starboard's plug-ins: every plug-in catalogue (plugins_admin.refresh, which otherwise reads each every 6 hours);
- Jellyfin's plug-ins: Jellyfin's own list of packages from its repositories, against the versions installed.

What is new puts the notes of every waiting update in one list, grouped by item, from the version installed to the
new one, each item's entries under Added, Changed, Fixed and Security (and Deprecated and Removed when there are any):

- Starboard: starboard/releases.py for the versions this copy knows, and the CHANGELOG.md of the new version's tag on
  GitHub for the versions after it (the same entries: releases.py is written from the changelog);
- Reelix: its changelog (changes.py, the one Apps, Updates shows);
- Starboard's plug-ins: the new version's manifest's changes (plugin_update.changes_between, as on the plug-in's page);
- Jellyfin's plug-ins: each new version's changelog from Jellyfin's packages, which its makers do not sort into types;
- the other apps: Starboard reads no notes for them, so each says so and links its release page.

Lightweight: nothing here runs on page load or on a timer. Both run only when the button is pressed, the notes are
fetched in a few threads with time limits, and what is fetched is kept in memory (the changelogs for 6 hours, the
manifests for 10 minutes, what Jellyfin said until the next check).
"""
import concurrent.futures as cf
import re
import threading
import time

TYPES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")
_lock = threading.Lock()
_jellyfin = {"at": 0, "waiting": []}  # what the last check found for Jellyfin's plug-ins
JELLYFIN_KEEP = 6 * 3600


# Check for updates -------------------------------------------------------------------------------------------------

def _check_starboard(app):
    if not getattr(app, "repo", "") or not app.config.data.get("update_check", True):
        return {"id": "starboard", "name": "Starboard", "ok": False,
                "said": "Not asked: Check GitHub for new releases is off below, in Update Starboard on the server instead"}
    lock = getattr(app, "_latest_lock", None)
    if lock is not None:
        with lock:
            app._latest["checked"] = 0  # look now, not at the next 6-hourly look
    tag = app.latest_release()
    if tag is None:
        return {"id": "starboard", "name": "Starboard", "ok": False, "said": "GitHub did not answer"}
    return {"id": "starboard", "name": "Starboard", "ok": True, "said": f"Newest release {str(tag).lstrip('v')}"}


def _check_apps(app):
    from . import changes, containers
    if not containers.available():
        return {"id": "apps", "name": "The apps and Reelix", "ok": False, "said": "Starboard has no Docker access, so it cannot check the apps' images"}
    try:
        result = containers.check(app.config.data["services"])
    except containers.DockerError as e:
        return {"id": "apps", "name": "The apps and Reelix", "ok": False, "said": str(e)[:200]}
    changes.observe(app.data_dir, result.get("items", []))  # as Apps, Updates does after its look
    rows = [r for r in result.get("items", []) if r.get("container")]
    cannot = [r["name"] for r in rows if r.get("error")]
    said = f"Checked {len(rows)} {'image' if len(rows) == 1 else 'images'}"
    if cannot:
        said += f". Could not reach: {', '.join(cannot[:6])}"
    return {"id": "apps", "name": "The apps and Reelix", "ok": not cannot, "said": said}


def _check_plugins(app):
    from . import plugins_admin as pa
    got = pa.refresh(app.config)  # every catalogue again now, but not twice within a few seconds
    failed = [c["name"] for c in got["catalogues"] if c.get("error")]
    said = got["said"].rstrip(".") if got["too_soon"] else f"Read {len(got['catalogues'])} {'catalogue' if len(got['catalogues']) == 1 else 'catalogues'}"
    if failed and not got["too_soon"]:
        said += f". Did not answer: {', '.join(failed[:4])}"
    return {"id": "plugins", "name": "Starboard's plug-ins", "ok": not failed, "said": said}


def _version_key(v):
    out = []
    for part in str(v or "").split("."):
        try:
            out.append(int(part))
        except ValueError:
            break
    return tuple(out)


def jellyfin_waiting_now(jf, call):
    """Jellyfin's plug-ins that have a newer version in Jellyfin's repositories: [{id, name, current, latest, versions}],
    versions being each newer version's {version, changelog}, newest first. call(method, path) asks Jellyfin."""
    installed = call("GET", "/Plugins") or []
    packages = call("GET", "/Packages") or []
    by_id = {str(p.get("guid") or "").replace("-", "").lower(): p for p in packages}
    out = []
    for p in installed:
        pkg = by_id.get(str(p.get("Id") or "").replace("-", "").lower())
        if not pkg:
            continue
        current = str(p.get("Version") or "")
        newer = [v for v in pkg.get("versions") or [] if _version_key(v.get("version")) > _version_key(current)]
        if not newer:
            continue
        newer.sort(key=lambda v: _version_key(v.get("version")), reverse=True)
        out.append({"id": str(p.get("Id") or ""), "name": str(p.get("Name") or pkg.get("name") or ""), "current": current,
                    "latest": str(newer[0].get("version") or ""),
                    "versions": [{"version": str(v.get("version") or ""), "changelog": str(v.get("changelog") or "")[:4000]} for v in newer[:20]]})
    return sorted(out, key=lambda x: x["name"].lower())


def _check_jellyfin(app):
    from . import auto_updates
    jf = auto_updates._jf(app.config.data["services"])
    if not jf:
        return None  # no Jellyfin in Manage apps: nothing to say
    try:
        waiting = jellyfin_waiting_now(jf, lambda m, p: auto_updates._jf_call(jf, m, p))
    except Exception as e:  # noqa: BLE001  one part that does not answer never hides the others
        return {"id": "jellyfin-plugins", "name": "Jellyfin's plug-ins", "ok": False, "said": f"Jellyfin did not answer: {getattr(e, 'reason', e)}"[:200]}
    with _lock:
        _jellyfin.update(at=time.time(), waiting=waiting)
    n = len(waiting)
    return {"id": "jellyfin-plugins", "name": "Jellyfin's plug-ins", "ok": True,
            "said": f"{n} with a new version" if n else "All up to date"}


def jellyfin_waiting():
    """What the last check found for Jellyfin's plug-ins, while it is recent (nothing is asked here)."""
    with _lock:
        if time.time() - _jellyfin["at"] > JELLYFIN_KEEP:
            return []
        return [dict(x) for x in _jellyfin["waiting"]]


def forget_jellyfin():
    """Jellyfin's plug-ins are updating: what the last check found is no longer waiting."""
    with _lock:
        _jellyfin.update(at=0, waiting=[])


def check(app):
    """Asks every part now, in parallel, each with its own time limit: {checked_at, parts: [{id, name, ok, said}]}.
    One part that fails says why; the others still answer."""
    jobs = [("starboard", _check_starboard), ("apps", _check_apps), ("plugins", _check_plugins), ("jellyfin-plugins", _check_jellyfin)]
    parts = []
    with cf.ThreadPoolExecutor(4) as pool:
        futures = [(pid, pool.submit(fn, app)) for pid, fn in jobs]
        for pid, f in futures:
            try:
                got = f.result(timeout=90)
            except Exception as e:  # noqa: BLE001
                got = {"id": pid, "name": pid, "ok": False, "said": f"Could not check: {str(e)[:160]}"}
            if got:
                parts.append(got)
    from . import logs
    logs.event("info", "updates", "Check for updates: " + "; ".join(f"{p['name']}: {p['said']}" for p in parts))
    return {"checked_at": time.time(), "parts": parts}


# What is new -------------------------------------------------------------------------------------------------------

def _combine(versions):
    """Versions newest first, each {version, date, sections: [{type, items}]} with items as changes.parse makes them
    ({parts, items}) or as plug-in changes (parts lists), into one set of sections in Keep a Changelog's order, each
    entry with the version it came in."""
    by_type = {}
    for v in versions:
        for s in v.get("sections") or []:
            kind = str(s.get("type") or "Changed").strip().capitalize()
            for it in s.get("items") or []:
                entry = it if isinstance(it, dict) else {"parts": it, "items": []}
                by_type.setdefault(kind, []).append({"parts": entry.get("parts") or [], "items": entry.get("items") or [],
                                                     "version": v.get("version", "")})
    order = sorted(by_type, key=lambda t: TYPES.index(t) if t in TYPES else len(TYPES))
    return [{"type": t, "items": by_type[t]} for t in order]


def _releases_py(old, new):
    """Starboard's own notes, from releases.py, newest first, in the changelog's shape."""
    from . import releases
    out = []
    for r in reversed(releases.between(old, new)):
        out.append({"version": r["version"], "date": r.get("date", ""),
                    "sections": [{"type": t, "items": [{"parts": [["strong", f"{title}:"], ["text", f" {words}"]], "items": []} for title, words in r[t.lower()]]}
                                 for t in TYPES if r.get(t.lower())]})
    return out


def _starboard(app, t):
    from . import changes, releases
    old, new = t.get("current") or "", (t.get("latest") or "").lstrip("v")
    repo = getattr(app, "repo", "") or ""
    link = f"https://github.com/{repo}/releases/tag/v{new}" if repo and new else ""
    versions = _releases_py(old, new)
    known_up_to = max((releases._key(r["version"]) for r in releases.RELEASES), default=(0, 0, 0))
    words = "From Starboard's release notes."
    if releases._key(new) > known_up_to and repo and re.match(r"^[\w.-]+/[\w.-]+$", repo):
        # Newer than this copy knows: the new version's own changelog, at its tag.
        url = f"https://raw.githubusercontent.com/{repo}/v{new}/CHANGELOG.md"
        try:
            later = [v for v in changes._fetch(url) if releases._key(v["version"]) > known_up_to
                     and releases._key(old) < releases._key(v["version"]) <= releases._key(new)]
            versions = later + versions
        except Exception as e:  # noqa: BLE001
            return {"link": link, "versions": versions, "words": words,
                    "problem": f"Starboard could not read the notes for {new} just now ({str(e)[:120]})"}
    return {"link": link, "versions": versions, "words": words}


def _reelix(app, t):
    from . import changes, containers
    image = ""
    if containers.available():
        rows = containers.apps(app.config.data["services"])["items"]
        row = next((r for r in rows if r.get("container") and changes.source(r["container"].get("image"))), None)
        image = row["container"]["image"] if row else ""
    link = "https://github.com/TheMightyTRex/Reelix/releases"
    if not image or not changes.source(image):
        return {"link": link, "versions": [], "words": ""}
    got = changes.between(image, t.get("current"), t.get("latest"))
    return {"link": link, "versions": got["versions"], "words": "From Reelix's changelog.", "source": got["source"]}


def _plugin(app, t):
    from . import plugin_life, plugin_update, update_batch
    pid = t["id"].split(":", 1)[1]
    k = plugin_life.updates_known(app.data_dir).get(pid)
    if not k:
        return {"link": "", "versions": [], "words": ""}
    manifest = update_batch._manifest(k["manifest"], k.get("sha256", ""))
    link = manifest.get("homepage") or manifest.get("support_url") or ""
    versions = plugin_update.changes_between(manifest, t.get("current") or None, manifest.get("version") or t.get("latest"))
    if not versions and k.get("changelog"):  # an older plug-in: one line in the catalogue
        from . import changes
        versions = [{"version": k["version"], "date": "", "sections": [{"type": "Changed", "items": [changes._inline(k["changelog"])]}]}]
    return {"link": link, "versions": versions, "words": "From the plug-in's own notes."}


def release_page(image):
    """Where an app's image says its releases are, as well as Starboard can tell from the image's name."""
    ref = (image or "").split("@", 1)[0]
    name = ref.rsplit(":", 1)[0] if ":" in ref.split("/")[-1] else ref
    parts = name.split("/")
    if parts[0] == "lscr.io" or (len(parts) >= 2 and parts[-2] == "linuxserver"):
        return f"https://github.com/linuxserver/docker-{parts[-1]}/releases"
    if parts[0] == "ghcr.io" and len(parts) >= 3:
        return f"https://github.com/{parts[1]}/{parts[2]}/releases"
    if "." in parts[0] and len(parts) >= 3:  # another registry: its own page is not known
        return ""
    if len(parts) == 1:
        return f"https://hub.docker.com/_/{parts[0]}"
    return f"https://hub.docker.com/r/{parts[-2]}/{parts[-1]}"


def _app(app, t):
    from . import containers
    link = ""
    if containers.available():
        sid = t["id"].split(":", 1)[1]
        row = next((r for r in containers.apps(app.config.data["services"])["items"] if r["id"] == sid), None)
        link = release_page(row["container"]["image"]) if row and row.get("container") else ""
    return {"link": link, "versions": [], "words": ""}


def _jellyfin_plugin(j):
    versions = []
    for v in j["versions"]:
        lines = [x.strip() for x in (v["changelog"] or "").splitlines() if x.strip() and not x.strip().startswith("#")]
        items = [{"parts": [["text", re.sub(r"^[-*]\s+", "", x)]], "items": []} for x in lines[:40]]
        if items:
            versions.append({"version": v["version"], "date": "", "sections": [{"type": "Notes", "items": items}]})
    return {"link": "", "versions": versions, "words": "From Jellyfin's list of its plug-ins. Their makers do not sort their notes into Added, Changed and Fixed."}


def whats_new(app):
    """Every waiting update's notes in one list: {items: [{target, kind, name, from, to, link, words, sections,
    versions (the versions listed), none (why there are no notes), problem, and logo or icon for its picture}],
    count}. Fetched now, in a few threads."""
    from . import update_runs
    waiting = [t for t in update_runs.targets(app) if t.get("update_available")
               and not (t["kind"] == "app" and t["name"].strip().lower() == "starboard")]
    jobs = []
    for t in waiting:
        fn = {"starboard": _starboard, "reelix": _reelix, "plugin": _plugin}.get(t["kind"], _app)
        jobs.append((t, fn))
    out = []
    with cf.ThreadPoolExecutor(4) as pool:
        futures = [(t, pool.submit(fn, app, t)) for t, fn in jobs]
        for t, f in futures:
            try:
                got = f.result(timeout=30)
            except Exception as e:  # noqa: BLE001  one that cannot be read says so; the rest are shown
                got = {"link": "", "versions": [], "words": "", "problem": f"Starboard could not read its notes just now ({str(e)[:120]})"}
            out.append(_item(t["id"], t["kind"], t["name"], t.get("current") or "", (t.get("latest") or "").lstrip("v"), got,
                             image=_image(t)))
    for j in jellyfin_waiting():
        out.append(_item(f"jellyfin:{j['id']}", "jellyfin-plugin", j["name"], j["current"], j["latest"], _jellyfin_plugin(j)))
    rank = {"starboard": 0, "reelix": 1, "plugin": 2, "jellyfin-plugin": 3, "app": 4}
    out.sort(key=lambda i: (rank.get(i["kind"], 5), i["name"].lower()))
    return {"items": out, "count": len(out)}


def _image(t):
    """The picture shown beside an update's notes in What is new (DASH-475), as on its card: a plug-in's own logo
    (or None, for its initials), an app's or Reelix's icon as the dashboard keeps it, Starboard's own mark."""
    if t["kind"] == "plugin":
        return {"logo": t.get("logo") or None}
    if t["kind"] in ("app", "reelix") and t.get("icon"):
        return {"icon": t["icon"]}
    if t["kind"] == "starboard":
        return {"logo": {"url": "/favicon.svg", "alt": ""}}
    return {}


def _item(target, kind, name, came, going, got, image=None):
    versions = got.get("versions") or []
    item = {"target": target, "kind": kind, "name": name, "from": came, "to": going, "link": got.get("link") or "",
            **(image or {}),
            "words": got.get("words") or "", "versions": [v.get("version") for v in versions],
            "sections": _combine(versions), "problem": got.get("problem") or "", "none": ""}
    if got.get("source"):
        item["source"] = got["source"]
    if not item["sections"] and not item["problem"]:
        item["words"] = ""
        item["none"] = (f"Starboard has no notes for {name}. Its maker lists what changed on its release page." if item["link"]
                        else f"Starboard has no notes for {name}, and does not know where its maker lists them.")
    return item
