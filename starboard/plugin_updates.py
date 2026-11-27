"""Updates for Starboard's plug-ins (owner, 26 November 2026): the list Settings, Plug-ins, Manage and Updates, Plug-ins
both show, from what Starboard already knows (nothing is fetched here). The rows are update_runs.plugin_targets, the
batch is update_batch (its copy first, health check and way back), the setting is auto_updates' "plugins" part and the
history is the plug-in runs in update_runs.recent. Only the words about new permissions are worked out here.
"""
import os

from . import auto_updates, plugin_life, plugins, update_batch, update_runs
from . import plugins_admin as pa


def new_permissions(app, pid, known):
    """What the new version asks for that the installed one does not, from the catalogue's own list for it: [{permission,
    words, risk}]. The update re-checks this against the new version's manifest before anything changes."""
    old = pa._read(os.path.join(pa.folder(app.data_dir, pid), "manifest.json"), {}) or {}
    new = sorted(set(known.get("permissions") or []) - set(old.get("permissions") or []))
    return [{"permission": p, "words": plugins.PERMISSIONS[p][0], "risk": plugins.PERMISSIONS[p][1]} for p in new if p in plugins.PERMISSIONS]


def waiting_words(app, pid, current, known):
    """For a plug-in with a newer version: {new_permissions, held, released}. held is why it waits for the owner (new
    permissions, or a big change), or ""."""
    perms = new_permissions(app, pid, known)
    held = ""
    if perms:
        held = "Read what it asks for, then update it on its own page"
    elif update_batch.big_change(current, known.get("version")):
        held = f"Version {known.get('version')} is a big change. Read what is new, then update it on its own page"
    return {"new_permissions": perms, "held": held, "released": known.get("released", "")}


def listing(app):
    """{items, counts, read, auto, recent}. Each item is a plug-in's row from update_runs.plugin_targets, with for one
    that has an update: new_permissions, held (why it waits for you, or "") and released."""
    known = plugin_life.updates_known(app.data_dir)
    items = []
    for t in update_runs.plugin_targets(app):
        pid = t["id"].split(":", 1)[1]
        k = known.get(pid)
        if k and "held" not in t:
            t = {**t, **waiting_words(app, pid, t.get("current"), k)}
        items.append(t)
    items.sort(key=lambda t: (not t["update_available"], t["name"].lower()))
    auto = next(p for p in auto_updates.summary(app)["parts"] if p["id"] == "plugins")
    runs = [update_runs.public(r) for r in update_runs.recent(app) if r.get("kind") == "plugin"]
    return {"items": items, "counts": update_runs.counts(items), "read": pa.last_read(), "auto": auto,
            "hours_words": auto_updates.hours_words(app.config.data), "recent": runs[:10],
            "running": next((r for r in runs if r["state"] == "running"), None)}
