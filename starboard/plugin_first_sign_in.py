"""A first sign-in Starboard made for an app plug-in, shown once on the plug-in's page (API 1.20, DASH-590).

An app such as Calibre-Web starts with a password everyone knows. A plug-in can ask Starboard to make a long random one
instead: the manifest names it in `first_sign_in`, and the app's own start-up sets it before the app first starts.

    "first_sign_in": {"user": "admin", "secret": "admin_password", "ready_file": "app/starboard-first-sign-in.done"}

- `secret` is a `{secret:name}` the plug-in uses in its container's `env`. Starboard makes it once and keeps it
  owner-only in `data/plugins/<id>/secrets.json`, as for every secret. It is never put in a log or a listing.
- `ready_file` is a file the app's start-up writes in its own data folder (a path inside `data/plugins/<id>/data/`)
  once it has set the password, and makes that folder 711 (a container's data folder is 700 for the user it runs as, and
  Starboard is another user, which could not otherwise check the file is there). Until it is there, Starboard offers
  nothing to show, so a plug-in that was already set up before it had this is never shown a password that was not set.
- The page offers **Show the password**; it asks for the Starboard password, shows the password once and keeps only
  the date it was shown. The password is kept as it was, so removing the plug-in and adding it again, with its folder
  moved to the holding folder, makes a new one.
"""
import datetime as dt
import os
import re

READY = re.compile(r"^[a-z0-9][a-z0-9-]{0,20}/[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
USER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@ -]{0,39}$")
SECRET = re.compile(r"^[a-z][a-z0-9_]{0,29}$")
KEYS = {"user", "secret", "ready_file"}


def problems(spec, secret_names, container_names):
    """What is wrong with a manifest's first_sign_in, in words."""
    if spec is None:
        return []
    if not isinstance(spec, dict) or set(spec) - KEYS or KEYS - set(spec):
        return ["first_sign_in must be an object with user, secret and ready_file (API 1.20)"]
    out = []
    if not (isinstance(spec["user"], str) and USER.match(spec["user"])):
        out.append("first_sign_in.user must be the sign-in name, up to 40 letters, numbers and . _ @ -")
    if not (isinstance(spec["secret"], str) and SECRET.match(spec["secret"])) or spec["secret"] not in secret_names:
        out.append("first_sign_in.secret must name a {secret:name} the plug-in uses in a container's env or files")
    ready = spec["ready_file"]
    if not (isinstance(ready, str) and READY.match(ready)) or ".." in str(ready) or ready.split("/")[0] not in container_names:
        out.append("first_sign_in.ready_file must be a file in one container's data folder, such as app/first-sign-in.done")
    return out


def _state(where):
    from . import plugins_admin as pa
    return pa._read(os.path.join(where, "state.json"), {}) or {}


def info(data_dir, pid, manifest):
    """What the plug-in's page needs: None without first_sign_in, else {user, state, shown_at}. State is "waiting"
    (the app has not set the password), "ready" (it is set and has not been shown) or "shown". Nothing secret."""
    from . import plugins_admin as pa
    spec = (manifest or {}).get("first_sign_in")
    if not isinstance(spec, dict):
        return None
    where = pa.folder(data_dir, pid)
    shown = _state(where).get("first_sign_in_shown")
    if shown:
        return {"user": spec["user"], "state": "shown", "shown_at": shown}
    ready = os.path.join(where, "data", *spec["ready_file"].split("/"))
    return {"user": spec["user"], "state": "ready" if os.path.isfile(ready) else "waiting", "shown_at": None}


def reveal(data_dir, pid):
    """The password, once. Marks it shown before it is returned, so a second call is refused. LookupError when there is
    nothing to show; the caller has checked the Starboard password."""
    from . import plugins_admin as pa
    where = pa.folder(data_dir, pid)
    manifest = pa._read(os.path.join(where, "manifest.json"), {}) or {}
    now = info(data_dir, pid, manifest)
    if now is None:
        raise LookupError("This plug-in has no first sign-in")
    if now["state"] == "shown":
        raise LookupError("The first sign-in was shown already. Starboard shows it once")
    if now["state"] != "ready":
        raise LookupError("There is no first sign-in to show yet. It is made when the app first starts")
    password = str((pa._read(os.path.join(where, "secrets.json"), {}) or {}).get(manifest["first_sign_in"]["secret"], ""))
    if not password:
        raise LookupError("Starboard has no password kept for this plug-in")
    path = os.path.join(where, "state.json")
    st = _state(where)
    st["first_sign_in_shown"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pa._write(path, st)
    return {"user": manifest["first_sign_in"]["user"], "password": password}
