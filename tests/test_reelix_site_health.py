"""The Reelix card's health line (DASH-559): "3 of 40 sites failing", from Reelix's own health checks, never a wrong number."""
import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

from starboard import reelix_site_health as rsh

REELIX = {"id": "r1", "name": "Reelix", "type": "link", "url": "http://reelix:7700/api/v1", "api_key": "k", "link": "http://reelix:7700"}
DOWN = "Indexer {} is unavailable due to failures until 2026-11-25 09:00 UTC (connection: the site took too long to answer)"


def checks(*names, extra=()):
    return [{"source": "indexers", "level": "warning", "message": DOWN.format(n)} for n in names] + list(extra)


class Words(unittest.TestCase):
    def test_failing_of_the_total(self):
        self.assertEqual(rsh.words(checks("A", "B", "C"), 40), "3 of 40 sites failing")

    def test_without_a_total_it_says_how_many_and_no_more(self):
        self.assertEqual(rsh.words(checks("A", "B", "C"), None), "3 sites failing")
        self.assertEqual(rsh.words(checks("A"), None), "1 site failing")

    def test_a_site_named_twice_counts_once_and_a_name_with_spaces_is_whole(self):
        self.assertEqual(rsh.words(checks("My Jackett", "My Jackett"), 5), "1 of 5 sites failing")

    def test_a_total_that_cannot_be_right_is_left_out(self):
        self.assertEqual(rsh.words(checks("A", "B", "C"), 2), "3 sites failing")  # sites were taken off since the last look
        self.assertEqual(rsh.words(checks("A"), 0), "1 site failing")

    def test_a_misconfigured_site_counts(self):
        c = [{"source": "indexers", "level": "error", "message": "Indexer X is misconfigured: bad key"}]
        self.assertEqual(rsh.words(c, 4), "1 of 4 sites failing")

    def test_all_failing_and_none_on(self):
        c = checks("A", "B", extra=[{"source": "indexers", "level": "error", "message": "All indexers are unavailable due to failures"}])
        self.assertEqual(rsh.words(c, 2), "All 2 sites failing")
        self.assertEqual(rsh.words(c, None), "All sites failing")
        none = [{"source": "indexers", "level": "warning", "message": "No indexers are enabled; Reelix cannot find releases"}]
        self.assertEqual(rsh.words(none, 9), "No sites to search are turned on")

    def test_nothing_failing_says_so_only_with_a_total(self):
        self.assertEqual(rsh.words([], 40), "40 sites to search, none failing")
        self.assertIsNone(rsh.words([], None))  # nothing to say rather than a guess

    def test_other_checks_are_not_sites(self):
        other = [{"source": "download_clients", "level": "warning", "message": "Indexer lookalike is unavailable due to failures"}]
        self.assertIsNone(rsh.words(other, None))


class Asking(unittest.TestCase):
    def ask(self, answer=None, error=None):
        def request(url, **kw):
            self.assertTrue(url.endswith("/api/v1/system/health"))
            self.assertEqual(kw["headers"], {"X-Api-Key": "k"})
            if error:
                raise error
            return answer
        with mock.patch.object(rsh.jsonhttp, "request", request):
            return rsh._health(REELIX)

    def test_a_good_answer(self):
        self.assertEqual(self.ask({"status": "ok", "checks": checks("A")}), checks("A"))

    def test_a_503_still_carries_the_report(self):
        body = json.dumps({"status": "error", "checks": checks("A")}).encode()
        err = urllib.error.HTTPError("u", 503, "x", {}, io.BytesIO(body))
        self.assertEqual(self.ask(error=err), checks("A"))

    def test_other_errors_and_odd_answers_are_nothing(self):
        for e in (urllib.error.HTTPError("u", 403, "x", {}, io.BytesIO(b"{}")), urllib.error.URLError("down"), OSError("gone"), ValueError("not json")):
            self.assertIsNone(self.ask(error=e))
        for odd in ({"status": "ok"}, [], "text", {"checks": "no"}):
            self.assertIsNone(self.ask(odd))


class Line(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.services = [{"id": "r1", "name": "Reelix", "type": "link", "icon": "reelix", "url": "http://reelix:7700", "api_key": "k", "enabled": True}]

    def line(self, health):
        with mock.patch.object(rsh, "_health", lambda r: health):
            return rsh.line(self.services, self.dir.name)

    def test_the_line_with_a_link_to_the_page_that_lists_them(self):
        rsh.record(self.dir.name, [{"enabled": True}] * 39 + [{"enabled": False}] + [{"enabled": True}])
        got = self.line(checks("A", "B", "C"))
        self.assertEqual(got, {"r1": {"text": "3 of 40 sites failing", "href": "/settings-reelix.html#rx-indexers"}})

    def test_reelix_not_answering_says_nothing(self):
        rsh.record(self.dir.name, [{"enabled": True}] * 40)
        self.assertEqual(self.line(None), {})

    def test_an_old_total_is_not_used(self):
        rsh.record(self.dir.name, [{"enabled": True}] * 40)
        with open(os.path.join(self.dir.name, rsh.FILE), encoding="utf-8") as f:
            got = json.load(f)
        got["at"] = time.time() - 8 * 86400
        with open(os.path.join(self.dir.name, rsh.FILE), "w", encoding="utf-8") as f:
            json.dump(got, f)
        self.assertEqual(self.line(checks("A"))["r1"]["text"], "1 site failing")

    def test_no_key_means_no_question_at_all(self):
        self.services[0]["api_key"] = ""
        with mock.patch.object(rsh, "_health", side_effect=AssertionError("must not ask")):
            self.assertEqual(rsh.line(self.services, self.dir.name), {})

    def test_the_total_is_written_once_and_again_only_when_it_changes(self):
        rsh.record(self.dir.name, [{"enabled": True}] * 4)
        first = os.stat(os.path.join(self.dir.name, rsh.FILE)).st_mtime_ns
        rsh.record(self.dir.name, [{"enabled": True}] * 4)
        self.assertEqual(os.stat(os.path.join(self.dir.name, rsh.FILE)).st_mtime_ns, first)
        rsh.record(self.dir.name, [{"enabled": True}] * 5)
        self.assertEqual(rsh.read(self.dir.name)["enabled"], 5)

    def test_a_damaged_file_is_nothing(self):
        with open(os.path.join(self.dir.name, rsh.FILE), "w", encoding="utf-8") as f:
            f.write("{no")
        self.assertEqual(rsh.read(self.dir.name), {})


if __name__ == "__main__":
    unittest.main()
