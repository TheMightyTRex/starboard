"""Change a person's password inside an app (DASH-589, single sign-on stage 1): "Also change it in the app".

Only where Starboard already holds an admin key for the app and the change is switched on (VERIFIED below): Jellyfin and
Audiobookshelf today. Emby is built but off until it has been tried on a real Emby. It finds the person's account by its account name and changes its password. It makes no account,
removes none and changes nothing else (stage 3 does those). Any other app is changed by hand, and Starboard only records it.

Read on 27 November 2026 from the apps' own source and documentation, and tried only against stand-ins (tests/test_people_apps.py):
  Jellyfin  POST /Users/Password?userId=ID  {"NewPw", "ResetPassword": false}. Jellyfin.Api/Controllers/UserController.cs asks for
            CurrentPw only when the caller is not an administrator, or is changing their own password. An administrator's API key
            changing another person's password needs none. That the key counts as an administrator is not shown in that file.
  Emby      POST /emby/Users/ID/Password    {"CurrentPw": "", "NewPw", "ResetPassword": false}. dev.emby.media lists the route but
            not its body; the fields are from Emby forum posts, some of which report a key being accepted with no change made. So
            check the account after the first change.
  Audiobookshelf  PATCH /api/users/ID       {"password"}. server/controllers/UserController.js update(), which checks no length.
A refusal or an unreachable app is said in words and changes nothing. The password never appears in a message, a log or an
address (it travels in the body only; the log line keeps no query and no body).
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from . import listening, mediaserver, services
from .people import PeopleError

APPS = ("jellyfin", "emby", "audiobookshelf")  # the apps this module can change a password in
# The apps whose change is offered and accepted. Emby is built and tested against a stand-in but has not been tried on a real Emby, and
# its documentation does not give the body, so it is left out: add "emby" here to turn it on (owner's decision, 27 November 2026).
VERIFIED = ("jellyfin", "audiobookshelf")


def supports(service):
    return isinstance(service, dict) and service.get("type") in APPS and service.get("type") in VERIFIED and bool(service.get("api_key")) and bool(service.get("url"))


def _service(services_list, service_id):
    for s in services_list or []:
        if isinstance(s, dict) and s.get("id") == service_id:
            return s
    raise LookupError("No app with that id")


def _match(rows, username):
    found = [r for r in rows if str(r.get("name", "")).casefold() == username.casefold()]
    return found[0] if len(found) == 1 else None


def _send(adapter, service, method, path, body):
    req = urllib.request.Request(service["url"].rstrip("/") + adapter.prefix + path, data=json.dumps(body).encode(), method=method,
                                 headers={**adapter._headers(service), "Content-Type": "application/json"})
    return services._fetch(service, req, services.TIMEOUT)


def change_password(services_list, service_id, username, password):
    """Change the password of the account called `username` in the app. Raises PeopleError (no such account), LookupError
    or services.ServiceError (the app refused or did not answer); each says it in words, never with the password."""
    service = _service(services_list, service_id)
    if not supports(service):
        raise PeopleError(f"Starboard cannot change passwords in {service.get('name', 'that app')}. Change it in the app, then mark it as set")
    name = service.get("name") or service_id
    if service["type"] == "audiobookshelf":
        rows = [{"id": u.get("id"), "name": u.get("username")} for u in listening.abs_users(service)]
        user = _match(rows, username)
        if not user:
            raise PeopleError(f"{name} has no account called {username}. Make the account in {name} first")
        listening._abs(service, f"/users/{urllib.parse.quote(str(user['id']), safe='')}", "PATCH", {"password": password})
        return f"Changed it in {name}"
    adapter = mediaserver.ADAPTERS[service["type"]]()
    user = _match(adapter.users(services_list), username)
    if not user:
        raise PeopleError(f"{name} has no account called {username}. Make the account in {name} first")
    uid = urllib.parse.quote(str(user["id"]), safe="")
    if service["type"] == "jellyfin":
        _send(adapter, service, "POST", f"/Users/Password?userId={uid}", {"NewPw": password, "ResetPassword": False})
    else:
        _send(adapter, service, "POST", f"/Users/{uid}/Password", {"CurrentPw": "", "NewPw": password, "ResetPassword": False})
    return f"Changed it in {name}"
