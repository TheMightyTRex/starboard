"""Copying settings from one Sonarr, Radarr or Lidarr into another (Settings, Apps, Manage apps, Copy app settings).

For a new app next to an old one, or a second copy (a 4K Radarr, say). Both apps must be in Manage apps with their
API keys, be the same kind and the same major version. What can be copied, in this order (later parts point at
earlier ones by name, so ids are matched again in the new app):
  tags, custom formats, quality profiles, root folders, download clients and remote path mappings, naming,
  media management.
Nothing in the new app is changed or removed: a part that is already there by name is left as it is. Naming and
media management are the exception: they are one set of settings each, so copying them replaces the new app's.

Passwords and keys come back from the old app as ******** (the apps never send them), so a download client that
needs one is asked for it; without it the client is added switched off. Indexers are not copied: add the new app
in Prowlarr instead, which keeps them in step.
"""

from .services import ServiceError, _api

PARTS = {
    "tags": "Tags",
    "formats": "Custom formats",
    "profiles": "Quality profiles",
    "folders": "Root folders",
    "clients": "Download clients and remote path mappings",
    "naming": "Naming",
    "media": "Media management",
}
KINDS = ("sonarr", "radarr", "lidarr")
HIDDEN = "********"


def _major(service):
    return str((_api(service, "/system/status", timeout=10) or {}).get("version", "")).split(".")[0]


def check(source, target):
    """Raises ValueError when the two apps cannot be copied between."""
    if source["type"] not in KINDS:
        raise ValueError("Copy from a Sonarr, Radarr or Lidarr")
    if source["type"] != target["type"]:
        raise ValueError(f"Copy between two apps of the same kind: {source['name']} is not the same kind as {target['name']}")
    if source["id"] == target["id"]:
        raise ValueError("Choose two different apps")
    for s in (source, target):
        if not s.get("api_key"):
            raise ValueError(f"Give {s['name']} its API key in Manage apps first")
    a, b = _major(source), _major(target)
    if a != b:
        raise ValueError(f"{source['name']} is version {a} and {target['name']} is version {b}. Copy only between the same major version")


def _read(service, parts):
    get = lambda path: _api(service, path, timeout=30) or []
    out = {}
    if parts & {"tags", "clients", "folders", "profiles", "formats"}:
        out["tags"] = get("/tag")
    if parts & {"formats", "profiles"}:
        out["formats"] = get("/customformat")
    if parts & {"profiles", "folders"}:
        out["profiles"] = get("/qualityprofile")
    if "folders" in parts:
        out["folders"] = get("/rootfolder")
        if service["type"] == "lidarr":
            out["metadata"] = get("/metadataprofile")
    if "clients" in parts:
        out["clients"] = get("/downloadclient")
        out["mappings"] = get("/remotepathmapping")
    if "naming" in parts:
        out["naming"] = _api(service, "/config/naming", timeout=30) or {}
    if "media" in parts:
        out["media"] = _api(service, "/config/mediamanagement", timeout=30) or {}
    return out


def _hidden(client):
    return [f["name"] for f in client.get("fields") or [] if f.get("value") == HIDDEN]


def _field_label(client, name):
    f = next((f for f in client.get("fields") or [] if f["name"] == name), {})
    return f.get("label") or name


def preview(source, target, parts):
    """What copying would do, part by part: each item is add, there (left as it is) or replace."""
    check(source, target)
    parts = set(parts) & set(PARTS)
    old, new = _read(source, parts), _read(target, parts)
    out = []
    named = {"tags": ("tags", "label"), "formats": ("formats", "name"), "profiles": ("profiles", "name"),
             "folders": ("folders", "path")}
    for part in PARTS:
        if part not in parts:
            continue
        items = []
        if part in named:
            key, field = named[part]
            have = {str(x.get(field, "")).lower() for x in new[key]}
            items = [{"name": x.get(field, ""), "state": "there" if str(x.get(field, "")).lower() in have else "add"} for x in old[key]]
        elif part == "clients":
            have = {c["name"].lower() for c in new["clients"]}
            for c in old["clients"]:
                there = c["name"].lower() in have
                items.append({"name": c["name"], "state": "there" if there else "add", "kind": c.get("implementationName") or c.get("implementation"),
                              "needs": [] if there else [{"field": n, "label": _field_label(c, n)} for n in _hidden(c)]})
            have = {(m.get("host", "").lower(), m.get("remotePath", "")) for m in new["mappings"]}
            items += [{"name": f"{m.get('host')}: {m.get('remotePath')} to {m.get('localPath')}",
                       "state": "there" if (m.get("host", "").lower(), m.get("remotePath", "")) in have else "add"} for m in old["mappings"]]
        else:
            items = [{"name": PARTS[part], "state": "replace"}]
        out.append({"part": part, "title": PARTS[part], "items": items})
    return {"parts": out, "note": "Indexers are not copied: add the new app in Prowlarr (Settings, Apps), which keeps them in step."}


def apply(source, target, parts, secrets=None):
    """Copies the chosen parts. secrets: {client name: {field: value}} for hidden passwords and keys.
    Returns one line per part and a list of problems."""
    check(source, target)
    parts = set(parts) & set(PARTS)
    secrets = secrets or {}
    old, new = _read(source, parts), _read(target, parts | ({"tags"} if parts else set()))
    post = lambda path, body, query=None: _api(target, path, query, method="POST", body=body, timeout=30)
    lines, problems = [], []

    def remember(kind, label, err):
        problems.append(f"{kind} {label}".strip() + f": {err}")

    # Tags: every tag the copied parts use, matched by name.
    tag_ids = {t["label"].lower(): t["id"] for t in new.get("tags", [])}
    old_tags = {t["id"]: t["label"] for t in old.get("tags", [])}

    def tag(old_id):
        label = old_tags.get(old_id)
        if label is None:
            return None
        if label.lower() not in tag_ids:
            tag_ids[label.lower()] = post("/tag", {"label": label})["id"]
        return tag_ids[label.lower()]

    def tags(ids):
        return [t for t in (tag(i) for i in ids or []) if t is not None]

    if "tags" in parts:
        before = len(tag_ids)
        for t in old.get("tags", []):
            try:
                tag(t["id"])
            except ServiceError as e:
                remember("Tag", t["label"], e)
        lines.append(f"Tags: added {len(tag_ids) - before}")

    # Custom formats, by name.
    format_ids = {f["name"].lower(): f["id"] for f in new.get("formats", [])}
    if "formats" in parts:
        added = 0
        for f in old.get("formats", []):
            if f["name"].lower() in format_ids:
                continue
            try:
                format_ids[f["name"].lower()] = post("/customformat", {k: v for k, v in f.items() if k != "id"})["id"]
                added += 1
            except ServiceError as e:
                remember("Custom format", f["name"], e)
        lines.append(f"Custom formats: added {added}")

    # Quality profiles, by name, with custom format scores matched by format name.
    profile_ids = {p["name"].lower(): p["id"] for p in new.get("profiles", [])}
    if "profiles" in parts:
        added = 0
        all_formats = _api(target, "/customformat", timeout=30) or []
        old_format_names = {f["id"]: f["name"] for f in old.get("formats", [])}
        for p in old.get("profiles", []):
            if p["name"].lower() in profile_ids:
                continue
            scores = {old_format_names.get(fi.get("format"), fi.get("name", "")).lower(): fi.get("score", 0) for fi in p.get("formatItems") or []}
            body = {k: v for k, v in p.items() if k != "id"}
            body["formatItems"] = [{"format": f["id"], "name": f["name"], "score": scores.get(f["name"].lower(), 0)} for f in all_formats]
            try:
                profile_ids[p["name"].lower()] = post("/qualityprofile", body)["id"]
                added += 1
            except ServiceError as e:
                remember("Quality profile", p["name"], e)
        lines.append(f"Quality profiles: added {added}")

    # Root folders, by path. Lidarr's need a name and default profiles, matched by name.
    if "folders" in parts:
        added = 0
        have = {f["path"].rstrip("/").lower() for f in new.get("folders", [])}
        old_profiles = {p["id"]: p["name"].lower() for p in old.get("profiles", [])}
        old_meta = {p["id"]: p["name"].lower() for p in old.get("metadata", [])}
        new_meta = {p["name"].lower(): p["id"] for p in new.get("metadata", [])}
        for f in old.get("folders", []):
            if f["path"].rstrip("/").lower() in have:
                continue
            body = {"path": f["path"]}
            if target["type"] == "lidarr":
                body.update(name=f.get("name") or f["path"].rstrip("/").rsplit("/", 1)[-1],
                            defaultQualityProfileId=profile_ids.get(old_profiles.get(f.get("defaultQualityProfileId"), ""), next(iter(profile_ids.values()), 1)),
                            defaultMetadataProfileId=new_meta.get(old_meta.get(f.get("defaultMetadataProfileId"), ""), next(iter(new_meta.values()), 1)),
                            defaultTags=tags(f.get("defaultTags")), defaultMonitorOption=f.get("defaultMonitorOption", "all"),
                            defaultNewItemMonitorOption=f.get("defaultNewItemMonitorOption", "all"))
            try:
                post("/rootfolder", body)
                added += 1
            except ServiceError as e:
                remember("Root folder", f["path"], f"{e}. The folder must exist inside {target['name']}'s container")
        lines.append(f"Root folders: added {added}")

    # Download clients, by name. Hidden passwords come from secrets; without them the client is added switched off.
    if "clients" in parts:
        added = off = 0
        have = {c["name"].lower() for c in new.get("clients", [])}
        for c in old.get("clients", []):
            if c["name"].lower() in have:
                continue
            given = secrets.get(c["name"]) or {}
            body = {k: v for k, v in c.items() if k != "id"}
            missing = False
            fields = []
            for f in c.get("fields") or []:
                f = dict(f)
                if f.get("value") == HIDDEN:
                    value = str(given.get(f["name"], "")).strip()
                    if value:
                        f["value"] = value
                    else:
                        f["value"] = ""
                        missing = True
                fields.append(f)
            body["fields"] = fields
            body["tags"] = tags(c.get("tags"))
            if missing:
                body["enable"] = False
            try:
                post("/downloadclient", body, {"forceSave": "true"})
                added += 1
                off += missing
            except ServiceError as e:
                remember("Download client", c["name"], e)
        have = {(m.get("host", "").lower(), m.get("remotePath", "")) for m in new.get("mappings", [])}
        mapped = 0
        for m in old.get("mappings", []):
            if (m.get("host", "").lower(), m.get("remotePath", "")) in have:
                continue
            try:
                post("/remotepathmapping", {k: v for k, v in m.items() if k != "id"})
                mapped += 1
            except ServiceError as e:
                remember("Remote path mapping", m.get("remotePath", ""), e)
        lines.append(f"Download clients: added {added}" + (f", {off} inactive until you add the password" if off else "")
                     + f"; remote path mappings: added {mapped}")

    # Naming and media management: one set of settings each, which replaces the new app's.
    for part, path, title in (("naming", "/config/naming", "Naming"), ("media", "/config/mediamanagement", "Media management")):
        if part not in parts:
            continue
        current = new.get(part) or {}
        body = {**old.get(part, {}), "id": current.get("id", 1)}
        try:
            _api(target, f"{path}/{body['id']}", method="PUT", body=body, timeout=30)
            lines.append(f"{title}: copied")
        except ServiceError as e:
            remember(title, "", e)
    return {"lines": lines, "problems": problems}
