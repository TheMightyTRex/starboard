"""Fallback posters for an app with no picture route (DASH-65): the item's image addresses, then TMDB through the
app's lookup, then nothing (the page draws its placeholder), each at the image site's small size."""

import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import picture_cache, posters

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


class NoCovers(BaseHTTPRequestHandler):
    """An app with films and series but no mediacover route, as Reelix's Radarr and Sonarr addresses."""
    asked = []
    items = {}
    lookups = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        NoCovers.asked.append(self.path)
        if url.path == "/own/poster.jpg":
            return self.reply(JPEG + b"own", "image/jpeg")
        if "/mediacover/" in url.path:
            return self.reply(b"{}", "application/json", 404)
        if "/lookup" in url.path:
            return self.reply(json.dumps(NoCovers.lookups.get(url.query, [])).encode(), "application/json")
        found = NoCovers.items.get(url.path)
        if found is None:
            return self.reply(b"{}", "application/json", 404)
        self.reply(json.dumps(found).encode(), "application/json")

    def reply(self, raw, kind, code=200):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Answer:
    def __init__(self, data, kind="image/jpeg"):
        self.data, self.headers = data, {"Content-Type": kind}

    def read(self, n=-1):
        return self.data[:n] if n and n > 0 else self.data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class PosterFallbackTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), NoCovers)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.films = {"id": "films", "name": "Films", "type": "radarr", "url": base, "api_key": "k"}
        self.tv = {"id": "tv", "name": "TV", "type": "sonarr", "url": base, "api_key": "k"}
        NoCovers.asked, NoCovers.items, NoCovers.lookups = [], {}, {}
        posters._missing.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = os.path.join(self.tmp.name, "posters")
        self.sites = []  # every address asked of an image site

        def image_site(req, timeout=0):
            self.sites.append(req.full_url)
            return Answer(JPEG + req.full_url.encode())
        from starboard import library
        patch = mock.patch.object(library._image_opener, "open", image_site)
        patch.start()
        self.addCleanup(patch.stop)

    def test_the_items_image_address_at_the_small_size(self):
        NoCovers.items["/api/v3/movie/5"] = {"id": 5, "tmdbId": 603, "images": [
            {"coverType": "fanart", "remoteUrl": "https://image.tmdb.org/t/p/original/fan.jpg"},
            {"coverType": "poster", "url": "https://image.tmdb.org/t/p/original/abc.jpg", "remoteUrl": "https://image.tmdb.org/t/p/original/abc.jpg"}]}
        data, kind = posters.get(self.films, "movie", "5", self.folder)
        self.assertEqual(self.sites, ["https://image.tmdb.org/t/p/w185/abc.jpg"])  # small, and the poster, not the fan art
        self.assertTrue(data.startswith(JPEG))
        self.assertEqual(kind, "image/jpeg")
        self.assertFalse([a for a in NoCovers.asked if "lookup" in a])  # TMDB is not asked when the item has a picture
        NoCovers.asked.clear()
        self.assertEqual(posters.get(self.films, "movie", "5", self.folder)[0], data)  # kept: nothing is asked again
        self.assertEqual((NoCovers.asked, len(self.sites)), ([], 1))

    def test_the_apps_own_copy_when_the_item_names_one(self):
        NoCovers.items["/api/v3/series/8"] = {"id": 8, "images": [{"coverType": "poster", "url": "/own/poster.jpg"}]}
        data, _ = posters.get(self.tv, "series", "8", self.folder)
        self.assertEqual(data, JPEG + b"own")
        self.assertEqual(self.sites, [])

    def test_an_address_on_another_site_is_never_fetched(self):
        NoCovers.items["/api/v3/movie/6"] = {"id": 6, "images": [
            {"coverType": "poster", "remoteUrl": "https://pictures.example/poster.jpg", "url": "//pictures.example/poster.jpg"},
            {"coverType": "poster", "remoteUrl": "http://image.tmdb.org/t/p/original/plain.jpg"}]}
        self.assertIsNone(posters.get(self.films, "movie", "6", self.folder))
        self.assertEqual(self.sites, [])

    def test_then_tmdb_through_the_apps_lookup(self):
        NoCovers.items["/api/v3/movie/7"] = {"id": 7, "tmdbId": 550, "images": []}
        NoCovers.lookups["tmdbId=550"] = {"tmdbId": 550, "remotePoster": "https://image.tmdb.org/t/p/original/fight.jpg"}
        data, _ = posters.get(self.films, "movie", "7", self.folder)
        self.assertEqual(self.sites, ["https://image.tmdb.org/t/p/w185/fight.jpg"])
        self.assertTrue(data.endswith(b"w185/fight.jpg"))
        NoCovers.items["/api/v3/series/9"] = {"id": 9, "tvdbId": 121361, "images": []}
        NoCovers.lookups["term=tvdb%3A121361"] = [{"images": [{"coverType": "poster", "remoteUrl": "https://image.tmdb.org/t/p/w500/thrones.jpg"}]}]
        posters.get(self.tv, "series", "9", self.folder)
        self.assertEqual(self.sites[-1], "https://image.tmdb.org/t/p/w185/thrones.jpg")

    def test_with_no_picture_anywhere_the_app_is_left_alone_for_an_hour(self):
        NoCovers.items["/api/v3/movie/4"] = {"id": 4, "tmdbId": 1, "images": []}
        self.assertIsNone(posters.get(self.films, "movie", "4", self.folder))
        self.assertTrue(NoCovers.asked)
        NoCovers.asked.clear()
        self.assertIsNone(posters.get(self.films, "movie", "4", self.folder))
        self.assertEqual(NoCovers.asked, [])  # the page shows its placeholder; nothing is asked
        picture_cache.clear(self.tmp.name)  # Clear the picture cache looks again
        posters.get(self.films, "movie", "4", self.folder)
        self.assertTrue(NoCovers.asked)

    def test_a_picture_over_the_size_limit_is_not_kept(self):
        NoCovers.items["/api/v3/movie/3"] = {"id": 3, "images": [{"coverType": "poster", "remoteUrl": "https://image.tmdb.org/t/p/original/big.jpg"}]}
        from starboard import library
        with mock.patch.object(library._image_opener, "open", lambda req, timeout=0: Answer(b"1" * (posters.MAX_BYTES + 1))):
            self.assertIsNone(posters.get(self.films, "movie", "3", self.folder))
        self.assertEqual(os.listdir(self.folder), [])

    def test_the_memory_of_missing_pictures_stays_small(self):
        for n in range(posters.MISSING_MAX + 5):
            posters._missing[f"p{n}"] = 0
        NoCovers.items["/api/v3/movie/2"] = {"id": 2, "images": []}
        posters.get(self.films, "movie", "2", self.folder)
        self.assertLessEqual(len(posters._missing), posters.MISSING_MAX)


if __name__ == "__main__":
    unittest.main()
