"""Reelix's smaller settings (DASH-204) against tests/reelix_stand_in.py: tags, path mappings and the site list's
automatic updates, each inside one admin sign-in."""
import unittest

from starboard import reelix_admin, reelix_extras
from tests.reelix_stand_in import StandIn, serve

PASSWORD = "reelix-admin-password"


class Extras(unittest.TestCase):
    def setUp(self):
        self.state = StandIn(password=PASSWORD)
        self.server, self.base = serve(self.state)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def act(self, action, body=None):
        with reelix_admin.Visit(self.base, PASSWORD) as reelix:
            return reelix_extras.act(reelix, action, body or {})

    def test_tags_are_listed_in_order_added_and_removed(self):
        self.assertEqual([t["label"] for t in self.act("tags")["tags"]], ["4k", "flaresolverr"])
        out = self.act("tag-add", {"label": "  kids  "})
        self.assertEqual(out["done"], "Tag kids added")
        self.assertIn("kids", [t["label"] for t in out["tags"]])
        kids = next(t for t in out["tags"] if t["label"] == "kids")
        out = self.act("tag-remove", {"id": kids["id"]})
        self.assertNotIn("kids", [t["label"] for t in out["tags"]])

    def test_a_tag_is_checked_before_reelix_is_asked(self):
        with self.assertRaises(ValueError):
            self.act("tag-add", {"label": "4K"})  # the same, whatever the case
        with self.assertRaises(ValueError):
            self.act("tag-add", {"label": "<script>"})
        with self.assertRaises(ValueError):
            self.act("tag-remove", {"id": 99})
        self.assertNotIn(("POST", "/tags"), self.state.calls)

    def test_path_mappings_are_added_changed_and_removed(self):
        out = self.act("mappings")
        self.assertEqual(out["mappings"], [])
        out = self.act("mapping-save", {"host": "192.168.1.20", "remote": "D:\\Downloads", "local": "/data/downloads/remote"})
        m = out["mappings"][0]
        self.assertEqual((m["remote"], m["local"]), ("D:\\Downloads\\", "/data/downloads/remote/"))
        out = self.act("mapping-save", {"id": m["id"], "host": "192.168.1.21", "remote": "/downloads", "local": "/data/downloads"})
        self.assertEqual(out["mappings"][0]["host"], "192.168.1.21")
        self.assertEqual(out["done"], "Path mapping for 192.168.1.21 saved")
        out = self.act("mapping-remove", {"id": m["id"]})
        self.assertEqual(out["mappings"], [])

    def test_a_path_mapping_needs_real_folders(self):
        for bad in ({"host": "gluetun", "remote": "downloads", "local": "/data"}, {"host": "gluetun", "remote": "/x", "local": "relative"},
                    {"host": "", "remote": "/x", "local": "/data"}, {"host": "gluetun", "remote": "/x/../etc", "local": "/data"}):
            with self.assertRaises(ValueError):
                self.act("mapping-save", bad)
        self.assertEqual(self.state.mappings, [])

    def test_the_site_list_state_and_its_choices(self):
        out = self.act("site-list")
        self.assertTrue(out["on"])
        self.assertEqual(out["every"], 24)
        self.assertEqual(out["state"], "ok")
        self.assertEqual(out["failed_count"], 1)
        self.assertIn({"value": 24, "label": "Once a day"}, out["choices"])

    def test_the_site_list_saves_and_keeps_reelixs_source(self):
        out = self.act("site-list-save", {"on": True, "every": "168"})
        self.assertEqual(out["every"], 168)
        self.assertEqual(out["done"], "The site list updates once a week")
        self.assertEqual(self.state.definitions["source_url"], "https://example.invalid/indexers.tar.gz")
        out = self.act("site-list-save", {"on": False, "every": 168})
        self.assertFalse(out["on"])
        with self.assertRaises(ValueError):
            self.act("site-list-save", {"on": True, "every": 9999})

    def test_update_now_starts_reelixs_sync(self):
        out = self.act("site-list-sync")
        self.assertTrue(out["syncing"])
        self.assertEqual(out["state"], "updating")
        self.assertIn(("POST", "/indexers/definitions/sync"), self.state.calls)

    def test_an_unknown_action_is_refused(self):
        with self.assertRaises(ValueError):
            self.act("drop-everything")


if __name__ == "__main__":
    unittest.main()
