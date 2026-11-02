"""Search for new apps, the release list and the upgrade guide's questions."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starboard import discovery, releases


class FakeSonarr(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = b"<html><head><title>Sonarr</title></head></html>"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class DiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSonarr)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_an_app_is_known_by_its_page_title_on_any_port(self):
        self.assertEqual(discovery._probe(self.port), ["sonarr"])

    def test_a_closed_port_finds_nothing(self):
        self.assertEqual(discovery._probe(1), [])

    def test_search_marks_apps_already_in_the_list(self):
        fake = {"sonarr": discovery.CATALOGUE["sonarr"][:2] + ([self.port],) + discovery.CATALOGUE["sonarr"][3:]}
        with mock.patch.object(discovery, "CATALOGUE", fake), mock.patch.object(discovery.containers, "available", lambda: False):
            found = discovery.search([])["items"]
            self.assertEqual([(i["key"], i["already"]) for i in found], [("sonarr", False)])
            have = [{"name": "Sonarr", "type": "sonarr", "url": f"http://127.0.0.1:{self.port}"}]
            self.assertTrue(discovery.search(have)["items"][0]["already"])

    def test_keys_are_read_only_from_safe_container_names(self):
        with mock.patch.object(discovery.containers, "available", lambda: True):
            self.assertIsNone(discovery.read_key("sonarr", "../etc"))
            self.assertIsNone(discovery.read_key("plex", "plex"))


class ReleasesTest(unittest.TestCase):
    def test_the_newest_tag_is_found_by_number_not_by_name(self):
        from starboard.server import newest_tag
        self.assertEqual(newest_tag(["v0.1.8", "v0.10.0", "v0.5.0", "v0.9.9-dev.1", "latest"]), "v0.10.0")
        self.assertIsNone(newest_tag(["edge"]))

    def test_the_current_version_has_release_notes(self):
        import pathlib
        version = (pathlib.Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
        self.assertEqual(releases.RELEASES[-1]["version"], version)
        known = {"apps", "keys", "jellyfin", "hours", "alerts", "preset", "names", "storage"}
        for r in releases.RELEASES:
            self.assertTrue(set(r["review"]) <= known, r["version"])
            self.assertNotIn("—", releases.markdown(r))

    def test_pending_collects_each_question_once(self):
        p = releases.pending("0.2.0", "0.5.0", True)
        self.assertEqual([r["version"] for r in p["releases"]], ["0.3.0", "0.3.4", "0.4.0", "0.5.0"])
        self.assertEqual(p["review"], ["jellyfin", "preset", "names", "apps", "storage"])
        self.assertTrue(p["wizard"])

    def test_fresh_and_up_to_date_installs_need_no_guide(self):
        self.assertFalse(releases.pending("", "0.5.0", False)["wizard"])
        self.assertFalse(releases.pending("0.5.0", "0.5.0", True)["wizard"])

    def test_an_install_from_before_the_record_starts_at_the_previous_release(self):
        p = releases.pending("", "0.5.0", True)
        self.assertEqual((p["from"], p["review"]), ("0.4.0", ["apps", "storage"]))


if __name__ == "__main__":
    unittest.main()
