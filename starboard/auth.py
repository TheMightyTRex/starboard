"""Passwords, sessions and sign-in rate limits."""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time

ITERATIONS = 600_000
MIN_PASSWORD = 10
FORGET_AFTER_DAYS = 1  # without Remember me, a session ends when the browser closes, or after a day at most


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def check_password(password, stored):
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        with _HASHING:
            test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(test.hex(), digest)
    except (ValueError, AttributeError):
        return False


def password_problem(password):
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters"
    if len(password) > 256:
        return "Use 256 characters or fewer"
    return None


class Sessions:
    """Sessions are random tokens; only their SHA-256 hashes are kept, on disk, so a restart keeps people signed in."""

    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "sessions.json")
        self.lock = threading.Lock()
        self.items = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    self.items = json.load(f)
            except (OSError, ValueError):
                self.items = {}

    @staticmethod
    def _key(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def _save(self):
        tmp = self.path + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self.items, f)
        os.replace(tmp, self.path)

    def create(self, days, version, remember=True):
        token = secrets.token_urlsafe(32)
        with self.lock:
            now = time.time()
            self.items = {k: v for k, v in self.items.items() if v["expires"] > now}
            self.items[self._key(token)] = {"expires": now + days * 86400, "version": version, "remember": remember}
            self._save()
        return token

    def valid(self, token, version):
        if not token:
            return False
        with self.lock:
            item = self.items.get(self._key(token))
            return bool(item and item["expires"] > time.time() and item["version"] == version)

    def remembered(self, token):
        with self.lock:
            item = self.items.get(self._key(token or ""))
            return bool(item and item.get("remember", True))

    def end(self, token):
        with self.lock:
            if self.items.pop(self._key(token or ""), None):
                self._save()

    def end_all(self):
        with self.lock:
            self.items = {}
            self._save()


_HASHING = threading.BoundedSemaphore(2)  # at most two password checks at once: each takes about 0.3 s


class RateLimit:
    """At most `limit` sign-in attempts per address in `window` seconds, counted before the password is checked,
    so attempts sent all at once cannot get past it. A right password clears the address's count."""

    def __init__(self, limit=5, window=900):
        self.limit, self.window = limit, window
        self.failures = {}
        self.lock = threading.Lock()

    def attempt(self, address):
        """Records an attempt and says whether it may go ahead."""
        with self.lock:
            now = time.time()
            recent = [t for t in self.failures.get(address, []) if now - t < self.window]
            if len(recent) >= self.limit:
                self.failures[address] = recent
                return False
            recent.append(now)
            self.failures[address] = recent
            if len(self.failures) > 10000:  # many addresses: forget the ones with nothing recent
                self.failures = {a: ts for a, ts in self.failures.items() if ts and now - ts[-1] < self.window}
            return True

    def blocked(self, address):
        with self.lock:
            now = time.time()
            return len([t for t in self.failures.get(address, []) if now - t < self.window]) >= self.limit

    def clear(self, address):
        with self.lock:
            self.failures.pop(address, None)
