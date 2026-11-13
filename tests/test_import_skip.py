"""Optimisation review (owner, 13 November 2026): the hourly watch history import read every film and episode from
Jellyfin each hour (on the owner's server 51,000 items, about 8 minutes of Jellyfin's time and 164 MB at Starboard's
peak) to find nothing new. It now asks for Jellyfin's newest item first, reads everything only when something it
depends on changed or once a day, and works through a page at a time (DASH-397)."""

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import migrate


class Jellyfin(BaseHTTPRequestHandler):
    newest = "m2"
    full_reads = 0
    pages = []
    played = []
    items = []

    def log_message(self, *a):
        pass

    def reply(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        if u.path == "/Users":
            return self.reply([{"Name": "alex", "Id": "u1"}])
        if u.path == "/Items" and "ids" in q:
            return self.reply({"Items": [{"Id": i, "ProviderIds": {"Tvdb": "81189"}} for i in q["ids"].split(",")]})
        if u.path == "/Items" and q.get("sortBy") == "DateCreated":
            return self.reply({"Items": [{"Id": Jellyfin.newest}], "TotalRecordCount": len(Jellyfin.items)})
        if u.path == "/Items":
            start, limit = int(q["StartIndex"]), int(q["Limit"])
            if start == 0:
                Jellyfin.full_reads += 1
            Jellyfin.pages.append(start)
            return self.reply({"Items": Jellyfin.items[start:start + limit], "TotalRecordCount": len(Jellyfin.items)})
        return self.reply({})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/UserPlayedItems/"):
            Jellyfin.played.append(path.rsplit("/", 1)[1])
        return self.reply({})


class ImportSkip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Jellyfin)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.services = [{"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": f"http://127.0.0.1:{cls.server.server_port}", "api_key": "k"}]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        Jellyfin.newest, Jellyfin.full_reads, Jellyfin.pages, Jellyfin.played = "m2", 0, [], []
        # 2,500 episodes of one show and two films: three pages of 1,000
        Jellyfin.items = ([{"Id": f"e{n}", "Type": "Episode", "SeriesId": "s1", "ParentIndexNumber": 1, "IndexNumber": n, "UserData": {}} for n in range(2500)]
                          + [{"Id": "m1", "Type": "Movie", "ProviderIds": {"Tmdb": "603"}, "UserData": {}}])
        src = os.path.join(self.dir, "old.json")
        with open(src, "w") as f:
            json.dump({"accounts": {"Alex": [
                {"type": "movie", "watched": True, "ids": {"tmdb": "603"}},
                {"type": "movie", "watched": True, "ids": {"tmdb": "999"}},  # not in Jellyfin yet
                {"type": "episode", "watched": True, "season": 1, "episode": 2400, "ids": {"tvdb": "81189"}}]}}, f)
        migrate.save_history(self.dir, "History file", migrate.read_file(src))
        migrate.set_mapping(self.dir, {"Alex": "alex"})

    def test_pages_then_nothing_new_then_something_new(self):
        said = migrate.apply(self.dir, self.services)
        self.assertEqual(said, "Marked 2 as watched and set 0 resume points; 1 not in Jellyfin yet")
        self.assertEqual(sorted(Jellyfin.played), ["e2400", "m1"])
        self.assertEqual(Jellyfin.pages, [0, 1000, 2000])  # a page at a time
        # Nothing new: one small request, the same words, the result kept
        self.assertEqual(migrate.apply(self.dir, self.services), "Marked 0 as watched and set 0 resume points; 1 not in Jellyfin yet")
        self.assertEqual(Jellyfin.full_reads, 1)
        last = migrate.status(self.dir, self.services)["last"]
        self.assertEqual(last["unmatched_count"], 1)
        # A new film arrives: everything is read again and it is applied
        Jellyfin.items.append({"Id": "m9", "Type": "Movie", "ProviderIds": {"Tmdb": "999"}, "UserData": {}})
        Jellyfin.newest = "m9"
        self.assertEqual(migrate.apply(self.dir, self.services), "Marked 1 as watched and set 0 resume points; 0 not in Jellyfin yet")
        self.assertEqual(Jellyfin.full_reads, 2)

    def test_a_full_read_at_least_once_a_day_and_after_a_new_mapping(self):
        migrate.apply(self.dir, self.services)
        with mock.patch.object(migrate, "time") as clock:
            clock.time.return_value = time.time() + migrate.FULL_EVERY + 1
            migrate.apply(self.dir, self.services)
        self.assertEqual(Jellyfin.full_reads, 2)
        time.sleep(0.01)
        migrate.set_mapping(self.dir, {"Alex": "alex"})  # saved again: the mapping file changed
        migrate.apply(self.dir, self.services)
        self.assertEqual(Jellyfin.full_reads, 3)


if __name__ == "__main__":
    unittest.main()
