"""Reelix's direct downloads in Starboard's Reelix health (DASH-218): what Reelix said with the admin password is kept,
and a broken yt-dlp, an expired Spotify sign-in or failing YouTube downloads show with what to do."""
import tempfile
import time
import unittest
from unittest import mock

from starboard import reelix_direct_health as rdh, services

REELIX = [{"id": "rx", "name": "Reelix", "type": "link", "icon": "reelix", "enabled": True,
           "url": "http://reelix:7700", "api_key": "made-up-key"}]


def state(on=True, ytdlp=True, ffmpeg=True, session=True, connected=True, problem=""):
    return {"on": on, "tools": [{"tool": "yt-dlp", "ok": ytdlp}, {"tool": "Native Spotify client", "ok": True},
                                {"tool": "FFmpeg", "ok": ffmpeg}, {"tool": "Spotify session", "ok": session}],
            "spotify": {"connected": connected, "problem": problem}}


class Problems(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def found(self, live=None):
        return rdh.problems(rdh.read(self.dir), live)

    def test_all_well_says_nothing(self):
        rdh.record(self.dir, state=state())
        self.assertEqual(self.found(), [])

    def test_a_broken_yt_dlp_is_an_error_put_right_by_updating_reelix(self):
        rdh.record(self.dir, state=state(ytdlp=False))
        [p] = self.found()
        self.assertEqual(p["level"], "error")
        self.assertIn("yt-dlp", p["message"])
        self.assertEqual(p["fix"]["href"], "/apps-updates.html")

    def test_an_expired_spotify_session_only_after_it_was_connected(self):
        rdh.record(self.dir, state=state(session=False, connected=False))
        self.assertEqual(self.found(), [], "never connected: nothing to say")
        rdh.record(self.dir, state=state())
        rdh.record(self.dir, state=state(session=False, connected=False))
        [p] = self.found()
        self.assertIn("Spotify is no longer connected", p["message"])
        self.assertEqual(p["fix"]["href"], "/settings-reelix.html#rx-direct-h")

    def test_failing_youtube_downloads_point_at_an_update(self):
        rdh.record(self.dir, state=state())
        rdh.record(self.dir, queue={"items": [
            {"state": "failed", "source": "youtube", "message": "ERROR: [youtube] abc: Sign in to confirm you are not a bot"},
            {"state": "failed", "source": "youtube", "message": "No space left on device"},
            {"state": "completed", "source": "youtube", "message": "Download complete"}]})
        [p] = self.found()
        self.assertIn("YouTube downloads are failing", p["message"])
        self.assertIn("Sign in to confirm", p["message"])

    def test_nothing_when_direct_downloads_are_off_or_the_look_is_old(self):
        rdh.record(self.dir, state=state(on=False, ytdlp=False))
        self.assertEqual(self.found(), [])
        rdh.record(self.dir, state=state(ytdlp=False), now=time.time() - 8 * 86400)
        self.assertEqual(self.found(), [])
        self.assertFalse(rdh.wanted(self.dir))

    def test_a_live_answer_wins_over_the_last_look(self):
        rdh.record(self.dir, state=state(ytdlp=False))
        self.assertEqual(self.found(live=[{"tool": "yt-dlp", "available": True, "detail": ""}]), [])


class InReelixHealth(unittest.TestCase):
    def setUp(self):
        services.FIRST_SEEN.clear()
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_shown_with_reelixs_own_checks_and_the_manager_key_tried_first(self):
        rdh.record(self.tmp.name, state=state(ytdlp=False))
        calls = []

        def fake(service, path, *a, **k):
            calls.append(path)
            if path == "/downloads/health":
                raise services.ServiceError("Reelix answered 403")
            return {"checks": [{"source": "indexers", "level": "warning", "message": "Indexer YTS is unavailable"}]}
        with mock.patch.object(services, "_api", side_effect=fake):
            items = services.health(REELIX, data_dir=self.tmp.name)["items"]
        self.assertEqual(calls, ["/system/health", "/downloads/health"])
        self.assertEqual([i["source"] for i in items], ["indexers", "direct"])
        self.assertEqual(items[1]["fix"]["label"], "Apps, Updates")

    def test_not_asked_when_direct_downloads_were_never_seen_on(self):
        calls = []
        with mock.patch.object(services, "_api", side_effect=lambda s, p, *a, **k: calls.append(p) or {"checks": []}):
            services.health(REELIX, data_dir=self.tmp.name)
        self.assertEqual(calls, ["/system/health"])


if __name__ == "__main__":
    unittest.main()
