"""Why is this here? (DASH-557): what the last search for new apps learned, kept and shown without looking again."""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

from starboard import discovery
from tests.test_discovery import FakeNzbget, FakeSonarr


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class Why(unittest.TestCase):
    def setUp(self):
        discovery.LAST = None
        discovery._TRACE.clear()
        self.sonarr, self.nzbget = serve(FakeSonarr), serve(FakeNzbget)
        self.sp, self.np = self.sonarr.server_address[1], self.nzbget.server_address[1]

    def tearDown(self):
        for s in (self.sonarr, self.nzbget):
            s.shutdown()
            s.server_close()

    def search(self, docker=None):
        cat = {"sonarr": discovery.CATALOGUE["sonarr"][:2] + ([self.sp],) + discovery.CATALOGUE["sonarr"][3:],
               "nzbget": discovery.CATALOGUE["nzbget"][:2] + ([self.np],) + discovery.CATALOGUE["nzbget"][3:],
               "radarr": discovery.CATALOGUE["radarr"][:2] + ([1],) + discovery.CATALOGUE["radarr"][3:]}
        with mock.patch.object(discovery, "CATALOGUE", cat), mock.patch.object(discovery.containers, "available", lambda: bool(docker)), \
                mock.patch.object(discovery.containers, "docker", lambda *a, **k: docker or []):
            return discovery.search([])

    def test_found_says_what_found_it_and_what_it_matched_on(self):
        docker = [{"Names": ["/tv"], "Ports": [{"PublicPort": self.sp, "IP": "0.0.0.0"}]}]
        self.search(docker)
        got = {f["key"]: f for f in discovery.LAST["found"]}
        self.assertEqual(sorted(got), ["nzbget", "sonarr"])
        self.assertEqual(got["sonarr"]["match"], 'The page title contains "sonarr"')
        self.assertIn("Sonarr's usual port", got["sonarr"]["found_by"])
        self.assertIn("Docker: the container tv publishes it", got["sonarr"]["found_by"])
        self.assertEqual(got["nzbget"]["found_by"], ["NZBGet's usual port"])  # no Docker for it: nothing claimed
        self.assertEqual(got["sonarr"]["container"], "tv")
        self.assertTrue(discovery.LAST["docker"])

    def test_not_found_says_the_address_the_answer_and_the_reason(self):
        self.search()
        missing = {m["key"]: m for m in discovery.LAST["missing"]}
        self.assertNotIn("sonarr", missing)
        tried = missing["radarr"]["tried"][0]
        self.assertEqual(tried["url"], "http://127.0.0.1:1")
        self.assertEqual(tried["answer"], "No answer")
        self.assertIn("closed", tried["reason"])
        self.assertTrue(discovery.LAST["tried"])
        self.assertFalse(discovery.LAST["docker"])

    def test_a_page_that_answers_but_matches_nothing_says_so(self):
        discovery._probe(self.sp)  # fills the trace
        with mock.patch.object(discovery, "CATALOGUE", {"radarr": discovery.CATALOGUE["radarr"][:2] + ([self.sp], ("title", "radarr")) + discovery.CATALOGUE["radarr"][4:]}), \
                mock.patch.object(discovery.containers, "available", lambda: False):
            discovery.search([])
        row = discovery.LAST["missing"][0]["tried"][0]
        self.assertIn('titled "sonarr"', row["answer"])
        self.assertIn("matched an app", row["reason"])

    def test_the_trace_answers_for_a_sign_in_page(self):
        discovery._probe(self.np)
        self.assertIn("signing in as NZBGet", discovery._TRACE[self.np]["answer"])
        self.assertTrue(discovery._TRACE[self.np]["match"])

    def test_it_is_kept_only_when_asked_and_read_back_without_a_search(self):
        self.search()
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(os.path.exists(os.path.join(d, discovery.LAST_FILE)))  # a search alone writes nothing
            discovery.save(d)
            with open(os.path.join(d, discovery.LAST_FILE), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["found"], discovery.LAST["found"])
            first = discovery.LAST
            discovery.LAST = None  # as after a restart
            with mock.patch.object(discovery, "_probe", side_effect=AssertionError("must not look again")):
                self.assertEqual(discovery.last(d)["found"], first["found"])
            self.assertIsNone(discovery.last(tempfile.gettempdir() + "/nowhere-at-all"))

    def test_a_damaged_file_is_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, discovery.LAST_FILE), "w") as f:
                f.write("{not json")
            self.assertIsNone(discovery.last(d))


if __name__ == "__main__":
    unittest.main()
