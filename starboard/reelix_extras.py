"""Reelix's smaller settings in Settings, Reelix (DASH-204): tags, path mappings and the site list's updates.

- Tags: Reelix's labels for sites, download apps and the rest (GET and POST /tags, DELETE /tags/{id}). Reelix has no
  rename, so a tag is added or removed.
- Path mappings: when a download app reports a folder Reelix cannot see under the same name, such as an app on
  another computer (GET, POST /remotepathmappings, PUT and DELETE /remotepathmappings/{id}).
- The site list: the list of sites Reelix can search, which it fetches from a public list (GET and PUT
  /settings/definitions, GET /indexers/definitions/status, POST /indexers/definitions/sync).

All of these are behind Reelix's admin password, except reading and adding tags, so every call runs inside
reelix_admin.Visit. Only Reelix's documented HTTP API is used. 13 November 2026.
"""
import re

EVERY = (6, 12, 24, 72, 168)  # hours between automatic checks of the site list: the choices offered
EVERY_WORDS = {6: "Every 6 hours", 12: "Every 12 hours", 24: "Once a day", 72: "Every 3 days", 168: "Once a week"}
_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,39}$")
_HOST = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,252})$")


# Tags ------------------------------------------------------------------------------------------------------------

def tags(reelix):
    _, found = reelix.call("GET", "/tags")
    items = sorted(({"id": t.get("id"), "label": str(t.get("label") or "")} for t in found or [] if isinstance(t, dict)),
                   key=lambda t: t["label"].lower())
    return {"tags": items}


def add_tag(reelix, label):
    label = " ".join(str(label or "").split())
    if not _LABEL.match(label):
        raise ValueError("A tag is 1 to 40 letters, numbers, spaces, dots, dashes or underscores, starting with a letter or number")
    have = {t["label"].lower() for t in tags(reelix)["tags"]}
    if label.lower() in have:
        raise ValueError(f"Reelix has a tag called {label} already")
    reelix.call("POST", "/tags", {"label": label}, ok=(200, 201))
    return {**tags(reelix), "done": f"Tag {label} added"}


def remove_tag(reelix, tag_id):
    try:
        tag_id = int(tag_id)
    except (TypeError, ValueError):
        raise ValueError("Choose a tag from the list") from None
    label = next((t["label"] for t in tags(reelix)["tags"] if t["id"] == tag_id), None)
    if label is None:
        raise ValueError("Reelix no longer has that tag. Load the page again")
    reelix.call("DELETE", f"/tags/{tag_id}", ok=(200, 204))
    return {**tags(reelix), "done": f"Tag {label} removed"}


# Path mappings ---------------------------------------------------------------------------------------------------

def _clean_path(text, what):
    text = str(text or "").strip()
    if not text.startswith("/") and not re.match(r"^[A-Za-z]:[\\/]", text):
        raise ValueError(f"{what} starts with / (or a drive letter, such as D:\\, for an app on Windows)")
    if len(text) > 500 or "\x00" in text or "/../" in text + "/":
        raise ValueError(f"{what} is not a folder Starboard can use")
    windows = not text.startswith("/")
    return text.rstrip("/\\") + ("\\" if windows else "/")


def mappings(reelix):
    _, found = reelix.call("GET", "/remotepathmappings")
    _, clients = reelix.call("GET", "/downloadclients")
    hosts = sorted({str((c.get("settings") or {}).get("host") or "") for c in clients or [] if isinstance(c, dict)} - {""})
    items = [{"id": m.get("id"), "host": m.get("host") or "", "remote": m.get("remote_path") or "", "local": m.get("local_path") or ""}
             for m in found or [] if isinstance(m, dict)]
    return {"mappings": items, "hosts": hosts}


def save_mapping(reelix, body):
    host = str(body.get("host") or "").strip()
    if not _HOST.match(host):
        raise ValueError("Choose the download app's host, as Reelix's Download apps list it")
    remote = _clean_path(body.get("remote"), "The folder the download app reports")
    local = _clean_path(body.get("local"), "The folder Reelix sees")
    if not local.startswith("/"):
        raise ValueError("The folder Reelix sees starts with /")
    payload = {"host": host, "remote_path": remote, "local_path": local}
    if body.get("id"):
        reelix.call("PUT", f"/remotepathmappings/{int(body['id'])}", payload)
        done = f"Path mapping for {host} saved"
    else:
        reelix.call("POST", "/remotepathmappings", payload, ok=(200, 201))
        done = f"Path mapping for {host} added"
    return {**mappings(reelix), "done": done}


def remove_mapping(reelix, mapping_id):
    try:
        mapping_id = int(mapping_id)
    except (TypeError, ValueError):
        raise ValueError("Choose a path mapping from the list") from None
    reelix.call("DELETE", f"/remotepathmappings/{mapping_id}", ok=(200, 204))
    return {**mappings(reelix), "done": "Path mapping removed"}


# The site list ---------------------------------------------------------------------------------------------------

def site_list(reelix):
    """What the Site list section shows: automatic updates on or off, how often, and how the last update went."""
    _, s = reelix.call("GET", "/settings/definitions")
    _, st = reelix.call("GET", "/indexers/definitions/status")
    s, st = s or {}, st or {}
    hours = int(s.get("auto_update_hours") or st.get("auto_update_hours") or 24)
    failed = [{"id": f.get("id"), "error": f.get("error") or ""} for f in st.get("failed") or [] if isinstance(f, dict)]
    error = s.get("last_error") or st.get("last_error") or ""
    state = "updating" if st.get("syncing") else "failed" if error else "never" if not (st.get("last_sync") or s.get("last_sync")) else "ok"
    choices = sorted(set(EVERY) | {hours})
    return {"on": bool(s.get("enabled", True)), "every": hours,
            "choices": [{"value": h, "label": EVERY_WORDS.get(h, f"Every {h} hours")} for h in choices],
            "state": state, "syncing": bool(st.get("syncing")), "error": error,
            "last_sync": st.get("last_sync") or s.get("last_sync"), "last_check": st.get("last_check") or s.get("last_check"),
            "loaded": st.get("loaded"), "custom": st.get("custom_count") or 0, "failed": failed[:50], "failed_count": len(failed),
            "source": s.get("source_url") or st.get("source_url") or ""}


def save_site_list(reelix, on, every):
    """Automatic updates and how often. Reelix keeps its other fields (source, version) as they are."""
    try:
        every = int(every)
    except (TypeError, ValueError):
        raise ValueError("Choose how often from the list") from None
    if not 1 <= every <= 720:
        raise ValueError("Choose how often from the list")
    _, s = reelix.call("GET", "/settings/definitions")
    keep = {k: v for k, v in (s or {}).items() if k in ("source_url", "schema_version")}
    reelix.call("PUT", "/settings/definitions", {**keep, "enabled": bool(on), "auto_update_hours": every})
    words = EVERY_WORDS.get(every, f"every {every} hours").lower()
    return {**site_list(reelix), "done": f"The site list updates {words}" if on else "Automatic updates of the site list deactivated"}


def sync_site_list(reelix):
    reelix.call("POST", "/indexers/definitions/sync", ok=(200, 202))
    out = site_list(reelix)
    out["syncing"], out["state"] = True, "updating"
    return {**out, "done": "Reelix is updating the site list"}


ACTIONS = {
    "tags": lambda r, b: tags(r), "tag-add": lambda r, b: add_tag(r, b.get("label")), "tag-remove": lambda r, b: remove_tag(r, b.get("id")),
    "mappings": lambda r, b: mappings(r), "mapping-save": lambda r, b: save_mapping(r, b), "mapping-remove": lambda r, b: remove_mapping(r, b.get("id")),
    "site-list": lambda r, b: site_list(r), "site-list-save": lambda r, b: save_site_list(r, b.get("on"), b.get("every")),
    "site-list-sync": lambda r, b: sync_site_list(r),
}


def act(reelix, action, body):
    if action not in ACTIONS:
        raise ValueError("Not something Starboard does")
    return ACTIONS[action](reelix, body if isinstance(body, dict) else {})
