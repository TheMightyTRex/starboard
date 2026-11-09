"""What is new in an app Starboard updates: read from the app's own changelog (CHANGELOG.md, Keep a Changelog), for
the versions between the one installed and the newest, and a notice after the app's version changes.

Only Reelix for now. Nothing runs in the background: the changelog is downloaded when someone opens What is new,
kept in memory for 6 hours, and capped at 1 MB. The versions seen are kept in app-changes.json, a few lines.
"""

import datetime as dt
import json
import os
import re
import threading
import time
import urllib.request

# (image repository, app name, changelog address). Reelix's images are the owner's fork's: Lite is built from the fork's
# fork/lite branch and the full one from its master, so each changelog comes from that branch (9 November 2026).
# Upstream's image is used only if someone chooses it.
SOURCES = [
    (re.compile(r"(^|/)themightytrex/reelix:lite$", re.I), "Reelix", "https://raw.githubusercontent.com/TheMightyTRex/Reelix/fork/lite/CHANGELOG.md"),
    (re.compile(r"(^|/)themightytrex/reelix(:.*)?$", re.I), "Reelix", "https://raw.githubusercontent.com/TheMightyTRex/Reelix/master/CHANGELOG.md"),
    (re.compile(r"(^|/)reelix(:.*)?$", re.I), "Reelix", "https://raw.githubusercontent.com/demonzoned/Reelix/master/CHANGELOG.md"),
]
TYPES = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")
KEEP = 6 * 3600
LIMIT = 1024 * 1024
VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")

_lock = threading.Lock()
_cache = {}  # address -> (fetched at, versions)


def source(image):
    """(app name, changelog address) for an image such as ghcr.io/themightytrex/reelix:lite, or None."""
    repo = (image or "").split("@", 1)[0]  # the tag stays: Lite and full have different changelogs
    for pattern, name, url in SOURCES:
        if pattern.search(repo):
            return name, url
    return None


def clean(version):
    """0.7.1 from "0.7.1", "v0.7.1" or "0.7.1-lite"; None for "lite", "latest", "dev" and test builds."""
    v = re.sub(r"-lite$", "", str(version or "").strip())
    return ".".join(VERSION.match(v).groups()) if VERSION.match(v) else None


def _key(version):
    return tuple(int(n) for n in version.split("."))


def _date(text):
    try:
        d = dt.date.fromisoformat(text)
        return f"{d.day} {d.strftime('%B')} {d.year}"
    except ValueError:
        return text  # already written out, as in "4 November 2026"


def _inline(text):
    """Bold, code and links as plain parts the page builds as text, never as HTML. A link keeps only its words."""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    parts = []
    for bit in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not bit:
            continue
        if bit.startswith("**") and bit.endswith("**") and len(bit) > 4:
            parts.append(["strong", bit[2:-2]])
        elif bit.startswith("`") and bit.endswith("`") and len(bit) > 2:
            parts.append(["code", bit[1:-1]])
        else:
            parts.append(["text", bit])
    return parts


def parse(text):
    """Every version in a Keep a Changelog file, newest first: version, date, withdrawn, summary and sections, each
    section a type with its entries, and each entry its parts with the entries nested under it."""
    versions, current, section, stack = [], None, None, []
    for line in text.splitlines():
        m = re.match(r"^## \[?v?(\d+\.\d+\.\d+)\]?\s*(?:-\s*|\()?([^)\[]*?)\)?\s*(\[(YANKED|Withdrawn)\])?\s*$", line, re.I)
        if m:
            current = {"version": m.group(1), "date": _date(m.group(2).strip()), "withdrawn": bool(m.group(3)),
                       "summary": [], "sections": []}
            versions.append(current)
            section, stack = None, []
            continue
        if line.startswith("## "):  # Unreleased, or anything else that is not a release
            current = section = None
            continue
        if current is None:
            continue
        m = re.match(r"^### (.+?)\s*$", line)
        if m:
            section = {"type": m.group(1), "items": []}
            current["sections"].append(section)
            stack = []
            continue
        m = re.match(r"^(\s*)[-*] (.+)$", line)
        if m and section is not None:
            depth = len(m.group(1).expandtabs(2)) // 2
            item = {"parts": _inline(m.group(2).strip()), "items": []}
            stack = stack[:depth]
            (stack[-1]["items"] if stack else section["items"]).append(item)
            stack.append(item)
            continue
        if line.strip() and stack and line.startswith("  "):  # a wrapped entry carries on
            stack[-1]["parts"] += _inline(" " + line.strip())
        elif line.strip() and section is None and not line.startswith("["):
            current["summary"] += _inline(line.strip() + " ")
    for v in versions:  # Keep a Changelog's order for the types, whatever order the file uses
        v["sections"].sort(key=lambda s: TYPES.index(s["type"]) if s["type"] in TYPES else len(TYPES))
    return versions


def _fetch(url):
    with _lock:
        hit = _cache.get(url)
    if hit and time.time() - hit[0] < KEEP:
        return hit[1]
    if not url.startswith("https://"):
        raise ValueError("A changelog address must start with https://")
    req = urllib.request.Request(url, headers={"User-Agent": "Starboard"})
    with urllib.request.urlopen(req, timeout=10) as r:  # a fixed https address from the table above, checked  # nosec B310
        body = r.read(LIMIT + 1)
    if len(body) > LIMIT:
        raise ValueError("The changelog is larger than 1 MB")
    versions = parse(body.decode("utf-8", "replace"))
    with _lock:
        _cache[url] = (time.time(), versions)
    return versions


def between(image, after, upto):
    """The changes for an image from after (not included) to upto (included), newest first. With no version known
    for after, only upto's own changes; with no upto, everything newer than after."""
    found = source(image)
    if not found:
        raise ValueError("Starboard does not know where this app keeps its changelog")
    name, url = found
    old, new = clean(after), clean(upto)
    versions = _fetch(url)
    if new is None and old is None:
        picked = versions[:1]
    else:
        picked = [v for v in versions
                  if (old is None or _key(v["version"]) > _key(old)) and (new is None or _key(v["version"]) <= _key(new))]
        if old is None:
            picked = picked[:1]
    return {"app": name, "source": url.replace("raw.githubusercontent.com", "github.com").replace("/master/", "/blob/master/"),
            "from": old, "to": new, "versions": picked}


# The version each app had when Starboard last looked, and the notice after it changes --------------------------

def _path(data_dir):
    return os.path.join(data_dir, "app-changes.json")


def _load(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data_dir, data):
    tmp = _path(data_dir) + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _path(data_dir))


def observe(data_dir, rows):
    """Marks each row whose image has a changelog, and records a notice when its version has gone up since the
    last look. Called with the Apps, Updates rows, which already hold each container's version."""
    with _lock:
        data = _load(data_dir)
        seen, notices = data.setdefault("seen", {}), data.setdefault("notices", {})
        changed = False
        for row in rows:
            c = row.get("container")
            found = c and source(c.get("image"))
            if not found:
                continue
            row["changelog"] = True
            now = clean(c.get("version"))
            if not now:
                continue
            before = seen.get(row["id"])
            if before != now:
                seen[row["id"]] = now
                changed = True
                if before and _key(now) > _key(before):
                    old = notices.get(row["id"], {}).get("from", before)  # two updates before anyone looked
                    notices[row["id"]] = {"app": row["id"], "name": row.get("name") or found[0], "image": c["image"],
                                          "from": old, "to": now, "at": time.time()}
        if changed:
            _save(data_dir, data)
    return rows


def notices(data_dir):
    return sorted(_load(data_dir).get("notices", {}).values(), key=lambda n: n.get("at", 0))


def seen(data_dir, app):
    with _lock:
        data = _load(data_dir)
        if data.get("notices", {}).pop(app, None) is not None:
            _save(data_dir, data)
