"""Backup and restore round trips, and moving history from other apps, with made-up data only (TEST-PLAN BAK and MIG)."""

import json
import os
import shutil
import sqlite3
import tempfile
import threading
import types
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import auth, backup, config, listening, migrate, watch
from tests.test_jellyfin import FakeJellyfin
from tests.test_listening import ADMIN, FakeAbs


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def reply(handler, body):
    raw = json.dumps(body).encode()
    handler.send_response(200)
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


APPS = [
    {"id": "sonarr", "name": "Sonarr", "type": "sonarr", "url": "http://sonarr:8989", "api_key": "s" * 32, "group": "Downloads"},
    {"id": "abs", "name": "Audiobookshelf", "type": "audiobookshelf", "url": "http://abs:80", "api_key": "a" * 240, "group": "Watch"},
    {"id": "notes", "name": "Notes", "type": "link", "url": "http://notes:3000", "group": "Tools", "icon": "https://example.com/n.png"},
]


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.dirs = [tempfile.mkdtemp(), tempfile.mkdtemp()]
        self.old, self.new = (config.Config(d) for d in self.dirs)
        for app in APPS:
            self.old.upsert_service(app)
        self.old.update_general({"site_name": "Made-up Media", "design": "board", "groups": ["Watch", "Downloads", "Tools"],
                                 "upcoming_view": "calendar", "upcoming_days": 30, "show_posters": False})
        self.old.data["auth"]["password_hash"] = "made-up-hash"
        self.old.save()

    def tearDown(self):
        for d in self.dirs:
            shutil.rmtree(d, ignore_errors=True)

    def test_bak01_round_trip_to_a_fresh_install(self):
        saved = json.loads(json.dumps(backup.export(self.old, "0.7.4")))
        self.assertNotIn("auth", json.dumps(saved))
        self.assertNotIn("made-up-hash", json.dumps(saved))
        self.assertEqual(backup.restore(self.new, saved), 3)
        for key in ("site_name", "design", "groups", "upcoming_view", "upcoming_days", "show_posters"):
            self.assertEqual(self.new.data[key], self.old.data[key], key)
        self.assertEqual([(s["id"], s["api_key"], s["group"]) for s in self.new.data["services"]],
                         [(s["id"], s["api_key"], s["group"]) for s in self.old.data["services"]])
        self.assertEqual(self.new.data["auth"]["password_hash"], "")  # the fresh install keeps its own (no) password
        reread = config.Config(self.dirs[1])  # and it is on disk, not only in memory
        self.assertEqual(len(reread.data["services"]), 3)

    def test_bak02_backup_from_before_audiobookshelf_had_its_own_type(self):
        old = {"format": "starboard-settings", "version": "0.5.2", "settings": {"site_name": "Old Media"},
               "services": [{"id": "abs", "name": "Audiobookshelf", "type": "link", "url": "http://abs:80"},
                            {"id": "books", "name": "Books", "type": "link", "url": "http://books:80"}]}
        backup.restore(self.new, old)
        self.assertEqual([s["type"] for s in self.new.data["services"]], ["audiobookshelf", "link"])
        self.assertEqual(self.new.data["site_name"], "Old Media")
        # A backup made now says its schema, so a deliberate link stays a link
        self.new.data["services"][0]["type"] = "link"
        backup.restore(self.new, backup.export(self.new, "0.7.4"))
        self.assertEqual(self.new.data["services"][0]["type"], "link")

    def test_bak03_not_a_backup_changes_nothing(self):
        before = json.dumps(self.old.data, sort_keys=True)
        for bad in (None, [], "", {}, {"format": "other"}, {"format": "starboard-settings"},
                    {"format": "starboard-settings", "services": "x"},
                    {"format": "starboard-settings", "services": [{"id": "a", "name": "", "type": "link"}]},
                    {"format": "starboard-settings", "services": [dict(APPS[0]), dict(APPS[0])]}):
            with self.assertRaises(config.ConfigError):
                backup.restore(self.old, bad)
        self.assertEqual(json.dumps(self.old.data, sort_keys=True), before)
        with open(self.old.path) as f:
            self.assertEqual(json.dumps(json.load(f), sort_keys=True), before)

    def test_bak04_unknown_parts_ignored_and_removed_choices_default(self):
        odd = backup.export(self.old, "0.9.0")
        odd["settings"].update(design="neon", upcoming_view="timeline", upcoming_days=5, a_setting_from_the_future=True)
        odd["services"] = [dict(APPS[0], colour="red"), dict(APPS[2], type="a-kind-that-went")]
        odd["something_new"] = {"x": 1}
        self.assertEqual(backup.restore(self.new, odd), 2)
        d = self.new.data
        self.assertEqual((d["design"], d["upcoming_view"], d["upcoming_days"]),
                         (config.DEFAULTS["design"], config.DEFAULTS["upcoming_view"], config.DEFAULTS["upcoming_days"]))
        self.assertNotIn("a_setting_from_the_future", d)
        self.assertNotIn("colour", d["services"][0])
        self.assertEqual(d["services"][1]["type"], "link")  # still on the dashboard, as a plain link
        self.assertEqual(d["site_name"], "Made-up Media")

    def test_bak05_copies_before_a_restore_and_an_update_can_be_restored(self):
        backup.restore(self.old, {"format": "starboard-settings", "settings": {"site_name": "Replaced"}, "services": []})
        self.assertEqual(self.old.data["services"], [])
        copies = backup.saved_copies(self.old)
        self.assertEqual(copies[0]["reason"], "Before a restore")
        path = os.path.join(self.dirs[0], "backups", copies[0]["name"])
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertEqual(backup.restore_saved(self.old, copies[0]["name"]), 3)
        self.assertEqual(self.old.data["site_name"], "Made-up Media")
        self.assertEqual(self.old.data["auth"]["password_hash"], "made-up-hash")

        # An update that changes the schema saves a copy first, and that copy restores (and is moved up again)
        d = tempfile.mkdtemp()
        self.dirs.append(d)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"schema": 1, "site_name": "Before 0.6", "services": [{"id": "abs", "name": "Audiobookshelf", "type": "link", "url": "http://abs:80"}],
                       "auth": {"password_hash": "kept", "session_version": 1}}, f)
        updated = config.Config(d)
        copy = backup.saved_copies(updated)[0]
        self.assertEqual(copy["reason"], "Before an update changed the settings")
        self.assertEqual(backup.restore_saved(updated, copy["name"]), 1)
        self.assertEqual(updated.data["services"][0]["type"], "audiobookshelf")
        self.assertEqual(updated.data["auth"]["password_hash"], "kept")

    def test_bak06_07_server_backup_job_running_done_failed_and_alert(self):
        jobs = self.dirs[0] + "/jobs"
        os.makedirs(jobs + "/requests")
        with mock.patch.dict(os.environ, {"STARBOARD_JOBS_DIR": jobs}):
            backup.request_server_backup(with_prompt=True)
            self.assertTrue(os.path.exists(jobs + "/requests/backup-with-prompt"))
            self.assertEqual(backup.server_status()["status"]["status"], "waiting")
            os.remove(jobs + "/requests/backup-with-prompt")
            for state in ("running", "done"):
                with open(jobs + "/backup-with-prompt.json", "w") as f:
                    json.dump({"status": state, "started": 100, "summary": "3 folders"}, f)
                st = backup.server_status()["status"]
                self.assertEqual((st["status"], st["with_prompt"]), (state, True))
            with open(jobs + "/backup.json", "w") as f:
                json.dump({"status": "failed", "started": 200, "finished": 260, "summary": "The disk is full", "exit": 1}, f)
            st = backup.server_status()["status"]
            self.assertEqual((st["status"], st["summary"], st["with_prompt"]), ("failed", "The disk is full", False))

            # The alert goes out once, with the summary
            self.old.data["watch"]["alerts"] = {"backup_failed": True}  # only this alert, so no disks or apps are read
            self.old.data["watch"]["channel"] = {"kind": "webhook", "url": "http://alerts.example/hook"}
            w = watch.Watch(types.SimpleNamespace(config=self.old, disk_temps=types.SimpleNamespace(record=lambda disks: None)))
            sent = []
            with mock.patch.object(watch, "send", lambda ch, title, msg, level="info": sent.append((title, msg))), \
                    mock.patch.object(watch.services, "cached", lambda *a, **k: []):
                w.tick()
                w.tick()
            failed = [s for s in sent if s[0] == "The server backup failed"]
            self.assertEqual(len(failed), 1)
            self.assertIn("The disk is full", failed[0][1])

    def test_bak08_copy_the_data_folder_to_a_new_machine(self):
        sessions = auth.Sessions(self.dirs[0])
        token = sessions.create(30, self.old.data["auth"]["session_version"])
        moved = tempfile.mkdtemp()
        self.dirs.append(moved)
        shutil.copytree(self.dirs[0], moved, dirs_exist_ok=True, copy_function=shutil.copy2)
        there = config.Config(moved)
        self.assertEqual(there.data, self.old.data)
        self.assertEqual(os.stat(os.path.join(moved, "config.json")).st_mode & 0o777, 0o600)
        # Sessions are kept as hashes only and are meant to survive a restart: a browser that signed in to the old
        # address does not send its cookie to a new one, and Sign out everywhere (System) ends them all.
        self.assertTrue(auth.Sessions(moved).valid(token, there.data["auth"]["session_version"]))
        with open(os.path.join(moved, "sessions.json")) as f:
            self.assertNotIn(token, f.read())


# Moving watch history ---------------------------------------------------------------------------

def plex_fixture(path):
    """A tiny Plex database: three films (one Jellyfin does not have), a show with one episode, two accounts."""
    db = sqlite3.connect(path)
    db.executescript('''
        create table accounts (id integer, name text);
        create table tags (id integer, tag text, tag_type integer);
        create table taggings (metadata_item_id integer, tag_id integer);
        create table metadata_items (id integer, metadata_type integer, title text, year integer, "index" integer, parent_id integer, guid text);
        create table media_items (metadata_item_id integer, duration integer);
        create table metadata_item_settings (account_id integer, guid text, view_count integer, view_offset integer, last_viewed_at integer);
        insert into accounts values (0, ''), (1, 'Alex'), (2, 'Sam');
        insert into metadata_items values
          (1, 1, 'Made Up Film', 1999, null, null, 'plex://movie/aaa'),
          (2, 1, 'Older Agent Film', 1985, null, null, 'com.plexapp.agents.imdb://tt0000001?lang=en'),
          (3, 1, 'Not Here Film', 2001, null, null, 'plex://movie/ccc'),
          (10, 2, 'Pretend Show', 2010, null, null, 'plex://show/ddd'),
          (11, 3, 'Season 1', null, 1, 10, 'plex://season/eee'),
          (12, 4, 'The Second One', null, 2, 11, 'plex://episode/fff');
        insert into tags values (1, 'tmdb://603', 314), (2, 'tvdb://81189', 314), (3, 'tmdb://999', 314);
        insert into taggings values (1, 1), (10, 2), (3, 3);
        insert into media_items values (1, 8160000), (2, 6000000), (3, 5400000), (12, 2700000);
        insert into metadata_item_settings values
          (1, 'plex://movie/aaa', 1, 0, 1735689600),
          (1, 'com.plexapp.agents.imdb://tt0000001?lang=en', 0, 30000, 1735700000),
          (1, 'plex://movie/ccc', 2, 0, 1735600000),
          (1, 'plex://episode/fff', 0, 60000, 1735800000),
          (2, 'plex://movie/aaa', 0, 0, null);
    ''')
    db.commit()
    db.close()


class FakeSourceJellyfin(BaseHTTPRequestHandler):
    """A Jellyfin to move away from: one user, a watched film, a part-watched episode, pages of one item."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/Users":
            return reply(self, [{"Name": "Alex", "Id": "old1"}])
        if q.get("Ids"):
            return reply(self, {"Items": [{"Id": "ser1", "Name": "Pretend Show", "ProductionYear": 2010, "ProviderIds": {"Tvdb": "81189"}}]})
        items = {"IsPlayed": [{"Id": "f1", "Type": "Movie", "Name": "Made Up Film", "ProductionYear": 1999, "ProviderIds": {"Tmdb": "603", "Other": "x"},
                               "RunTimeTicks": 81600000000, "UserData": {"Played": True, "PlayCount": 2, "LastPlayedDate": "2025-01-01T00:00:00Z"}}],
                 "IsResumable": [{"Id": "ep1", "Type": "Episode", "SeriesId": "ser1", "SeriesName": "Pretend Show", "ParentIndexNumber": 1,
                                  "IndexNumber": 2, "Name": "The Second One", "UserData": {"PlaybackPositionTicks": 600000000}},
                                 {"Id": "f1", "Type": "Movie", "Name": "Made Up Film", "ProductionYear": 1999, "ProviderIds": {"Tmdb": "603"},
                                  "RunTimeTicks": 81600000000, "UserData": {"Played": True, "PlayCount": 2, "LastPlayedDate": "2025-01-01T00:00:00Z"}}]}
        wanted = items.get(q.get("Filters", [""])[0], [])
        start = int(q.get("StartIndex", ["0"])[0])
        reply(self, {"Items": wanted[start:start + 1], "TotalRecordCount": len(wanted)})


class MigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.jf, url = serve(FakeJellyfin)
        cls.services = [{"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": url, "api_key": "k"}]

    @classmethod
    def tearDownClass(cls):
        cls.jf.shutdown()
        cls.jf.server_close()

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        FakeJellyfin.played, FakeJellyfin.positions = [], []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_mig01_07_plex_database_into_jellyfin_once(self):
        db = os.path.join(self.dir, "plex.db")
        plex_fixture(db)
        accounts = migrate.read_plex_db(db)
        self.assertEqual(set(accounts), {"Alex"})  # Sam only opened a film; the unnamed account is skipped
        alex = {e.get("title"): e for e in accounts["Alex"]}
        self.assertEqual(alex["Made Up Film"]["ids"], {"tmdb": "603"})
        self.assertEqual(alex["Older Agent Film"]["ids"], {"imdb": "tt0000001"})  # older Plex agents too
        self.assertEqual((alex["The Second One"]["show"], alex["The Second One"]["season"], alex["The Second One"]["episode"]), ("Pretend Show", 1, 2))
        self.assertEqual(alex["Made Up Film"]["last_watched"], "2025-01-01T00:00:00+00:00")

        migrate.save_history(self.dir, "Plex database", accounts)
        migrate.set_mapping(self.dir, {"Alex": "alex", "Nobody": "alex"})
        self.assertEqual(migrate.apply(self.dir, self.services), "Marked 1 as watched and set 2 resume points; 1 not in Jellyfin yet")
        self.assertEqual(FakeJellyfin.played, ["m1"])
        self.assertEqual(sorted(FakeJellyfin.positions), [("e1", 600000000), ("m2", 300000000)])
        last = migrate.status(self.dir, self.services)["last"]
        self.assertEqual(last["unmatched"], [{"account": "Alex", "title": "Not Here Film (2001)"}])

        # MIG-07: the same import again, read and applied twice more, counts nothing twice
        migrate.save_history(self.dir, "Plex database", migrate.read_plex_db(db))
        self.assertIsNone(migrate.status(self.dir, self.services)["last"])  # the old list went with the old history
        self.assertEqual(migrate.apply(self.dir, self.services), "Marked 0 as watched and set 0 resume points; 1 not in Jellyfin yet")
        migrate.apply(self.dir, self.services)
        self.assertEqual((len(FakeJellyfin.played), len(FakeJellyfin.positions)), (1, 2))
        self.assertEqual(migrate.status(self.dir, self.services)["accounts"][0]["applied"], 3)

    def test_mig04_from_another_jellyfin(self):
        source, url = serve(FakeSourceJellyfin)
        try:
            accounts = migrate.read_media_server(url, "old-key", "Jellyfin")
        finally:
            source.shutdown()
            source.server_close()
        alex = {e["type"]: e for e in accounts["Alex"]}
        self.assertEqual(len(accounts["Alex"]), 2)  # a film both played and resumable is read once
        self.assertEqual((alex["movie"]["watched"], alex["movie"]["ids"], alex["movie"]["duration_ms"]), (True, {"tmdb": "603"}, 8160000))
        self.assertEqual((alex["episode"]["position_ms"], alex["episode"]["ids"], alex["episode"]["show_year"]), (60000, {"tvdb": "81189"}, 2010))
        migrate.save_history(self.dir, "Jellyfin", accounts)
        migrate.set_mapping(self.dir, {"Alex": "alex"})
        self.assertTrue(migrate.apply(self.dir, self.services).startswith("Marked 1 as watched and set 1 resume points"))

    def test_mig05_history_files(self):
        right = os.path.join(self.dir, "history.json")
        with open(right, "w") as f:
            json.dump({"source": "Plex", "accounts": {"Alex": [{"type": "movie", "watched": True, "ids": {"tmdb": "603"}}]}}, f)
        self.assertEqual(list(migrate.read_file(right)), ["Alex"])
        for name, content in (("empty.json", ""), ("list.json", "[]"), ("other.json", '{"accounts": []}'), ("db.json", "SQLite format 3\0")):
            path = os.path.join(self.dir, name)
            with open(path, "w") as f:
                f.write(content)
            with self.assertRaisesRegex(ValueError, "not a watch history file"):
                migrate.read_file(path)
        big = os.path.join(self.dir, "big.json")
        with open(big, "wb") as f:
            f.truncate(migrate.MAX_HISTORY_FILE + 1)  # sparse: takes no room on the disk
        with self.assertRaisesRegex(ValueError, "larger than 512 MB"):
            migrate.read_file(big)


class FakePlexBooks(BaseHTTPRequestHandler):
    """Plex with an audiobook library: a book in two files (part way through the second) and one not in Audiobookshelf."""

    def log_message(self, *a):
        pass

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if urllib.parse.parse_qs(u.query).get("X-Plex-Token") != ["plex-token"]:
            self.send_response(401)
            self.end_headers()
            return
        if u.path == "/library/sections":
            body = {"Directory": [{"key": "1", "type": "artist", "title": "Audiobooks"}, {"key": "2", "type": "artist", "title": "Music"}]}
        elif u.path == "/myplex/account":
            body = {"username": "sam"}
        elif u.path == "/library/sections/1/all":
            track = lambda album, author, i, played, offset, f: {
                "parentRatingKey": album, "parentTitle": album, "grandparentTitle": author, "parentIndex": 1, "index": i,
                "duration": 10_000_000, "viewOffset": offset, "viewCount": 1 if played else 0, "lastViewedAt": 1_700_000_000 + i,
                "Media": [{"Part": [{"file": f}]}]}
            body = {"Metadata": [track("A Wizard of Earthsea", "Ursula K. Le Guin", 1, True, 0, "/books/Le Guin/Earthsea/01.mp3"),
                                 track("A Wizard of Earthsea", "Ursula K. Le Guin", 2, False, 2_500_000, "/books/Le Guin/Earthsea/02.mp3"),
                                 track("Unscanned Book", "Anne Example", 1, False, 400_000, "/books/Example/Unscanned.m4b")]}
        else:
            body = {}
        reply(self, {"MediaContainer": body})


class ListeningFromPlexTest(unittest.TestCase):
    def test_mig08_plex_audiobooks_into_audiobookshelf(self):
        plex, plex_url = serve(FakePlexBooks)
        abs_server, abs_url = serve(FakeAbs)
        abs_server.keys, abs_server.made, abs_server.deleted, abs_server.written, abs_server.progress = {}, [], [], {}, {}
        d = tempfile.mkdtemp()
        try:
            accounts = listening.read_plex(plex_url, "plex-token")
            books = {e["title"]: e for e in accounts["sam"]}
            self.assertEqual(books["A Wizard of Earthsea"]["position_s"], 12500)
            self.assertEqual(books["A Wizard of Earthsea"]["folder"], "/books/Le Guin/Earthsea")
            services = [{"id": "abs", "name": "Audiobookshelf", "type": "audiobookshelf", "url": abs_url, "api_key": ADMIN, "enabled": True}]
            listening.save_progress(d, "Plex", accounts)
            listening.set_mapping(d, {"sam": "sam"})
            self.assertEqual(listening.apply(d, services), "Wrote 1 book; kept 0 that already had progress; 1 not found in Audiobookshelf")
            self.assertEqual(abs_server.written["u-sam"][0]["currentTime"], 18750)  # scaled: Audiobookshelf's copy is longer
            self.assertEqual(listening.status(d, services)["last"]["unmatched"], [{"account": "sam", "title": "Unscanned Book", "author": "Anne Example"}])
            with self.assertRaises(Exception):
                listening.read_plex(plex_url, "wrong-token")
        finally:
            for s in (plex, abs_server):
                s.shutdown()
                s.server_close()
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
