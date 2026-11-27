"""Accounts inside the apps (DASH-589, single sign-on stage 3): make, pause, resume and remove one person's account in an app,
and the limits a Child gets, from the People page. Only Jellyfin and Audiobookshelf, with the admin key Starboard already holds
(ACCOUNT_APPS). Emby is built but off until it has been tried on a real Emby (the same rule as the password change). Kavita has no
admin route Starboard can use, so it is only recorded. Reelix people sign in through Jellyfin, Plex or OpenID Connect, so Starboard
makes no Reelix account (the fork would need documented create and disable routes for that).

Read on 27 November 2026 from the apps' own source and documentation, and tried only against stand-ins (tests/test_people_accounts.py):
  Jellyfin  POST /Users/New {"Name", "Password"}; the user's Policy is read with GET /Users and written back whole with
            POST /Users/{id}/Policy ("IsDisabled", "MaxParentalRating", "EnableAllFolders", "EnabledFolders",
            "EnableContentDeletion", "EnableContentDownloading"); DELETE /Users/{id}; ratings from GET /Localization/ParentalRatings.
  Audiobookshelf  POST /api/users {"username", "password", "type", "isActive", "permissions"}; PATCH /api/users/{id} {"isActive"};
            DELETE /api/users/{id}; libraries from GET /api/libraries ("accessAllLibraries", "librariesAccessible", "download").

Every action is idempotent: making an account that is there says so and only applies the limits again, pausing a paused one and
removing one that is gone change nothing. A password never appears in a message or a log. Nothing runs at rest.
"""
import json
import urllib.parse
import urllib.request

from . import listening, mediaserver, services
from .people import PeopleError

ACCOUNT_APPS = ("jellyfin", "audiobookshelf")  # the apps whose accounts Starboard makes, pauses and removes; add "emby" once tried on a real one
CHILD_RATING = "PG"  # the default highest rating a Child may watch in Jellyfin; the owner chooses another when making the account


def supports(service):
    return isinstance(service, dict) and service.get("type") in ACCOUNT_APPS and bool(service.get("api_key")) and bool(service.get("url"))


def _service(services_list, service_id):
    for s in services_list or []:
        if isinstance(s, dict) and s.get("id") == service_id:
            return s
    raise LookupError("No app with that id")


def _need(services_list, service_id):
    service = _service(services_list, service_id)
    if not supports(service):
        raise PeopleError(f"Starboard cannot change accounts in {service.get('name', 'that app')}. Change them in the app and Starboard only records them")
    return service


def _jf(service, method, path, body=None):
    adapter = mediaserver.ADAPTERS[service["type"]]()
    data = json.dumps(body).encode() if body is not None else None
    headers = {**adapter._headers(service), **({"Content-Type": "application/json"} if data else {})}
    req = urllib.request.Request(service["url"].rstrip("/") + adapter.prefix + path, data=data, method=method, headers=headers)
    return services._fetch(service, req, services.TIMEOUT)


def _abs_users(service):
    return (listening._abs(service, "/users") or {}).get("users") or []


def _find(service, username):
    """The account called `username` (case does not matter) as {id, name, paused, raw}, or None."""
    want = username.casefold()
    if service["type"] == "jellyfin":
        for u in _jf(service, "GET", "/Users") or []:
            if str(u.get("Name", "")).casefold() == want:
                return {"id": str(u["Id"]), "name": u["Name"], "paused": bool((u.get("Policy") or {}).get("IsDisabled")), "raw": u}
        return None
    for u in _abs_users(service):
        if str(u.get("username", "")).casefold() == want:
            return {"id": str(u["id"]), "name": u["username"], "paused": u.get("isActive") is False, "raw": u}
    return None


def libraries(services_list, service_id):
    """The libraries a Child could be limited to: [{id, name}]."""
    service = _need(services_list, service_id)
    if service["type"] == "jellyfin":
        return [{"id": str(r.get("ItemId") or ""), "name": str(r.get("Name") or "")} for r in _jf(service, "GET", "/Library/VirtualFolders") or [] if isinstance(r, dict) and r.get("ItemId")]
    return [{"id": str(r["id"]), "name": str(r.get("name") or "")} for r in (listening._abs(service, "/libraries") or {}).get("libraries") or []]


def ratings(services_list, service_id):
    """Jellyfin's parental ratings, lowest first: [{name, value}]. Empty for an app with none."""
    service = _need(services_list, service_id)
    if service["type"] != "jellyfin":
        return []
    rows = [{"name": str(r.get("Name")), "value": r.get("Value")} for r in _jf(service, "GET", "/Localization/ParentalRatings") or [] if isinstance(r, dict) and isinstance(r.get("Value"), int)]
    return sorted({r["name"]: r for r in rows}.values(), key=lambda r: (r["value"], r["name"]))


def _limit_policy(policy, limits, rating_value):
    """A Jellyfin policy with a Child's limits: no deleting or downloading, the highest rating, and only the chosen libraries."""
    out = dict(policy or {})
    out["EnableContentDeletion"] = False
    out["EnableContentDownloading"] = False
    if rating_value is not None:
        out["MaxParentalRating"] = rating_value
    if limits.get("libraries"):
        out.update(EnableAllFolders=False, EnabledFolders=list(limits["libraries"]))
    return out


def check(services_list, service_id, username):
    """Whether the account is there and paused: {exists, paused}. Reads only."""
    found = _find(_need(services_list, service_id), username)
    return {"exists": bool(found), "paused": bool(found and found["paused"])}


def ensure(services_list, service_id, username, password, child=False, limits=None):
    """Make the account if it is not there; for a Child, apply the limits either way. Returns the words to say."""
    service = _need(services_list, service_id)
    name, limits = service.get("name") or service_id, limits or {}
    found = _find(service, username)
    made = False
    if not found:
        if not password:
            raise PeopleError("Make a password first, then make the account")
        if service["type"] == "jellyfin":
            _jf(service, "POST", "/Users/New", {"Name": username, "Password": password})
        else:
            perms = {"download": not child, "update": False, "delete": False, "upload": False, "accessAllLibraries": True}
            if child and limits.get("libraries"):
                perms.update(accessAllLibraries=False)
            listening._abs(service, "/users", "POST", {"username": username, "password": password, "type": "user", "isActive": True,
                                                       "permissions": perms,
                                                       **({"librariesAccessible": list(limits["libraries"])} if child and limits.get("libraries") else {})})
        found = _find(service, username)
        made = True
    if child and found:
        _apply_child(service, found, limits)
    return f"Made the account in {name}" + (" with a child's limits" if child else "") if made else \
        f"The account is in {name} already" + (", and a child's limits were applied again" if child else "")


def _apply_child(service, found, limits):
    if service["type"] == "jellyfin":
        value = None
        want = limits.get("rating") or CHILD_RATING
        for r in _jf(service, "GET", "/Localization/ParentalRatings") or []:
            if isinstance(r, dict) and r.get("Name") == want and isinstance(r.get("Value"), int):
                value = r["Value"]
                break
        _jf(service, "POST", f"/Users/{urllib.parse.quote(found['id'], safe='')}/Policy", _limit_policy((found["raw"] or {}).get("Policy"), limits, value))
    else:
        perms = {"download": False, "update": False, "delete": False, "upload": False}
        body = {"permissions": perms}
        if limits.get("libraries"):
            perms["accessAllLibraries"] = False
            body["librariesAccessible"] = list(limits["libraries"])
        listening._abs(service, f"/users/{urllib.parse.quote(found['id'], safe='')}", "PATCH", body)


def set_paused(services_list, service_id, username, paused):
    """Pause (turn the account off, keeping everything it holds) or resume it. A missing account or one already in that state
    changes nothing and says so."""
    service = _need(services_list, service_id)
    name = service.get("name") or service_id
    found = _find(service, username)
    if not found:
        return f"{name} has no account called {username}, so nothing changed"
    if found["paused"] == paused:
        return f"The account in {name} is {'paused' if paused else 'active'} already"
    uid = urllib.parse.quote(found["id"], safe="")
    if service["type"] == "jellyfin":
        policy = dict((found["raw"] or {}).get("Policy") or {})
        policy["IsDisabled"] = paused
        _jf(service, "POST", f"/Users/{uid}/Policy", policy)
    else:
        listening._abs(service, f"/users/{uid}", "PATCH", {"isActive": not paused})
    return f"{'Paused' if paused else 'Resumed'} the account in {name}"


def remove(services_list, service_id, username):
    """Delete the account in the app (the caller has checked the Starboard password and asked plainly). Gone already is fine."""
    service = _need(services_list, service_id)
    name = service.get("name") or service_id
    found = _find(service, username)
    if not found:
        return f"{name} has no account called {username}, so nothing changed"
    uid = urllib.parse.quote(found["id"], safe="")
    if service["type"] == "jellyfin":
        _jf(service, "DELETE", f"/Users/{uid}")
    else:
        listening._abs(service, f"/users/{uid}", "DELETE")
    return f"Removed the account in {name}"
