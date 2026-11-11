"""What is left to set up (DASH-185)."""
import os
import tempfile
import unittest
from unittest import mock

from starboard import setup_left, stack


class SetupLeft(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.makedirs(stack.folder(self.tmp.name))
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml"), "w") as f:
            f.write("services:\n" + "".join(f"  {a}:\n    container_name: {a}\n" for a in ("reelix", "nzbget", "jellyfin")))
        setup_left.forget()

    def cfg(self, *services):
        return mock.Mock(data={"services": list(services)})

    def test_reelix_health_says_what_is_missing(self):
        health = [{"source": "indexers", "level": "error", "message": "No indexers are enabled; Reelix cannot find releases"}]
        with mock.patch.object(setup_left, "_reelix_health", return_value=health), \
                mock.patch.object(setup_left, "_usenet_server", return_value=False):
            items = {i["key"]: i["done"] for i in setup_left.items(self.cfg(), self.tmp.name)}
        self.assertEqual(items, {"sites": False, "download": True, "tmdb": False, "usenet": False, "jellyfin": False, "mediaservers": False})

    def test_what_cannot_be_asked_is_left_out_and_records_count(self):
        setup_left.record(self.tmp.name, tmdb=True, media_servers=True)
        with mock.patch.object(setup_left, "_reelix_health", return_value=None), \
                mock.patch.object(setup_left, "_usenet_server", return_value=None):
            out = setup_left.left(self.cfg({"type": "jellyfin", "api_key": "k", "name": "Jellyfin", "url": "http://x"}), self.tmp.name)
        self.assertEqual({i["key"] for i in out["items"]}, {"tmdb", "jellyfin", "mediaservers"})
        self.assertEqual(out["left"], 0)


    def test_radio_step_follows_what_reelix_reads(self):
        # Owner, 10 November 2026: radio connected outside the set-up wizard stayed on Still to set up.
        from starboard import radio_import
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml"), "a") as f:
            f.write("  audiobookshelf:\n    container_name: audiobookshelf\n")
        with mock.patch.object(setup_left, "_reelix_health", return_value=None), \
                mock.patch.object(setup_left, "_usenet_server", return_value=None):
            for status, done in (({"connected": True, "waiting": 0}, True), ({"connected": False, "waiting": 0}, False)):
                with mock.patch.object(radio_import, "status", return_value=status):
                    radio = [i for i in setup_left.items(self.cfg(), self.tmp.name) if i["key"].startswith("radio")]
                self.assertEqual([(i["key"], i["done"]) for i in radio], [("radio", done)])

    def test_guided_steps_go_when_done(self):
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml"), "a") as f:
            f.write("  wizarr:\n    container_name: wizarr\n")
        tdarr = {"type": "link", "icon": "wizarr", "name": "Wizarr", "url": "http://127.0.0.1:5690", "link": "http://wizarr.example:5690"}
        with mock.patch.object(setup_left, "_reelix_health", return_value=None), \
                mock.patch.object(setup_left, "_usenet_server", return_value=None):
            item = next(i for i in setup_left.items(self.cfg(tdarr), self.tmp.name) if i["key"] == "wizarr")
            self.assertEqual((item["href"], item["done"], item["guided"]), ("http://wizarr.example:5690", False, True))
            setup_left.mark_done(self.tmp.name, "wizarr")
            self.assertTrue(next(i for i in setup_left.items(self.cfg(tdarr), self.tmp.name) if i["key"] == "wizarr")["done"])
        with self.assertRaises(ValueError):
            setup_left.mark_done(self.tmp.name, "reelix")


    def test_ignore_takes_an_item_off_what_is_left_and_bring_back_returns_it(self):
        with mock.patch.object(setup_left, "_reelix_health", return_value=None), \
                mock.patch.object(setup_left, "_usenet_server", return_value=None):
            before = setup_left.left(self.cfg(), self.tmp.name)["left"]
            setup_left.ignore(self.tmp.name, "tmdb")
            setup_left.forget()
            out = setup_left.left(self.cfg(), self.tmp.name)
            self.assertEqual(out["left"], before - 1)
            self.assertTrue(next(i for i in out["items"] if i["key"] == "tmdb")["ignored"])
            setup_left.ignore(self.tmp.name, "tmdb", on=False)
            setup_left.forget()
            self.assertEqual(setup_left.left(self.cfg(), self.tmp.name)["left"], before)
        with self.assertRaises(ValueError):
            setup_left.ignore(self.tmp.name, "")


if __name__ == "__main__":
    unittest.main()


class PanelPagesTest(unittest.TestCase):
    """Every Starboard step in Still to set up opens its page in the slide-out, so its page must be allowed there."""

    def test_every_step_page_may_open_in_the_slide_out(self):
        import re
        from starboard import setup_left
        src = open(setup_left.__file__).read()
        pages = set(re.findall(r'"href": f?"(/[a-z-]+(?:\{[^}]+\}[a-z-]*)?\.html)', src))
        pages = {p.replace("{'films' if tab == 'films' else 'tv'}", x) for p in pages for x in ("films", "tv")} if pages else pages
        pages = {p for p in pages if "{" not in p and p != "/index.html"}
        self.assertTrue(pages)
        self.assertEqual(pages - setup_left.PANEL_PAGES, set())
