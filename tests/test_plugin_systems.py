"""Plug-in API 1.19 (25 November 2026, DASH-567): the tag for the system a plug-in needs. A manifest names it in
`requires`; older manifests get it from the permissions they ask for; Starboard says it in words on the Catalogue, the
plug-in page, Manage and Ready to update, and says why when the system is not there. Nothing is ever stopped for it."""
import json
import os
import re
import tempfile
import unittest
from unittest import mock

from starboard import plugin_systems as ps, plugins, plugins_admin as pa
from tests.test_plugins import ON_DEMAND

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JELLYFIN = [{"id": "jellyfin", "type": "jellyfin", "url": "http://127.0.0.1:8096", "api_key": "k"}]
REELIX = [{"id": "reelix", "type": "link", "icon": "reelix", "url": "http://127.0.0.1:7878"}]


class Parsing(unittest.TestCase):
    def test_the_forms(self):
        self.assertEqual(ps.parse_need("jellyfin"), (("jellyfin",), False))
        self.assertEqual(ps.parse_need("jellyfin only"), (("jellyfin",), True))
        self.assertEqual(ps.parse_need("plex or emby"), (("plex", "emby"), False))
        self.assertEqual(ps.parse_need("plex or emby or jellyfin"), (("plex", "emby", "jellyfin"), False))

    def test_bad_forms(self):
        for bad in ("", "Jellyfin", "plex or", "or plex", "plex and emby", "plex or emby only", "plex or plex", "jellyfin only only",
                    "jellyfin  only", None, 3, ["jellyfin"]):
            self.assertIsNone(ps.parse_need(bad), bad)

    def test_the_check_names_each_problem(self):
        self.assertEqual(ps.problems([]), [])
        self.assertEqual(ps.problems(["jellyfin only", "plex or emby", "reelix", "qbittorrent"]), [])
        self.assertTrue(ps.problems("jellyfin"))
        self.assertTrue(ps.problems(["jellyfin"] * 2))
        self.assertTrue(ps.problems(["jellyfin", "reelix", "plex", "emby", "kavita"]))
        self.assertIn("is not a system Starboard knows", ps.problems(["windows"])[0])
        self.assertIn("must be a system", ps.problems(["Jellyfin!"])[0])

    def test_a_manifest_is_checked_and_is_additive(self):
        self.assertEqual(plugins.check({**ON_DEMAND, "requires": ["jellyfin only"]}), [])
        self.assertEqual(plugins.check({**ON_DEMAND, "requires": []}), [])
        self.assertEqual(plugins.check(ON_DEMAND), [])  # an older manifest says nothing and is still fine
        self.assertTrue([p for p in plugins.check({**ON_DEMAND, "requires": ["nonsense"]}) if "requires[0]" in p])
        self.assertGreaterEqual(tuple(map(int, plugins.API_VERSION.split("."))), (1, 20, 0))

    def test_the_schema_and_the_reference_have_it(self):
        with open(os.path.join(ROOT, "starboard", "plugin-manifest.schema.json")) as f:
            schema = json.load(f)
        self.assertEqual(schema["properties"]["requires"]["maxItems"], 4)
        for good in ("jellyfin", "jellyfin only", "plex or emby"):
            self.assertTrue(re.match(schema["properties"]["requires"]["items"]["pattern"], good), good)
        for bad in ("Jellyfin", "plex and emby", "plex or emby only x"):
            self.assertFalse(re.match(schema["properties"]["requires"]["items"]["pattern"], bad), bad)
        with open(os.path.join(ROOT, "docs", "help", "developers", "plugin-manifest-reference.md")) as f:
            self.assertIn("`requires`", f.read())


class FromPermissions(unittest.TestCase):
    def test_old_manifests_keep_working_and_get_a_tag(self):
        for perm, tag in (("jellyfin:key", "Jellyfin only"), ("jellyfin:metadata", "Jellyfin only"), ("jellyfin:libraries", "Jellyfin only"),
                          ("reelix:key", "Needs Reelix"), ("usenet:servers", "Needs SABnzbd or NZBGet")):
            got = ps.describe({"permissions": [perm]})
            self.assertEqual((got["tag"], got["from"]), (tag, "permissions"), perm)
        self.assertEqual(ps.describe({"permissions": ["jellyfin:key", "jellyfin:metadata", "jellyfin:libraries"]})["tag"], "Jellyfin only")
        self.assertEqual(ps.describe({"permissions": ["apps:read", "network:lan"]}), {"tag": "", "needs": [], "from": "", "ok": None, "reason": ""})

    def test_an_explicit_requires_wins_and_empty_means_nothing(self):
        got = ps.describe({"permissions": ["jellyfin:key"], "requires": ["plex or jellyfin"]})
        self.assertEqual((got["tag"], got["from"]), ("Plex or Jellyfin", "manifest"))
        got = ps.describe({"permissions": ["jellyfin:key"], "requires": []})
        self.assertEqual((got["tag"], got["needs"], got["from"]), ("", [], "manifest"))

    def test_several_needs_read_in_order(self):
        self.assertEqual(ps.describe({"requires": ["jellyfin", "reelix"]})["tag"], "Jellyfin only, needs Reelix")
        self.assertEqual(ps.describe({"permissions": ["reelix:key", "jellyfin:key"]})["tag"], "Needs Reelix, Jellyfin only")

    def test_the_older_manifests_of_the_collection_are_all_mapped(self):
        # Every permission that names a system is mapped, so nothing in the collection is left without its tag.
        self.assertEqual(set(ps.FROM_PERMISSIONS) - set(plugins.PERMISSIONS), set())
        for alts in ps.FROM_PERMISSIONS.values():
            self.assertTrue(all(a in ps.SYSTEMS for a in alts))


class Presence(unittest.TestCase):
    def test_a_service_with_an_address_is_there(self):
        self.assertEqual(ps.present_in(JELLYFIN), {"jellyfin"})
        self.assertEqual(ps.present_in(REELIX), {"reelix"})
        self.assertEqual(ps.present_in(JELLYFIN + REELIX), {"jellyfin", "reelix"})
        self.assertEqual(ps.present_in([{**JELLYFIN[0], "enabled": False}, {"type": "jellyfin", "url": ""}, {"type": "link"}, "x"]), set())
        self.assertEqual(ps.present_in(None, extra=("plex",)), {"plex"})

    def test_every_combination(self):
        jellyfin_only = {"requires": ["jellyfin only"]}
        plex_or_emby = {"requires": ["plex or emby"]}
        both = {"requires": ["jellyfin", "reelix"]}
        cases = (
            (jellyfin_only, {"jellyfin"}, True, ""),
            (jellyfin_only, set(), False, "Needs Jellyfin, which this Starboard does not use"),
            (jellyfin_only, {"plex"}, False, "Needs Jellyfin, which this Starboard does not use"),
            (plex_or_emby, {"plex"}, True, ""),
            (plex_or_emby, {"emby"}, True, ""),
            (plex_or_emby, {"plex", "emby", "jellyfin"}, True, ""),
            (plex_or_emby, {"jellyfin"}, False, "Needs Plex or Emby, which this Starboard does not use"),
            (both, {"jellyfin", "reelix"}, True, ""),
            (both, {"jellyfin"}, False, "Needs Reelix, which this Starboard does not use"),
            (both, {"reelix"}, False, "Needs Jellyfin, which this Starboard does not use"),
            (both, set(), False, "Needs Jellyfin, and Reelix, which this Starboard does not use"),
            ({"requires": ["jellyfin", "plex or emby"]}, set(), False, "Needs Jellyfin, and either Plex or Emby, which this Starboard does not use"),
            ({"requires": []}, set(), True, ""),
            ({}, set(), True, ""),
        )
        for thing, present, ok, why in cases:
            got = ps.describe(thing, present)
            self.assertEqual((got["ok"], got["reason"]), (ok, why), (thing, present))
            self.assertEqual(bool(got["waiting"]), not ok, (thing, present))

    def test_not_known_yet_says_nothing(self):
        got = ps.describe({"requires": ["jellyfin"]})
        self.assertEqual((got["ok"], got["reason"]), (None, ""))
        self.assertIs(ps.judge(got, None), got)

    def test_judging_does_not_change_the_answer_given(self):
        base = ps.describe({"requires": ["jellyfin"]})
        before = json.dumps(base)
        ps.judge(base, set())
        self.assertEqual(json.dumps(base), before)

    def test_waiting_is_said_in_words_and_nothing_is_stopped(self):
        got = ps.describe({"requires": ["jellyfin"]}, set())
        self.assertEqual(got["waiting"], "Waiting: needs Jellyfin, which this Starboard does not use. It is not stopped and keeps its "
                                         "settings, and carries on when that system is there.")
        self.assertEqual(ps.describe({"requires": ["jellyfin"]}, {"jellyfin"}).get("waiting"), "")

    def test_words_never_use_colour_or_banned_words(self):
        for thing in ({"requires": ["jellyfin only"]}, {"requires": ["plex or emby"]}, {"requires": ["reelix", "qbittorrent"]}):
            got = ps.describe(thing, set())
            text = " ".join([got["tag"], got["reason"], got["waiting"]])
            self.assertNotRegex(text, r"\b(See|Look|advanced)\b")
            self.assertNotIn("—", text)
            self.assertNotRegex(text, r"n't|'s\b|'re\b")


class Shown(unittest.TestCase):
    def test_the_add_a_plug_in_summary_has_the_tag(self):
        m = {**ON_DEMAND, "permissions": ["media:read", "jellyfin:key"]}
        got = pa.summary(m, [])["system"]
        self.assertEqual((got["tag"], got["ok"]), ("Jellyfin only", None))
        self.assertEqual(pa.summary({**ON_DEMAND, "requires": ["plex or emby"]}, [])["system"]["tag"], "Plex or Emby")

    def test_a_catalogue_entry_carries_it_or_gets_it_from_its_permissions(self):
        e = {"id": "watch-stats", "name": "Watch statistics", "permissions": ["jellyfin:key"]}
        self.assertEqual(pa._clean_entry(e)["system"]["tag"], "Jellyfin only")
        self.assertEqual(pa._clean_entry({**e, "requires": ["plex or emby"]})["system"]["tag"], "Plex or Emby")
        self.assertEqual(pa._clean_entry({**e, "requires": []})["system"]["tag"], "")
        self.assertEqual(pa._clean_entry({**e, "requires": ["x", 5, "jellyfin"]})["system"]["tag"], "Jellyfin only")
        self.assertEqual(pa._clean_entry({"id": "plain-one", "name": "Plain"})["system"]["tag"], "")

    def test_an_installed_plug_in_is_listed_with_its_tag(self):
        m = {**ON_DEMAND, "permissions": ["media:read", "network:vpn", "jellyfin:key"]}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(pa, "host_path", side_effect=lambda d_, pid: f"/srv/sb/plugins/{pid}"):
            pa.install(d, m, "/srv/media")
            got = pa.listing(d)[0]["system"]
            self.assertEqual(got["tag"], "Jellyfin only")
            self.assertEqual(ps.judge(got, ps.present_in([]))["ok"], False)
            self.assertEqual(ps.judge(got, ps.present_in(JELLYFIN))["ok"], True)
            self.assertEqual(pa.listing(d)[0]["state"], "installed")  # the state is untouched: nothing is stopped for it


if __name__ == "__main__":
    unittest.main()
