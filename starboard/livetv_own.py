"""The owner's own Live TV sources (DASH-359, owner 12 November 2026: "add json files as groups", "add XML sources -
each one gets its own entry with a switch"). Each source is an address the person adds on the plug-in's
"Your lists and guides" screen, kept in the plug-in's data folder with its own Activate or Deactivate:

  a channel list: an M3U playlist, or JSON with a stream address per channel. Its channels are tested like Free-TV's
                  and go into own.m3u, grouped under the list's name; one more tuner in Jellyfin for all of them.
  a guide:        an XMLTV file (.xml or .xml.gz). Programmes for the channels in own.m3u go into guide-own.xml.

The channel lists that only point at a web page or need a paid account give nothing to play. Stremio add-on
addresses (manifest.json) are not channel lists: they are refused with a sentence saying so.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import time
import urllib.parse

from . import livetv

FILE = "own-sources.json"  # in the plug-in's own data folder
PLAYLIST, GUIDE = "own.m3u", "guide-own.xml"
MAX_SOURCES = 40
MAX_CHANNELS = 2000  # from one list
UA = "Lavf/60.16.100"


def _path(data_dir):
    return os.path.join(data_dir, FILE)


def sources(data_dir):
    try:
        with open(_path(data_dir), encoding="utf-8") as f:
            got = json.load(f)
        return [s for s in got if isinstance(s, dict) and s.get("id") and s.get("url")]
    except (OSError, ValueError, TypeError):
        return []


def save(data_dir, items):
    tmp = _path(data_dir) + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f)
    os.replace(tmp, _path(data_dir))


def _name(url):
    u = urllib.parse.urlparse(url)
    tail = [p for p in u.path.split("/") if p]
    return livetv._clean(f"{u.hostname or ''}{' · ' + tail[-1] if tail else ''}", 60)


def _text(raw):
    if raw[:2] == b"\x1f\x8b":
        raw = livetv._gunzip(raw)
    return raw.decode("utf-8", "replace").lstrip("﻿ \r\n\t")


def _head(raw, size=65536):
    """The first bytes of a download as text, unpacking only those (xmltv.live's gb.xml.gz unpacks to 40 MB, too
    much for the plug-in's 192 MB just to see what it is)."""
    if raw[:2] == b"\x1f\x8b":
        import gzip
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:
            raw = g.read(size)
    return raw[:size].decode("utf-8", "replace").lstrip("﻿ \r\n\t")


def _is_guide(text):
    return text.startswith("<") and bool(re.search(r"<tv[\s>]", text[:4000]))


def kind_of(text):
    """'list' (M3U or JSON channels), 'guide' (XMLTV), or a ValueError saying what it is not."""
    if text.startswith("#EXTM3U") or text.startswith("#EXTINF"):
        return "list"
    if text.startswith("<") and re.search(r"<tv[\s>]", text[:4000]):
        return "guide"
    if text.startswith(("{", "[")):
        try:
            data = json.loads(text)
        except ValueError:
            raise ValueError("That JSON file could not be read") from None
        if isinstance(data, dict) and "catalogs" in data and "resources" in data:
            raise ValueError("That is a Stremio add-on, not a channel list: it has no stream addresses to add")
        if not json_channels(data):
            raise ValueError("That JSON file has no channels with a stream address")
        return "list"
    raise ValueError("That address is not an M3U playlist, a JSON channel list or an XMLTV guide")


def json_channels(data):
    """Channels from JSON: a list of channels, or {"channels": [...] or {id: {...}}}. Each needs a name and an
    http(s) stream address (url, stream, streamUrl or src); logo, group and id (or tvg-id) are used when given."""
    if isinstance(data, dict):
        data = data.get("channels", data.get("items", []))
    if isinstance(data, dict):
        data = [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]
    out = []
    for c in data if isinstance(data, list) else []:
        if not isinstance(c, dict):
            continue
        url = next((str(c[k]) for k in ("url", "stream", "streamUrl", "stream_url", "src") if c.get(k)), "")
        name = str(c.get("name") or c.get("title") or "")
        if name and livetv._clean_url(url):
            out.append({"id": str(c.get("tvg-id") or c.get("tvg_id") or c.get("epg_id") or c.get("id") or ""), "name": name,
                        "url": url, "logo": str(c.get("logo") or c.get("tvg-logo") or c.get("image") or ""),
                        "group": str(c.get("group") or c.get("group-title") or c.get("category") or "")})
    return out[:MAX_CHANNELS]


def m3u_channels(text):
    out, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and i + 1 < len(lines):
            url = next((x.strip() for x in lines[i + 1:i + 4] if x.strip() and not x.startswith("#")), "")
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            if livetv._clean_url(url):
                out.append({"id": attrs.get("tvg-id", ""), "name": line.rsplit(",", 1)[-1].strip(), "url": url,
                            "logo": attrs.get("tvg-logo", ""), "group": attrs.get("group-title", "")})
    return out[:MAX_CHANNELS]


def read(url, fetch=None):
    """(kind, channels or None) for an address; raises ValueError in words."""
    raw = (fetch or livetv.fetch)(url, timeout=60)
    if _is_guide(_head(raw)):  # a guide is only looked at, never unpacked whole here (it is read a piece at a time later)
        return "guide", None
    text = _text(raw)
    kind = kind_of(text)
    if kind == "guide":
        return kind, None
    chans = m3u_channels(text) if text.startswith("#") else json_channels(json.loads(text))
    if not chans:
        raise ValueError("That list has no channels with a stream address")
    return kind, chans


def add(data_dir, url, fetch=None):
    url = url.strip()
    if not livetv._clean_url(url) or url != livetv._clean_url(url):
        raise ValueError("Type a web address starting http:// or https://")
    have = sources(data_dir)
    if any(s["url"] == url for s in have):
        raise ValueError("That address is already added")
    if len(have) >= MAX_SOURCES:
        raise ValueError(f"Up to {MAX_SOURCES} lists and guides")
    kind, chans = read(url, fetch)
    sid = hashlib.sha256(url.encode()).hexdigest()[:10]
    item = {"id": sid, "url": url, "kind": kind, "name": _name(url), "on": True, "added": time.time(),
            "said": f"{len(chans)} channels found" if chans is not None else "A guide"}
    save(data_dir, have + [item])
    return item


def fingerprint(data_dir):
    return livetv._fingerprint([(s["id"], s["url"], s.get("on", True)) for s in sources(data_dir)])


def build(d, data_dir, fetch=None, plays=None):
    """Writes own.m3u from every active channel list (only channels that play), then the guide. Returns a sentence."""
    lists = [s for s in sources(data_dir) if s.get("on", True) and s.get("kind") == "list"]
    entries, seen, notes = [], set(), {}
    for s in lists:
        try:
            _, chans = read(s["url"], fetch)
        except Exception as e:  # one list failing does not stop the others
            notes[s["id"]] = (f"Could not be read: {str(e)[:100]}", "problem")
            continue
        with cf.ThreadPoolExecutor(8) as ex:
            ok = list(ex.map(lambda c: (plays or livetv.plays)(c["url"], UA), chans))
        good = 0
        for n, (c, works) in enumerate(zip(chans, ok)):
            cid = c["id"] or f"own-{s['id']}-{n}"
            if not works or cid in seen:
                continue
            seen.add(cid)
            good += 1
            line = livetv._entry(cid, c, 30000 + len(entries), f"{s['name']} · {c['group'] or 'Other'}", c["url"])
            entries.append(line.replace("#EXTINF:-1 ", f'#EXTINF:-1 starboard-src="{s["id"]}" ', 1))
        notes[s["id"]] = (f"{good} of {len(chans)} channels play", "ok" if good else "warning")
    livetv._write(os.path.join(d, PLAYLIST), "\n".join(["#EXTM3U"] + entries) + "\n")
    _note(data_dir, notes)
    return f"Your lists: {len(entries)} channels" + ("; " + guide(d, data_dir) if seen else "")


def guide(d, data_dir):
    urls = [s["url"] for s in sources(data_dir) if s.get("on", True) and s.get("kind") == "guide"]
    ids = livetv._ids_in(os.path.join(d, PLAYLIST))
    if not urls or not ids:
        livetv._write(os.path.join(d, GUIDE), '<?xml version="1.0" encoding="utf-8"?>\n<tv generator-info-name="Starboard"></tv>\n')
        return "your guides: none active"
    return f"your guides: {livetv._filtered_guide(urls, ids, os.path.join(d, GUIDE))} programmes"


def _note(data_dir, notes):
    items = sources(data_dir)
    for s in items:
        if s["id"] in notes:
            s["said"], s["state"] = notes[s["id"]]
    save(data_dir, items)


def drop(d, sid):
    """Takes one source's channels out of own.m3u and the full channel list now. Returns how many went."""
    path = os.path.join(d, PLAYLIST)
    if not os.path.exists(path):
        return 0
    chans = livetv._parse(path)
    keep = [c for c in chans if c["attrs"].get("starboard-src") != sid]
    lines = ["#EXTM3U"]
    for c in keep:
        lines += ["#EXTINF:-1 " + " ".join(f'{k}="{v}"' for k, v in c["attrs"].items()) + f",{c['name']}", c["url"]]
    livetv._write(path, "\n".join(lines) + "\n")
    rest = [c for c in livetv.all_channels(d) if c.get("source") != sid]
    livetv._write(os.path.join(d, livetv.ALL), json.dumps(rest))
    return len(chans) - len(keep)
