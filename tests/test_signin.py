"""A two-step code and single sign-on for Starboard's own sign-in (DASH-512).

The two-step code is checked against RFC 6238's own values. Single sign-on is checked end to end against a throwaway
provider (tests/oidc_stand_in.py) that can misbehave in one way at a time: nothing here touches a real provider.
"""
import hashlib
import http.client
import json
import os
import re
import tempfile
import threading
import time
import unittest
import urllib.parse

from starboard import api_v1, auth, oidc, signin, totp
from starboard.server import App, make_server
from tests import oidc_stand_in

RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # "12345678901234567890", RFC 6238's test secret
PASSWORD = "correct horse battery"


class TotpTest(unittest.TestCase):
    def test_rfc_6238_values(self):
        # The RFC lists 8 digits; the 6 digit code is the last 6 of them.
        for t, expected in ((59, "287082"), (1111111109, "081804"), (1111111111, "050471"), (1234567890, "005924"),
                            (2000000000, "279037"), (20000000000, "353130")):
            self.assertEqual(totp.code_at(RFC_SECRET, t // 30), expected)

    def test_a_code_works_once_and_a_neighbouring_step_is_allowed(self):
        now = 1_700_000_010
        step = now // 30
        code = totp.code_at(RFC_SECRET, step)
        self.assertEqual(totp.verify(RFC_SECRET, code, 0, now), step)
        self.assertIsNone(totp.verify(RFC_SECRET, code, step, now))  # used: never again
        self.assertEqual(totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, step - 1), 0, now), step - 1)  # a phone a little slow
        self.assertIsNone(totp.verify(RFC_SECRET, totp.code_at(RFC_SECRET, step + 5), 0, now))  # too far
        self.assertEqual(totp.verify(RFC_SECRET, " " + code[:3] + " " + code[3:], 0, now), step)  # typed with a space

    def test_junk_is_refused(self):
        for junk in ("", None, "12345", "1234567", "abcdef", "١٢٣٤٥٦", "12 34 5", "000000" * 3):
            self.assertIsNone(totp.verify(RFC_SECRET, junk, 0, 1_700_000_010), junk)

    def test_the_link_for_the_qr_code(self):
        link = totp.uri(RFC_SECRET, "Harbour", "Starboard")
        self.assertTrue(link.startswith("otpauth://totp/Starboard%3AHarbour?secret=" + RFC_SECRET))
        self.assertIn("issuer=Starboard", link)

    def test_recovery_codes_are_hashed_and_work_once(self):
        codes, hashes = totp.new_recovery_codes()
        self.assertEqual((len(codes), len(set(codes))), (8, 8))
        for c, h in zip(codes, hashes):
            self.assertRegex(c, r"^[a-z2-9]{5}-[a-z2-9]{5}$")
            self.assertNotIn(c.replace("-", ""), h)
            self.assertTrue(h.startswith("pbkdf2_sha256$"))
        left = totp.use_recovery_code(codes[3].upper(), hashes)  # case and a missing dash do not matter
        self.assertEqual(len(left), 7)
        self.assertIsNone(totp.use_recovery_code(codes[3], left))
        self.assertIsNone(totp.use_recovery_code("aaaaa-bbbbb", hashes))
        self.assertIsNotNone(totp.use_recovery_code(codes[0].replace("-", ""), left))


class Rs256Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = oidc_stand_in.Provider()
        cls.meta = oidc.discover(cls.provider.issuer, force=True)

    @classmethod
    def tearDownClass(cls):
        cls.provider.stop()

    def setUp(self):
        self.provider.mode = ""
        self.provider.email_verified = True
        oidc.forget()

    def verify(self, nonce="n1", **k):
        token = self.provider.id_token("n1", self.provider.client_id)
        return oidc.verify_id_token(token, self.meta, self.provider.issuer, self.provider.client_id, nonce, **k)

    def test_a_genuine_token_is_accepted(self):
        claims = self.verify()
        self.assertEqual(claims["email"], "owner@example.org")

    def test_each_check_refuses_what_it_should(self):
        for mode in ("wrong_nonce", "wrong_aud", "expired", "future", "bad_signature", "wrong_issuer", "alg_none", "hs256", "unknown_kid"):
            self.provider.mode = mode
            with self.assertRaises(oidc.SignInError, msg=mode):
                self.verify()

    def test_another_nonce_than_the_one_sent_is_refused(self):
        with self.assertRaises(oidc.SignInError):
            self.verify(nonce="a-different-sign-in")

    def test_a_token_signed_by_another_key_is_refused(self):
        token = self.provider.id_token("n1", self.provider.client_id)
        h, c, s = token.split(".")
        forged = oidc_stand_in.sign_rs256((h + "." + c).encode(), oidc_stand_in.key("k2"))
        with self.assertRaises(oidc.SignInError):
            oidc.verify_id_token(h + "." + c + "." + oidc_stand_in.b64(forged), self.meta, self.provider.issuer, self.provider.client_id, "n1")

    def test_a_published_key_under_2048_bits_is_never_used(self):
        small = oidc_stand_in.make_key(1024)
        self.assertFalse(oidc.rs256_valid(small["n"], small["e"], b"x", oidc_stand_in.sign_rs256(b"x", small)))

    def test_padding_that_is_not_the_exact_hash_is_refused(self):
        k = oidc_stand_in.key("k1")
        good = oidc_stand_in.sign_rs256(b"message", k)
        self.assertTrue(oidc.rs256_valid(k["n"], k["e"], b"message", good))
        self.assertFalse(oidc.rs256_valid(k["n"], k["e"], b"other message", good))
        self.assertFalse(oidc.rs256_valid(k["n"], k["e"], b"message", good[:-1]))
        self.assertFalse(oidc.rs256_valid(k["n"], k["e"], b"message", b"\x00" * len(good)))

    def test_who_is_the_owner(self):
        c = {"email": "Owner@Example.org", "email_verified": True, "preferred_username": "owner", "groups": ["admins", "family"], "sub": "u1"}
        self.assertTrue(oidc.is_owner(c, "email", "owner@example.org"))
        self.assertFalse(oidc.is_owner({**c, "email_verified": False}, "email", "owner@example.org"))
        self.assertFalse(oidc.is_owner({**c, "email_verified": "false"}, "email", "owner@example.org"))
        self.assertFalse(oidc.is_owner({k: v for k, v in c.items() if k != "email_verified"}, "email", "owner@example.org"))
        self.assertTrue(oidc.is_owner({**c, "email_verified": "true"}, "email", "owner@example.org"))
        self.assertTrue(oidc.is_owner(c, "preferred_username", "owner"))
        self.assertFalse(oidc.is_owner(c, "preferred_username", "Owner"))  # other claims match exactly
        self.assertTrue(oidc.is_owner(c, "groups", "family"))
        self.assertFalse(oidc.is_owner(c, "groups", "fam"))
        self.assertFalse(oidc.is_owner(c, "nothing", "x"))
        self.assertFalse(oidc.is_owner(c, "email", ""))

    def test_addresses_that_must_not_be_called(self):
        for bad in ("http://169.254.169.254/", "ftp://auth.example/", "http://user:pw@127.0.0.1/", "http://example.invalid/", "javascript:alert(1)"):
            with self.assertRaises(ValueError, msg=bad):
                oidc.check_address(bad)
        oidc.check_address("http://127.0.0.1:9/")  # this computer, for testing: fine over http
        oidc.check_address("http://localhost:9/")
        for lan in ("http://192.168.1.5/", "http://10.0.0.2:8080/", "http://auth.home.arpa/"):
            with self.assertRaises(ValueError, msg=lan):  # a home network is not safe over http
                oidc.check_address(lan)
        oidc.check_address("https://192.168.1.5/")


class Server(unittest.TestCase):
    """The whole sign-in against a running Starboard and the throwaway provider."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        totp.RECOVERY_ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.provider = oidc_stand_in.Provider()
        status, _, headers, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": PASSWORD})
        cls.cookie = cls.session_of(headers)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.provider.stop()
        cls.tmp.cleanup()

    # helpers
    @staticmethod
    def session_of(headers):
        return [v.split(";")[0] for k, v in headers if k.lower() == "set-cookie" and v.startswith("starboard_session=")][0]

    @classmethod
    def call(cls, method, path, body=None, cookie=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=15)
        h = {"Content-Type": "application/json", "X-Starboard": "1", **(headers or {})}
        if cookie:
            h["Cookie"] = cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, raw, r.getheaders(), r)
        conn.close()
        return out

    def api(self, method, path, body=None, cookie=True, **k):
        self.app.limits.clear("127.0.0.1")
        status, raw, headers, _ = self.call(method, path, body, self.cookie if cookie is True else cookie, **k)
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            data = {"raw": raw.decode("utf-8", "replace")}
        return status, data, headers

    def location(self, headers):
        return dict((k.lower(), v) for k, v in headers).get("location", "")

    def setUp(self):
        for lim in (self.app.limits, self.app.code_limits, self.app.code_limits_all, self.app.sso_limits, self.app.sso_return_limits):
            lim.failures.clear()
        oidc.forget()
        oidc.forget_pending()
        self.provider.mode = ""
        self.provider.email_verified = True
        self.provider.email = "owner@example.org"
        a = self.app.config.data["auth"]
        for k in ("totp", "oidc", "password_login"):
            a.pop(k, None)
        self.app.config.save()
        Server.cookie = "starboard_session=" + self.app.sessions.create(1, self.app.session_version)  # a reset in another test ends sessions

    # two-step code ------------------------------------------------------------------------------------------------
    def turn_on_totp(self):
        status, made, _ = self.api("POST", "/api/security/totp/start", {"password": PASSWORD})
        self.assertEqual(status, 200)
        self.assertEqual(set(made), {"secret", "qr"})
        self.assertGreater(made["qr"]["size"], 20)
        secret = self.app.config.data["auth"]["totp"]["pending"]
        self.assertEqual(made["secret"].replace(" ", ""), secret)
        status, done, _ = self.api("POST", "/api/security/totp/confirm", {"code": totp.code_at(secret, int(time.time() // 30))})
        self.assertEqual(status, 200, done)
        return secret, done["codes"]

    def test_nothing_is_on_until_set_up(self):
        status, st, _ = self.api("GET", "/api/security/signin")
        self.assertEqual((st["totp"]["enabled"], st["oidc"]["enabled"], st["password_login"]), (False, False, True))
        status, data, headers = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)
        self.assertEqual(status, 200)
        self.assertNotIn("needs_code", data)
        self.assertTrue(self.session_of(headers))
        status, sess, _ = self.api("GET", "/api/session", cookie=False)
        self.assertIsNone(sess["sso"])
        self.assertTrue(sess["password_login"])

    def test_set_up_asks_for_the_password_and_a_code_from_the_phone(self):
        self.assertEqual(self.api("POST", "/api/security/totp/start", {"password": "wrong wrong wrong"})[0], 401)
        status, made, _ = self.api("POST", "/api/security/totp/start", {"password": PASSWORD})
        self.assertEqual(status, 200)
        secret = self.app.config.data["auth"]["totp"]["pending"]
        self.assertEqual(self.api("POST", "/api/security/totp/confirm", {"code": "000000"})[0], 400)
        self.assertFalse(signin.totp_on(self.app))  # a wrong code turns nothing on
        status, done, _ = self.api("POST", "/api/security/totp/confirm", {"code": totp.code_at(secret, int(time.time() // 30))})
        self.assertEqual((status, len(done["codes"])), (200, 8))
        self.assertTrue(signin.totp_on(self.app))
        stored = json.dumps(self.app.config.data["auth"]["totp"]["recovery"])
        for c in done["codes"]:
            self.assertNotIn(c.replace("-", ""), stored)  # only hashes are kept

    def test_the_code_is_asked_after_the_password_and_a_session_comes_only_with_it(self):
        secret, codes = self.turn_on_totp()
        status, data, headers = self.api("POST", "/api/login", {"password": PASSWORD, "remember": True}, cookie=False)
        self.assertEqual((status, data["needs_code"]), (200, True))
        self.assertFalse([h for h in headers if h[0].lower() == "set-cookie"])  # no session yet
        challenge = data["challenge"]
        self.assertEqual(self.api("GET", "/api/session", cookie="starboard_session=" + challenge)[1]["signed_in"], False)
        self.assertEqual(self.api("POST", "/api/login/code", {"challenge": challenge, "code": "000000"}, cookie=False)[0], 401)
        step = int(time.time() // 30)
        status, data, headers = self.api("POST", "/api/login/code", {"challenge": challenge, "code": totp.code_at(secret, step + 1)}, cookie=False)
        self.assertEqual(status, 200)
        cookie = self.session_of(headers)
        self.assertTrue(self.app.sessions.valid(cookie.split("=", 1)[1], self.app.session_version))
        self.assertIn("SameSite=Strict", [v for k, v in headers if k.lower() == "set-cookie"][0])  # the session is what it always was
        self.assertIn("Max-Age", [v for k, v in headers if k.lower() == "set-cookie"][0])
        self.assertEqual(self.api("GET", "/api/session", cookie=cookie)[1]["signed_in"], True)
        # the challenge is spent, and the same code never works again
        self.assertEqual(self.api("POST", "/api/login/code", {"challenge": challenge, "code": totp.code_at(secret, step + 1)}, cookie=False)[0], 401)
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        self.assertEqual(self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": totp.code_at(secret, step + 1)}, cookie=False)[0], 401)

    def test_a_recovery_code_works_once(self):
        secret, codes = self.turn_on_totp()
        def sign_in(code):
            data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
            return self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": code}, cookie=False)[0]
        self.assertEqual(sign_in(codes[2]), 200)
        self.assertEqual(sign_in(codes[2]), 401)
        self.assertEqual(sign_in(codes[5].upper().replace("-", " ")), 200)
        self.assertEqual(self.api("GET", "/api/security/signin")[1]["totp"]["recovery_left"], 6)

    def test_wrong_codes_are_limited_and_the_challenge_runs_out(self):
        secret, codes = self.turn_on_totp()
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        results = [self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": "111111"}, cookie=False)[0] for _ in range(5)]
        self.assertEqual(results, [401] * 5)
        self.assertEqual(self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": "111111"}, cookie=False)[0], 429)
        self.app.code_limits.failures.clear()
        # even the right code no longer works on a challenge that had 5 wrong ones
        status, body, _ = self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": totp.code_at(secret, int(time.time() // 30))}, cookie=False)
        self.assertEqual(status, 401)
        self.assertIn("password", body["error"].lower())

    def test_too_many_wrong_codes_from_anywhere_stop_the_step(self):
        self.turn_on_totp()
        for _ in range(10):
            self.app.code_limits_all.attempt("all")
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        self.assertEqual(self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": "123456"}, cookie=False)[0], 429)

    def test_a_challenge_is_for_the_address_that_made_it(self):
        secret, _ = self.turn_on_totp()
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        key = signin._hash(data["challenge"])
        signin._challenges[key]["address"] = "203.0.113.9"
        self.assertEqual(self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": totp.code_at(secret, int(time.time() // 30) + 1)}, cookie=False)[0], 401)

    def test_turning_it_off_and_new_recovery_codes_ask_for_more(self):
        secret, codes = self.turn_on_totp()
        self.assertEqual(self.api("POST", "/api/security/totp/recovery", {"password": PASSWORD, "code": "000000"})[0], 400)
        step = int(time.time() // 30)
        status, done, _ = self.api("POST", "/api/security/totp/recovery", {"password": PASSWORD, "code": totp.code_at(secret, step + 1)})
        self.assertEqual(status, 200)
        self.assertNotEqual(set(done["codes"]), set(codes))
        self.assertIsNone(totp.use_recovery_code(codes[0], self.app.config.data["auth"]["totp"]["recovery"]))  # the old ones are gone
        self.assertEqual(self.api("POST", "/api/security/totp/off", {"password": "nope nope nope"})[0], 401)
        self.assertEqual(self.api("POST", "/api/security/totp/off", {"password": PASSWORD})[0], 200)
        self.assertFalse(signin.totp_on(self.app))
        self.assertNotIn("needs_code", self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1])

    # single sign-on -----------------------------------------------------------------------------------------------
    def redirect(self):
        return f"http://127.0.0.1:{self.port}/api/oidc/callback"

    def save_sso(self, **over):
        body = {"password": PASSWORD, "name": "Test provider", "issuer": self.provider.issuer, "client_id": self.provider.client_id,
                "client_secret": self.provider.client_secret, "redirect_uri": self.redirect(), "claim": "email", "value": "owner@example.org", **over}
        return self.api("POST", "/api/security/oidc/save", body)

    def go_through_the_provider(self, test=False, remember=False, cookie=None):
        """The browser's trip: Starboard's start, the provider's page, back to Starboard's callback. Returns the callback's answer."""
        status, raw, headers, _ = self.call("GET", "/api/oidc/start" + ("?test=1" if test else "") + ("?remember=1" if remember and not test else ""), cookie=cookie)
        self.assertEqual(status, 303, raw)
        where = self.location(headers)
        if "/authorize" not in where:
            return status, raw, headers, where, None
        binder = [v.split(";")[0] for k, v in headers if k.lower() == "set-cookie"][0]
        self.assertIn("SameSite=Lax", [v for k, v in headers if k.lower() == "set-cookie"][0])
        u = urllib.parse.urlsplit(where)
        conn = http.client.HTTPConnection(u.hostname, u.port, timeout=15)
        conn.request("GET", u.path + "?" + u.query)
        r = conn.getresponse()
        back = r.getheader("Location")
        r.read()
        conn.close()
        self.assertTrue(back, "the provider did not send the browser back")
        cb = urllib.parse.urlsplit(back)
        status, raw, headers, _ = self.call("GET", cb.path + "?" + cb.query, cookie="; ".join(x for x in (binder, cookie) if x))
        return status, raw, headers, back, binder

    def enable_sso(self):
        self.assertEqual(self.save_sso()[0], 200)
        status, raw, headers, _, *_ = self.go_through_the_provider(test=True, cookie=self.cookie)
        self.assertEqual(status, 200)
        self.assertEqual(self.api("POST", "/api/security/oidc/enable", {"password": PASSWORD, "enabled": True})[0], 200)

    def test_saving_reads_the_providers_description_and_keeps_the_secret_to_itself(self):
        status, st, _ = self.save_sso()
        self.assertEqual(status, 200, st)
        self.assertEqual((st["oidc"]["enabled"], st["oidc"]["has_secret"], st["oidc"]["tested"]), (False, True, False))
        self.assertNotIn(self.provider.client_secret, json.dumps(st))
        self.assertNotIn(self.provider.client_secret, self.api("GET", "/api/security/signin")[2].__repr__())
        self.assertNotIn(self.provider.client_secret, json.dumps(self.api("GET", "/api/security/signin")[1]))
        self.assertNotIn(self.provider.client_secret, json.dumps(self.api("GET", "/api/config")[1]))
        status, st, _ = self.save_sso(client_secret="")  # blank keeps the saved secret
        self.assertEqual(status, 200)
        self.assertEqual(self.app.config.data["auth"]["oidc"]["client_secret"], self.provider.client_secret)

    def test_saving_refuses_bad_details_in_words(self):
        self.assertEqual(self.save_sso(issuer="http://169.254.169.254/")[0], 400)
        self.assertEqual(self.save_sso(issuer="http://example.invalid")[0], 400)
        status, body, _ = self.save_sso(issuer=self.provider.issuer + "/not-the-issuer")
        self.assertEqual(status, 400)
        self.assertEqual(self.save_sso(value="")[0], 400)
        self.assertEqual(self.save_sso(value="not-an-email")[0], 400)
        self.assertEqual(self.save_sso(client_secret="", client_id="")[0], 400)
        self.assertEqual(self.api("POST", "/api/security/oidc/save", {"password": "wrong wrong wrong"})[0], 401)

    def test_it_cannot_be_turned_on_before_it_has_been_saved_and_tested(self):
        self.assertEqual(self.api("POST", "/api/security/oidc/enable", {"password": PASSWORD, "enabled": True})[0], 409)
        self.save_sso()
        self.assertEqual(self.api("GET", "/api/session", cookie=False)[1]["sso"], None)
        status, raw, headers, _ = self.call("GET", "/api/oidc/start")  # off: the start goes nowhere
        self.assertEqual((status, "sso=off" in self.location(headers)), (303, True))

    def test_the_whole_flow_signs_you_in_with_the_same_kind_of_session(self):
        self.enable_sso()
        self.assertEqual(self.api("GET", "/api/session", cookie=False)[1]["sso"], {"name": "Test provider"})
        status, raw, headers, back, binder = self.go_through_the_provider(remember=True)
        self.assertEqual(status, 200)
        self.assertIn(b"url=/dashboard.html", raw)  # a page that moves on, so the Strict cookie goes with the next request
        setc = [v for k, v in headers if k.lower() == "set-cookie"][0]
        self.assertTrue(setc.startswith("starboard_session="))
        self.assertIn("HttpOnly", setc)
        self.assertIn("SameSite=Strict", setc)
        cookie = setc.split(";")[0]
        self.assertTrue(self.app.sessions.valid(cookie.split("=", 1)[1], self.app.session_version))
        self.assertEqual(self.api("GET", "/api/session", cookie=cookie)[1]["signed_in"], True)
        # what the provider was sent: PKCE, a state, a nonce, the stored redirect address and the secret never in an address
        auth_req = [r for r in self.provider.requests if r[1] == "/authorize"][-1][2]
        self.assertEqual((auth_req["code_challenge_method"], auth_req["redirect_uri"], auth_req["response_type"]), ("S256", self.redirect(), "code"))
        self.assertTrue(auth_req["state"] and auth_req["nonce"] and len(auth_req["code_challenge"]) == 43)
        for r in self.provider.requests:
            self.assertNotIn(self.provider.client_secret, json.dumps(r[2]) if r[0] == "GET" else "")
        token_req = [r for r in self.provider.requests if r[1] == "/token"][-1]
        self.assertTrue(token_req[3]["Authorization"].startswith("Basic "))  # the secret goes in a header, in the request body only to a POST-only provider
        self.assertNotIn("client_secret", token_req[2])

    def test_a_state_works_once_and_only_in_the_browser_that_made_it(self):
        self.enable_sso()
        status, raw, headers, back, binder = self.go_through_the_provider()
        self.assertEqual(status, 200)
        cb = urllib.parse.urlsplit(back)
        again = self.call("GET", cb.path + "?" + cb.query, cookie=binder)
        self.assertEqual(again[0], 303)
        self.assertIn("sso=expired", self.location(again[2]))
        # another browser (no cookie of ours) holding the link that was made for this one
        status, raw, headers, _ = self.call("GET", "/api/oidc/start")
        u = urllib.parse.urlsplit(self.location(headers))
        conn = http.client.HTTPConnection(u.hostname, u.port, timeout=15)
        conn.request("GET", u.path + "?" + u.query)
        r = conn.getresponse()
        back = urllib.parse.urlsplit(r.getheader("Location"))
        conn.close()
        answer = self.call("GET", back.path + "?" + back.query)  # no binder cookie
        self.assertEqual(answer[0], 303)
        self.assertIn("sso=failed", self.location(answer[2]))
        self.assertFalse([h for h in answer[2] if h[0].lower() == "set-cookie"])
        # a made-up state
        self.assertIn("sso=expired", self.location(self.call("GET", "/api/oidc/callback?state=abc&code=def", cookie=binder)[2]))

    def test_every_way_a_provider_can_cheat_ends_at_the_sign_in_page_with_no_session(self):
        self.enable_sso()
        for mode in ("wrong_nonce", "wrong_aud", "expired", "future", "bad_signature", "wrong_issuer", "alg_none", "hs256", "unknown_kid", "no_id_token"):
            self.provider.mode = mode
            oidc.forget()
            status, raw, headers, *_ = self.go_through_the_provider()
            self.assertEqual(status, 303, mode)
            self.assertIn("/login.html?sso=", self.location(headers), mode)
            self.assertFalse([h for h in headers if h[0].lower() == "set-cookie"], mode)

    def test_only_the_owner_gets_in(self):
        self.enable_sso()
        for email, verified in (("intruder@example.org", True), ("owner@example.org", False)):
            self.provider.email, self.provider.email_verified = email, verified
            status, raw, headers, *_ = self.go_through_the_provider()
            self.assertEqual(status, 303)
            self.assertIn("sso=nomatch", self.location(headers), email)
            self.assertFalse([h for h in headers if h[0].lower() == "set-cookie"])

    def test_a_chosen_claim_can_name_the_owner(self):
        self.assertEqual(self.save_sso(claim="preferred_username", value="owner")[0], 200)
        self.assertEqual(self.go_through_the_provider(test=True, cookie=self.cookie)[0], 200)
        self.assertEqual(self.api("POST", "/api/security/oidc/enable", {"password": PASSWORD, "enabled": True})[0], 200)
        self.provider.email_verified = False  # email is not what is used here
        self.assertEqual(self.go_through_the_provider()[0], 200)

    def test_a_provider_that_sends_the_browser_elsewhere_gets_nothing_of_ours(self):
        self.enable_sso()
        self.provider.mode = "redirect_elsewhere"
        s, r, h, _ = self.call("GET", "/api/oidc/start")
        self.assertIn("/authorize", self.location(h))  # Starboard only ever sends the browser to the provider it was told about

    def test_a_test_sign_in_needs_a_session_and_signs_nobody_in(self):
        self.save_sso()
        status, raw, headers, _ = self.call("GET", "/api/oidc/start?test=1")  # no session
        self.assertIn("sso=off", self.location(headers))
        status, raw, headers, *_ = self.go_through_the_provider(test=True, cookie=self.cookie)
        self.assertEqual(status, 200)
        self.assertIn(b"settings-security-signin.html?sso=tested", raw)
        self.assertFalse([h for h in headers if h[0].lower() == "set-cookie"])  # a test makes no session
        self.assertTrue(self.api("GET", "/api/security/signin")[1]["oidc"]["tested"])
        self.save_sso(value="someone@example.org")  # a change clears the test
        self.assertFalse(self.api("GET", "/api/security/signin")[1]["oidc"]["tested"])

    def test_a_test_started_in_one_session_cannot_be_finished_with_none(self):
        self.save_sso()
        status, raw, headers, *_ = self.go_through_the_provider(test=True, cookie=self.cookie)
        status, raw, headers, _ = self.call("GET", "/api/oidc/start?test=1", cookie=self.cookie)
        u = urllib.parse.urlsplit(self.location(headers))
        binder = [v.split(";")[0] for k, v in headers if k.lower() == "set-cookie"][0]
        conn = http.client.HTTPConnection(u.hostname, u.port, timeout=15)
        conn.request("GET", u.path + "?" + u.query)
        back = urllib.parse.urlsplit(conn.getresponse().getheader("Location"))
        conn.close()
        answer = self.call("GET", back.path + "?" + back.query, cookie=binder)  # signed out by now
        self.assertEqual(answer[0], 303)
        self.assertFalse([h for h in answer[2] if h[0].lower() == "set-cookie"])

    # the password's switch, and the way back in -------------------------------------------------------------------
    def test_the_password_can_be_turned_off_only_after_a_working_test_and_the_way_back_in_works(self):
        self.save_sso()
        self.assertEqual(self.api("POST", "/api/security/password-login", {"password": PASSWORD, "allowed": False})[0], 409)
        self.enable_sso()
        self.assertEqual(self.api("POST", "/api/security/password-login", {"password": "wrong wrong wrong", "allowed": False})[0], 401)
        self.assertEqual(self.api("POST", "/api/security/password-login", {"password": PASSWORD, "allowed": False})[0], 200)
        status, body, _ = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)
        self.assertEqual(status, 403)
        self.assertIn("reset-sign-in.sh", body["error"])
        self.assertFalse(self.api("GET", "/api/session", cookie=False)[1]["password_login"])
        self.assertEqual(self.go_through_the_provider()[0], 200)  # single sign-on still opens it
        # from the terminal
        open(os.path.join(self.tmp.name, "reset-sign-in"), "w").close()
        signin.reset(self.app)
        a = self.app.config.data["auth"]
        self.assertEqual((signin.password_allowed(self.app), signin.totp_on(self.app), signin.sso_on(self.app)), (True, False, False))
        self.assertTrue(a["password_hash"])  # the password itself is not touched
        self.assertEqual(self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[0], 200)

    def test_turning_single_sign_on_off_or_changing_it_brings_the_password_back(self):
        self.enable_sso()
        self.api("POST", "/api/security/password-login", {"password": PASSWORD, "allowed": False})
        self.assertEqual(self.api("POST", "/api/security/oidc/enable", {"password": PASSWORD, "enabled": False})[0], 200)
        self.assertTrue(signin.password_allowed(self.app))
        self.enable_sso()
        self.api("POST", "/api/security/password-login", {"password": PASSWORD, "allowed": False})
        self.save_sso(client_id="changed")
        self.assertTrue(signin.password_allowed(self.app))
        self.api("POST", "/api/security/oidc/remove", {"password": PASSWORD})
        self.assertNotIn("oidc", self.app.config.data["auth"])

    def test_the_marker_file_is_read_at_start_up(self):
        with tempfile.TemporaryDirectory() as d:
            first = App(d)
            first.config.data["auth"]["password_hash"] = auth.hash_password(PASSWORD, 1000)
            first.config.data["auth"]["totp"] = {"enabled": True, "secret": totp.new_secret(), "recovery": []}
            first.config.data["auth"]["oidc"] = {"enabled": True, "issuer": "https://x.example", "client_id": "a", "client_secret": "b", "redirect_uri": "https://s.example/cb", "tested": True}
            first.config.data["auth"]["password_login"] = False
            first.config.save()
            open(os.path.join(d, "reset-sign-in"), "w").close()
            again = App(d)
            self.assertFalse(os.path.exists(os.path.join(d, "reset-sign-in")))
            self.assertEqual((signin.password_allowed(again), signin.totp_on(again), signin.sso_on(again)), (True, False, False))
            self.assertEqual(again.config.data["auth"]["oidc"]["client_id"], "a")  # the provider's details stay, off
            self.assertTrue(again.config.data["auth"]["password_hash"])
            self.assertFalse(again.needs_setup)

    def test_a_forgotten_password_reset_turns_both_off_too(self):
        with tempfile.TemporaryDirectory() as d:
            first = App(d)
            first.config.data["auth"]["password_hash"] = auth.hash_password(PASSWORD, 1000)
            first.config.data["auth"]["totp"] = {"enabled": True, "secret": totp.new_secret(), "recovery": []}
            first.config.save()
            open(os.path.join(d, "reset-password"), "w").close()
            again = App(d)
            self.assertTrue(again.needs_setup)
            self.assertFalse(signin.totp_on(again))

    # who may use these routes ----------------------------------------------------------------------------------------
    def test_an_api_key_cannot_reach_any_of_it(self):
        key = api_v1.create_key(self.app.data_dir, "tester", "manage", None, 30)[0]
        bearer = {"Authorization": f"Bearer {key}"}
        for method, path in (("GET", "/api/security/signin"), ("POST", "/api/security/totp/start"), ("POST", "/api/security/oidc/save"),
                             ("POST", "/api/security/password-login"), ("POST", "/api/security/oidc/enable")):
            status, _, _, _ = self.call(method, path, {"password": PASSWORD}, headers=bearer)
            self.assertEqual(status, 401, path)
        for method, path in (("POST", "/api/v1/security/signin"), ("GET", "/api/v1/security/signin")):
            self.assertIn(self.call(method, path, {}, headers=bearer)[0], (404, 405), path)

    def test_every_change_needs_the_password_and_signing_in(self):
        for path in ("/api/security/totp/start", "/api/security/totp/off", "/api/security/oidc/save", "/api/security/oidc/enable",
                     "/api/security/oidc/remove", "/api/security/password-login", "/api/security/totp/recovery"):
            self.assertEqual(self.api("POST", path, {}, cookie=False)[0], 401, path)
            self.assertIn(self.api("POST", path, {"password": "wrong wrong wrong"})[0], (401,), path)

    def test_a_change_from_another_site_is_refused(self):
        status, raw, headers, _ = self.call("POST", "/api/security/totp/start", {"password": PASSWORD}, cookie=self.cookie,
                                            headers={"Origin": "https://evil.example", "X-Starboard": "1"})
        self.assertIn(status, (401, 403))
        self.assertFalse(signin.totp_on(self.app))

    # nothing secret in a log --------------------------------------------------------------------------------------
    def test_no_secret_reaches_a_log_the_audit_log_or_a_settings_copy(self):
        secret, codes = self.turn_on_totp()
        entered = totp.code_at(secret, int(time.time() // 30) + 1)
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": entered}, cookie=False)
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": codes[0]}, cookie=False)
        self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": "654321"}, cookie=False)
        self.api("POST", "/api/security/totp/off", {"password": PASSWORD})
        self.enable_sso()
        self.provider.mode = "bad_signature"
        self.go_through_the_provider()
        self.provider.mode = ""
        self.go_through_the_provider()
        secrets_ = [secret, secret.lower(), entered, PASSWORD, self.provider.client_secret, *[c.replace("-", "") for c in codes], *codes, "654321"]
        seen = 0
        for folder, _, files in os.walk(self.tmp.name):
            if os.path.basename(folder) == "backups":
                continue
            for name in files:
                if name in ("config.json", "sessions.json", "config.json.tmp") or name.endswith(".tmp"):
                    continue
                with open(os.path.join(folder, name), "rb") as f:
                    text = f.read().decode("utf-8", "replace")
                seen += 1
                for s in secrets_:
                    self.assertNotIn(s, text, f"{s[:3]}... is in {name}")
        self.assertGreater(seen, 0)
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            audit = f.read()
        for what in ("totp_enabled", "sign_in_code_ok", "sign_in_recovery_code_used", "sign_in_code_failed", "totp_disabled", "sso_configured",
                     "sso_tested", "sso_enabled", "sso_refused", "sign_in_sso"):
            self.assertIn(f'"what": "{what}"', audit, what)

    def test_a_settings_backup_never_holds_the_secrets(self):
        self.turn_on_totp()
        self.save_sso()
        from starboard import backup
        self.assertIn("auth", backup.NEVER_KEYS)

    def test_a_flood_with_no_password_behind_it_cannot_lock_the_owner_out(self):
        secret, _ = self.turn_on_totp()
        for _ in range(25):
            self.app.code_limits.failures.clear()
            self.assertEqual(self.api("POST", "/api/login/code", {"challenge": "made-up", "code": "000000"}, cookie=False)[0], 401)
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        status, _, _ = self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": totp.code_at(secret, int(time.time() // 30) + 1)}, cookie=False)
        self.assertEqual(status, 200)

    def test_the_limit_is_audited_once_a_window_not_for_every_refusal(self):
        self.turn_on_totp()
        from starboard.server import Handler
        Handler._audited.clear()
        data = self.api("POST", "/api/login", {"password": PASSWORD}, cookie=False)[1]
        for _ in range(10):
            self.app.code_limits_all.attempt("all")
        for _ in range(8):
            self.assertEqual(self.api("POST", "/api/login/code", {"challenge": data["challenge"], "code": "123456"}, cookie=False)[0], 429)
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            self.assertEqual(f.read().count("sign_in_code_limited"), 1)

    def test_changing_the_issuer_clears_the_kept_secret(self):
        self.assertEqual(self.save_sso()[0], 200)
        other = oidc_stand_in.Provider()
        try:
            status, body, _ = self.save_sso(issuer=other.issuer, client_secret="")
            self.assertEqual(status, 400)
            self.assertIn("secret was cleared", body["error"])
            self.assertEqual(self.app.config.data["auth"]["oidc"]["client_secret"], self.provider.client_secret)  # nothing was handed on
            self.assertEqual(self.save_sso(issuer=other.issuer, client_secret=other.client_secret, client_id=other.client_id)[0], 200)
        finally:
            other.stop()

    def test_coming_back_from_the_provider_does_not_touch_the_password_counter(self):
        self.enable_sso()
        for _ in range(3):
            self.app.limits.attempt("127.0.0.1")
        self.go_through_the_provider()
        self.assertEqual(len(self.app.limits.failures.get("127.0.0.1", [])), 3)
        self.assertGreaterEqual(len(self.app.sso_return_limits.failures.get("127.0.0.1", [])) + 1, 1)

    def test_one_address_cannot_push_out_another_ones_sign_in(self):
        self.enable_sso()
        cfg = signin.section(self.app, "oidc")
        where, binder = oidc.begin(cfg, address="198.51.100.1")
        for _ in range(40):
            try:
                oidc.begin(cfg, address="203.0.113.9")
            except oidc.SignInError as e:
                self.assertEqual(e.code, "limited")
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(where).query)["state"][0]
        self.assertIn(oidc._hash(state), oidc._pending)  # the first one is still waiting

    def test_text_from_a_provider_is_made_safe_for_a_log(self):
        e = oidc.SignInError("x\ny", "alg bad\r\nINJECTED\x1b[31m " + "a" * 500)
        self.assertNotRegex(e.reason + e.text, r"[\x00-\x1f\x7f]")
        self.assertLessEqual(len(e.reason), 300)

    def test_a_server_that_sends_a_byte_at_a_time_is_cut_off(self):
        import socket as _s
        srv = _s.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        stop = threading.Event()

        def drip():
            c, _ = srv.accept()
            c.recv(4096)
            c.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 100000\r\n\r\n")
            while not stop.is_set():
                try:
                    c.sendall(b" ")
                except OSError:
                    break
                time.sleep(0.3)
            c.close()
        threading.Thread(target=drip, daemon=True).start()
        old = oidc.DEADLINE
        oidc.DEADLINE = 2
        began = time.monotonic()
        try:
            with self.assertRaises(oidc.SignInError):
                oidc._fetch(f"http://127.0.0.1:{srv.getsockname()[1]}/x")
        finally:
            oidc.DEADLINE = old
            stop.set()
            srv.close()
        self.assertLess(time.monotonic() - began, 5)

    def test_the_connection_goes_to_the_address_that_was_checked(self):
        calls = []
        real = oidc.socket.getaddrinfo

        def lookup(host, port, *a, **k):
            calls.append(host)
            return real("127.0.0.1", port, *a, **k) if len(calls) < 2 else real("169.254.169.254", port, *a, **k)
        p = oidc_stand_in.Provider()
        from unittest import mock
        with mock.patch.object(oidc.socket, "getaddrinfo", lookup), mock.patch("starboard.outside.socket.getaddrinfo", lookup):
            oidc._addresses("rebind.test", p.port)
            with self.assertRaises(OSError):  # a later answer that points at a metadata address is refused
                oidc._addresses("rebind.test", p.port)
        p.stop()

    def test_the_access_page_names_single_sign_on_when_it_is_on(self):
        from starboard import access
        row = lambda: next(a for a in access.summary(self.app) if a["key"] == "sso")  # noqa: E731
        self.assertFalse(row()["on"])
        self.enable_sso()
        self.assertTrue(row()["on"])
        self.assertIn("settings-security-signin.html", row()["link"])


if __name__ == "__main__":
    unittest.main()
