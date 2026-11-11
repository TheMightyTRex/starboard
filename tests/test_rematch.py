"""Change match (11 November 2026): the old match out (files kept), the new one in at the same folder, or the old back."""
import http.server
import json
import threading
import unittest

from starboard import rematch


class Reelix(http.server.BaseHTTPRequestHandler):
    calls = []
    refuse = set()

    def log_message(self, *a):
        pass

    def send(self, body, code=200):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        Reelix.calls.append(("GET", self.path, None))
        if self.path == "/api/v1/movies/5":
            return self.send({"id": 5, "tmdb_id": 111, "path": "/data/media/movies/Odd (2020)", "quality_profile_id": 3})
        if self.path == "/api/v1/rootfolders":
            return self.send([{"id": 1, "path": "/data/media/movies"}, {"id": 2, "path": "/data/media/tv"}])
        if self.path.startswith("/api/v1/movies/lookup"):
            return self.send([{"tmdb_id": 222, "title": "Right Film", "year": 2020, "overview": "x"}])
        self.send({}, 404)

    def do_DELETE(self):
        Reelix.calls.append(("DELETE", self.path, None))
        self.send({}, 200)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Reelix.calls.append(("POST", self.path, body))
        tmdb = body["items"][0]["tmdb_id"]
        if tmdb in Reelix.refuse:
            return self.send({"added": [], "errors": [{"path": "x", "message": "already in the library"}]})
        self.send({"added": [77 if tmdb == 222 else 5], "errors": []})


class RematchTest(unittest.TestCase):
    def setUp(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Reelix)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.reelix = {"type": "link", "url": f"http://127.0.0.1:{srv.server_address[1]}/api/v1", "api_key": "k", "name": "Reelix", "id": "r1"}
        Reelix.calls.clear()
        Reelix.refuse = set()

    def test_search_and_change_keep_the_folder_and_the_files(self):
        self.assertEqual(rematch.search(self.reelix, "films", "Right")[0]["key"], "222")
        out = rematch.change(self.reelix, "films", 5, "222")
        self.assertEqual(out["id"], 77)
        self.assertIn(("DELETE", "/api/v1/movies/5?delete_files=false", None), Reelix.calls)
        post = [c for c in Reelix.calls if c[0] == "POST"][0][2]
        self.assertEqual(post["items"], [{"path": "/data/media/movies/Odd (2020)", "tmdb_id": 222, "quality_profile_id": 3}])
        self.assertEqual(post["root_folder_id"], 1)

    def test_a_refused_match_puts_the_old_one_back(self):
        Reelix.refuse = {222}
        with self.assertRaisesRegex(ValueError, "The old match is back"):
            rematch.change(self.reelix, "films", 5, "222")
        self.assertEqual([c[2]["items"][0]["tmdb_id"] for c in Reelix.calls if c[0] == "POST"], [222, 111])


if __name__ == "__main__":
    unittest.main()
