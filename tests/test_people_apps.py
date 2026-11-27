"""Changing a password inside an app (DASH-589): Jellyfin, Emby and Audiobookshelf, against stand-in servers that answer the way
the apps' API descriptions say. Not tried against a real app. Checks which request is made, with which key, that the password
travels only in the body, that a missing account or a refusal is said in words without the password, and that nothing else changes."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import people, people_apps, services


class App:
    def __init__(self, users, status=200):
        self.seen, self.users, self.status = [], users, status
        me = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _answer(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n).decode() if n else ""
                me.seen.append((method, self.path, dict(self.headers), body))
                if method != "GET" and me.status != 200:
                    self.send_response(me.status)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                raw = json.dumps(me.users if method == "GET" else {}).encode() if method == "GET" else b""
                self.send_response(200 if raw else 204)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_GET = lambda self: self._answer("GET")  # noqa: E731
            do_POST = lambda self: self._answer("POST")  # noqa: E731
            do_PATCH = lambda self: self._answer("PATCH")  # noqa: E731
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def service(kind, url, **more):
    return {"id": kind, "name": kind.capitalize(), "type": kind, "url": url, "api_key": "admin-key", **more}


class Changing(unittest.TestCase):
    def test_jellyfin_changes_the_named_account_only(self):
        app = App([{"Id": "u1", "Name": "Sam", "Policy": {}}, {"Id": "u2", "Name": "Alex", "Policy": {}}])
        self.addCleanup(app.stop)
        s = [service("jellyfin", app.url)]
        self.assertEqual(people_apps.change_password(s, "jellyfin", "sam", "a long new password"), "Changed it in Jellyfin")
        method, path, headers, body = app.seen[-1]
        self.assertEqual((method, path), ("POST", "/Users/Password?userId=u1"))
        self.assertEqual(json.loads(body), {"NewPw": "a long new password", "ResetPassword": False})
        self.assertIn("admin-key", headers["Authorization"])
        self.assertEqual([x[0] for x in app.seen], ["GET", "POST"])  # the list, then one change

    def test_emby_uses_its_own_path_and_header(self):
        app = App([{"Id": "9", "Name": "Sam"}])
        self.addCleanup(app.stop)
        people_apps.change_password([service("emby", app.url)], "emby", "Sam", "a long new password")
        method, path, headers, body = app.seen[-1]
        self.assertEqual((method, path, headers["X-Emby-Token"]), ("POST", "/emby/Users/9/Password", "admin-key"))
        self.assertEqual(json.loads(body), {"CurrentPw": "", "NewPw": "a long new password", "ResetPassword": False})

    def test_audiobookshelf_patches_the_user(self):
        app = App({"users": [{"id": "x1", "username": "sam", "isActive": True}]})
        self.addCleanup(app.stop)
        people_apps.change_password([service("audiobookshelf", app.url)], "audiobookshelf", "Sam", "a long new password")
        method, path, headers, body = app.seen[-1]
        self.assertEqual((method, path, headers["Authorization"]), ("PATCH", "/api/users/x1", "Bearer admin-key"))
        self.assertEqual(json.loads(body), {"password": "a long new password"})

    def test_no_such_account_is_said_and_nothing_is_changed(self):
        app = App([{"Id": "u1", "Name": "Alex"}])
        self.addCleanup(app.stop)
        with self.assertRaises(people.PeopleError) as e:
            people_apps.change_password([service("jellyfin", app.url)], "jellyfin", "Sam", "a long new password")
        self.assertIn("has no account called Sam", str(e.exception))
        self.assertEqual([x[0] for x in app.seen], ["GET"])

    def test_a_refusal_is_said_without_the_password(self):
        app = App([{"Id": "u1", "Name": "Sam"}], status=403)
        self.addCleanup(app.stop)
        with self.assertRaises(services.ServiceError) as e:
            people_apps.change_password([service("jellyfin", app.url)], "jellyfin", "Sam", "a long new password")
        self.assertIn("refused", str(e.exception))
        self.assertNotIn("a long new password", str(e.exception))

    def test_an_app_that_is_not_there_or_not_supported_is_refused(self):
        for kind in ("kavita", "plex"):
            with self.assertRaises((people.PeopleError, LookupError)):
                people_apps.change_password([service(kind, "http://127.0.0.1:9")], kind, "Sam", "a long new password")
        with self.assertRaises(LookupError):
            people_apps.change_password([], "jellyfin", "Sam", "a long new password")
        self.assertFalse(people_apps.supports({"type": "jellyfin", "url": "http://x", "api_key": ""}))  # no key: no admin route

    def test_an_unreachable_app_is_said(self):
        with self.assertRaises(services.ServiceError) as e:
            people_apps.change_password([service("jellyfin", "http://127.0.0.1:1")], "jellyfin", "Sam", "a long new password")
        self.assertIn("Cannot reach", str(e.exception))


if __name__ == "__main__":
    unittest.main()
