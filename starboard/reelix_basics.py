"""Settings, Reelix, the basics (DASH-226): the settings most people change, in the approved order: films and series
information (the TMDB key, with Test), picture quality, language of releases and who can ask for things. Reelix keeps
them behind its admin password, so Starboard asks for it each time (reelix_admin.py).

Picture quality picks the quality profile new requests and additions use, for films and for series. Who can ask sets
what a new Reelix user may do: only you, everyone with you approving each one, or everyone approved automatically.
People who already have a Reelix account keep what they have; Settings, Reelix, People changes them."""
from . import setup_answers

# Reelix's permission bits (reelix-core permissions.rs): asking and approving, for each kind.
ASK = (1 << 5) | (1 << 6) | (1 << 13) | (1 << 16) | (1 << 17) | (1 << 20)  # films, series, issues, books, music, radio
APPROVE = (1 << 9) | (1 << 10) | (1 << 18) | (1 << 19) | (1 << 21)
WHO = {"me": "Only me", "approve": "Everyone, I approve each one", "auto": "Everyone, approved automatically"}


def _who(perms):
    perms = int(perms or 0)
    if not perms & ASK:
        return "me"
    return "auto" if perms & APPROVE == APPROVE else "approve"


def state(reelix):
    _, meta = reelix.call("GET", "/settings/metadata")
    _, req = reelix.call("GET", "/settings/requests")
    _, profiles = reelix.call("GET", "/qualityprofiles")
    video = [p for p in profiles or [] if p.get("family", "video") == "video"]
    meta, req = meta or {}, req or {}
    chosen = ((req.get("movie") or {}).get("profile_id")) or (video[0]["id"] if video else None)
    language = next((p.get("language") for p in video if "language" in p), "English")
    return {"tmdb": bool(meta.get("tmdb_api_key") or meta.get("tmdb_read_token")),
            "profiles": [{"id": p["id"], "name": p.get("name", "")} for p in video], "profile": chosen,
            "language": language if language in ("English", "Original") else "",
            "languages": setup_answers.WORDS["language"]["choices"],
            "who": _who(req.get("default_permissions")), "whos": [{"value": k, "label": v} for k, v in WHO.items()]}


def save(reelix, changes):
    """Saves what was changed; returns the new state and what was done, in words."""
    done = []
    c = changes or {}
    if c.get("tmdb"):
        key = setup_answers.clean_tmdb(c["tmdb"])
        _, meta = reelix.call("GET", "/settings/metadata")
        reelix.call("PUT", "/settings/metadata", setup_answers.tmdb_settings(key, meta))
        done.append("TMDB key saved")
    if "profile" in c or "who" in c:
        _, req = reelix.call("GET", "/settings/requests")
        req = dict(req or {})
        if "profile" in c and str(c["profile"]).isdigit():
            for kind in ("movie", "series"):
                req[kind] = {**(req.get(kind) or {}), "profile_id": int(c["profile"])}
            done.append("Picture quality saved")
        if c.get("who") in WHO:
            perms = int(req.get("default_permissions") or 0) & ~(ASK | APPROVE)
            perms |= {"me": 0, "approve": ASK, "auto": ASK | APPROVE}[c["who"]]
            req["default_permissions"] = perms
            req["auto_approve_movie"] = req["auto_approve_series"] = c["who"] == "auto"
            done.append(f"Who can ask: {WHO[c['who']].lower()}")
        reelix.call("PUT", "/settings/requests", req)
    if "language" in c:
        done += setup_answers.apply_language(reelix, c["language"]) or ["Language saved"]
    return {**state(reelix), "done": done}
