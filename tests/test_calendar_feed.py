"""The calendar feed (DASH-67, DASH-469): /calendar.ics with a token that opens that file and nothing else, and the
iCalendar it gives (RFC 5545: CRLF, folding at 75 octets, escaping, UID and DTSTAMP, all-day release dates)."""
import datetime as dt
import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from unittest import mock

from starboard import api_v1, auth, calendar_feed, services
from starboard.server import make_server

STAMP = dt.datetime(2026, 11, 19, 12, 0, 0, tzinfo=dt.timezone.utc)
TYPES = {"son": "sonarr", "rad": "radarr", "lid": "lidarr", "rea": "readarr", "rlx": "link"}
ITEMS = [
    {"service": "son", "service_name": "Sonarr", "title": "Example Show", "detail": "S02E03 · Lighthouses, part one; again",
     "when": "2026-11-20T21:00:00Z", "have": False, "item_id": 7, "overview": "A line\nand another, with a back\\slash"},
    {"service": "rad", "service_name": "Radarr", "title": "Example Film", "detail": "Film", "when": "2026-11-21T00:00:00Z",
     "have": True, "item_id": 9, "overview": ""},
    {"service": "lid", "service_name": "Lidarr", "title": "Example Band", "detail": "Example Album", "when": "2026-11-22T00:00:00Z",
     "have": False, "item_id": 3, "overview": ""},
    {"service": "rea", "service_name": "Readarr", "title": "Example Book", "detail": "An Author", "when": "2026-11-23",
     "have": False, "item_id": 4, "overview": "Ünïcödé " * 30},
    {"service": "rlx", "service_name": "Reelix", "kind": "radio", "title": "The Example Hour", "detail": "Series 4, episode 2",
     "when": "2026-11-24T09:00:00+01:00", "have": False, "item_id": 5, "overview": ""},
]


def unfold(text):
    return text.replace("\r\n ", "")


class IcsTest(unittest.TestCase):
    def setUp(self):
        self.raw = calendar_feed.ics(ITEMS, TYPES, "Home, sweet; home", STAMP)
        self.text = self.raw.decode("utf-8")

    def test_crlf_line_endings_only(self):
        self.assertTrue(self.text.endswith("\r\n"))
        self.assertNotIn("\n", self.text.replace("\r\n", ""))
        self.assertNotIn("\r", self.text.replace("\r\n", ""))

    def test_lines_are_folded_at_75_octets(self):
        lines = self.raw.split(b"\r\n")
        self.assertTrue(any(line.startswith(b" ") for line in lines), "the long description is folded")
        for line in lines:
            self.assertLessEqual(len(line), 75, line)
            line.decode("utf-8")  # never split inside a character

    def test_fold_keeps_multibyte_characters_whole(self):
        long = "DESCRIPTION:" + "é" * 100
        folded = calendar_feed.fold(long)
        for part in folded.encode().split(b"\r\n"):
            self.assertLessEqual(len(part), 75)
            part.decode("utf-8")
        self.assertEqual(unfold(folded), long + "\r\n")

    def test_text_is_escaped(self):
        self.assertEqual(calendar_feed.escape("a,b;c\\d\ne"), "a\\,b\\;c\\\\d\\ne")
        text = unfold(self.text)
        self.assertIn("X-WR-CALNAME:Home\\, sweet\\; home: Coming up\r\n", text)
        self.assertIn("SUMMARY:Example Show · S02E03 · Lighthouses\\, part one\\; again\r\n", text)
        self.assertIn("A line\\nand another\\, with a back\\\\slash", text)

    def test_calendar_shape(self):
        text = unfold(self.text)
        self.assertTrue(text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:"))
        self.assertTrue(text.endswith("END:VCALENDAR\r\n"))
        self.assertEqual(text.count("BEGIN:VEVENT"), len(ITEMS))
        self.assertEqual(text.count("END:VEVENT"), len(ITEMS))

    def test_every_event_has_a_uid_and_dtstamp(self):
        events = re.findall(r"BEGIN:VEVENT\r\n(.*?)END:VEVENT", unfold(self.text), re.S)
        uids = set()
        for e in events:
            uid = re.search(r"^UID:(.+)\r$", e, re.M).group(1)
            uids.add(uid)
            self.assertIn("DTSTAMP:20261119T120000Z\r\n", e)
        self.assertEqual(len(uids), len(ITEMS))
        again = calendar_feed.ics(ITEMS, TYPES, "Other", STAMP + dt.timedelta(days=1)).decode()
        self.assertEqual(uids, set(re.findall(r"^UID:(.+)\r$", unfold(again), re.M)), "the same release keeps its UID")

    def test_release_dates_are_all_day_and_episodes_are_timed(self):
        text = unfold(self.text)
        self.assertIn("DTSTART;VALUE=DATE:20261121\r\nDTEND;VALUE=DATE:20261122\r\n", text)  # the film
        self.assertIn("DTSTART;VALUE=DATE:20261122\r\n", text)  # the album
        self.assertIn("DTSTART;VALUE=DATE:20261123\r\n", text)  # the book, a date alone
        self.assertIn("DTSTART:20261120T210000Z\r\nDTEND:20261120T213000Z\r\n", text)  # the episode, in UTC
        self.assertIn("DTSTART:20261124T080000Z\r\n", text)  # radio, from +01:00 to UTC
        self.assertIn("SUMMARY:Example Book by An Author\r\n", text)
        self.assertIn("SUMMARY:Example Film\r\n", text)

    def test_one_event_per_release(self):
        text = calendar_feed.ics(ITEMS + ITEMS[:1], TYPES, "Starboard", STAMP).decode()
        self.assertEqual(text.count("BEGIN:VEVENT"), len(ITEMS))

    def test_no_date_no_event(self):
        text = calendar_feed.ics([dict(ITEMS[0], when="")], TYPES, "Starboard", STAMP).decode()
        self.assertNotIn("BEGIN:VEVENT", text)


class TokenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_stored_hashed_and_private(self):
        token = calendar_feed.make(self.tmp.name)
        path = os.path.join(self.tmp.name, calendar_feed.FILE)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn(token, raw)
        self.assertNotIn(token[len(calendar_feed.PREFIX):], raw)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertNotIn("hash", calendar_feed.status(self.tmp.name))

    def test_a_new_token_stops_the_old_one(self):
        old = calendar_feed.make(self.tmp.name)
        self.assertTrue(calendar_feed.valid(self.tmp.name, old))
        new = calendar_feed.make(self.tmp.name)
        self.assertFalse(calendar_feed.valid(self.tmp.name, old))
        self.assertTrue(calendar_feed.valid(self.tmp.name, new))
        calendar_feed.stop(self.tmp.name)
        self.assertFalse(calendar_feed.valid(self.tmp.name, new))
        self.assertIsNone(calendar_feed.status(self.tmp.name)["made_at"])

    def test_compared_in_constant_time(self):
        token = calendar_feed.make(self.tmp.name)
        with mock.patch("starboard.calendar_feed.hmac.compare_digest", return_value=False) as cmp:
            self.assertFalse(calendar_feed.valid(self.tmp.name, token))
        cmp.assert_called_once()

    def test_odd_tokens_refused(self):
        calendar_feed.make(self.tmp.name)
        for t in ("", None, "sbcal_", "sb_read_abcdef_" + "x" * 40, "sbcal_" + "x" * 43 + "\n", ["sbcal_x"]):
            self.assertFalse(calendar_feed.valid(self.tmp.name, t))


class FeedRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        r, _ = cls.request(None, "POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=False)
        cls.cookie = r.getheader("Set-Cookie").split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def setUp(self):
        services.forget()
        self.app.limits.clear("127.0.0.1")
        api_v1._buckets.pop("calendar-feed", None)
        patch = mock.patch("starboard.services.calendar", return_value={"items": ITEMS[:2], "errors": []})
        self.calendar = patch.start()
        self.addCleanup(patch.stop)

    def request(self, method, path, body=None, headers=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", FeedRouteTest.port, timeout=10)
        h = {"Content-Type": "application/json"}
        if method != "GET":
            h["X-Starboard"] = "1"
        if cookie:
            h["Cookie"] = FeedRouteTest.cookie
        h.update(headers or {})
        conn.request(method, path, json.dumps(body) if body is not None else None, h)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        try:
            return r, json.loads(raw)
        except ValueError:
            return r, raw

    def make(self):
        r, body = self.request("POST", "/api/calendar-feed", {})
        self.assertEqual(r.status, 200, body)
        self.assertEqual(r.getheader("Cache-Control"), "no-store")
        self.assertTrue(body["made_at"])
        return body["path"]

    def test_the_token_opens_the_feed(self):
        path = self.make()
        r, raw = self.request("GET", path, cookie=False)
        self.assertEqual(r.status, 200)
        self.assertEqual(r.getheader("Content-Type"), "text/calendar; charset=utf-8")
        self.assertIn("private, max-age=", r.getheader("Cache-Control"))
        self.assertTrue(raw.startswith(b"BEGIN:VCALENDAR\r\n"))
        start, end = self.calendar.call_args.kwargs["start"], self.calendar.call_args.kwargs["end"]
        self.assertLessEqual((end - start).days, 62)  # what services.calendar allows in one go
        r2, raw2 = self.request("GET", path, headers={"If-None-Match": r.getheader("ETag")}, cookie=False)
        self.assertEqual(r2.status, 304)
        self.assertEqual(self.calendar.call_count, 1, "the shared answer is used again")

    def test_a_new_token_stops_the_old_address(self):
        old = self.make()
        new = self.make()
        self.assertEqual(self.request("GET", old, cookie=False)[0].status, 404)
        self.assertEqual(self.request("GET", new, cookie=False)[0].status, 200)
        r, body = self.request("DELETE", "/api/calendar-feed")
        self.assertEqual(r.status, 200)
        self.assertIsNone(body["made_at"])
        self.assertEqual(self.request("GET", new, cookie=False)[0].status, 404)

    def test_the_token_opens_nothing_else(self):
        token = self.make().split("token=", 1)[1]
        for path in ("/api/calendar", "/api/config", "/api/calendar-feed", "/upcoming.html", "/api/v1/apps"):
            for how in ({"Authorization": f"Bearer {token}"}, {"Cookie": f"starboard={token}"}):
                r, _ = self.request("GET", f"{path}?token={token}", headers=how, cookie=False)
                self.assertIn(r.status, (303, 401), f"{path} {how}")

    def test_an_api_key_or_no_token_does_not_open_the_feed(self):
        self.make()
        key, _ = api_v1.create_key(self.tmp.name, "Reader", "read", [], 90)
        for path, headers in (("/calendar.ics", {}), (f"/calendar.ics?token={key}", {}),
                              ("/calendar.ics", {"Authorization": f"Bearer {key}"})):
            self.assertEqual(self.request("GET", path, headers=headers, cookie=False)[0].status, 404, path)
        # A signed-in browser's session does not open it either: the token is the only way in.
        self.assertEqual(self.request("GET", "/calendar.ics")[0].status, 404)

    def test_refused_tokens_count_towards_the_lockout(self):
        self.make()
        bad = "/calendar.ics?token=sbcal_" + "x" * 43
        statuses = [self.request("GET", bad, cookie=False)[0].status for _ in range(self.app.limits.limit + 1)]
        self.assertEqual(statuses[-1], 429)
        self.assertTrue(all(s == 404 for s in statuses[:-1]))
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl"), encoding="utf-8") as f:
            self.assertIn("calendar_refused", f.read())

    def test_rate_limited_like_api_keys(self):
        path = self.make()
        api_v1._buckets["calendar-feed"] = (0, __import__("time").monotonic())
        r, _ = self.request("GET", path, cookie=False)
        self.assertEqual(r.status, 429)
        self.assertTrue(r.getheader("Retry-After"))

    def test_every_app_failing_is_not_kept_as_an_empty_calendar(self):
        path = self.make()
        self.calendar.return_value = {"items": [], "errors": [{"service": "x", "message": "Cannot reach Sonarr"}]}
        self.assertEqual(self.request("GET", path, cookie=False)[0].status, 503)
        self.calendar.return_value = {"items": ITEMS[:1], "errors": []}
        self.assertEqual(self.request("GET", path, cookie=False)[0].status, 200)

    def test_making_an_address_needs_the_dashboard(self):
        r, _ = self.request("POST", "/api/calendar-feed", {}, cookie=False)
        self.assertEqual(r.status, 401)
        r, _ = self.request("POST", "/api/calendar-feed", {}, headers={"X-Starboard": "0"})
        self.assertEqual(r.status, 403)
        r, body = self.request("GET", "/api/calendar-feed")
        self.assertEqual(r.status, 200)
        self.assertNotIn("path", body)
        self.assertNotIn("hash", body)

    def test_unknown_host_names_are_refused(self):
        path = self.make()
        r, _ = self.request("GET", path, headers={"Host": "calendar.attacker.example"}, cookie=False)
        self.assertEqual(r.status, 421)



if __name__ == "__main__":
    unittest.main()
