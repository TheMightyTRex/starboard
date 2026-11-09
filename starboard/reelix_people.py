"""Settings, Reelix, People (DASH-199): who has a Reelix account and what each may do, as one of Reelix's own roles
(admin, manager, power user, user, or no asking). Says that Reelix's admin is "admin" with the Starboard password
from set-up, and that changing the Starboard password does not change it."""
ROLES = {  # Reelix's role presets (reelix-core permissions.rs), as numbers
    "user": (1 << 5) | (1 << 6) | (1 << 13),
}
ROLES["power"] = ROLES["user"] | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10) | (1 << 11) | (1 << 12) | (1 << 16) | (1 << 17) | (1 << 18) | (1 << 19) | (1 << 20) | (1 << 21)
ROLES["manager"] = ROLES["power"] | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4)
ROLES["admin"] = 1
ROLES["none"] = 0
WORDS = {"admin": "Admin: everything", "manager": "Manager: library, requests and people", "power": "Can ask, approved automatically",
         "user": "Can ask, you approve", "none": "Cannot ask"}


def role_of(perms):
    perms = int(perms or 0)
    if perms & 1:
        return "admin"
    for name in ("manager", "power", "user"):
        if perms & ROLES[name] == ROLES[name]:
            return name
    return "none" if not perms & ROLES["user"] else "user"


def listing(reelix):
    _, users = reelix.call("GET", "/users")
    users = users.get("items") if isinstance(users, dict) else users or []
    return {"people": [{"id": u["id"], "name": u.get("display_name") or u.get("username"), "user": u.get("username"),
                        "from": {"local": "Reelix", "jellyfin": "Jellyfin", "plex": "Plex"}.get(u.get("auth_source"), u.get("auth_source") or ""),
                        "role": role_of(u.get("permissions"))} for u in users],
            "roles": [{"value": k, "label": v} for k, v in WORDS.items()],
            "about": "Reelix's admin is admin, with the password you chose when Starboard set Reelix up. Changing your Starboard password does not change it."}


def set_role(reelix, user_id, role):
    if role not in ROLES:
        raise ValueError("Choose what this person may do")
    _, user = reelix.call("GET", f"/users/{int(user_id)}")
    if (user or {}).get("username") in ("admin", "starboard") and role != role_of((user or {}).get("permissions")):
        raise ValueError("Starboard does not change its own account or Reelix's admin")
    reelix.call("PUT", f"/users/{int(user_id)}", {"permissions": ROLES[role]})
    out = listing(reelix)
    return {**out, "done": f"{(user or {}).get('display_name') or 'They'}: {WORDS[role].lower()}"}
