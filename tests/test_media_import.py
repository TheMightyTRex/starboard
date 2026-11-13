"""Films and series already on disk, through Reelix's library import (DASH-186)."""
import http.server
import json
import threading
import unittest
from unittest import mock

from starboard import media_import


class Reelix(http.server.BaseHTTPRequestHandler):
    seen = []
    have = False

    def _send(self, body, code=200):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        assert self.headers["X-Api-Key"] == "manager-key"
        if self.path == "/api/v1/rootfolders":
            return self._send([{"id": 1, "path": "/data/media/movies", "media_kind": "movie", "accessible": True,
                                "unmapped_folders": [{"name": "Arrival (2016)", "path": "/data/media/movies/Arrival (2016)"}]},
                               {"id": 2, "path": "/data/media/tv", "media_kind": "series", "accessible": True, "unmapped_folders": []}])
        if self.path.startswith("/api/v1/libraryimport/scan"):
            return self._send([{"folder": {"name": "Arrival (2016)", "path": "/data/media/movies/Arrival (2016)"}, "parsed_title": "Arrival",
                                "parsed_year": 2016, "file_count": 1, "size": 9, "suggestions": []}])
        if self.path == "/api/v1/bookrootfolders":
            return self._send([{"id": 4, "path": "/data/media/audiobooks", "kind": "audiobook", "accessible": True,
                                "unmapped_folders": [{"name": "Made-up Author", "path": "/data/media/audiobooks/Made-up Author"}]}])
        if self.path.startswith("/api/v1/bookimport/scan"):
            return self._send([{"folder": "Made-up Author", "path": "/data/media/audiobooks/Made-up Author", "kind": "audiobook",
                                "guessed_author": "Made-up Author", "suggestions": [], "lookup_error": None}])
        if self.path == "/api/v1/musicrootfolders":
            return self._send([{"id": 5, "path": "/data/media/music", "kind": "music", "accessible": True,
                                "unmapped_folders": [{"name": "Made-up Band", "path": "/data/media/music/Made-up Band"},
                                                     {"name": "Twin Name", "path": "/data/media/music/Twin Name"}]}])
        if self.path.startswith("/api/v1/musicimport/scan"):
            return self._send([{"folder": n, "path": f"/data/media/music/{n}", "guessed_artist": n, "suggestions": [], "lookup_error": None}
                               for n in ("Made-up Band", "Twin Name")])
        if self.path == "/api/v1/qualityprofiles?kind=music":
            return self._send([{"id": 11, "name": "Music: Any"}])
        if self.path == "/api/v1/metadataprofiles":
            return self._send([{"id": 1, "name": "Standard"}])
        if self.path == "/api/v1/qualityprofiles?kind=audiobook":
            return self._send([{"id": 9, "name": "Audiobook: Any"}])
        if self.path.startswith("/api/v1/movies?"):
            return self._send({"items": [{"tmdb_id": 329865, "title": "Arrival", "path": "/data/media/movies/Arrival"}] if Reelix.have else []})
        if self.path == "/api/v1/qualityprofiles":
            return self._send([{"id": 7, "name": "HD"}, {"id": 8, "name": "Music", "family": "music"}])
        self._send({"message": "no"}, 404)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Reelix.seen.append((self.path, body))
        if self.path == "/api/v1/libraryimport/match":
            return self._send([{"folder": {"name": "Arrival (2016)", "path": body["paths"][0]}, "parsed_title": "Arrival",
                                "parsed_year": 2016, "file_count": 1, "size": 9,
                                "suggestions": [{"tmdb_id": 329865, "title": "Arrival", "year": 2016}]}])
        if self.path == "/api/v1/bookimport/match":
            return self._send([{"folder": "Made-up Author", "path": body["paths"][0], "kind": "audiobook", "guessed_author": "Made-up Author",
                                "suggestions": [{"openlibrary_id": "OL1A", "name": "Made-up Author", "top_work": "A Made-up Book",
                                                 "work_count": 12, "author_id": None}], "lookup_error": None}])
        if self.path == "/api/v1/musicimport/match":
            one = {"musicbrainz_id": "11111111-1111-4111-8111-111111111111", "name": "Made-up Band", "artist_type": "Group",
                   "country": "GB", "disambiguation": "made-up", "artist_id": None}
            twins = [{"musicbrainz_id": f"2222222{n}-2222-4222-8222-222222222222", "name": "Twin Name", "artist_type": "Person",
                      "country": c, "artist_id": None} for n, c in ((1, "GB"), (2, "US"))]
            return self._send([{"folder": "Made-up Band", "path": "/data/media/music/Made-up Band", "guessed_artist": "Made-up Band",
                                "suggestions": [one], "lookup_error": None},
                               {"folder": "Twin Name", "path": "/data/media/music/Twin Name", "guessed_artist": "Twin Name",
                                "suggestions": twins, "lookup_error": None}])
        if self.path == "/api/v1/musicimport":
            return self._send({"added": [3], "errors": []})
        if self.path == "/api/v1/bookimport":
            return self._send({"added": [7], "errors": []})
        if self.path == "/api/v1/libraryimport":
            return self._send({"added": [41], "errors": []})
        self._send({"message": "no"}, 404)

    def log_message(self, *a):
        pass


class MediaImport(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Reelix)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.shutdown)
        self.addCleanup(self.srv.server_close)
        self.cfg = mock.Mock(data={"services": [{"type": "link", "icon": "reelix", "api_key": "manager-key",
                                                 "url": f"http://127.0.0.1:{self.srv.server_address[1]}"}]})

    def test_folders_scan_and_import(self):
        self.assertEqual(media_import.folders(self.cfg, "films"), [{"id": 1, "path": "/data/media/movies", "waiting": 1}])
        page = media_import.scan(self.cfg, 1)
        self.assertEqual((page["total"], page["items"][0]["matches"][0]["tmdb_id"]), (1, 329865))
        out = media_import.run(self.cfg, 1, [{"path": page["items"][0]["path"], "tmdb_id": 329865}])
        self.assertEqual(out, {"added": 1, "errors": []})
        sent = Reelix.seen[-1][1]
        self.assertEqual((sent["items"][0]["quality_profile_id"], sent["search_on_add"]), (7, False))

    def test_a_match_already_in_the_library_is_marked_and_a_left_out_folder_not_counted(self):
        # Owner, 10 November 2026: two series folders of shows already in the library stayed on Still to set up.
        import tempfile
        self.cfg.data_dir = tempfile.mkdtemp()
        Reelix.have = True
        self.addCleanup(setattr, Reelix, "have", False)
        page = media_import.scan(self.cfg, 1)
        self.assertEqual(page["items"][0]["matches"][0]["already"], "Arrival")
        media_import.leave_out(self.cfg, ["/data/media/movies/Arrival (2016)"])
        self.assertEqual(media_import.folders(self.cfg, "films")[0]["waiting"], 0)
        self.assertEqual(media_import.scan(self.cfg, 1)["total"], 0)

    def test_audiobooks_come_in_by_author_following_only_what_is_there(self):
        # Owner, 11 November 2026: Library, Audiobooks was empty with 49 author folders on disk (DASH-282).
        self.assertEqual(media_import.folders(self.cfg, "audiobooks"), [{"id": 4, "path": "/data/media/audiobooks", "waiting": 1}])
        page = media_import.scan_books(self.cfg, 4)
        m = page["items"][0]["matches"][0]
        self.assertEqual((m["id"], m["title"], m["detail"]), ("OL1A", "Made-up Author", "12 works, best known for A Made-up Book"))
        self.assertTrue(page["items"][0]["sure"])  # one author of that exact name
        out = media_import.run_books(self.cfg, 4, [{"path": page["items"][0]["path"], "id": "OL1A"}])
        self.assertEqual(out, {"added": 1, "errors": []})
        self.assertEqual(Reelix.seen[-1], ("/api/v1/bookimport", {"root_folder_id": 4, "items": [
            {"path": "/data/media/audiobooks/Made-up Author", "openlibrary_id": "OL1A", "monitor": "existing",
             "audio_quality_profile_id": 9}]}))
        with self.assertRaisesRegex(media_import.ImportError_, "Choose a match"):
            media_import.run_books(self.cfg, 4, [{"path": "/x", "id": "tt1"}])

    def test_music_comes_in_by_artist_following_only_what_is_there(self):
        # DASH-282: Library, Music's note and dialog, through Reelix's music import.
        self.assertEqual(media_import.folders(self.cfg, "music"), [{"id": 5, "path": "/data/media/music", "waiting": 2}])
        self.assertIs(media_import.scanner("music")[0], media_import.scan_music)
        page = media_import.scan_music(self.cfg, 5)
        one, twins = page["items"]
        self.assertEqual((one["matches"][0]["title"], one["matches"][0]["detail"], one["sure"]), ("Made-up Band", "made-up, band, GB", True))
        self.assertFalse(twins["sure"])  # two artists of that name: a person chooses
        out = media_import.run_music(self.cfg, 5, [{"path": one["path"], "id": one["matches"][0]["id"]}])
        self.assertEqual(out, {"added": 1, "errors": []})
        self.assertEqual(Reelix.seen[-1], ("/api/v1/musicimport", {"root_folder_id": 5, "items": [
            {"path": "/data/media/music/Made-up Band", "musicbrainz_id": "11111111-1111-4111-8111-111111111111", "monitor": "existing",
             "quality_profile_id": 11, "metadata_profile_id": 1}]}))
        with self.assertRaisesRegex(media_import.ImportError_, "Choose a match"):
            media_import.run_music(self.cfg, 5, [{"path": "/x", "id": "OL1A"}])

    def test_nothing_chosen_is_said(self):
        with self.assertRaisesRegex(media_import.ImportError_, "Choose a match"):
            media_import.run(self.cfg, 1, [{"path": "/x", "tmdb_id": None}])


if __name__ == "__main__":
    unittest.main()
