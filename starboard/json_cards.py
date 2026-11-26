"""A custom card for any service's JSON (DASH-555, owner, 23 November 2026): a person gives an address, with an optional
key, and chooses which fields of the JSON answer to show, each with a label, a unit and a rule for its status. Starboard
draws them as a small table of keys and values on a dashboard card, with a row for the card in Other services.

What it costs: nothing at rest. A card is asked only when the dashboard shows it, or when a person presses Ask now, and a
card's answer is kept for the refresh time it was given (one minute to one hour) however many people look, so the
service is not asked more often than that. Only the chosen fields are kept (a few numbers and words, never the whole
answer), and nothing is read while the dashboard is hidden or closed.

What it will call, the same checks as the sign-in provider's request (oidc.py): the address is looked up once and the
connection goes to that very address; every address it resolves to must be on the home network (this computer, 10.x,
172.16 to 172.31, 192.168.x, 100.64 to 100.127 as Tailscale uses, and the private IPv6 range) unless the owner has allowed
others, and even then never a link-local, multicast, reserved or cloud metadata one; a redirect is never followed; the
whole request has a deadline; the answer has a size limit; and a key is never sent in the open to an address that is not on
the home network. A saved key goes only to the server it was saved for.

Fields are named by a path through the JSON: dots between names and numbers for list entries (data.queue.total, or
items.0.name; items[0].name also works). A path that reaches a list shows how many entries it has.
"""
import ipaddress
import json
import re
import secrets
import threading
import time
import urllib.parse

from . import oidc, outside

MAX_CARDS = 12
MAX_FIELDS = 20
READ_LIMIT = 256 * 1024
DEADLINE = 8  # seconds for a whole request
REFRESH = (60, 300, 900, 1800, 3600)  # seconds a card's answer is kept
DEFAULT_REFRESH = 60
FAILED_KEEP = 30  # a failed ask is not repeated sooner than this, so a service that is down is not hammered
FRESH_GAP = 5  # Ask now at most this often for one card
OPS = {"above": "is above", "below": "is below", "equals": "is", "not_equals": "is not", "contains": "contains", "not_contains": "does not contain"}
KEY_STYLES = {"x-api-key": "X-Api-Key header", "bearer": "Bearer token"}
BAD = ("warning", "problem")
ID_RE = re.compile(r"^jc[0-9a-f]{8}$")
SECRETISH = re.compile(r"token|secret|passw|apikey|api_key|api-key|authorization|credential|cookie", re.I)
def _v4(a, b, prefix):
    return ipaddress.ip_network(((a << 24) | (b << 16), prefix))


# This computer (127.x), 10.x, 172.16 to 172.31, 192.168.x, 100.64 to 100.127 (Tailscale), and IPv6's own and private ranges.
HOME_NETWORKS = [_v4(127, 0, 8), _v4(10, 0, 8), _v4(172, 16, 12), _v4(192, 168, 16), _v4(100, 64, 10),
                 ipaddress.ip_network("::1/128"), ipaddress.ip_network("fc00::/7")]
DEFAULT = {"allow_outside": False, "cards": []}

_cache = {}  # card id -> {"at", "answer", "ok"}
_locks = {}
_guard = threading.Lock()


class CardError(Exception):
    """Something a person can read and act on. Never holds a key."""

    def __init__(self, text, status=400):
        super().__init__(oidc.clean_text(text, 400))
        self.text, self.status = oidc.clean_text(text, 400), status


# Addresses -----------------------------------------------------------------------------------------------------------

def on_home_network(ip):
    try:
        a = ipaddress.ip_address(str(ip).split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
        a = a.ipv4_mapped
    return any(a in n for n in HOME_NETWORKS)


def home_peer(ip):
    """A resolved address that may be called when only the home network is allowed."""
    return oidc.allowed_peer(ip) and on_home_network(ip)


def check_address(url, allow_outside, resolve=None):
    """Raises CardError with the reason when an address cannot be used; None when it can. A name that does not resolve
    here is let through (Starboard cannot reach it either, and asking says so)."""
    text = str(url or "").strip()
    parts = urllib.parse.urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.fragment or re.search(r"\s", text):
        raise CardError("The address must start with http:// or https://, with no spaces, no user name or password and no # part. Put a key in the Key box")
    try:
        parts.port
    except ValueError:
        raise CardError("The address has a port that is not a number from 1 to 65535") from None
    try:
        outside.check_url(text, resolve)
    except ValueError as e:
        raise CardError(str(e)) from None
    if allow_outside:
        return
    host = parts.hostname
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
        found = [host]
    except ValueError:
        try:
            found = sorted({i[4][0] for i in (resolve or oidc.socket.getaddrinfo)(host, parts.port or (443 if parts.scheme == "https" else 80), type=oidc.socket.SOCK_STREAM)})
        except (OSError, UnicodeError):
            return
    for ip in found:
        if not on_home_network(ip):
            raise CardError(f"{host} is not on your home network. A custom card asks home network addresses only, unless you allow others in Other services, Custom cards")


# One request -----------------------------------------------------------------------------------------------------------

def _headers(key, style):
    out = {"Accept": "application/json", "User-Agent": "Starboard", "Connection": "close"}
    if key:
        if style == "bearer":
            out["Authorization"] = "Bearer " + key
        else:
            out["X-Api-Key"] = key
    return out


def fetch(url, key="", style="x-api-key", allow_outside=False):
    """One GET: the JSON answer, parsed. CardError says what went wrong in words for the person."""
    import http.client
    check_address(url, allow_outside)
    parts = urllib.parse.urlsplit(url)
    peer = oidc.allowed_peer if allow_outside else home_peer
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    if not oidc._REQUEST_PATH.fullmatch(path):
        raise CardError("The address has characters a request cannot hold. Use letters, numbers and the usual punctuation only")
    deadline = time.monotonic() + DEADLINE
    conn = None
    try:
        sock = oidc._connect(parts, deadline, peer)
        ip = sock.getpeername()[0]
        if not peer(ip):  # the address really connected to, checked once more before anything is sent
            sock.close()
            raise OSError("the connection went to an address that is not allowed")
        if key and parts.scheme == "http" and not on_home_network(ip):
            sock.close()
            raise CardError("A key is not sent to an address outside your home network over http://. Use https://")
        conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=DEADLINE)
        conn.sock = sock
        sock.settimeout(max(1, deadline - time.monotonic()))
        conn.request("GET", path, headers=_headers(key, style))
        r = conn.getresponse()
        raw = b""
        while len(raw) <= READ_LIMIT and not r.isclosed():
            left = deadline - time.monotonic()
            if left <= 0:
                raise OSError("too slow")
            sock.settimeout(left)
            chunk = r.read1(8192)
            if not chunk:
                break
            raw += chunk
        status = r.status
    except CardError:
        raise
    except (OSError, ValueError, http.client.HTTPException) as e:
        text = str(e) if isinstance(e, OSError) and "not allowed" in str(e) else ""
        raise CardError(text or f"Starboard could not reach that address ({type(e).__name__})", 502) from None
    finally:
        if conn:
            conn.close()
    if 300 <= status < 400:
        raise CardError(f"The service answered {status}, which sends Starboard somewhere else. A redirect is never followed: use the address it redirects to", 502)
    if status in (401, 403):
        raise CardError(f"The service refused the request ({status}). Check the key and how it is sent", 502)
    if status >= 400:
        raise CardError(f"The service answered with an error ({status})", 502)
    if len(raw) > READ_LIMIT:
        raise CardError(f"The service sent more than {READ_LIMIT // 1024} KB, which is too much for a card", 502)
    try:
        doc = json.loads(raw)
    except ValueError:
        raise CardError("The service did not answer in JSON", 502) from None
    if not isinstance(doc, (dict, list)):
        raise CardError("The service answered with a single value, not an object or a list", 502)
    return doc


# Paths, values and rules ---------------------------------------------------------------------------------------------

def parse_path(path):
    text = str(path or "").strip()
    if not text or len(text) > 200 or re.search(r"[\x00-\x1f]", text):
        raise ValueError("Enter the path to a field, such as data.queue.total")
    tokens = re.findall(r"[^.\[\]]+", text)
    if not tokens or len(tokens) > 12:
        raise ValueError("Enter the path to a field, such as data.queue.total")
    return tokens


def pick(doc, tokens):
    """(found, value) for a path through the JSON."""
    cur = doc
    for t in tokens:
        if isinstance(cur, dict) and t in cur:
            cur = cur[t]
        elif isinstance(cur, list) and t.isdigit() and int(t) < len(cur):
            cur = cur[int(t)]
        else:
            return False, None
    return True, cur


def _number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip().replace(",", ""))
    except ValueError:
        return None


def display(value):
    """(text, kind) for what a field holds: numbers with thousands, yes or no, words cut short, a list's length."""
    if value is None:
        return "Empty", "empty"
    if isinstance(value, bool):
        return ("Yes" if value else "No"), "bool"
    if isinstance(value, (int, float)):
        if isinstance(value, float) and value != value or value in (float("inf"), float("-inf")):
            return "Not a number", "number"
        return (f"{value:,}" if isinstance(value, int) else f"{value:,.2f}".rstrip("0").rstrip(".")), "number"
    if isinstance(value, list):
        return (f"{len(value):,} {'entry' if len(value) == 1 else 'entries'}"), "list"
    if isinstance(value, dict):
        return f"{len(value):,} {'field' if len(value) == 1 else 'fields'}", "object"
    return oidc.clean_text(value, 120).strip() or "Empty", "text"


def judge(rule, value):
    """"ok" when the rule's condition holds, else the level the rule gives (warning or problem); None without a rule."""
    if not rule:
        return None
    bad = rule.get("bad") if rule.get("bad") in BAD else "warning"
    op, want = rule.get("op"), str(rule.get("value", ""))
    if isinstance(value, (dict, list)) and op in ("above", "below"):
        return bad
    if op in ("above", "below"):
        a, b = _number(value), _number(want)
        if a is None or b is None:
            return bad
        return "ok" if (a > b if op == "above" else a < b) else bad
    text = ("yes" if value else "no") if isinstance(value, bool) else str(value if value is not None else "")
    if op in ("equals", "not_equals"):
        a, b = _number(value), _number(want)
        same = a == b if a is not None and b is not None else text.strip().lower() == want.strip().lower()
        if isinstance(value, bool) and want.strip().lower() in ("true", "false"):
            same = bool(value) == (want.strip().lower() == "true")
        return "ok" if same == (op == "equals") else bad
    if op in ("contains", "not_contains"):
        has = want.strip().lower() in text.lower()
        return "ok" if has == (op == "contains") else bad
    return None


def rows_of(doc, fields):
    """The chosen fields of an answer, each with its words, its unit and its status."""
    out = []
    for f in fields:
        found, value = pick(doc, parse_path(f["path"]))
        if not found:
            out.append({"label": f["label"], "value": "Not in the answer", "unit": "", "state": "warning"})
            continue
        words, kind = display(value)
        shown = f.get("unit", "") if kind in ("number", "text") else ""
        out.append({"label": f["label"], "value": words, "unit": shown, "state": judge(f.get("rule"), value)})
    return out


def overall(rows):
    states = [r["state"] for r in rows if r["state"]]
    if not states:
        return None
    return "problem" if "problem" in states else "warning" if "warning" in states else "ok"


def leaves(doc, limit=300, depth=6):
    """Every field a person could choose, in the order of the answer: {path, sample, kind}. A list is offered as itself
    (how many entries) and its first three entries are opened. A field that looks like a secret has its sample hidden."""
    out = []

    def walk(value, path, level):
        if len(out) >= limit:
            return
        if path:
            words, kind = display(value)
            hidden = SECRETISH.search(path.rsplit(".", 1)[-1]) and kind == "text"
            out.append({"path": path, "sample": "Hidden: it looks like a secret" if hidden else words[:60], "kind": kind})
        if level >= depth:
            return
        if isinstance(value, dict):
            for k, v in list(value.items())[:60]:
                if re.fullmatch(r"[^.\[\]\x00-\x1f]{1,60}", str(k)):
                    walk(v, f"{path}.{k}" if path else str(k), level + 1)
        elif isinstance(value, list):
            for i, v in enumerate(value[:3]):
                walk(v, f"{path}.{i}" if path else str(i), level + 1)

    walk(doc, "", 0)
    return out, len(out) >= limit


# Cards, as saved ---------------------------------------------------------------------------------------------------

def section(data):
    s = data.setdefault("json_cards", json.loads(json.dumps(DEFAULT)))
    s.setdefault("allow_outside", False)
    s.setdefault("cards", [])
    return s


def _text(v, limit):
    return oidc.clean_text(str(v if v is not None else ""), limit).strip()


def clean_rule(rule):
    if not rule:
        return None
    if not isinstance(rule, dict) or rule.get("op") not in OPS:
        raise CardError("Choose how the rule compares the value")
    want = _text(rule.get("value"), 60)
    if not want:
        raise CardError("Enter the value the rule compares with")
    if rule["op"] in ("above", "below") and _number(want) is None:
        raise CardError("Above and below compare numbers: enter a number")
    return {"op": rule["op"], "value": want, "bad": rule.get("bad") if rule.get("bad") in BAD else "warning"}


def clean_fields(fields):
    if not isinstance(fields, list) or not fields:
        raise CardError("Choose at least one field to show")
    if len(fields) > MAX_FIELDS:
        raise CardError(f"A card shows {MAX_FIELDS} fields at most")
    out, seen = [], set()
    for f in fields:
        if not isinstance(f, dict):
            raise CardError("A field is not in the form Starboard expects")
        try:
            tokens = parse_path(f.get("path"))
        except ValueError as e:
            raise CardError(str(e)) from None
        path = ".".join(tokens)
        if path in seen:
            raise CardError(f"{path} is chosen twice")
        seen.add(path)
        label = _text(f.get("label"), 40) or tokens[-1][:40]
        out.append({"path": path, "label": label, "unit": _text(f.get("unit"), 12), "rule": clean_rule(f.get("rule"))})
    return out


def public_card(c, with_state=True):
    out = {"id": c["id"], "name": c["name"], "url": c["url"], "has_key": bool(c.get("key")), "key_style": c.get("key_style", "x-api-key"),
           "refresh": c.get("refresh", DEFAULT_REFRESH), "fields": c["fields"]}
    if with_state:
        last = _cache.get(c["id"])
        out["last"] = ({"state": last["answer"].get("state"), "problem": last["answer"].get("problem"), "asked": last["answer"].get("asked")}
                       if last else None)
    return out


def listing(cfg):
    s = section(cfg.data)
    return {"allow_outside": bool(s["allow_outside"]), "cards": [public_card(c) for c in s["cards"]], "max": MAX_CARDS,
            "refresh": list(REFRESH), "ops": OPS, "key_styles": KEY_STYLES}


def save_card(cfg, incoming):
    """Adds a card or changes one (when it names an id). A blank key keeps the saved one, but never sends it to a
    different server; clear_key removes it."""
    if not isinstance(incoming, dict):
        raise CardError("Send the card as an object")
    name = _text(incoming.get("name"), 40)
    if not name:
        raise CardError("Enter a name for the card")
    url = str(incoming.get("url") or "").strip()[:300]
    if not url:
        raise CardError("Enter the address of the service's JSON")
    fields = clean_fields(incoming.get("fields"))
    refresh = incoming.get("refresh", DEFAULT_REFRESH)
    if refresh not in REFRESH:
        raise CardError("Choose how often from the list")
    style = incoming.get("key_style", "x-api-key")
    if style not in KEY_STYLES:
        raise CardError("Choose how the key is sent from the list")
    typed = str(incoming.get("key") or "").strip()[:2000]
    with cfg.lock:
        s = section(cfg.data)
        check_address(url, bool(s["allow_outside"]))
        old = next((c for c in s["cards"] if c["id"] == incoming.get("id")), None) if incoming.get("id") else None
        if incoming.get("id") and not old:
            raise CardError("That card is not there any more", 404)
        if not old and len(s["cards"]) >= MAX_CARDS:
            raise CardError(f"Starboard keeps {MAX_CARDS} custom cards at most. Remove one first")
        from .config import same_server
        saved = old.get("key", "") if old else ""
        if incoming.get("clear_key"):
            saved = ""
        elif saved and not typed and not same_server(old["url"], url):
            raise CardError("The address changed to a different server, so the saved key was not sent. Enter the key for the new address, or choose Remove the saved key")
        key = typed or saved
        card = {"id": old["id"] if old else "jc" + secrets.token_hex(4), "name": name, "url": url, "key": key, "key_style": style,
                "refresh": refresh, "fields": fields}
        if old:
            s["cards"][s["cards"].index(old)] = card
        else:
            s["cards"].append(card)
        cfg.save()
    forget(card["id"])
    return public_card(card)


def delete_card(cfg, card_id):
    with cfg.lock:
        s = section(cfg.data)
        if not any(c["id"] == card_id for c in s["cards"]):
            raise CardError("That card is not there any more", 404)
        s["cards"] = [c for c in s["cards"] if c["id"] != card_id]
        dash = cfg.data.get("dashboard") or {}
        if isinstance(dash.get("cards"), list):  # it leaves the dashboard with it
            dash["cards"] = [c for c in dash["cards"] if c.get("id") != f"json:{card_id}"]
        cfg.save()
    forget(card_id)


def set_allow_outside(cfg, on):
    with cfg.lock:
        section(cfg.data)["allow_outside"] = bool(on)
        cfg.save()
    forget()


def clean_all(value):
    """The saved section as a backup carries it, checked again on restore: only what a card may hold."""
    out = json.loads(json.dumps(DEFAULT))
    if not isinstance(value, dict):
        return out
    out["allow_outside"] = value.get("allow_outside") is True
    for c in (value.get("cards") if isinstance(value.get("cards"), list) else [])[:MAX_CARDS]:
        try:
            fields = clean_fields(c.get("fields"))
            url = str(c.get("url") or "").strip()[:300]
            parts = urllib.parse.urlsplit(url)
            if not ID_RE.match(str(c.get("id"))) or parts.scheme not in ("http", "https") or not parts.hostname:
                continue
            out["cards"].append({"id": c["id"], "name": _text(c.get("name"), 40) or "Custom card", "url": url, "key": str(c.get("key") or "")[:2000],
                                 "key_style": c.get("key_style") if c.get("key_style") in KEY_STYLES else "x-api-key",
                                 "refresh": c.get("refresh") if c.get("refresh") in REFRESH else DEFAULT_REFRESH, "fields": fields})
        except (CardError, AttributeError, TypeError):
            continue
    return out


# Asking ------------------------------------------------------------------------------------------------------------

def forget(card_id=None):
    with _guard:
        if card_id:
            _cache.pop(card_id, None)
        else:
            _cache.clear()


def _answer_of(card, rows=None, problem=None):
    state = "problem" if problem else overall(rows)
    return {"id": card["id"], "name": card["name"], "state": state, "items": rows or [], "problem": problem, "asked": int(time.time())}


def answer(cfg, card_id, fresh=False, now=None):
    """The card's answer: the kept one while it is younger than the card's refresh time, else the service is asked once.
    fresh (Ask now) asks again at once but never more often than every FRESH_GAP seconds."""
    now = now if now is not None else time.monotonic()
    with cfg.lock:
        s = section(cfg.data)
        card = next((c for c in s["cards"] if c["id"] == card_id), None)
        allow = bool(s["allow_outside"])
        card = json.loads(json.dumps(card)) if card else None
    if not card:
        raise CardError("That card is not there any more", 404)
    with _guard:
        lock = _locks.setdefault(card_id, threading.Lock())
    with lock:  # one ask at a time for a card, and the one who waited uses its answer
        kept = _cache.get(card_id)
        if kept:
            age = now - kept["at"]
            life = card["refresh"] if kept["ok"] else FAILED_KEEP
            if age < (FRESH_GAP if fresh else life):
                return dict(kept["answer"], cached=True)
        try:
            doc = fetch(card["url"], card.get("key", ""), card.get("key_style", "x-api-key"), allow)
            result, ok = _answer_of(card, rows_of(doc, card["fields"])), True
        except CardError as e:
            result, ok = _answer_of(card, problem=e.text), False
        with _guard:
            _cache[card_id] = {"at": now, "answer": result, "ok": ok}
        return dict(result, cached=False)


def probe(cfg, incoming):
    """Asks an address once for the fields to choose from, with the key typed or the saved one for that card."""
    url = str(incoming.get("url") or "").strip()[:300]
    if not url:
        raise CardError("Enter the address of the service's JSON")
    style = incoming.get("key_style", "x-api-key")
    if style not in KEY_STYLES:
        raise CardError("Choose how the key is sent from the list")
    key = str(incoming.get("key") or "").strip()[:2000]
    with cfg.lock:
        s = section(cfg.data)
        allow = bool(s["allow_outside"])
        old = next((c for c in s["cards"] if c["id"] == incoming.get("id")), None)
        if old and not key and not incoming.get("clear_key"):
            from .config import same_server
            if same_server(old["url"], url):
                key = old.get("key", "")
    doc = fetch(url, key, style, allow)
    found, more = leaves(doc)
    return {"fields": found, "more": more, "type": "list" if isinstance(doc, list) else "object"}
