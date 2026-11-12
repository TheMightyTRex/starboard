"""Requests after moving into Reelix: keep Seerr, or use Reelix's own requests (DASH-192, 13 November 2026).

When Seerr runs beside Reelix, Settings, Your install asks which one people ask for films and series in:

- Reelix's own requests (recommended): Reelix replaces Seerr (stack.REPLACED_BY_REELIX), the move brings Seerr's
  users and requests across, Starboard's Requests page reads Reelix's (DASH-157), and it is one app fewer. Seerr's
  dashboard entry is made inactive at once, so Requests reads Reelix's; Seerr itself stops at the takeover.
- Keep Seerr: Seerr is taken over with the rest (takeover.plan keep_apps) and pointed at Reelix's Radarr and Sonarr
  addresses (http://reelix:7700/radarr and /sonarr) with Reelix's manager key, choosing the quality profile and folder
  Reelix offers, through Seerr's own settings API. Done once Seerr runs on Starboard's stack, where it can reach Reelix
  by name.

Either way the page gives a short message to send to the people who use Seerr. The choice is kept in
data/stack/requests-route.json.
"""
import json
import os
import time

from . import services, stack

FILE = "requests-route.json"
CHOICES = ("reelix", "seerr")
RECOMMENDED = "reelix"
REELIX_HOST, REELIX_PORT = "reelix", 7700


def read(data_dir):
    try:
        with open(os.path.join(stack.folder(data_dir), FILE), encoding="utf-8") as f:
            got = json.load(f)
        return got if isinstance(got, dict) and got.get("choice") in CHOICES else None
    except (OSError, ValueError, TypeError):  # TypeError: no data folder (a stand-in app in a test)
        return None


def save(data_dir, choice, applied=False, notes=()):
    if choice not in CHOICES:
        raise ValueError("Choose Reelix's own requests or Keep Seerr")
    os.makedirs(stack.folder(data_dir), mode=0o700, exist_ok=True)
    rec = {"choice": choice, "at": time.time(), "applied": bool(applied), "notes": list(notes)}
    with open(os.path.join(stack.folder(data_dir), FILE), "w", encoding="utf-8") as f:
        json.dump(rec, f)
    return rec


def seerr_entry(all_services):
    return next((s for s in all_services if s["type"] == "seerr" and s.get("api_key")), None)


def message(choice, reelix_address="", seerr_address=""):
    """The short message to send to the people who use Seerr."""
    if choice == "seerr":
        return ("Nothing changes for you: keep asking for films and series in Seerr"
                + (f" at {seerr_address}" if seerr_address else "") + ", with the same sign-in. "
                "Behind the scenes, Seerr now sends your requests to Reelix.")
    return ("Requests have moved from Seerr to Reelix. From now on, ask for films and series in Reelix"
            + (f" at {reelix_address}" if reelix_address else "") + ". Sign in with your Jellyfin user name and "
            "password, as you did in Seerr. Your earlier requests are there too.")


def _servers(seerr, kind, call):
    return call(seerr, f"/settings/{kind}") or []


def point_seerr_at_reelix(seerr, reelix_key, call=None):
    """Seerr's Radarr and Sonarr servers point at Reelix's compatible addresses. Returns notes for the page."""
    call = call or (lambda s, path, method="GET", body=None: services._api(dict(s, type="seerr"), path, method=method, body=body))
    notes = []
    for kind, prefix, label in (("radarr", "/radarr", "films"), ("sonarr", "/sonarr", "series")):
        conn = {"hostname": REELIX_HOST, "port": REELIX_PORT, "apiKey": reelix_key, "useSsl": False, "baseUrl": prefix}
        try:
            test = call(seerr, f"/settings/{kind}/test", "POST", conn) or {}
            profiles, folders = test.get("profiles") or [], test.get("rootFolders") or []
            have = _servers(seerr, kind, call)
            old = next((x for x in have if x.get("isDefault") and not x.get("is4k")), have[0] if have else None)
            profile = next((p for p in profiles if old and p.get("name") == old.get("activeProfileName")), profiles[0] if profiles else None)
            folder = next((f for f in folders if old and f.get("path") == old.get("activeDirectory")), folders[0] if folders else None)
            if not profile or not folder:
                notes.append(f"Seerr reaches Reelix's {label}, but Reelix has no quality profile or folder for them yet")
                continue
            body = {**(old or {}), **conn, "name": f"Reelix {label}", "activeProfileId": profile["id"],
                    "activeProfileName": profile.get("name", ""), "activeDirectory": folder["path"], "is4k": False,
                    "isDefault": True, "syncEnabled": False, "preventSearch": False}
            body.pop("id", None)
            if old:
                call(seerr, f"/settings/{kind}/{old['id']}", "PUT", body)
            else:
                body.setdefault("minimumAvailability", "released")
                if kind == "sonarr":
                    body.setdefault("activeAnimeProfileId", profile["id"])
                    body.setdefault("activeAnimeDirectory", folder["path"])
                    body.setdefault("enableSeasonFolders", True)
                call(seerr, f"/settings/{kind}", "POST", body)
            notes.append(f"Seerr sends {label} requests to Reelix")
        except (services.ServiceError, OSError, ValueError) as e:
            notes.append(f"Seerr does not send {label} requests to Reelix yet ({e}). Set it in Seerr, Settings, "
                         f"{'Radarr' if kind == 'radarr' else 'Sonarr'}: address {REELIX_HOST}, port {REELIX_PORT}, "
                         f"URL base {prefix}, with Reelix's API key")
    return notes


def apply(config, data_dir, choice):
    """Sets the chosen route up as far as it can now. Returns (applied, notes)."""
    svcs = config.data["services"]
    seerr = seerr_entry(svcs)
    if choice == "reelix":
        if seerr and seerr.get("enabled", True):
            config.upsert_service({**seerr, "enabled": False})
        on_stack = "seerr" in (stack.chosen_keys(data_dir) or [])
        notes = ["Starboard's Requests page now shows Reelix's requests"]
        notes.append("Seerr still runs on Starboard's apps: take it away in Change your install when nobody uses it"
                     if on_stack else "Seerr stops when Starboard takes over your apps")
        return True, notes
    if seerr and not seerr.get("enabled", True):
        config.upsert_service({**seerr, "enabled": True})
    if "seerr" not in (stack.chosen_keys(data_dir) or []):
        return False, ["Seerr is taken over with your other apps, then pointed at Reelix"]
    reelix = next((s for s in svcs if s.get("icon") == "reelix" and s["type"] == "link" and s.get("api_key")), None)
    if not seerr or not reelix:
        return False, ["Starboard needs Seerr and Reelix on your apps, each with its API key, to connect them"]
    return True, point_seerr_at_reelix(seerr, reelix["api_key"])
