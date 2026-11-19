"""Plug-in API 1.15, DASH-406: the permission library:holding with the media:holding volume (the media folder, read
and write, so a move into media/.holding is a rename), said plainly before install, and the restore action a custom
screen's row may offer, drawn as Put back."""
import copy
import json
import os
import unittest

from starboard import plugin_custom, plugins
from tests.test_plugins import ON_DEMAND


def cleanup_manifest(vol="media:holding", perm=True, user="media"):
    m = copy.deepcopy(ON_DEMAND)
    m["permissions"] = ["jellyfin:key"] + (["library:holding"] if perm else [])
    m["containers"] = m["containers"][:1]
    m["containers"][0].pop("network")
    m["resources"] = {"main": {"memory": 40}}
    m["containers"][0]["volumes"] = ["data", vol]
    if user:
        m["containers"][0]["user"] = user
    return m


class Permission(unittest.TestCase):
    def test_the_version(self):
        self.assertEqual(plugins.API_VERSION, "1.16.0")
        self.assertTrue(plugins._range_ok(">=1.15 <2.0"))

    def test_only_with_the_permission(self):
        self.assertEqual(plugins.check(cleanup_manifest(), dev=True), [])
        self.assertIn("containers[0]: media:holding needs the permission library:holding",
                      plugins.check(cleanup_manifest(perm=False), dev=True))
        self.assertEqual(plugins.PERMISSIONS["library:holding"][1], "high")
        self.assertIsNone(plugins.PERMISSIONS["library:holding"][2])  # no API scope: it is a folder, not a route
        self.assertNotIn("holding", plugins.key_scopes(cleanup_manifest()))

    def test_it_may_run_as_the_media_folders_owner(self):
        self.assertEqual(plugins.check(cleanup_manifest(), dev=True), [])
        no_folder = cleanup_manifest(vol="media:ro")
        no_folder["permissions"].append("media:read")
        self.assertIn("containers[0]: user media is only for a container that mounts media/<one folder>, media:holding or jellyfin-metadata",
                      plugins.check(no_folder, dev=True))

    def test_other_names_stay_refused(self):
        for bad in ("media", "media:rw", "media:holding:ro", "holding", "media/.holding/../x"):
            problems = plugins.check(cleanup_manifest(vol=bad), dev=True)
            self.assertTrue(any("volumes may be" in p and "media:holding" in p for p in problems), (bad, problems))

    def test_the_warning_says_it_plainly(self):
        w = plugins.install_warning(cleanup_manifest())
        self.assertEqual(w["risk"], "high")
        self.assertIn("Every file in your media folder", w["see"])
        said = [c for c in w["change"] if c.startswith("Your media folder: it can move films and series into the holding folder")]
        self.assertEqual(len(said), 1)
        self.assertIn("media/.holding", said[0])
        self.assertIn("add only a plug-in you trust", said[0])
        # the permission without the volume changes nothing, so it is not said
        m = cleanup_manifest()
        m["containers"][0]["volumes"] = ["data"]
        m["containers"][0].pop("user")
        self.assertFalse(any("holding folder" in c for c in plugins.install_warning(m)["change"]))

    def test_mounted_read_and_write_at_media(self):
        text = plugins.compose(cleanup_manifest(), "/srv/p", "/srv/data/media", media_user="1000:1000")
        self.assertIn('"/srv/data/media:/media"', text)
        self.assertNotIn('"/srv/data/media:/media:ro"', text)
        self.assertIn('user: "1000:1000"', text)
        self.assertIn('/run/starboard:ro"', text)

    def test_a_folder_setting_is_chosen_inside_it(self):
        self.assertEqual(plugins.media_mounts(cleanup_manifest()), ["/media"])
        m = cleanup_manifest()
        m["settings"].append({"key": "where", "label": "Where", "type": "folder"})
        self.assertEqual(plugins.check(m, dev=True), [])

    def test_the_schema_lists_it(self):
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "starboard", "plugin-manifest.schema.json")
        with open(here) as f:
            schema = json.load(f)
        self.assertIn("library:holding", schema["properties"]["permissions"]["items"]["enum"])


class PutBack(unittest.TestCase):
    def screen(self, actions):
        return {"type": "list", "title": "Holding folder", "items": [{"id": "h1", "title": "A made-up film (2001)", "actions": actions}]}

    def test_restore_is_kept_and_others_dropped(self):
        out = plugin_custom.clean(self.screen(["restore", "delete", "toggle"]))
        self.assertEqual(out["items"][0]["actions"], ["restore", "toggle"])

    def test_restore_reaches_the_plugin(self):
        self.assertIn("restore", plugin_custom.ACTIONS)

    def test_the_page_draws_it_as_put_back(self):
        here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "js", "plugins.js")
        with open(here, encoding="utf-8") as f:
            js = f.read()
        self.assertIn('restore: ["Put back", "undo-2"]', js)
        self.assertIn('a === "test" || a === "toggle" || a === "restore"', js)


if __name__ == "__main__":
    unittest.main()
