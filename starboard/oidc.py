"""Single sign-on with OpenID Connect (DASH-512): the authorisation code flow with PKCE, standard library only.

What is checked, in order: the address of the provider is one Starboard may call; the provider's own description
names the same issuer; the state and the browser it was made for match (so nobody can send you a sign-in they
started); the code is swapped for tokens with the client secret and the PKCE verifier; the ID token is RS256, signed
by one of the keys the provider publishes, from the right issuer, for this client, not expired, and carries this
sign-in's nonce; and the person is the one account's owner: a verified email, or a claim the owner chose.

RS256 is RSASSA-PKCS1-v1_5 with SHA-256: the signature raised to the public exponent must equal the padded hash.
Starboard builds the padded hash itself and compares the two in constant time, so it never parses attacker-shaped
padding, and it refuses keys under 2048 bits. Nothing here needs a library.
"""

import base64
import hashlib
import hmac
import ipaddress
import json
import re
import secrets
import socket
import threading
import time
import urllib.parse

from . import outside

TIMEOUT = 10
READ_LIMIT = 1024 * 1024
STATE_LIFE = 600  # seconds from the start of a sign-in to its return
MAX_PENDING = 50
MAX_PENDING_EACH = 5  # in-flight sign-ins from one address; more are refused, nobody else's is ever dropped
SKEW = 120  # seconds of clock difference allowed
KEYS_LIFE = 3600  # the provider's published keys are read again after this long, or once when a token names a new key
KEYS_RETRY = 300  # but not more often than this
DEFAULT_SCOPES = "openid email"
BINDER_COOKIE = "starboard_sso"
_SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def clean_text(text, limit=300):
    """Text that came from a provider, for a log line or a message: control characters become spaces, and it is cut short."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]", " ", str(text))[:limit]


class SignInError(Exception):
    """A sign-in that cannot go on. text is for the person; reason is for the log and never holds a secret."""

    def __init__(self, text, reason=None, code="failed"):
        text, reason = clean_text(text), clean_text(reason or text)
        super().__init__(text)
        self.text, self.reason, self.code = text, reason, code


# Addresses ------------------------------------------------------------------------------------------------------

def _loopback(host):
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def check_address(url, what="address"):
    """https always. http only for an address on this computer itself (a developer's provider, the tests): on a home
    network anyone could answer for the provider, hand out their own keys and sign in as you, and the client secret
    would cross the network in the open."""
    parts = urllib.parse.urlsplit(str(url or ""))
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError(f"The {what} must be an address starting with https://")
    try:
        outside.check_url(url)
    except ValueError as e:
        raise ValueError(str(e)) from None
    if parts.scheme == "http" and not _loopback(parts.hostname):
        raise ValueError(f"The {what} uses http://, which anyone on the network could answer for and so sign in as you, and the client secret would cross it in the open. "
                         "Use https://. Only http://localhost or 127.0.0.1 is allowed, for testing")


DEADLINE = 15  # seconds for a whole request, so a server that sends a byte at a time cannot hold a thread


def allowed_peer(ip):
    """An explicit allowlist test on a resolved address (DASH-542), the last word before a request is sent: True only
    for an ordinary public address, an address on a home network or this computer's own, and never for a link-local,
    multicast, unspecified, reserved or cloud metadata one. outside.bad_address names what is refused and why; this
    says what is let through, so an address neither list thought of is not called."""
    if outside.bad_address(str(ip)):
        return False
    a = ipaddress.ip_address(str(ip).split("%", 1)[0])
    if isinstance(a, ipaddress.IPv6Address) and a.ipv4_mapped:
        a = a.ipv4_mapped
    if a.is_loopback:  # checked first: ::1 sits in the reserved block
        return True
    if a.is_link_local or a.is_multicast or a.is_unspecified or a.is_reserved:
        return False
    return bool(a.is_global or a.is_private)


_REQUEST_PATH = re.compile(r"/[\x21-\x7e]*")  # printable ASCII, no space, no line break: nothing that could start another request


def _addresses(host, port):
    try:
        found = [host] if ipaddress.ip_address(host.split("%", 1)[0]) else []
    except ValueError:
        try:
            found = sorted({i[4][0] for i in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})
        except (OSError, UnicodeError):
            raise OSError("the name does not resolve") from None
    for ip in found:
        why = outside.bad_address(ip)
        if why:
            raise OSError(f"{host} is not allowed: {why}")
        if not allowed_peer(ip):
            raise OSError(f"{host} is not allowed: it is not an ordinary public, home network or local address")
    return found


def _connect(parts, deadline):
    """The address is looked up once, checked, and the connection made to that very address, with the name kept for the
    Host header and for TLS: a name that answers differently a moment later (DNS rebinding) gets nothing."""
    host, port = parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)
    last = None
    for ip in _addresses(host, port):
        try:
            sock = socket.create_connection((ip, port), timeout=max(1, deadline - time.monotonic()))
        except OSError as e:
            last = e
            continue
        if parts.scheme == "https":
            import ssl
            try:
                context = ssl.create_default_context()
                context.minimum_version = ssl.TLSVersion.TLSv1_2  # never the old protocol versions (CodeQL, 23 November 2026)
                sock = context.wrap_socket(sock, server_hostname=host)
            except (ssl.SSLError, OSError) as e:
                sock.close()
                raise OSError(f"TLS failed: {type(e).__name__}") from None
        return sock
    raise last or OSError("no address")


def _fetch(url, form=None, basic=None, what="the provider"):
    check_address(url, "provider address")
    parts = urllib.parse.urlsplit(url)
    headers = {"Accept": "application/json", "User-Agent": "Starboard", "Connection": "close"}
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if basic:
        pair = f"{urllib.parse.quote(basic[0], safe='')}:{urllib.parse.quote(basic[1], safe='')}"
        headers["Authorization"] = "Basic " + base64.b64encode(pair.encode()).decode()
    import http.client
    deadline = time.monotonic() + DEADLINE
    conn = None
    try:
        sock = _connect(parts, deadline)
        if not allowed_peer(sock.getpeername()[0]):  # the address really connected to, checked once more before anything is sent
            sock.close()
            raise OSError("the connection went to an address that is not allowed")
        conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=DEADLINE)
        conn.sock = sock
        sock.settimeout(max(1, deadline - time.monotonic()))
        path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
        if not _REQUEST_PATH.fullmatch(path):
            raise ValueError("the address has characters a request path cannot hold")
        conn.request("POST" if form is not None else "GET", path, body=body, headers=headers)
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
    except (OSError, ValueError, http.client.HTTPException) as e:
        raise SignInError(f"Starboard could not reach {what}", f"could not reach {what}: {type(e).__name__}") from None
    finally:
        if conn:
            conn.close()
    if status >= 300:  # an error, or a redirect, which is never followed
        raise SignInError(f"{what.capitalize()} refused the request ({status})", f"{what} answered {status}")
    if len(raw) > READ_LIMIT:
        raise SignInError(f"{what.capitalize()} sent too much")
    try:
        out = json.loads(raw)
    except ValueError:
        raise SignInError(f"{what.capitalize()} did not answer in the form Starboard expects") from None
    if not isinstance(out, dict):
        raise SignInError(f"{what.capitalize()} did not answer in the form Starboard expects")
    return out


# The provider's description and keys ----------------------------------------------------------------------------

_cache = {"meta": {}, "keys": {}}
_cache_lock = threading.Lock()


def forget():
    with _cache_lock:
        _cache["meta"], _cache["keys"] = {}, {}


def discover(issuer, force=False):
    """The provider's description. Its own issuer must be exactly the one entered, or a token it signs for another
    could be taken for this one's."""
    with _cache_lock:
        hit = _cache["meta"].get(issuer)
    if hit and not force and time.time() - hit[0] < KEYS_LIFE:
        return hit[1]
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    meta = _fetch(url, what="the provider")
    if meta.get("issuer") != issuer:
        raise SignInError(f"The provider says its issuer is {str(meta.get('issuer'))[:200]}. Enter the issuer address exactly like that",
                          "the provider's issuer differs from the one entered")
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not isinstance(meta.get(key), str):
            raise SignInError("The provider's description is missing its sign-in addresses", f"no {key}")
        try:
            check_address(meta[key], "provider address")
        except ValueError as e:
            raise SignInError(str(e)) from None
    if "S256" not in (meta.get("code_challenge_methods_supported") or ["S256"]):
        raise SignInError("The provider does not support PKCE with S256, which Starboard needs", "no S256")
    algs = meta.get("id_token_signing_alg_values_supported")
    if algs and "RS256" not in algs:
        raise SignInError("The provider does not sign with RS256, which Starboard needs", "no RS256")
    with _cache_lock:
        _cache["meta"][issuer] = (time.time(), meta)
    return meta


def _b64(text):
    return base64.urlsafe_b64decode(str(text) + "=" * (-len(str(text)) % 4))


def _int(text):
    return int.from_bytes(_b64(text), "big")


def keys_for(meta, kid, fetch=None):
    """The RSA keys the provider publishes. A key id Starboard does not know makes it read the list again, at most
    every five minutes, so a provider that rotates its keys keeps working and a made-up id cannot make it read often."""
    uri = meta["jwks_uri"]
    with _cache_lock:
        have = _cache["keys"].get(uri)
    fresh = bool(have) and time.time() - have["at"] < KEYS_LIFE
    if fresh and (kid is None or kid in have["by_kid"]):
        return have
    if fresh and time.time() - have["tried"] < KEYS_RETRY:
        return have  # a key id nobody knows, and the list was read a moment ago: no new request
    doc = (fetch or _fetch)(uri, what="the provider's keys")
    by_kid, unnamed = {}, []
    for k in doc.get("keys") or []:
        if not isinstance(k, dict) or k.get("kty") != "RSA" or k.get("use", "sig") != "sig" or k.get("alg", "RS256") != "RS256":
            continue
        try:
            n, e = _int(k["n"]), _int(k["e"])
        except (KeyError, ValueError, TypeError):
            continue
        if n.bit_length() < 2048 or e < 3 or e % 2 == 0 or e.bit_length() > 32:
            continue
        if k.get("kid") is None:
            unnamed.append((n, e))
        else:
            by_kid[str(k["kid"])] = (n, e)
    entry = {"at": time.time(), "tried": time.time(), "by_kid": by_kid, "unnamed": unnamed}
    with _cache_lock:
        _cache["keys"][uri] = entry
    return entry


# The ID token ---------------------------------------------------------------------------------------------------

def rs256_valid(n, e, signed, signature):
    k = (n.bit_length() + 7) // 8
    if n.bit_length() < 2048 or len(signature) != k:
        return False
    s = int.from_bytes(signature, "big")
    if s >= n:
        return False
    recovered = pow(s, e, n).to_bytes(k, "big")
    t = _SHA256_PREFIX + hashlib.sha256(signed).digest()
    expected = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return hmac.compare_digest(recovered, expected)


def verify_id_token(token, meta, issuer, client_id, nonce, now=None, fetch=None):
    """The claims of an ID token that is genuine, from this provider, for this client and this sign-in."""
    now = time.time() if now is None else now
    parts = str(token or "").split(".")
    if len(parts) != 3 or any(not p or len(p) > 20000 for p in parts):
        raise SignInError("The provider's ID token is not in the expected form", "ID token is not three parts")
    try:
        header = json.loads(_b64(parts[0]))
        claims = json.loads(_b64(parts[1]))
        signature = _b64(parts[2])
    except (ValueError, TypeError):
        raise SignInError("The provider's ID token could not be read", "ID token is not valid JSON") from None
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise SignInError("The provider's ID token could not be read", "ID token is not an object")
    if header.get("alg") != "RS256" or "crit" in header:
        raise SignInError("The provider's ID token is not signed with RS256", f"alg {str(header.get('alg'))[:20]} refused")
    kid = header.get("kid")
    entry = keys_for(meta, None if kid is None else str(kid), fetch)
    candidates = [entry["by_kid"][str(kid)]] if kid is not None and str(kid) in entry["by_kid"] else \
        (entry["unnamed"] + ([] if kid is not None else list(entry["by_kid"].values())))
    signed = (parts[0] + "." + parts[1]).encode("ascii", "replace")
    if not any(rs256_valid(n, e, signed, signature) for n, e in candidates):
        raise SignInError("The provider's ID token signature is not right", "signature does not match the provider's keys")
    if not isinstance(claims.get("iss"), str) or not hmac.compare_digest(claims["iss"].encode(), issuer.encode()):
        raise SignInError("The ID token is from another issuer", "iss differs")
    aud = claims.get("aud")
    audience = [aud] if isinstance(aud, str) else aud if isinstance(aud, list) and all(isinstance(a, str) for a in aud) else []
    if client_id not in audience:
        raise SignInError("The ID token is for another application", "aud does not name this client")
    if len(audience) > 1 and claims.get("azp") != client_id:
        raise SignInError("The ID token is for several applications", "azp is not this client")
    for key in ("exp", "iat"):
        if not isinstance(claims.get(key), (int, float)) or isinstance(claims.get(key), bool):
            raise SignInError("The ID token has no time on it", f"{key} missing")
    if claims["exp"] <= now - SKEW:
        raise SignInError("The ID token has expired", "exp is in the past")
    if claims["iat"] > now + SKEW:
        raise SignInError("The ID token is from the future. Check that this computer's clock is right", "iat is in the future")
    if isinstance(claims.get("nbf"), (int, float)) and claims["nbf"] > now + SKEW:
        raise SignInError("The ID token is not valid yet", "nbf is in the future")
    if not isinstance(claims.get("nonce"), str) or not hmac.compare_digest(claims["nonce"].encode(), nonce.encode()):
        raise SignInError("The ID token belongs to another sign-in", "nonce differs")
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise SignInError("The ID token names nobody", "no sub")
    return claims


def is_owner(claims, claim, value):
    """True when the claim the owner chose holds the value the owner gave. Email needs the provider to say it checked
    the address. A claim that is a list (groups) matches when the value is in it."""
    value = str(value or "").strip()
    if not claim or not value:
        return False
    got = claims.get(claim)
    if claim == "email":
        if claims.get("email_verified") not in (True, "true"):
            return False
        got, value = (str(got).strip().lower() if isinstance(got, str) else None), value.lower()
    items = got if isinstance(got, list) else [got]
    hit = False
    for item in items:
        if isinstance(item, str) and hmac.compare_digest(item.encode(), value.encode()):
            hit = True
    return hit


# One sign-in in progress ----------------------------------------------------------------------------------------

_pending = {}
_pending_lock = threading.Lock()


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def begin(cfg, remember=False, test=False, address=""):
    """(the address to send the browser to, the binder for its cookie). The state, nonce and PKCE verifier stay here."""
    meta = discover(cfg["issuer"])
    state, nonce, verifier, binder = (secrets.token_urlsafe(24) for _ in range(4))
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    now = time.time()
    with _pending_lock:
        for k in [k for k, v in _pending.items() if v["until"] < now]:
            del _pending[k]
        if len(_pending) >= MAX_PENDING or sum(1 for v in _pending.values() if v.get("address") == address) >= MAX_PENDING_EACH:
            raise SignInError("Too many sign-ins are waiting. Try again in a few minutes", "too many pending sign-ins", "limited")
        _pending[_hash(state)] = {"address": address, "nonce": nonce, "verifier": verifier, "binder": _hash(binder), "until": now + STATE_LIFE,
                                  "remember": bool(remember), "test": bool(test)}
    query = urllib.parse.urlencode({
        "response_type": "code", "client_id": cfg["client_id"], "redirect_uri": cfg["redirect_uri"],
        "scope": cfg.get("scopes") or DEFAULT_SCOPES, "state": state, "nonce": nonce,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    sep = "&" if "?" in meta["authorization_endpoint"] else "?"
    return meta["authorization_endpoint"] + sep + query, binder


def finish(cfg, state, code, binder, now=None, fetch_tokens=None, fetch_keys=None):
    """Swaps the code for tokens and returns (the claims, remember, test). Raises SignInError."""
    if not isinstance(state, str) or not isinstance(code, str) or not state or not code or len(state) > 200 or len(code) > 2000:
        raise SignInError("The provider did not send a sign-in back", "no state or code")
    with _pending_lock:  # taken out on first use: a state works once
        item = _pending.pop(_hash(state), None)
    if not item or item["until"] < (time.time() if now is None else now):
        raise SignInError("This sign-in has expired or was not started here. Start again", "unknown or expired state", "expired")
    if not binder or not hmac.compare_digest(item["binder"], _hash(binder)):
        raise SignInError("This sign-in was started in another browser. Start again", "state not made for this browser")
    meta = discover(cfg["issuer"])
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": cfg["redirect_uri"], "code_verifier": item["verifier"]}
    methods = meta.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"]
    if "client_secret_basic" in methods:
        basic = (cfg["client_id"], cfg["client_secret"])
    else:
        basic, form = None, {**form, "client_id": cfg["client_id"], "client_secret": cfg["client_secret"]}
    tokens = (fetch_tokens or _fetch)(meta["token_endpoint"], form=form, basic=basic, what="the provider's token address")
    if str(tokens.get("token_type", "bearer")).lower() != "bearer" or not tokens.get("id_token"):
        raise SignInError("The provider did not send an ID token. Check that the openid scope is allowed", "no id_token")
    nonce = item["nonce"]
    claims = verify_id_token(tokens["id_token"], meta, cfg["issuer"], cfg["client_id"], nonce, now, fetch_keys)
    return claims, item["remember"], item["test"]


def forget_pending():
    with _pending_lock:
        _pending.clear()
