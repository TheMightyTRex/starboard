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


if __name__ == "__main__":
    unittest.main()
