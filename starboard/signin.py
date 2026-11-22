"""Starboard's own sign-in methods beyond the password (DASH-512): a two-step code and single sign-on.

Both are off until set up in Settings, Security, Sign-in. The password keeps working unless the owner turns it
off on purpose, and ./reset-sign-in.sh on the server turns both off and the password back on, whatever state
they are in. What is kept lives in the settings file under "auth", which a settings backup never includes:

    auth.totp  = {enabled, secret, pending, last_step, recovery: [hashes]}
    auth.oidc  = {enabled, name, issuer, client_id, client_secret, redirect_uri, scopes, claim, value, tested}
    auth.password_login = False  only when the owner deactivated it

The secrets are never sent to the browser, never written to a log or the audit log, and never put in an address.
"""

import hashlib
import secrets
import threading
import time

from . import api_v1, logs, oidc, qr, totp

CHALLENGE_LIFE = 300
MAX_CHALLENGES = 20
CHALLENGE_TRIES = 5
MAX_NAME = 40
MAX_FIELD = 300
CLAIM_OK = "abcdefghijklmnopqrstuvwxyz0123456789_-:."


class SigninError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def section(app, name):
    return app.config.data.setdefault("auth", {}).get(name) or {}


# State ------------------------------------------------------------------------------------------------------------

def password_allowed(app):
    return app.config.data.get("auth", {}).get("password_login", True) is not False


def totp_on(app):
    t = section(app, "totp")
    return bool(t.get("enabled") and t.get("secret"))


def sso_on(app):
    o = section(app, "oidc")
    return bool(o.get("enabled") and o.get("issuer") and o.get("client_id") and o.get("client_secret") and o.get("redirect_uri"))


def for_login_page(app):
    """What the sign-in page may know before anyone has signed in: the name on the button, and whether a password works."""
    o = section(app, "oidc")
    return {"sso": {"name": o.get("name") or "Single sign-on"} if sso_on(app) else None, "password_login": password_allowed(app)}


def status(app):
    """For Settings: everything but the secrets, which are only said to exist."""
    t, o = section(app, "totp"), section(app, "oidc")
    return {
        "password_login": password_allowed(app),
        "totp": {"enabled": totp_on(app), "recovery_left": len(t.get("recovery") or [])},
        "oidc": {"enabled": sso_on(app), "name": o.get("name", ""), "issuer": o.get("issuer", ""), "client_id": o.get("client_id", ""),
                 "has_secret": bool(o.get("client_secret")), "redirect_uri": o.get("redirect_uri", ""), "scopes": o.get("scopes", oidc.DEFAULT_SCOPES),
                 "claim": o.get("claim", "email"), "value": o.get("value", ""), "tested": bool(o.get("tested")), "configured": bool(o.get("issuer"))},
    }


def _save(app):
    app.config.save()


def audit(app, what, **details):
    api_v1.audit(app.data_dir, what, **details)


# The two steps at sign-in -----------------------------------------------------------------------------------------

_challenges = {}
_challenge_lock = threading.Lock()


def _hash(text):
    return hashlib.sha256(text.encode()).hexdigest()


def new_challenge(address, remember):
    """Made once the password was right and a code is still needed. Not a session: it opens nothing."""
    token = secrets.token_urlsafe(24)
    now = time.time()
    with _challenge_lock:
        for k in [k for k, v in _challenges.items() if v["until"] < now]:
            del _challenges[k]
        while len(_challenges) >= MAX_CHALLENGES:
            del _challenges[min(_challenges, key=lambda k: _challenges[k]["until"])]
        _challenges[_hash(token)] = {"until": now + CHALLENGE_LIFE, "address": address, "remember": bool(remember), "tries": 0}
    return token


def check_code(app, token, address, code):
    """Returns whether the session should remember, when the code (or a recovery code) is right. Raises SigninError.
    The challenge allows 5 tries and then needs the password again; only the code is asked for here."""
    key = _hash(str(token or ""))
    with _challenge_lock:
        item = _challenges.get(key)
        if not item or item["until"] < time.time() or item["address"] != address:
            _challenges.pop(key, None)
            raise SigninError(401, "The password step has run out. Enter your password again")
        item["tries"] += 1
        if item["tries"] > CHALLENGE_TRIES:
            del _challenges[key]
            raise SigninError(401, "Too many wrong codes. Enter your password again")
    if not totp_on(app):
        with _challenge_lock:
            _challenges.pop(key, None)
        raise SigninError(401, "Enter your password again")
    entered = str(code or "")
    # Checked and marked used under one lock: two requests with the same code cannot both pass.
    with app.config.lock:
        t = section(app, "totp")
        if not totp_on(app):
            step, left = None, None
        else:
            step = totp.verify(t["secret"], entered, t.get("last_step", 0))
            left = totp.use_recovery_code(entered, t.get("recovery") or []) if step is None else None
        if step is not None:
            t["last_step"] = step
            _save(app)
        elif left is not None:
            t["recovery"] = left
            _save(app)
    if step is None and left is None:
        audit(app, "sign_in_code_failed", address=address)
        logs.event("warning", "sign-in", "A sign-in used the wrong two-step code")
        raise SigninError(401, "That code is not right")
    with _challenge_lock:
        remember = _challenges.pop(key, {}).get("remember", False)
    if step is None:
        audit(app, "sign_in_recovery_code_used", address=address, left=len(left))
        logs.event("warning", "sign-in", f"Signed in with a recovery code. {len(left)} left")
    else:
        audit(app, "sign_in_code_ok", address=address)
        logs.event("info", "sign-in", "Signed in with a two-step code")
    return remember


# Settings: two-step code ------------------------------------------------------------------------------------------

def totp_start(app, account):
    """A new secret, kept as pending until a code from the phone proves it was scanned. Nothing changes for sign-in yet."""
    secret = totp.new_secret()
    with app.config.lock:
        app.config.data["auth"].setdefault("totp", {})["pending"] = secret
        _save(app)
    link = totp.uri(secret, account, "Starboard")
    return {"secret": totp.spaced(secret), "qr": _qr(link)}


def _qr(text):
    size, path = qr.svg_path(qr.encode(text, level="M"))
    return {"size": size, "path": path}


def totp_confirm(app, code, address):
    t = app.config.data["auth"].get("totp") or {}
    pending = t.get("pending")
    if not pending:
        raise SigninError(409, "Start the set-up again to get a new QR code")
    step = totp.verify(pending, code)
    if step is None:
        audit(app, "totp_setup_code_wrong", address=address)
        raise SigninError(400, "That code is not right. Check the code in the app now, and that this computer's clock is right")
    codes, hashes = totp.new_recovery_codes()
    with app.config.lock:
        app.config.data["auth"]["totp"] = {"enabled": True, "secret": pending, "last_step": step, "recovery": hashes}
        _save(app)
    audit(app, "totp_enabled", address=address)
    logs.event("info", "sign-in", "A two-step code was activated")
    return {"codes": codes, "status": status(app)}


def totp_off(app, address):
    with app.config.lock:
        app.config.data["auth"].pop("totp", None)
        _save(app)
    audit(app, "totp_disabled", address=address)
    logs.event("warning", "sign-in", "The two-step code was deactivated")
    return status(app)


def new_recovery(app, code, address):
    t = section(app, "totp")
    if not totp_on(app):
        raise SigninError(409, "Activate the two-step code first")
    step = totp.verify(t["secret"], code, t.get("last_step", 0))
    if step is None:
        audit(app, "recovery_codes_refused", address=address)
        raise SigninError(400, "That code is not right")
    codes, hashes = totp.new_recovery_codes()
    with app.config.lock:
        t["recovery"], t["last_step"] = hashes, step
        _save(app)
    audit(app, "recovery_codes_made", address=address)
    return {"codes": codes, "status": status(app)}


# Settings: single sign-on -----------------------------------------------------------------------------------------

def _text(data, key, limit=MAX_FIELD):
    return str(data.get(key, "")).strip()[:limit]


def oidc_save(app, data, address, default_redirect):
    """Saves what the owner entered after reading the provider's own description, so a wrong address says so now.
    A blank secret keeps the saved one. Saving turns single sign-on off and clears the test until it is tried again."""
    o = dict(section(app, "oidc"))
    issuer = _text(data, "issuer")
    client_id = _text(data, "client_id")
    secret = str(data.get("client_secret") or "").strip()[:1000] or o.get("client_secret", "")
    redirect = _text(data, "redirect_uri") or default_redirect
    claim = _text(data, "claim", 40).lower() or "email"
    value = _text(data, "value")
    scopes = " ".join(_text(data, "scopes", 200).split()) or oidc.DEFAULT_SCOPES
    name = _text(data, "name", MAX_NAME) or "Single sign-on"
    if not issuer or not client_id or not secret:
        raise SigninError(400, "Enter the issuer address, the client ID and the client secret")
    if not value:
        raise SigninError(400, "Enter who may sign in: the email address, or the value of the claim you chose")
    if any(c not in CLAIM_OK for c in claim):
        raise SigninError(400, "A claim name uses letters, numbers and _ - : . only")
    if claim == "email" and "@" not in value:
        raise SigninError(400, "Enter the email address that your provider has checked")
    if "openid" not in scopes.split():
        raise SigninError(400, "The scopes must include openid")
    try:
        oidc.check_address(issuer, "issuer address")
        oidc.check_address(redirect, "redirect address")
    except ValueError as e:
        raise SigninError(400, str(e)) from None
    try:
        oidc.discover(issuer, force=True)
    except oidc.SignInError as e:
        raise SigninError(400, e.text) from None
    changed = any(o.get(k) != v for k, v in (("issuer", issuer), ("client_id", client_id), ("client_secret", secret),
                                              ("redirect_uri", redirect), ("claim", claim), ("value", value), ("scopes", scopes)))
    with app.config.lock:
        app.config.data["auth"]["oidc"] = {**o, "issuer": issuer, "client_id": client_id, "client_secret": secret, "redirect_uri": redirect,
                                           "claim": claim, "value": value, "scopes": scopes, "name": name,
                                           "enabled": False if changed else bool(o.get("enabled")), "tested": False if changed else bool(o.get("tested"))}
        if changed and app.config.data["auth"].get("password_login") is False:
            app.config.data["auth"]["password_login"] = True  # nothing is left that only single sign-on opens
        _save(app)
    oidc.forget()
    audit(app, "sso_configured", address=address, issuer=issuer)
    logs.event("info", "sign-in", "Single sign-on was set up")
    return status(app)


def oidc_enable(app, on, address):
    o = section(app, "oidc")
    if on and not o.get("issuer"):
        raise SigninError(409, "Set up the provider first")
    with app.config.lock:
        if on:
            o["enabled"] = True
        else:
            app.config.data["auth"].setdefault("oidc", {})["enabled"] = False
            app.config.data["auth"]["password_login"] = True  # turning single sign-on off must never leave nobody able to sign in
        _save(app)
    audit(app, "sso_enabled" if on else "sso_disabled", address=address)
    logs.event("info" if on else "warning", "sign-in", "Single sign-on was " + ("activated" if on else "deactivated"))
    return status(app)


def oidc_forget(app, address):
    with app.config.lock:
        app.config.data["auth"].pop("oidc", None)
        app.config.data["auth"]["password_login"] = True
        _save(app)
    oidc.forget()
    audit(app, "sso_removed", address=address)
    logs.event("warning", "sign-in", "Single sign-on was removed")
    return status(app)


def set_password_login(app, allowed, address):
    """Turning the password off is allowed only when single sign-on is on and a test sign-in with it worked since it
    was last changed: otherwise nobody could be sure of getting back in."""
    if not allowed:
        o = section(app, "oidc")
        if not (sso_on(app) and o.get("tested")):
            raise SigninError(409, "Activate single sign-on and test it first. Then the password can be deactivated")
    with app.config.lock:
        if allowed:
            app.config.data["auth"].pop("password_login", None)
        else:
            app.config.data["auth"]["password_login"] = False
        _save(app)
    audit(app, "password_sign_in_on" if allowed else "password_sign_in_off", address=address)
    logs.event("warning" if not allowed else "info", "sign-in", "Password sign-in was " + ("activated" if allowed else "deactivated"))
    return status(app)


def mark_tested(app):
    with app.config.lock:
        section(app, "oidc")["tested"] = True
        _save(app)


# The way back in --------------------------------------------------------------------------------------------------

def reset(app):
    """./reset-sign-in.sh, run on the server: the two-step code and single sign-on off, the password back on. The
    password itself and every setting stay. Everyone is signed out, so no session started under them goes on."""
    with app.config.lock:
        a = app.config.data["auth"]
        a.pop("totp", None)
        a.pop("password_login", None)
        if a.get("oidc"):
            a["oidc"]["enabled"] = False
            a["oidc"]["tested"] = False
        a["session_version"] = a.get("session_version", 1) + 1
        _save(app)
    app.sessions.end_all()
    logs.event("warning", "security", "The two-step code and single sign-on were deactivated on the server. Everyone is signed out; the password works")
    api_v1.audit(app.data_dir, "sign_in_reset")
