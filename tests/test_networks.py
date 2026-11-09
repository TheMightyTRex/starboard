"""TV network logos (DASH-264)."""
import tempfile
import threading
import unittest
from unittest import mock

from starboard import networks


class Logos(unittest.TestCase):
    def test_one_lookup_per_network_kept_on_disk(self):
        index = {"items": [{"i": 1, "g": ["BBC One"]}, {"i": 2, "g": ["BBC One"]}, {"i": 3, "g": ["Netflix"]}]}

        def fake(reelix, path, params=None, method="GET", body=None, timeout=None):
            if path.startswith("/series/"):
                return {"tmdb_id": 100 + int(path.rsplit("/", 1)[1])}
            if path == "/media/tv/101":
                return {"companies": [{"name": "BBC One", "logo_url": "https://image.tmdb.org/t/p/w300/bbc.png"}]}
            return {"companies": [{"name": "Netflix", "logo_url": "http://elsewhere.example/n.png"}]}
        with tempfile.TemporaryDirectory() as d, mock.patch("starboard.services._api", side_effect=fake) as api:
            done = threading.Event()
            real = threading.Thread

            def run_now(target=None, name=None, daemon=None):
                t = real(target=lambda: (target(), done.set()), daemon=True)
                return t
            with mock.patch("starboard.networks.threading.Thread", side_effect=run_now):
                networks.refresh(d, {}, index)
            done.wait(5)
            self.assertEqual(networks.logo_of(d, "bbc one"), "https://image.tmdb.org/t/p/w300/bbc.png")
            self.assertEqual(networks.logo_of(d, "Netflix"), "")  # only TMDB's own image address is kept
            self.assertEqual(sum(1 for c in api.call_args_list if c[0][1].startswith("/series/")), 2)


if __name__ == "__main__":
    unittest.main()
