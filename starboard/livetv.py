"""Live TV for Jellyfin: free channel playlists, their TV guides, Sky-style numbering and each channel's own logo.

Optional (Settings, Apps, Jellyfin, Live TV; off until turned on). Works in the folder Jellyfin reads its Live TV
files from (STARBOARD_IPTV_DIR, which the installer asks about). The guides are refreshed once a day, because
listings only cover the next few days. The channel lists are rebuilt (and every stream tested, the costly part)
only when a source's list of channels has changed, or once a week to drop channels that stopped playing:
  guide.xml          the guide for the channel IDs listed in guide-map.txt, from epgshare01
  channels.m3u       Free-TV channels from freetv-source.m3u, keeping only the ones that play from here
  samsung.m3u, guide-samsung.xml   Samsung TV Plus UK and US, from i.mjh.nz (Matt Huisman)
  pluto.m3u, guide-pluto.xml       Pluto TV UK; streams go through Starboard, which keeps a Pluto session
Then it numbers every channel by Sky's categories (101 Entertainment, 401 Lifestyle, 451 Movies, 501 Music,
601 Sport, 701 News, 801 Documentaries, 1001 Kids, 1101 Other), each with its own logo in its own colours (white
logos were removed on 20 November 2026). Skipped on purpose: DRM and adult channels, and anything that does not play from this connection.
"""

import concurrent.futures as cf
import gzip
import io
import json
import os
import re
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid

from . import outside

RAW = "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master"
GUIDES = [
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz",
]
ADULT = ("erotica", "adult", "xxx", "playboy")
SAMSUNG_UA = "okhttp/4.12.0"
FILES = ["channels.m3u", "samsung.m3u", "pluto.m3u", "own.m3u"]  # Free-TV first, so its channels lead each block; own.m3u: the owner's own lists (livetv_own.py)
BLOCKS = [("Entertainment", 101), ("Lifestyle", 401), ("Movies", 451), ("Music", 501), ("Sport", 601),
          ("News", 701), ("Documentaries", 801), ("Kids", 1001), ("Other", 1101)]
TVL = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries"
# Better sources for logos whose original is region-blocked.
LOGO_OVERRIDES = {"CNN": f"{TVL}/united-states/cnn-us.png", "ABC News": f"{TVL}/united-states/abc-news-live-us.png",
                  "CBS News": f"{TVL}/united-states/cbs-news-24-7-us.png", "NBC News": f"{TVL}/united-states/nbc-news-now-us.png",
                  "Pop": f"{TVL}/united-kingdom/pop-uk.png",
                  "WeatherNation": f"{TVL}/united-states/weathernation-us.png", "Drybar Comedy": "", "Bloomberg": ""}
FREE_TV = {"CBBC": "Kids", "CBeebies": "Kids", "Pop": "Kids", "BBC News": "News", "GB News": "News", "CNN": "News",
           "ABC News": "News", "CBS News": "News", "NBC News": "News", "FOX Live Now": "News", "Bloomberg": "News",
           "WeatherNation": "News", "Great! Movies": "Movies", "True Crime": "Documentaries"}
DAY = 20 * 3600  # "older than a day", with room for the hourly check
RETRY = 12 * 3600  # a guide that failed is tried again after this, not every hour


def _et():
    """The XML parser, loaded only when a guide is built (it is not needed the rest of the time)."""
    import xml.etree.ElementTree as ET
    return ET


def folder():
    return os.environ.get("STARBOARD_IPTV_DIR", "")


MAX_DOWNLOAD = 200 * 1024 * 1024  # a guide is about 30 MB; anything far bigger is refused
MAX_UNPACKED = 600 * 1024 * 1024


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Keep Live TV downloads inside the same outbound-address policy as configured apps."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        outside.check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_url(url, headers=None, timeout=120):
    """Open a web URL only after checking its resolved address and every HTTP redirect."""
    outside.check_url(url)
    request = urllib.request.Request(url, headers=headers or {})
    return urllib.request.build_opener(_SafeRedirect()).open(request, timeout=timeout)


def fetch(url, ua="Starboard", timeout=120, limit=MAX_DOWNLOAD):
    """Downloads an http(s) address, refusing unsafe destinations, redirects and oversized responses."""
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("Only http and https addresses")
    with _open_url(url, {"User-Agent": ua}, timeout=timeout) as r:  # checked above and on redirects  # nosec B310
        data = r.read(limit + 1)
    if len(data) > limit:
        raise ValueError("The download is too large")
    return data


def _gunzip(data):
    """Unpacks gzip data, stopping at MAX_UNPACKED (a small file that unpacks to gigabytes is refused)."""
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as g:
        out = g.read(MAX_UNPACKED + 1)
    if len(out) > MAX_UNPACKED:
        raise ValueError("The file unpacks to too much")
    return out


class _Capped(io.RawIOBase):
    """Reads an unpacking guide a piece at a time: the first piece was already read to check it, and the whole
    file may not unpack to more than MAX_UNPACKED."""
    def __init__(self, head, rest):
        self.head, self.rest, self.total = head, rest, len(head)

    def readable(self):
        return True

    def readinto(self, buf):
        if self.head:
            n = min(len(buf), len(self.head))
            buf[:n], self.head = self.head[:n], self.head[n:]
            return n
        data = self.rest.read(len(buf))
        self.total += len(data)
        if self.total > MAX_UNPACKED:
            raise ValueError("The file unpacks to too much")
        buf[:len(data)] = data
        return len(data)


def _check_head(head):
    """A guide may start with a DOCTYPE line, as Samsung TV Plus and Pluto TV do, but may not define entities: no
    entities, so no entity bombs. Entities can only be defined before the guide's first element, at the start."""
    if b"<!ENTITY" in head:
        raise ValueError("The guide defines entities, which Starboard does not accept")


def _guide_events(url, timeout=300):
    """Downloads a gzip'd XMLTV guide to a temporary file and parses it while it unpacks, so neither the download
    nor the unpacked guide is held in memory (a 147 MB guide peaked at about 213 MB before, about 30 MB now).
    The file goes away when parsing ends. `url` can also be an uploaded guide's stored copy, an absolute path that
    only livetv_own passes; and a guide that is not packed is read as it is (DASH-359)."""
    local = url.startswith("/")
    if not local and not url.lower().startswith(("https://", "http://")):
        raise ValueError("Only http and https addresses")
    tmp = open(url, "rb") if local else tempfile.TemporaryFile()  # noqa: SIM115  (closed below)
    try:
        if not local:
            with _open_url(url, {"User-Agent": "Starboard"}, timeout=timeout) as r:  # checked to be http(s) above  # nosec B310
                copied = 0
                while True:
                    chunk = r.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > MAX_DOWNLOAD:
                        raise ValueError("The download is too large")
                    tmp.write(chunk)
        tmp.seek(0)
        packed = tmp.read(2) == b"\x1f\x8b"
        tmp.seek(0)
        g = gzip.GzipFile(fileobj=tmp) if packed else tmp
        head = g.read(65536)
        _check_head(head)
        events = _et().iterparse(io.BufferedReader(_Capped(head, g), 1024 * 1024), events=("start", "end"))
        _, root = next(events)
        depth = 1
        for event, el in events:
            if event == "start":
                depth += 1
                continue
            depth -= 1
            yield event, el
            if depth == 1:
                root.remove(el)  # a finished channel or programme: the caller kept it or let it go, so the tree stays small
    finally:
        tmp.close()


def _clean(text, limit=200):
    """Text that goes into a playlist line: no line breaks, control characters or double quotes."""
    return re.sub(r'[\x00-\x1f\x7f"]', "", str(text or ""))[:limit]


def _clean_url(url):
    url = _clean(url, 600)
    return url if url.lower().startswith(("https://", "http://")) else ""


def _write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def _old(path):
    return not os.path.exists(path) or time.time() - os.path.getmtime(path) > DAY


AHEAD = 12 * 3600  # a guide with less than this still to come is fetched again (Samsung's covers about ten hours)
_STOP = re.compile(rb'stop="(\d{14})(?: ?([+-])(\d{2})(\d{2}))?"')


def guide_end(path):
    """When the last programme in an XMLTV guide ends, as a Unix time; 0 when there is none or no file. Read a piece
    at a time, so a guide of several MB is never held in memory."""
    import calendar
    last = 0
    try:
        with open(path, "rb") as f:
            tail = b""
            while True:
                piece = f.read(1 << 20)
                if not piece:
                    break
                text = tail + piece
                for m in _STOP.finditer(text):
                    t = calendar.timegm(time.strptime(m.group(1).decode(), "%Y%m%d%H%M%S"))
                    if m.group(2):
                        t -= (1 if m.group(2) == b"+" else -1) * (int(m.group(3)) * 3600 + int(m.group(4)) * 60)
                    last = max(last, t)
                tail = text[-64:]
    except (OSError, ValueError):
        return 0
    return last


def _short(path, now=None):
    """True when the guide has less than AHEAD still to come."""
    return guide_end(path) < (now or time.time()) + AHEAD


# Checks and building blocks ---------------------------------------------------------------

def adult(v):
    text = f"{v.get('name', '')} {v.get('group', '')}".lower()
    return any(w in text for w in ADULT)


def plays(url, ua):
    """A stream plays when its playlist, a quality variant and that variant's first video segment all load."""
    if not str(url).lower().startswith(("https://", "http://")):
        return False
    try:
        with _open_url(url, {"User-Agent": ua}, timeout=15) as r:  # checked to be http(s) above  # nosec B310
            base, text = r.url, r.read(200000).decode("utf-8", "replace")
        if "#EXTM3U" not in text:
            return False
        lines = [line.strip() for line in text.splitlines()]
        variants = [lines[i + 1] for i, line in enumerate(lines[:-1]) if line.startswith("#EXT-X-STREAM-INF")]
        for v in (variants[:2] or [None]):
            if v:
                v = urllib.parse.urljoin(base, v)
                if not v.lower().startswith(("https://", "http://")):  # a playlist line from the internet: never a file
                    return False
                with _open_url(v, {"User-Agent": ua}, timeout=15) as r:  # checked to be http(s) above  # nosec B310
                    vbase, vtext = r.url, r.read(200000).decode("utf-8", "replace")
            else:
                vbase, vtext = base, text
            segments = [line.strip() for line in vtext.splitlines() if line.strip() and not line.startswith("#")]
            if not segments:
                continue
            segment = urllib.parse.urljoin(vbase, segments[-1])
            if not segment.lower().startswith(("https://", "http://")):
                return False
            with _open_url(segment, {"User-Agent": ua, "Range": "bytes=0-2047"}, timeout=15) as r:  # checked to be http(s) above  # nosec B310
                if r.status in (200, 206) and r.read(2048):
                    return True
        return False
    except Exception:  # a channel that fails in any way is left out today
        return False


def _entry(cid, v, chno, group, url):
    """One playlist entry. Everything from the channel lists is cleaned, so it cannot add lines of its own."""
    name = _clean(str(v.get("name", "")).replace('"', "'"))
    return (f'#EXTINF:-1 tvg-id="{_clean(cid, 80)}" tvg-name="{name}" tvg-logo="{_clean_url(v.get("logo", ""))}" '
            f'tvg-chno="{int(chno)}" group-title="{_clean(group)}",{name}\n{_clean_url(url)}')


def _filtered_guide(sources, ids, out):
    ET = _et()
    root = ET.Element("tv", {"generator-info-name": "Starboard"})
    keep = []
    for url in sources:
        for _, el in _guide_events(url):
            if el.tag in ("channel", "programme") and (el.get("id") if el.tag == "channel" else el.get("channel")) in ids:
                keep.append(el)
            elif el.tag in ("channel", "programme"):
                el.clear()
    root.extend(sorted(keep, key=lambda e: e.tag != "channel"))
    tmp = out + ".tmp"
    ET.ElementTree(root).write(tmp, encoding="utf-8", xml_declaration=True)
    os.replace(tmp, out)
    return sum(e.tag == "programme" for e in keep)


def _channels_json(service):
    return json.loads(_gunzip(fetch(f"{RAW}/{service}/.channels.json.gz")))


# The playlists and guides -----------------------------------------------------------------

def build_guide(d):
    path = os.path.join(d, "guide-map.txt")
    if not os.path.exists(path):
        return "No guide-map.txt, so no main guide"
    with open(path, encoding="utf-8") as f:
        wanted = {line.strip() for line in f if line.strip()}
    ET = _et()
    root = ET.Element("tv", {"generator-info-name": "Starboard (from epgshare01)"})
    channels, programmes, seen = [], [], set()
    for url in GUIDES:
        for _, el in _guide_events(url):
            if el.tag == "channel" and el.get("id") in wanted and el.get("id") not in seen:
                seen.add(el.get("id"))
                channels.append(el)
            elif el.tag == "programme" and el.get("channel") in wanted:
                programmes.append(el)
            elif el.tag in ("channel", "programme"):
                el.clear()
    root.extend(channels + programmes)
    out = os.path.join(d, "guide.xml")
    ET.ElementTree(root).write(out + ".tmp", encoding="utf-8", xml_declaration=True)
    os.replace(out + ".tmp", out)
    return f"Guide: {len(channels)} channels, {len(programmes)} programmes"


def build_freetv(d):
    src_path = os.path.join(d, "freetv-source.m3u")
    if not os.path.exists(src_path):
        return "No freetv-source.m3u, so no Free-TV channels"
    with open(src_path, encoding="utf-8") as f:
        src = f.read().splitlines()
    pairs = [(src[i], src[i + 1]) for i, line in enumerate(src[:-1]) if line.startswith("#EXTINF")]
    with cf.ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(lambda p: plays(p[1], "Lavf/60.16.100"), pairs))
    keep = [p for p, good in zip(pairs, ok) if good]
    _write(os.path.join(d, "channels.m3u"), "\n".join(["#EXTM3U"] + [line for p in keep for line in p]) + "\n")
    return f"Free-TV: {len(keep)} of {len(pairs)} play"


def _samsung_channels(data):
    return {region: {k: v for k, v in data["regions"][region]["channels"].items() if not v.get("license_url") and not adult(v)}
            for region in ("gb", "us")}


def _ids_in(path):
    try:
        with open(path, encoding="utf-8") as f:
            return set(re.findall(r'tvg-id="([^"]+)"', f.read()))
    except OSError:
        return set()


def _ids_with_programmes(path):
    """The channel ids a written guide has programmes for (a filtered guide, small enough to read in one go)."""
    try:
        with open(path, encoding="utf-8") as f:
            return set(re.findall(r'<programme[^>]*\bchannel="([^"]+)"', f.read()))
    except OSError:
        return set()


def samsung_guide(d):
    ids = _ids_in(os.path.join(d, "samsung.m3u"))
    p = _filtered_guide(["https://i.mjh.nz/SamsungTVPlus/gb.xml.gz", "https://i.mjh.nz/SamsungTVPlus/us.xml.gz"], ids,
                        os.path.join(d, "guide-samsung.xml"))
    return f"Samsung TV Plus guide: {p} programmes"


def pluto_guide(d):
    ids = _ids_in(os.path.join(d, "pluto.m3u"))
    p = _filtered_guide(["https://i.mjh.nz/PlutoTV/gb.xml.gz"], ids, os.path.join(d, "guide-pluto.xml"))
    return f"Pluto TV guide: {p} programmes"


def build_samsung(d, data=None):
    data = data or _channels_json("SamsungTVPlus")
    lines, ids = ["#EXTM3U"], set()
    for region, offset, label in (("gb", 0, "Samsung UK"), ("us", 10000, "Samsung US")):
        chans = {k: v for k, v in data["regions"][region]["channels"].items() if not v.get("license_url") and not adult(v)}
        with cf.ThreadPoolExecutor(16) as ex:
            ok = dict(zip(chans, ex.map(lambda k: plays(f"https://jmp2.uk/stvp-{k}", SAMSUNG_UA), chans)))
        for k, v in sorted(chans.items(), key=lambda kv: kv[1]["chno"]):
            if ok[k]:
                lines.append(_entry(k, v, v["chno"] + offset, f"{label} · {v.get('group', 'Other')}", f"https://jmp2.uk/stvp-{k}"))
                ids.add(k)
    _write(os.path.join(d, "samsung.m3u"), "\n".join(lines) + "\n")
    p = _filtered_guide(["https://i.mjh.nz/SamsungTVPlus/gb.xml.gz", "https://i.mjh.nz/SamsungTVPlus/us.xml.gz"], ids,
                        os.path.join(d, "guide-samsung.xml"))
    return f"Samsung TV Plus: {len(ids)} channels, {p} programmes"


def build_pluto(d, self_url, data=None):
    data = data or _channels_json("PlutoTV")
    chans = {k: v for k, v in data["regions"]["gb"]["channels"].items() if not adult(v)}
    lines = ["#EXTM3U"] + [_entry(k, v, v["chno"] + 20000, f"Pluto UK · {v.get('group', 'Other')}", f"{self_url}/iptv/pluto/{k}.m3u8")
                           for k, v in sorted(chans.items(), key=lambda kv: kv[1]["chno"])]
    _write(os.path.join(d, "pluto.m3u"), "\n".join(lines) + "\n")
    p = _filtered_guide(["https://i.mjh.nz/PlutoTV/gb.xml.gz"], set(chans), os.path.join(d, "guide-pluto.xml"))
    return f"Pluto TV: {len(chans)} channels, {p} programmes"


# Pluto: one session for every channel, renewed before it runs out --------------------------------

_pluto = {"exp": 0}
_pluto_lock = threading.Lock()


def pluto_url(channel_id):
    if not re.match(r"^[A-Za-z0-9]{8,40}$", channel_id or ""):
        raise ValueError("Not a Pluto channel")
    with _pluto_lock:
        if time.time() > _pluto["exp"]:
            q = urllib.parse.urlencode({"appName": "web", "appVersion": "9.1.2", "deviceVersion": "122.0.0",
                                        "deviceModel": "web", "deviceMake": "chrome", "deviceType": "web",
                                        "clientID": str(uuid.uuid4()), "clientModelNumber": "1.0.0",
                                        "serverSideAds": "false", "drmCapabilities": ""})
            b = json.loads(fetch(f"https://boot.pluto.tv/v4/start?{q}", ua="Mozilla/5.0", timeout=20, limit=1_000_000))
            stitcher = str(b["servers"]["stitcher"]).rstrip("/")
            if not re.match(r"^https://[a-z0-9.-]+\.pluto\.tv$", stitcher):
                raise ValueError("Pluto sent an unexpected stream server")
            _pluto.update(stitcher=stitcher, params=b["stitcherParams"], jwt=b["sessionToken"],
                          exp=time.time() + int(b.get("refreshInSec", 3600)) - 600)
        return (f'{_pluto["stitcher"]}/v2/stitch/hls/channel/{channel_id}/master.m3u8?{_pluto["params"]}'
                f'&jwt={_pluto["jwt"]}&masterJWTPassthrough=true')


# Numbering and logos ------------------------------------------------------------------------

def category(name, group):
    if name in FREE_TV:
        return FREE_TV[name]
    g = group.lower()
    for words, cat in ((("news", "opinion", "weather"), "News"), (("sport", "motor"), "Sport"), (("movie",), "Movies"),
                       (("kids",), "Kids"), (("documentar", "nature", "history", "science", "real life", "true crime"), "Documentaries"),
                       (("food", "travel", "home", "living", "lifestyle"), "Lifestyle"), (("music",), "Music"),
                       (("latino", "anime", "ambian"), "Other")):
        if any(w in g for w in words):
            return cat
    return "Entertainment"


def _parse(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF") and i + 1 < len(lines):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            out.append({"attrs": attrs, "name": line.rsplit(",", 1)[1], "url": lines[i + 1], "file": path})
    return out


def logo_key(ch):
    return re.sub(r"[^A-Za-z0-9._-]", "_", ch["attrs"].get("tvg-id") or ch["name"])[:80]


HIDDEN = "hidden-channels.json"  # in the plug-in's own data folder (DASH-313)
ALL = ".starboard-channels.json"  # every channel found, hidden ones too, so one can be turned back on


def hidden_ids(data_dir):
    try:
        with open(os.path.join(data_dir, HIDDEN), encoding="utf-8") as f:
            got = json.load(f)
        return {str(h["id"]) if isinstance(h, dict) else str(h) for h in got}
    except (OSError, ValueError, TypeError, KeyError):
        return set()


def save_hidden(data_dir, ids):
    tmp = os.path.join(data_dir, HIDDEN + ".new")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)
    os.replace(tmp, os.path.join(data_dir, HIDDEN))


# Whole lists (DASH-359, owner 12 November 2026): an inactive list is not fetched, its playlist and guide are emptied,
# so Jellyfin drops its channels, and it is built again as new when it is activated.
LISTS = {"freetv": ("Free-TV", "channels.m3u", "guide.xml"), "samsung": ("Samsung TV Plus", "samsung.m3u", "guide-samsung.xml"),
         "pluto": ("Pluto TV", "pluto.m3u", "guide-pluto.xml")}
LISTS_OFF = "lists-off.json"  # in the plug-in's own data folder


def lists_off(data_dir):
    try:
        with open(os.path.join(data_dir, LISTS_OFF), encoding="utf-8") as f:
            return {str(x) for x in json.load(f)} & set(LISTS)
    except (OSError, ValueError, TypeError):
        return set()


def save_lists_off(data_dir, names):
    tmp = os.path.join(data_dir, LISTS_OFF + ".new")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sorted(set(names) & set(LISTS)), f)
    os.replace(tmp, os.path.join(data_dir, LISTS_OFF))


def empty_list(d, name):
    """Empties one list's playlist and guide and takes its channels off the full list. Returns how many went."""
    _, playlist, guide = LISTS[name]
    _write(os.path.join(d, playlist), "#EXTM3U\n")
    _write(os.path.join(d, guide), '<?xml version="1.0" encoding="utf-8"?>\n<tv generator-info-name="Starboard"></tv>\n')
    every = all_channels(d)
    rest = [c for c in every if c.get("list") != playlist]
    _write(os.path.join(d, ALL), json.dumps(rest))
    return len(every) - len(rest)


NOW = "now.json"  # in the plug-in's data folder: the next few hours, for the On TV now card (DASH-359)


def _xmltv_time(value):
    import calendar
    m = re.match(r"(\d{14})(?: ?([+-])(\d{2})(\d{2}))?", value or "")
    if not m:
        return 0
    t = calendar.timegm(time.strptime(m.group(1), "%Y%m%d%H%M%S"))
    if m.group(2):
        t -= (1 if m.group(2) == "+" else -1) * (int(m.group(3)) * 3600 + int(m.group(4)) * 60)
    return t


def write_now(d, data_dir, before=3 * 3600, after=5 * 3600, now=None):
    """The programmes from a little before now to a few hours ahead, for every channel in Jellyfin, read from the
    written guides a piece at a time into a small file (owner, 13 November 2026: option 5, what is on now, as a
    dashboard card). Written after each run, so the card reads one small file, never the guides."""
    now = now or time.time()
    chans = {}
    for name in FILES:
        path = os.path.join(d, name)
        if os.path.exists(path):
            for c in _parse(path):
                cid = c["attrs"].get("tvg-id")
                if cid and cid not in chans:
                    chans[cid] = {"name": c["name"], "number": c["attrs"].get("tvg-chno", ""), "section": c["attrs"].get("group-title", ""),
                                  "programmes": []}
    ET = _et()
    for g in ["guide.xml", "guide-samsung.xml", "guide-pluto.xml", "guide-own.xml"]:
        path = os.path.join(d, g)
        if not os.path.exists(path):
            continue
        try:
            for _, el in ET.iterparse(path):  # the guides Starboard wrote itself  # nosec B314
                if el.tag == "programme":
                    c = chans.get(el.get("channel"))
                    start, stop = _xmltv_time(el.get("start")), _xmltv_time(el.get("stop"))
                    if c is not None and stop > now - before and start < now + after:
                        c["programmes"].append([start, stop, (el.findtext("title") or "").strip()[:120]])
                    el.clear()
                elif el.tag == "channel":
                    el.clear()
        except ET.ParseError:  # a broken guide: the others still count
            continue
    for c in chans.values():
        c["programmes"].sort()
    tmp = os.path.join(data_dir, NOW + ".new")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"written": now, "channels": chans}, f)
    os.replace(tmp, os.path.join(data_dir, NOW))
    return sum(1 for c in chans.values() if c["programmes"])


def mark_built(name, fp):
    """Records that one channel list was just built (a list just added, DASH-359), so the hourly run does not build it
    again at once."""
    d = folder()
    path = os.path.join(d, ".starboard-livetv.json")
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    state[name] = {"fp": fp, "built": time.time()}
    _write(path, json.dumps(state))


def all_channels(d):
    try:
        with open(os.path.join(d, ALL), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def drop_hidden(d, hidden):
    """Takes hidden channels out of the lists Jellyfin reads, now, without fetching anything. Returns how many."""
    gone = 0
    for name in FILES:
        path = os.path.join(d, name)
        if not os.path.exists(path):
            continue
        chans = _parse(path)
        keep = [c for c in chans if c["attrs"].get("tvg-id") not in hidden]
        if len(keep) == len(chans):
            continue
        gone += len(chans) - len(keep)
        lines = ["#EXTM3U"]
        for c in keep:
            lines += ["#EXTINF:-1 " + " ".join(f'{k}="{v}"' for k, v in c["attrs"].items()) + f",{c['name']}", c["url"]]
        _write(path, "\n".join(lines) + "\n")
    return gone


def number_and_logos(d, hidden=frozenset()):
    """Numbers every channel by category, and gives each its own logo (or a better source from LOGO_OVERRIDES)."""
    chans = []
    for name in FILES:
        if os.path.exists(os.path.join(d, name)):
            chans += _parse(os.path.join(d, name))
    for ch in chans:  # remember each channel's own logo and group, so a second run starts from them
        ch["attrs"]["tvg-logo-src"] = ch["attrs"].get("tvg-logo-src") or ch["attrs"].get("tvg-logo", "")
        ch["attrs"]["tvg-logo"] = ch["attrs"]["tvg-logo-src"]
        ch["attrs"]["group-src"] = ch["attrs"].get("group-src") or ch["attrs"].get("group-title", "")
    for ch in chans:  # each channel's own logo, in its own colours
        ch["attrs"]["tvg-logo"] = LOGO_OVERRIDES.get(ch["name"], ch["attrs"]["tvg-logo-src"])
    region = lambda c: 1 if c["attrs"]["group-src"] == "US" or c["attrs"]["group-src"].startswith("Samsung US") else 0
    for ch in chans:
        ch["cat"] = category(ch["name"], ch["attrs"]["group-src"])
    nxt = dict(BLOCKS)
    order = {c: i for i, (c, _) in enumerate(BLOCKS)}
    rank = {os.path.join(d, f): i for i, f in enumerate(FILES)}
    for ch in sorted(chans, key=lambda c: (order[c["cat"]], region(c), rank[c["file"]], int(c["attrs"].get("tvg-chno", 0) or 0))):
        ch["attrs"]["tvg-chno"] = str(nxt[ch["cat"]])
        nxt[ch["cat"]] += 1
        ch["attrs"]["group-title"] = ch["cat"]
    # Every channel, hidden ones too, for the plug-in's Channels screen (DASH-313); then the hidden ones go.
    _write(os.path.join(d, ALL), json.dumps([{"id": c["attrs"].get("tvg-id", ""), "name": c["name"], "number": c["attrs"]["tvg-chno"],
                                              "section": c["cat"], "list": os.path.basename(c["file"]),
                                              "region": "" if c["file"].endswith("own.m3u") else "US" if region(c) else "UK",
                                              "source": c["attrs"].get("starboard-src", "")} for c in chans]))
    chans = [c for c in chans if c["attrs"].get("tvg-id") not in hidden]
    for name in FILES:
        path = os.path.join(d, name)
        mine = [c for c in chans if c["file"] == path]
        if mine:
            lines = ["#EXTM3U"]
            for c in sorted(mine, key=lambda c: int(c["attrs"]["tvg-chno"])):
                lines += ["#EXTINF:-1 " + " ".join(f'{k}="{v}"' for k, v in c["attrs"].items()) + f",{c['name']}", c["url"]]
            _write(path, "\n".join(lines) + "\n")
    return f"Numbered {len(chans)} channels; {sum(1 for c in chans if c['attrs'].get('tvg-logo'))} with logos"


WEEK = 7 * 86400


def _fingerprint(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def run(self_url, force=False):
    """Refreshes what is due. Guides: daily. Channel lists: when a source's list changed, or weekly (or with force).
    Returns a sentence about what it did."""
    d = folder()
    if not d or not os.path.isdir(d):
        raise ValueError("No Live TV folder: set STARBOARD_IPTV_DIR with ./install.sh")
    state_path = os.path.join(d, ".starboard-livetv.json")
    try:
        with open(state_path, encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    now = time.time()
    done, rebuilt = [], False

    def due_list(name, fp):
        """A channel list is rebuilt when it changed, a week has passed, the playlist is missing, or with force."""
        old = state.get(name, {})
        return force or fp != old.get("fp") or now - old.get("built", 0) > WEEK or address_changed or \
            not os.path.exists(os.path.join(d, {"freetv": "channels.m3u"}.get(name, f"{name}.m3u")))

    def step(label, fn):
        try:
            done.append(fn())
            return True
        except Exception as e:  # one source failing does not stop the others
            done.append(f"{label}: {str(e)[:120]}")
            return False

    address_changed = state.get("self_url") != self_url
    failed = state.setdefault("failed", {})

    def guide_due(name, path):
        """A guide is due when it is a day old or has less than 12 hours still to come (owner, 10 November 2026:
        Samsung's covers about ten hours, so once a day left it empty by the evening), unless it failed less than
        RETRY ago (a failing source is not downloaded again every hour)."""
        return force or ((_old(path) or _short(path, now)) and now - failed.get(name, 0) > RETRY)

    def guide_step(name, label, fn):
        ok = step(label, fn)
        if ok:
            failed.pop(name, None)
        else:
            failed[name] = now
        return ok

    off = lists_off(os.environ.get("STARBOARD_DATA", "/data"))
    for name in sorted(off):  # inactive lists: emptied once, then left alone until activated
        state.pop(name, None)  # so it is built again as new when it is activated
        if any(c["file"] for c in (_parse(os.path.join(d, LISTS[name][1])) if os.path.exists(os.path.join(d, LISTS[name][1])) else [])):
            empty_list(d, name)
            done.append(f"{LISTS[name][0]}: inactive, emptied")
            rebuilt = True
    if "freetv" not in off and guide_due("guide", os.path.join(d, "guide.xml")):
        guide_step("guide", "Guide", lambda: build_guide(d))
    # Free-TV: its source is a file in the folder.
    try:
        with open(os.path.join(d, "freetv-source.m3u"), "rb") as f:
            fp = _fingerprint(f.read().decode("utf-8", "replace"))
    except OSError:
        fp = None
    if fp and "freetv" not in off and due_list("freetv", fp):
        if step("Free-TV", lambda: build_freetv(d)):
            state["freetv"] = {"fp": fp, "built": now}
            rebuilt = True
    # Samsung TV Plus and Pluto TV: their channel lists are small; fetch them only when a guide is due.
    for name, service, build, guide in (("samsung", "SamsungTVPlus", build_samsung, samsung_guide),
                                        ("pluto", "PlutoTV", lambda dd, data: build_pluto(dd, self_url, data), pluto_guide)):
        if name in off:
            continue
        due = guide_due(name, os.path.join(d, f"guide-{name}.xml"))
        if not due and not address_changed and now - state.get(name, {}).get("built", 0) <= WEEK:
            continue
        try:
            data = _channels_json(service)
        except Exception as e:  # keep yesterday's files
            done.append(f"{name}: {str(e)[:120]}")
            continue
        chans = _samsung_channels(data) if name == "samsung" else {k: v.get("name") for k, v in data["regions"]["gb"]["channels"].items() if not adult(v)}
        fp = _fingerprint({r: sorted(c) for r, c in chans.items()} if name == "samsung" else sorted(chans))
        if due_list(name, fp):
            if guide_step(name, name, lambda: build(d, data)):  # builds the playlist and its guide
                state[name] = {"fp": fp, "built": now}
                rebuilt = True
        elif due:
            guide_step(name, f"{name} guide", lambda: guide(d))
    # The owner's own lists and guides (DASH-359): built when they change, weekly, or with force; guides daily.
    from . import livetv_own
    data_dir = os.environ.get("STARBOARD_DATA", "/data")
    own_fp = livetv_own.fingerprint(data_dir)
    if livetv_own.sources(data_dir) or os.path.exists(os.path.join(d, livetv_own.PLAYLIST)):
        if due_list("own", own_fp):
            if step("Your lists", lambda: livetv_own.build(d, data_dir)):
                state["own"] = {"fp": own_fp, "built": now}
                rebuilt = True
        elif guide_due("own", os.path.join(d, livetv_own.GUIDE)):
            guide_step("own", "Your guides", lambda: livetv_own.guide(d, data_dir))
    if rebuilt:
        done.append(number_and_logos(d, hidden_ids(os.environ.get("STARBOARD_DATA", "/data"))))
    state["self_url"] = self_url
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, state_path)
    return " · ".join(done) or "Nothing due: guides cover the next 12 hours and no channel list has changed"


def logo_file(name):
    d = folder()
    if not d or not re.match(r"^[A-Za-z0-9._-]{1,80}\.png$", name):
        return None
    path = os.path.join(d, "logos", name)
    return path if os.path.isfile(path) else None
