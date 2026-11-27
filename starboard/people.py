"""People (DASH-589, single sign-on stage 1): the household members, children and guests who use your apps.

Starboard stays single owner: the one Starboard password and the one dashboard are yours. A person here cannot sign in to
Starboard. Starboard keeps the list so that each person has their own account in each app, and a long, unique password for
each one, instead of one shared password that everyone knows (design/single-sign-on.md, section 7, stage 1).

What it keeps, in `data/people.json` (owner-only, 0600): for each person an id, a name, an optional email address, a role,
a state (active, paused or removed) and, for each app, an account name and, once made, the password Starboard made for it.
The file is not part of a Settings backup (those hold settings only). A full backup keeps it, as it keeps the plug-ins' own
keys. A password is never put in a log, the audit log, an address or an error message, and is shown only after the owner
enters the Starboard password again.

Starboard does not yet make the account inside the app (stage 3). Until then the owner makes it by hand, and this page
holds the password to give it and says honestly whether the owner has said it was set. Nothing here calls an app.

Nothing runs at rest: the file is read when the People page is opened or a person is changed, and never between.
"""
import datetime as dt
import json
import os
import re
import secrets
import threading

FILE = "people.json"
MAX_PEOPLE = 50  # the design's budget: a file under 100 KB for 50 people
NAME_MAX = 40
ROLES = {
    "household": ("Household member", "Uses the apps, and can ask for things where an app allows it."),
    "child": ("Child", "Uses the apps. Each app sets its own limits, and not every app can limit a child."),
    "guest": ("Guest", "A few apps for a short time. Remove them when the visit ends."),
}
STATES = ("active", "paused", "removed")
FORGET_AFTER_DAYS = 30  # a removed person's record waits this long before the owner may forget it (design section 4)
# Letters and numbers with no characters that can be mistaken for each other (no 0, O, 1, l, I): typed on a phone or a television remote without a mistake.
ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PASSWORD_LENGTH = 24  # about 139 bits; the design asks for 20 or more
# The apps people sign in to, found by the name or kind of each service. Download apps and tools such as Jellystat and
# Wizarr are the owner's, never given to a person (design section 3).
PEOPLE_APPS = ("jellyfin", "plex", "emby", "audiobookshelf", "kavita", "komga", "calibre-web", "navidrome", "immich",
               "seerr", "jellyseerr", "overseerr", "ombi")

_lock = threading.Lock()
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s.]{2,}$")
USERNAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+ -]{0,59}$")
PERSON_ID = re.compile(r"^p-[0-9a-f]{8}$")
APP_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


class PeopleError(ValueError):
    """Something wrong with the request, said in words the owner can act on."""


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"version": 1, "people": []}
    if not isinstance(data, dict) or not isinstance(data.get("people"), list):
        return {"version": 1, "people": []}
    return data


def _write(data_dir, data):
    path = _path(data_dir)
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def make_password():
    return "".join(secrets.choice(ALPHABET) for _ in range(PASSWORD_LENGTH))


def apps_from(services):
    """[{id, name, address}] of the owner's apps a person can have an account in, from Starboard's list of apps."""
    out = []
    for s in services or []:
        if not isinstance(s, dict) or s.get("enabled") is False:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", str(s.get("name", "")).lower()).strip("-")
        if s.get("type") in PEOPLE_APPS or slug in PEOPLE_APPS or any(slug.startswith(p + "-") for p in PEOPLE_APPS):
            out.append({"id": str(s["id"]), "name": str(s.get("name") or s["id"]), "address": str(s.get("link") or s.get("url") or "")})
    return out


def _clean_name(name):
    name = re.sub(r"\s+", " ", str(name or "")).strip()
    if not name:
        raise PeopleError("Enter a name")
    if len(name) > NAME_MAX:
        raise PeopleError(f"Use {NAME_MAX} letters or fewer for the name")
    if any(ord(c) < 32 or ord(c) == 127 for c in name) or "<" in name or ">" in name:
        raise PeopleError("The name has a character Starboard cannot keep. Use letters, numbers and spaces")
    return name


def _clean_email(email):
    email = str(email or "").strip()
    if not email:
        return ""
    if len(email) > 320 or not EMAIL.match(email):
        raise PeopleError("That email address does not look right. Leave it empty, or write it as name@example.com")
    return email


def _clean_role(role):
    if role not in ROLES:
        raise PeopleError("Choose Household member, Child or Guest")
    return role


def _find(data, person_id):
    if not PERSON_ID.match(str(person_id or "")):
        raise LookupError("No person with that id")
    for p in data["people"]:
        if p.get("id") == person_id:
            return p
    raise LookupError("No person with that id")


def _same_name(data, name, except_id=""):
    folded = name.casefold()
    return any(p["name"].casefold() == folded and p["id"] != except_id and p.get("state") != "removed" for p in data["people"])


def _days_since(stamp):
    try:
        then = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return 0
    return max(0, (dt.datetime.now(dt.timezone.utc) - then).days)


def public(person, apps):
    """A person as the page sees them: never a password, only whether one is kept."""
    names = {a["id"]: a["name"] for a in apps}
    accounts = []
    for app_id, acct in sorted((person.get("accounts") or {}).items(), key=lambda kv: names.get(kv[0], kv[0]).casefold()):
        state = "none"
        if acct.get("password"):
            state = "in-use" if acct.get("set_at") else "made"
        accounts.append({"app": app_id, "app_name": names.get(app_id, ""), "app_present": app_id in names,
                         "username": acct.get("username", ""), "state": state, "made_at": acct.get("made_at", ""),
                         "set_at": acct.get("set_at", "")})
    removed_days = _days_since(person.get("removed_at")) if person.get("state") == "removed" else 0
    return {"id": person["id"], "name": person["name"], "email": person.get("email", ""), "role": person["role"],
            "role_name": ROLES[person["role"]][0], "state": person.get("state", "active"), "created": person.get("created", ""),
            "paused_at": person.get("paused_at", ""), "removed_at": person.get("removed_at", ""),
            "can_forget": person.get("state") == "removed" and removed_days >= FORGET_AFTER_DAYS,
            "forget_in_days": max(0, FORGET_AFTER_DAYS - removed_days) if person.get("state") == "removed" else 0,
            "accounts": accounts}


def listing(data_dir, services):
    apps = apps_from(services)
    with _lock:
        data = _read(data_dir)
    people = [public(p, apps) for p in data["people"] if p.get("role") in ROLES]
    people.sort(key=lambda p: (STATES.index(p["state"]) if p["state"] in STATES else 0, p["name"].casefold()))
    return {"people": people, "apps": apps, "roles": [{"id": k, "name": v[0], "about": v[1]} for k, v in ROLES.items()],
            "limit": MAX_PEOPLE, "name_max": NAME_MAX, "forget_after_days": FORGET_AFTER_DAYS}


def add(data_dir, name, email, role):
    name, email, role = _clean_name(name), _clean_email(email), _clean_role(role)
    with _lock:
        data = _read(data_dir)
        if sum(1 for p in data["people"] if p.get("state") != "removed") >= MAX_PEOPLE:
            raise PeopleError(f"Starboard keeps up to {MAX_PEOPLE} people. Remove one first")
        if _same_name(data, name):
            raise PeopleError(f"There is a person called {name} already. Use a different name, such as a surname's first letter")
        person = {"id": "p-" + secrets.token_hex(4), "name": name, "email": email, "role": role, "state": "active",
                  "created": _now(), "accounts": {}}
        data["people"].append(person)
        _write(data_dir, data)
        return person


def update(data_dir, person_id, name, email, role):
    name, email, role = _clean_name(name), _clean_email(email), _clean_role(role)
    with _lock:
        data = _read(data_dir)
        p = _find(data, person_id)
        if p.get("state") == "removed":
            raise PeopleError("Put this person back before changing them")
        if _same_name(data, name, p["id"]):
            raise PeopleError(f"There is a person called {name} already. Use a different name")
        p.update({"name": name, "email": email, "role": role})
        _write(data_dir, data)
        return p


def set_state(data_dir, person_id, action):
    """pause, resume, remove or restore. Nothing is deleted: a removed person's record waits for 30 days."""
    moves = {"pause": ("active", "paused"), "resume": ("paused", "active"), "remove": (("active", "paused"), "removed"),
             "restore": ("removed", "active")}
    if action not in moves:
        raise PeopleError("Choose pause, resume, remove or restore")
    before, after = moves[action]
    before = (before,) if isinstance(before, str) else before
    with _lock:
        data = _read(data_dir)
        p = _find(data, person_id)
        if p.get("state", "active") not in before:
            raise PeopleError(f"{p['name']} is {p.get('state', 'active')}, so that is not possible")
        if action == "restore" and _same_name(data, p["name"], p["id"]):
            raise PeopleError(f"There is another person called {p['name']} now. Change one of the names first")
        p["state"] = after
        p.pop("paused_at", None)
        p.pop("removed_at", None)
        if after == "paused":
            p["paused_at"] = _now()
        if after == "removed":
            p["removed_at"] = _now()
        _write(data_dir, data)
        return p


def forget(data_dir, person_id):
    """The record and every kept password go for good. Only for a person removed for 30 days; the caller has checked the
    Starboard password. Starboard never deletes what a person made inside an app."""
    with _lock:
        data = _read(data_dir)
        p = _find(data, person_id)
        if p.get("state") != "removed":
            raise PeopleError("Remove the person first")
        if _days_since(p.get("removed_at")) < FORGET_AFTER_DAYS:
            raise PeopleError(f"A removed person's record is kept for {FORGET_AFTER_DAYS} days first, in case it was a mistake")
        data["people"] = [x for x in data["people"] if x["id"] != person_id]
        _write(data_dir, data)
        return p


def _account(data, person_id, app_id, apps, need=False):
    p = _find(data, person_id)
    if not APP_ID.match(str(app_id or "")):
        raise LookupError("No app with that id")
    if p.get("state") == "removed":
        raise PeopleError("Put this person back before changing their accounts")
    if app_id not in {a["id"] for a in apps} and app_id not in (p.get("accounts") or {}):
        raise LookupError("No app with that id")
    acct = (p.setdefault("accounts", {})).get(app_id)
    if need and not acct:
        raise LookupError("There is no account for that app yet")
    return p, acct


def _clean_username(username, fallback):
    username = str(username or "").strip() or fallback
    if not USERNAME.match(username):
        raise PeopleError("The account name can use letters, numbers, spaces and . _ @ + - only, up to 60 characters")
    return username


def save_account(data_dir, services, person_id, app_id, username):
    """Record the account name this person has (or will have) in the app."""
    apps = apps_from(services)
    with _lock:
        data = _read(data_dir)
        p, acct = _account(data, person_id, app_id, apps)
        name = _clean_username(username, p["name"])
        if acct is None:
            p["accounts"][app_id] = {"username": name}
        else:
            acct["username"] = name
        _write(data_dir, data)
        return p


def new_password(data_dir, services, person_id, app_id, replace=False):
    """Make a long password for the account. An existing one is replaced only when asked, and that clears "set in the app"."""
    apps = apps_from(services)
    with _lock:
        data = _read(data_dir)
        p, acct = _account(data, person_id, app_id, apps)
        if acct is None:
            acct = p["accounts"][app_id] = {"username": _clean_username("", p["name"])}
        if acct.get("password") and not replace:
            raise PeopleError("There is a password already. Choose Make a new password to replace it")
        acct["password"] = make_password()
        acct["made_at"] = _now()
        acct.pop("set_at", None)
        _write(data_dir, data)
        return p


def reveal(data_dir, person_id, app_id):
    """{username, password} for one account. The caller has checked the Starboard password."""
    with _lock:
        data = _read(data_dir)
        p = _find(data, person_id)
        acct = (p.get("accounts") or {}).get(app_id)
        if not acct or not acct.get("password"):
            raise LookupError("There is no password for that account yet")
        return {"username": acct.get("username", ""), "password": acct["password"]}


def mark_set(data_dir, services, person_id, app_id, done):
    """The owner says the password is (or is no longer) set in the app."""
    apps = apps_from(services)
    with _lock:
        data = _read(data_dir)
        p, acct = _account(data, person_id, app_id, apps, need=True)
        if not acct.get("password"):
            raise PeopleError("Make a password first")
        if done:
            acct["set_at"] = _now()
        else:
            acct.pop("set_at", None)
        _write(data_dir, data)
        return p


def drop_account(data_dir, person_id, app_id):
    """Take the account and its kept password out of Starboard's list. Nothing changes in the app."""
    with _lock:
        data = _read(data_dir)
        p = _find(data, person_id)
        if app_id not in (p.get("accounts") or {}):
            raise LookupError("There is no account for that app")
        del p["accounts"][app_id]
        _write(data_dir, data)
        return p


def person_public(data_dir, services, person_id):
    apps = apps_from(services)
    with _lock:
        return public(_find(_read(data_dir), person_id), apps)
