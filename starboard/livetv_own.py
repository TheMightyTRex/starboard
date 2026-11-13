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


def m3u_channels(text, skipped=None):
    """Channels from an M3U playlist. `skipped`: a list that gets each address Jellyfin cannot play, such as a Kodi
    add-on link (plugin://), so the result can say why they were left out."""
    out, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and i + 1 < len(lines):
            url = next((x.strip() for x in lines[i + 1:i + 4] if x.strip() and not x.startswith("#")), "")
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            if not livetv._clean_url(url) and skipped is not None and url:
                skipped.append(url)
            if livetv._clean_url(url):
                out.append({"id": attrs.get("tvg-id", ""), "name": line.rsplit(",", 1)[-1].strip(), "url": url,
                            "logo": attrs.get("tvg-logo", ""), "group": attrs.get("group-title", "")})
    return out[:MAX_CHANNELS]


FILES = "own-files"  # uploaded files, in the plug-in's own data folder; a source's url is then "file:<name in it>"
MAX_UPLOAD = 60 * 1024 * 1024
MAX_LIST = 20 * 1024 * 1024  # a channel list is read whole; a guide never is


def local_path(data_dir, url):
    """The stored copy of an uploaded file, for a source whose url is file:<name>; None for a web address."""
    if not url.startswith("file:"):
        return None
    name = os.path.basename(url[5:])
    return os.path.join(data_dir, FILES, name) if re.fullmatch(r"[0-9a-f]{10}\.[a-z.]{1,8}", name) else None


def read(url, fetch=None, data_dir=None, skipped=None):
    """(kind, channels or None) for an address or an uploaded file; raises ValueError in words."""
    path = local_path(data_dir or "", url) if data_dir else None
    if url.startswith("file:"):
        if not path or not os.path.exists(path):
            raise ValueError("The uploaded file is missing: add it again")
        with open(path, "rb") as f:
            raw = f.read(1 << 20)
    else:
        raw = (fetch or livetv.fetch)(url, timeout=60)
    if _is_guide(_head(raw)):  # a guide is only looked at, never unpacked whole here (it is read a piece at a time later)
        return "guide", None
    if path:
        if os.path.getsize(path) > MAX_LIST:
            raise ValueError("A channel list can be up to 20 MB")
        with open(path, "rb") as f:
            raw = f.read()
    text = _text(raw)
    kind = kind_of(text)
    if kind == "guide":
        return kind, None
    chans = m3u_channels(text, skipped) if text.startswith("#") else json_channels(json.loads(text))
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
            "said": _found(chans)}
    save(data_dir, have + [item])
    return item


def add_file(data_dir, filename, stream, length):
    """An uploaded M3U, JSON or XMLTV file (DASH-359, owner 12 November 2026: "allow a file picker ... as well as the
    URL"). Read from `stream` a piece at a time into the plug-in's folder, then looked at like an address."""
    if not 0 < length <= MAX_UPLOAD:
        raise ValueError("Choose a file up to 60 MB (a large guide can be packed as .xml.gz)")
    have = sources(data_dir)
    if len(have) >= MAX_SOURCES:
        raise ValueError(f"Up to {MAX_SOURCES} lists and guides")
    shown = livetv._clean(os.path.basename(str(filename or "file")), 80) or "file"
    os.makedirs(os.path.join(data_dir, FILES), exist_ok=True)
    tmp = os.path.join(data_dir, FILES, ".upload")
    digest, left = hashlib.sha256(), length
    with open(tmp, "wb") as f:
        while left:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            digest.update(chunk)
            left -= len(chunk)
    if left:
        os.remove(tmp)
        raise ValueError("The upload stopped before the end")
    sid = digest.hexdigest()[:10]
    if any(s["id"] == sid for s in have):
        os.remove(tmp)
        raise ValueError("That file is already added")
    ext = ".gz" if shown.lower().endswith(".gz") else ""
    stored = os.path.join(data_dir, FILES, sid + (ext or ".file"))
    os.replace(tmp, stored)
    url = f"file:{os.path.basename(stored)}"
    try:
        kind, chans = read(url, data_dir=data_dir)
    except Exception:
        os.remove(stored)  # the plug-in's own copy of a file it cannot use
        raise
    item = {"id": sid, "url": url, "kind": kind, "name": shown, "on": True, "added": time.time(),
            "said": _found(chans)}
    save(data_dir, have + [item])
    return item


def forget(data_dir, item):
    """Removes an uploaded file's stored copy (Remove on the screen); the person's own file is untouched."""
    path = local_path(data_dir, item.get("url", ""))
    if path and os.path.exists(path):
        os.remove(path)


def _found(chans):
    if chans is None:
        return "A guide"
    return f"{len(chans)} {'channel' if len(chans) == 1 else 'channels'} found"


def fingerprint(data_dir):
    return livetv._fingerprint([(s["id"], s["url"], s.get("on", True)) for s in sources(data_dir)])


def _key(name):
    """A channel's name for spotting duplicates: no HD, UK or punctuation, so "BBC One HD" is "BBC One"."""
    n = re.sub(r"\(.*?\)|\[.*?\]", " ", str(name).lower())
    n = re.sub(r"\b(hd|fhd|uhd|sd|4k|uk|gb|1080p?|720p?|tv)\b", " ", n)
    return re.sub(r"[^a-z0-9]+", "", n)


def _why(url):
    """Why a channel did not play, in a few words, for the result (DASH-359)."""
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=10) as r:  # an http(s) address from the list  # nosec B310
            r.read(1024)
        return "answer but do not play"
    except urllib.error.HTTPError as e:
        return "answer Not found" if e.code in (404, 410) else "refuse to play here" if e.code in (401, 403, 451) else f"answer error {e.code}"
    except Exception:  # no answer at all, or not a web address
        return "do not answer"


def build(d, data_dir, fetch=None, plays=None, only=None, why=None):
    """Writes own.m3u from every active channel list (only channels that play), then the guides. `only`: test just
    that list again, keeping the others' channels as they are (a list just added). A channel that is already in Live
    TV, in any list, active or not, comes in inactive (owner, 13 November 2026), once: activate it at any time. Each
    list's progress and result are kept on it for the screen's notices. Returns a sentence."""
    items = sources(data_dir)
    lists = [x for x in items if x.get("on", True) and x.get("kind") == "list"]
    old = livetv._parse(os.path.join(d, PLAYLIST)) if os.path.exists(os.path.join(d, PLAYLIST)) else []
    known_urls, known_names = set(), set()
    for c in livetv.all_channels(d):  # every channel from the other lists, hidden ones too
        if c.get("list") != PLAYLIST:
            known_names.add(_key(c.get("name", "")))
    for name in livetv.FILES:
        if name != PLAYLIST and os.path.exists(os.path.join(d, name)):
            known_urls.update(c["url"] for c in livetv._parse(os.path.join(d, name)))
    hidden = livetv.hidden_ids(data_dir)
    entries, seen, newly_hidden = [], set(), set()
    for x in lists:
        if only and x["id"] != only:  # kept as they are
            for c in old:
                if c["attrs"].get("starboard-src") == x["id"] and c["attrs"].get("tvg-id") not in seen:
                    seen.add(c["attrs"].get("tvg-id"))
                    known_urls.add(c["url"])
                    known_names.add(_key(c["name"]))
                    entries.append("#EXTINF:-1 " + " ".join(f'{k}="{v}"' for k, v in c["attrs"].items()) + f",{c['name']}\n{c['url']}")
            continue
        skipped = []
        try:
            _, chans = read(x["url"], fetch, data_dir, skipped)
        except Exception as e:  # one list failing does not stop the others
            _update(data_dir, x["id"], said=f"Could not be read: {str(e)[:100]}", state="problem", progress=None,
                    result={"added": 0, "total": 0, "text": f"It could not be read: {str(e)[:160]}"})
            continue
        total = len(chans) + len(skipped)
        _update(data_dir, x["id"], progress={"done": 0, "total": len(chans)})
        ok, done = [False] * len(chans), 0
        with cf.ThreadPoolExecutor(8) as ex:
            futures = {ex.submit(plays or livetv.plays, c["url"], UA): i for i, c in enumerate(chans)}
            for f in cf.as_completed(futures):
                ok[futures[f]] = bool(f.result())
                done += 1
                if done % 5 == 0 or done == len(chans):
                    _update(data_dir, x["id"], progress={"done": done, "total": len(chans)})
        before = set(x.get("imported") or [])
        good = dupes = 0
        for n, (c, works) in enumerate(zip(chans, ok)):
            cid = c["id"] or f"own-{x['id']}-{n}"
            if not works or cid in seen:
                continue
            seen.add(cid)
            good += 1
            if cid not in before and (c["url"] in known_urls or _key(c["name"]) in known_names):
                dupes += 1
                newly_hidden.add(cid)  # already in Live TV: in, but inactive, once
            known_urls.add(c["url"])
            known_names.add(_key(c["name"]))
            line = livetv._entry(cid, c, 30000 + len(entries), f"{x['name']} · {c['group'] or 'Other'}", c["url"])
            entries.append(line.replace("#EXTINF:-1 ", f'#EXTINF:-1 starboard-src="{x["id"]}" ', 1))
        failed = [c["url"] for c, works in zip(chans, ok) if not works]
        reasons = {}
        if failed:
            with cf.ThreadPoolExecutor(8) as ex:
                for r in ex.map(why or _why, failed[:30]):
                    reasons[r] = reasons.get(r, 0) + 1
        text = []
        if dupes:
            text.append(f"{dupes} {'is' if dupes == 1 else 'are'} already in Live TV, so {'it came' if dupes == 1 else 'they came'} in inactive: activate {'it' if dupes == 1 else 'them'} in Channels when you want")
        for r, k in sorted(reasons.items(), key=lambda kv: -kv[1]):
            one = re.sub(r"^do not", "does not", re.sub(r"^(answer|refuse)\b", r"\1s", r))
            text.append(f"{k} {'address' if k == 1 else 'addresses'} {one if k == 1 else r}")
        if skipped:
            text.append(f"{len(skipped)} {'is a Kodi add-on link' if len(skipped) == 1 else 'are Kodi add-on links'} (plugin://), which Jellyfin cannot play"
                        if all(u.startswith("plugin://") for u in skipped) else f"{len(skipped)} are not web addresses, which Jellyfin cannot play")
        _update(data_dir, x["id"], said=f"{good} of {total} channels play", state="ok" if good else "warning", progress=None,
                imported=sorted(before | {c["id"] or f"own-{x['id']}-{n}" for n, c in enumerate(chans)}),
                result={"added": good - dupes, "inactive": dupes, "total": total, "text": ". ".join(text)})
    if newly_hidden:
        livetv.save_hidden(data_dir, hidden | newly_hidden)
    livetv._write(os.path.join(d, PLAYLIST), "\n".join(["#EXTM3U"] + entries) + "\n")
    return f"Your lists: {len(entries)} channels" + ("; " + guide(d, data_dir) if seen else "")


def _guide_names(url):
    """{name key: guide channel id} from a guide's channels, read a piece at a time, stopping at the programmes."""
    out = {}
    for _, el in livetv._guide_events(url):
        if el.tag == "programme":
            break
        if el.tag == "channel" and el.get("id"):
            for dn in el.findall("display-name"):
                out.setdefault(_key(dn.text or ""), el.get("id"))
    return out


def guide(d, data_dir):
    """guide-own.xml from every active guide: ones added on their own, and each list's own guide (DASH-359). A list's
    guide fills that list's channels by channel id or, failing that, by name: the channel takes the guide's id."""
    items = sources(data_dir)
    path = os.path.join(d, PLAYLIST)
    chans = livetv._parse(path) if os.path.exists(path) else []
    renamed = False
    for x in items:
        if x.get("kind") == "list" and x.get("on", True) and x.get("guide"):
            try:
                names = _guide_names(local_path(data_dir, x["guide"]) or x["guide"])
            except Exception:  # said on the list's row; the rest go on
                x["guide_said"] = "The guide could not be read"
                continue
            ids = set(names.values())
            for c in chans:
                if c["attrs"].get("starboard-src") == x["id"] and c["attrs"].get("tvg-id") not in ids and _key(c["name"]) in names:
                    c["attrs"]["tvg-id"] = names[_key(c["name"])]
                    renamed = True
    if renamed:
        lines = ["#EXTM3U"]
        for c in chans:
            lines += ["#EXTINF:-1 " + " ".join(f'{k}="{v}"' for k, v in c["attrs"].items()) + f",{c['name']}", c["url"]]
        livetv._write(path, "\n".join(lines) + "\n")
    urls = [local_path(data_dir, x["url"]) or x["url"] for x in items if x.get("on", True) and x.get("kind") == "guide"]
    urls += [local_path(data_dir, x["guide"]) or x["guide"] for x in items if x.get("on", True) and x.get("kind") == "list" and x.get("guide")]
    ids = livetv._ids_in(path)
    if not urls or not ids:
        livetv._write(os.path.join(d, GUIDE), '<?xml version="1.0" encoding="utf-8"?>\n<tv generator-info-name="Starboard"></tv>\n')
        save(data_dir, items)
        return "your guides: none active"
    count = livetv._filtered_guide(list(dict.fromkeys(urls)), ids, os.path.join(d, GUIDE))
    with_prog = livetv._ids_with_programmes(os.path.join(d, GUIDE))
    for x in items:
        if x.get("kind") == "list" and x.get("guide"):
            mine = [c for c in chans if c["attrs"].get("starboard-src") == x["id"]]
            x["guide_said"] = f"{sum(1 for c in mine if c['attrs'].get('tvg-id') in with_prog)} of {len(mine)} channels have programmes"
    save(data_dir, items)
    return f"your guides: {count} programmes"


def _update(data_dir, sid, **values):
    """Changes one source's record (its progress, result and notes); None removes a value."""
    items = sources(data_dir)
    for x in items:
        if x["id"] == sid:
            for k, v in values.items():
                if v is None:
                    x.pop(k, None)
                else:
                    x[k] = v
    save(data_dir, items)


def set_guide(data_dir, sid, url, fetch=None):
    """A guide for one channel list (owner, 13 November 2026: "a button on each added channel list, a way to add an
    EPG feed for it"): an address, checked to be a guide."""
    url = url.strip()
    if not url.startswith("file:") and (not livetv._clean_url(url) or url != livetv._clean_url(url)):
        raise ValueError("Type a web address starting http:// or https://")
    x = next((x for x in sources(data_dir) if x["id"] == sid and x.get("kind") == "list"), None)
    if not x:
        raise ValueError("Not one of your channel lists")
    kind, _ = read(url, fetch, data_dir)
    if kind != "guide":
        raise ValueError("That is not an XMLTV guide")
    if x.get("guide", "").startswith("file:") and x["guide"] != url:
        forget(data_dir, {"url": x["guide"]})
    _update(data_dir, sid, guide=url, guide_said="Added: its programmes arrive in a few minutes")
    return x["name"]


def set_guide_file(data_dir, sid, filename, stream, length):
    """A guide file for one channel list, kept beside the uploaded lists."""
    if not any(x["id"] == sid and x.get("kind") == "list" for x in sources(data_dir)):
        raise ValueError("Not one of your channel lists")
    if not 0 < length <= MAX_UPLOAD:
        raise ValueError("Choose a file up to 60 MB (a large guide can be packed as .xml.gz)")
    os.makedirs(os.path.join(data_dir, FILES), exist_ok=True)
    digest, left, tmp = hashlib.sha256(), length, os.path.join(data_dir, FILES, ".upload")
    with open(tmp, "wb") as f:
        while left:
            chunk = stream.read(min(1 << 20, left))
            if not chunk:
                break
            f.write(chunk)
            digest.update(chunk)
            left -= len(chunk)
    if left:
        os.remove(tmp)
        raise ValueError("The upload stopped before the end")
    stored = os.path.join(data_dir, FILES, digest.hexdigest()[:10] + (".gz" if str(filename).lower().endswith(".gz") else ".file"))
    os.replace(tmp, stored)
    try:
        return set_guide(data_dir, sid, f"file:{os.path.basename(stored)}")
    except Exception:
        os.remove(stored)
        raise


def remove_guide(data_dir, sid):
    x = next((x for x in sources(data_dir) if x["id"] == sid), None)
    if not x or not x.get("guide"):
        raise ValueError("That list has no guide")
    if x["guide"].startswith("file:"):
        forget(data_dir, {"url": x["guide"]})
    _update(data_dir, sid, guide=None, guide_said=None)
    return x["name"]


def notices(data_dir):
    """The screen's notices (DASH-359): a list being added, with how far its test has got, then what came of it,
    until it is closed."""
    out = []
    for x in sources(data_dir):
        p, r = x.get("progress"), x.get("result")
        if p:
            pct = int(100 * p["done"] / p["total"]) if p.get("total") else 0
            out.append({"id": x["id"], "tone": "warning", "progress": pct,
                        "title": f"Adding {x['name']}: {p['done']} of {p['total']} channels tested",
                        "text": "Each channel is tried before it goes into Jellyfin, which takes a few minutes. Channels that do not play are left out. You can leave this page; it carries on."})
        elif r and not x.get("seen_result"):
            added, total = r.get("added", 0), r.get("total", 0)
            n = added + r.get("inactive", 0)
            out.append({"id": x["id"], "dismiss": True, "tone": "success" if added else "warning" if n else "danger",
                        "title": f"{x['name']}: {added} of {total} channels added" + (f", {r['inactive']} inactive" if r.get("inactive") else ""),
                        "text": (r.get("text") or "Every channel plays.") + ("." if r.get("text") and not r["text"].endswith(".") else "")})
    return out[:5]


def dismiss(data_dir, sid):
    _update(data_dir, sid, seen_result=True)


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
