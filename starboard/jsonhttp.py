"""One JSON request to an app, shared by the modules that talk to apps (services, app_setup, media_import, Live TV's
Jellyfin step and others): the body sent as JSON, the answer read up to a limit and parsed, and what an app said
when it answered with an error. Each caller keeps its own words for a person, so urllib's errors pass through:
HTTPError when the app answered with an error (error_words and error_message read what it said), URLError or
OSError when nothing answered, and ValueError when the answer is not JSON.
"""
import json
import urllib.request

USER_AGENT = "Starboard"


def request(url, method="GET", body=None, headers=None, timeout=10, limit=None, opener=None, text=False, full=False):
    """The answer parsed as JSON, or None when it is empty. text: an answer that is not JSON comes back as text.
    limit: at most that many bytes are read. full: (HTTP status, answer). opener: a urllib opener (tests, a socket)."""
    data = json.dumps(body).encode() if body is not None else None
    h = {"Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})}
    if data is not None:
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    # The callers' addresses are an app's, checked to be http(s) when it was saved, or one Starboard chose itself.
    with (opener.open(req, timeout=timeout) if opener else urllib.request.urlopen(req, timeout=timeout)) as r:  # nosec B310
        raw = r.read() if limit is None else r.read(limit)
        status = r.status
    if not raw:
        answer = None
    elif text:
        try:
            answer = json.loads(raw)
        except ValueError:
            answer = raw.decode("utf-8", "replace")
    else:
        answer = json.loads(raw)
    return (status, answer) if full else answer


def error_words(e, limit=300):
    """The start of what an app said with its error, as text ("" when nothing)."""
    try:
        return (e.read(limit) or b"")[:limit].decode("utf-8", "replace").strip()
    except (OSError, ValueError):
        return ""


def error_message(e, limit=20000):
    """The message in an app's JSON error: {"message": ...}, or the *arr apps' [{"errorMessage": ...}]. "" when none."""
    try:
        payload = json.loads(e.read(limit))
    except (OSError, ValueError):
        return ""
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return str(payload[0].get("errorMessage") or "")
    if isinstance(payload, dict):
        return str(payload.get("message") or "")
    return ""

