"""Recommended Jellyfin plug-ins (DASH-404), against a stand-in Jellyfin (tests/jellyfin_stand_in.py)."""
import json
import os
import tempfile
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import jellyfin_plugins as jp
from tests.jellyfin_stand_in import KEY, StandIn

NEW = "https://raw.githubusercontent.com/TheMightyTRex/jellyfin-plugins/main/manifest.json"
OLD = "https://raw.githubusercontent.com/TheMightyTRex/jellyfin-plugin-picture-shrinker/main/manifest.json"


def serve(stand_in):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _do(self, method):
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n)) if n else None
            code, answer = stand_in.handle(method, self.path, body, dict(self.headers))
            raw = json.dumps(answer).encode() if answer is not None else b""
            self.send_response(code)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            self._do("GET")

        def do_POST(self):
            self._do("POST")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class JellyfinPluginsTest(unittest.TestCase):
    def setUp(self):
        # Never GitHub in a test: the Picture shrinker's list is empty unless a test gives it one (released_list).
        jp._released.clear()
        self.addCleanup(jp._released.clear)
        original = jp._fetch_manifest
        jp._fetch_manifest = lambda url: []
        self.addCleanup(setattr, jp, "_fetch_manifest", original)

    def start(self, **kw):
        self.jf = StandIn(**kw)
        self.srv = serve(self.jf)
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.services = [{"type": "jellyfin", "name": "Jellyfin", "url": f"http://127.0.0.1:{self.srv.server_port}", "api_key": KEY}]
        self.dir = tempfile.mkdtemp()
        self.cfg = {"download_hours": {"enabled": True, "start": 2, "end": 7}}

    def status(self):
        return jp.status(self.services, self.dir, self.cfg)

    def group(self, st, gid):
        return next(g for g in st["groups"] if g["id"] == gid)

    def test_no_jellyfin(self):
        self.assertEqual(jp.status([], tempfile.mkdtemp())["connected"], False)
        with self.assertRaises(ValueError):
            jp.choose([], tempfile.mkdtemp(), "playback", "on")

    def test_nothing_installed_offers_each_group(self):
        self.start()
        st = self.status()
        self.assertTrue(st["connected"])
        self.assertEqual([g["id"] for g in st["groups"]], ["skip", "playback", "merge", "trakt", "pictures"])
        self.assertTrue(all(g["chosen"] == "none" and g["installed"] == [] for g in st["groups"]))
        downloaded = self.group(st, "skip")["choices"][0]
        self.assertEqual((downloaded["id"], downloaded["package"], downloaded["available"]), ("downloaded", "TheIntroDB", True))

    def released_list(self, abis):
        """The Picture shrinker repository's list, as GitHub would give it, without asking GitHub."""
        jp._released.clear()
        self.addCleanup(jp._released.clear)
        listed = [{"guid": jp.PACKAGES["pictures"]["guid"], "versions": [{"version": "1.1.0.0", "targetAbi": a} for a in abis]}]
        original = jp._fetch_manifest
        jp._fetch_manifest = lambda url: listed
        self.addCleanup(setattr, jp, "_fetch_manifest", original)

    def test_picture_shrinker_on_jellyfin_10_11(self):
        self.released_list(["10.11.0.0"])
        self.start(version="10.11.11")
        on = self.group(self.status(), "pictures")["choices"][0]
        self.assertTrue(on["available"])
        out = jp.choose(self.services, self.dir, "pictures", "on", self.cfg)
        self.assertIn("Installed Picture shrinker, from the TheMightyTRexUK repository Starboard added", out["done"][0])
        self.assertIn(NEW, [r["Url"] for r in self.jf.repos])
        self.assertNotIn(OLD, [r["Url"] for r in self.jf.repos])

    def test_old_picture_shrinker_address_is_replaced(self):
        """17 November 2026: the old Picture shrinker address becomes the one address, in its place in the list, with
        its Enabled setting; every other repository the person added stays as it is."""
        other = {"Name": "Someone else", "Url": "https://example.org/manifest.json", "Enabled": False}
        self.start(repos=[{"Name": "Jellyfin Stable", "Url": jp.OFFICIAL[1], "Enabled": True},
                          {"Name": "Picture shrinker", "Url": OLD, "Enabled": True}, other])
        st = self.status()
        self.assertEqual(self.jf.repos, [{"Name": "Jellyfin Stable", "Url": jp.OFFICIAL[1], "Enabled": True},
                                         {"Name": "TheMightyTRexUK", "Url": NEW, "Enabled": True}, other])
        self.assertIn("Replaced the old Picture shrinker repository address", st["finished"][0])
        calls = len(self.jf.calls)
        self.assertEqual(self.status()["finished"], [])  # once only
        self.assertNotIn(("POST", "/Repositories"), self.jf.calls[calls:])

    def test_old_address_removed_when_the_new_one_is_there(self):
        self.start(repos=[{"Name": "Picture shrinker", "Url": OLD + "/", "Enabled": True},
                          {"Name": "Mine", "Url": NEW, "Enabled": False}])
        self.status()
        self.assertEqual(self.jf.repos, [{"Name": "Mine", "Url": NEW, "Enabled": False}])

    def test_old_address_replaced_when_a_plug_in_is_chosen(self):
        self.start(repos=[{"Name": "Picture shrinker", "Url": OLD, "Enabled": True}])
        out = jp.choose(self.services, self.dir, "playback", "on", self.cfg)
        self.assertIn("Replaced the old Picture shrinker repository address", out["done"][0])
        self.assertEqual([r["Url"] for r in self.jf.repos], [NEW, jp.OFFICIAL[1]])

    def test_no_old_address_changes_no_repository(self):
        self.start()
        self.status()
        self.assertNotIn(("POST", "/Repositories"), self.jf.calls)

    def test_picture_shrinker_waits_for_its_first_release(self):
        """DASH-433: its repository is public with an empty list until the owner releases it, so it is not offered."""
        self.released_list([])
        self.start(version="10.11.11")
        on = self.group(self.status(), "pictures")["choices"][0]
        self.assertFalse(on["available"])
        self.assertIn("Not released yet", on["hint"])
        with self.assertRaises(ValueError):
            jp.choose(self.services, self.dir, "pictures", "on", self.cfg)
        self.assertNotIn(NEW, [r["Url"] for r in self.jf.repos])

    def test_release_check_is_kept_and_survives_a_failed_read(self):
        jp._released.clear()
        self.addCleanup(jp._released.clear)
        calls = []
        def fetch(url):
            calls.append(url)
            return [{"guid": jp.PACKAGES["pictures"]["guid"], "versions": [{"targetAbi": "10.11.0.0"}]}]
        self.assertTrue(jp.released("pictures", "10.11.6", fetch, now=1000))
        self.assertTrue(jp.released("pictures", "10.11.6", fetch, now=2000))
        self.assertEqual(len(calls), 1)  # read once in 6 hours
        def broken(url):
            raise urllib.error.URLError("offline")
        self.assertTrue(jp.released("pictures", "10.11.6", broken, now=1000 + jp.RELEASE_CHECK_SECONDS + 1))  # keeps what it read
        self.assertFalse(jp.released("pictures", "10.10.7", fetch, now=1000))
        self.assertTrue(jp.released("playback", "10.11.6"))  # no check for the others

    def test_picture_shrinker_on_jellyfin_12(self):
        """DASH-433: the Jellyfin 12 build (targetAbi 12.0.0.0) suits every Jellyfin 12, such as the 12.4 here."""
        self.released_list(["12.0.0.0", "10.11.0.0"])
        self.start()  # Jellyfin 12.4
        on = self.group(self.status(), "pictures")["choices"][0]
        self.assertTrue(on["available"])
        self.assertNotIn("not ready", on.get("hint", ""))
        out = jp.choose(self.services, self.dir, "pictures", "on", self.cfg)
        self.assertIn("Installed Picture shrinker", out["done"][0])

    def test_picture_shrinker_on_jellyfin_12_waits_for_a_12_build(self):
        """A list with only the 10.11 build is not a release for Jellyfin 12."""
        self.released_list(["10.11.0.0"])
        self.start()  # Jellyfin 12.4
        on = self.group(self.status(), "pictures")["choices"][0]
        self.assertFalse(on["available"])
        self.assertIn("Not released yet", on["hint"])
        with self.assertRaises(ValueError):
            jp.choose(self.services, self.dir, "pictures", "on", self.cfg)

    def test_picture_shrinker_not_offered_on_jellyfin_13(self):
        self.released_list(["12.0.0.0", "10.11.0.0"])
        self.start(version="13.0.0")
        on = self.group(self.status(), "pictures")["choices"][0]
        self.assertFalse(on["available"])
        self.assertEqual(on["hint"], "Needs Jellyfin 10.11 or 12.")
        with self.assertRaises(ValueError):
            jp.choose(self.services, self.dir, "pictures", "on", self.cfg)

    def test_picture_shrinker_release_lines(self):
        def fetch(url):
            return [{"guid": jp.PACKAGES["pictures"]["guid"], "versions": [{"targetAbi": "12.0.0.0"}, {"targetAbi": "10.11.0.0"}]}]
        for version, ok in (("10.11.0", True), ("10.11.11", True), ("12.0.0", True), ("12.4.0", True), ("10.10.7", False)):
            jp._released.clear()
            self.assertEqual(jp.released("pictures", version, fetch, now=1000), ok, version)
        def only12(url):
            return [{"guid": jp.PACKAGES["pictures"]["guid"], "versions": [{"targetAbi": "12.1.0.0"}]}]
        for version, ok in (("12.0.0", False), ("12.4.0", True), ("10.11.11", False)):
            jp._released.clear()
            self.assertEqual(jp.released("pictures", version, only12, now=1000), ok, version)
        self.assertTrue(jp.suits("pictures", "12.4.0"))
        self.assertTrue(jp.suits("pictures", "10.11.11"))
        self.assertFalse(jp.suits("pictures", "13.0.0"))
        self.assertFalse(jp.suits("pictures", "10.10.7"))

    def test_downloaded_times_by_version(self):
        self.assertEqual(jp.downloaded_choice("12.4.0"), "theintrodb")
        self.assertEqual(jp.downloaded_choice("10.11.6"), "skipmedb")
        self.assertIsNone(jp.downloaded_choice("10.10.7"))

    def test_install_adds_repository_then_restart_activates(self):
        self.start()
        out = jp.choose(self.services, self.dir, "skip", "downloaded", self.cfg)
        self.assertTrue(out["restart"])
        self.assertIn("Installed TheIntroDB", out["done"][0])
        self.assertIn("https://raw.githubusercontent.com/TheIntroDB/jellyfin-plugin/main/manifest.json", [r["Url"] for r in self.jf.repos])
        self.assertIn("https://repo.jellyfin.org/files/plugin/manifest.json", [r["Url"] for r in self.jf.repos], "the owner's repositories stay")
        st = self.status()
        self.assertTrue(st["restart"])
        skip = self.group(st, "skip")
        self.assertEqual(skip["chosen"], "downloaded")
        self.assertEqual((skip["installed"][0]["name"], skip["installed"][0]["version"]), ("TheIntroDB", "1.3.1.0"))
        jp.restart(self.services)
        st = self.status()
        self.assertFalse(st["restart"])
        self.assertEqual(self.group(st, "skip")["installed"][0]["status"], "Active")

    def test_install_twice_changes_nothing(self):
        self.start()
        jp.choose(self.services, self.dir, "playback", "on", self.cfg)
        again = jp.choose(self.services, self.dir, "playback", "on", self.cfg)
        self.assertEqual(again, {"done": ["Nothing to change"], "restart": False})
        self.assertEqual(sum(1 for p in self.jf.plugins if p["Name"] == "Playback Reporting"), 1)
        self.assertEqual(sum(1 for r in self.jf.repos if r["Url"] == jp.OFFICIAL[1]), 1)

    def test_intro_skipper_runs_only_in_quiet_hours(self):
        self.start()
        jp.choose(self.services, self.dir, "skip", "analysed", self.cfg)
        jp.restart(self.services)
        st = self.status()
        self.assertIn("Intro Skipper analyses in quiet hours only, one episode at a time", st["finished"])
        guid = jp.PACKAGES["introskipper"]["guid"].replace("-", "")
        self.assertEqual((self.jf.config[guid]["AutoDetectIntros"], self.jf.config[guid]["MaxParallelism"]), (False, 1))
        self.assertEqual(self.jf.config[guid]["ProcessPriority"], "BelowNormal", "other settings stay")
        task = next(t for t in self.jf.tasks if t["Key"] == "IntroSkipperDetectSegmentsTask")
        self.assertEqual(task["Triggers"], [{"Type": "DailyTrigger", "TimeOfDayTicks": 2 * jp.TICKS_PER_HOUR, "MaxRuntimeTicks": 5 * jp.TICKS_PER_HOUR}])
        # Once only: a change the owner makes in Jellyfin afterwards stays
        task["Triggers"] = [{"Type": "DailyTrigger", "TimeOfDayTicks": 0}]
        self.assertEqual(self.status()["finished"], [])
        self.assertEqual(task["Triggers"], [{"Type": "DailyTrigger", "TimeOfDayTicks": 0}])

    def test_reading_the_list_changes_nothing_the_owner_installed(self):
        # DASH-409, issue 147: Intro Skipper and Merge Versions added in Jellyfin itself, not through Starboard
        guid = jp.PACKAGES["introskipper"]["guid"].replace("-", "")
        merge = jp.PACKAGES["merge"]["guid"].replace("-", "")
        self.start(plugins=[{"Name": "Intro Skipper", "Version": "1.10.11.0", "Id": guid, "Status": "Active", "CanUninstall": True},
                            {"Name": "Merge Versions", "Version": "1.0.0.0", "Id": merge, "Status": "Active", "CanUninstall": True}])
        st = self.status()
        self.assertEqual(st["finished"], [])
        self.assertEqual(self.group(st, "skip")["chosen"], "analysed")
        self.assertEqual([m for m, _ in self.jf.calls if m != "GET"], [], "reading sends nothing that changes Jellyfin")

    def test_merge_versions_moves_to_quiet_hours(self):
        self.start()
        jp.choose(self.services, self.dir, "merge", "on", self.cfg)
        jp.restart(self.services)
        self.assertIn("Merge Versions merges once a day, in quiet hours", self.status()["finished"])
        for key in ("MergeMoviesTask", "MergeEpisodesTask"):
            t = next(t for t in self.jf.tasks if t["Key"] == key)
            self.assertEqual(t["Triggers"][0]["Type"], "DailyTrigger")

    def test_switching_deactivates_never_removes(self):
        self.start()
        jp.choose(self.services, self.dir, "skip", "downloaded", self.cfg)
        jp.restart(self.services)
        out = jp.choose(self.services, self.dir, "skip", "analysed", self.cfg)
        self.assertIn("Deactivated TheIntroDB (still installed)", out["done"])
        jp.restart(self.services)
        names = {p["Name"]: p["Status"] for p in self.jf.plugins}
        self.assertEqual(names, {"TheIntroDB": "Disabled", "Intro Skipper": "Active"})
        self.assertEqual(self.group(self.status(), "skip")["chosen"], "analysed")
        # Back again: activated, not installed twice
        out = jp.choose(self.services, self.dir, "skip", "downloaded", self.cfg)
        self.assertIn("Activated TheIntroDB again", out["done"])
        self.assertIn("Deactivated Intro Skipper (still installed)", out["done"])
        self.assertEqual(len(self.jf.plugins), 2)
        self.assertNotIn(("DELETE", "/Plugins"), [(m, r[:8]) for m, r in self.jf.calls])

    def test_do_not_install_deactivates(self):
        self.start()
        jp.choose(self.services, self.dir, "trakt", "on", self.cfg)
        jp.restart(self.services)
        out = jp.choose(self.services, self.dir, "trakt", "none", self.cfg)
        self.assertEqual(out["done"], ["Deactivated Trakt (still installed)"])

    def test_old_jellyfin_refuses_what_it_cannot_run(self):
        self.start(version="10.11.6")
        st = self.status()
        skip = self.group(st, "skip")
        self.assertEqual(skip["choices"][0]["package"], "SkipMe.db")
        self.assertFalse(skip["choices"][1]["available"])
        with self.assertRaises(ValueError):
            jp.choose(self.services, self.dir, "skip", "analysed", self.cfg)
        out = jp.choose(self.services, self.dir, "skip", "downloaded", self.cfg)
        self.assertIn("Installed SkipMe.db", out["done"][0])

    def test_unknown_choice_refused(self):
        self.start()
        with self.assertRaises(ValueError):
            jp.choose(self.services, self.dir, "skip", "everything", self.cfg)
        with self.assertRaises(ValueError):
            jp.choose(self.services, self.dir, "sonarr", "on", self.cfg)

    def test_quiet_hours_default_and_wrap(self):
        self.assertEqual(jp.quiet_hours({}), (1, 5))
        self.assertEqual(jp.quiet_hours({"download_hours": {"enabled": True, "start": 23, "end": 6}}), (23, 7))

    def test_jellyfin_down(self):
        services = [{"type": "jellyfin", "name": "Jellyfin", "url": "http://127.0.0.1:9", "api_key": KEY}]
        st = jp.status(services, tempfile.mkdtemp())
        self.assertFalse(st["connected"])
        self.assertIn("Jellyfin did not answer", st["problem"])

    def test_state_file_in_data_dir(self):
        self.start()
        jp.choose(self.services, self.dir, "merge", "on", self.cfg)
        jp.restart(self.services)
        self.status()
        self.assertTrue(os.path.exists(os.path.join(self.dir, "jellyfin-plugins.json")))


if __name__ == "__main__":
    unittest.main()
