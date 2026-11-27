"""Accounts inside the apps (DASH-589, stage 3): Jellyfin and Audiobookshelf against stateful stand-in servers that answer the way the
apps' source says. Not tried against a real app. Idempotence, the Child's limits, pause and remove, and that nothing else is touched."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import people, people_accounts as pacc, services


class Fake:
    """A small app that keeps its users, so a second call sees what the first one did."""
    def __init__(self, kind):
        self.kind, self.seen, self.users, self.next = kind, [], {}, 1
        me = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _read(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n) or b"{}") if n else {}

            def _send(self, code, obj=None):
                raw = json.dumps(obj).encode() if obj is not None else b""
                self.send_response(code)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def handle_any(self, method):
                body = self._read()
                path = self.path.split("?")[0]
                me.seen.append((method, path, body, dict(self.headers)))
                return me.route(method, path, body, self._send)

            do_GET = lambda self: self.handle_any("GET")  # noqa: E731
            do_POST = lambda self: self.handle_any("POST")  # noqa: E731
            do_PATCH = lambda self: self.handle_any("PATCH")  # noqa: E731
            do_DELETE = lambda self: self.handle_any("DELETE")  # noqa: E731
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def route(self, method, path, body, send):
        if self.kind == "jellyfin":
            if (method, path) == ("GET", "/Users"):
                return send(200, [{"Id": i, "Name": u["Name"], "Policy": u["Policy"]} for i, u in self.users.items()])
            if (method, path) == ("POST", "/Users/New"):
                uid = f"u{self.next}"
                self.next += 1
                self.users[uid] = {"Name": body["Name"], "Policy": {"IsAdministrator": False, "IsDisabled": False, "EnableAllFolders": True}}
                return send(200, {"Id": uid, "Name": body["Name"]})
            if method == "POST" and path.endswith("/Policy"):
                self.users[path.split("/")[2]]["Policy"] = body
                return send(204)
            if method == "DELETE" and path.startswith("/Users/"):
                self.users.pop(path.split("/")[2], None)
                return send(204)
            if path == "/Localization/ParentalRatings":
                return send(200, [{"Name": "G", "Value": 1}, {"Name": "PG", "Value": 5}, {"Name": "PG-13", "Value": 7}, {"Name": "R", "Value": 9}])
            if path == "/Library/VirtualFolders":
                return send(200, [{"Name": "Films", "ItemId": "lib1"}, {"Name": "Adult", "ItemId": "lib2"}])
        else:
            if (method, path) == ("GET", "/api/users"):
                return send(200, {"users": [{"id": i, **u} for i, u in self.users.items()]})
            if (method, path) == ("POST", "/api/users"):
                uid = f"x{self.next}"
                self.next += 1
                self.users[uid] = {"username": body["username"], "isActive": body.get("isActive", True), "permissions": body.get("permissions", {}),
                                   "librariesAccessible": body.get("librariesAccessible", [])}
                return send(200, {"user": {"id": uid}})
            if method == "PATCH" and path.startswith("/api/users/"):
                u = self.users[path.split("/")[3]]
                for k, v in body.items():
                    u[k] = {**u.get(k, {}), **v} if k == "permissions" else v
                return send(200, {"success": True})
            if method == "DELETE" and path.startswith("/api/users/"):
                self.users.pop(path.split("/")[3], None)
                return send(200, {"success": True})
            if path == "/api/libraries":
                return send(200, {"libraries": [{"id": "l1", "name": "Books"}, {"id": "l2", "name": "Adult"}]})
        send(404, {})


def svc(kind, url):
    return {"id": kind, "name": kind.capitalize(), "type": kind, "url": url, "api_key": "admin-key"}


class Jellyfin(unittest.TestCase):
    def setUp(self):
        self.app = Fake("jellyfin")
        self.addCleanup(self.app.stop)
        self.s = [svc("jellyfin", self.app.url)]

    def test_making_an_account_is_idempotent(self):
        self.assertEqual(pacc.ensure(self.s, "jellyfin", "Sam", "a long password here"), "Made the account in Jellyfin")
        self.assertEqual(pacc.ensure(self.s, "jellyfin", "sam", "a long password here"), "The account is in Jellyfin already")
        self.assertEqual(len(self.app.users), 1)
        created = [x for x in self.app.seen if x[1] == "/Users/New"]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0][2], {"Name": "Sam", "Password": "a long password here"})
        self.assertIn("admin-key", created[0][3]["Authorization"])

    def test_a_missing_password_is_said_and_nothing_is_made(self):
        with self.assertRaises(people.PeopleError):
            pacc.ensure(self.s, "jellyfin", "Sam", "")
        self.assertEqual(self.app.users, {})

    def test_a_child_gets_the_limits_and_they_are_applied_again_without_a_second_account(self):
        words = pacc.ensure(self.s, "jellyfin", "Alex", "a long password here", child=True, limits={"rating": "PG-13", "libraries": ["lib1"]})
        self.assertEqual(words, "Made the account in Jellyfin with a child's limits")
        policy = next(iter(self.app.users.values()))["Policy"]
        self.assertEqual((policy["MaxParentalRating"], policy["EnableAllFolders"], policy["EnabledFolders"]), (7, False, ["lib1"]))
        self.assertEqual((policy["EnableContentDeletion"], policy["EnableContentDownloading"]), (False, False))
        self.assertIn("applied again", pacc.ensure(self.s, "jellyfin", "Alex", "a long password here", child=True))
        self.assertEqual(len(self.app.users), 1)
        self.assertEqual(next(iter(self.app.users.values()))["Policy"]["MaxParentalRating"], 5)  # the default, PG, when none is chosen

    def test_a_grown_up_keeps_the_policy_as_it_was(self):
        pacc.ensure(self.s, "jellyfin", "Sam", "a long password here")
        self.assertNotIn("MaxParentalRating", next(iter(self.app.users.values()))["Policy"])

    def test_pause_and_resume_change_only_the_disabled_flag_and_are_idempotent(self):
        pacc.ensure(self.s, "jellyfin", "Sam", "a long password here")
        before = dict(next(iter(self.app.users.values()))["Policy"])
        self.assertEqual(pacc.set_paused(self.s, "jellyfin", "Sam", True), "Paused the account in Jellyfin")
        after = next(iter(self.app.users.values()))["Policy"]
        self.assertEqual({**before, "IsDisabled": True}, after)
        self.assertIn("paused already", pacc.set_paused(self.s, "jellyfin", "Sam", True))
        self.assertEqual(pacc.check(self.s, "jellyfin", "Sam"), {"exists": True, "paused": True})
        self.assertEqual(pacc.set_paused(self.s, "jellyfin", "Sam", False), "Resumed the account in Jellyfin")
        self.assertIn("active already", pacc.set_paused(self.s, "jellyfin", "Sam", False))

    def test_removing_is_idempotent_and_only_the_named_account_goes(self):
        pacc.ensure(self.s, "jellyfin", "Sam", "a long password here")
        pacc.ensure(self.s, "jellyfin", "Alex", "a long password here")
        self.assertEqual(pacc.remove(self.s, "jellyfin", "Sam"), "Removed the account in Jellyfin")
        self.assertEqual([u["Name"] for u in self.app.users.values()], ["Alex"])
        self.assertIn("nothing changed", pacc.remove(self.s, "jellyfin", "Sam"))
        self.assertIn("nothing changed", pacc.set_paused(self.s, "jellyfin", "Sam", True))
        self.assertEqual(pacc.check(self.s, "jellyfin", "Sam"), {"exists": False, "paused": False})

    def test_ratings_and_libraries_for_the_dialog(self):
        self.assertEqual([r["name"] for r in pacc.ratings(self.s, "jellyfin")], ["G", "PG", "PG-13", "R"])
        self.assertEqual(pacc.libraries(self.s, "jellyfin"), [{"id": "lib1", "name": "Films"}, {"id": "lib2", "name": "Adult"}])


class Audiobookshelf(unittest.TestCase):
    def setUp(self):
        self.app = Fake("audiobookshelf")
        self.addCleanup(self.app.stop)
        self.s = [svc("audiobookshelf", self.app.url)]

    def test_make_pause_resume_remove_each_idempotent(self):
        self.assertEqual(pacc.ensure(self.s, "audiobookshelf", "Sam", "a long password here"), "Made the account in Audiobookshelf")
        self.assertIn("already", pacc.ensure(self.s, "audiobookshelf", "Sam", "a long password here"))
        self.assertEqual(len(self.app.users), 1)
        self.assertEqual(pacc.set_paused(self.s, "audiobookshelf", "Sam", True), "Paused the account in Audiobookshelf")
        self.assertIn("paused already", pacc.set_paused(self.s, "audiobookshelf", "Sam", True))
        self.assertIs(next(iter(self.app.users.values()))["isActive"], False)
        self.assertEqual(pacc.set_paused(self.s, "audiobookshelf", "Sam", False), "Resumed the account in Audiobookshelf")
        self.assertEqual(pacc.remove(self.s, "audiobookshelf", "Sam"), "Removed the account in Audiobookshelf")
        self.assertIn("nothing changed", pacc.remove(self.s, "audiobookshelf", "Sam"))
        self.assertEqual(self.app.users, {})

    def test_a_child_gets_only_the_chosen_libraries_and_no_downloads(self):
        pacc.ensure(self.s, "audiobookshelf", "Alex", "a long password here", child=True, limits={"libraries": ["l1"]})
        u = next(iter(self.app.users.values()))
        self.assertEqual((u["permissions"]["download"], u["permissions"]["accessAllLibraries"], u["librariesAccessible"]), (False, False, ["l1"]))
        pacc.ensure(self.s, "audiobookshelf", "Alex", "a long password here", child=True, limits={"libraries": ["l1", "l2"]})
        self.assertEqual(next(iter(self.app.users.values()))["librariesAccessible"], ["l1", "l2"])
        self.assertEqual(len(self.app.users), 1)
        self.assertEqual(pacc.libraries(self.s, "audiobookshelf"), [{"id": "l1", "name": "Books"}, {"id": "l2", "name": "Adult"}])

    def test_a_grown_up_may_download(self):
        pacc.ensure(self.s, "audiobookshelf", "Sam", "a long password here")
        self.assertIs(next(iter(self.app.users.values()))["permissions"]["download"], True)


class Refusals(unittest.TestCase):
    def test_other_apps_are_only_recorded_and_emby_is_off(self):
        for kind in ("kavita", "emby", "plex", "sonarr"):
            s = [{"id": kind, "name": kind.capitalize(), "type": kind, "url": "http://127.0.0.1:9", "api_key": "k"}]
            with self.assertRaises(people.PeopleError) as e:
                pacc.ensure(s, kind, "Sam", "a long password here")
            self.assertIn("only records them", str(e.exception))
        with mock.patch.object(pacc, "ACCOUNT_APPS", ("emby",)):
            self.assertTrue(pacc.supports({"type": "emby", "url": "http://x", "api_key": "k"}))  # one line turns it on
        with self.assertRaises(LookupError):
            pacc.check([], "jellyfin", "Sam")

    def test_a_refusal_or_an_unreachable_app_is_said_without_the_password(self):
        s = [svc("jellyfin", "http://127.0.0.1:1")]
        with self.assertRaises(services.ServiceError) as e:
            pacc.ensure(s, "jellyfin", "Sam", "a long password here")
        self.assertNotIn("a long password here", str(e.exception))
        self.assertIn("Cannot reach", str(e.exception))


if __name__ == "__main__":
    unittest.main()
