"""Reelix's admin settings from Starboard (DASH-154 to 156 with DASH-133), against tests/reelix_stand_in.py: sign in for
one change and out again, nothing kept, forms checked against the schema, sites to search added only when chosen,
searches through the VPN, and Jellyfin and Audiobookshelf connected with the keys Starboard has."""
import http.client
import json
import os
import tempfile
import threading
import unittest

from starboard import auth, reelix_admin, reelix_sites, reelix_setup, stack
from starboard.server import make_server
from tests.reelix_stand_in import StandIn, serve

PASSWORD = "reelix-admin-password"


class StandInTest(unittest.TestCase):
    def setUp(self):
        self.state = StandIn(password=PASSWORD)
        self.server, self.base = serve(self.state)
        reelix_admin.forget_catalogues()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def stack_with(self, *apps):
        os.makedirs(stack.folder(self.tmp.name), exist_ok=True)
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml"), "w") as f:
            f.write("services:\n" + "".join(f"  {a}:\n    container_name: {a}\n" for a in apps))


class VisitTest(StandInTest):
    def test_signs_in_for_one_change_then_out_and_keeps_nothing(self):
        visit = reelix_admin.Visit(self.base, PASSWORD)
        with visit as reelix:
            self.assertEqual(reelix.call("GET", "/settings/indexers")[0], 200)
            self.assertIsNone(visit.password)  # used once, then gone
        self.assertEqual((self.state.logins, self.state.logouts), (1, 1))
        self.assertEqual(self.state.sessions, set())
        self.assertIsNone(visit.session)

    def test_signs_out_even_when_the_change_fails(self):
        with self.assertRaises(ValueError):
            with reelix_admin.Visit(self.base, PASSWORD):
                raise ValueError("a change that failed")
        self.assertEqual(self.state.logouts, 1)

    def test_a_wrong_password_is_said_in_words(self):
        with self.assertRaises(reelix_admin.WrongPassword) as e:
            with reelix_admin.Visit(self.base, "not it"):
                pass
        self.assertIn("did not accept that password for its user admin", str(e.exception))
        with self.assertRaises(reelix_admin.WrongPassword):
            reelix_admin.Visit(self.base, "")

    def test_cookie_changes_carry_the_cross_site_header(self):
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            reelix.call("PUT", "/settings/indexers", {"rss_interval_minutes": 30})  # the stand-in refuses one without it
        self.assertEqual(self.state.search["rss_interval_minutes"], 30)


class FormsTest(StandInTest):
    FIELDS = [{"name": "url", "label": "URL", "type": "url", "required": True},
              {"name": "api_key", "label": "API key", "type": "secret", "required": True},
              {"name": "on", "label": "On", "type": "bool"}, {"name": "n", "label": "Seeders", "type": "number"},
              {"name": "cats", "label": "Categories", "type": "list"},
              {"name": "sort", "label": "Sort", "type": "select", "options": [{"value": "time"}, {"value": "seeders"}]}]

    def test_only_schema_fields_each_as_its_kind(self):
        out = reelix_admin.clean_settings(self.FIELDS, {"url": "https://a.example/", "api_key": "k", "on": "true", "n": "3",
                                                        "cats": "2000, 5000", "sort": "seeders", "command": "rm -rf /"})
        self.assertEqual(out, {"url": "https://a.example/", "api_key": "k", "on": True, "n": 3, "cats": [2000, 5000], "sort": "seeders"})

    def test_problems_are_said_together(self):
        with self.assertRaises(ValueError) as e:
            reelix_admin.clean_settings(self.FIELDS, {"url": "ftp://x", "api_key": "", "n": "many", "sort": "size"})
        for words in ("enter an address starting http://", "API key is needed", "enter a number", "choose one of the choices"):
            self.assertIn(words, str(e.exception))

    def test_a_masked_or_empty_secret_keeps_the_saved_one_when_changing(self):
        out = reelix_admin.clean_settings(self.FIELDS, {"url": "https://a.example/", "api_key": "********"}, editing=True)
        self.assertNotIn("api_key", out)
        out = reelix_admin.clean_settings(self.FIELDS, {"url": "https://a.example/", "api_key": ""}, editing=True)
        self.assertNotIn("api_key", out)

    def test_catalogue_is_slim_kept_a_while_and_one_schema_has_its_fields(self):
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            first = reelix_admin.catalogue(reelix, "indexers", self.base)
            reelix_admin.catalogue(reelix, "indexers", self.base)
            self.assertEqual(self.state.calls.count(("GET", "/indexers/schema")), 1)  # the second came from the cache
            self.assertNotIn("fields", first[0])
            self.assertEqual(first[0]["source"], "builtin")  # Torznab and Newznab first
            one = reelix_admin.schema_of(reelix, "indexers", "definition:1337x")
            self.assertEqual(one["fields"][0]["name"], "base_url")
            with self.assertRaises(ValueError):
                reelix_admin.schema_of(reelix, "indexers", "definition:nothing")
            media = reelix_admin.catalogue(reelix, "mediaservers", self.base)
            self.assertIn("fields", media[0])  # short lists come with their fields

    def test_test_save_change_and_remove(self):
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            item = {"implementation": "torznab", "name": "Mine", "settings": {"base_url": "https://mine.example/api", "api_key": "abc"}}
            self.assertTrue(reelix_admin.test(reelix, "indexers", item)["ok"])
            self.assertFalse(reelix_admin.test(reelix, "indexers", {**item, "settings": {"base_url": "https://fails.example/"}})["ok"])
            saved = reelix_admin.save(reelix, "indexers", item)
            self.assertEqual(saved["settings"]["api_key"], "********")
            changed = reelix_admin.save(reelix, "indexers", {**item, "id": saved["id"], "name": "Mine again",
                                                             "settings": {**saved["settings"], "categories": "2000"}})
            self.assertEqual(changed["name"], "Mine again")
            self.assertEqual(self.state.items["indexers"][0]["settings"]["api_key"], "abc")  # the saved secret stayed
            reelix_admin.remove(reelix, "indexers", saved["id"])
            self.assertEqual(self.state.items["indexers"], [])

    def test_listing_brings_each_sites_state_and_results(self):
        self.state.add("indexers", "definition:yts", "YTS", {"base_url": "https://yts.example/"})
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            out = reelix_admin.listing(reelix, "indexers")
        self.assertEqual(out["items"][0]["stats"]["queries"], 13)
        self.assertEqual(out["definitions"]["loaded"], len(self.state.items) and out["definitions"]["loaded"])


class SitesTest(StandInTest):
    def test_nothing_is_added_unless_chosen(self):
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            self.assertEqual(reelix_sites.add_sites(reelix, reelix_sites.clean_choice({})), [])
        self.assertNotIn(("GET", "/indexers/schema"), self.state.calls)

    def test_chosen_sites_and_your_own_address_are_added_once(self):
        choice = reelix_sites.clean_choice({"builtin": ["definition:1337x", "definition:eztv", "definition:1337x"],
                                            "own": [{"kind": "newznab", "url": "https://usenet.example/api", "api_key": "k1"}]})
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            done = reelix_sites.add_sites(reelix, choice)
            again = reelix_sites.add_sites(reelix, choice)
        self.assertEqual(done, ["Added 1337x", "Added EZTV", "Added usenet.example"])
        self.assertEqual(again, [])
        added = {i["implementation"]: i for i in self.state.items["indexers"]}
        self.assertEqual(added["definition:1337x"]["settings"]["sort"], "time")  # the schema's defaults
        self.assertLessEqual({"base_url": "https://usenet.example/api", "api_key": "k1"}.items(), added["newznab"]["settings"].items())

    def test_a_site_reelix_no_longer_has_or_refuses_is_said(self):
        choice = reelix_sites.clean_choice({"builtin": ["definition:gone"], "own": [{"url": "http://blocked.example/"}]})
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            done = reelix_sites.add_sites(reelix, choice)
        self.assertIn("gone is not in this Reelix's list of sites", done[0])
        self.assertIn("Turn on Addresses on your network in Settings, Reelix, Sites to search", done[1])

    def test_choices_are_checked(self):
        for bad in ({"builtin": ["rm -rf /"]}, {"own": [{"url": "file:///etc/passwd"}]}, {"own": [{"kind": "ftp", "url": "http://a/"}]}):
            with self.assertRaises(ValueError):
                reelix_sites.clean_choice(bad)
        self.assertEqual(reelix_sites.describe(reelix_sites.clean_choice({"builtin": ["definition:yts"],
                                                                          "own": [{"url": "https://idx.example/"}]})),
                         "YTS, idx.example (Torznab)")
        self.assertIn("None yet", reelix_sites.describe({}))

    def test_searches_through_the_vpn_and_back(self):
        self.stack_with("reelix", "gluetun", "flaresolverr")
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            self.assertFalse(reelix_sites.search_state(reelix, self.tmp.name)["through_vpn"])
            reelix_sites.set_vpn(reelix, self.tmp.name, True)
            state = reelix_sites.search_state(reelix, self.tmp.name)
            self.assertTrue(state["through_vpn"] and state["vpn_available"] and state["allow_private"])
            self.assertEqual(state["proxy"], "http://gluetun:8888")
            self.assertEqual(state["flaresolverr"], "http://gluetun:8191")
            reelix_sites.set_vpn(reelix, self.tmp.name, False)
            self.assertFalse(reelix_sites.search_state(reelix, self.tmp.name)["through_vpn"])

    def test_gluetun_runs_its_proxy_for_reelix(self):
        built = stack.build({"apps": ["reelix", "gluetun", "qbittorrent"], "config_dir": "/srv/c", "data_dir": "/srv/m",
                             "vpn": {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "x",
                                     "wireguard_addresses": "10.0.0.2/32"}})
        self.assertIn("HTTPPROXY: \"on\"", built["compose"].replace("HTTPPROXY: on", "HTTPPROXY: \"on\""))

    def test_the_set_ups_choice_is_kept_for_reelix_and_checked_first(self):
        choice = {"apps": ["reelix", "gluetun", "qbittorrent"], "config_dir": "/srv/c", "data_dir": "/srv/m",
                  "vpn": {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "x", "wireguard_addresses": "10.0.0.2/32"},
                  "sites": {"builtin": ["definition:yts"], "own": [{"url": "https://idx.example/", "api_key": "k"}]}}
        built = stack.build(choice)
        os.makedirs(stack.folder(self.tmp.name), exist_ok=True)
        stack.note_reelix(self.tmp.name, choice, built)
        info = reelix_setup.read_setup(self.tmp.name)
        self.assertTrue(info["vpn"])
        self.assertEqual(info["sites"]["builtin"], ["definition:yts"])
        self.assertEqual(oct(os.stat(reelix_setup.setup_file(self.tmp.name)).st_mode & 0o777), "0o600")  # it holds a key
        with self.assertRaises(ValueError):
            stack.build({**choice, "sites": {"own": [{"url": "not an address"}]}})


class MediaServersTest(StandInTest):
    SERVICES = [{"type": "jellyfin", "api_key": "jf-key", "url": "http://127.0.0.1:8096"},
                {"type": "audiobookshelf", "api_key": "abs-key", "url": "http://192.168.1.5:13378"}]

    def test_connected_with_the_keys_starboard_has(self):
        self.stack_with("reelix", "jellyfin")
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            done = reelix_sites.connect_media_servers(reelix, self.SERVICES, self.tmp.name)
            again = reelix_sites.connect_media_servers(reelix, self.SERVICES, self.tmp.name)
        self.assertEqual(done, ["Connected Reelix to Jellyfin", "Connected Reelix to Audiobookshelf"])
        self.assertEqual(again, [])
        got = {i["implementation"]: i["settings"] for i in self.state.items["mediaservers"]}
        self.assertEqual(got["jellyfin"], {"url": "http://jellyfin:8096", "api_key": "jf-key"})  # by name inside the stack
        self.assertEqual(got["audiobookshelf"]["url"], "http://192.168.1.5:13378")  # not Starboard's: its own address

    def test_no_keys_no_call(self):
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            self.assertEqual(reelix_sites.connect_media_servers(reelix, [{"type": "jellyfin", "url": "http://x"}], self.tmp.name), [])
        self.assertNotIn(("GET", "/mediaservers"), self.state.calls)

    def test_offers_say_what_is_connected_and_what_could_be(self):
        self.state.add("mediaservers", "jellyfin", "Jellyfin", {"url": "http://jellyfin:8096", "api_key": "x"})
        offers = reelix_sites.media_server_offers(self.SERVICES[:1], self.tmp.name, self.state.items["mediaservers"])
        self.assertEqual([(o["app"], o["connected"], o["has_key"]) for o in offers],
                         [("jellyfin", True, True), ("audiobookshelf", False, False)])


class AfterInstallTest(StandInTest):
    """Install apps run again with a Reelix set up before: Jellyfin and Audiobookshelf are connected with the
    keys Starboard has, signing in with the password just checked."""

    class App:
        def __init__(self, data_dir, services):
            self.data_dir = data_dir
            self.config = type("Config", (), {"data": {"services": services}})()

    def test_connects_with_the_password_just_checked(self):
        port = self.base.rsplit(":", 1)[1]
        os.makedirs(stack.folder(self.tmp.name), exist_ok=True)
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml"), "w") as f:
            f.write(f'services:\n  reelix:\n    container_name: reelix\n    ports:\n      - "{port}:7700"\n')
        self.state.handle = self._healthy(self.state.handle)
        app = self.App(self.tmp.name, MediaServersTest.SERVICES)
        reelix_sites.after_install(app, PASSWORD, wait=False).join(20)
        self.assertEqual(sorted(i["implementation"] for i in self.state.items["mediaservers"]), ["audiobookshelf", "jellyfin"])
        self.assertEqual(self.state.logins, self.state.logouts)

    def test_nothing_without_keys_or_reelix(self):
        self.assertIsNone(reelix_sites.after_install(self.App(self.tmp.name, MediaServersTest.SERVICES), PASSWORD, wait=False))
        self.assertIsNone(reelix_sites.after_install(self.App(self.tmp.name, []), PASSWORD, wait=False))

    @staticmethod
    def _healthy(handle):
        def wrapped(method, path, body=None, headers=None):
            if path == "/system/health":
                return 200, {"status": "ok"}, None
            return handle(method, path, body, headers)
        return wrapped


class RouteTest(StandInTest):
    """Through Starboard: signed in to Starboard, the Reelix password in the body, never kept."""

    def setUp(self):
        super().setUp()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        self.sb, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.sb.serve_forever, daemon=True).start()
        self.cookie = None
        resp, _ = self.request("POST", "/api/setup", {"token": self.app.setup_token, "password": "correct horse battery"})
        self.cookie = resp.getheader("Set-Cookie").split(";")[0]
        self.request("POST", "/api/services", {"name": "Reelix", "type": "link", "icon": "reelix", "url": self.base, "api_key": "manager"})
        self.request("POST", "/api/services", {"name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "jf-key"})

    def tearDown(self):
        self.sb.shutdown()
        self.sb.server_close()
        super().tearDown()

    def request(self, method, path, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.sb.server_address[1], timeout=10)
        h = {"Content-Type": "application/json", "X-Starboard": "1"}
        if self.cookie:
            h["Cookie"] = self.cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp, json.loads(raw or b"null")

    def test_about_needs_no_password(self):
        resp, about = self.request("GET", "/api/reelix/admin/about")
        self.assertEqual(resp.status, 200)
        self.assertEqual(about["media_keys"], ["jellyfin"])
        self.assertTrue(about["address"].startswith("127.0.0.1:"))

    def test_open_add_and_connect(self):
        resp, out = self.request("POST", "/api/reelix/admin/indexers/open", {"password": PASSWORD})
        self.assertEqual(resp.status, 200)
        self.assertEqual(out["items"], [])
        self.assertIn("definition:1337x", out["suggested"])
        resp, out = self.request("POST", "/api/reelix/admin/indexers/save", {"password": PASSWORD, "item": {
            "implementation": "definition:eztv", "name": "EZTV", "settings": {"base_url": "https://eztv.example/"}}})
        self.assertEqual((resp.status, out["items"][0]["name"]), (200, "EZTV"))
        resp, out = self.request("POST", "/api/reelix/admin/mediaservers/connect", {"password": PASSWORD})
        self.assertEqual(out["done"], ["Connected Reelix to Jellyfin"])
        self.assertEqual(self.state.logins, self.state.logouts)  # every visit signed out again
        with open(os.path.join(self.tmp.name, "config.json")) as f:
            self.assertNotIn(PASSWORD, f.read())  # never kept

    def test_a_wrong_password_stays_on_the_page_and_counts(self):
        resp, out = self.request("POST", "/api/reelix/admin/indexers/open", {"password": "wrong"})
        self.assertEqual((resp.status, out["reason"]), (401, "password"))
        for _ in range(12):
            resp, out = self.request("POST", "/api/reelix/admin/indexers/open", {"password": "wrong"})
        self.assertEqual(resp.status, 429)
        self.app.limits.clear("127.0.0.1")

    def test_other_kinds_and_actions_are_refused(self):
        resp, _ = self.request("POST", "/api/reelix/admin/users/open", {"password": PASSWORD})
        self.assertEqual(resp.status, 404)
        resp, _ = self.request("POST", "/api/reelix/admin/indexers/delete-everything", {"password": PASSWORD})
        self.assertEqual(resp.status, 400)
        resp, _ = self.request("GET", "/api/reelix/admin/indexers/open")
        self.assertEqual(resp.status, 404)  # the password goes in a body, never an address


if __name__ == "__main__":
    unittest.main()
