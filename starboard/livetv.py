"""Live TV for Jellyfin: free channel playlists, their TV guides, Sky-style numbering and clean logos.

Optional (Settings, Apps, Jellyfin, Live TV; off until turned on). Works in the folder Jellyfin reads its Live TV
files from (STARBOARD_IPTV_DIR, which the installer asks about). The guides are refreshed once a day, because
listings only cover the next few days. The channel lists are rebuilt (and every stream tested, the costly part)
only when a source's list of channels has changed, or once a week to drop channels that stopped playing:
  guide.xml          the guide for the channel IDs listed in guide-map.txt, from epgshare01
  channels.m3u       Free-TV channels from freetv-source.m3u, keeping only the ones that play from here
  samsung.m3u, guide-samsung.xml   Samsung TV Plus UK and US, from i.mjh.nz (Matt Huisman)
  pluto.m3u, guide-pluto.xml       Pluto TV UK; streams go through Starboard, which keeps a Pluto session
Then it numbers every channel by Sky's categories (101 Entertainment, 401 Lifestyle, 451 Movies, 501 Music,
601 Sport, 701 News, 801 Documentaries, 1001 Kids, 1101 Other) and, if white logos are on, turns each logo
white on a transparent background with Pillow (open source; see THIRD-PARTY.md). Without Pillow, or with white
logos off, channels keep their own logos. Skipped on purpose: DRM and adult channels, and anything that does not
play from this connection.
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

RAW = "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master"
GUIDES = [
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz",
]
ADULT = ("erotica", "adult", "xxx", "playboy")
SAMSUNG_UA = "okhttp/4.12.0"
FILES = ["channels.m3u", "samsung.m3u", "pluto.m3u"]  # Free-TV first, so its channels lead each block
BLOCKS = [("Entertainment", 101), ("Lifestyle", 401), ("Movies", 451), ("Music", 501), ("Sport", 601),
          ("News", 701), ("Documentaries", 801), ("Kids", 1001), ("Other", 1101)]
TVL = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries"
# Better sources for logos whose original is region-blocked or does not whiten well.
LOGO_OVERRIDES = {"CNN": f"{TVL}/united-states/cnn-us.png", "ABC News": f"{TVL}/united-states/abc-news-live-us.png",
                  "CBS News": f"{TVL}/united-states/cbs-news-24-7-us.png", "NBC News": f"{TVL}/united-states/nbc-news-now-us.png",
                  "Pop": f"{TVL}/united-kingdom/pop-uk.png",
                  "WeatherNation": f"{TVL}/united-states/weathernation-us.png", "Drybar Comedy": "", "Bloomberg": ""}
FREE_TV = {"CBBC": "Kids", "CBeebies": "Kids", "Pop": "Kids", "BBC News": "News", "GB News": "News", "CNN": "News",
           "ABC News": "News", "CBS News": "News", "NBC News": "News", "FOX Live Now": "News", "Bloomberg": "News",
           "WeatherNation": "News", "Great! Movies": "Movies", "True Crime": "Documentaries"}
LOGO_VERSION = "v3"
DAY = 20 * 3600  # "older than a day", with room for the hourly check
RETRY = 12 * 3600  # a guide that failed is tried again after this, not every hour


def _et():
    """The XML parser, loaded only when a guide is built (it is not needed the rest of the time)."""
    import xml.etree.ElementTree as ET
    return ET


def folder():
    return os.environ.get("STARBOARD_IPTV_DIR", "")


def pillow():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


MAX_DOWNLOAD = 200 * 1024 * 1024  # a guide is about 30 MB; anything far bigger is refused
MAX_UNPACKED = 600 * 1024 * 1024


def fetch(url, ua="Starboard", timeout=120, limit=MAX_DOWNLOAD):
    """Downloads an http(s) address, refusing anything else or anything larger than the limit."""
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("Only http and https addresses")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}), timeout=timeout) as r:  # checked to be http(s) above  # nosec B310
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


def _xml_events(data):
    """Parses gzip'd XMLTV guide bytes already in memory (small files and tests)."""
    raw = _gunzip(data)
    _check_head(raw[:65536])
    return _et().iterparse(io.BytesIO(raw))


def _guide_events(url, timeout=300):
    """Downloads a gzip'd XMLTV guide to a temporary file and parses it while it unpacks, so neither the download
    nor the unpacked guide is held in memory (a 147 MB guide peaked at about 213 MB before, about 30 MB now).
    The file goes away when parsing ends."""
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("Only http and https addresses")
    tmp = tempfile.TemporaryFile()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Starboard"}), timeout=timeout) as r:  # checked to be http(s) above  # nosec B310
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
        g = gzip.GzipFile(fileobj=tmp)
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
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}), timeout=15) as r:  # checked to be http(s) above  # nosec B310
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
                with urllib.request.urlopen(urllib.request.Request(v, headers={"User-Agent": ua}), timeout=15) as r:  # checked to be http(s) above  # nosec B310
                    vbase, vtext = r.url, r.read(200000).decode("utf-8", "replace")
            else:
                vbase, vtext = base, text
            segments = [line.strip() for line in vtext.splitlines() if line.strip() and not line.startswith("#")]
            if not segments:
                continue
            segment = urllib.parse.urljoin(vbase, segments[-1])
            if not segment.lower().startswith(("https://", "http://")):
                return False
            req = urllib.request.Request(segment, headers={"User-Agent": ua, "Range": "bytes=0-2047"})
            with urllib.request.urlopen(req, timeout=15) as r:  # checked to be http(s) above  # nosec B310
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


def whiten(data):
    """A logo turned white on a transparent 400 by 225 canvas. Raises ValueError for a photo or a blank image."""
    import warnings
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 16_000_000  # a logo is small; a huge image (a decompression bomb) is refused
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        # Only the formats logos use: Pillow's rarer decoders (TIFF, FlashPix and others) are where its worst flaws
        # have been, and channel lists come from the internet.
        im = Image.open(io.BytesIO(data), formats=["PNG", "JPEG", "GIF", "WEBP", "BMP", "ICO"])
        im.load()
    im = im.convert("RGBA")
    im.thumbnail((400, 400))
    w, h = im.size
    px = im.load()
    alpha = im.getchannel("A")
    transparent = sum(1 for v in alpha.getdata() if v < 128) / (w * h)
    if transparent > 0.05:  # a transparent logo: keep its shape
        mask = alpha
        opaque = [(r, g, b) for (r, g, b, a) in im.getdata() if a > 128]
        light = sum(1 for r, g, b in opaque if min(r, g, b) > 200) / max(1, len(opaque))
        if 0.06 < light < 0.75:  # two-tone (white text in a red box): the white parts become holes
            mp, m = Image.new("L", (w, h)), None
            m = mp.load()
            for y in range(h):
                for x in range(w):
                    r, g, b, a = px[x, y]
                    m[x, y] = 0 if min(r, g, b) > 200 else a
            mask = mp
    else:  # opaque: the border colour is the background
        border = [px[x, y][:3] for x in range(w) for y in (0, h - 1)] + [px[x, y][:3] for y in range(h) for x in (0, w - 1)]
        bg = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
        mask = Image.new("L", (w, h))
        mp = mask.load()
        for y in range(h):
            for x in range(w):
                r, g, b, _ = px[x, y]
                d = max(abs(r - bg[0]), abs(g - bg[1]), abs(b - bg[2]))
                mp[x, y] = max(0, min(255, (d - 28) * 5))
    box = mask.point(lambda v: 255 if v > 24 else 0).getbbox()
    if not box:
        raise ValueError("blank logo")
    mask = mask.crop(box)
    hist = mask.histogram()
    if sum(hist[40:216]) / max(1, sum(hist[25:])) > (0.4 if transparent > 0.05 else 0.2):
        raise ValueError("a photo, not a logo")
    W, H, pad = 400, 225, 0.14
    scale = min(W * (1 - 2 * pad) / mask.width, H * (1 - 2 * pad) / mask.height)
    mask = mask.resize((max(1, int(mask.width * scale)), max(1, int(mask.height * scale))), Image.LANCZOS)
    out = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    white = Image.new("RGBA", mask.size, (255, 255, 255, 255))
    white.putalpha(mask)
    out.paste(white, ((W - mask.width) // 2, (H - mask.height) // 2), white)
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def text_logo(name):
    """The channel's name in white, for channels whose artwork is a photo or missing. Pillow's own font."""
    from PIL import Image, ImageDraw, ImageFont
    W, H = 400, 225
    out = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(out)
    name = re.split(r"[:(]| - |'powered", name, flags=re.I)[0].strip(" '")
    words, lines, size, font = name.upper().split(), [], 58, None
    for size in range(58, 20, -2):
        font = ImageFont.load_default(size)
        lines, cur = [], ""
        for wd in words:
            t = f"{cur} {wd}".strip()
            if d.textlength(t, font=font) <= W * 0.8 or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = wd
        lines.append(cur)
        if len(lines) <= 3 and all(d.textlength(line, font=font) <= W * 0.8 for line in lines):
            break
    lh = size * 1.12
    y = (H - lh * len(lines)) / 2
    for line in lines:
        d.text(((W - d.textlength(line, font=font)) / 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += lh
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _make_logo(ch, logos, white):
    """(key, whether a logo file is there). Logos already made are kept whatever the setting."""
    src = LOGO_OVERRIDES.get(ch["name"], ch["attrs"].get("tvg-logo-src", ""))
    key = logo_key(ch)
    path = os.path.join(logos, f"{key}.png")
    if "/iptv/logos/" in src:  # a logo this folder already serves (Free-TV's own list): use it as it is
        return key, os.path.exists(path)
    if os.path.exists(path) and (not white or _stamp(path) == f"{LOGO_VERSION}|{src}"):
        return key, True
    if not white:
        return key, False
    try:
        if not src:
            raise ValueError("no logo")
        png = whiten(fetch(src, ua="Mozilla/5.0", timeout=20, limit=5_000_000))
    except Exception as e:
        if "429" in str(e):  # rate limited: keep what is there, try again next time
            return key, os.path.exists(path)
        try:
            png = text_logo(ch["name"])
        except Exception:
            return key, os.path.exists(path)
    tmp = f"{path}.{threading.get_ident()}.tmp"
    with open(tmp, "wb") as f:
        f.write(png)
    os.replace(tmp, path)
    with open(path + ".src", "w", encoding="utf-8") as f:
        f.write(f"{LOGO_VERSION}|{src}")
    return key, True


def _stamp(path):
    try:
        with open(path + ".src", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def number_and_logos(d, self_url, white):
    logos = os.path.join(d, "logos")
    os.makedirs(logos, exist_ok=True)
    chans = []
    for name in FILES:
        if os.path.exists(os.path.join(d, name)):
            chans += _parse(os.path.join(d, name))
    for ch in chans:  # remember each channel's own logo and group, so a second run starts from them
        ch["attrs"]["tvg-logo-src"] = ch["attrs"].get("tvg-logo-src") or ch["attrs"].get("tvg-logo", "")
        ch["attrs"]["tvg-logo"] = ch["attrs"]["tvg-logo-src"]
        ch["attrs"]["group-src"] = ch["attrs"].get("group-src") or ch["attrs"].get("group-title", "")
    white = white and pillow()
    with cf.ThreadPoolExecutor(6) as ex:
        have = dict(ex.map(lambda c: _make_logo(c, logos, white), chans))
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
        if have.get(logo_key(ch)):
            ch["attrs"]["tvg-logo"] = f"{self_url}/iptv/logos/{logo_key(ch)}.png"
    for name in FILES:
        path = os.path.join(d, name)
        mine = [c for c in chans if c["file"] == path]
        if mine:
            lines = ["#EXTM3U"]
            for c in sorted(mine, key=lambda c: int(c["attrs"]["tvg-chno"])):
                lines += ["#EXTINF:-1 " + " ".join(f'{k}="{v}"' for k, v in c["attrs"].items()) + f",{c['name']}", c["url"]]
            _write(path, "\n".join(lines) + "\n")
    return f"Numbered {len(chans)} channels; {sum(have.values())} with logos" + ("" if white else " (white logos off)")


WEEK = 7 * 86400


def _fingerprint(obj):
    import hashlib
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def run(self_url, white, force=False):
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

    if guide_due("guide", os.path.join(d, "guide.xml")):
        guide_step("guide", "Guide", lambda: build_guide(d))
    # Free-TV: its source is a file in the folder.
    try:
        with open(os.path.join(d, "freetv-source.m3u"), "rb") as f:
            fp = _fingerprint(f.read().decode("utf-8", "replace"))
    except OSError:
        fp = None
    if fp and due_list("freetv", fp):
        if step("Free-TV", lambda: build_freetv(d)):
            state["freetv"] = {"fp": fp, "built": now}
            rebuilt = True
    # Samsung TV Plus and Pluto TV: their channel lists are small; fetch them only when a guide is due.
    for name, service, build, guide in (("samsung", "SamsungTVPlus", build_samsung, samsung_guide),
                                        ("pluto", "PlutoTV", lambda dd, data: build_pluto(dd, self_url, data), pluto_guide)):
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
    if rebuilt:
        done.append(number_and_logos(d, self_url, white))
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
