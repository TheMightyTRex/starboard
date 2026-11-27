"""People (DASH-589, single sign-on stage 1): the person list, the passwords Starboard makes for each app, and who may reach them."""
import http.client
import json
import os
import stat
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, logs, people, shell
from starboard.server import make_server

PASSWORD = "correct horse battery"
SERVICES = [{"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": "http://jellyfin:8096", "link": "http://192.168.1.20:8096"},
            {"id": "audiobookshelf", "name": "Audiobookshelf", "type": "audiobookshelf", "url": "http://abs:80"},
            {"id": "sonarr", "name": "Sonarr", "type": "sonarr", "url": "http://sonarr:8989"},
            {"id": "qbittorrent", "name": "qBittorrent", "type": "qbittorrent", "url": "http://qbit:8080"},
            {"id": "kavita", "name": "Kavita", "type": "link", "url": "http://kavita:5000"},
            {"id": "wizarr", "name": "Wizarr", "type": "link", "url": "http://wizarr:5690"},
            {"id": "off", "name": "Navidrome", "type": "link", "url": "http://nd:4533", "enabled": False}]


class Model(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name="Sam", role="household", email=""):
        return people.add(self.dir, name, email, role)

    def test_only_the_apps_people_use_are_offered(self):
        names = [a["name"] for a in people.apps_from(SERVICES)]
        self.assertEqual(names, ["Jellyfin", "Audiobookshelf", "Kavita"])  # no download app, no tool, nothing switched off
        self.assertEqual(people.apps_from(SERVICES)[0]["address"], "http://192.168.1.20:8096")  # the address people open

    def test_a_person_needs_a_name_a_real_role_and_a_sensible_email(self):
        for bad in ("", "   ", "x" * 41, "<b>Sam</b>", "Sam\x07"):
            with self.assertRaises(people.PeopleError, msg=repr(bad)):
                self.add(bad)
        with self.assertRaises(people.PeopleError):
            self.add(role="owner")  # the owner is never made here
        with self.assertRaises(people.PeopleError):
            self.add(email="not an address")
        self.assertEqual(self.add("  Alex   Jones ", email="alex@example.org")["name"], "Alex Jones")

    def test_two_people_cannot_share_a_name_until_one_is_removed(self):
        a = self.add("Sam")
        with self.assertRaises(people.PeopleError):
            self.add("sam")
        people.set_state(self.dir, a["id"], "remove")
        b = self.add("Sam")
        with self.assertRaises(people.PeopleError):
            people.set_state(self.dir, a["id"], "restore")  # two active Sams
        people.update(self.dir, b["id"], "Samira", "", "guest")
        self.assertEqual(people.set_state(self.dir, a["id"], "restore")["state"], "active")

    def test_the_most_people_is_fifty(self):
        for i in range(people.MAX_PEOPLE):
            self.add(f"Person {i}")
        with self.assertRaises(people.PeopleError):
            self.add("One more")

    def test_fifty_people_with_a_password_in_three_apps_each_stay_under_100_kb(self):
        services = SERVICES[:2] + [SERVICES[4]]
        for i in range(people.MAX_PEOPLE):
            p = self.add(f"Person {i}", email=f"person{i}@example.org")
            for app in ("jellyfin", "audiobookshelf", "kavita"):
                people.new_password(self.dir, services, p["id"], app)
        self.assertLess(os.path.getsize(os.path.join(self.dir, people.FILE)), 100 * 1024)

    def test_pause_resume_remove_restore_follow_the_rules(self):
        p = self.add()
        self.assertEqual(people.set_state(self.dir, p["id"], "pause")["state"], "paused")
        self.assertEqual(people.set_state(self.dir, p["id"], "resume")["state"], "active")
        with self.assertRaises(people.PeopleError):
            people.set_state(self.dir, p["id"], "resume")  # not paused
        people.set_state(self.dir, p["id"], "remove")
        with self.assertRaises(people.PeopleError):
            people.update(self.dir, p["id"], "Sam", "", "guest")  # put back first
        with self.assertRaises(people.PeopleError):
            people.set_state(self.dir, p["id"], "pause")
        with self.assertRaises(people.PeopleError):
            people.set_state(self.dir, p["id"], "explode")

    def test_a_removed_person_is_forgotten_only_after_thirty_days(self):
        p = self.add()
        with self.assertRaises(people.PeopleError):
            people.forget(self.dir, p["id"])  # not removed
        people.set_state(self.dir, p["id"], "remove")
        with self.assertRaises(people.PeopleError):
            people.forget(self.dir, p["id"])  # too soon
        shown = people.listing(self.dir, SERVICES)["people"][0]
        self.assertFalse(shown["can_forget"])
        self.assertEqual(shown["forget_in_days"], 30)
        data = people._read(self.dir)
        data["people"][0]["removed_at"] = "2026-01-01T00:00:00Z"
        people._write(self.dir, data)
        self.assertTrue(people.listing(self.dir, SERVICES)["people"][0]["can_forget"])
        people.forget(self.dir, p["id"])
        self.assertEqual(people.listing(self.dir, SERVICES)["people"], [])

    def test_a_password_is_long_random_and_has_no_confusing_characters(self):
        seen = {people.make_password() for _ in range(200)}
        self.assertEqual(len(seen), 200)
        for pw in seen:
            self.assertEqual(len(pw), 24)
            self.assertFalse(set(pw) & set("0O1lI"))
            self.assertTrue(set(pw) <= set(people.ALPHABET))

    def test_the_account_story_from_no_account_to_set_in_the_app(self):
        p = self.add()
        pid = p["id"]
        state = lambda: people.listing(self.dir, SERVICES)["people"][0]["accounts"]
        people.save_account(self.dir, SERVICES, pid, "jellyfin", "")
        self.assertEqual((state()[0]["username"], state()[0]["state"]), ("Sam", "none"))  # the name is the default
        with self.assertRaises(people.PeopleError):
            people.mark_set(self.dir, SERVICES, pid, "jellyfin", True)  # no password yet
        people.new_password(self.dir, SERVICES, pid, "jellyfin")
        self.assertEqual(state()[0]["state"], "made")
        first = people.reveal(self.dir, pid, "jellyfin")["password"]
        with self.assertRaises(people.PeopleError):
            people.new_password(self.dir, SERVICES, pid, "jellyfin")  # never replaced by accident
        people.mark_set(self.dir, SERVICES, pid, "jellyfin", True)
        self.assertEqual(state()[0]["state"], "in-use")
        people.new_password(self.dir, SERVICES, pid, "jellyfin", replace=True)
        self.assertEqual(state()[0]["state"], "made")  # a new password is not set in the app yet
        self.assertNotEqual(people.reveal(self.dir, pid, "jellyfin")["password"], first)
        people.drop_account(self.dir, pid, "jellyfin")
        self.assertEqual(state(), [])
        with self.assertRaises(LookupError):
            people.reveal(self.dir, pid, "jellyfin")

    def test_a_password_of_your_own_needs_ten_characters_and_nothing_else(self):
        p = self.add()
        for bad, words in (("", "Enter the password"), ("   ", "Enter the password"), ("short", "at least 10"), ("123456789", "at least 10"),
                           (" leadingspace1", "starts or ends with a space"), ("x" * 129, "128 characters or fewer"), ("tab\there-now", "cannot be entered")):
            with self.assertRaises(people.PeopleError, msg=bad) as e:
                people.set_password(self.dir, SERVICES, p["id"], "jellyfin", own=bad)
            self.assertIn(words, str(e.exception))
            if len(bad.strip()) >= 9:
                self.assertNotIn(bad.strip(), str(e.exception))  # the words never repeat it
        for fine in ("abcdefghij", "all lower case words only", "NoDigitsOrSymbolsHere"):  # no capitals, numbers or symbols asked for
            q = self.add(f"P {fine[:5]}")
            people.set_password(self.dir, SERVICES, q["id"], "jellyfin", own=fine)
            self.assertEqual(people.reveal(self.dir, q["id"], "jellyfin")["password"], fine)

    def test_an_own_password_is_recorded_as_chosen_and_a_generated_one_is_not(self):
        p = self.add()
        people.set_password(self.dir, SERVICES, p["id"], "jellyfin", own="my own long password")
        people.set_password(self.dir, SERVICES, p["id"], "audiobookshelf")
        by = {a["app"]: a for a in people.listing(self.dir, SERVICES)["people"][0]["accounts"]}
        self.assertEqual((by["jellyfin"]["own"], by["audiobookshelf"]["own"]), (True, False))
        self.assertEqual(len(people.reveal(self.dir, p["id"], "audiobookshelf")["password"]), 24)

    def test_replacing_needs_replace_and_clears_set_in_the_app(self):
        p = self.add()
        people.set_password(self.dir, SERVICES, p["id"], "jellyfin")
        people.mark_set(self.dir, SERVICES, p["id"], "jellyfin", True)
        with self.assertRaises(people.PeopleError):
            people.set_password(self.dir, SERVICES, p["id"], "jellyfin", own="another long one")
        people.set_password(self.dir, SERVICES, p["id"], "jellyfin", replace=True, own="another long one")
        acct = people.listing(self.dir, SERVICES)["people"][0]["accounts"][0]
        self.assertEqual((acct["state"], acct["own"]), ("made", True))

    def test_changing_it_in_the_app_is_recorded_only_when_the_app_took_it(self):
        p = self.add()
        calls = []
        people.set_password(self.dir, SERVICES, p["id"], "jellyfin", own="first long password", push=lambda u, pw: calls.append((u, pw)))
        self.assertEqual(calls, [("Sam", "first long password")])
        self.assertEqual(people.listing(self.dir, SERVICES)["people"][0]["accounts"][0]["state"], "in-use")  # the app has it

        def refuse(user, pw):
            raise people.PeopleError("Jellyfin has no account called Sam")
        with self.assertRaises(people.PeopleError):
            people.set_password(self.dir, SERVICES, p["id"], "jellyfin", replace=True, own="second long password", push=refuse)
        self.assertEqual(people.reveal(self.dir, p["id"], "jellyfin")["password"], "first long password")  # nothing was recorded

    def test_an_app_rule_raises_the_minimum_and_generated_passwords_meet_it(self):
        with mock.patch.dict(people.APP_RULES, {"jellyfin": {"min": 30, "note": "Jellyfin needs 30 characters."}}):
            self.assertEqual(people.rule_for(SERVICES[0]), {"min": 30, "known": True, "note": "Jellyfin needs 30 characters."})
            p = self.add()
            with self.assertRaises(people.PeopleError) as e:
                people.set_password(self.dir, SERVICES, p["id"], "jellyfin", own="a" * 29)
            self.assertIn("at least 30", str(e.exception))
            people.set_password(self.dir, SERVICES, p["id"], "jellyfin")
            self.assertGreaterEqual(len(people.reveal(self.dir, p["id"], "jellyfin")["password"]), 30)
        self.assertEqual(people.rule_for(SERVICES[0])["min"], 10)  # no rule known: ten, and the app may refuse it
        self.assertIn("may refuse", people.rule_for(SERVICES[0])["note"])
        self.assertEqual(people.listing(self.dir, SERVICES)["own_min"], 10)

    def test_every_person_and_app_gets_its_own_password(self):
        a, b = self.add("Sam"), self.add("Alex")
        for who in (a, b):
            for app in ("jellyfin", "audiobookshelf"):
                people.new_password(self.dir, SERVICES, who["id"], app)
        passwords = {people.reveal(self.dir, who["id"], app)["password"] for who in (a, b) for app in ("jellyfin", "audiobookshelf")}
        self.assertEqual(len(passwords), 4)

    def test_an_app_that_is_not_one_of_the_owners_is_refused(self):
        p = self.add()
        for app in ("sonarr", "nothing", "../x", "Jellyfin"):
            with self.assertRaises((LookupError, people.PeopleError), msg=app):
                people.new_password(self.dir, SERVICES, p["id"], app)

    def test_the_listing_never_holds_a_password(self):
        p = self.add()
        people.new_password(self.dir, SERVICES, p["id"], "jellyfin")
        secret = people.reveal(self.dir, p["id"], "jellyfin")["password"]
        self.assertNotIn(secret, json.dumps(people.listing(self.dir, SERVICES)))
        self.assertNotIn(secret, json.dumps(people.person_public(self.dir, SERVICES, p["id"])))

    def test_the_file_is_owner_only_and_a_damaged_one_is_an_empty_list(self):
        self.add()
        mode = stat.S_IMODE(os.stat(os.path.join(self.dir, people.FILE)).st_mode)
        self.assertEqual(mode, 0o600)
        with open(os.path.join(self.dir, people.FILE), "w") as f:
            f.write("{not json")
        self.assertEqual(people.listing(self.dir, SERVICES)["people"], [])

    def test_a_bad_id_is_not_found(self):
        for bad in ("", "p-zz", "../p-00000000", "p-0000000"):
            with self.assertRaises(LookupError, msg=bad):
                people.person_public(self.dir, SERVICES, bad)


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        _, _, headers = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": PASSWORD})
        cls.cookie = [v.split(";")[0] for k, v in headers if k.lower() == "set-cookie" and v.startswith("starboard_session=")][0]
        for s in SERVICES[:2]:
            cls.app.config.upsert_service({"name": s["name"], "type": s["type"], "url": s["url"], "api_key": "made-up"})

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, body=None, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=15)
        h = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            h["Cookie"] = cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, json.loads(raw or b"{}") if raw[:1] in (b"{", b"[") else {"raw": raw.decode("utf-8", "replace")}, r.getheaders())
        conn.close()
        return out

    def api(self, method, path, body=None, cookie=True):
        self.app.limits.clear("127.0.0.1")
        return self.call(method, path, body, self.cookie if cookie is True else cookie)[:2]

    def test_it_needs_the_owner_signed_in(self):
        for method, path in (("GET", "/api/people"), ("POST", "/api/people"), ("POST", "/api/people/p-00000000/pause"),
                             ("POST", "/api/people/p-00000000/accounts/jellyfin/reveal")):
            self.assertEqual(self.api(method, path, {}, cookie=None)[0], 401, path)

    def test_a_plug_in_key_cannot_reach_it(self):
        from starboard import api_v1
        key, _ = api_v1.create_key(self.tmp.name, "Plug-in: test", "manage", [], 90)
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/api/people", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(conn.getresponse().status, 401)
        conn.close()

    def test_add_change_account_and_password_end_to_end(self):
        status, out = self.api("POST", "/api/people", {"name": "Robin", "role": "child", "email": ""})
        self.assertEqual(status, 200, out)
        pid = out["person"]
        self.assertEqual([a["name"] for a in out["apps"]], ["Jellyfin", "Audiobookshelf"])
        status, out = self.api("POST", f"/api/people/{pid}/accounts/jellyfin/password", {})
        self.assertEqual(status, 200, out)
        self.assertEqual(next(p for p in out["people"] if p["id"] == pid)["accounts"][0]["state"], "made")
        self.assertNotIn(people.reveal(self.tmp.name, pid, "jellyfin")["password"], json.dumps(out))  # the listing holds no value
        status, out = self.api("POST", f"/api/people/{pid}/accounts/jellyfin/password", {})
        self.assertEqual(status, 400)  # not replaced by accident
        status, out = self.api("POST", f"/api/people/{pid}/accounts/sonarr/password", {})
        self.assertEqual(status, 404)  # not an app people use

    def test_showing_a_password_needs_the_starboard_password_each_time_and_is_never_logged(self):
        pid = self.api("POST", "/api/people", {"name": "Reveal", "role": "household"})[1]["person"]
        self.api("POST", f"/api/people/{pid}/accounts/audiobookshelf/password", {})
        kept = people.reveal(self.tmp.name, pid, "audiobookshelf")["password"]
        path = f"/api/people/{pid}/accounts/audiobookshelf/reveal"
        self.assertEqual(self.api("POST", path, {})[0], 401)
        self.assertEqual(self.api("POST", path, {"password": "wrong password"})[0], 401)
        lines = []
        with mock.patch.object(logs, "event", lambda level, area, message, **k: lines.append(message)):
            status, out = self.api("POST", path, {"password": PASSWORD})
            self.api("POST", f"/api/people/{pid}/accounts/audiobookshelf/password", {"replace": True, "password": PASSWORD})
        self.assertEqual((status, out["password"]), (200, kept))
        self.assertEqual(out["username"], "Reveal")
        self.assertTrue(lines)
        self.assertFalse([m for m in lines if kept in m or people.reveal(self.tmp.name, pid, "audiobookshelf")["password"] in m])

    def test_forgetting_needs_the_password_too(self):
        pid = self.api("POST", "/api/people", {"name": "Forget", "role": "guest"})[1]["person"]
        self.api("POST", f"/api/people/{pid}/remove", {})
        self.assertEqual(self.api("POST", f"/api/people/{pid}/forget", {})[0], 401)
        status, out = self.api("POST", f"/api/people/{pid}/forget", {"password": PASSWORD})
        self.assertEqual(status, 400, out)  # the password was right: it is too soon

    def test_own_passwords_and_resets_over_the_route(self):
        pid = self.api("POST", "/api/people", {"name": "Own", "role": "household"})[1]["person"]
        path = f"/api/people/{pid}/accounts/jellyfin/password"
        status, out = self.api("POST", path, {"own_password": "short"})
        self.assertEqual(status, 400)
        self.assertIn("at least 10", out["error"])
        self.assertNotIn("short", out["error"].replace("too short", ""))
        self.assertEqual(self.api("POST", path, {"own_password": "my own long password"})[0], 200)  # a first one needs no Starboard password
        self.assertEqual(people.reveal(self.tmp.name, pid, "jellyfin")["password"], "my own long password")
        self.assertEqual(self.api("POST", path, {"replace": True, "own_password": "a new long password"})[0], 401)  # a reset needs it
        self.assertEqual(self.api("POST", path, {"replace": True, "own_password": "a new long password", "password": "wrong password"})[0], 401)
        self.assertEqual(people.reveal(self.tmp.name, pid, "jellyfin")["password"], "my own long password")
        self.assertEqual(self.api("POST", path, {"replace": True, "own_password": "a new long password", "password": PASSWORD})[0], 200)
        self.assertEqual(people.reveal(self.tmp.name, pid, "jellyfin")["password"], "a new long password")

    def test_also_change_it_in_the_app_asks_the_password_calls_the_app_and_never_logs_it(self):
        from starboard import people_apps
        pid = self.api("POST", "/api/people", {"name": "Also", "role": "household"})[1]["person"]
        path = f"/api/people/{pid}/accounts/jellyfin/password"
        seen, lines = [], []
        with mock.patch.object(people_apps, "change_password", lambda services, app, user, pw: seen.append((app, user, pw)) or "ok"), \
                mock.patch.object(logs, "event", lambda level, area, message, **k: lines.append(message)):
            self.assertEqual(self.api("POST", path, {"also_change": True, "own_password": "typed long password"})[0], 401)
            self.assertEqual(seen, [])
            status, out = self.api("POST", path, {"also_change": True, "own_password": "typed long password", "password": PASSWORD})
        self.assertEqual((status, seen), (200, [("jellyfin", "Also", "typed long password")]))
        self.assertEqual(next(a for p in out["people"] if p["id"] == pid for a in p["accounts"])["state"], "in-use")
        self.assertFalse([m for m in lines if "typed long password" in m])

    def test_the_app_list_says_which_apps_starboard_can_change_and_the_rule(self):
        apps = self.api("GET", "/api/people")[1]["apps"]
        self.assertEqual({a["id"]: a["can_change"] for a in apps}, {"jellyfin": True, "audiobookshelf": True})
        self.assertTrue(all(a["rule"]["min"] == 10 for a in apps))

    def test_the_people_file_is_not_in_a_settings_backup(self):
        from starboard import backup
        self.api("POST", "/api/people", {"name": "Zed Backup", "role": "guest"})
        self.assertTrue(os.path.isfile(os.path.join(self.tmp.name, people.FILE)))
        self.assertNotIn("Zed", json.dumps(backup.export(self.app.config, self.app.version, self.tmp.name), default=str))


class Page(unittest.TestCase):
    def test_the_page_is_in_the_menu_and_has_help(self):
        settings = next(items for key, _n, _i, items in shell.MENU if key == "settings")
        pages = [p for _name, _icon, items in settings for p, _l, _i in items]
        self.assertIn("settings-people.html", pages)
        self.assertIn("settings-people.html", shell.HELP)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assertTrue(os.path.isfile(os.path.join(root, "web", "settings-people.html")))
        self.assertTrue(os.path.isfile(os.path.join(root, "docs", "help", shell.HELP["settings-people.html"][0])))


if __name__ == "__main__":
    unittest.main()
