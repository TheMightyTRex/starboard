"""Settings, Plug-ins (DASH-149): adding, enabling, disabling and removing plug-ins, their settings, and Stop all.
The manifest, permissions and Compose file are in plugins.py; the design is PLUGIN-SYSTEM-DESIGN (DASH-272).

Each plug-in lives in data/plugins/<id>/ (owner-only): manifest.json, settings.json, key (its API key), compose.yaml
and state.json. What its containers read (settings.json, key and jellyfin.json) is copied into run/, which they mount
as the folder /run/starboard (DASH-357): readable by any user a container runs as, while the 0700 folder around it
keeps everyone else on the computer out, and a saved setting reaches a running plug-in at once. Removing one moves the folder to data/plugins/.removed/<id>-<date>;
Starboard never deletes it (the owner removes it by hand).
"""
import datetime as dt
import json
import os
import re
import shutil
import urllib.request

from . import api_v1, plugins

STATES = ("installed", "enabled", "disabled", "failed")  # stored; plugin_life.status adds needs-setup and not-supported
MAX_MANIFEST = 256 * 1024


def root(data_dir):
    return os.path.join(data_dir, "plugins")


def folder(data_dir, pid):
    if not re.match(plugins.ID, pid or ""):
        raise ValueError("Not a plug-in id")
    return os.path.join(root(data_dir), pid)


SHARED = ("settings.json", "key", "jellyfin.json")  # what a plug-in's containers read, from run/ (DASH-357)


def _write(path, data, mode=0o600):
    tmp = path + ".new"
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "w", encoding="utf-8") as f:
        f.write(data if isinstance(data, str) else json.dumps(data, indent=1))
    os.replace(tmp, path)
    where, name = os.path.split(path)
    if name in SHARED and os.path.basename(os.path.dirname(where)) == "plugins":
        share(where)


def share(where):
    """Copies what the plug-in's containers read into run/ (0755, files 0644) inside its 0700 folder. Each file is
    replaced whole, so a container never reads half a file, and the folder mount shows the new one at once."""
    run = os.path.join(where, "run")
    os.makedirs(run, exist_ok=True)
    os.chmod(where, 0o700)
    os.chmod(run, 0o755)
    for name in SHARED:
        src, dst = os.path.join(where, name), os.path.join(run, name)
        if not os.path.exists(src):
            if os.path.exists(dst):
                os.remove(dst)  # a copy of something Starboard no longer keeps, such as Jellyfin's key once not allowed
            continue
        with open(src, "rb") as f:
            raw = f.read()
        tmp = dst + ".new"
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644), "wb") as f:
            f.write(raw)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dst)


_ONE = r'(\s*- )"([^"\n]*)/(?:settings\.json|key|jellyfin\.json):/run/starboard/(?:settings\.json|key|jellyfin\.json):ro"\n'
OLD_MOUNTS = re.compile(rf"^{_ONE}(?:\s*- \"[^\"\n]*/(?:settings\.json|key|jellyfin\.json):/run/starboard/[a-z.]+:ro\"\n)*", re.M)


def upgrade_mounts(where):
    """A Compose file from before DASH-357 mounts settings.json, key and jellyfin.json one by one, so a running
    plug-in kept the file it started with. Rewrites each container's lines as the one run/ folder. True if changed."""
    path = os.path.join(where, "compose.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False
    new = OLD_MOUNTS.sub(lambda m: f'{m.group(1)}"{m.group(2)}/run:/run/starboard:ro"\n', text)
    if new == text:
        return False
    share(where)
    _write(path, new, 0o644)
    return True


def _read(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def styles(data_dir):
    """Every style from plug-ins that are turned on: [{value, name, description, plugin}] for Display (DASH-284)."""
    out = []
    for p in listing(data_dir):
        if p["state"] != "enabled":
            continue
        m = _read(os.path.join(folder(data_dir, p["id"]), "manifest.json"), {})
        for st in m.get("styles") or []:
            out.append({"value": f"{p['id']}.{st['id']}", "name": st["name"], "description": st.get("description", ""),
                        "plugin": p["name"], "light": st["light"]["accent"], "dark": st["dark"]["accent"],
                        "bg": st["light"]["bg"], "bg_dark": st["dark"]["bg"]})
    return out


def styles_css(data_dir):
    from . import plugin_styles
    rules = []
    for p in listing(data_dir):
        if p["state"] == "enabled":
            m = _read(os.path.join(folder(data_dir, p["id"]), "manifest.json"), {})
            rules.append(plugin_styles.css(p["id"], m.get("styles") or []))
    return "".join(rules)


def summary(manifest, problems=None):
    """What the Add a plug-in screen shows before anything is installed."""
    return {"id": manifest.get("id"), "name": manifest.get("name"), "version": manifest.get("version"),
            "description": manifest.get("description"), "author": manifest.get("author"), "licence": manifest.get("licence"),
            "homepage": manifest.get("homepage"), "needs": manifest.get("needs") or [],
            "permissions": plugins.permission_words(manifest) if isinstance(manifest.get("permissions"), list) else [],
            "containers": [{"name": c.get("name"), "network": c.get("network", "default"), "volumes": c.get("volumes") or []}
                           for c in manifest.get("containers") or [] if isinstance(c, dict)],
            "actions": [{"id": a.get("id") or str(i), "label": a.get("label", "")} for i, a in enumerate(manifest.get("actions") or [])
                        if isinstance(a, dict)],
            "styles": [{"id": st.get("id"), "name": st.get("name"), "description": st.get("description", "")}
                       for st in manifest.get("styles") or [] if isinstance(st, dict)],
            "warning": plugins.install_warning(manifest),
            "problems": problems if problems is not None else plugins.check(manifest)}


def fetch_manifest(address, opener=None, sha256=""):
    """A manifest from an https address (a repository's raw starboard-plugin.json), checked like any address
    Starboard is told to call (DASH-279), 5 seconds and 256 KB at most."""
    from . import outside
    address = str(address or "").strip()
    if not re.match(r"^https://\S+$", address):
        raise ValueError("Give the manifest's https address, such as a repository's raw starboard-plugin.json")
    outside.check_url(address)
    req = urllib.request.Request(address, headers={"User-Agent": "Starboard", "Accept": "application/json"})
    with (opener or urllib.request.build_opener()).open(req, timeout=5) as r:  # checked above  # nosec B310
        raw = r.read(MAX_MANIFEST + 1)
    if len(raw) > MAX_MANIFEST:
        raise ValueError("That manifest is too large")
    if sha256:  # from a catalogue (DASH-330): the file must be the one the catalogue listed
        import hashlib
        if hashlib.sha256(raw).hexdigest() != sha256:
            raise ValueError("The file changed since the catalogue listed it, so Starboard did not use it")
    return parse(raw)


def parse(raw):
    try:
        m = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ValueError("That is not a plug-in manifest (starboard-plugin.json)") from None
    if not isinstance(m, dict):
        raise ValueError("That is not a plug-in manifest (starboard-plugin.json)")
    return m


def added(data_dir):
    """The plug-ins added (any state), [{id, name}], for the menus: a plug-in's pages and its tab in Settings,
    Plug-ins show only once it is added."""
    try:
        names = sorted(os.listdir(root(data_dir)))
    except OSError:
        return []
    out = []
    for p in names:
        m = _read(os.path.join(root(data_dir), p, "manifest.json")) if re.match(plugins.ID, p) else None
        if isinstance(m, dict):
            out.append({"id": p, "name": str(m.get("name") or p)[:40]})
    return sorted(out, key=lambda x: x["name"].lower())


CATALOGUE_URL = "https://raw.githubusercontent.com/TheMightyTRex/starboard-plugins/main/catalogue.json"
CATALOGUE_FILE = os.path.join(plugins.BUILTIN_DIR, "catalogue.json")  # the copy Starboard ships, used until the first fetch
MAX_SOURCES = 10
_catalogues = {}  # address -> {"at", "name", "items", "error"}


def _clean_entry(e):
    if not isinstance(e, dict) or not re.match(plugins.ID, str(e.get("id", ""))):
        return None
    # Versions (DASH-330): each with the Starboard API it needs and its manifest's SHA-256. Only the newest version
    # this Starboard can run is offered; how many newer ones were hidden, and what they need, is said under it.
    from . import plugin_life
    versions = plugin_life.clean_versions(e)
    best, hidden, needs = plugin_life.best_version(versions)
    return {"id": e["id"], "name": str(e.get("name") or e["id"])[:40], "description": str(e.get("description") or "")[:240],
            "kind": str(e.get("kind") or "Other")[:30], "author": str(e.get("author") or "")[:60],
            "permissions": [p for p in e.get("permissions") or [] if p in plugins.PERMISSIONS],
            "notices": [n for n in e.get("notices") or [] if n in plugins.NOTICES],
            "manifest": (best or {}).get("manifest", ""), "version": (best or {}).get("version", ""),
            "sha256": (best or {}).get("sha256", ""), "changelog": (best or {}).get("changelog", ""),
            "versions": [best] if best else [], "hidden": hidden, "hidden_needs": needs,
            "published": bool(e.get("published", True))}


def fetch_catalogue(address, opener=None):
    """One catalogue.json from an https address: {"name", "plugins": [...]}, checked like any outside address
    (5 seconds, 256 KB). ValueError says what is wrong in plain words."""
    from . import outside
    address = str(address or "").strip()
    if not re.match(r"^https://\S{1,400}$", address):
        raise ValueError("Give the catalogue's https address, such as a repository's raw catalogue.json")
    outside.check_url(address)
    req = urllib.request.Request(address, headers={"User-Agent": "Starboard", "Accept": "application/json"})
    try:
        with (opener or urllib.request.build_opener()).open(req, timeout=5) as r:  # checked above  # nosec B310
            raw = r.read(MAX_MANIFEST + 1)
    except OSError as e:
        raise ValueError(f"That address did not answer: {e}") from None
    if len(raw) > MAX_MANIFEST:
        raise ValueError("That catalogue is too large")
    try:
        data = json.loads(raw)
    except ValueError:
        raise ValueError("That is not a plug-in catalogue (catalogue.json)") from None
    if not isinstance(data, dict) or not isinstance(data.get("plugins"), list):
        raise ValueError("That is not a plug-in catalogue: it has no list of plug-ins")
    items = [x for x in map(_clean_entry, data["plugins"]) if x][:200]
    return {"name": str(data.get("name") or address.split("/")[2])[:60], "items": items}


def sources(cfg):
    """The catalogues Starboard reads: its own collection first (always), then the ones added from a link."""
    extra = [x for x in cfg.data.get("plugin_catalogues") or [] if isinstance(x, dict) and x.get("url")]
    return [{"url": CATALOGUE_URL, "own": True}] + [{"url": x["url"], "own": False} for x in extra][:MAX_SOURCES]


def add_source(cfg, address, opener=None):
    got = fetch_catalogue(address, opener)
    have = [x for x in cfg.data.get("plugin_catalogues") or [] if isinstance(x, dict)]
    if address.strip() == CATALOGUE_URL or any(x.get("url") == address.strip() for x in have):
        raise ValueError("That catalogue is already in the list")
    if len(have) >= MAX_SOURCES:
        raise ValueError(f"Starboard reads {MAX_SOURCES} catalogues at most. Remove one first")
    cfg.data["plugin_catalogues"] = have + [{"url": address.strip(), "name": got["name"]}]
    cfg.save()
    _catalogues.pop(address.strip(), None)
    return got


def remove_source(cfg, address):
    have = [x for x in cfg.data.get("plugin_catalogues") or [] if isinstance(x, dict)]
    left = [x for x in have if x.get("url") != address]
    if len(left) == len(have):
        raise LookupError("That catalogue is not in the list")
    cfg.data["plugin_catalogues"] = left
    cfg.save()
    _catalogues.pop(address, None)


def catalogue(cfg=None, opener=None, now=None):
    """Every catalogue's plug-ins, each read at most once a day. Starboard's own collection falls back to the copy it
    ships; another catalogue that does not answer keeps its last good list and says so.
    Returns (catalogues [{url, name, own, count, error}], plug-ins [... with "catalogue" and "own"])."""
    import time
    now = now or time.time()
    srcs = sources(cfg) if cfg is not None else [{"url": CATALOGUE_URL, "own": True}]
    out_sources, out_items = [], []
    for src in srcs:
        url = src["url"]
        hit = _catalogues.get(url)
        if not hit or now - hit["at"] > 86400:
            try:
                got = fetch_catalogue(url, opener)
                hit = {"at": now, "name": got["name"], "items": got["items"], "error": ""}
            except Exception as e:  # noqa: BLE001 - offline, moved or broken: say so, keep what we had
                if src["own"] and not (hit and hit["items"]):
                    shipped = _read(CATALOGUE_FILE, {}) or {}
                    hit = {"at": now, "name": shipped.get("name") or "Starboard plug-ins",
                           "items": [x for x in map(_clean_entry, shipped.get("plugins") or []) if x], "error": ""}
                else:
                    hit = {**(hit or {"name": url.split("/")[2], "items": []}), "at": now, "error": str(e)[:200]}
            _catalogues[url] = hit
        out_sources.append({"url": url, "name": hit["name"], "own": src["own"], "count": len(hit["items"]), "error": hit["error"]})
        out_items += [{**x, "catalogue": hit["name"], "own": src["own"]} for x in hit["items"]]
    return out_sources, out_items


def listing(data_dir):
    out = []
    try:
        names = sorted(os.listdir(root(data_dir)))
    except OSError:
        names = []
    for pid in names:
        if pid.startswith(".") or not re.match(plugins.ID, pid):
            continue
        m = _read(os.path.join(root(data_dir), pid, "manifest.json"))
        st = _read(os.path.join(root(data_dir), pid, "state.json"), {})
        if m:
            from . import plugin_styles
            fonts = plugin_styles.FONTS
            looks = [{"value": f"{pid}.{x['id']}", "id": x["id"], "name": x["name"], "description": x.get("description", ""),
                      "light": x["light"], "dark": x["dark"], "radius": x.get("radius", 0), "shadow": x.get("shadow", "none"),
                      "font": fonts.get(x.get("font", "hyperlegible"), fonts["hyperlegible"])}
                     for x in m.get("styles") or [] if isinstance(x, dict)]
            from . import plugin_life
            out.append({**summary(m, []), "looks": looks, "builtin": bool(st.get("builtin")), "state": st.get("state", "installed"), "installed_at": st.get("installed_at"),
                        "status": plugin_life.status(data_dir, pid, m, st), "jobs": [j.get("label") for j in m.get("jobs") or []],
                        "message": st.get("message", ""), "settings": public_settings(data_dir, pid, m)})
    return out


def builtins():
    """Plug-ins that ship inside Starboard (plugins/<id>/starboard-plugin.json), by id."""
    out = {}
    try:
        names = sorted(os.listdir(plugins.BUILTIN_DIR))
    except OSError:
        return out
    for name in names:
        m = _read(os.path.join(plugins.BUILTIN_DIR, name, "starboard-plugin.json"))
        if m and m.get("id") == name:
            out[name] = m
    return out


def own_image():
    """The image Starboard itself runs, which built-in plug-ins run too; None outside Docker."""
    from . import containers
    try:
        info = containers.docker("GET", "/containers/starboard/json")
    except containers.DockerError:
        return None
    return (info.get("Config") or {}).get("Image") or None


def host_for_builtin():
    """What a built-in plug-in's Compose file needs from this install."""
    return {"image": own_image(), "user": f"{os.getuid()}:{os.getgid()}",
            "iptv": os.environ.get("STARBOARD_LIVETV_PATH") or None, "tz": os.environ.get("TZ") or None}


def install(data_dir, manifest, media_dir, dev=False, builtin=False, defaults=None, host=None):
    """Checks and installs a plug-in (not started): its folder, settings with defaults, its API key with exactly the
    approved scopes, and its Compose file. Returns its listing entry."""
    builtin = builtin and manifest.get("id") in builtins() and builtins()[manifest["id"]] == manifest
    problems = plugins.check(manifest, dev=dev, builtin=builtin)
    if problems:
        raise ValueError("This plug-in cannot be added: " + "; ".join(problems[:6]))
    pid = manifest["id"]
    where = folder(data_dir, pid)
    if os.path.exists(os.path.join(where, "manifest.json")):
        raise ValueError(f"{manifest['name']} is already added. Update it from its tab instead")
    os.makedirs(where, mode=0o700, exist_ok=True)
    _write(os.path.join(where, "manifest.json"), manifest)
    values = {s["key"]: s["default"] for s in manifest.get("settings") or [] if "default" in s}
    values.update({k: v for k, v in (defaults or {}).items() if k in {s["key"] for s in manifest.get("settings") or []}})
    _write(os.path.join(where, "settings.json"), values)
    item = {"id": None}
    if manifest.get("containers"):  # only something that runs gets an API key and a Compose file
        key, item = api_v1.create_key(data_dir, f"Plug-in: {manifest['name']}"[:60], "read", plugins.key_scopes(manifest), None)
        _write(os.path.join(where, "key"), key)
        hosted = (host or host_for_builtin()) if builtin else None
        _write(os.path.join(where, "compose.yaml"), plugins.compose(manifest, host_path(data_dir, pid), media_dir, hosted), 0o644)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write(os.path.join(where, "state.json"), {"state": "installed", "installed_at": now, "key_id": item["id"], "builtin": builtin})
    api_v1.audit(data_dir, "plugin_installed", plugin=pid, version=manifest["version"], permissions=manifest.get("permissions") or [])
    return next(p for p in listing(data_dir) if p["id"] == pid)


def host_path(data_dir, pid):
    """data/plugins/<id> as the computer itself sees it (Starboard may run in a container)."""
    from . import stack
    host = stack.host_folder(data_dir)
    base = host[: -len("/stack")] if host and host.endswith("/stack") else os.path.abspath(data_dir)
    return f"{base}/plugins/{pid}"


def _prepare_folders(data_dir, pid):
    """Shell lines that make each container's data folder and give it to the user the container runs as, run as root
    in the helper before starting: a folder Docker makes by itself belongs to root, and the plug-in could not write."""
    from . import containers
    m = _read(os.path.join(folder(data_dir, pid), "manifest.json"), {}) or {}
    st = _read(os.path.join(folder(data_dir, pid), "state.json"), {}) or {}
    lines = []
    for c in m.get("containers") or []:
        if "data" not in (c.get("volumes") or []):
            continue
        user = c.get("user") or (f"{os.getuid()}:{os.getgid()}" if st.get("builtin") and c.get("image") == "starboard" else "10001:10001")
        if not re.match(r"^\d{1,6}:\d{1,6}$", user) or not re.match(r"^[a-z0-9-]{1,21}$", c.get("name", "")):
            continue
        d = containers._quote(f"data/{c['name']}")
        lines.append(f"mkdir -p {d} && chown {user} {d} && chmod 700 {d}")
    return " && ".join(lines)


def _compose_run(data_dir, pid, command, helper=None):
    """Runs `docker compose <command>` for the plug-in in the short-lived helper; returns (ok, text)."""
    from . import containers
    if helper is None and not containers.available():
        return False, "Starboard has no access to Docker here, so it cannot start or stop plug-ins"
    host = host_path(data_dir, pid)
    q = containers._quote
    # The exit code is kept (a pipe into tail would hide a failure), and only the last lines are shown.
    prep = _prepare_folders(data_dir, pid) if command.startswith("up") else ""
    script = ((f"{prep} || {{ echo 'Could not make its data folder'; exit 1; }}; " if prep else "") +
              f"out=$(docker compose -p {q('plugin-' + pid)} -f compose.yaml {command} 2>&1); code=$?; "
              "printf '%s\n' \"$out\" | tail -n 40")
    if command.startswith("up"):
        # Starboard joins the plug-in's own network, so the plug-in can reach Starboard's API and nothing else.
        script += f"; [ $code -eq 0 ] && docker network connect {q('plugin-' + pid)} starboard 2>/dev/null"
    script += "; exit $code"
    try:
        code, text = (helper or containers._helper)(host, script)
    except containers.DockerError as e:
        return False, f"Starboard cannot reach Docker ({e})"
    return code == 0, text


def set_state(data_dir, pid, state, message=""):
    st = _read(os.path.join(folder(data_dir, pid), "state.json"), {})
    st.update(state=state, message=message[:500])
    _write(os.path.join(folder(data_dir, pid), "state.json"), st)


def _runs_nothing(data_dir, pid):
    return not (_read(os.path.join(folder(data_dir, pid), "manifest.json"), {}) or {}).get("containers")


def write_jellyfin(data_dir, pid, services):
    """Jellyfin's address and key for a plug-in that was allowed them (jellyfin:key), owner-only, as the plug-in's
    containers reach Jellyfin: an address on this computer goes through host.docker.internal."""
    m = _read(os.path.join(folder(data_dir, pid), "manifest.json"), {}) or {}
    if "jellyfin:key" not in (m.get("permissions") or []):
        return False
    jf = next((s for s in services or [] if s.get("type") == "jellyfin" and s.get("url") and s.get("api_key")), None)
    url = re.sub(r"^(https?://)(127\.0\.0\.1|localhost)(?=[:/]|$)", r"\1host.docker.internal", (jf or {}).get("url", ""))
    _write(os.path.join(folder(data_dir, pid), "jellyfin.json"), {"url": url, "api_key": (jf or {}).get("api_key", "")})
    return bool(jf)


def enable(data_dir, pid, helper=None, services=None):
    from . import plugin_life
    plugin_life.can_enable(data_dir, pid)  # set up first, and only on a Starboard it was made for (DASH-330)
    if _runs_nothing(data_dir, pid):  # only styles: nothing to start (DASH-284)
        set_state(data_dir, pid, "enabled")
        api_v1.audit(data_dir, "plugin_enabled", plugin=pid)
        return
    write_jellyfin(data_dir, pid, services)
    where = folder(data_dir, pid)
    upgrade_mounts(where)
    share(where)  # also after Roll back, which moves files rather than writing them
    ok, text = _compose_run(data_dir, pid, "up -d --remove-orphans", helper)
    st = _read(os.path.join(where, "state.json"), {}) or {}
    if st.pop("resting", None) is not None:  # up -d started every container, resting ones too (DASH-357)
        _write(os.path.join(where, "state.json"), st)
    set_state(data_dir, pid, "enabled" if ok else "failed", "" if ok else text[-300:])
    api_v1.audit(data_dir, "plugin_enabled" if ok else "plugin_failed", plugin=pid)
    if not ok:
        raise ValueError(f"It did not start: {text.strip()[-200:]}")


def disable(data_dir, pid, helper=None):
    if _runs_nothing(data_dir, pid):
        set_state(data_dir, pid, "disabled")
        api_v1.audit(data_dir, "plugin_disabled", plugin=pid)
        return
    ok, text = _compose_run(data_dir, pid, "stop", helper)
    set_state(data_dir, pid, "disabled", "" if ok else text[-300:])
    api_v1.audit(data_dir, "plugin_disabled", plugin=pid)


def uninstall(data_dir, pid, helper=None):
    """Stops and removes its containers, revokes its key, and moves its folder aside (never deleted)."""
    where = folder(data_dir, pid)
    st = _read(os.path.join(where, "state.json"), {})
    try:
        if not _runs_nothing(data_dir, pid):
            _compose_run(data_dir, pid, "down", helper)
    except Exception:  # Docker may be unreachable; the folder still moves and the key still goes
        pass
    if st.get("key_id"):
        api_v1.revoke_key(data_dir, st["key_id"])
    aside = os.path.join(root(data_dir), ".removed")
    os.makedirs(aside, mode=0o700, exist_ok=True)
    target = os.path.join(aside, f"{pid}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.move(where, target)
    api_v1.audit(data_dir, "plugin_removed", plugin=pid)
    return target


def refresh_builtins(data_dir, media_dir, services, helper=None, host=None):
    """At each start: a built-in plug-in follows Starboard's own update. Its manifest and Compose file are written
    again from the copy inside Starboard, and an active one is started again, so it runs the new image with the new
    settings. Returns the names started again; a problem is left in the plug-in's own state, never raised."""
    done = []
    shipped = builtins()
    for p in listing(data_dir):
        if not p.get("builtin") or p["id"] not in shipped:
            continue
        pid, manifest = p["id"], shipped[p["id"]]
        where = folder(data_dir, pid)
        try:
            text = plugins.compose(manifest, host_path(data_dir, pid), media_dir, host or host_for_builtin())
        except ValueError as e:
            set_state(data_dir, pid, p["state"], str(e))
            continue
        _write(os.path.join(where, "manifest.json"), manifest)
        _write(os.path.join(where, "compose.yaml"), text, 0o644)
        if p["state"] == "enabled":
            try:
                enable(data_dir, pid, helper=helper, services=services)
                done.append(p["name"])
            except ValueError:
                pass  # enable() has recorded why, for its section in Settings, Plug-ins
    return done


def upgrade_all(data_dir, services, helper=None):
    """At each start, for plug-ins added before DASH-357: run/ is filled and the Compose file mounts it; an active
    one is started again once so it reads the folder. Returns the names started again."""
    done = []
    for p in listing(data_dir):
        where = folder(data_dir, p["id"])
        try:
            share(where)
            changed = upgrade_mounts(where)
        except OSError as e:
            set_state(data_dir, p["id"], p["state"], f"Its files could not be shared: {e}")
            continue
        if changed and p["state"] == "enabled":
            try:
                enable(data_dir, p["id"], helper=helper, services=services)
                done.append(p["name"])
            except ValueError:
                pass
    return done


def stop_all(data_dir, helper=None):
    """The kill switch (PS11): every enabled plug-in stopped."""
    stopped = []
    for p in listing(data_dir):
        if p["state"] == "enabled":
            disable(data_dir, p["id"], helper)
            stopped.append(p["name"])
    return stopped


# Settings -----------------------------------------------------------------------------------------------------

def public_settings(data_dir, pid, manifest=None):
    """Its settings for the page: secrets as set or not set, never their values (P7)."""
    m = manifest or _read(os.path.join(folder(data_dir, pid), "manifest.json"), {})
    values = _read(os.path.join(folder(data_dir, pid), "settings.json"), {})
    out = []
    for s in m.get("settings") or []:
        v = values.get(s["key"])
        out.append({**{k: s[k] for k in ("key", "label", "type", "hint", "min", "max", "unit", "choices", "required") if k in s},
                    "value": (None if s["type"] == "secret" else v), "set": v not in (None, "")})
    return out


def save_settings(data_dir, pid, incoming):
    m = _read(os.path.join(folder(data_dir, pid), "manifest.json"))
    if not m:
        raise LookupError("No plug-in with that id")
    path = os.path.join(folder(data_dir, pid), "settings.json")
    values = _read(path, {})
    spec = {s["key"]: s for s in m.get("settings") or []}
    for key, v in (incoming or {}).items():
        s = spec.get(key)
        if not s or s["type"] == "custom":
            raise ValueError(f"{key} is not one of {m['name']}'s settings")
        t = s["type"]
        if t == "switch":
            v = bool(v)
        elif t == "number":
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v < s.get("min", float("-inf")) or v > s.get("max", float("inf")):
                raise ValueError(f"{s['label']}: give a number from {s.get('min', '')} to {s.get('max', '')}".replace("from  to ", ""))
        elif t == "choice":
            if v not in (s.get("choices") or []):
                raise ValueError(f"{s['label']}: choose one from the list")
        elif t == "address":
            from . import outside
            outside.check_url(v)
        elif t == "secret":
            if v in (None, ""):
                continue  # empty keeps the one there is
            v = str(v)[:2000]
        elif t in ("text", "folder"):
            v = str(v)[:500]
            if t == "folder":
                from .plugins import media_mounts
                inside = media_mounts(m)
                v = v.rstrip("/") or "/"
                if ".." in v.split("/") or not any(v == top or v.startswith(top + "/") for top in inside):
                    raise ValueError(f"{s['label']}: choose a folder inside {', '.join(inside) or 'the media folder'}")
        elif t == "list":
            if not isinstance(v, list):
                raise ValueError(f"{s['label']}: give a list")
            v = [str(x)[:500] for x in v][:200]
        values[key] = v
    _write(path, values)
    api_v1.audit(data_dir, "plugin_settings", plugin=pid, keys=sorted(incoming or {}))
    from . import plugin_life
    if not plugin_life.missing_settings(m, values):
        plugin_life.mark_set_up(data_dir, pid)
    return public_settings(data_dir, pid, m)
