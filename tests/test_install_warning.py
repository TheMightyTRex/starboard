"""The install warning (owner, 12 November 2026) and plug-in menu items (shown only once the plug-in is added)."""
import json
import os
import tempfile
import unittest

from starboard import plugins, plugins_admin


def manifest(**kw):
    m = {"manifest_version": 1, "id": "example", "name": "Example", "version": "1.0.0", "description": "x", "author": "a",
         "licence": "MIT", "homepage": "https://example.org", "support_url": "https://example.org", "starboard_api": ">=1.0 <2.0",
         "permissions": [], "containers": [{"name": "main", "image": "ghcr.io/a/b:1", "port": 8080}]}
    m.update(kw)
    return m


class Warning(unittest.TestCase):
    def test_nothing_asked(self):
        w = plugins.install_warning(manifest())
        self.assertEqual(w["see"], [])
        self.assertEqual(w["reach"], ["Only Starboard: it has no way out to your network or the internet"])
        self.assertIn("data/plugins/example", w["change"][0])
        self.assertEqual(w["risk"], "low")
        self.assertIn("128 MB", w["runs"][0])

    def test_everything_said(self):
        m = manifest(permissions=["media:read", "jellyfin:key", "network:lan", "downloads:read"],
                     containers=[{"name": "main", "image": "ghcr.io/a/b:1", "volumes": ["media:ro", "media/podcasts"], "network": "lan"}],
                     resources={"main": {"memory": 256, "cpus": 0.5}})
        w = plugins.install_warning(m)
        self.assertEqual(w["risk"], "high")
        self.assertIn("Every file in your media folder (read only)", w["see"])
        self.assertTrue(any("podcasts" in x for x in w["change"]))
        self.assertTrue(any("Jellyfin" in x for x in w["change"]))
        self.assertIn("internet", w["reach"][0])
        self.assertIn("256 MB", w["runs"][0])

    def test_styles_only(self):
        w = plugins.install_warning(manifest(containers=[], permissions=["appearance:styles"]))
        self.assertEqual((w["reach"], w["runs"]), ([], []))
        self.assertTrue(w["change"][0].startswith("How Starboard looks"))

    def test_in_summary(self):
        self.assertIn("warning", plugins_admin.summary(manifest()))


class Added(unittest.TestCase):
    def test_only_with_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = plugins_admin.root(d)
            for pid, has in (("on-demand", True), ("half-done", False), (".removed", True)):
                os.makedirs(os.path.join(root, pid))
                if has:
                    with open(os.path.join(root, pid, "manifest.json"), "w") as f:
                        json.dump({}, f)
            self.assertEqual(plugins_admin.added(d), ["on-demand"])
            self.assertEqual(plugins_admin.added(os.path.join(d, "none")), [])


if __name__ == "__main__":
    unittest.main()
