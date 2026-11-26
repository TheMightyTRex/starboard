"""Jellyfin as the built-in media server plug-in record (DASH-565, PR C): added by default, nothing runs, nothing in
the person's settings changes, and the one in use cannot be switched off by accident."""
import http.client
import json
import os
import tempfile
import threading
import unittest

from starboard import auth, mediaserver, plugins, plugins_admin as pa

JF = {"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "made-up-key-7731", "enabled": True}


class Record(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name

    def state(self):
        return next((p for p in pa.basics(self.d) if p["id"] == "jellyfin"), None)

    def test_the_shipped_manifest_passes_the_checks_as_a_built_in_only(self):
        m = pa.builtins()["jellyfin"]
        self.assertEqual(plugins.check(m, builtin=True), [])
        self.assertIn("Only a plug-in that comes with Starboard can be the media server for now", plugins.check(m))
        self.assertTrue(pa.is_media_server(m))
        self.assertFalse(pa.is_media_server(pa.builtins()["livetv"]))
        self.assertNotIn("containers", m)  # nothing runs: it uses no memory of its own

    def test_a_new_install_adds_it_not_active(self):
        self.assertTrue(pa.ensure_default(self.d, []))
        self.assertEqual((self.state()["state"], self.state()["builtin"]), ("installed", True))
        self.assertFalse(os.path.exists(os.path.join(self.d, "plugins", "jellyfin", "compose.yaml")))
        self.assertFalse(os.path.exists(os.path.join(self.d, "plugins", "jellyfin", "key")))

    def test_an_install_with_jellyfin_has_it_active(self):
        self.assertTrue(pa.ensure_default(self.d, [JF]))
        self.assertEqual(self.state()["state"], "enabled")
        listed = next(p for p in pa.listing(self.d) if p["id"] == "jellyfin")
        self.assertTrue(listed["media_server"])
        self.assertEqual(listed["status"]["state"], "enabled")

    def test_a_switched_off_jellyfin_entry_does_not_count(self):
        pa.ensure_default(self.d, [{**JF, "enabled": False}])
        self.assertEqual(self.state()["state"], "installed")

    def test_it_is_idempotent_and_never_changes_a_state(self):
        pa.ensure_default(self.d, [JF])
        pa.set_state(self.d, "jellyfin", "disabled")
        self.assertFalse(pa.ensure_default(self.d, [JF]))
        self.assertEqual(self.state()["state"], "disabled")

    def test_it_follows_starboards_copy_of_the_manifest(self):
        pa.ensure_default(self.d, [])
        path = os.path.join(self.d, "plugins", "jellyfin", "manifest.json")
        with open(path) as f:
            old = json.load(f)
        with open(path, "w") as f:
            json.dump({**old, "version": "0.9.0"}, f)
        pa.ensure_default(self.d, [])
        with open(path) as f:
            self.assertEqual(json.load(f)["version"], pa.builtins()["jellyfin"]["version"])

    def test_a_removed_one_is_not_added_again(self):
        pa.ensure_default(self.d, [])
        pa.uninstall(self.d, "jellyfin")
        self.assertIsNone(self.state())
        self.assertFalse(pa.ensure_default(self.d, [JF]))
        self.assertIsNone(self.state())

    def test_nothing_else_is_written_for_the_person(self):
        pa.ensure_default(self.d, [JF])
        self.assertEqual(sorted(os.listdir(os.path.join(self.d, "plugins"))), ["jellyfin"])
        self.assertFalse(os.path.exists(os.path.join(self.d, "settings.json")))

    def test_a_start_with_built_in_files_keeps_the_record_quiet(self):
        pa.ensure_default(self.d, [JF])
        path = os.path.join(self.d, "plugins", "jellyfin", "state.json")
        with open(path) as f:
            before = f.read()
        self.assertEqual(pa.refresh_builtins(self.d, "/nonexistent", [JF]), [])
        with open(path) as f:
            self.assertEqual(f.read(), before)

    def test_stop_all_keeps_the_one_named(self):
        pa.ensure_default(self.d, [JF])
        self.assertEqual(pa.stop_all(self.d, keep={"jellyfin"}), [])
        self.assertEqual(self.state()["state"], "enabled")
        self.assertEqual(pa.stop_all(self.d), ["Jellyfin"])

    def test_in_use_follows_the_slot(self):
        self.assertTrue(mediaserver.in_use({}, "jellyfin"))
        self.assertFalse(mediaserver.in_use({"extras": {"media_server": ""}}, "jellyfin"))
        self.assertFalse(mediaserver.in_use({}, "plex"))
        self.assertFalse(mediaserver.in_use({}, ""))


class Light(unittest.TestCase):
    def test_the_once_wrapper_asks_once_for_each_folder(self):
        self.assertTrue(pa.ensure_default_once("/nonexistent/a", []) is False)  # a folder it cannot write to is quiet
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(pa.ensure_default_once(d, []))
            self.assertFalse(pa.ensure_default_once(d, []))
            self.assertTrue(os.path.isdir(os.path.join(d, "plugins", "jellyfin")))

    def test_starting_loads_nothing_for_the_plug_in_record(self):
        """Starboard stays lightweight: a start that nobody has opened loads nothing extra loads and no record is added."""
        import subprocess
        import sys
        code = ("import sys, tempfile, os\nfrom starboard.server import make_server\n"
                "d = tempfile.mkdtemp()\nmake_server('127.0.0.1', 0, d)\n"
                "print('starboard.plugin_styles' in sys.modules, os.path.exists(os.path.join(d, 'plugins')))")
        env = {**os.environ, "STARBOARD_HISTORY": "0", "STARBOARD_SCHEDULE": "0", "STARBOARD_WATCH": "0", "STARBOARD_JOBS": "0", "STARBOARD_DOCKER": "/nonexistent/docker.sock"}
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), timeout=60)
        self.assertEqual(out.stdout.strip().splitlines()[-1], "False False", out.stderr[-300:])


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from starboard.server import make_server
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.password = "correct horse battery"
        r, _ = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": cls.password}, cookie=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def call(cls, method, path, body=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        headers = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            headers["Cookie"] = cls.cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r, json.loads(raw) if raw[:1] in (b"{", b"[") else raw

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def setUp(self):
        self.app.config.data["extras"].pop("media_server", None)

    def test_the_session_adds_the_record_for_a_signed_in_person_only(self):
        d = os.path.join(self.app.data_dir, "plugins", "jellyfin")
        r, _ = self.call("GET", "/api/session", cookie=False)
        self.assertEqual(r.status, 200)
        r, got = self.call("GET", "/api/session")
        self.assertEqual(r.status, 200)
        self.assertTrue(os.path.isdir(d))
        self.assertIn("jellyfin", [p["id"] if isinstance(p, dict) else p for p in got["plugins"]])

    def test_the_list_has_it_with_the_slot_beside_it(self):
        r, got = self.call("GET", "/api/plugins")
        self.assertEqual(r.status, 200)
        one = next(p for p in got["plugins"] if p["id"] == "jellyfin")
        self.assertEqual((one["builtin"], one["media_server"]), (True, True))
        self.assertEqual((got["media_server"]["active"], got["media_server"]["name"]), ("jellyfin", "Jellyfin"))
        built = next(b for b in got["builtin"] if b["id"] == "jellyfin")
        self.assertTrue(built["added"] and built["media_server"])
        self.assertFalse(next(b for b in got["builtin"] if b["id"] == "livetv")["media_server"])

    def test_the_one_in_use_cannot_be_deactivated_or_removed(self):
        self.call("GET", "/api/plugins")
        pa.set_state(self.app.data_dir, "jellyfin", "enabled")
        for what, body in (("disable", {}), ("remove", {"password": self.password})):
            r, got = self.call("POST", f"/api/plugins/jellyfin/{what}", body)
            self.assertEqual(r.status, 409, what)
            self.assertIn("Jellyfin is your media server, so it stays on", got["error"])
        self.assertEqual(next(p for p in pa.basics(self.app.data_dir) if p["id"] == "jellyfin")["state"], "enabled")

    def test_stop_all_leaves_it_on(self):
        self.call("GET", "/api/plugins")
        pa.set_state(self.app.data_dir, "jellyfin", "enabled")
        r, got = self.call("POST", "/api/plugins/stop-all", {})
        self.assertEqual((r.status, got["stopped"]), (200, []))

    def test_with_no_media_server_it_may_be_deactivated(self):
        self.call("GET", "/api/plugins")
        pa.set_state(self.app.data_dir, "jellyfin", "enabled")
        self.app.config.data["extras"]["media_server"] = ""
        r, _ = self.call("POST", "/api/plugins/jellyfin/disable", {})
        self.assertEqual(r.status, 200)
        r, _ = self.call("POST", "/api/plugins/jellyfin/enable", {})
        self.assertEqual(r.status, 200)


if __name__ == "__main__":
    unittest.main()
