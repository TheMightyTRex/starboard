"""Live TV moves into a plug-in (DASH-285, owner, 10 November 2026).

Live TV is now the built-in Live TV plug-in (plugins/livetv): its container builds the channel lists and guides and
adds them to Jellyfin. Starboard keeps serving the logos and Pluto TV links at /iptv/ from the same Live TV folder,
so Jellyfin's tuners and guides stay as they are.

The move happens by itself, once, when Starboard starts: if Live TV was on (extras.livetv), Starboard can run
containers and the installer gave a Live TV folder, it adds the plug-in with the same settings (white logos, the
address Jellyfin uses, the folder as Jellyfin sees it), activates it, and switches its own job off. When any of that
is missing (no Docker access, Starboard not in Docker), Live TV keeps running inside Starboard as before, so nobody
loses it; Settings, Plug-ins offers the plug-in when it can run.
"""
import os

PID = "livetv"


def plugin_state(data_dir):
    """"enabled", "installed", "disabled", "failed" or None when the plug-in is not added."""
    from . import plugins_admin
    return next((p["state"] for p in plugins_admin.listing(data_dir) if p["id"] == PID), None)


_active = {}


def plugin_active(data_dir):
    """Asked for every logo Jellyfin loads, so kept for 30 seconds."""
    import time
    hit = _active.get(data_dir)
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    on = plugin_state(data_dir) == "enabled"
    _active[data_dir] = (time.time(), on)
    return on


def can_run(data_dir):
    """Why the plug-in cannot run here, or "" when it can."""
    from . import containers, plugins_admin, stack
    if not containers.available():
        return "Starboard has no access to Docker here"
    if not os.environ.get("STARBOARD_LIVETV_PATH"):
        return "The installer gave Starboard no Live TV folder (./install.sh asks)"
    if not stack.host_folder(data_dir):
        return "Starboard cannot find its own folder on this computer"
    if not plugins_admin.own_image():
        return "Starboard cannot find its own image"
    return ""


def settings_from(cfg, self_url):
    """The plug-in's settings from Starboard's own Live TV settings, so nothing changes for Jellyfin."""
    from . import livetv_jellyfin
    extras = cfg.data["extras"]
    return {"white_logos": bool(extras.get("white_logos", True)),
            "address": (extras.get("livetv_address") or self_url or "").rstrip("/"),
            # The folder Jellyfin's own tuners use first, so nothing is added twice; else worked out, as before.
            "jellyfin_folder": livetv_jellyfin.folder_from_jellyfin(cfg.data["services"])
            or livetv_jellyfin.jellyfin_folder(extras, cfg.data_dir) or ""}


def add(cfg, data_dir, media_dir, self_url, helper=None):
    """Adds and activates the built-in Live TV plug-in with today's settings. Returns its listing entry."""
    from . import plugins_admin
    manifest = plugins_admin.builtins()[PID]
    if plugin_state(data_dir) is None:
        plugins_admin.install(data_dir, manifest, media_dir, builtin=True, defaults=settings_from(cfg, self_url))
    plugins_admin.enable(data_dir, PID, helper=helper, services=cfg.data["services"])
    return next(p for p in plugins_admin.listing(data_dir) if p["id"] == PID)


def move(cfg, data_dir, media_dir, self_url, helper=None, log=lambda *a: None):
    """The one-time move at start. Returns what happened, in words, or "" when there was nothing to do."""
    extras = cfg.data["extras"]
    if not extras.get("livetv") or plugin_state(data_dir) is not None:
        return ""
    why = can_run(data_dir)
    if why:
        return ""  # Live TV stays in Starboard, as before
    try:
        add(cfg, data_dir, media_dir, self_url, helper)
    except Exception as e:  # anything at all: Live TV carries on inside Starboard, and the reason is logged
        log(f"Live TV stays in Starboard for now: {e}")
        return ""
    with cfg.lock:
        cfg.data["extras"]["livetv"] = False  # Starboard's own job stops; the plug-in runs it now
        cfg.save()
    return "Live TV is now a plug-in, with the same settings. Its channels and guides in Jellyfin are unchanged"
