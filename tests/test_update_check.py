"""Check for updates and What is new (DASH-462): every part asked at once, one that fails never hiding the others;
Jellyfin's plug-ins compared with Jellyfin's packages; every waiting update's notes combined by item under Added,
Changed, Fixed and Security, from the version installed to the new one; a plain note and the release page where
there are none; Install all updates counting what Jellyfin has; and the two routes, signed in only."""
import http.client
import json
import os
import tempfile
import threading
import time
import unittest
from unittest import mock

from starboard import auth, changes, releases, update_batch, update_check, update_runs
from tests.jellyfin_stand_in import KEY, StandIn


class Config:
    def __init__(self, data):
        self.data = data


class App:
    def __init__(self, data_dir, services=None, repo="TheMightyTRex/starboard"):
        self.data_dir = data_dir
        self.config = Config({"services": services or [], "update_check": True})
        self.repo = repo
        self.version = "0.20.0"
        self._latest = {"checked": time.time(), "tag": "v0.20.0"}
        self._latest_lock = threading.Lock()
        self.asked = 0

    def latest_release(self):
        if time.time() - self._latest["checked"] < 6 * 3600:
            return self._latest["tag"]
        self.asked += 1
        self._latest.update(checked=time.time(), tag="v0.21.0")
        return self._latest["tag"]


def waiting(tid, kind, name, current, latest):
    return {"id": tid, "kind": kind, "name": name, "current": current, "latest": latest, "update_available": True,
            "can_update": True, "why": "", "can_roll_back": False, "roll_back_to": "", "note": ""}


def stand_in_call(jf):
    def call(method, path):
        status, answer = jf.handle(method, path, headers={"Authorization": f'MediaBrowser Token="{KEY}"'})
        if status >= 400:
            raise OSError(f"Jellyfin answered {status}")
        return answer
    return call


class JellyfinWaiting(unittest.TestCase):
    def test_finds_newer_versions_with_their_notes(self):
        jf = StandIn(plugins=[{"Name": "Playback Reporting", "Version": "19.0.0.0", "Id": "5c53438191a343cb907a35aa02eb9d2c", "Status": "Active"},
                              {"Name": "Trakt", "Version": "31.0.0.0", "Id": "4fe3201ed6ae4f2e8917e12bda571281", "Status": "Active"}])
        jf.updates["5c53438191a343cb907a35aa02eb9d2c"] = "20.0.0.0"
        found = update_check.jellyfin_waiting_now({}, stand_in_call(jf))
        self.assertEqual([(j["name"], j["current"], j["latest"]) for j in found], [("Playback Reporting", "19.0.0.0", "20.0.0.0")])
        self.assertIn("Fixed a crash", found[0]["versions"][0]["changelog"])

    def test_nothing_newer(self):
        jf = StandIn(plugins=[{"Name": "Trakt", "Version": "31.0.0.0", "Id": "4fe3201ed6ae4f2e8917e12bda571281", "Status": "Active"}])
        self.assertEqual(update_check.jellyfin_waiting_now({}, stand_in_call(jf)), [])


class Check(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        update_check._jellyfin.update(at=0, waiting=[])

    def test_every_part_answers_and_one_failing_hides_nothing(self):
        app = App(self.tmp.name, services=[{"id": "jf", "type": "jellyfin", "url": "http://jf", "api_key": "k"}])
        with mock.patch.object(update_check, "_check_apps", side_effect=OSError("Docker is busy")), \
             mock.patch.object(update_check, "_check_plugins", return_value={"id": "plugins", "name": "Starboard's plug-ins", "ok": True, "said": "Read 1 catalogue"}), \
             mock.patch("starboard.auto_updates._jf", return_value={"url": "http://jf", "api_key": "k"}), \
             mock.patch("starboard.auto_updates._jf_call", side_effect=lambda jf, m, p: {"/Plugins": [{"Id": "a", "Name": "Trakt", "Version": "1.0.0.0"}],
                                                                                       "/Packages": [{"guid": "a", "name": "Trakt", "versions": [{"version": "1.1.0.0", "changelog": "- Faster"}]}]}[p]):
            got = update_check.check(app)
        by = {p["id"]: p for p in got["parts"]}
        self.assertEqual(app.asked, 1, "Starboard asks GitHub now, not at the next 6-hourly look")
        self.assertTrue(by["starboard"]["ok"])
        self.assertIn("0.21.0", by["starboard"]["said"])
        self.assertFalse(by["apps"]["ok"])
        self.assertIn("Docker is busy", by["apps"]["said"])
        self.assertTrue(by["plugins"]["ok"])
        self.assertEqual(by["jellyfin-plugins"]["said"], "1 with a new version")
        self.assertEqual([j["name"] for j in update_check.jellyfin_waiting()], ["Trakt"])

    def test_starboard_not_asked_when_its_check_is_off(self):
        app = App(self.tmp.name)
        app.config.data["update_check"] = False
        got = update_check._check_starboard(app)
        self.assertFalse(got["ok"])
        self.assertEqual(app.asked, 0)

    def test_catalogues_read_again(self):
        from starboard import plugins_admin as pa
        app = App(self.tmp.name)
        pa._catalogues["https://example.invalid/c.json"] = {"at": time.time(), "name": "Old", "items": [], "error": ""}
        self.addCleanup(pa._catalogues.pop, "https://example.invalid/c.json", None)
        with mock.patch.object(pa, "sources", return_value=[{"url": "https://example.invalid/c.json", "own": False}]), \
             mock.patch.object(pa, "fetch_catalogue", return_value={"name": "New", "items": []}) as fetched:
            got = update_check._check_plugins(app)
        fetched.assert_called_once()
        self.assertTrue(got["ok"])

    def test_no_jellyfin_says_nothing(self):
        app = App(self.tmp.name)
        with mock.patch.object(update_check, "_check_apps", return_value={"id": "apps", "name": "Apps", "ok": True, "said": ""}), \
             mock.patch.object(update_check, "_check_plugins", return_value={"id": "plugins", "name": "P", "ok": True, "said": ""}):
            got = update_check.check(app)
        self.assertNotIn("jellyfin-plugins", [p["id"] for p in got["parts"]])


class WhatsNew(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        update_check._jellyfin.update(at=0, waiting=[])
        self.app = App(self.tmp.name)

    def run_with(self, targets):
        with mock.patch.object(update_runs, "targets", return_value=targets), mock.patch("starboard.containers.available", return_value=False):
            return update_check.whats_new(self.app)

    def test_starboard_from_releases_py_combined_by_type(self):
        known = [r["version"] for r in releases.RELEASES]
        old, new = known[-4], known[-1]
        got = self.run_with([waiting("starboard", "starboard", "Starboard", old, new)])
        item = got["items"][0]
        self.assertEqual(item["name"], "Starboard")
        self.assertEqual(item["versions"], [v for v in reversed(known) if releases._key(old) < releases._key(v) <= releases._key(new)])
        types = [s["type"] for s in item["sections"]]
        self.assertEqual(types, sorted(types, key=update_check.TYPES.index), "Added, Changed, Fixed, Security, in that order")
        self.assertEqual(item["link"], f"https://github.com/TheMightyTRex/starboard/releases/tag/v{new}")
        self.assertTrue(all(x["version"] for s in item["sections"] for x in s["items"]))
        self.assertEqual(item["none"], "")

    def test_starboard_newer_than_this_copy_reads_the_tags_changelog(self):
        newest = releases.RELEASES[-1]["version"]
        major, minor, _ = (int(x) for x in newest.split("."))
        nxt = f"{major}.{minor + 1}.0"
        text = f"# Changelog\n\n## [{nxt}] (18 November 2026)\n\n### Added\n- **New thing:** It works.\n\n### Security\n- **Checks:** Clean.\n"
        with mock.patch.object(changes, "_fetch", return_value=changes.parse(text)) as fetched:
            got = self.run_with([waiting("starboard", "starboard", "Starboard", newest, nxt)])
        fetched.assert_called_once_with(f"https://raw.githubusercontent.com/TheMightyTRex/starboard/v{nxt}/CHANGELOG.md")
        item = got["items"][0]
        self.assertEqual([s["type"] for s in item["sections"]], ["Added", "Security"])
        self.assertEqual(item["sections"][0]["items"][0]["parts"][0], ["strong", "New thing:"])

    def test_starboard_notes_that_cannot_be_read_say_so(self):
        newest = releases.RELEASES[-1]["version"]
        with mock.patch.object(changes, "_fetch", side_effect=OSError("offline")):
            got = self.run_with([waiting("starboard", "starboard", "Starboard", newest, "99.0.0")])
        self.assertIn("could not read the notes for 99.0.0", got["items"][0]["problem"])
        self.assertTrue(got["items"][0]["link"])

    def test_plugin_from_its_new_manifest(self):
        manifest = {"version": "1.2.0", "homepage": "https://example.invalid/ps",
                    "changes": [{"version": "1.2.0", "date": "2026-11-17", "added": ["**Shrink all** at once."], "fixed": ["A crash."]},
                                {"version": "1.1.0", "date": "2026-11-10", "fixed": ["Odd shapes."]},
                                {"version": "1.0.0", "date": "2026-11-01", "added": ["First."]}]}
        with mock.patch("starboard.plugin_life.updates_known", return_value={"ps": {"version": "1.2.0", "changelog": "", "manifest": "https://x/m.json", "sha256": ""}}), \
             mock.patch.object(update_batch, "_manifest", return_value=manifest):
            got = self.run_with([waiting("plugin:ps", "plugin", "Picture shrinker", "1.0.0", "1.2.0")])
        item = got["items"][0]
        self.assertEqual(item["versions"], ["1.2.0", "1.1.0"], "from the installed version (not included) to the new one")
        fixed = next(s for s in item["sections"] if s["type"] == "Fixed")
        self.assertEqual([x["version"] for x in fixed["items"]], ["1.2.0", "1.1.0"], "newest first")
        self.assertEqual(item["link"], "https://example.invalid/ps")

    def test_an_app_without_notes_says_so_with_its_release_page(self):
        with mock.patch("starboard.containers.apps", return_value={"items": [{"id": "sonarr", "container": {"image": "lscr.io/linuxserver/sonarr:latest"}}]}):
            with mock.patch.object(update_runs, "targets", return_value=[waiting("app:sonarr", "app", "Sonarr", "4.0.11", "4.0.12")]), \
                 mock.patch("starboard.containers.available", return_value=True):
                got = update_check.whats_new(self.app)
        item = got["items"][0]
        self.assertEqual(item["sections"], [])
        self.assertEqual(item["link"], "https://github.com/linuxserver/docker-sonarr/releases")
        self.assertIn("Starboard has no notes for Sonarr", item["none"])

    def test_one_that_fails_does_not_hide_the_others(self):
        with mock.patch.object(update_check, "_plugin", side_effect=ValueError("bad manifest")):
            got = self.run_with([waiting("plugin:x", "plugin", "X", "1.0.0", "1.1.0"), waiting("app:radarr", "app", "Radarr", "5.0.0", "5.1.0")])
        by = {i["name"]: i for i in got["items"]}
        self.assertIn("bad manifest", by["X"]["problem"])
        self.assertIn("does not know where", by["Radarr"]["none"])

    def test_jellyfin_plugins_found_by_the_check(self):
        update_check._jellyfin.update(at=time.time(), waiting=[{"id": "a", "name": "Trakt", "current": "1.0.0.0", "latest": "1.1.0.0",
                                                                "versions": [{"version": "1.1.0.0", "changelog": "# Notes\n- Faster\n* Smaller"}]}])
        got = self.run_with([])
        item = got["items"][0]
        self.assertEqual(item["kind"], "jellyfin-plugin")
        self.assertEqual([x["parts"] for x in item["sections"][0]["items"]], [[["text", "Faster"]], [["text", "Smaller"]]])

    def test_order_starboard_reelix_plugins_jellyfin_apps(self):
        with mock.patch.object(update_check, "_starboard", return_value={"versions": []}), \
             mock.patch.object(update_check, "_reelix", return_value={"versions": []}), \
             mock.patch.object(update_check, "_plugin", return_value={"versions": []}):
            got = self.run_with([waiting("app:sonarr", "app", "Sonarr", "1", "2"), waiting("plugin:p", "plugin", "P", "1", "2"),
                                 waiting("reelix", "reelix", "Reelix", "1", "2"), waiting("starboard", "starboard", "Starboard", "1", "2"),
                                 waiting("app:starboard", "app", "Starboard", "1", "2")])
        self.assertEqual([i["kind"] for i in got["items"]], ["starboard", "reelix", "plugin", "app"])


class ReleasePage(unittest.TestCase):
    def test_pages(self):
        self.assertEqual(update_check.release_page("lscr.io/linuxserver/radarr:latest"), "https://github.com/linuxserver/docker-radarr/releases")
        self.assertEqual(update_check.release_page("linuxserver/bazarr"), "https://github.com/linuxserver/docker-bazarr/releases")
        self.assertEqual(update_check.release_page("ghcr.io/advplyr/audiobookshelf:latest"), "https://github.com/advplyr/audiobookshelf/releases")
        self.assertEqual(update_check.release_page("jellyfin/jellyfin:10.11"), "https://hub.docker.com/r/jellyfin/jellyfin")
        self.assertEqual(update_check.release_page("nginx@sha256:abc"), "https://hub.docker.com/_/nginx")
        self.assertEqual(update_check.release_page("registry.example.org/a/b:1"), "")


class InstallAllCountsJellyfin(unittest.TestCase):
    def test_found_jellyfin_updates_are_named_and_counted(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = App(tmp.name, services=[{"id": "jf", "type": "jellyfin"}])
        update_check._jellyfin.update(at=time.time(), waiting=[{"id": "a", "name": "Trakt", "current": "1", "latest": "2", "versions": []}])
        self.addCleanup(update_check._jellyfin.update, at=0, waiting=[])
        with mock.patch.object(update_runs, "targets", return_value=[]), mock.patch("starboard.auto_updates._jf", return_value={"id": "jf"}):
            plan = update_batch.plan(app)
        self.assertEqual(plan["count"], 1, "one Jellyfin plug-in alone is enough for Install all updates")
        self.assertIn("Trakt 2", plan["items"][0]["note"])

    def test_forgotten_once_jellyfin_updates_its_plug_ins(self):
        from starboard import auto_updates
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = App(tmp.name, services=[{"id": "jf", "type": "jellyfin"}])
        update_check._jellyfin.update(at=time.time(), waiting=[{"id": "a", "name": "Trakt", "current": "1", "latest": "2", "versions": []}])
        update_runs._runs.clear()
        update_runs._loaded.discard(tmp.name)
        calls = {"/Plugins": [], "/ScheduledTasks": [{"Key": auto_updates.JF_TASK, "Id": "t1", "Triggers": []}]}
        with mock.patch.object(auto_updates, "_jf", return_value={"id": "jf"}), \
             mock.patch.object(auto_updates, "_jf_call", side_effect=lambda jf, m, p, body=None: calls[p]), \
             mock.patch.object(update_runs, "_starboard_running", return_value=False):
            run = auto_updates.jellyfin_plugins_begin(app, by="you", batch=True)[0]
        with update_runs._lock:
            update_runs._active.pop(run["id"], None)
        self.assertEqual(update_check.jellyfin_waiting(), [])

    def test_old_words_when_nothing_was_found(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = App(tmp.name, services=[{"id": "jf", "type": "jellyfin"}])
        update_check._jellyfin.update(at=0, waiting=[])
        with mock.patch.object(update_runs, "targets", return_value=[]), mock.patch("starboard.auto_updates._jf", return_value={"id": "jf"}):
            plan = update_batch.plan(app)
        self.assertEqual(plan["count"], 0)
        self.assertEqual(plan["items"][0]["note"], "Jellyfin installs any new versions it has")


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
        cls.cookie = None

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def request(self, method, path, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Content-Type": "application/json"}
        if method != "GET":
            h["X-Starboard"] = "1"
        if cookie and self.cookie:
            h["Cookie"] = self.cookie
        conn.request(method, path, "{}" if method != "GET" else None, h)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        try:
            return r, json.loads(raw)
        except ValueError:
            return r, raw

    def sign_in(self):
        if Routes.cookie:
            return
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("POST", "/api/setup", json.dumps({"token": self.app.setup_token, "password": "correct horse battery"}),
                     {"Content-Type": "application/json", "X-Starboard": "1"})
        r = conn.getresponse()
        r.read()
        conn.close()
        self.assertEqual(r.status, 200)
        Routes.cookie = r.getheader("Set-Cookie").split(";")[0]

    def test_signed_out_is_refused(self):
        r, _ = self.request("POST", "/api/updates/check", cookie=False)
        self.assertIn(r.status, (401, 403))

    def test_check_and_whats_new(self):
        self.sign_in()
        with mock.patch.object(update_check, "check", return_value={"checked_at": 1, "parts": []}) as checked:
            r, body = self.request("POST", "/api/updates/check")
        self.assertEqual(r.status, 200, body)
        checked.assert_called_once()
        with mock.patch.object(update_check, "whats_new", return_value={"items": [], "count": 0}):
            r, body = self.request("GET", "/api/updates/whats-new")
        self.assertEqual((r.status, body["count"]), (200, 0))
        r, _ = self.request("GET", "/api/updates/check")
        self.assertEqual(r.status, 405)
        r, body = self.request("GET", "/api/updates")
        self.assertEqual(r.status, 200)
        self.assertIn("jellyfin_waiting", body)


if __name__ == "__main__":
    unittest.main()
