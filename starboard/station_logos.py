"""Radio station logos (owner, 12 November 2026): the owner's own logo files, kept in data/library/station-logos/
(never shipped with Starboard: each logo belongs to its broadcaster). Each station in the Library is matched to a
file by its name, allowing for the short forms file names use ("BBC-Radio-Brist" is BBC Radio Bristol, "R" is
Radio), and the match and the logo's tone (light, dark or solid, measured once by a browser) are kept in
station-logos.json so no logo is matched or measured twice.

A zip of logos can be added from Settings, Radio: only PNG, JPEG and WebP pictures are taken, 2 MB each at most,
1,000 at most, and nothing outside the folder."""
import io
import json
import os
import re
import threading
import unicodedata
import zipfile

PICTURES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
MAX_FILE, MAX_FILES = 2 * 1024 * 1024, 1000
TONES = ("light", "dark", "solid")
_lock = threading.Lock()

# Short forms in logo file names, as whole words (lower case).
WORDS = {"r": "radio", "rad": "radio", "r1": "radio 1", "r2": "radio 2", "r3": "radio 3", "r4": "radio 4", "r5": "radio 5",
         "r5sportextra": "radio 5 sports extra", "rc": "radio cymru", "rng": "radio nan gaidheal", "3cr": "three counties radio",
         "cwr": "coventry and warwickshire", "h": "hereford", "w": "worcester", "brist": "bristol", "cambs": "cambridgeshire",
         "glos": "gloucestershire", "lancs": "lancashire", "leics": "leicester", "lincs": "lincolnshire", "manc": "manchester",
         "mersey": "merseyside", "newc": "newcastle", "norfk": "norfolk", "nottm": "nottingham", "sheff": "sheffield",
         "shrop": "shropshire", "wilt": "wiltshire", "berks": "berkshire", "solend": "solent dorset", "4extra": "4 extra",
         "1xtra": "1xtra", "asiannetwork": "asian network", "worldservice": "world service", "lpool": "liverpool",
         "est": "east", "mids": "midlands", "ne": "north east", "nw": "north west", "s": "south", "n": "north",
         "yorkshre": "yorkshire", "ghr": "greatest hits radio", "xmas": "christmas"}


def folder(data_dir):
    return os.path.join(data_dir, "library", "station-logos")


def _index_path(data_dir):
    return os.path.join(data_dir, "library", "station-logos.json")


def _read(data_dir):
    try:
        with open(_index_path(data_dir), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data_dir, data):
    os.makedirs(os.path.dirname(_index_path(data_dir)), exist_ok=True)
    tmp = _index_path(data_dir) + ".new"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, _index_path(data_dir))


def _fold(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.replace("&", " and "))).strip()


def key_of_station(name):
    """A station's name as one key: "BBC Radio 4 Extra" -> "bbcradio4extra"."""
    return _fold(name).replace(" ", "")


def key_of_file(filename):
    """A logo file's name as one key, its short forms written out: "BBC-Radio-Brist.png" -> "bbcradiobristol"."""
    base = os.path.splitext(os.path.basename(filename))[0]
    words = [WORDS.get(w, w) for w in _fold(base.replace("-", " ").replace("_", " ")).split()]
    return "".join(words).replace(" ", "")


def files(data_dir):
    try:
        return sorted(f for f in os.listdir(folder(data_dir)) if os.path.splitext(f)[1].lower() in PICTURES)
    except OSError:
        return []


def match(name, names):
    """The best logo file for a station name, or "". Exact first, then without the word "radio", then a file name
    cut short ("bbcradiobrist" for "bbcradiobristol"), the longest that fits."""
    want = key_of_station(name).replace("and", "")
    if not want:
        return ""
    keys = [(key_of_file(f).replace("and", ""), f) for f in names]
    for k, f in keys:
        if k == want:
            return f
    for k, f in keys:  # a national station whose file says so: "LBC" is LBC-UK
        if k == want + "uk":
            return f
    bare = want.replace("radio", "")
    for k, f in keys:
        if k.replace("radio", "") == bare:
            return f
    cut = [(k, f) for k, f in keys if len(k) >= 8 and want.startswith(k) and not want[len(k):][:1].isdigit()
           and len(k) >= 0.75 * len(want)]
    return max(cut, key=lambda kf: len(kf[0]))[1] if cut else ""


def logo_of(data_dir, name):
    """{"file", "tone"} for a station, matched once and kept; {} when there is no logo for it."""
    k = key_of_station(name)
    with _lock:
        data = _read(data_dir)
        entry = data.get(k)
        names = files(data_dir)
        if entry is None or (entry.get("file") and entry["file"] not in names):
            entry = {"file": match(name, names)}
            data[k] = entry
            _save(data_dir, data)
    return entry if entry.get("file") else {}


def picture(data_dir, name):
    """(bytes, type) of a station's logo, or None."""
    entry = logo_of(data_dir, name)
    if not entry:
        return None
    path = os.path.join(folder(data_dir), entry["file"])
    try:
        with open(path, "rb") as f:
            return f.read(MAX_FILE), PICTURES[os.path.splitext(path)[1].lower()]
    except (OSError, KeyError):
        return None


def set_tone(data_dir, name, tone):
    if tone not in TONES:
        raise ValueError("A tone is light, dark or solid")
    k = key_of_station(name)
    with _lock:
        data = _read(data_dir)
        if not (data.get(k) or {}).get("file"):
            raise LookupError("No logo for that station")
        data[k] = {**data[k], "tone": tone}
        _save(data_dir, data)


def add_zip(data_dir, raw):
    """Takes the pictures from a zip of logos (later files with the same name replace earlier ones), then matches
    again. Returns how many pictures were added and how many files were left out."""
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        raise ValueError("That is not a zip file") from None
    os.makedirs(folder(data_dir), exist_ok=True)
    added = skipped = 0
    for info in z.infolist()[: MAX_FILES * 2]:
        if info.is_dir():
            continue
        name = os.path.basename(info.filename)
        ext = os.path.splitext(name)[1].lower()
        if ext not in PICTURES or not re.match(r"^[\w .()&+'-]{1,120}$", name) or info.file_size > MAX_FILE or added >= MAX_FILES:
            skipped += 1
            continue
        data = z.read(info)
        if not (data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff" or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")):
            skipped += 1
            continue
        with open(os.path.join(folder(data_dir), name), "wb") as f:
            f.write(data)
        added += 1
    with _lock:
        _save(data_dir, {})  # match every station again against the new set
    return {"added": added, "skipped": skipped, "total": len(files(data_dir))}


def summary(data_dir, stations):
    """For Settings, Radio: how many logos there are, and which stations have none."""
    names = files(data_dir)
    missing = [s for s in stations if not logo_of(data_dir, s)]
    return {"logos": len(names), "stations": len(stations), "matched": len(stations) - len(missing), "missing": missing}
