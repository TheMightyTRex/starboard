"""Search the sites directly (DASH-213): Reelix's free search with the manager key, results without their links, and Get
this one from a token, as Reelix's raw grab."""
import unittest
from unittest import mock

from starboard import reelix_search, services

REELIX = [{"id": "rx", "name": "Reelix", "type": "link", "icon": "reelix", "enabled": True, "url": "http://reelix:7700", "api_key": "made-up-key"}]
ANSWER = {"releases": [
    {"guid": "a", "title": "Example.2160p", "protocol": "torrent", "indexer_id": 4, "indexer": "Example", "size": 10, "seeders": 3,
     "publish_date": "2026-11-01T00:00:00Z", "download_url": "https://site.invalid/get?passkey=secret", "info_url": "javascript:alert(1)",
     "indexer_flags": ["freeleech", "made-up"]},
    {"guid": "b", "title": "Example.1080p", "protocol": "usenet", "indexer_id": 5, "indexer": "Usenet", "magnet_url": None, "download_url": None},
    {"title": "no guid, left out", "indexer_id": 5}],
    "indexers": [{"indexer_id": 4, "name": "Example", "count": 1, "elapsed_ms": 1500, "error": None},
                 {"indexer_id": 6, "name": "Slow", "count": 0, "elapsed_ms": 30000, "error": "timed out"}]}


class Search(unittest.TestCase):
    def setUp(self):
        reelix_search._kept.clear()
        self.calls = []

        def fake(service, path, params=None, method="GET", body=None, timeout=None):
            self.calls.append((method, path, params, body))
            if path == "/indexers/search":
                return ANSWER
            return {"queue_id": 9, "download_client": "qBittorrent", "download_id": "x"}
        self.patch = mock.patch.object(services, "_api", side_effect=fake)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_search_asks_reelix_with_the_kind_and_keeps_links_on_the_server(self):
        out = reelix_search.search(REELIX, "  Blue   Planet ", "films")
        self.assertEqual(self.calls[0][2], {"q": "Blue Planet", "kind": "movie", "limit": 100})
        self.assertEqual([r["title"] for r in out["results"]], ["Example.2160p", "Example.1080p"])
        self.assertNotIn("secret", str(out))
        first = out["results"][0]
        self.assertEqual(first["flags"], ["Free to download"])
        self.assertEqual(first["info_url"], "", "only http and https links are passed on")
        self.assertTrue(first["can_get"])
        self.assertFalse(out["results"][1]["can_get"])
        self.assertEqual(out["sites"][1], {"id": 6, "name": "Slow", "count": 0, "seconds": 30.0, "error": "timed out"})

    def test_words_and_kinds_are_checked_first(self):
        for q, kind in (("a", "all"), ("x" * 201, "all"), ("dune", "games")):
            with self.assertRaises(ValueError):
                reelix_search.search(REELIX, q, kind)
        with self.assertRaises(ValueError):
            reelix_search.search([], "dune")
        self.assertEqual(self.calls, [])

    def test_get_this_one_sends_the_kept_link_as_a_raw_grab(self):
        out = reelix_search.search(REELIX, "dune")
        got = reelix_search.grab(REELIX, out["token"], 0)
        self.assertEqual(got["done"], "Sent to qBittorrent")
        method, path, _, body = self.calls[-1]
        self.assertEqual((method, path), ("POST", "/releases/grab"))
        self.assertEqual(body, {"guid": "a", "indexer_id": 4, "download_url": "https://site.invalid/get?passkey=secret", "title": "Example.2160p"})

    def test_get_this_one_needs_a_live_token_and_a_link(self):
        out = reelix_search.search(REELIX, "dune")
        with self.assertRaises(ValueError):
            reelix_search.grab(REELIX, "not-a-token", 0)
        with self.assertRaises(ValueError):
            reelix_search.grab(REELIX, out["token"], 1)  # the site gave no link
        with self.assertRaises(ValueError):
            reelix_search.grab(REELIX, out["token"], 7)

    def test_only_a_few_searches_are_kept(self):
        tokens = [reelix_search.search(REELIX, f"dune {i}")["token"] for i in range(reelix_search.KEEP_AT_MOST + 2)]
        self.assertLessEqual(len(reelix_search._kept), reelix_search.KEEP_AT_MOST)
        with self.assertRaises(ValueError):
            reelix_search.grab(REELIX, tokens[0], 0)
        reelix_search.grab(REELIX, tokens[-1], 0)


if __name__ == "__main__":
    unittest.main()
