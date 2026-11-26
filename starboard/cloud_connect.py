"""Connect a cloud service (DASH-452, TheMightyTRexUK, 16 November 2026: "I want to add a better way to link backups to a
cloud remote - can you have a wizard setup the system on a slide out and have it authorise and connect?").

The wizard on Copies off this computer: choose a service, sign in, choose or make the folder, test, then save. What it
saves is the same as the older way (backup_copies, kind "rclone"): a remote named starboard-cloud and its part of
rclone.conf, kept in Starboard's own folder, readable by Starboard only, never in a backup, never sent to the browser.

Signing in, by kind of service (web/cloud-services.json is the one list):

- Keys (Backblaze B2, S3, WebDAV, SFTP): the keys or password are entered in the wizard. rclone makes the remote in its
  helper container with `rclone config create ... --obscure`, so passwords are stored the way rclone expects.
- Complete in this browser (Google Drive, OneDrive, Dropbox): `rclone authorize` runs in the helper and listens on
  127.0.0.1:53682 inside that container only. Starboard reads the service's own sign-in address from it and shows it
  as a link. After signing in, the service sends the browser to http://127.0.0.1:53682/?state=...&code=..., which does
  not load (the browser is on another device, or the listener is in a container). The person pastes that address back;
  Starboard checks it (only 127.0.0.1 or localhost, rclone's port, the state rclone made and a code) and hands a
  rebuilt address, never the pasted text, to the listener, which swaps the code for the token. No port is published.
- Complete on the phone (Google Drive and OneDrive, owner, 16 November 2026): the device flow (RFC 8628). Starboard
  asks the service for a short code, shows a QR code of the service's own page and the code, and asks the service
  every few seconds until the person approves on their phone. It needs Starboard's own registered sign-in (a client
  ID) at Google and at Microsoft, as rclone's own are refused for this flow (checked 16 November 2026: Google says
  "Invalid client type", Microsoft "AADSTS70002"). Until one is set (CLIENTS, or STARBOARD_GOOGLE_CLIENT_ID and
  STARBOARD_MICROSOFT_CLIENT_ID), the choice is not offered. These requests go from Starboard to fixed https addresses
  only (DEVICE), as its release check goes to GitHub; everything that touches files is rclone in its helper.

One sign-in at a time. Each step has a time limit, and the helper is removed when the sign-in ends, fails, runs out of
time or the person closes the slide-out (cancel). Nothing is written to the backup settings until Save.
"""
import base64
import json
import os
import re
import secrets
import shutil
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import backup_copies, logs, qr

REMOTE = "starboard-cloud"
PORT = 53682
SIGNIN_LIMIT = 600     # 10 minutes to sign in, on either device
PHONE_PAUSE = 1.0      # times the service's own poll interval; the tests make it small so they do not wait seconds
PHONE_LIMIT = 600      # the device code lives 15 (Microsoft) or 30 (Google) minutes; Starboard waits 10
STEP_LIMIT = 120       # a folder list, a folder made, a test
LINK_WAIT = 45         # for rclone to say its sign-in address
RCLONE_TYPE = {"drive": "drive", "onedrive": "onedrive", "dropbox": "dropbox", "b2": "b2", "s3": "s3", "webdav": "webdav", "sftp": "sftp"}
# The service's sign-in page must be on one of these, or Starboard does not show it.
SIGNIN_HOSTS = {"drive": ("accounts.google.com",), "onedrive": ("login.microsoftonline.com", "login.live.com"),
                "dropbox": ("www.dropbox.com", "dropbox.com")}
# Complete on the phone: the device flow, at fixed https addresses only.
DEVICE = {
    "drive": {"code": "https://oauth2.googleapis.com/device/code", "token": "https://oauth2.googleapis.com/token",
              "scope": "https://www.googleapis.com/auth/drive.file", "pages": ("www.google.com", "google.com")},
    "onedrive": {"code": "https://login.microsoftonline.com/common/oauth2/v2.0/devicecode",
                 "token": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                 "scope": "Files.ReadWrite offline_access", "pages": ("microsoft.com", "www.microsoft.com", "login.microsoft.com")},
}
GRAPH_DRIVE = "https://graph.microsoft.com/v1.0/me/drive"
# Read only (Bring in media, DASH-455): reading files already in a Drive needs drive.readonly, which Google does not
# allow with the device flow, so Google Drive is Complete in this browser only; OneDrive asks only to read.
READ_ONLY = {"drive": "drive.readonly", "onedrive": "Files.Read Files.Read.All offline_access"}
# Starboard's own registered sign-in at Google ("TVs and Limited Input devices", drive.file) and Microsoft (public client
# flows allowed, personal and work accounts). Empty until TheMightyTRexUK registers them (DECISIONS-WAITING.md).
CLIENTS = {"drive": {"id": "", "secret": ""}, "onedrive": {"id": "", "secret": ""}}
TEST_HOOK = None  # tests and the example server put their stand-in addresses here; None is the real services

FOLDER_PART = re.compile(r"^[^/\\\x00-\x1f\x7f:*?\"<>|]{1,100}$")
ID_RE = re.compile(r"^[A-Za-z0-9/+=_.-]{1,200}$")
REGION_RE = re.compile(r"^[a-z0-9-]{0,40}$")
HOST_RE = re.compile(r"^([A-Za-z0-9]([A-Za-z0-9-]{0,62})(\.[A-Za-z0-9]([A-Za-z0-9-]{0,62}))*|\[[0-9A-Fa-f:]{2,39}\])$")
CODE_RE = re.compile(r"^[A-Za-z0-9._~/+=-]{1,2048}$")
STATE_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
TOKEN_LINE = re.compile(r"--->\s*(.+?)\s*<---End paste", re.S)

_lock = threading.RLock()
_session = None


def _note(sess, level, words):
    """One line in Starboard's log for each step of a sign-in, so one that does not finish says where and why
    (owner, 19 November 2026: OneDrive's two-step check did not finish, and nothing showed why). Never the sign-in's
    address, code or token: only the service, how it signs in, the step and the sentence shown."""
    try:
        name = service(sess["service"])["name"]
    except Exception:  # noqa: BLE001 - a log line never stops a sign-in
        name = str(sess.get("service") or "a service")
    way = {"browser": "in this browser", "phone": "on the phone"}.get(sess.get("way"), "")
    logs.event(level, "cloud sign-in", f"{name}{' ' + way if way else ''}: {words}"[:400], step=str(sess.get("state") or ""))


class CloudError(Exception):
    pass


# The list of services ---------------------------------------------------------------------------------------------

def _services_file():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "cloud-services.json")


def services():
    with open(_services_file(), encoding="utf-8") as f:
        return json.load(f)["services"]


def service(sid):
    for s in services():
        if s["id"] == sid:
            return s
    raise CloudError("Choose a service from the list")


def client(sid):
    """Starboard's own sign-in for Complete on the phone, or None when it has none for this service."""
    env = {"drive": ("STARBOARD_GOOGLE_CLIENT_ID", "STARBOARD_GOOGLE_CLIENT_SECRET"),
           "onedrive": ("STARBOARD_MICROSOFT_CLIENT_ID", "")}.get(sid)
    if not env:
        return None
    cid = os.environ.get(env[0]) or CLIENTS[sid]["id"]
    secret = (os.environ.get(env[1]) if env[1] else "") or CLIENTS[sid]["secret"]
    return {"id": cid, "secret": secret} if cid else None


def offered():
    """The list for the page: each service, and whether Complete on the phone can be offered on this Starboard."""
    return [{**s, "phone": bool(s.get("phone") and client(s["id"]))} for s in services()]


# Checking what the person entered -------------------------------------------------------------------------------------

def _clean_url(text, label, field=""):
    t = str(text or "").strip()
    u = urllib.parse.urlsplit(t)
    if (u.scheme not in ("http", "https") or not u.hostname or not HOST_RE.match(u.hostname if ":" not in u.hostname else f"[{u.hostname}]")
            or len(t) > 500 or any(c in t for c in " \t\r\n\"'\\<>`") or u.username or u.password):
        raise ValueError(f"{field}|{label}: enter an address that starts with https://, such as https://cloud.example/")
    return t


def check_fields(sid, given):
    """The keys or password for a keys service, checked one by one. Returns {field: value}; raises ValueError naming the
    field, as the page shows it beside that field ("field|sentence")."""
    s = service(sid)
    if s["signin"] != "keys":
        raise CloudError("This service signs in with its own page")
    out = {}
    for f in s["fields"]:
        raw = given.get(f["id"])
        value = str(raw if raw is not None else f.get("default", "")).strip()
        if not value:
            if f["required"]:
                raise ValueError(f"{f['id']}|{f['label']}: enter it")
            continue
        kind = f["kind"]
        if kind == "url":
            value = _clean_url(value, f["label"], f["id"])
        elif kind == "id" and not ID_RE.match(value):
            raise ValueError(f"{f['id']}|{f['label']}: copy it again, it has letters that a key never has")
        elif kind == "region" and not REGION_RE.match(value):
            raise ValueError(f"{f['id']}|{f['label']}: such as eu-west-2, in small letters")
        elif kind == "host" and not HOST_RE.match(value):
            raise ValueError(f"{f['id']}|{f['label']}: enter a name such as nas.home or an address such as 192.168.1.20")
        elif kind == "port" and not (value.isdigit() and 1 <= int(value) <= 65535):
            raise ValueError(f"{f['id']}|{f['label']}: a number from 1 to 65535")
        elif kind == "choice" and value not in [c[0] for c in f["choices"]]:
            raise ValueError(f"{f['id']}|{f['label']}: choose one")
        elif kind in ("user", "secret"):
            if len(value) > (500 if kind == "secret" else 200) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError(f"{f['id']}|{f['label']}: it cannot have line breaks, and at most 500 characters")
        out[f["id"]] = value if kind != "secret" else str(raw)  # a password is kept as entered, spaces too
    return out


def check_folder(text):
    """A folder at the service, such as starboard-backups or my-bucket/starboard. Raises ValueError with a sentence."""
    t = str(text or "").strip().strip("/")
    parts = t.split("/") if t else []
    if not parts or len(parts) > 10 or len(t) > 300 or any(p in (".", "..") or not FOLDER_PART.match(p) for p in parts):
        raise ValueError("Use a folder name such as starboard-backups: letters, numbers, spaces, dots and dashes, with / between folders")
    return t


def check_answer(sess, pasted):
    """The address the service sent the browser to, pasted back. Only http://127.0.0.1 or localhost on rclone's port,
    with the state this sign-in made and a code. Returns the address rebuilt from those two values alone."""
    t = str(pasted or "").strip()
    if len(t) > 4096 or any(c in t for c in " \t\r\n<>\"'`\\"):
        raise ValueError("Paste the whole address from the browser's address bar, starting http://127.0.0.1 or http://localhost")
    if not re.match(r"^https?://", t):
        t = "http://" + t  # a phone's address bar may hide the http://
    u = urllib.parse.urlsplit(t)
    try:
        port = u.port
    except ValueError:
        port = None
    if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost") or port != PORT or u.path not in ("", "/") or u.username or u.fragment:
        raise ValueError(f"That is not the address the sign-in ends on. It starts http://127.0.0.1:{PORT}/ or http://localhost:{PORT}/")
    q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
    if any(len(v) != 1 for v in q.values()):
        raise ValueError("That address has a part twice. Copy it again from the address bar")
    if q.get("error"):
        raise CloudError("You did not allow Starboard to use the account, so nothing was connected. Select Start again to sign in again")
    state, code = (q.get("state") or [""])[0], (q.get("code") or [""])[0]
    if not state or state != sess.get("auth_state"):
        raise ValueError("That address is from a different sign-in. Use the link on this step, then paste the address it ends on")
    if not CODE_RE.match(code):
        raise ValueError("That address has no sign-in code. Copy the whole address, including everything after the question mark")
    return f"http://127.0.0.1:{PORT}/?" + urllib.parse.urlencode({"state": state, "code": code})


def check_pasted_config(remote, config):
    """Your own rclone remote: name:folder and its part of rclone.conf, as backup_copies checks it."""
    m = backup_copies.REMOTE_RE.match(str(remote or "").strip())
    if not m:
        raise ValueError("remote|Write the remote as name:folder, such as mycloud:starboard-backups")
    config = str(config or "").strip()
    if not config or len(config) > 20000:
        raise ValueError("config|Paste the part of your rclone.conf for this remote, from [name] to the next [")
    if m.group(1) not in backup_copies.remote_names(config):
        raise ValueError(f"config|Paste the part of your rclone.conf that starts with [{m.group(1)}]")
    return str(remote).strip(), config + "\n"


# The session ----------------------------------------------------------------------------------------------------------

def _public(sess):
    if not sess:
        return {"state": "none"}
    out = {k: sess.get(k) for k in ("id", "service", "way", "state", "error", "link", "user_code", "page", "folder", "test", "account")}
    out["seconds_left"] = max(0, int(sess["deadline"] - time.time())) if sess.get("deadline") else None
    out["signed_in"] = bool(sess.get("config"))
    if sess.get("page"):
        size, path = qr.svg_path(qr.encode(sess["page"], level="M"))
        out["qr"] = {"size": size, "path": path}
    return {k: v for k, v in out.items() if v not in (None, "")}


def current():
    with _lock:
        _expire()
        return _public(_session)


STATE_WORDS = {"starting": "waiting for the sign-in page", "link": "waiting for the address the sign-in ends on",
               "checking": "swapping the answer for access", "phone": "waiting for approval on the phone",
               "details": "entering the details", "signed-in": "signed in, choosing the folder"}


def _expire():
    global _session
    s = _session
    if s and s.get("deadline") and time.time() > s["deadline"] and s["state"] in ("starting", "link", "checking", "phone"):
        _note(s, "warning", f"the time to sign in ran out (it was at: {STATE_WORDS.get(s['state'], s['state'])})")
        s.update(state="expired", error="The time to sign in ran out, so nothing was connected. Select Try again to start again")
        _end(s)


def _work(data_dir, sid):
    path = os.path.join(data_dir, backup_copies.WORK, f"cloud-{sid}")
    os.makedirs(path, mode=0o700, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def _end(sess, keep_config=True):
    """The helper goes, and the sign-in's files with it. The finished config stays in memory until Save or cancel."""
    cid = sess.pop("cid", None)
    if cid:
        RUN.remove(cid)
    work = sess.get("work")
    if work and os.path.isdir(work):
        shutil.rmtree(work, ignore_errors=True)
    if not keep_config:
        sess.pop("config", None)


def cancel():
    """The person closed the slide-out, or chose another service: the helper is removed and nothing is kept."""
    global _session
    with _lock:
        if _session:
            if _session["state"] in ("starting", "link", "checking", "phone", "details", "signed-in"):
                _note(_session, "info", f"closed before it was saved (it was at: {STATE_WORDS.get(_session['state'], _session['state'])})")
            _session["state"] = "cancelled"
            _end(_session, keep_config=False)
        _session = None
    return {"state": "none"}


def start(data_dir, sid, way="browser", read_only=False, dest=None):
    """Starts signing in to a service: the link (browser), the code (phone), or nothing to wait for (keys, paste). read_only asks the service only to read files (Bring in media)."""
    global _session
    s = service(sid)
    if way not in ("browser", "phone"):
        raise CloudError("Choose how to sign in")
    if read_only and way == "phone" and sid == "drive":
        raise CloudError("Google only lets Starboard read the files you already have when you sign in in a browser. Choose Complete in this browser")
    if way == "phone" and not (s.get("phone") and client(sid)):
        raise CloudError("Complete on the phone is not offered for this service. Choose Complete in this browser")
    cancel()
    sess = {"id": secrets.token_hex(8), "service": sid, "way": way if s["signin"] == "oauth" else s["signin"], "state": "starting",
            "data_dir": data_dir, "started": time.time(), "deadline": time.time() + SIGNIN_LIMIT, "read_only": bool(read_only),
            "dest": dest or "", "rname": remote_name(data_dir, sid, dest)}
    with _lock:
        _session = sess
    _note(sess, "info", "started" + (" (asking only to read files)" if read_only else ""))
    if s["signin"] != "oauth":
        sess.update(state="details", deadline=None)
        return _public(sess)
    try:
        if way == "phone":
            _phone_start(sess)
        else:
            sess["work"] = _work(data_dir, sess["id"])
            RUN.authorize(sess)
            threading.Thread(target=_watch_link, args=(sess,), name="cloud-signin", daemon=True).start()
    except Exception as e:
        _note(sess, "warning", f"could not start: {e}")
        cancel()
        raise
    return _public(sess)


def remote_name(data_dir, sid, dest=None):
    """The rclone remote's name for a connection. The first keeps starboard-cloud, so a place made before several places
    keeps working; each next one has its own (starboard-onedrive, starboard-onedrive-2), so one sign-in never overwrites
    another. Signing in again to a place keeps that place's name."""
    used = {}
    for d in backup_copies.destinations(data_dir):
        if d["kind"] == "rclone" and d["remote"]:
            used[d["remote"].split(":", 1)[0]] = d["id"]
    if dest:
        for name, did in used.items():
            if did == dest and re.match(r"^[A-Za-z0-9_.-]{1,60}$", name):
                return name
    if REMOTE not in used:
        return REMOTE
    for n in range(1, 21):
        name = f"starboard-{sid}" if n == 1 else f"starboard-{sid}-{n}"
        if name not in used:
            return name
    return f"starboard-{sid}-{secrets.token_hex(2)}"


def _rname(sess):
    return sess.get("rname") or REMOTE


def _mine(sid):
    with _lock:
        if not _session or _session["id"] != sid:
            raise CloudError("That sign-in has ended. Select Start again")
        _expire()
        return _session


# Complete in this browser: rclone authorize in the helper -------------------------------------------------------------

def authorize_script(sess):
    """The helper's script: rclone authorize in the background, its sign-in address read through its own redirect, then
    the pasted answer handed to its listener. rclone says 127.0.0.1 or localhost, by service (Dropbox and OneDrive use
    localhost). Every step has a time limit; the script ends with rclone."""
    sid = sess["service"]
    blob = {"scope": "drive.file"} if sid == "drive" else {}
    if sess.get("read_only"):
        blob = {"scope": READ_ONLY["drive"]} if sid == "drive" else {"access_scopes": READ_ONLY["onedrive"]} if sid == "onedrive" else blob
    blob.update((TEST_HOOK or {}).get("authorize", {}).get(sid, {}))
    arg = base64.b64encode(json.dumps(blob).encode()).decode().rstrip("=") if blob else ""  # rclone reads it without padding
    rtype = RCLONE_TYPE[sid]
    # Separate statements: "a && b && (c) &" would send a and b (the cd) to the background with c.
    return ("cd /c || exit 1; umask 077; O=$(stat -c %u:%g /c); touch out; chown $O out; "
            f"( timeout {SIGNIN_LIMIT} rclone authorize {rtype} {arg} --auth-no-open-browser > out 2>&1; rc=$?; chown $O out; "
            "echo $rc > done.part; chown $O done.part; mv done.part done ) & "
            f"i=0; while [ $i -lt {LINK_WAIT} ]; do L=$(grep -oE 'http://(127[.]0[.]0[.]1|localhost):{PORT}/auth[?]state=[A-Za-z0-9_-]+' out | head -n 1); "
            "[ -n \"$L\" ] && break; sleep 1; i=$((i+1)); done; "
            "[ -n \"$L\" ] && wget -S -T 15 -O /dev/null \"$L\" 2>&1 | sed -n 's/^ *[Ll]ocation: *//p' | head -n 1 > link.part; "
            "chown $O link.part; mv link.part link; "
            "while [ ! -f done ]; do if [ -f answer ]; then wget -q -T 60 -O /dev/null \"$(cat answer)\"; rm -f answer; fi; sleep 1; done; exit 0")


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _signin_link(sess, text):
    """The service's own sign-in address, read from rclone's redirect, checked against the service's hosts."""
    link = text.strip()
    u = urllib.parse.urlsplit(link)
    hosts = SIGNIN_HOSTS.get(sess["service"], ()) + tuple((TEST_HOOK or {}).get("hosts", ()))
    if u.scheme not in ("https", "http") or u.hostname not in hosts or (u.scheme == "http" and not TEST_HOOK):
        raise CloudError("The sign-in page was not where it should be, so Starboard did not show it. Select Try again")
    q = urllib.parse.parse_qs(u.query)
    state = (q.get("state") or [""])[0]
    if not STATE_RE.match(state):
        raise CloudError("The sign-in page had no state. Select Try again")
    return link, state


def _watch_link(sess):
    """Follows the helper's files until rclone says its address, then until the token arrives or time runs out."""
    work = sess["work"]
    until = time.time() + LINK_WAIT + 20
    while sess["state"] == "starting":
        text = _read(os.path.join(work, "link"))
        if text.strip():
            try:
                link, state = _signin_link(sess, text)
                with _lock:
                    sess.update(link=link, auth_state=state, state="link")
                _note(sess, "info", f"sign-in page ready at {urllib.parse.urlsplit(link).hostname}")
            except CloudError as e:
                _fail(sess, str(e))
                return
        elif os.path.exists(os.path.join(work, "done")) or time.time() > until:
            backup_copies.log_detail(sess.get("data_dir"), f"Connecting {_name(sess)}, starting the sign-in", _read(os.path.join(work, "out")), 1)
            _fail(sess, "rclone did not start the sign-in. Select Try again" + _last(work))
            return
        time.sleep(0.5)
    while sess["state"] in ("link", "checking"):
        if os.path.exists(os.path.join(work, "done")):
            got = token_from_rclone(_read(os.path.join(work, "out")))
            if got:
                try:
                    _signed_in(sess, json.loads(got))
                except (ValueError, CloudError) as e:
                    _fail(sess, str(e))
            else:
                backup_copies.log_detail(sess.get("data_dir"), f"Connecting {_name(sess)}, signing in", _read(os.path.join(work, "out")), 1)
                _fail(sess, "The service did not give Starboard access. Select Start again to sign in again" + _last(work))
            return
        if time.time() > sess["deadline"]:
            with _lock:
                _expire()
            return
        time.sleep(1)


def _last(work):
    """rclone's last problem, or its last line, for the sentence the page shows."""
    said = [ln.strip() for ln in _read(os.path.join(work, "out")).splitlines() if ln.strip()]
    lines = [ln for ln in said if "ERROR" in ln or "Failed" in ln or "rror" in ln] or said[-1:]
    return f" ({lines[-1][-160:]})" if lines else " (rclone said nothing)"


def token_from_rclone(said):
    """The token rclone authorize printed between its markers, as JSON text, or None. Older rclone prints the token's JSON;
    newer prints a base64 blob of {"token": "<the token's JSON>"}."""
    m = TOKEN_LINE.search(said or "")
    if not m:
        return None
    text = m.group(1).strip()
    if text.startswith("{"):
        return text
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4)) if re.match(r"^[A-Za-z0-9_-]+$", text) else base64.b64decode(text + "=" * (-len(text) % 4))
        got = json.loads(raw)
        tok = got.get("token") if isinstance(got, dict) else None
        if isinstance(tok, str) and tok.startswith("{"):
            json.loads(tok)
            return tok
    except (ValueError, TypeError):
        pass
    return None


def answer(sid, pasted):
    """The address pasted back: checked, then handed to rclone's listener in the helper."""
    sess = _mine(sid)
    if sess["state"] != "link":
        raise CloudError("Starboard is not waiting for an address now")
    try:
        url = check_answer(sess, pasted)
    except CloudError as e:
        _fail(sess, str(e))
        raise
    except ValueError as e:
        _note(sess, "warning", f"the pasted address was not used: {e}")
        raise
    fd = os.open(os.path.join(sess["work"], "answer.part"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(url)
    os.replace(os.path.join(sess["work"], "answer.part"), os.path.join(sess["work"], "answer"))
    with _lock:
        sess.update(state="checking", deadline=min(sess["deadline"], time.time() + 90))
    _note(sess, "info", "the address the sign-in ended on was pasted back")
    return _public(sess)


def _fail(sess, sentence):
    with _lock:
        if sess["state"] not in ("cancelled",):
            _note(sess, "warning", f"did not finish (it was at: {STATE_WORDS.get(sess['state'], sess['state'])}): {sentence}")
            sess.update(state="failed", error=sentence)
        _end(sess)


# Complete on the phone: the device flow --------------------------------------------------------------------------------

def _http(url, form=None, headers=None, limit=65536):
    """One request to a fixed address: (status, JSON). Never follows a redirect to somewhere else."""
    data = urllib.parse.urlencode(form).encode() if form is not None else None
    req = urllib.request.Request(url, data=data, headers={"Accept": "application/json", "User-Agent": "Starboard", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:  # fixed https addresses (DEVICE, GRAPH_DRIVE)  # nosec B310
            status, body = r.status, r.read(limit)
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read(limit)
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise CloudError(f"Starboard could not reach the sign-in service: {getattr(e, 'reason', e)}") from None
    try:
        return status, json.loads(body.decode("utf-8") or "{}")
    except ValueError:
        return status, {}


def _device(sid):
    d = dict(DEVICE[sid])
    d.update((TEST_HOOK or {}).get("device", {}).get(sid, {}))
    return d


def _phone_start(sess):
    sid, d, c = sess["service"], _device(sess["service"]), client(sess["service"])
    form = {"client_id": c["id"], "scope": READ_ONLY["onedrive"] if sess.get("read_only") and sid == "onedrive" else d["scope"]}
    status, got = HTTP(d["code"], form)
    if status != 200 or not got.get("device_code") or not got.get("user_code"):
        raise CloudError(f"The service did not give Starboard a code ({got.get('error_description') or got.get('error') or status}). Choose Complete in this browser")
    page = got.get("verification_uri") or got.get("verification_url") or ""
    u = urllib.parse.urlsplit(page)
    if u.scheme != "https" and not (TEST_HOOK and u.scheme == "http") or u.hostname not in d["pages"] + tuple((TEST_HOOK or {}).get("hosts", ())):
        raise CloudError("The service sent a page Starboard does not know, so it did not show it. Choose Complete in this browser")
    code = str(got["user_code"])
    if not re.match(r"^[A-Za-z0-9-]{4,20}$", code):
        raise CloudError("The service sent a code Starboard could not read. Choose Complete in this browser")
    life = min(int(got.get("expires_in") or PHONE_LIMIT), PHONE_LIMIT)
    _note(sess, "info", "code shown for the phone")
    sess.update(state="phone", page=page, user_code=code, device_code=got["device_code"], interval=max(2, int(got.get("interval") or 5)),
                deadline=time.time() + life)
    threading.Thread(target=_poll_phone, args=(sess,), name="cloud-phone", daemon=True).start()


def _poll_phone(sess):
    """Asks the service every few seconds whether the person approved, until they do, refuse, or time runs out."""
    d, c = _device(sess["service"]), client(sess["service"])
    while sess["state"] == "phone":
        time.sleep(sess["interval"] * PHONE_PAUSE)
        if sess["state"] != "phone":
            return
        if time.time() > sess["deadline"]:
            with _lock:
                _expire()
            return
        form = {"client_id": c["id"], "device_code": sess["device_code"], "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}
        if c.get("secret"):
            form["client_secret"] = c["secret"]
        try:
            status, got = HTTP(d["token"], form)
        except CloudError:
            continue  # the network blinked: ask again next time
        err = got.get("error")
        if status == 200 and got.get("access_token"):
            try:
                _signed_in(sess, got, own_client=c)
            except (ValueError, CloudError) as e:
                _fail(sess, str(e))
            return
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            sess["interval"] += 5
            continue
        if err in ("access_denied", "authorization_declined"):
            _fail(sess, "You did not allow Starboard to use the account, so nothing was connected. Select Try again to sign in again")
        elif err in ("expired_token", "bad_verification_code"):
            with _lock:
                sess.update(state="expired", error="The code ran out of time, so nothing was connected. Select Try again for a new code")
                _end(sess)
        else:
            _fail(sess, f"The service stopped the sign-in ({got.get('error_description') or err or status}). Select Try again")
        return


# After signing in -------------------------------------------------------------------------------------------------------

def _rclone_token(got):
    """The service's answer as rclone keeps a token: access, refresh, type and when it runs out."""
    if not isinstance(got, dict) or not isinstance(got.get("access_token"), str):
        raise ValueError("The service did not send a sign-in Starboard can keep. Select Start again")
    if "expiry" in got:  # rclone authorize's answer is already in rclone's form
        tok = {k: got[k] for k in ("access_token", "token_type", "refresh_token", "expiry", "expires_in") if k in got}
    else:
        expiry = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + int(got.get("expires_in") or 3600)))
        tok = {"access_token": got["access_token"], "token_type": got.get("token_type") or "Bearer",
               "refresh_token": got.get("refresh_token", ""), "expiry": expiry}
    return json.dumps(tok, separators=(",", ":"))


def _section(lines, rname=REMOTE):
    for k, v in lines:
        if any(c in str(v) for c in "\r\n") or not re.match(r"^[a-z_]+$", k):
            raise ValueError("That sign-in has a line break in it, so Starboard did not keep it")
    return f"[{rname}]\n" + "".join(f"{k} = {v}\n" for k, v in lines if v != "")


def _signed_in(sess, got, own_client=None):
    sid = sess["service"]
    token = _rclone_token(got)
    lines = [("type", RCLONE_TYPE[sid])]
    if own_client:
        lines += [("client_id", own_client["id"]), ("client_secret", own_client.get("secret", ""))]
    if sid == "drive":
        lines.append(("scope", READ_ONLY["drive"] if sess.get("read_only") else "drive.file"))
    if sid == "onedrive" and sess.get("read_only"):
        lines.append(("access_scopes", READ_ONLY["onedrive"]))
    if sid == "onedrive":
        status, drive = HTTP((TEST_HOOK or {}).get("graph", GRAPH_DRIVE), None, {"Authorization": f"Bearer {json.loads(token)['access_token']}"})
        if status != 200 or not re.match(r"^[A-Za-z0-9!._-]{1,200}$", str(drive.get("id") or "")):
            raise CloudError("Signed in, but OneDrive did not say which of its storage areas to use. Select Start again")
        kind = drive.get("driveType") if drive.get("driveType") in ("personal", "business", "documentLibrary") else "personal"
        lines += [("drive_id", drive["id"]), ("drive_type", kind)]
        sess["account"] = str((drive.get("owner") or {}).get("user", {}).get("displayName") or "")[:100]
    lines.append(("token", token))
    with _lock:
        sess.update(config=_section(lines, _rname(sess)), state="signed-in", error="", deadline=None)
        _end(sess)
    _note(sess, "info", "signed in" + (f", OneDrive {dict(lines).get('drive_type')}" if sid == "onedrive" else ""))


def details(sid, given):
    """Keys or a pasted remote: rclone makes the remote in the helper (passwords obscured as rclone keeps them)."""
    sess = _mine(sid)
    s = service(sess["service"])
    if s["signin"] == "paste":
        remote, config = check_pasted_config(given.get("remote"), given.get("config"))
        with _lock:
            sess.update(config=config, remote=remote, state="signed-in")
        return _public(sess)
    values = check_fields(sess["service"], given)
    params = dict(values)
    if sess["service"] == "s3":
        params["provider"] = "Other" if values.get("endpoint") else "AWS"
        params["env_auth"] = "false"
    if sess["service"] == "b2":
        params["hard_delete"] = "true"  # pruned copies really go, as at every other place
    work = _work(sess["data_dir"], sess["id"] + "-keys")
    try:
        os.makedirs(os.path.join(work, "v"), mode=0o700, exist_ok=True)
        args = []
        for k, v in params.items():
            if not re.match(r"^[a-z_]+$", k):
                continue
            fd = os.open(os.path.join(work, "v", k), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(v)
            args.append(f'{k}="$(cat /c/v/{k})"')
        script = (f"rclone --config /c/rclone.conf config create {_rname(sess)} {RCLONE_TYPE[sess['service']]} {' '.join(args)} "
                  "--obscure --non-interactive >/c/said 2>&1; code=$?; chown -R $(stat -c %u:%g /c) /c 2>/dev/null; exit $code")
        code, said = RUN.short(sess, script, work)
        backup_copies.log_detail(sess.get("data_dir"), f"Connecting {_name(sess)}, making the remote", said, code)
        config = _read(os.path.join(work, "rclone.conf"))
        if code or f"[{_rname(sess)}]" not in config:
            raise CloudError("rclone could not use those details: " + (said.strip().splitlines() or ["no reason given"])[-1][:200])
        with _lock:
            sess.update(config=config, state="signed-in")
        return _public(sess)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _remote_root(sess):
    return sess.get("remote") or f"{_rname(sess)}:"


def _with_config(sess, script, label):
    """Runs an rclone script in the helper with this sign-in's config, then keeps any refreshed token."""
    if not sess.get("config"):
        raise CloudError("Sign in first")
    work = _work(sess["data_dir"], sess["id"] + "-" + label)
    try:
        fd = os.open(os.path.join(work, "rclone.conf"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(sess["config"])
        code, said = RUN.short(sess, script + "; code=$?; chown -R $(stat -c %u:%g /c) /c 2>/dev/null; exit $code", work)
        backup_copies.log_detail(sess.get("data_dir"), f"Connecting {_name(sess)}, {LABEL_WORDS.get(label, label)}", said, code)
        after = _read(os.path.join(work, "rclone.conf"))
        if after.strip() and after != sess["config"]:
            sess["config"] = after
        return code, said
    finally:
        shutil.rmtree(work, ignore_errors=True)


LABEL_WORDS = {"list": "listing the folders", "test": "the test"}


def _name(sess):
    try:
        return service(sess["service"])["name"]
    except Exception:  # noqa: BLE001
        return str(sess.get("service") or "a service")


RC = "rclone --config /c/rclone.conf --contimeout 30s --timeout 90s --retries 1 --low-level-retries 2"


def folders(sid):
    """The folders at the top of the service (for Backblaze B2 and S3, the buckets), at most 200."""
    sess = _mine(sid)
    root = _remote_root(sess)
    code, said = _with_config(sess, f"timeout {STEP_LIMIT} {RC} lsf --dirs-only --max-depth 1 {backup_copies._q(root)}", "list")
    if code:
        _note(sess, "warning", f"could not list the folders: {plain(said, sess)}")
        raise CloudError(plain(said, sess))
    names = [ln.rstrip("/") for ln in said.splitlines() if ln.endswith("/") and FOLDER_PART.match(ln.rstrip("/"))]
    return {"folders": sorted(names, key=str.lower)[:200], "root": root}


def _target(sess):
    root = _remote_root(sess)
    folder = sess["folder"]
    return root + folder if root.endswith(":") else root.rstrip("/") + "/" + folder


def test(sid, folder):
    """The test step: make the folder if it is not there, write a small file, read it back, remove it."""
    sess = _mine(sid)
    sess["folder"] = check_folder(folder)
    target = _target(sess)
    mark = secrets.token_hex(6)
    script = test_script(target, mark)
    code, said = _with_config(sess, f"timeout {STEP_LIMIT} sh -c {backup_copies._q(script)}", "test")
    result = read_test(said, code, sess, backup_copies.newest_size(sess["data_dir"]))
    sess["test"] = result
    _note(sess, "info" if result["ok"] else "warning", "the test worked" if result["ok"] else f"the test did not work: {result.get('error', '')}")
    if result["ok"]:
        sess["state"] = "tested"
    return _public(sess)


def test_script(target, mark):
    """Make the folder, write, read back and remove a small file, each saying when it worked; then how much room there is
    and how many full backups are there."""
    q = backup_copies._q
    name = f"{target.rstrip('/')}/.starboard-test-{mark}"
    return (f"{RC} mkdir {q(target)} && echo STEP-FOLDER && "
            f"echo starboard-{mark} | {RC} rcat {q(name)} && echo STEP-WRITE && "
            f"[ \"$({RC} cat {q(name)})\" = starboard-{mark} ] && echo STEP-READ && "
            f"{RC} deletefile {q(name)} && echo STEP-REMOVE && "
            f"( {RC} about --json {q(target)} 2>/dev/null | tr -d ' \\n' | grep -o '\"free\":[0-9]*' | sed 's/.*:/FREE /' ; true ) && "
            f"echo COUNT $({RC} lsf --files-only {q(target)} | grep -cE {q(backup_copies.BACKUP_GLOB)})")


STEPS = (("folder", "Reach the folder"), ("write", "Write a small test file"), ("read", "Read it back"), ("remove", "Remove it"))


def read_test(said, code, sess=None, newest_size=None, signin=None):
    """The helper's words as the test's steps, each done or not, with a sentence when one did not work."""
    done = [k for k, _ in STEPS if f"STEP-{k.upper()}" in said]
    m = re.search(r"FREE (\d+)", said)
    free = int(m.group(1)) if m else None
    ok = not code and len(done) == len(STEPS)
    out = {"ok": ok, "steps": [{"id": k, "label": label, "done": k in done} for k, label in STEPS], "free": free, "at": time.time()}
    if not ok:
        out["error"] = plain(said, sess, signin)
    elif free is not None and newest_size and free < newest_size:
        out.update(ok=False, error=f"There is room for {free // 1024 ** 2} MB there, and the newest backup is {newest_size // 1024 ** 2} MB. Free some space, or keep fewer copies")
    return out


def plain(said, sess=None, signin=None):
    """rclone's last words, in a sentence the wizard can show. A sign-in that a service no longer accepts starts with
    "SIGNIN|", so the page offers Sign in again (which opens the wizard at its sign-in step)."""
    low = said.lower()
    if signin is None and sess:
        signin = service(sess["service"])["signin"]
    tokenish = "token" in low or "invalid_grant" in low or "oauth" in low
    if signin == "oauth" and (tokenish or "401" in low or "unauthorized" in low or "unauthenticated" in low):
        return "SIGNIN|The sign-in has expired or was taken back at the service, so Starboard cannot reach it. Select Sign in again"
    if "signaturedoesnotmatch" in low or "invalidaccesskeyid" in low or "bad_auth_token" in low or "unauthorized" in low or "401" in low or "403" in low and "forbidden" not in low:
        return "The service did not accept those keys or that password. Check them, then select Try again"
    if "unable to authenticate" in low or "ssh: handshake failed" in low:
        return "The SFTP server did not accept that user name and password. Check them, then select Try again"
    if "no such host" in low or "connection refused" in low or "i/o timeout" in low or "dial tcp" in low or "network is unreachable" in low:
        return "Starboard could not reach the service. Check the address and that it is on, then select Try again"
    if "bucket" in low and ("not found" in low or "does not exist" in low or "nosuchbucket" in low):
        return "That bucket is not there, or the key has no access to it. Make the bucket at the service first, or choose one from the list"
    if "quota" in low or ("insufficient" in low and "storage" in low) or "no space" in low:
        return "The service is full. Free some space there, or keep fewer copies"
    if "permission" in low or "forbidden" in low or "access denied" in low:
        return "The service did not let Starboard write there. Choose another folder, or give the key permission to write"
    if "timed out" in low or "deadline exceeded" in low or "terminated" in low:
        return "The service took too long to answer. Select Try again"
    lines = [ln for ln in said.strip().splitlines() if not ln.startswith(("STEP-", "FREE ", "COUNT "))]
    return (lines[-1][-200:] if lines else "The test did not finish. Select Try again")


def save(data_dir, sid, keep, way_remembered=None):
    """Save: the remote and its config go to Copies off this computer, which then copies each new full backup there."""
    sess = _mine(sid)
    if not sess.get("config") or not sess.get("folder"):
        raise CloudError("Sign in and choose the folder first")
    if not (sess.get("test") or {}).get("ok"):
        raise CloudError("Test the connection first: Starboard keeps only a place it could write to")
    try:
        keep = int(keep)
    except (TypeError, ValueError):
        raise ValueError("Keep the newest: give a number from 1 to 50") from None
    if not 1 <= keep <= 50:
        raise ValueError("Keep the newest: give a number from 1 to 50")
    dest = sess.get("dest") or ""
    if dest and not backup_copies._pick(data_dir, dest):
        dest = ""  # the place was removed while signing in: it is added again
    if not dest:
        dest = backup_copies.new_id(data_dir)
        old = backup_copies.blank(data_dir)
        old["id"] = dest
        if len(backup_copies.destinations(data_dir)) >= backup_copies.MAX_PLACES:
            raise ValueError(f"Starboard keeps up to {backup_copies.MAX_PLACES} places. Remove one first")
    else:
        old = backup_copies.settings(data_dir, dest)
    new = {**old, "id": dest, "kind": "rclone", "remote": _target(sess), "keep": keep, "service": sess["service"], "enabled": True,
           "account": sess.get("account") or old.get("account", ""),
           "signin_way": sess["way"] if sess["way"] in ("browser", "phone") else old.get("signin_way", "")}
    sec = {**(backup_copies.secrets(data_dir, dest) if backup_copies._pick(data_dir, dest) else {"smb_password": ""}), "rclone_config": sess["config"]}
    new.pop("detailed_log", None)
    backup_copies.save(data_dir, new, sec, dest)
    result = {**sess["test"], "where": new["remote"]}
    backup_copies.save_test(data_dir, result, dest)
    with _lock:
        global _session
        _end(sess, keep_config=False)
        _session = None
    return new


# Running the helper ----------------------------------------------------------------------------------------------------

class Runner:
    """The helper containers (rclone's pinned image). The example server and the tests put their own in RUN."""

    def _binds(self, sess, work):
        from . import stack
        host = stack.host_folder(sess["data_dir"])
        if not host:
            raise CloudError("Starboard cannot find its own folder on this computer")
        rel = os.path.relpath(work, sess["data_dir"])
        if rel.startswith(".."):
            raise CloudError("That work folder is not Starboard's own")
        return [f"{os.path.dirname(host)}/{rel}:/c"]

    def authorize(self, sess):
        """Starts the sign-in helper and leaves it running (removed by _end)."""
        from . import containers
        if not containers.available():
            raise CloudError("Starboard needs Docker access to sign in")
        backup_copies._pull(backup_copies.RCLONE_IMAGE)
        body = {"Image": backup_copies.RCLONE_IMAGE, "Entrypoint": ["sh", "-c"], "Cmd": [authorize_script(sess)],
                "Labels": {"starboard.updater": "1", "starboard.cloud-signin": "1"},
                "HostConfig": {"Binds": self._binds(sess, sess["work"]), "NetworkMode": "bridge", "Memory": 256 * 1024 ** 2,
                               "PidsLimit": 64, "CapDrop": ["ALL"], "CapAdd": ["CHOWN", "DAC_OVERRIDE", "FOWNER"],
                               "SecurityOpt": ["no-new-privileges:true"]}}
        cid = containers.docker("POST", f"/containers/create?name=starboard-cloud-signin-{sess['id']}", body)["Id"]
        sess["cid"] = cid
        containers.docker("POST", f"/containers/{cid}/start")

    def short(self, sess, script, work):
        """A short helper run with this work folder as /c: (exit code, output)."""
        return backup_copies._helper(script, self._binds(sess, work), image=backup_copies.RCLONE_IMAGE, network="bridge",
                                     timeout=STEP_LIMIT + 30)

    def remove(self, cid):
        from . import containers
        try:
            containers.docker("DELETE", f"/containers/{cid}?force=1")
        except containers.DockerError:
            pass


RUN = Runner()
HTTP = _http


def tidy_leftovers():
    """At start: a sign-in helper left by a Starboard that stopped part way is removed."""
    from . import containers
    if not containers.available():
        return
    try:
        flt = urllib.parse.quote(json.dumps({"label": ["starboard.cloud-signin=1"]}))
        for c in containers.docker("GET", f"/containers/json?all=1&filters={flt}") or []:
            RUN.remove(c["Id"])
    except containers.DockerError:
        pass
