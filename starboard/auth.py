"""Passwords, sessions and sign-in rate limits."""

import hashlib
import hmac
import json
import os
import secrets
import threading
import time

ITERATIONS = 600_000
MIN_PASSWORD = 12


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def check_password(password, stored):
    try:
        algo, iterations, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
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

    def create(self, days, version):
        token = secrets.token_urlsafe(32)
        with self.lock:
            now = time.time()
            self.items = {k: v for k, v in self.items.items() if v["expires"] > now}
            self.items[self._key(token)] = {"expires": now + days * 86400, "version": version}
            self._save()
        return token

    def valid(self, token, version):
        if not token:
            return False
        with self.lock:
            item = self.items.get(self._key(token))
            return bool(item and item["expires"] > time.time() and item["version"] == version)

    def end(self, token):
        with self.lock:
            if self.items.pop(self._key(token or ""), None):
                self._save()

    def end_all(self):
        with self.lock:
            self.items = {}
            self._save()


class RateLimit:
    """At most `limit` failed sign-ins per address in `window` seconds."""

    def __init__(self, limit=5, window=900):
        self.limit, self.window = limit, window
        self.failures = {}
        self.lock = threading.Lock()

    def blocked(self, address):
        with self.lock:
            now = time.time()
            recent = [t for t in self.failures.get(address, []) if now - t < self.window]
            self.failures[address] = recent
            return len(recent) >= self.limit

    def fail(self, address):
        with self.lock:
            self.failures.setdefault(address, []).append(time.time())

    def clear(self, address):
        with self.lock:
            self.failures.pop(address, None)
