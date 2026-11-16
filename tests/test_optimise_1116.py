"""Optimisation review, 16 November 2026: reads that ran on every page, and every minute at idle, are lighter,
and say the same as before. A logo's hash is kept while the file is unchanged; code that needs only which plug-ins are
added and which are on reads their manifest and state files, not the whole listing; Docker is asked about each image
once, not on every visit to the Apps and Updates pages."""
import builtins
import os
import tempfile
import unittest
from unittest import mock

from starboard import plugin_cards, plugin_life, plugin_logo, plugin_watch, plugins_admin as pa
from tests.test_plugins import ON_DEMAND

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8"/></svg>'


class LogoHashKept(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        plugin_logo._hashes.clear()

    def opened(self, folder):
        """kept(folder), and how many times it opened a logo file."""
        real, seen = builtins.open, []

        def counting(path, *a, **k):
            if str(path).startswith(folder):
                seen.append(path)
            return real(path, *a, **k)
        with mock.patch("builtins.open", counting):
            return plugin_logo.kept(folder), len(seen)

    def test_the_hash_is_read_once_and_again_only_when_the_logo_changes(self):
        d = self.tmp.name
        plugin_logo.save(d, SVG, "image/svg+xml")
        (path, kind, first), opened = self.opened(d)
        self.assertEqual((kind, opened), ("image/svg+xml", 1))
        again, opened = self.opened(d)
        self.assertEqual((again[2], opened), (first, 0))  # unchanged: nothing opened
        # A new logo of the same size, written in place: the change time moves, so the new hash shows at once.
        plugin_logo.save(d, SVG.replace(b"rect", b"Rect"), "image/svg+xml")
        newer, opened = self.opened(d)
        self.assertEqual(opened, 1)
        self.assertNotEqual(newer[2], first)
        # Copied over by an update or a roll back, without save(): still seen.
        tmp = os.path.join(d, "other.svg")
        with open(tmp, "wb") as f:
            f.write(SVG)
        os.replace(tmp, path)
        self.assertEqual(plugin_logo.kept(d)[2], first)

    def test_a_png_after_an_svg_and_no_logo_at_all(self):
        d = self.tmp.name
        self.assertIsNone(plugin_logo.kept(d))
        plugin_logo.save(d, SVG, "image/svg+xml")
        self.assertEqual(plugin_logo.kept(d)[1], "image/svg+xml")
        os.replace(os.path.join(d, "logo.svg"), os.path.join(d, "logo.svg.old"))
        self.assertIsNone(plugin_logo.kept(d))


class BasicsMatchTheListing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/starboard/data/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)
        d = self.tmp.name
        pa.install(d, ON_DEMAND, "/srv/media")
        second = {k: v for k, v in ON_DEMAND.items() if k not in ("cards", "styles", "jobs")}
        second.update(id="line-speed", name="Line speed", version="2.1.0")
        pa.install(d, second, "/srv/media")
        pa.set_state(d, "line-speed", "enabled")
        os.makedirs(os.path.join(pa.root(d), ".hidden"))  # never listed
        os.makedirs(os.path.join(pa.root(d), "half-made"))  # no manifest: never listed

    def test_basics_say_what_the_listing_says(self):
        d = self.tmp.name
        full = [{k: p[k] for k in ("id", "name", "version", "state", "builtin")} for p in pa.listing(d)]
        self.assertEqual(pa.basics(d), full)
        self.assertEqual([p["id"] for p in full], ["line-speed", "on-demand"])
        self.assertEqual({p["id"]: p["state"] for p in full}, {"line-speed": "enabled", "on-demand": "installed"})

    def test_pages_and_background_checks_never_build_the_whole_listing(self):
        d = self.tmp.name
        pa.set_state(d, "on-demand", "enabled")
        with mock.patch.object(pa, "listing", side_effect=AssertionError("the whole listing was built")):
            self.assertEqual([c["id"] for c in plugin_cards.available(d)], ["plugin:on-demand:titles"])
            pa.styles(d)
            pa.styles_css(d)
            plugin_life.jobs(d)
            plugin_life.listened(d)
            plugin_life.updates_known(d)
            plugin_watch.wanted(d)

    def test_a_card_keeps_its_plug_ins_logo(self):
        d = self.tmp.name
        pa.set_state(d, "on-demand", "enabled")
        plugin_logo.save(pa.folder(d, "on-demand"), SVG, "image/svg+xml")
        m = pa._read(os.path.join(pa.folder(d, "on-demand"), "manifest.json"))
        m["logo"] = {"file": "logo.svg", "alt": "On demand"}
        pa._write(os.path.join(pa.folder(d, "on-demand"), "manifest.json"), m)
        card = plugin_cards.available(d)[0]
        self.assertEqual(card["logo"], pa.logo_info(d, "on-demand", m))
        self.assertTrue(card["logo"]["url"].startswith("/api/plugins/on-demand/logo?v="))


if __name__ == "__main__":
    unittest.main()


class ImageDetailsKept(unittest.TestCase):
    """The Apps and Updates pages: Docker is asked about each image once, not on every visit."""

    def setUp(self):
        from starboard import containers
        self.c = containers
        containers._images.clear()
        self.addCleanup(containers._images.clear)
        self.calls = []
        self.listed = [{"Id": "1", "Names": ["/sonarr"], "Image": "lscr.io/linuxserver/sonarr:latest", "ImageID": "sha256:a",
                        "State": "running", "Status": "Up", "Labels": {}},
                       {"Id": "2", "Names": ["/radarr"], "Image": "lscr.io/linuxserver/radarr:5.1", "ImageID": "sha256:b",
                        "State": "running", "Status": "Up", "Labels": {}}]
        self.digest = {"sha256:a": "lscr.io/linuxserver/sonarr@sha256:111", "sha256:b": "lscr.io/linuxserver/radarr@sha256:222"}

        def docker(method, path, body=None, raw=False, timeout=30):
            self.calls.append(path)
            if path.startswith("/containers/json"):
                return self.listed
            image = path.split("/")[2].replace("%3A", ":")
            return {"Config": {"Labels": {"org.opencontainers.image.version": "4.0." + image[-1]}, "Env": ["A=1"], "Cmd": ["x"]},
                    "Created": "2026-11-01T00:00:00Z", "RepoDigests": [self.digest[image]], "Size": 1}
        p = mock.patch.object(containers, "docker", side_effect=docker)
        p.start()
        self.addCleanup(p.stop)

    def test_each_image_is_asked_about_once_and_says_the_same(self):
        first = self.c.containers()
        self.assertEqual(len(self.calls), 3)
        self.calls.clear()
        again = self.c.containers()
        self.assertEqual(self.calls, ["/containers/json?all=1"])
        self.assertEqual(again, first)
        self.assertEqual((first[0]["version"], first[0]["created"], first[0]["digests"]),
                         ("4.0.a", "2026-11-01", ["lscr.io/linuxserver/sonarr@sha256:111"]))

    def test_the_update_check_reads_the_digests_fresh(self):
        self.c.containers()
        self.digest["sha256:a"] = "lscr.io/linuxserver/sonarr@sha256:999"
        self.calls.clear()
        fresh = self.c.containers(fresh=True)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(fresh[0]["digests"], ["lscr.io/linuxserver/sonarr@sha256:999"])
        self.calls.clear()
        with mock.patch.object(self.c, "_check_one", side_effect=lambda c: {}):
            self.c.check([])
        self.assertEqual(sum(p.startswith("/images/") for p in self.calls), 2)  # Look for updates asks Docker again

    def test_an_image_no_longer_used_is_forgotten(self):
        self.c.containers()
        self.listed.pop()
        self.c.containers()
        self.assertEqual(set(self.c._images), {"sha256:a"})
