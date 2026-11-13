"""A plug-in's life after it is added (DASH-330): states, set-up before Turn on, update and Roll back, catalogue
versions and checksums, events and jobs."""
import copy
import datetime as dt
import hashlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugin_life, plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND


def with_required():
    m = copy.deepcopy(ON_DEMAND)
    m["settings"] = list(m.get("settings") or []) + [{"key": "address", "label": "Its address", "type": "text", "required": True}]
    return m


class Life(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for target, kw in ((pa, {"host_path": lambda d, pid: f"/srv/starboard/data/plugins/{pid}"}),):
            for name, fn in kw.items():
                p = mock.patch.object(target, name, side_effect=fn)
                p.start()
                self.addCleanup(p.stop)
        p = mock.patch.object(pa, "_compose_run", return_value=(True, ""))
        self.compose = p.start()
        self.addCleanup(p.stop)

    def test_needs_setup_until_required_settings_are_filled(self):
        pa.install(self.tmp.name, with_required(), "/srv/media")
        s = plugin_life.status(self.tmp.name, "on-demand")
        self.assertEqual((s["state"], s["action"]), ("needs-setup", "settings"))
        self.assertIn("Its address", s["sentence"])
        with self.assertRaisesRegex(ValueError, "Fill in Its address"):
            pa.enable(self.tmp.name, "on-demand")
        pa.save_settings(self.tmp.name, "on-demand", {"address": "somewhere"})
        self.assertEqual(plugin_life.status(self.tmp.name, "on-demand")["state"], "installed")
        pa.enable(self.tmp.name, "on-demand")
        self.assertEqual(plugin_life.status(self.tmp.name, "on-demand")["state"], "enabled")

    def test_not_supported_when_starboard_is_past_its_range(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        with mock.patch.object(plugins, "API_VERSION", "9.0.0"):
            s = plugin_life.status(self.tmp.name, "on-demand")
        self.assertEqual((s["state"], s["button"]), ("not-supported", "Look for an update"))

    def test_update_keeps_the_previous_version_and_roll_back_swaps(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        pa.save_settings(self.tmp.name, "on-demand", {"quality": "720p"})
        newer = {**copy.deepcopy(ON_DEMAND), "version": "9.9.9"}
        said = plugin_life.update(self.tmp.name, "on-demand", newer, "/srv/media")
        self.assertIn("9.9.9", said)
        where = pa.folder(self.tmp.name, "on-demand")
        self.assertEqual(pa._read(os.path.join(where, "previous", "manifest.json"))["version"], ON_DEMAND["version"])
        self.assertEqual(pa._read(os.path.join(where, "settings.json"))["quality"], "720p")  # settings stay
        s = plugin_life.status(self.tmp.name, "on-demand")
        self.assertTrue(s["can_roll_back"])
        plugin_life.rollback(self.tmp.name, "on-demand", "/srv/media")
        self.assertEqual(pa._read(os.path.join(where, "manifest.json"))["version"], ON_DEMAND["version"])
        self.assertEqual(pa._read(os.path.join(where, "previous", "manifest.json"))["version"], "9.9.9")

    def test_update_refuses_another_plugin(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        with self.assertRaisesRegex(ValueError, "another plug-in"):
            plugin_life.update(self.tmp.name, "on-demand", {**ON_DEMAND, "id": "other-one"}, "/srv/media")

    def test_a_failure_soon_after_an_update_offers_roll_back_first(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        pa.enable(self.tmp.name, "on-demand")
        self.compose.return_value = (False, "Error: no such image")
        plugin_life.update(self.tmp.name, "on-demand", {**copy.deepcopy(ON_DEMAND), "version": "9.9.9"}, "/srv/media")
        s = plugin_life.status(self.tmp.name, "on-demand")
        self.assertEqual(s["state"], "failed")
        self.assertEqual(s["action"], "rollback")


CHANGES = [  # API 1.10 (DASH-393), newest first
    {"version": "0.4.0", "date": "2026-11-13", "added": ["**Usenet** as well as torrents", "A Test all button"], "fixed": ["Plays on a Roku"]},
    {"version": "0.3.0", "changed": ["Searches are kept for 10 minutes"]},
    {"version": "0.2.0", "added": ["The first version"]}]


class WhatsNew(unittest.TestCase):
    """What is new on a plug-in's State after an update, a Roll back or an update from an address (DASH-393)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name, fn in (("host_path", lambda d, pid: f"/srv/starboard/data/plugins/{pid}"), ("_compose_run", lambda *a, **k: (True, ""))):
            p = mock.patch.object(pa, name, side_effect=fn)
            p.start()
            self.addCleanup(p.stop)
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")

    def version(self, v, changes=CHANGES):
        return {**copy.deepcopy(ON_DEMAND), "version": v, "starboard_api": ">=1.10 <2.0", "changes": copy.deepcopy(changes)}

    def test_nothing_is_shown_before_an_update(self):
        self.assertIsNone(plugin_life.whats_new(self.tmp.name, "on-demand"))
        self.assertIsNone(next(p for p in pa.listing(self.tmp.name) if p["id"] == "on-demand")["whats_new"])

    def test_an_update_shows_the_changes_between_the_two_versions_newest_first(self):
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.4.0"), "/srv/media")
        w = plugin_life.whats_new(self.tmp.name, "on-demand")
        self.assertEqual((w["kind"], w["from"], w["to"]), ("newer", "0.2.0", "0.4.0"))
        self.assertEqual([v["version"] for v in w["versions"]], ["0.4.0", "0.3.0"])  # not 0.2.0, which they had
        first = w["versions"][0]
        self.assertEqual(first["date"], "13 November 2026")
        self.assertEqual([s["type"] for s in first["sections"]], ["Added", "Fixed"])
        self.assertEqual(first["sections"][0]["items"][0], [["strong", "Usenet"], ["text", " as well as torrents"]])
        # It is on the plug-in's listing, which the settings page draws.
        self.assertEqual(next(p for p in pa.listing(self.tmp.name) if p["id"] == "on-demand")["whats_new"]["to"], "0.4.0")

    def test_two_updates_before_anyone_looked_keep_the_first_version(self):
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.3.0", CHANGES[1:]), "/srv/media")
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.4.0"), "/srv/media")
        w = plugin_life.whats_new(self.tmp.name, "on-demand")
        self.assertEqual((w["from"], [v["version"] for v in w["versions"]]), ("0.2.0", ["0.4.0", "0.3.0"]))

    def test_got_it_is_kept_on_the_server_until_the_next_update(self):
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.3.0", CHANGES[1:]), "/srv/media")
        plugin_life.whats_new_seen(self.tmp.name, "on-demand")
        self.assertIsNone(plugin_life.whats_new(self.tmp.name, "on-demand"))
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.4.0"), "/srv/media")
        w = plugin_life.whats_new(self.tmp.name, "on-demand")
        self.assertEqual((w["from"], [v["version"] for v in w["versions"]]), ("0.3.0", ["0.4.0"]))

    def test_roll_back_lists_the_changes_of_the_version_left_behind(self):
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.4.0"), "/srv/media")
        plugin_life.whats_new_seen(self.tmp.name, "on-demand")
        plugin_life.rollback(self.tmp.name, "on-demand", "/srv/media")
        w = plugin_life.whats_new(self.tmp.name, "on-demand")
        self.assertEqual((w["kind"], w["from"], w["to"]), ("older", "0.4.0", "0.2.0"))
        self.assertEqual([v["version"] for v in w["versions"]], ["0.4.0", "0.3.0"])

    def test_roll_back_before_anyone_looked_shows_nothing(self):
        plugin_life.update(self.tmp.name, "on-demand", self.version("0.4.0"), "/srv/media")
        plugin_life.rollback(self.tmp.name, "on-demand", "/srv/media")
        self.assertIsNone(plugin_life.whats_new(self.tmp.name, "on-demand"))  # back where they were

    def test_a_plug_in_without_changes_shows_the_catalogue_line(self):
        plugin_life.update(self.tmp.name, "on-demand", {**copy.deepcopy(ON_DEMAND), "version": "0.4.0"}, "/srv/media",
                           note="Usenet as well as torrents.")
        w = plugin_life.whats_new(self.tmp.name, "on-demand")
        self.assertEqual((w["versions"], w["note"]), ([], "Usenet as well as torrents."))


class Catalogue(unittest.TestCase):
    def test_only_versions_this_starboard_runs_are_offered(self):
        entry = {"id": "x-plug", "versions": [
            {"version": "3.0.0", "starboard_api": ">=9.0", "manifest": "https://e.example/3.json"},
            {"version": "2.1.0", "starboard_api": ">=1.0 <2.0", "manifest": "https://e.example/2.json", "manifest_sha256": "a" * 64},
            {"version": "1.0.0", "manifest": "https://e.example/1.json"}]}
        clean = pa._clean_entry(entry)
        self.assertEqual((clean["version"], clean["hidden"], clean["hidden_needs"]), ("2.1.0", 1, ">=9.0"))
        self.assertEqual(clean["sha256"], "a" * 64)

    def test_an_entry_without_versions_still_works(self):
        clean = pa._clean_entry({"id": "x-plug", "manifest": "https://e.example/m.json"})
        self.assertEqual(clean["manifest"], "https://e.example/m.json")

    def test_a_changed_file_is_refused(self):
        raw = json.dumps(ON_DEMAND).encode()

        class Opener:
            def open(self, req, timeout=None):
                return io.BytesIO(raw)
        with mock.patch("starboard.outside.check_url"):
            self.assertEqual(pa.fetch_manifest("https://e.example/m.json", Opener(), hashlib.sha256(raw).hexdigest())["id"], "on-demand")
            with self.assertRaisesRegex(ValueError, "changed since the catalogue"):
                pa.fetch_manifest("https://e.example/m.json", Opener(), "0" * 64)


class Jobs(unittest.TestCase):
    def test_when_jobs_are_due(self):
        now = dt.datetime(2026, 11, 12, 3, 35)
        daily = {"daily": "03:30"}
        self.assertTrue(plugin_life.due(daily, now.timestamp() - 86400, now, 0))
        self.assertFalse(plugin_life.due(daily, now.timestamp() - 60, now, 0))
        self.assertFalse(plugin_life.due(daily, 0, now.replace(hour=3, minute=0), 0))
        self.assertTrue(plugin_life.due({"every_hours": 2}, now.timestamp() - 7300, now, 0))
        self.assertFalse(plugin_life.due({"every_hours": 2}, now.timestamp() - 3600, now, 0))
        self.assertTrue(plugin_life.due({"at_start": True}, 100, now, 200))
        self.assertFalse(plugin_life.due({"at_start": True}, 300, now, 200))

    def test_quiet_hours_follow_download_hours(self):
        class Cfg:
            data = {"download_hours": {"enabled": True, "start": 23, "end": 5}}
        self.assertTrue(plugin_life._in_quiet_hours(Cfg, dt.datetime(2026, 1, 1, 2)))
        self.assertFalse(plugin_life._in_quiet_hours(Cfg, dt.datetime(2026, 1, 1, 12)))
        self.assertTrue(plugin_life._in_quiet_hours(None, dt.datetime(2026, 1, 1, 3)))


class Manifest(unittest.TestCase):
    def base(self, **extra):
        return {**copy.deepcopy(ON_DEMAND), **extra}

    def test_new_fields_are_checked(self):
        self.assertEqual(plugins.check(self.base(notices=["p2p"], setup_required=True)), [])
        self.assertTrue(plugins.check(self.base(notices=["gambling"])))
        self.assertTrue(any("needs the permission" in p for p in plugins.check(self.base(events=["app.down"]))))
        good_job = {"id": "nightly", "label": "Tidy up", "path": "/tidy", "daily": "03:30"}
        self.assertEqual(plugins.check(self.base(jobs=[good_job])), [])
        self.assertTrue(plugins.check(self.base(jobs=[{**good_job, "every_hours": 2}])))  # two triggers
        self.assertTrue(plugins.check(self.base(jobs=[{**good_job, "daily": "25:00"}])))

    def test_the_install_warning_lists_notices_jobs_and_set_up(self):
        w = plugins.install_warning(self.base(notices=["p2p"], setup_required=True,
                                              jobs=[{"id": "nightly", "label": "Tidy up", "path": "/tidy", "daily": "03:30", "quiet_hours": True}]))
        self.assertTrue(any("internet address" in n for n in w["notices"]))
        self.assertTrue(any("Needs setting up" in n for n in w["notices"]))
        self.assertTrue(any("daily at 03:30, only in quiet hours" in r for r in w["runs"]))


class Events(unittest.TestCase):
    def test_only_changes_after_the_first_check_are_sent(self):
        from starboard import services
        sent = []
        w = plugin_life.EventWatch()
        jf = {"added": [{"type": "Movie", "title": "Old"}], "playing": []}
        q = {"items": [{"service_name": "Reelix", "title": "A", "progress": 100}]}
        with mock.patch.object(services, "cached", side_effect=lambda key, ttl, fn: jf if key == "jellyfin" else q):
            w.check({"item.added", "download.finished", "playback.started"}, [], lambda e, d: sent.append((e, d)) or 1)
            self.assertEqual(sent, [])
            jf["added"].append({"type": "Movie", "title": "New"})
            jf["playing"].append({"user": "Sam", "device": "TV", "title": "New"})
            q["items"].append({"service_name": "Reelix", "title": "B", "progress": 100})
            w.check({"item.added", "download.finished", "playback.started"}, [], lambda e, d: sent.append((e, d)) or 1)
        self.assertEqual(sorted(e for e, _ in sent), ["download.finished", "item.added", "playback.started"])

    def test_app_down_after_two_checks_and_up_once(self):
        from starboard import services
        said = []
        with mock.patch.object(services, "ON_CHANGE", side_effect=lambda e, d: said.append(e)):
            s = {"id": "test-app-events", "name": "Thing", "type": "radarr"}
            for state in ("up", "down", "down", "down", "up", "up"):
                services._record(s, {"id": s["id"], "state": state})
        self.assertEqual(said, ["app.down", "app.up"])


if __name__ == "__main__":
    unittest.main()
