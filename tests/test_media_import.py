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

    def test_nothing_chosen_is_said(self):
        with self.assertRaisesRegex(media_import.ImportError_, "Choose a match"):
            media_import.run(self.cfg, 1, [{"path": "/x", "tmdb_id": None}])


if __name__ == "__main__":
    unittest.main()
