"""Listening progress into Audiobookshelf: reading, matching, applying with a key that acts as each person."""

import json
import os
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from starboard import config, listening

ADMIN = "admin-key"


class FakeAbs(BaseHTTPRequestHandler):
    """Audiobookshelf with two users and three books. Keys made for a user act as that user."""
    books = [
        {"id": "li-1", "path": "/audiobooks/Ursula K. Le Guin/A Wizard of Earthsea",
         "media": {"duration": 30000, "metadata": {"title": "A Wizard of Earthsea", "authorName": "Ursula K. Le Guin", "asin": "B00ASIN001"}}},
        {"id": "li-2", "path": "/audiobooks/Terry Pratchett/Mort",
         "media": {"duration": 36000, "metadata": {"title": "Mort", "authorName": "Terry Pratchett", "isbn": "978-0-552-13106-1"}}},
        {"id": "li-3", "path": "/audiobooks/Anne Example/Sea Stories",
         "media": {"duration": 10000, "metadata": {"title": "Sea Stories: A Collection", "authorName": "Anne Example"}}},
    ]

    def log_message(self, *a):
        pass

    def reply(self, code, body=None):
        raw = json.dumps(body).encode() if body is not None else b"OK"
        self.send_response(code)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def who(self):
        key = self.headers.get("Authorization", "").removeprefix("Bearer ")
        if key == ADMIN:
            return "admin"
        return self.server.keys.get(key, {}).get("user")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if not self.who():
            return self.reply(401, {})
        if path == "/api/libraries":
            return self.reply(200, {"libraries": [{"id": "lib", "mediaType": "book"}, {"id": "pods", "mediaType": "podcast"}]})
        if path == "/api/libraries/lib/items":
            return self.reply(200, {"results": self.books, "total": len(self.books)})
        if path == "/api/users":
            return self.reply(200, {"users": [{"id": "u-sam", "username": "sam"}, {"id": "u-alex", "username": "Alex"}]})
        if path.startswith("/api/users/"):
            uid = path.rsplit("/", 1)[1]
            return self.reply(200, {"id": uid, "mediaProgress": self.server.progress.get(uid, [])})
        self.reply(404, {})

    def do_POST(self):
        if self.who() != "admin":
            return self.reply(403, {})
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        key_id = f"k{len(self.server.made) + 1}"
        self.server.keys[f"user-key-{key_id}"] = {"user": body["userId"], "id": key_id}
        self.server.made.append(body)
        self.reply(200, {"apiKey": {"apiKey": f"user-key-{key_id}", "id": key_id}})

    def do_PATCH(self):
        user = self.who()
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if user in (None, "admin"):
            return self.reply(403, {})
        for p in body:
            self.server.progress.setdefault(user, []).append({"libraryItemId": p["libraryItemId"], "currentTime": p["currentTime"],
                                                              "isFinished": p["isFinished"]})
        self.server.written.setdefault(user, []).extend(body)
        self.reply(200)

    def do_DELETE(self):
        key_id = self.path.rsplit("/", 1)[1]
        for k, v in list(self.server.keys.items()):
            if v["id"] == key_id:
                del self.server.keys[k]
        self.server.deleted.append(key_id)
        self.reply(200)


class FakeJellyfin(BaseHTTPRequestHandler):
    """One user, with a book in three files (part way through the second) and a single-file book finished."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/Users":
            body = [{"Id": "j1", "Name": "Sam"}]
        else:
            tick = 10_000_000
            items = [
                {"Id": f"f{i}", "Name": f"Part {i}", "Album": "A Wizard of Earthsea", "AlbumArtist": "Ursula K. Le Guin", "ParentId": "d1",
                 "IndexNumber": i, "RunTimeTicks": 10000 * tick, "Path": f"/books/Le Guin/Earthsea/0{i}.mp3",
                 "UserData": {"Played": i == 1, "PlaybackPositionTicks": 2500 * tick if i == 2 else 0,
                              "LastPlayedDate": "2026-10-30T20:00:00Z" if i == 2 else None}}
                for i in (1, 2, 3)]
            items.append({"Id": "m1", "Name": "Mort", "AlbumArtist": "Terry Pratchett", "ParentId": "d2", "RunTimeTicks": 36000 * tick,
                          "ProviderIds": {"Isbn": "9780552131061"}, "Path": "/books/Pratchett/Mort.m4b",
                          "UserData": {"Played": True, "LastPlayedDate": "2026-09-01T10:00:00Z"}})
            items.append({"Id": "x1", "Name": "Unheard Book", "AlbumArtist": "Nobody", "ParentId": "d3", "RunTimeTicks": 100 * tick,
                          "Path": "/books/Nobody/Unheard.m4b", "UserData": {}})
            items.append({"Id": "z1", "Name": "Lost Book", "AlbumArtist": "Someone", "ParentId": "d4", "RunTimeTicks": 100 * tick,
                          "Path": "/books/Someone/Lost.m4b", "UserData": {"PlaybackPositionTicks": 50 * tick}})
            body = {"Items": items, "TotalRecordCount": len(items)}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


class ListeningTest(unittest.TestCase):
    def setUp(self):
        self.abs, self.abs_url = serve(FakeAbs)
        self.abs.keys, self.abs.made, self.abs.deleted, self.abs.written = {}, [], [], {}
        self.abs.progress = {"u-alex": [{"libraryItemId": "li-2", "currentTime": 100, "isFinished": False}]}
        self.jf, self.jf_url = serve(FakeJellyfin)
        self.dir = tempfile.mkdtemp()
        self.services = [{"id": "abs", "name": "Audiobookshelf", "type": "audiobookshelf", "url": self.abs_url, "api_key": ADMIN, "enabled": True}]

    def tearDown(self):
        for server in (self.abs, self.jf):
            server.shutdown()
            server.server_close()

    def test_book_in_several_files_becomes_one_position(self):
        tracks = [{"order": 1, "duration_ms": 1000, "position_ms": 0, "played": True, "last": 5},
                  {"order": 2, "duration_ms": 1000, "position_ms": 400, "played": False, "last": 9},
                  {"order": 3, "duration_ms": 1000, "position_ms": 0, "played": False, "last": None}]
        self.assertEqual(listening._book(tracks), {"position_s": 1.4, "duration_s": 3.0, "finished": False, "finished_at": None, "updated": 9})
        self.assertIsNone(listening._book([{**t, "position_ms": 0, "played": False} for t in tracks]))
        done = listening._book([{**t, "played": True, "position_ms": 0} for t in tracks])
        self.assertTrue(done["finished"])

    def test_matching_order_and_scaling(self):
        index = listening.Index([{"id": "a", "title": "The Hobbit", "author": "J. R. R. Tolkien", "asin": "", "isbn": "", "folder": "/x/Tolkien/Hobbit", "duration_s": 1000},
                                 {"id": "b", "title": "Other", "author": "", "asin": "B0", "isbn": "", "folder": "", "duration_s": 0}])
        self.assertEqual(index.find({"title": "The Hobbit", "author": "J.R.R. Tolkien"})["id"], "a")  # initials written either way
        self.assertIsNone(index.find({"title": "The Hobbit", "author": "Someone Else"}))
        self.assertEqual(index.find({"title": "the hobbit!", "author": "J. R. R. Tolkien, Narrator"})["id"], "a")
        self.assertEqual(index.find({"title": "Nope", "folder": "/media/Tolkien/Hobbit/01.mp3"})["id"], "a")
        self.assertEqual(index.find({"title": "Nope", "asin": "b0"})["id"], "b")  # ASINs in any case
        p = listening._payload({"position_s": 500, "duration_s": 2000}, {"id": "a", "duration_s": 1000})
        self.assertEqual((p["currentTime"], p["progress"]), (250, 0.25))

    def test_read_from_jellyfin_and_apply(self):
        accounts = listening.read_media_server(self.jf_url, "key", "Jellyfin")
        sam = {e["title"]: e for e in accounts["Sam"]}
        self.assertEqual(set(sam), {"A Wizard of Earthsea", "Mort", "Lost Book"})  # an unheard book is left out
        self.assertEqual(sam["A Wizard of Earthsea"]["position_s"], 12500)
        self.assertTrue(sam["Mort"]["finished"])
        listening.save_progress(self.dir, "Jellyfin", {**accounts, "Alex": [dict(sam["Mort"], finished=False, position_s=50)]})
        st = listening.status(self.dir, self.services)
        self.assertEqual({a["name"]: a["suggested"] for a in st["accounts"]}, {"Sam": "sam", "Alex": "Alex"})
        listening.set_mapping(self.dir, {"Sam": "sam", "Alex": "Alex", "Stranger": "sam"})

        sentence = listening.apply(self.dir, self.services)
        self.assertEqual(sentence, "Wrote 2 books; kept 1 that already had progress; 1 not found in Audiobookshelf")
        written = {p["libraryItemId"]: p for p in self.abs.written["u-sam"]}
        self.assertEqual(written["li-1"]["currentTime"], 12500)  # matched by title and author
        self.assertEqual((written["li-2"]["isFinished"], written["li-2"]["progress"]), (True, 1))  # by ISBN
        self.assertNotIn("u-alex", self.abs.written)  # Alex already had progress in Audiobookshelf: never changed
        self.assertEqual(self.abs.keys, {})  # every key made to act as a person was deleted
        self.assertEqual([m["userId"] for m in self.abs.made], ["u-sam"])
        self.assertEqual(listening.status(self.dir, self.services)["last"]["unmatched"], [{"account": "Sam", "title": "Lost Book", "author": "Someone"}])

        # A second run writes nothing again
        self.assertTrue(listening.apply(self.dir, self.services).startswith("Wrote 0 books"))
        self.assertEqual(len(self.abs.made), 1)

    def test_read_from_another_audiobookshelf(self):
        self.abs.progress["u-sam"] = [{"libraryItemId": "li-3", "currentTime": 600, "duration": 10000, "isFinished": False, "lastUpdate": 1_700_000_000_000}]
        accounts = listening.read_abs(self.abs_url, ADMIN)
        self.assertEqual(accounts["sam"][0]["title"], "Sea Stories: A Collection")
        self.assertEqual(accounts["Alex"][0]["position_s"], 100)

    def test_needs_an_admin_key(self):
        with self.assertRaises(ValueError):
            listening.apply(self.dir, [])

    def test_old_settings_give_audiobookshelf_its_own_type(self):
        data = config.migrate({"schema": 1, "services": [{"name": "Audiobookshelf", "type": "link"}, {"name": "Books", "type": "link"}]})
        self.assertEqual([s["type"] for s in data["services"]], ["audiobookshelf", "link"])
        self.assertEqual(data["schema"], 2)


if __name__ == "__main__":
    unittest.main()
