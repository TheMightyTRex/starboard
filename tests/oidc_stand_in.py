"""A throwaway OpenID Connect provider for Starboard's single sign-on tests (DASH-512): no real provider, no real
account and no real credential is ever used. Standard library only, one 2048-bit RSA key made here (a few seconds,
once), and an ID token signed RS256 by hand.

    GET  /.well-known/openid-configuration   the provider's description
    GET  /jwks                               its public keys
    GET  /authorize                          approves at once and sends the browser back with a code and the state
    POST /token                              swaps the code (with PKCE, and the client secret) for an ID token

`mode` makes it misbehave in one way at a time, so each check Starboard makes can be seen to refuse: wrong_nonce,
wrong_aud, expired, future, bad_signature, wrong_issuer, alg_none, hs256, unknown_kid, unverified, other_email,
no_id_token, redirect_elsewhere. Run alone with: python3 tests/oidc_stand_in.py PORT
"""
import base64
import hashlib
import hmac
import json
import secrets
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SMALL_PRIMES = [p for p in range(3, 2000) if all(p % q for q in range(2, int(p ** 0.5) + 1))]
_SHA256_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")
_key = {}


def _probably_prime(n, rounds=24):
    if n < 4:
        return n in (2, 3)
    if n % 2 == 0:
        return False
    for p in SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _prime(bits):
    while True:
        n = secrets.randbits(bits) | (1 << (bits - 1)) | (1 << (bits - 2)) | 1
        if _probably_prime(n):
            return n


def make_key(bits=2048):
    e = 65537
    while True:
        p, q = _prime(bits // 2), _prime(bits // 2)
        n, phi = p * q, (p - 1) * (q - 1)
        if p != q and n.bit_length() == bits and phi % e:
            return {"n": n, "e": e, "d": pow(e, -1, phi)}


def key(name="k1"):
    if name not in _key:
        _key[name] = make_key()
    return _key[name]


def b64(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def b64int(i):
    return b64(i.to_bytes((i.bit_length() + 7) // 8, "big"))


def sign_rs256(signed, k):
    size = (k["n"].bit_length() + 7) // 8
    t = _SHA256_PREFIX + hashlib.sha256(signed).digest()
    em = b"\x00\x01" + b"\xff" * (size - len(t) - 3) + b"\x00" + t
    return pow(int.from_bytes(em, "big"), k["d"], k["n"]).to_bytes(size, "big")


class Provider:
    def __init__(self, host="127.0.0.1", port=0, client_id="starboard-test", client_secret=None):
        self.client_id = client_id
        self.client_secret = client_secret or secrets.token_urlsafe(24)
        self.mode = ""
        self.email, self.sub, self.username = "owner@example.org", "user-1", "owner"
        self.email_verified = True
        self.extra = {}
        self.codes, self.requests = {}, []
        self.server = ThreadingHTTPServer((host, port), self._handler())
        self.port = self.server.server_address[1]
        self.issuer = f"http://{host}:{self.port}"
        key("k1")
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def jwks(self):
        keys = [{"kty": "RSA", "use": "sig", "alg": "RS256", "kid": "k1", "n": b64int(key("k1")["n"]), "e": b64int(key("k1")["e"])}]
        if "k2" in _key:
            keys.append({"kty": "RSA", "use": "sig", "alg": "RS256", "kid": "k2", "n": b64int(_key["k2"]["n"]), "e": b64int(_key["k2"]["e"])})
        return {"keys": keys}

    def id_token(self, nonce, client_id):
        now = int(time.time())
        mode = self.mode
        claims = {"iss": self.issuer + ("/other" if mode == "wrong_issuer" else ""), "aud": "someone-else" if mode == "wrong_aud" else client_id,
                  "sub": self.sub, "iat": now, "exp": now + 300, "nonce": "not-the-nonce" if mode == "wrong_nonce" else nonce,
                  "email": "intruder@example.org" if mode == "other_email" else self.email, "email_verified": False if mode == "unverified" else self.email_verified,
                  "preferred_username": self.username, **self.extra}
        if mode == "expired":
            claims["exp"] = now - 3600
            claims["iat"] = now - 7200
        if mode == "future":
            claims["iat"] = now + 7200
            claims["exp"] = now + 9000
        header = {"alg": "RS256", "typ": "JWT", "kid": "k1"}
        if mode == "alg_none":
            header["alg"] = "none"
        if mode == "hs256":
            header["alg"] = "HS256"
        if mode == "unknown_kid":
            header["kid"] = "nobody"
        signed = (b64(json.dumps(header).encode()) + "." + b64(json.dumps(claims).encode())).encode()
        if mode == "alg_none":
            return signed.decode() + "."
        if mode == "hs256":  # signed with the public modulus as the HMAC secret: the classic algorithm confusion
            return signed.decode() + "." + b64(hmac.new(key("k1")["n"].to_bytes(256, "big"), signed, hashlib.sha256).digest())
        sig = sign_rs256(signed, key("k1"))
        if mode == "bad_signature":
            sig = bytes([sig[0] ^ 1]) + sig[1:]
        if mode == "unknown_kid":
            sig = sign_rs256(signed, key("k1"))
        return signed.decode() + "." + b64(sig)

    def _handler(self):
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _json(self, status, body):
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                u = urllib.parse.urlsplit(self.path)
                q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
                outer.requests.append(("GET", u.path, q, dict(self.headers)))
                if u.path == "/.well-known/openid-configuration":
                    return self._json(200, {"issuer": outer.issuer, "authorization_endpoint": outer.issuer + "/authorize",
                                            "token_endpoint": outer.issuer + "/token", "jwks_uri": outer.issuer + "/jwks",
                                            "response_types_supported": ["code"], "id_token_signing_alg_values_supported": ["RS256"],
                                            "code_challenge_methods_supported": ["S256"], "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"]})
                if u.path == "/jwks":
                    return self._json(200, outer.jwks())
                if u.path == "/authorize":
                    if q.get("client_id") != outer.client_id or q.get("response_type") != "code" or q.get("code_challenge_method") != "S256" or not q.get("code_challenge"):
                        return self._json(400, {"error": "invalid_request"})
                    code = secrets.token_urlsafe(16)
                    outer.codes[code] = {"nonce": q.get("nonce", ""), "challenge": q["code_challenge"], "redirect_uri": q.get("redirect_uri", "")}
                    to = q["redirect_uri"] if outer.mode != "redirect_elsewhere" else "http://127.0.0.1:1/steal"
                    sep = "&" if "?" in to else "?"
                    self.send_response(302)
                    self.send_header("Location", to + sep + urllib.parse.urlencode({"code": code, "state": q.get("state", "")}))
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self._json(404, {"error": "not found"})

            def do_POST(self):
                u = urllib.parse.urlsplit(self.path)
                n = int(self.headers.get("Content-Length") or 0)
                form = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode()).items()}
                outer.requests.append(("POST", u.path, form, dict(self.headers)))
                if u.path != "/token":
                    return self._json(404, {"error": "not found"})
                cid, secret = form.get("client_id"), form.get("client_secret")
                auth = self.headers.get("Authorization", "")
                if auth.startswith("Basic "):
                    cid, _, secret = base64.b64decode(auth[6:]).decode().partition(":")
                    cid, secret = urllib.parse.unquote(cid), urllib.parse.unquote(secret)
                if cid != outer.client_id or not hmac.compare_digest(str(secret or ""), outer.client_secret):
                    return self._json(401, {"error": "invalid_client"})
                item = outer.codes.pop(form.get("code", ""), None)
                if not item or form.get("grant_type") != "authorization_code" or form.get("redirect_uri") != item["redirect_uri"]:
                    return self._json(400, {"error": "invalid_grant"})
                challenge = b64(hashlib.sha256(form.get("code_verifier", "").encode()).digest())
                if not hmac.compare_digest(challenge, item["challenge"]):
                    return self._json(400, {"error": "invalid_grant", "error_description": "PKCE failed"})
                if outer.mode == "no_id_token":
                    return self._json(200, {"access_token": "x", "token_type": "Bearer"})
                return self._json(200, {"access_token": secrets.token_urlsafe(8), "token_type": "Bearer", "expires_in": 300,
                                        "id_token": outer.id_token(item["nonce"], cid)})
        return H


if __name__ == "__main__":
    p = Provider(port=int(sys.argv[1]) if len(sys.argv) > 1 else 0)
    print(f"READY issuer={p.issuer} client_id={p.client_id} client_secret={p.client_secret} email={p.email}", flush=True)
    threading.Event().wait()
