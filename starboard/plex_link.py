"""Signing in to Plex with Plex's own link code (DASH-595, owner, 26 November 2026).

Starboard does not read Plex's token from the Plex container. A person either pastes the token or signs in here:
Starboard asks plex.tv for a four-character code, the page shows it with plex.tv/link, and the person approves it in
Plex. The page asks for the answer while it is open; the server never asks plex.tv by itself, so nothing runs while
the page is closed. The token stays in this module's memory until the app is saved or tested: it is never sent to the
browser, never written to a log and never kept when the code runs out, is cancelled or the server restarts.
"""
import os
import secrets
import threading
import time
import urllib.error

from . import jsonhttp

PINS_URL = "https://plex.tv/api/v2/pins"
LINK_PAGE = "https://plex.tv/link"
TIMEOUT = 10
LIFE = 300  # seconds a code may wait for approval: five minutes, then it is dropped (Plex's own is longer)
MAX_PENDING = 3
SAME_ANSWER = 1.5  # seconds: a second ask this soon gets the last answer, so a busy page cannot flood plex.tv

_call = jsonhttp.request  # tests and the example server put a stand-in here; plex.tv is never called from them
_lock = threading.Lock()
_pending = {}  # Plex's pin id -> {"code", "client", "until", "token", "state", "asked"}


class LinkError(Exception):
    """Said in words for the page; never carries a token."""


def client_id(data_dir):
    """A name for this Starboard that Plex shows in its list of signed-in apps. Not a secret; made once, kept in the data folder."""
    path = os.path.join(data_dir, "plex-client-id")
    try:
        with open(path, encoding="ascii") as f:
            found = f.read().strip()
        if 16 <= len(found) <= 64 and found.isalnum():
            return found
    except OSError:
        pass
    found = secrets.token_hex(16)
    try:
        with open(path, "w", encoding="ascii") as f:
            f.write(found)
    except OSError:
        pass
    return found


def _headers(client):
    return {"X-Plex-Client-Identifier": client, "X-Plex-Product": "Starboard", "X-Plex-Device-Name": "Starboard", "Accept": "application/json"}


def _forget_old(now):
    for pid in [p for p, v in _pending.items() if v["until"] <= now or v["state"] in ("cancelled", "expired")]:
        _pending.pop(pid, None)


def start(data_dir, call=None, now=time.time):
    """Asks plex.tv for a code. Returns {"id", "code", "link", "expires_in"}."""
    call = call or _call
    client = client_id(data_dir)
    try:
        answer = call(PINS_URL + "?strong=false", "POST", headers=_headers(client), timeout=TIMEOUT, limit=20000)
    except urllib.error.HTTPError as e:
        raise LinkError(f"plex.tv did not give a code (it answered {e.code}). Try again, or paste the token") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise LinkError("Starboard could not reach plex.tv. Check the server's internet connection, or paste the token") from None
    pid, code = (answer or {}).get("id") if isinstance(answer, dict) else None, (answer or {}).get("code") if isinstance(answer, dict) else None
    if not isinstance(pid, int) or not isinstance(code, str) or not code.isalnum() or len(code) > 12:
        raise LinkError("plex.tv gave an answer Starboard does not know. Try again, or paste the token")
    t = now()
    with _lock:
        _forget_old(t)
        while len(_pending) >= MAX_PENDING:  # the oldest goes: a page that was closed without Cancel
            _pending.pop(min(_pending, key=lambda p: _pending[p]["until"]))
        _pending[pid] = {"code": code, "client": client, "until": t + LIFE, "token": "", "state": "waiting", "asked": 0.0}
    return {"id": pid, "code": code, "link": LINK_PAGE, "expires_in": LIFE}


def poll(pid, call=None, now=time.time):
    """{"state": "waiting" | "approved" | "expired" | "cancelled", "left": seconds}. Asks plex.tv once per call
    (at most every second and a half). The token is kept here, not returned."""
    call = call or _call
    t = now()
    with _lock:
        item = _pending.get(pid)
        if not item:
            return {"state": "expired", "left": 0}
        if item["state"] == "approved":
            return {"state": "approved", "left": 0}
        if item["until"] <= t:
            _pending.pop(pid, None)
            return {"state": "expired", "left": 0}
        if item["state"] == "cancelled":
            return {"state": "cancelled", "left": 0}
        if t - item["asked"] < SAME_ANSWER:
            return {"state": "waiting", "left": int(item["until"] - t)}
        item["asked"] = t
        client, code = item["client"], item["code"]
    try:
        answer = call(f"{PINS_URL}/{int(pid)}?code={code}", "GET", headers=_headers(client), timeout=TIMEOUT, limit=20000)
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):  # plex.tv has dropped the code
            with _lock:
                _pending.pop(pid, None)
            return {"state": "expired", "left": 0}
        raise LinkError(f"plex.tv answered {e.code}. The page tries again") from None
    except (urllib.error.URLError, OSError, ValueError):
        raise LinkError("Starboard could not reach plex.tv. The page tries again") from None
    token = (answer or {}).get("authToken") if isinstance(answer, dict) else None
    with _lock:
        item = _pending.get(pid)
        if not item:
            return {"state": "expired", "left": 0}
        if isinstance(token, str) and 10 <= len(token) <= 200 and token.replace("-", "").replace("_", "").isalnum():
            item["token"], item["state"] = token, "approved"
            return {"state": "approved", "left": 0}
        return {"state": "waiting", "left": max(0, int(item["until"] - t))}


def cancel(pid):
    with _lock:
        _pending.pop(pid, None)


def token_of(pid, keep=False, now=time.time):
    """The token a finished sign-in found, for saving or testing the app; "" when there is none (not approved, expired,
    or already used). keep: leave it for a second use (the test, then the save)."""
    with _lock:
        item = _pending.get(pid) if isinstance(pid, int) else None
        if not item or item["state"] != "approved" or item["until"] + LIFE <= now():
            return ""
        token = item["token"]
        if not keep:
            _pending.pop(pid, None)
        return token


def reset():
    with _lock:
        _pending.clear()
