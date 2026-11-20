"""Libraries fetched the first time something needs them, instead of being carried in every image.

Pillow (about 18 MB unpacked) is needed only for Live TV's white logos, so most servers never use it. The first time
it is needed, its wheel (about 7 MB) is downloaded from the Python Package Index at the fixed address below, checked
against the SHA-256 written here, and unpacked into the data folder (<data>/pylib). Each later load checks every
unpacked file against the wheel's own list of files (RECORD), whose SHA-256 is also written here, so a file that was
changed or added in the data folder is never imported: the wheel is fetched again instead.

Without the internet, or on a processor with no ready-made wheel (32-bit Raspberry Pi), Unavailable says why, and
what needs it carries on without it.
"""
import base64
import csv
import hashlib
import importlib
import io
import os
import platform
import shutil
import sys
import sysconfig
import threading
import urllib.error
import urllib.request
import zipfile

FILES = "https://files.pythonhosted.org/packages/"
# name: what it is imported as, its version, and for each processor: (path on PyPI, wheel SHA-256, RECORD SHA-256).
# A new version: pip download the wheels, then sha256sum each and its .dist-info/RECORD.
WHEELS = {
    "pillow": {
        "label": "Pillow", "import": "PIL", "version": "13.0.0", "download": "about 7 MB",
        "x86_64": ("a8/7c/45ee28531f89ee4582967d8a17f7a26d71ca64cd902b93c269590cd60a00/pillow-13.0.0-cp312-cp312-musllinux_1_2_x86_64.whl",
                   "23edf4ec4b6f4f240e8df6e4985e9ee2ced86474632433e55fb1e2548744bf40",
                   "1f8d804e02aa69474c266b16badb93ab70fc1d59fcc921666de9f30dc110eba3"),
        "aarch64": ("26/9b/f38b7c4d8f599537e2d1a6d546cec9beef7536ff8f5c49a3f9c78179d8ac/pillow-13.0.0-cp312-cp312-musllinux_1_2_aarch64.whl",
                    "4bd024d567eca931b668978d672dba914d4b8e2628e2c3073a2ad178de8a2620",
                    "6ccbcead8d299d3bb5ea77acfdecca0d4062ae745b6e38b0662b9dca332ef3fd"),
    },
}
MAX_WHEEL = 32 * 1024 * 1024
MAX_UNPACKED = 64 * 1024 * 1024
_lock = threading.Lock()


class Unavailable(Exception):
    """Why a library cannot be used here, in words for a person."""


def _importable(name):
    try:
        importlib.import_module(WHEELS[name]["import"])
        return True
    except ImportError:
        return False


def _spec(name):
    """This Python's wheel of `name`, or None. The wheels are for Python 3.12 on musl (Alpine, as in the image)."""
    if sys.version_info[:2] != (3, 12) or "musl" not in (sysconfig.get_config_var("EXT_SUFFIX") or ""):
        return None
    return WHEELS[name].get(platform.machine())


def available(name):
    """True when `name` is here already or can be fetched for this processor. Nothing is downloaded."""
    return _spec(name) is not None or _importable(name)


def _root():
    return os.path.join(os.environ.get("STARBOARD_DATA", "/data"), "pylib")


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h


def _intact(where, record_sha):
    """True when the folder holds exactly the wheel's files, each as the wheel had it."""
    records = [os.path.join(dp, f) for dp, _, fs in os.walk(where) for f in fs if f == "RECORD" and dp.endswith(".dist-info")]
    if len(records) != 1 or _digest(records[0]).hexdigest() != record_sha:
        return False
    with open(records[0], encoding="utf-8", newline="") as f:
        listed = {row[0]: row[1] for row in csv.reader(f) if row}
    for dp, dirs, fs in os.walk(where):
        for n in dirs + fs:
            if os.path.islink(os.path.join(dp, n)):
                return False
        for n in fs:
            rel = os.path.relpath(os.path.join(dp, n), where).replace(os.sep, "/")
            want = listed.get(rel)
            if want is None:
                return False  # a file the wheel does not have: a cached .pyc, or something put there
            if want:  # RECORD lists itself with no hash
                algo, _, value = want.partition("=")
                got = base64.urlsafe_b64encode(_digest(os.path.join(dp, n)).digest()).rstrip(b"=").decode()
                if algo != "sha256" or got != value:
                    return False
    return True


def _fetch(name, spec, where):
    w = WHEELS[name]
    req = urllib.request.Request(FILES + spec[0], headers={"User-Agent": "Starboard"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:  # a fixed https address  # nosec B310
            data = r.read(MAX_WHEEL + 1)
    except (urllib.error.URLError, OSError):
        raise Unavailable(f"Starboard could not download {w['label']} ({w['download']}) from the Python Package Index "
                          "(pypi.org), so this server needs to reach the internet for it. It tries again next time") from None
    if len(data) > MAX_WHEEL or hashlib.sha256(data).hexdigest() != spec[1]:
        raise Unavailable(f"The download of {w['label']} was not the file Starboard expected, so it was not used")
    os.makedirs(os.path.dirname(where), exist_ok=True)
    part = f"{where}.part-{os.getpid()}"
    shutil.rmtree(part, ignore_errors=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos = z.infolist()
        if sum(i.file_size for i in infos) > MAX_UNPACKED:
            raise Unavailable(f"The download of {w['label']} was larger than expected, so it was not used")
        for i in infos:
            target = os.path.realpath(os.path.join(part, i.filename))
            if not target.startswith(os.path.realpath(part) + os.sep) or i.is_dir():
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(i) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    shutil.rmtree(where, ignore_errors=True)
    os.rename(part, where)


def load(name):
    """Makes `name` importable, fetching it the first time. Raises Unavailable with the reason in a person's words."""
    if _importable(name):  # in this Python already (a developer's computer), or loaded before
        return
    w = WHEELS[name]
    spec = _spec(name)
    if not spec:
        raise Unavailable(f"{w['label']} has no ready-made version for this processor")
    where = os.path.join(_root(), f"{name}-{w['version']}-{platform.machine()}")
    with _lock:
        if where not in sys.path:
            if not (os.path.isdir(where) and _intact(where, spec[2])):
                _fetch(name, spec, where)
                if not _intact(where, spec[2]):
                    raise Unavailable(f"{w['label']} did not unpack as expected, so it was not used")
            sys.path.append(where)
            importlib.invalidate_caches()
    if not _importable(name):
        raise Unavailable(f"{w['label']} was downloaded but did not load on this server")
