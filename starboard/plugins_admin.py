"""Settings, Plug-ins (DASH-149): adding, enabling, disabling and removing plug-ins, their settings, and Stop all.
The manifest, permissions and Compose file are in plugins.py; the design is PLUGIN-SYSTEM-DESIGN (DASH-272).

Each plug-in lives in data/plugins/<id>/: manifest.json, settings.json (secrets owner-only), key (its API key,
owner-only), compose.yaml and state.json. Removing one moves the folder to data/plugins/.removed/<id>-<date>;
Starboard never deletes it (the owner removes it by hand).
"""
import datetime as dt
import json
import os
import re
import shutil
import urllib.request

from . import api_v1, plugins

STATES = ("installed", "enabled", "disabled", "failed")
MAX_MANIFEST = 256 * 1024


def root(data_dir):
    return os.path.join(data_dir, "plugins")


def folder(data_dir, pid):
    if not re.match(plugins.ID, pid or ""):
        raise ValueError("Not a plug-in id")
    return os.path.join(root(data_dir), pid)


def _write(path, data, mode=0o600):
    tmp = path + ".new"
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "w", encoding="utf-8") as f:
        f.write(data if isinstance(data, str) else json.dumps(data, indent=1))
    os.replace(tmp, path)


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


def fetch_manifest(address, opener=None):
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
_catalogue = {"at": 0, "items": None}


def _clean_entry(e):
    if not isinstance(e, dict) or not re.match(plugins.ID, str(e.get("id", ""))):
        return None
    address = str(e.get("manifest") or "")
    return {"id": e["id"], "name": str(e.get("name") or e["id"])[:40], "description": str(e.get("description") or "")[:240],
            "kind": str(e.get("kind") or "Other")[:30], "author": str(e.get("author") or "")[:60],
            "permissions": [p for p in e.get("permissions") or [] if p in plugins.PERMISSIONS],
            "manifest": address if re.match(r"^https://\S{1,400}$", address) else "", "published": bool(e.get("published"))}


def catalogue(opener=None, now=None):
    """The Starboard plug-ins collection: its catalogue.json, fetched at most once a day (checked like any outside
    address, 5 seconds, 256 KB), else the copy Starboard ships."""
    import time
    now = now or time.time()
    if _catalogue["items"] is None or now - _catalogue["at"] > 86400:
        items = None
        try:
            from . import outside
            outside.check_url(CATALOGUE_URL)
            req = urllib.request.Request(CATALOGUE_URL, headers={"User-Agent": "Starboard", "Accept": "application/json"})
            with (opener or urllib.request.build_opener()).open(req, timeout=5) as r:  # checked above  # nosec B310
                items = json.loads(r.read(MAX_MANIFEST)).get("plugins")
        except Exception:  # noqa: BLE001 - offline or not there yet: the shipped copy
            items = None
        if not isinstance(items, list):
            items = (_read(CATALOGUE_FILE, {}) or {}).get("plugins") or []
        _catalogue.update(at=now, items=[x for x in map(_clean_entry, items) if x][:200])
    return list(_catalogue["items"])


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
            out.append({**summary(m, []), "looks": looks, "builtin": bool(st.get("builtin")), "state": st.get("state", "installed"), "installed_at": st.get("installed_at"),
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
    if _runs_nothing(data_dir, pid):  # only styles: nothing to start (DASH-284)
        set_state(data_dir, pid, "enabled")
        api_v1.audit(data_dir, "plugin_enabled", plugin=pid)
        return
    write_jellyfin(data_dir, pid, services)
    ok, text = _compose_run(data_dir, pid, "up -d --remove-orphans", helper)
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
        out.append({**{k: s[k] for k in ("key", "label", "type", "hint", "min", "max", "unit", "choices") if k in s},
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
            if t == "folder" and (".." in v or not v.startswith("/")):
                raise ValueError(f"{s['label']}: give a folder inside the plug-in's own folders")
        elif t == "list":
            if not isinstance(v, list):
                raise ValueError(f"{s['label']}: give a list")
            v = [str(x)[:500] for x in v][:200]
        values[key] = v
    _write(path, values)
    api_v1.audit(data_dir, "plugin_settings", plugin=pid, keys=sorted(incoming or {}))
    return public_settings(data_dir, pid, m)
