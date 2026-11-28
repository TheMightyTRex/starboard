"""Plug-in API 1.25 (28 November 2026, DASH-620): the permission fetch with a list of named sites (POST /api/v1/plugin/fetch,
Starboard API 1.13.0), the record "What it fetched", and the hand-off folders handoff:send and handoff:receive."""
import base64
import http.client
import io
import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, auth, plugin_fetch, plugin_socket, plugin_tester, plugins, plugins_admin as pa
from starboard.server import make_server
from tests.test_plugins import ON_DEMAND

HOSTS = ["api.openverse.org", "api.pexels.com"]
FETCHING = {**ON_DEMAND, "id": "online-one", "name": "Online one", "starboard_api": ">=1.25 <2.0", "fetch": HOSTS,
            "permissions": [*ON_DEMAND["permissions"], "fetch", "handoff:send"],
            "containers": [{**ON_DEMAND["containers"][0], "network": "default", "volumes": ["data", "handoff/tv-pack:send"]}], "resources": {"main": {"memory": 40}}}
PLAIN = {**FETCHING, "id": "plain-two", "name": "Plain two", "permissions": ["system:read"], "containers": [{**FETCHING["containers"][0], "volumes": ["data"]}]}
PLAIN.pop("fetch")


class FakeResp:
    def __init__(self, status=200, body=b"{}", headers=None):
        self.status, self.fp, self.h = status, io.BytesIO(body), {"Content-Type": "application/json", **(headers or {})}

    def getheader(self, n, d=None):
        return self.h.get(n, d)

    def read(self, n=-1):
        return self.fp.read(n)


class FakeConn:
    def close(self):
        pass


def serving(*answers):
    """Stands in for the connection: answers in turn; records (host, path, headers)."""
    seen, left = [], list(answers)

    def get(host, path, ip, headers, timeout, context):
        seen.append((host, path, ip, dict(headers)))
        a = left.pop(0)
        if isinstance(a, Exception):
            raise a
        return FakeConn(), a
    return seen, mock.patch.object(plugin_fetch, "_get", side_effect=get)


PUBLIC = mock.patch.object(plugin_fetch, "resolve", return_value=["93.184.216.34"])


class Rules(unittest.TestCase):
    def test_only_public_addresses(self):
        for ok in ("93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946", "::ffff:93.184.216.34"):
            self.assertTrue(plugin_fetch.public_address(ok), ok)
        for bad in ("127.0.0.1", "::1", "10.0.0.5", "192.168.1.20", "172.16.0.1", "169.254.169.254", "100.64.0.1", "0.0.0.0", "224.0.0.1",
                    "fe80::1", "fd00::1", "::ffff:10.0.0.1", "::ffff:127.0.0.1", "64:ff9b::7f00:1", "2002:7f00:1::", "not an address"):
            self.assertFalse(plugin_fetch.public_address(bad), bad)

    def test_a_name_that_points_home_is_refused(self):
        for found in (["127.0.0.1"], ["93.184.216.34", "192.168.1.5"], ["169.254.169.254"]):
            with mock.patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", (a, 443)) for a in found]):
                with self.assertRaises(plugin_fetch.Refused):
                    plugin_fetch.resolve("api.pexels.com")

    def test_the_address_rules(self):
        h = ["api.pexels.com"]
        self.assertEqual(plugin_fetch.parse("https://api.pexels.com/v1/search?query=sea", h), ("api.pexels.com", "/v1/search?query=sea"))
        self.assertEqual(plugin_fetch.parse("https://API.pexels.com:443", h), ("api.pexels.com", "/"))
        for bad in ("http://api.pexels.com/", "https://other.example.com/", "https://api.pexels.com.evil.com/", "https://u:p@api.pexels.com/",
                    "https://api.pexels.com:8443/", "https://api.pexels.com/a#b", "https://127.0.0.1/", "https://api.pexels.com/a/../b",
                    "https://api.pexels.com/a b", "ftp://api.pexels.com/", 5, None, "https://api.pexels.com/" + "a" * 2000, "https://api.pexels.com@evil.com/"):
            with self.assertRaises(plugin_fetch.Refused, msg=str(bad)[:40]):
                plugin_fetch.parse(bad, h)

    def test_the_list_of_sites(self):
        self.assertEqual(plugin_fetch.hosts_problems(HOSTS), [])
        for bad in ([], "api.x.org", ["localhost"], ["10.0.0.1"], ["API.example.com"], ["*.example.com"], ["a.example.com:443"], ["nas.local"],
                    ["x.home.arpa"], ["a.example.com"] * 2, [f"s{i}.example.com" for i in range(13)], [5]):
            self.assertTrue(plugin_fetch.hosts_problems(bad), bad)


class Fetching(unittest.TestCase):
    def setUp(self):
        plugin_fetch.reset()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)
        pa.install(self.tmp, FETCHING, "/srv/media")
        self.who = {"id": "online-one", "name": "Online one"}

    def go(self, body, *answers):
        seen, patch = serving(*answers)
        with PUBLIC, patch:
            return plugin_fetch.fetch(self.tmp, self.who, HOSTS, body), seen

    def test_a_fetch_returns_the_body_and_is_recorded_without_the_path_or_keys(self):
        out, seen = self.go({"url": "https://api.pexels.com/v1/search?query=sea&key=SECRET", "what": "Search for backgrounds",
                             "headers": {"authorization": "KEY123"}}, FakeResp(200, b'{"a":1}'))
        self.assertEqual((out["status"], out["size"], out["host"]), (200, 7, "api.pexels.com"))
        self.assertEqual(base64.b64decode(out["body_base64"]), b'{"a":1}')
        self.assertEqual(seen[0][3]["Authorization"], "KEY123")
        rec = plugin_fetch.record_of(self.tmp, "online-one")
        self.assertEqual([(r["host"], r["what"], r["size"], r["result"]) for r in rec], [("api.pexels.com", "Search for backgrounds", 7, "ok")])
        with open(os.path.join(pa.folder(self.tmp, "online-one"), plugin_fetch.FILE)) as f:
            text = f.read()
        for secret in ("SECRET", "KEY123", "/v1/search", "query"):
            self.assertNotIn(secret, text)

    def test_a_redirect_goes_only_to_a_listed_site_and_a_key_does_not_follow(self):
        out, seen = self.go({"url": "https://api.pexels.com/a", "headers": {"X-Api-Key": "K", "Accept": "x/y"}},
                            FakeResp(302, b"", {"Location": "https://api.openverse.org/b"}), FakeResp(200, b"ok"))
        self.assertEqual(out["host"], "api.openverse.org")
        self.assertEqual(seen[1][3], {"Accept": "x/y"})
        for loc in ("https://evil.example.com/x", "http://api.pexels.com/x", "https://10.0.0.1/x"):
            with self.assertRaises(plugin_fetch.Refused):
                self.go({"url": "https://api.pexels.com/a"}, FakeResp(302, b"", {"Location": loc}))
        with self.assertRaises(plugin_fetch.Failed):  # in a circle
            self.go({"url": "https://api.pexels.com/a"}, *[FakeResp(302, b"", {"Location": "/a"})] * 5)

    def test_size_and_time_limits(self):
        with self.assertRaises(plugin_fetch.Failed):
            self.go({"url": "https://api.pexels.com/a", "max_bytes": 10}, FakeResp(200, b"x" * 100))
        with self.assertRaises(plugin_fetch.Failed):  # declared too big: refused before it is read
            self.go({"url": "https://api.pexels.com/a", "max_bytes": 10}, FakeResp(200, b"", {"Content-Length": "999"}))
        with mock.patch("time.monotonic", side_effect=[0, 1, 1000, 1001, 1002]):
            with self.assertRaises(plugin_fetch.Failed):
                self.go({"url": "https://api.pexels.com/a", "seconds": 5}, FakeResp(200, b"x" * 100))
        out, _ = self.go({"url": "https://api.pexels.com/a"}, FakeResp(500, b"e" * 100000))
        self.assertEqual((out["status"], out["size"]), (500, plugin_fetch.ERROR_BYTES))
        self.assertEqual(plugin_fetch.record_of(self.tmp, "online-one")[0]["result"], "answered 500")
        for bad in ({"seconds": 0}, {"seconds": 121}, {"max_bytes": 0}, {"max_bytes": 10 ** 9}, {"save_as": "../x"}, {"what": "x" * 61},
                    {"headers": {"Cookie": "a"}}, {"headers": {"Authorization": "a\nb"}}):
            with self.assertRaises(plugin_fetch.Refused, msg=str(bad)):
                self.go({"url": "https://api.pexels.com/a", **bad}, FakeResp())

    def test_a_big_file_is_saved_in_the_plugins_own_folder(self):
        out, _ = self.go({"url": "https://api.pexels.com/a", "save_as": "clip.mp4", "max_bytes": 1000000}, FakeResp(200, b"v" * 5000))
        self.assertEqual((out["saved"], out["size"]), ("clip.mp4", 5000))
        self.assertNotIn("body_base64", out)
        path = os.path.join(pa.folder(self.tmp, "online-one"), "data", "main", "fetched", "clip.mp4")
        self.assertEqual(os.path.getsize(path), 5000)
        with self.assertRaises(plugin_fetch.Failed):  # too big: nothing half written is left
            self.go({"url": "https://api.pexels.com/a", "save_as": "big.mp4", "max_bytes": 100}, FakeResp(200, b"v" * 500))
        self.assertEqual(sorted(os.listdir(os.path.dirname(path))), ["clip.mp4"])

    def test_a_refused_call_is_recorded_with_the_site_only(self):
        with self.assertRaises(plugin_fetch.Refused):
            self.go({"url": "https://evil.example.com/steal?token=abc", "what": "Odd"}, FakeResp())
        r = plugin_fetch.record_of(self.tmp, "online-one")[0]
        self.assertEqual((r["host"], r["result"]), ("evil.example.com", "refused"))

    def test_one_at_a_time_and_a_limit_a_minute(self):
        plugin_fetch._one.acquire()
        try:
            with mock.patch.object(plugin_fetch, "BUSY_WAIT", 0.05), PUBLIC:
                with self.assertRaises(api_v1.RateLimited):
                    plugin_fetch.fetch(self.tmp, self.who, HOSTS, {"url": "https://api.pexels.com/a"})
        finally:
            plugin_fetch._one.release()
        plugin_fetch.reset()
        with mock.patch.object(plugin_fetch, "PER_MINUTE", 2):
            self.go({"url": "https://api.pexels.com/a"}, FakeResp())
            self.go({"url": "https://api.pexels.com/a"}, FakeResp())
            with self.assertRaises(api_v1.RateLimited):
                self.go({"url": "https://api.pexels.com/a"}, FakeResp())

    def test_the_record_keeps_200(self):
        for i in range(450):
            plugin_fetch._record(self.tmp, "online-one", "api.pexels.com", f"n{i}", i, "ok")
        rec = plugin_fetch.record_of(self.tmp, "online-one")
        self.assertEqual((len(rec), rec[0]["what"]), (200, "n449"))


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sbfetch")
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.host_path = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}")
        cls.host_path.start()
        cls.keys = {}
        for m in (FETCHING, PLAIN):
            pa.install(cls.tmp, m, "/srv/media")
            pa.set_state(cls.tmp, m["id"], "enabled")
            with open(os.path.join(pa.folder(cls.tmp, m["id"]), "key")) as f:
                cls.keys[m["id"]] = f.read().strip()
        cls.manager, _ = api_v1.create_key(cls.tmp, "Home Assistant", "manage", [], 90)
        plugin_socket.start(cls.app)

    @classmethod
    def tearDownClass(cls):
        plugin_socket._reset_for_tests()
        cls.host_path.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        plugin_fetch.reset()

    def post(self, body, key=None, plugin="online-one"):
        from tests.test_plugin_api_socket import UnixConnection
        # a plug-in on its own network reaches Starboard only through its socket; a person's key goes over HTTP
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30) if key == self.manager else UnixConnection(plugin_socket.path_for(self.tmp, plugin))
        conn.request("POST", "/api/v1/plugin/fetch", body=json.dumps(body).encode(),
                     headers={"Authorization": f"Bearer {key or self.keys['online-one']}", "Content-Type": "application/json"})
        r = conn.getresponse()
        out = json.loads(r.read() or b"null")
        conn.close()
        return r, out

    def test_fetch_through_the_route(self):
        _, patch = serving(FakeResp(200, b"hello"))
        with PUBLIC, patch:
            r, body = self.post({"url": "https://api.openverse.org/v1/audio/?q=rain", "what": "Search for music"})
        self.assertEqual((r.status, body["ok"], base64.b64decode(body["body_base64"])), (200, True, b"hello"))

    def test_a_site_not_on_the_list_is_400_and_a_site_that_fails_is_502(self):
        r, body = self.post({"url": "https://example.com/"})
        self.assertEqual((r.status, body["code"]), (400, "bad_request"))
        self.assertIn("not on this plug-in's list", body["title"])
        _, patch = serving(OSError("down"))
        with PUBLIC, patch:
            r, body = self.post({"url": "https://api.pexels.com/x"})
        self.assertEqual((r.status, body["code"]), (502, "fetch_failed"))

    def test_any_other_key_gets_404(self):
        for key, who in ((self.manager, "online-one"), (self.keys["plain-two"], "plain-two")):
            r, body = self.post({"url": "https://api.pexels.com/x"}, key, who)
            self.assertEqual((r.status, body["code"]), (404, "not_found"))

    def test_through_the_plugins_own_socket(self):
        from tests.test_plugin_api_socket import UnixConnection
        c = UnixConnection(plugin_socket.path_for(self.tmp, "online-one"))
        _, patch = serving(FakeResp(200, b"x"))
        try:
            with PUBLIC, patch:
                c.request("POST", "/api/v1/plugin/fetch", body=json.dumps({"url": "https://api.pexels.com/x"}).encode(),
                          headers={"Authorization": f"Bearer {self.keys['online-one']}"})
                r = c.getresponse()
                self.assertEqual((r.status, json.loads(r.read())["size"]), (200, 1))
        finally:
            c.close()

    def test_what_it_fetched_is_on_the_plugins_page_data(self):
        plugin_fetch._record(self.tmp, "online-one", "api.pexels.com", "Look it up", 12, "ok")
        found = {p["id"]: p for p in pa.listing(self.tmp)}
        self.assertEqual(found["online-one"]["fetch"], HOSTS)
        self.assertEqual(found["plain-two"]["fetch"], [])
        self.assertEqual(plugin_fetch.record_of(self.tmp, "online-one")[0]["size"], 12)


class Manifest(unittest.TestCase):
    def test_fetch_and_handoff_are_known_and_checked(self):
        self.assertEqual(plugins.check(FETCHING), [])
        self.assertFalse([i for i in plugin_tester.run(FETCHING) if i["severity"] == "error"])
        self.assertTrue(any("needs the permission fetch" in x for x in plugins.check({**FETCHING, "permissions": ["handoff:send"]})))
        self.assertTrue(any("needs a fetch list" in x for x in plugins.check({**FETCHING, "fetch": None} if False else
                                                                              {k: v for k, v in FETCHING.items() if k != "fetch"})))
        self.assertTrue(plugins.check({**FETCHING, "fetch": ["localhost"]}))
        c = FETCHING["containers"][0]
        self.assertTrue(any("handoff:send" in x for x in plugins.check({**FETCHING, "permissions": ["fetch"]})))
        self.assertTrue(any("handoff:receive" in x for x in plugins.check(
            {**FETCHING, "containers": [{**c, "volumes": ["data", "handoff/tv-pack:receive"]}]})))
        self.assertTrue(plugins.check({**FETCHING, "containers": [{**c, "volumes": ["handoff/../x:send"]}]}))
        schema = json.load(open(os.path.join(os.path.dirname(plugins.__file__), "plugin-manifest.schema.json")))
        for p in ("fetch", "handoff:send", "handoff:receive"):
            self.assertIn(p, schema["properties"]["permissions"]["items"]["enum"])
        self.assertIn("fetch", schema["properties"])
        self.assertGreaterEqual(tuple(map(int, plugins.API_VERSION.split("."))), (1, 25, 0))

    def test_the_install_warning_names_the_sites_and_the_folder(self):
        w = plugins.install_warning(FETCHING)
        self.assertTrue(any("api.openverse.org, api.pexels.com" in x for x in w["reach"]))
        self.assertFalse(any("no way out" in x for x in w["reach"]))
        self.assertTrue(any("hand-off folder tv-pack" in x for x in w["change"]))
        recv = plugins.install_warning({**FETCHING, "containers": [{**FETCHING["containers"][0], "volumes": ["data", "handoff/tv-pack:receive"]}]})
        self.assertTrue(any("hand-off folder tv-pack" in x for x in recv["see"]))

    def test_the_compose_file_shares_one_folder_for_both(self):
        for way in ("send", "receive"):
            m = {**FETCHING, "permissions": [*FETCHING["permissions"], f"handoff:{way}"],
                 "containers": [{**FETCHING["containers"][0], "volumes": ["data", f"handoff/tv-pack:{way}"]}]}
            text = plugins.compose(m, "/srv/sb/data/plugins/online-one", "/srv/media")
            self.assertIn('"/srv/sb/data/handoff/tv-pack:/handoff/tv-pack"', text)

    def test_the_folder_is_made_for_the_kinds_it_names(self):
        d = tempfile.mkdtemp()
        try:
            pa.ensure_handoff(d, FETCHING)
            self.assertTrue(os.path.isdir(os.path.join(d, "handoff", "tv-pack")))
            self.assertEqual(os.stat(os.path.join(d, "handoff", "tv-pack")).st_mode & 0o777, 0o777)
            self.assertEqual(pa.handoff_kinds(PLAIN), [])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_capabilities_are_named(self):
        from starboard import plugin_capabilities as c
        self.assertIn("fetch", c.names())
        self.assertIn("handoff", c.names())


if __name__ == "__main__":
    unittest.main()
