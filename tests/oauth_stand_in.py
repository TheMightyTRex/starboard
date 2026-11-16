"""A stand-in sign-in service for Connect a cloud service (DASH-452): no real Google, Microsoft or Dropbox account is
used. It answers as an OAuth service does, standard library only:

- GET  /authorize    the sign-in page (200). With allow=1 (the person signed in and selected Allow) it sends the browser
                     to redirect_uri with a code and the state, or with error=access_denied when mode is "deny".
- POST /token        swaps a code (authorization_code), a device code (device_code) or a refresh token for a token.
- POST /device/code  the device flow: a device code, a short user code and the page to open.
- GET  /device       the page a phone opens; GET /device/approve?user_code=... approves (as signing in there would).
- GET  /me/drive     OneDrive's "which drive" question.

Run it alone with: python3 tests/oauth_stand_in.py PORT [HOST]
"""
import json
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StandIn:
    def __init__(self, host="127.0.0.1", port=0, public=None):
        self.mode = "approve"        # approve, deny (refuse at the sign-in page or on the phone), expire (device code runs out)
        self.pending = 2             # device flow: how many polls say authorization_pending before the approval counts
        self.codes, self.devices, self.requests = {}, {}, []
        self.server = ThreadingHTTPServer((host, port), self._handler())
        self.port = self.server.server_address[1]
        self.base = public or f"http://{host}:{self.port}"

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

            def _form(self):
                n = int(self.headers.get("Content-Length") or 0)
                return {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(n).decode()).items()}

            def do_GET(self):
                u = urllib.parse.urlsplit(self.path)
                q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
                outer.requests.append(("GET", u.path, q))
                if u.path == "/authorize":
                    if q.get("allow") != "1":
                        return self._json(200, {"page": "Sign in to the stand-in, then allow Starboard"})
                    to = q.get("redirect_uri", "")
                    if outer.mode == "deny":
                        extra = {"error": "access_denied", "state": q.get("state", "")}
                    else:
                        code = "4/" + secrets.token_urlsafe(12)
                        outer.codes[code] = q.get("client_id")
                        extra = {"code": code, "state": q.get("state", "")}
                    self.send_response(302)
                    self.send_header("Location", to + ("&" if "?" in to else "?") + urllib.parse.urlencode(extra))
                    self.end_headers()
                    return
                if u.path == "/device":
                    return self._json(200, {"page": "Enter the code from Starboard"})
                if u.path == "/device/approve":
                    for d in outer.devices.values():
                        if d["user_code"] == q.get("user_code"):
                            d["approved"] = outer.mode != "deny"
                            d["denied"] = outer.mode == "deny"
                    return self._json(200, {"ok": True})
                if u.path == "/me/drive":
                    if not (self.headers.get("Authorization") or "").startswith("Bearer standin-"):
                        return self._json(401, {"error": {"code": "InvalidAuthenticationToken"}})
                    return self._json(200, {"id": "b!standin-drive", "driveType": "personal", "owner": {"user": {"displayName": "Alex"}}})
                return self._json(404, {"error": "not found"})

            def do_POST(self):
                u = urllib.parse.urlsplit(self.path)
                form = self._form()
                outer.requests.append(("POST", u.path, form))
                if u.path == "/device/code":
                    dc, uc = secrets.token_urlsafe(24), f"{secrets.randbelow(9000) + 1000}-{secrets.randbelow(9000) + 1000}"
                    outer.devices[dc] = {"user_code": uc, "polls": 0, "approved": False, "denied": False}
                    return self._json(200, {"device_code": dc, "user_code": uc, "verification_uri": outer.base + "/device",
                                            "expires_in": 900, "interval": 1})
                if u.path == "/token":
                    grant = form.get("grant_type", "")
                    if grant == "authorization_code":
                        if outer.codes.pop(form.get("code", ""), None) is None:
                            return self._json(400, {"error": "invalid_grant"})
                    elif grant == "urn:ietf:params:oauth:grant-type:device_code":
                        d = outer.devices.get(form.get("device_code", ""))
                        if not d:
                            return self._json(400, {"error": "bad_verification_code"})
                        d["polls"] += 1
                        if outer.mode == "expire":
                            return self._json(400, {"error": "expired_token"})
                        if d["denied"]:
                            return self._json(400, {"error": "access_denied"})
                        if not d["approved"] or d["polls"] <= outer.pending:
                            return self._json(428, {"error": "authorization_pending"})
                    elif grant == "refresh_token":
                        if form.get("refresh_token") == "revoked":
                            return self._json(400, {"error": "invalid_grant", "error_description": "Token has been expired or revoked."})
                    else:
                        return self._json(400, {"error": "unsupported_grant_type"})
                    return self._json(200, {"access_token": "standin-" + secrets.token_hex(8), "token_type": "Bearer",
                                            "refresh_token": "refresh-" + secrets.token_hex(8), "expires_in": 3600})
                return self._json(404, {"error": "not found"})
        return H

    def start(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def approve(self, user_code):
        for d in self.devices.values():
            if d["user_code"] == user_code:
                d["approved"] = True


if __name__ == "__main__":
    s = StandIn(sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0", int(sys.argv[1]))
    print("READY", s.port, flush=True)
    s.server.serve_forever()
