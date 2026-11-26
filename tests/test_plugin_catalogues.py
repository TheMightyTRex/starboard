"""Plug-in catalogues (owner, 12 November 2026): Starboard's own collection, and others added from a link."""
import io
import json
import unittest
from unittest import mock

from starboard import plugins_admin as pa


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Opener:
    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def open(self, req, timeout=None):
        self.asked.append(req.full_url)
        a = self.answers.get(req.full_url)
        if a is None:
            raise OSError("no answer")
        return Resp(json.dumps(a).encode())


class Cfg:
    def __init__(self):
        self.data, self.saved = {}, 0

    def save(self):
        self.saved += 1


OTHER = "https://example.org/catalogue.json"
ENTRY = {"id": "hello", "name": "Hello", "description": "Says hello", "kind": "Look", "manifest": "https://example.org/hello.json",
         "permissions": ["network:lan", "made:up"]}


@mock.patch("starboard.outside.check_url", lambda url: None)
class Catalogues(unittest.TestCase):
    def setUp(self):
        pa._catalogues.clear()

    def test_add_read_remove(self):
        cfg = Cfg()
        op = Opener({OTHER: {"name": "Friend's plug-ins", "plugins": [ENTRY, {"id": "BAD ID"}]},
                     pa.CATALOGUE_URL: {"name": "Starboard plug-ins", "plugins": []}})
        got = pa.add_source(cfg, OTHER, op)
        self.assertEqual((got["name"], len(got["items"])), ("Friend's plug-ins", 1))
        self.assertEqual(cfg.data["plugin_catalogues"], [{"url": OTHER, "name": "Friend's plug-ins"}])
        with self.assertRaises(ValueError):
            pa.add_source(cfg, OTHER, op)  # already there
        cats, items = pa.catalogue(cfg, op, now=1000)
        self.assertEqual([c["own"] for c in cats], [True, False])
        self.assertEqual(items[0]["permissions"], ["network:lan"])  # unknown permissions dropped
        self.assertEqual(items[0]["catalogue"], "Friend's plug-ins")
        pa.remove_source(cfg, OTHER)
        self.assertEqual(cfg.data["plugin_catalogues"], [])
        with self.assertRaises(LookupError):
            pa.remove_source(cfg, OTHER)

    def test_only_the_own_collection_may_recommend(self):
        # DASH-425 (owner, 14 November 2026): "its recommended in the catalogue", never added by itself.
        cfg = Cfg()
        cfg.data["plugin_catalogues"] = [{"url": OTHER, "name": "x"}]
        own = {**ENTRY, "id": "direct-play", "recommended": True}
        op = Opener({pa.CATALOGUE_URL: {"name": "Starboard plug-ins", "plugins": [own, {**ENTRY, "id": "plain"}, {**ENTRY, "id": "odd", "recommended": "yes"}]},
                     OTHER: {"name": "Friend", "plugins": [{**ENTRY, "recommended": True}]}})
        _, items = pa.catalogue(cfg, op, now=1000)
        got = {(e["id"], e["own"]): e["recommended"] for e in items}
        self.assertEqual(got, {("direct-play", True): True, ("plain", True): False, ("odd", True): False, ("hello", False): False})

    def test_the_shipped_copy_recommends_direct_play(self):
        import os
        with open(os.path.join(os.path.dirname(__file__), "..", "plugins", "catalogue.json"), encoding="utf-8") as f:
            rows = {e["id"]: e for e in json.load(f)["plugins"]}
        self.assertIs(rows["direct-play"]["recommended"], True)
        self.assertLessEqual(sum(1 for e in rows.values() if e.get("recommended")), 4)  # a few, not every one

    def test_refuses_what_is_not_a_catalogue(self):
        for bad in ("http://example.org/c.json", "not an address"):
            with self.assertRaises(ValueError):
                pa.fetch_catalogue(bad, Opener({}))
        with self.assertRaises(ValueError):
            pa.fetch_catalogue(OTHER, Opener({OTHER: {"hello": 1}}))
        with self.assertRaises(ValueError):
            pa.fetch_catalogue(OTHER, Opener({}))

    def test_own_falls_back_to_shipped_copy_and_others_keep_last_list(self):
        cfg = Cfg()
        cfg.data["plugin_catalogues"] = [{"url": OTHER, "name": "x"}]
        op = Opener({OTHER: {"name": "Friend", "plugins": [ENTRY]}})
        cats, items = pa.catalogue(cfg, op, now=1000)
        self.assertGreater(cats[0]["count"], 0)  # the copy Starboard ships
        self.assertIn("did not answer", cats[0]["error"])  # and the page says GitHub did not answer
        self.assertEqual(cats[0]["read_at"], 0)
        cats, items = pa.catalogue(cfg, Opener({}), now=1000 + 90000)  # a day later, nothing answers
        self.assertTrue(cats[1]["error"])
        self.assertEqual(cats[1]["count"], 1)  # the last good list

    def test_read_once_a_day(self):
        op = Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [ENTRY]}})
        pa.catalogue(None, op, now=1000)
        pa.catalogue(None, op, now=2000)
        self.assertEqual(len(op.asked), 1)


@mock.patch("starboard.outside.check_url", lambda url: None)
class CheckNow(unittest.TestCase):
    """Check for updates now (owner, 26 November 2026): a release made after the last read is found at once, a catalogue
    that does not answer is said in words, and the button cannot be pressed again within a few seconds."""

    def setUp(self):
        pa._catalogues.clear()
        pa._forced["at"] = 0

    def test_kept_six_hours_then_read_again(self):
        op = Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [ENTRY]}})
        pa.catalogue(None, op, now=1000)
        pa.catalogue(None, op, now=1000 + 5 * 3600)  # inside 6 hours: nothing asked
        self.assertEqual(len(op.asked), 1)
        pa.catalogue(None, op, now=1000 + 6 * 3600 + 5)
        self.assertEqual(len(op.asked), 2)

    def test_a_new_version_is_found_by_checking_now(self):
        old = {**ENTRY, "version": "1.1.1"}
        new = {**ENTRY, "version": "1.1.2"}
        pa.catalogue(None, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [old]}}), now=1000)
        _, items = pa.catalogue(None, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [new]}}), now=2000)
        self.assertEqual(items[0]["version"], "1.1.1")  # an hour later it is still the old list: this was the bug
        got = pa.refresh(None, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [new]}}), now=2000)
        self.assertFalse(got["too_soon"])
        self.assertEqual(pa._catalogues[pa.CATALOGUE_URL]["items"][0]["version"], "1.1.2")
        self.assertEqual(got["catalogues"][0]["read_at"], 2000)

    def test_cannot_be_pressed_again_within_the_gap(self):
        op = Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": []}})
        pa.refresh(None, op, now=5000)
        again = pa.refresh(None, op, now=5000 + 10)
        self.assertTrue(again["too_soon"])
        self.assertEqual(again["wait"], pa.MIN_GAP - 10)
        self.assertIn(f"Try again in {pa.MIN_GAP - 10} seconds", again["said"])
        self.assertEqual(len(op.asked), 1)
        later = pa.refresh(None, op, now=5000 + pa.MIN_GAP + 1)
        self.assertFalse(later["too_soon"])
        self.assertEqual(len(op.asked), 2)

    def test_a_catalogue_that_fails_says_why_and_keeps_its_last_list(self):
        cfg = Cfg()
        cfg.data["plugin_catalogues"] = [{"url": OTHER, "name": "x"}]
        pa.refresh(cfg, Opener({OTHER: {"name": "Friend", "plugins": [ENTRY]}, pa.CATALOGUE_URL: {"name": "S", "plugins": []}}), now=1000)
        got = pa.refresh(cfg, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": []}}), now=2000)
        bad = [c for c in got["catalogues"] if not c["ok"]]
        self.assertEqual(len(bad), 1)
        self.assertEqual((bad[0]["count"], bad[0]["read_at"]), (1, 1000))  # the list from 1000 stays, and when it was read
        self.assertIn("did not answer", bad[0]["error"])
        self.assertEqual(got["failed"], 1)
        self.assertIn("1 did not answer", got["said"])
        self.assertEqual(pa.last_read()["errors"], 1)

    def test_errors_are_in_words(self):
        import socket
        import urllib.error
        self.assertIn("error 404", pa._why(urllib.error.HTTPError("https://x", 404, "Not Found", {}, None)))
        self.assertIn("5 seconds", pa._why(urllib.error.URLError(socket.timeout("timed out"))))
        self.assertIn("internet connection", pa._why(urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))))
        for text in (pa._why(OSError("[Errno 5] weird")), pa._why(urllib.error.URLError(ConnectionRefusedError()))):
            self.assertNotIn("Errno", text)

    def test_last_read_is_the_oldest_answer(self):
        cfg = Cfg()
        cfg.data["plugin_catalogues"] = [{"url": OTHER, "name": "x"}]
        pa.catalogue(cfg, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": []}, OTHER: {"name": "F", "plugins": []}}), now=1000)
        pa.catalogue(cfg, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": []}, OTHER: {"name": "F", "plugins": []}}), now=2000, force=True)
        self.assertEqual(pa.last_read()["read_at"], 2000)
        pa._catalogues[OTHER]["read_at"] = 1500
        self.assertEqual(pa.last_read()["read_at"], 1500)

    def test_the_update_is_listed_after_the_check_without_opening_the_catalogue(self):
        import tempfile

        from starboard import plugin_life
        with tempfile.TemporaryDirectory() as d:
            pdir = pa.folder(d, "hello")
            import os
            os.makedirs(pdir)
            pa._write(os.path.join(pdir, "manifest.json"), {"id": "hello", "name": "Hello", "version": "1.1.1"})
            pa._write(os.path.join(pdir, "state.json"), {"state": "installed"})
            self.assertEqual(plugin_life.updates_known(d), {})
            pa.refresh(None, Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [{**ENTRY, "version": "1.1.2", "permissions": ["network:lan"]}]}}), now=1000)
            known = plugin_life.updates_known(d)
            self.assertEqual(known["hello"]["version"], "1.1.2")
            self.assertEqual(known["hello"]["permissions"], ["network:lan"])


if __name__ == "__main__":
    unittest.main()


@mock.patch("starboard.outside.check_url", lambda url: None)
class StallboardChoice(unittest.TestCase):
    """DASH-563 (owner, 23 November 2026): Stallboard is a built-in choice, one tick, never on by itself. The recorded
    copy in tests/fixtures is the real catalogue.json as it was served on 24 November 2026, cut to 3 plug-ins; the
    full 33 were checked once against the live file with fetch_catalogue, and no test makes a live request."""

    def setUp(self):
        import os
        pa._catalogues.clear()
        self.url = pa.BUILTIN_SOURCES[0]["url"]
        with open(os.path.join(os.path.dirname(__file__), "fixtures", "stallboard-catalogue.json"), encoding="utf-8") as f:
            self.recorded = json.load(f)

    def test_the_recorded_copy_reads_with_the_real_fetch(self):
        got = pa.fetch_catalogue(self.url, Opener({self.url: self.recorded}))
        self.assertEqual((got["name"], len(got["items"])), ("Stallboard", 3))
        first = got["items"][0]
        self.assertTrue(first["manifest"].startswith("https://") and first["sha256"] is not None)
        self.assertTrue(first["permissions"] and set(first["permissions"]) <= set(pa.plugins.PERMISSIONS))

    def test_off_until_ticked_then_read_and_never_recommended(self):
        cfg = Cfg()
        op = Opener({self.url: {**self.recorded, "plugins": [{**self.recorded["plugins"][0], "recommended": True}]},
                     pa.CATALOGUE_URL: {"name": "Starboard plug-ins", "plugins": []}})
        self.assertEqual([s["url"] for s in pa.sources(cfg)], [pa.CATALOGUE_URL])
        self.assertEqual([(c["id"], c["on"]) for c in pa.builtin_choices(cfg)], [("stallboard", False)])
        pa.set_builtin(cfg, "stallboard", True)
        self.assertEqual(cfg.data["plugin_catalogues_on"], ["stallboard"])
        cats, items = pa.catalogue(cfg, op, now=1000)
        self.assertEqual([(c["name"], c["own"], c["builtin"]) for c in cats],
                         [("Starboard plug-ins", True, ""), ("Stallboard", False, "stallboard")])
        self.assertTrue(items and not any(e["recommended"] for e in items if not e["own"]))  # only the own collection recommends
        pa.set_builtin(cfg, "stallboard", False)
        self.assertEqual(cfg.data["plugin_catalogues_on"], [])
        self.assertEqual(len(pa.sources(cfg)), 1)

    def test_ticking_reads_nothing_and_installs_nothing(self):
        cfg, op = Cfg(), Opener({})
        pa.set_builtin(cfg, "stallboard", True)
        self.assertEqual(op.asked, [])
        with self.assertRaises(LookupError):
            pa.set_builtin(cfg, "made-up", True)

    def test_added_by_link_and_ticked_is_read_once(self):
        cfg = Cfg()
        cfg.data["plugin_catalogues"] = [{"url": self.url, "name": "Stallboard"}]
        pa.set_builtin(cfg, "stallboard", True)
        self.assertEqual([s["url"] for s in pa.sources(cfg)].count(self.url), 1)
        with self.assertRaises(ValueError):
            pa.add_source(Cfg(), self.url, Opener({}))  # offered as a choice instead

    def test_a_catalogue_that_does_not_answer_says_so(self):
        cfg = Cfg()
        pa.set_builtin(cfg, "stallboard", True)
        cats, _ = pa.catalogue(cfg, Opener({pa.CATALOGUE_URL: {"name": "x", "plugins": []}}), now=1000)
        self.assertTrue(cats[1]["error"])

    def test_the_choice_is_backed_up_and_checked_on_restore(self):
        import tempfile

        from starboard import backup
        from starboard.config import Config
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            one = Config(a)
            one.data["plugin_catalogues_on"] = ["stallboard"]
            one.save()
            out = backup.export(one, "0.30.0", a)
            self.assertEqual(out["settings"]["plugin_catalogues_on"], ["stallboard"])
            two = Config(b)
            backup.restore(two, out)
            self.assertEqual(two.data["plugin_catalogues_on"], ["stallboard"])
            out["settings"]["plugin_catalogues_on"] = ["stallboard", "<script>"]
            backup.restore(two, out)
            self.assertEqual(two.data["plugin_catalogues_on"], ["stallboard"])
