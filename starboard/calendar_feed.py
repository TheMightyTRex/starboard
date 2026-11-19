"""The calendar feed (DASH-67, DASH-469): Coming up as an iCalendar file at /calendar.ics?token=..., for a phone or
calendar app to subscribe to.

- A calendar app cannot sign in, so the address carries a token. The token opens this one file and nothing else: it
  is not an API key (sbcal_, not sb_), the session never accepts it, and /api/v1 never matches it.
- One token at a time, made on the Coming up page by a signed-in person. Starboard keeps only its SHA-256 hash, in
  calendar-feed.json in the data folder (mode 600), and compares hashes in constant time. A new token replaces the
  old one, so the old address stops working at once; stopping the feed removes it.
- A refused token counts towards the sign-in lockout for that address, as a refused API key does (AS10). A good token
  shares the API's token bucket under its own name: 120 a minute.
- The feed answers from the same shared answers Coming up uses, kept for 15 minutes, with an ETag, so a calendar app
  that asks often costs one look at the apps every 15 minutes at most.
- Films, books and albums are all-day events on their release date; episodes and radio are timed events at the time
  they air.
"""
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets

FILE = "calendar-feed.json"
PREFIX = "sbcal_"
TOKEN = re.compile(r"^sbcal_[A-Za-z0-9_-]{40,60}$")
BACK_DAYS = 7  # a week back, so last night's episode stays in the calendar
AHEAD_DAYS = 55  # with BACK_DAYS, the 62 days services.calendar allows in one go (about 8 weeks ahead)
KEEP_SECONDS = 900  # the shared answer and the Cache-Control max-age
TIMED_MINUTES = 30  # how long a timed event lasts in the calendar: the apps do not say
PRODID = "-//TheMightyTRexUK//Starboard//EN"
KINDS = {"sonarr": "Episode", "radarr": "Film", "lidarr": "Album", "readarr": "Book", "radio": "Radio"}


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def _load(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) and isinstance(data.get("hash"), str) else None
    except (OSError, ValueError):
        return None


def _save(data_dir, data):
    path = _path(data_dir)
    if data is None:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return
    tmp = path + ".new"
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def status(data_dir):
    """What the page shows: when the address was made and last used. Never the token or its hash."""
    data = _load(data_dir)
    return {"made_at": data.get("made_at") if data else None, "last_used_at": data.get("last_used_at") if data else None,
            "back_days": BACK_DAYS, "ahead_days": AHEAD_DAYS}


def make(data_dir):
    """A new token, shown this once; the old one, if any, stops working."""
    token = PREFIX + secrets.token_urlsafe(32)
    _save(data_dir, {"hash": _digest(token), "made_at": _iso(_now()), "last_used_at": None})
    return token


def stop(data_dir):
    _save(data_dir, None)


def valid(data_dir, token):
    """True only for the current token. The hashes are compared in constant time."""
    if not isinstance(token, str) or not TOKEN.match(token):
        return False
    data = _load(data_dir)
    return bool(data) and hmac.compare_digest(data["hash"], _digest(token))


def note_use(data_dir, now=None):
    """last_used_at, written at most once an hour to spare the disk."""
    data = _load(data_dir)
    if not data:
        return
    now = now or _now()
    last = data.get("last_used_at")
    if last and (now - dt.datetime.strptime(last, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() < 3600:
        return
    data["last_used_at"] = _iso(now)
    _save(data_dir, data)


def window(today=None):
    """The dates the feed covers: (start, end)."""
    today = today or dt.date.today()
    return today - dt.timedelta(days=BACK_DAYS), today + dt.timedelta(days=AHEAD_DAYS)


# iCalendar (RFC 5545) -----------------------------------------------------------------------------------------

def escape(text):
    """TEXT values: backslash, semicolon and comma escaped, line breaks as \\n (RFC 5545 3.3.11)."""
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    return "".join(c for c in text if c == "\t" or ord(c) >= 32 and ord(c) != 127)  # no other control characters


def fold(line):
    """One content line folded to at most 75 octets per line, never inside a UTF-8 character (RFC 5545 3.1)."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line + "\r\n"
    out, chunk, limit = [], b"", 75
    for ch in line:
        b = ch.encode("utf-8")
        if len(chunk) + len(b) > limit:
            out.append(chunk)
            chunk, limit = b"", 74  # each line after the first starts with a space
        chunk += b
    out.append(chunk)
    return "\r\n ".join(c.decode("utf-8") for c in out) + "\r\n"


def _when(value):
    """(date, datetime in UTC or None) from an app's date: a datetime only when the value has a time of day."""
    value = str(value or "").strip()
    if not value:
        return None, None
    try:
        if len(value) <= 10:
            return dt.date.fromisoformat(value[:10]), None
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return dt.date.fromisoformat(value[:10]), None
        except ValueError:
            return None, None
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t.astimezone(dt.timezone.utc).date(), t.astimezone(dt.timezone.utc)


def kind_of(item, types):
    if item.get("kind") == "radio":
        return "radio"
    return types.get(item.get("service"), "")


def summary(item, kind):
    title, detail = item.get("title") or "", item.get("detail") or ""
    if kind == "radarr" or not detail or detail == "Film":
        return title
    if kind == "readarr":
        return f"{title} by {detail}"
    return f"{title} · {detail}"


def uid(item, kind):
    """The same for the same release from one feed to the next, so calendar apps update an event, not add one."""
    seed = "|".join(str(x) for x in (item.get("service"), kind, item.get("item_id"), item.get("title"), item.get("detail")))
    return hashlib.sha256(seed.encode()).hexdigest()[:32] + "@starboard"


def event(item, kind, stamp):
    """One VEVENT's lines, or [] for an item with no date."""
    day, at = _when(item.get("when"))
    if not day:
        return []
    timed = at is not None and kind in ("sonarr", "radio")
    lines = ["BEGIN:VEVENT", f"UID:{uid(item, kind)}", f"DTSTAMP:{stamp:%Y%m%dT%H%M%SZ}"]
    if timed:
        lines += [f"DTSTART:{at:%Y%m%dT%H%M%SZ}", f"DTEND:{at + dt.timedelta(minutes=TIMED_MINUTES):%Y%m%dT%H%M%SZ}"]
    else:  # a release date: an all-day event, which ends the next day (DTEND is not included)
        lines += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + dt.timedelta(days=1):%Y%m%d}"]
    state = "In the library" if item.get("have") else "Wanted"
    words = [KINDS.get(kind, "Release") + f" from {item.get('service_name') or 'your apps'}. {state}."]
    if item.get("overview"):
        words.append(str(item["overview"]))
    lines += [f"SUMMARY:{escape(summary(item, kind))}", f"DESCRIPTION:{escape(chr(10).join(words))}",
              f"CATEGORIES:{escape(KINDS.get(kind, 'Release'))}", "TRANSP:TRANSPARENT", "END:VEVENT"]
    return lines


def ics(items, types, name="Starboard", stamp=None):
    """The whole calendar as bytes: CRLF line endings, lines folded at 75 octets.
    types maps an app's id to its type (sonarr, radarr, lidarr, readarr)."""
    stamp = stamp or _now()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{escape(f'{name}: Coming up')}", "X-WR-CALDESC:" + escape("New episodes, films, albums, books and radio from Starboard"),
             "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H"]
    seen = set()
    for item in items:
        kind = kind_of(item, types)
        lines_for = event(item, kind, stamp)
        if not lines_for or lines_for[1] in seen:  # one event per release, even if two apps list it
            continue
        seen.add(lines_for[1])
        lines += lines_for
    lines.append("END:VCALENDAR")
    return "".join(fold(line) for line in lines).encode("utf-8")
