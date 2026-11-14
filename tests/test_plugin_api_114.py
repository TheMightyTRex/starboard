"""Plug-in API 1.14 (DASH-428, DASH-432): the logo (checked, cleaned, kept and served), the card band's status and
time, a job schedule from the plug-in's settings, and the jellyfin:metadata permission."""
import base64
import copy
import datetime as dt
import json
import os
import struct
import tempfile
import time
import unittest
import zlib
from unittest import mock

from starboard import plugin_cards, plugin_life, plugin_logo, plugin_tester, plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND

GOOD_SVG = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><title>Play</title>'
            b'<defs><linearGradient id="g"><stop offset="0" stop-color="#0b5f5a"/></linearGradient></defs>'
            b'<rect x="2" y="4" width="20" height="13" fill="url(#g)" data-x="1"/><path d="M10 7v6l5-3z" fill="currentColor"/>'
            b'<use href="#g"/></svg>')


def png(w, h):
    raw = b"".join(b"\x00" + b"\x00" * (w * 3) for _ in range(h))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def schedule_manifest(default=None):
    m = copy.deepcopy(ON_DEMAND)
    m["settings"] = m["settings"] + [{"key": "when", "label": "When to shrink", "type": "schedule",
                                      "default": default or {"every": "week", "day": "sunday", "time": "03:30"}}]
    m["jobs"] = [{"id": "shrink", "label": "Shrink pictures", "path": "/jobs/shrink", "schedule": "when", "time_limit_minutes": 120}]
    return m


class Logo(unittest.TestCase):
    def test_a_plain_svg_is_kept_and_drawn_again(self):
        out = plugin_logo.clean_svg(GOOD_SVG)
        self.assertIn(b'viewBox="0 0 24 24"', out)
        self.assertIn(b"url(#g)", out)
        self.assertNotIn(b"data-x", out)  # left out quietly: it draws nothing

    def test_anything_that_runs_or_loads_is_refused(self):
        bad = {
            b'<svg viewBox="0 0 1 1"><script>alert(1)</script></svg>': "not allowed",
            b'<svg viewBox="0 0 1 1" onload="alert(1)"></svg>': "event handler",
            b'<svg viewBox="0 0 1 1"><image href="https://x.invalid/a.png"/></svg>': "not allowed",
            b'<svg viewBox="0 0 1 1"><use href="https://x.invalid/a.svg#b"/></svg>': "goes outside",
            b'<svg viewBox="0 0 1 1"><rect fill="url(https://x.invalid/a)"/></svg>': "url()",
            b'<svg viewBox="0 0 1 1"><rect style="fill:red"/></svg>': "style",
            b'<svg viewBox="0 0 1 1"><foreignObject/></svg>': "not allowed",
            b'<!DOCTYPE svg [<!ENTITY a "b">]><svg viewBox="0 0 1 1"/>': "DOCTYPE",
            b'<svg><rect/></svg>': "viewBox",
            b'<html/>': "not an SVG",
            b'<svg viewBox="0 0 1 1">' + b" " * plugin_logo.SVG_MAX + b"</svg>": "larger",
        }
        for raw, words in bad.items():
            with self.assertRaises(ValueError) as e:
                plugin_logo.clean_svg(raw)
            self.assertIn(words, str(e.exception), raw[:40])

    def test_png_size_and_shape(self):
        self.assertEqual(plugin_logo.check_png(png(64, 64))[:8], b"\x89PNG\r\n\x1a\n")
        for bad, words in ((png(64, 32), "square"), (png(16, 16), "square"), (png(300, 300), "square"), (b"GIF89a", "not a PNG")):
            with self.assertRaises(ValueError) as e:
                plugin_logo.check_png(bad)
            self.assertIn(words, str(e.exception))

    def test_the_manifest_field(self):
        m = copy.deepcopy(ON_DEMAND)
        m["logo"] = {"file": "logo.svg", "alt": "A play symbol on a screen"}
        self.assertEqual(plugins.check(m, dev=True), [])
        for bad in ({"file": "../logo.svg", "alt": "A play symbol"}, {"file": "logo.gif", "alt": "A play symbol"},
                    {"file": "logo.svg"}, {"file": "logo.svg", "alt": "x"}, "logo.svg", {"file": "logo.svg", "alt": "Play", "size": 2}):
            m["logo"] = bad
            self.assertTrue(any(p.startswith("logo") for p in plugins.check(m, dev=True)), bad)

    def test_the_address_is_beside_the_manifest(self):
        self.assertEqual(plugin_logo.address_beside("https://x.invalid/repo/main/direct-play/starboard-plugin.json", "logo.svg"),
                         "https://x.invalid/repo/main/direct-play/logo.svg")
        with self.assertRaises(ValueError):
            plugin_logo.address_beside("https://x.invalid/a/starboard-plugin.json", "../b/logo.svg")

    def test_a_catalogue_logo_is_a_cleaned_data_address(self):
        good = "data:image/svg+xml;base64," + base64.b64encode(GOOD_SVG).decode()
        entry = pa._clean_entry({"id": "direct-play", "logo": good, "logo_alt": "A play symbol"})
        self.assertTrue(entry["logo"]["url"].startswith("data:image/svg+xml;base64,"))
        self.assertEqual(entry["logo"]["alt"], "A play symbol")
        bad = "data:image/svg+xml;base64," + base64.b64encode(b'<svg viewBox="0 0 1 1"><script/></svg>').decode()
        for e in ({"logo": bad, "logo_alt": "A play symbol"}, {"logo": good}, {"logo": "https://x.invalid/a.svg", "logo_alt": "A play"}):
            self.assertIsNone(pa._clean_entry({"id": "direct-play", **e})["logo"], e)

    def test_kept_served_and_put_aside(self):
        with tempfile.TemporaryDirectory() as d:
            where = pa.folder(d, "on-demand")
            os.makedirs(where)
            m = {**ON_DEMAND, "logo": {"file": "logo.svg", "alt": "A play symbol"}}
            self.assertIsNone(pa.logo_info(d, "on-demand", m))
            pa.keep_logo(d, "on-demand", (plugin_logo.clean_svg(GOOD_SVG), "image/svg+xml"))
            info = pa.logo_info(d, "on-demand", m)
            self.assertTrue(info["url"].startswith("/api/plugins/on-demand/logo?v="))
            self.assertEqual(info["alt"], "A play symbol")
            pa.keep_logo(d, "on-demand", None)  # a version without one: the last is put aside, not deleted
            self.assertIsNone(pa.logo_info(d, "on-demand", m))
            self.assertTrue(os.path.exists(os.path.join(where, "logo.svg.old")))

    def test_the_tester_reports_a_refused_logo_and_suggests_one(self):
        m = copy.deepcopy(ON_DEMAND)
        r = plugin_tester.report(m, dev=True)
        self.assertTrue(any(i["where"] == "logo" and i["severity"] == "info" for i in r["issues"]))
        m["logo"] = {"file": "logo.svg", "alt": "A play symbol"}
        r = plugin_tester.report(m, dev=True, logo_problem="The SVG logo was refused: <script> is not allowed")
        self.assertTrue(r["ok"])  # it is still added, with its initials
        self.assertTrue(any(i["where"] == "logo" and i["severity"] == "warning" for i in r["issues"]))


class Band(unittest.TestCase):
    def test_status_and_updated_are_kept(self):
        now = int(time.time())
        out = plugin_cards.clean("list", {"items": [], "status": "converting", "updated": now})
        self.assertEqual((out["status"], out["status_label"], out["tone"], out["updated"]), ("converting", "Converting", "info", now))
        out = plugin_cards.clean("stat", {"value": 1, "status": "ok", "status_label": "Protected and checked today, all good"})
        self.assertEqual((out["status_label"], out["tone"]), ("Protected and checked to", "success"))  # cut to 24

    def test_every_status_has_words_and_a_design_system_tone(self):
        for words, tone in plugin_cards.STATUSES.values():
            self.assertTrue(words[0].isupper())
            self.assertIn(tone, ("success", "info", "neutral", "muted", "warning", "danger"))

    def test_unknown_values_are_left_out_and_the_tester_says_so(self):
        out = plugin_cards.clean("stat", {"value": 1, "status": "on fire", "updated": time.time() + 86400})
        self.assertNotIn("status", out)
        self.assertNotIn("updated", out)
        with self.assertRaises(ValueError) as e:
            plugin_cards.clean("stat", {"value": 1, "status": "on fire"}, strict=True)
        self.assertIn("status must be one of", str(e.exception))
        with self.assertRaises(ValueError):
            plugin_cards.clean("stat", {"value": 1, "status_label": "Busy"}, strict=True)

    def test_the_answer_says_when_starboard_asked(self):
        with tempfile.TemporaryDirectory() as d:
            where = pa.folder(d, "on-demand")
            os.makedirs(where)
            with open(os.path.join(where, "manifest.json"), "w") as f:
                json.dump(ON_DEMAND, f)
            from tests.test_plugin_cards import FakeOpener
            plugin_cards._cache.clear()  # another test may have kept an answer for the same card
            with mock.patch.object(plugin_cards, "_host", return_value="x"):
                out = plugin_cards.answer(d, "on-demand", "titles", FakeOpener(b'{"value": 3, "status": "done"}'))
            self.assertEqual(out["data"]["status"], "done")
            self.assertAlmostEqual(out["asked"], time.time(), delta=5)


class Schedule(unittest.TestCase):
    def test_the_setting_and_the_job_are_checked(self):
        self.assertEqual(plugins.check(schedule_manifest(), dev=True), [])
        m = schedule_manifest({"every": "fortnight", "time": "03:30"})
        self.assertIn("settings[3]: default must say every day, every week or every month", plugins.check(m, dev=True))
        m = schedule_manifest()
        m["jobs"][0]["schedule"] = "quality"  # a choice, not a schedule
        self.assertIn("jobs[0]: schedule must name one of its settings of type schedule", plugins.check(m, dev=True))
        m["jobs"][0]["daily"] = "03:00"
        self.assertTrue(any("give one of daily" in p for p in plugins.check(m, dev=True)))

    def test_values(self):
        ok = ({"every": "day", "time": "00:00"}, {"every": "week", "day": "monday", "time": "23:59"},
              {"every": "month", "date": 31, "time": "03:30"})
        for v in ok:
            self.assertIsNone(plugins.schedule_problem(v), v)
        for v, words in (({"every": "week", "time": "03:30"}, "day of the week"), ({"every": "month", "date": 0, "time": "03:30"}, "date"),
                         ({"every": "day", "time": "24:00"}, "time"), ({"every": "day", "time": "03:30", "hour": 3}, "schedule"),
                         ("weekly", "schedule"), ({"every": "month", "date": True, "time": "03:30"}, "date")):
            self.assertIn(words, plugins.schedule_problem(v), v)
        self.assertEqual(plugins.schedule_clean({"every": "week", "day": "sunday", "date": 4, "time": "03:30"}),
                         {"every": "week", "day": "sunday", "time": "03:30"})
        self.assertEqual(plugins.schedule_words({"every": "month", "date": 31, "time": "03:30"}),
                         "Every month on the 31st at 03:30 (the last day in shorter months)")
        self.assertEqual(plugins.schedule_words({"every": "month", "date": 2, "time": "03:30"}), "Every month on the 2nd at 03:30")

    def test_when_it_is_due(self):
        week = {"every": "week", "day": "sunday", "time": "03:30"}
        job = {"schedule": "when"}
        sunday = dt.datetime(2026, 11, 15, 3, 35)
        self.assertTrue(plugin_life.due(job, 0, sunday, 0, week))
        self.assertFalse(plugin_life.due(job, sunday.timestamp(), sunday, 0, week))  # ran already
        self.assertFalse(plugin_life.due(job, 0, sunday.replace(hour=3, minute=0), 0, week))  # not yet
        self.assertFalse(plugin_life.due(job, 0, sunday + dt.timedelta(hours=7), 0, week))  # missed: waits for next week
        self.assertFalse(plugin_life.due(job, 0, sunday, 0, None))  # no usable schedule: only Run now

    def test_a_month_without_the_date_runs_on_its_last_day(self):
        month = {"every": "month", "date": 31, "time": "03:30"}
        self.assertEqual(plugin_life.last_slot(month, dt.datetime(2026, 4, 30, 4)), dt.datetime(2026, 4, 30, 3, 30))
        self.assertEqual(plugin_life.last_slot(month, dt.datetime(2026, 2, 28, 4)), dt.datetime(2026, 2, 28, 3, 30))
        self.assertEqual(plugin_life.next_slot(month, dt.datetime(2026, 1, 30, 12)), dt.datetime(2026, 1, 31, 3, 30))
        self.assertEqual(plugin_life.next_slot(month, dt.datetime(2026, 12, 31, 4)), dt.datetime(2027, 1, 31, 3, 30))
        self.assertTrue(plugin_life.due({"schedule": "w"}, 0, dt.datetime(2027, 2, 28, 3, 31), 0, month))

    def test_saved_from_settings_and_shown_in_jobs(self):
        with tempfile.TemporaryDirectory() as d:
            where = pa.folder(d, "on-demand")
            os.makedirs(where)
            m = schedule_manifest()
            for name, data in (("manifest.json", m), ("state.json", {"state": "enabled"}), ("settings.json", {})):
                with open(os.path.join(where, name), "w") as f:
                    json.dump(data, f)
            with mock.patch.object(pa.api_v1, "audit"):
                with self.assertRaises(ValueError) as e:
                    pa.save_settings(d, "on-demand", {"when": {"every": "week", "time": "03:30"}})
                self.assertIn("When to shrink: needs a day of the week", str(e.exception))
                pa.save_settings(d, "on-demand", {"when": {"every": "month", "date": 1, "day": "monday", "time": "02:00"}})
            with open(os.path.join(where, "settings.json")) as f:
                self.assertEqual(json.load(f)["when"], {"every": "month", "date": 1, "time": "02:00"})
            jobs = plugin_life.jobs(d)
            self.assertTrue(jobs[0]["when"].startswith("Every month on the 1st at 02:00, next "), jobs[0]["when"])

    def test_install_warning_says_who_chooses(self):
        runs = plugins.install_warning(schedule_manifest())["runs"]
        self.assertIn("A job, Shrink pictures, on the schedule you choose in its settings (every week on sunday at 03:30 to start with)", runs)


class MetadataPermission(unittest.TestCase):
    def manifest(self, vol="jellyfin-metadata", perm=True):
        m = copy.deepcopy(ON_DEMAND)
        m["permissions"] = m["permissions"] + (["jellyfin:metadata"] if perm else [])
        m["containers"][0]["volumes"] = ["data", vol]
        if not vol.endswith(":ro"):  # writing needs the media folder's owner; reading needs nothing more
            m["containers"][0]["user"] = "media"
        return m

    def test_only_with_the_permission(self):
        self.assertEqual(plugins.check(self.manifest(), dev=True), [])
        self.assertIn("containers[0]: jellyfin-metadata needs the permission jellyfin:metadata",
                      plugins.check(self.manifest(perm=False), dev=True))
        self.assertEqual(plugins.PERMISSIONS["jellyfin:metadata"][1], "medium")

    def test_the_warning_says_it_plainly(self):
        w = plugins.install_warning(self.manifest())
        self.assertTrue(any(c.startswith("Jellyfin's metadata folder: the posters, photos and details Jellyfin saved. It can change") for c in w["change"]))
        self.assertEqual(w["risk"], "high")  # jellyfin:key is there too
        w = plugins.install_warning(self.manifest("jellyfin-metadata:ro"))
        self.assertIn("Jellyfin's metadata folder: the posters, photos and details Jellyfin saved (read only)", w["see"])

    def test_mounted_only_when_granted_at_metadata(self):
        text = plugins.compose(self.manifest(), "/srv/p", "/srv/media", extra={"jellyfin_metadata": "/srv/config/jellyfin-metadata"})
        self.assertIn('"/srv/config/jellyfin-metadata:/metadata"', text)
        ro = plugins.compose(self.manifest("jellyfin-metadata:ro"), "/srv/p", "/srv/media", extra={"jellyfin_metadata": "/srv/md"})
        self.assertIn('"/srv/md:/metadata:ro"', ro)
        self.assertNotIn("/metadata", plugins.compose(ON_DEMAND, "/srv/p", "/srv/media"))
        with self.assertRaises(ValueError) as e:
            plugins.compose(self.manifest(), "/srv/p", "/srv/media")
        self.assertIn("Jellyfin's metadata folder", str(e.exception))

    def test_the_folder_is_found_from_jellyfins_own_mounts(self):
        from starboard import containers
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(containers, "docker", return_value={"Mounts": [{"Destination": "/metadata", "Source": "/srv/c/jellyfin-metadata"}]}):
                self.assertEqual(pa.jellyfin_metadata_dir(d), "/srv/c/jellyfin-metadata")
            with mock.patch.object(containers, "docker", return_value={"Mounts": [{"Destination": "/config", "Source": "/srv/c/jellyfin"}]}):
                self.assertEqual(pa.jellyfin_metadata_dir(d), "/srv/c/jellyfin/data/metadata")
            with mock.patch.object(containers, "docker", side_effect=containers.DockerError("no")), \
                    mock.patch("starboard.stack.env_values", return_value={"CONFIG_DIR": "/srv/c"}):
                self.assertEqual(pa.jellyfin_metadata_dir(d), "/srv/c/jellyfin-metadata")


class Schema(unittest.TestCase):
    def test_the_schema_file_is_current(self):
        with tempfile.TemporaryDirectory() as d:
            plugins.write_schema(os.path.join(d, "s.json"))
            here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starboard", "plugin-manifest.schema.json")
            with open(os.path.join(d, "s.json")) as a, open(here) as b:
                self.assertEqual(json.load(a), json.load(b))


if __name__ == "__main__":
    unittest.main()
