"""Plug-in API 1.20 (26 November 2026, DASH-590): a sign-in Starboard made for an app plug-in, such as Calibre-Web's
admin, shown once on its page instead of the default everybody knows."""
import json
import os
import tempfile
import unittest

from starboard import plugin_first_sign_in as fsi, plugins, plugins_admin as pa
from tests.test_app_plugins import app_manifest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = {"user": "admin", "secret": "db_password", "ready_file": "app/starboard-first-sign-in.done"}


def manifest(**more):
    return app_manifest(first_sign_in=SPEC, **more)


class Check(unittest.TestCase):
    def test_a_good_one_passes_and_it_is_additive(self):
        self.assertEqual(plugins.check(manifest()), [])
        self.assertEqual(plugins.check(app_manifest()), [])

    def test_each_mistake_is_named(self):
        for spec in ({**SPEC, "extra": 1}, {"user": "admin", "secret": "db_password"}, "admin", {**SPEC, "user": ""},
                     {**SPEC, "secret": "not_used"}, {**SPEC, "ready_file": "app/../x"}, {**SPEC, "ready_file": "nope/file"},
                     {**SPEC, "ready_file": "/etc/passwd"}, {**SPEC, "ready_file": "app"}):
            self.assertTrue([p for p in plugins.check(app_manifest(first_sign_in=spec)) if "first_sign_in" in p], spec)

    def test_the_version_and_schema(self):
        self.assertEqual(plugins.API_VERSION, "1.20.0")
        with open(os.path.join(ROOT, "starboard", "plugin-manifest.schema.json")) as f:
            schema = json.load(f)
        self.assertIn("first_sign_in", schema["properties"])
        self.assertEqual(sorted(schema["properties"]["first_sign_in"]["required"]), ["ready_file", "secret", "user"])
        with open(os.path.join(ROOT, "docs", "help", "developers", "plugin-manifest-reference.md")) as f:
            self.assertIn("`first_sign_in`", f.read())


class Shown(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        pa.install(self.d, manifest(), "/srv/media")
        self.where = pa.folder(self.d, "stats-app")
        self.m = manifest()
        pa.secrets_for(self.d, "stats-app", self.m)

    def tearDown(self):
        self.tmp.cleanup()

    def ready(self):
        os.makedirs(os.path.join(self.where, "data", "app"), exist_ok=True)
        with open(os.path.join(self.where, "data", "app", "starboard-first-sign-in.done"), "w") as f:
            f.write("done\n")

    def password(self):
        with open(os.path.join(self.where, "secrets.json")) as f:
            return json.load(f)["db_password"]

    def test_nothing_is_offered_until_the_app_has_set_it(self):
        self.assertEqual(fsi.info(self.d, "stats-app", self.m), {"user": "admin", "state": "waiting", "shown_at": None})
        with self.assertRaises(LookupError):
            fsi.reveal(self.d, "stats-app")
        self.assertEqual(json.load(open(os.path.join(self.where, "state.json"))).get("first_sign_in_shown"), None)

    def test_it_is_shown_once_and_only_the_date_is_kept(self):
        self.ready()
        self.assertEqual(fsi.info(self.d, "stats-app", self.m)["state"], "ready")
        got = fsi.reveal(self.d, "stats-app")
        self.assertEqual(got, {"user": "admin", "password": self.password()})
        again = fsi.info(self.d, "stats-app", self.m)
        self.assertEqual(again["state"], "shown")
        self.assertTrue(again["shown_at"].endswith("Z"))
        with self.assertRaises(LookupError):
            fsi.reveal(self.d, "stats-app")
        self.assertNotIn(self.password(), json.dumps(again))

    def test_the_listing_never_holds_the_password(self):
        self.ready()
        row = next(p for p in pa.listing(self.d) if p["id"] == "stats-app")
        self.assertEqual(row["first_sign_in"]["state"], "ready")
        self.assertNotIn(self.password(), json.dumps(pa.listing(self.d)))
        fsi.reveal(self.d, "stats-app")
        self.assertNotIn(self.password(), json.dumps(pa.listing(self.d)))

    def test_a_plug_in_without_one_has_none(self):
        self.assertIsNone(fsi.info(self.d, "stats-app", app_manifest()))
        with self.assertRaises(LookupError):
            fsi.reveal(self.d, "stats-app")  # its manifest holds no first_sign_in


class Page(unittest.TestCase):
    def test_the_page_script_draws_it_and_asks_for_the_password(self):
        with open(os.path.join(ROOT, "web", "js", "plugins.js")) as f:
            js = f.read()
        self.assertIn("firstSignInSection(p)", js)
        self.assertIn("/first-sign-in", js)
        self.assertIn('autocomplete: "current-password"', js[js.index("function firstSignInSection"):])

    def test_the_route_needs_the_starboard_password_and_logs_no_password(self):
        with open(os.path.join(ROOT, "starboard", "server.py")) as f:
            src = f.read()
        block = src[src.index("first-sign-in$"):src.index("first-sign-in$") + 900]
        self.assertIn("self.check_password(self.body())", block)
        self.assertIn("never the password", block)


if __name__ == "__main__":
    unittest.main()
