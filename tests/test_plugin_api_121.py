"""Plug-in API 1.21 (27 November 2026, DASH-589): needs_plugins, the plug-ins a plug-in needs, and switch, the setting that turns a
plug-in on and off. Switching off or turning off a plug-in that others need asks first, naming them, and turns them off too."""
import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, plugins, plugins_admin as pa
from starboard.server import make_server
from tests.test_plugin_api_117 import QUIET

PROVIDER = {**QUIET, "id": "sign-in-provider", "name": "Sign-in provider", "version": "1.0.0", "switch": "enabled",
            "settings": [{"key": "enabled", "label": "Use it", "type": "switch", "default": False}]}
APP_A = {**QUIET, "id": "needs-provider-a", "name": "Provider app A", "needs_plugins": ["sign-in-provider"]}
APP_B = {**QUIET, "id": "needs-provider-b", "name": "Provider app B", "needs_plugins": ["sign-in-provider"]}
FREE = {**QUIET, "id": "free-one", "name": "Free one"}


class Manifest(unittest.TestCase):
    def test_the_new_fields_are_known_and_checked(self):
        self.assertGreaterEqual(tuple(map(int, plugins.API_VERSION.split("."))), (1, 21, 0))
        self.assertEqual(plugins.check(PROVIDER), [])
        self.assertEqual(plugins.check(APP_A), [])
        with open(os.path.join(os.path.dirname(plugins.__file__), "plugin-manifest.schema.json"), encoding="utf-8") as f:
            props = json.load(f)["properties"]
        self.assertIn("needs_plugins", props)
        self.assertIn("switch", props)

    def test_bad_values_are_said_in_words(self):
        for bad in ("sign-in-provider", ["Bad Id"], [1], ["a-b"] * 11, ["needs-provider-a"]):
            self.assertTrue(any("needs_plugins" in p for p in plugins.check({**APP_A, "needs_plugins": bad})), bad)
        self.assertTrue(any("switch must be" in p for p in plugins.check({**PROVIDER, "switch": "nothing"})))
        self.assertTrue(any("switch must be" in p for p in plugins.check({**PROVIDER, "switch": "x", "settings": [{"key": "x", "label": "X", "type": "text"}]})))

    def test_an_older_manifest_without_them_is_unchanged(self):
        self.assertEqual(plugins.check(QUIET), [])


class Asking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sbdep")
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.patches = [mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}"),
                       mock.patch.object(pa, "_compose_run", return_value=(True, ""))]
        for p in cls.patches:
            p.start()
        for m in (PROVIDER, APP_A, APP_B, FREE):
            pa.install(cls.tmp, m, "/srv/media")
        _, _, headers = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"})
        cls.cookie = [v.split(";")[0] for k, v in headers if k.lower() == "set-cookie" and v.startswith("starboard_session=")][0]

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def call(cls, method, path, body=None, cookie=None):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=15)
        h = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie:
            h["Cookie"] = cookie
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        out = (r.status, json.loads(raw or b"{}"), r.getheaders())
        conn.close()
        return out

    def api(self, method, path, body=None):
        return self.call(method, path, body, self.cookie)[:2]

    def states(self):
        return {p["id"]: p["state"] for p in pa.basics(self.tmp)}

    def setUp(self):
        for m in (PROVIDER, APP_A, APP_B, FREE):
            pa.set_state(self.tmp, m["id"], "enabled")
        pa.save_settings(self.tmp, "sign-in-provider", {"enabled": True})

    def test_the_dependents_are_the_enabled_plug_ins_that_need_it(self):
        self.assertEqual([d["id"] for d in pa.dependents(self.tmp, "sign-in-provider")], ["needs-provider-a", "needs-provider-b"])
        pa.set_state(self.tmp, "needs-provider-b", "disabled")
        self.assertEqual([d["id"] for d in pa.dependents(self.tmp, "sign-in-provider")], ["needs-provider-a"])
        self.assertEqual(pa.dependents(self.tmp, "free-one"), [])

    def test_deactivating_asks_first_in_plain_words_and_changes_nothing(self):
        status, out = self.api("POST", "/api/plugins/sign-in-provider/disable", {})
        self.assertEqual(status, 409)
        self.assertEqual(out["error"], "Provider app A and Provider app B need Sign-in provider. If you turn it off, they will be "
                                       "turned off too, and nothing is deleted. Continue?")
        self.assertEqual([d["id"] for d in out["dependents"]], ["needs-provider-a", "needs-provider-b"])
        self.assertEqual(set(self.states().values()), {"enabled"})

    def test_saying_yes_deactivates_it_and_the_plug_ins_that_need_it(self):
        status, _ = self.api("POST", "/api/plugins/sign-in-provider/disable", {"confirm_dependents": True})
        self.assertEqual(status, 200)
        self.assertEqual(self.states(), {"sign-in-provider": "disabled", "needs-provider-a": "disabled", "needs-provider-b": "disabled", "free-one": "enabled"})

    def test_a_plug_in_nothing_needs_deactivates_at_once(self):
        self.assertEqual(self.api("POST", "/api/plugins/free-one/disable", {})[0], 200)
        self.assertEqual(self.api("POST", "/api/plugins/needs-provider-a/disable", {})[0], 200)  # needing one is not being needed
        self.assertEqual(self.states()["sign-in-provider"], "enabled")

    def test_switching_the_switch_off_asks_the_same_and_yes_deactivates_them(self):
        status, out = self.api("PUT", "/api/plugins/sign-in-provider/settings", {"settings": {"enabled": False}})
        self.assertEqual(status, 409)
        self.assertIn("If you switch it off, they will be turned off too", out["error"])
        self.assertTrue(pa._read(os.path.join(pa.folder(self.tmp, "sign-in-provider"), "settings.json"))["enabled"])  # nothing saved
        status, out = self.api("PUT", "/api/plugins/sign-in-provider/settings", {"settings": {"enabled": False}, "confirm_dependents": True})
        self.assertEqual(status, 200)
        self.assertEqual([d["id"] for d in out["deactivated"]], ["needs-provider-a", "needs-provider-b"])
        self.assertFalse(pa._read(os.path.join(pa.folder(self.tmp, "sign-in-provider"), "settings.json"))["enabled"])
        self.assertEqual(self.states(), {"sign-in-provider": "enabled", "needs-provider-a": "disabled", "needs-provider-b": "disabled", "free-one": "enabled"})

    def test_switching_on_or_saving_something_else_never_asks(self):
        self.assertEqual(self.api("PUT", "/api/plugins/sign-in-provider/settings", {"settings": {"enabled": True}})[0], 200)
        pa.save_settings(self.tmp, "sign-in-provider", {"enabled": False})
        self.assertEqual(self.api("PUT", "/api/plugins/sign-in-provider/settings", {"settings": {"enabled": True}})[0], 200)
        self.assertEqual(self.api("PUT", "/api/plugins/free-one/settings", {"settings": {}})[0], 200)

    def test_one_dependent_is_worded_in_the_singular(self):
        pa.set_state(self.tmp, "needs-provider-b", "disabled")
        words = pa.dependents_words("Sign-in provider", pa.dependents(self.tmp, "sign-in-provider"), "turn it off")
        self.assertEqual(words, "Provider app A needs Sign-in provider. If you turn it off, it will be turned off too, and nothing is deleted. Continue?")

    def test_the_switch_that_was_never_set_counts_as_its_default(self):
        pa.save_settings(self.tmp, "sign-in-provider", {"enabled": False})
        pa._write(os.path.join(pa.folder(self.tmp, "sign-in-provider"), "settings.json"), {})  # never saved: default off
        self.assertFalse(pa.switching_off(self.tmp, "sign-in-provider", {"enabled": False}))


if __name__ == "__main__":
    unittest.main()
