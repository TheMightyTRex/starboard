"""A two-step code (TOTP, RFC 6238) and recovery codes, standard library only (DASH-512).

The code is 6 digits from HMAC-SHA1 over the 30 second step, as every authenticator app makes it. Comparisons are
constant-time. A code that was used once is never accepted again (the step it belonged to is remembered), so a code
seen over a shoulder cannot be replayed within its minute. Recovery codes are random, shown once and kept only as
hashes.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse

from . import auth

STEP = 30
DIGITS = 6
WINDOW = 1  # one step either side, for a phone whose clock is a little out
RECOVERY_COUNT = 8
RECOVERY_ITERATIONS = 20_000  # the codes have about 50 bits each; this keeps checking all eight under a second
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alikes: no i, l, o, 0 or 1


def new_secret():
    """160 random bits as base32 without padding, which every authenticator app reads."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret):
    text = secret.strip().replace(" ", "").upper()
    return base64.b32decode(text + "=" * (-len(text) % 8))


def code_at(secret, step):
    digest = hmac.new(_key(secret), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 10 ** DIGITS
    return f"{value:0{DIGITS}d}"


def verify(secret, code, last_step=0, now=None):
    """The step the code belongs to when it is right and new, else None. last_step is the newest step already used."""
    text = "".join(str(code or "").split())
    if not (len(text) == DIGITS and text.isdigit() and text.isascii()):
        return None
    current = int((time.time() if now is None else now) // STEP)
    found = None
    for step in range(current - WINDOW, current + WINDOW + 1):
        # Every step is compared, whatever the first answer, so the time taken says nothing about which was close
        if hmac.compare_digest(code_at(secret, step), text) and found is None:
            found = step
    if found is None or found <= last_step:
        return None
    return found


def uri(secret, account, issuer):
    label = urllib.parse.quote(f"{issuer}:{account}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={urllib.parse.quote(issuer, safe='')}&algorithm=SHA1&digits={DIGITS}&period={STEP}"


def spaced(secret):
    """For typing by hand: groups of four."""
    return " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))


# Recovery codes -------------------------------------------------------------------------------------------------

def new_recovery_codes(count=RECOVERY_COUNT):
    """(the codes to show once, the hashes to keep). A code is two groups of five, such as k7m2q-9xtpa."""
    codes = ["-".join("".join(secrets.choice(ALPHABET) for _ in range(5)) for _ in range(2)) for _ in range(count)]
    return codes, [auth.hash_password(normal(c), RECOVERY_ITERATIONS) for c in codes]


def normal(code):
    return "".join(str(code or "").lower().split()).replace("-", "")


def use_recovery_code(code, hashes):
    """The hashes left when the code is one of them (so it cannot be used twice), else None. All are checked."""
    text = normal(code)
    if len(text) != 10:
        return None
    hit = None
    for i, stored in enumerate(hashes):
        if auth.check_password(text, stored) and hit is None:
            hit = i
    if hit is None:
        return None
    return [h for i, h in enumerate(hashes) if i != hit]
