"""Settings, Radio (owner, 12 November 2026: "sources for adding and searching for radio programs from other stations
and genres - this needs a settings page"). The sources are Reelix's: BBC, Apple Podcasts, Podcast Index, the
Internet Archive and podcast feeds. Starboard shows each one with what it is for, turns them on or off, sets the
country and language searches prefer, and keeps the Podcast Index key. Reelix keeps these behind its admin password,
so every call here runs inside reelix_admin.Visit. More sources (Global Player, NTS, Mixcloud) need Reelix first:
starboard/RADIO-SOURCES-2026-11-12.md, RFX-93 onwards."""

ABOUT = {
    "bbc": "BBC Sounds: programmes from BBC national, nations and local stations, with its categories.",
    "apple": "Apple Podcasts: radio shows from every broadcaster that publishes them as podcasts, such as LBC, Times Radio and talkSPORT, with genre charts.",
    "podcastindex": "Podcast Index: an open podcast directory with categories. Needs a free key and secret from podcastindex.org.",
    "archive": "The Internet Archive: old-time radio and other recordings in the public domain.",
    "rss": "A podcast feed: any show by its feed address.",
}
COUNTRIES = [("", "Anywhere"), ("GB", "United Kingdom"), ("IE", "Ireland"), ("US", "United States"), ("CA", "Canada"),
             ("AU", "Australia"), ("NZ", "New Zealand")]
LANGUAGES = [("", "Any language"), ("en", "English"), ("cy", "Welsh"), ("gd", "Scottish Gaelic"), ("ga", "Irish"),
             ("fr", "French"), ("de", "German"), ("es", "Spanish")]
MASK = "********"


def state(reelix):
    """What the Sources section shows."""
    _, providers = reelix.call("GET", "/radio/providers")
    _, s = reelix.call("GET", "/radio/settings")
    s = s or {}
    allowed = set(s.get("enabled_providers") or [])
    out = []
    for p in providers or []:
        pid = str(p.get("id") or "")
        # Reelix with RFX-102 says how episodes arrive, any risk, and the source's stations; older Reelix does not.
        arrive = str(p.get("episodes_arrive") or "")
        risk = str(p.get("risk") or "")
        stations = [s for s in p.get("stations") or [] if isinstance(s, dict)]
        about = ABOUT.get(pid, "")
        extra = " ".join(x for x in (f"Episodes: {arrive[:1].lower() + arrive[1:]}." if arrive else "",
                                      f"{len(stations)} stations." if stations else "", risk) if x)
        out.append({"id": pid, "name": p.get("name") or pid, "about": " ".join(x for x in (about, extra) if x),
                    "search": bool(p.get("supports_search")), "on": (not allowed or pid in allowed),
                    "needs_key": bool(p.get("key_needed")) or pid == "podcastindex", "works": bool(p.get("enabled"))})
    return {"sources": out, "country": s.get("country") or "", "language": s.get("language") or "",
            "countries": COUNTRIES, "languages": LANGUAGES,
            "podcastindex_key": s.get("podcastindex_api_key") or "", "podcastindex_secret_set": bool(s.get("podcastindex_api_secret"))}


def save(reelix, body):
    """Writes the choices into Reelix's radio settings, keeping everything else it has there."""
    _, providers = reelix.call("GET", "/radio/providers")
    known = [str(p.get("id")) for p in providers or []]
    on = [p for p in body.get("on") or [] if p in known]
    if not on:
        raise ValueError("Leave at least one source on")
    country, language = str(body.get("country") or ""), str(body.get("language") or "")
    if country not in {c for c, _ in COUNTRIES} or language not in {c for c, _ in LANGUAGES}:
        raise ValueError("Choose a country and a language from the lists")
    _, current = reelix.call("GET", "/radio/settings")
    new = {**(current or {}), "enabled_providers": [] if set(on) == set(known) else on,
           "country": country or None, "language": language or None}
    key = str(body.get("podcastindex_key") or "").strip()
    secret = str(body.get("podcastindex_secret") or "").strip()
    new["podcastindex_api_key"] = key or None
    new["podcastindex_api_secret"] = MASK if (not secret and (current or {}).get("podcastindex_api_secret") and key) else (secret or None)
    reelix.call("PUT", "/radio/settings", new)
    done = [f"{len(on)} of {len(known)} sources on"]
    if "podcastindex" in on and not key:
        done.append("Podcast Index stays off until it has a key and secret")
    return {"state": state(reelix), "done": done}
