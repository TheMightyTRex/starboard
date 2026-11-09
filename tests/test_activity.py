"""History and the refused list, from Reelix (DASH-159), and Choose a download (library.releases and grab)."""
import unittest
from unittest import mock

from starboard import activity, library

REELIX = [{"id": "rx", "url": "http://r/api/v1", "api_key": "k", "name": "Reelix"}]


class History(unittest.TestCase):
    def test_rows_in_words(self):
        page = {"items": [{"id": 1, "event_type": "download_failed", "date": "2026-11-09T10:00:00Z",
                           "media": {"kind": "series", "id": 3, "title": "Ghosts"}, "episode": {"season_number": 6, "episode_number": 1},
                           "source_title": "Ghosts.S06E01", "quality": {"quality": "WEBDL-1080p"}, "indexer": "Site", "data": {"message": "stalled"}}],
                "total": 1}
        with mock.patch("starboard.services.reelix_native", return_value=REELIX), mock.patch("starboard.services._api", return_value=page) as api:
            out = activity.history([], "failed")
        self.assertEqual(api.call_args[0][2]["event_type"], "download_failed")
        row = out["items"][0]
        self.assertEqual((row["event"], row["what"], row["href"], row["message"]), ("Download failed", "Ghosts S06E01", "/library-tv-show.html?id=3", "stalled"))

    def test_take_off_the_refused_list(self):
        with mock.patch("starboard.services.reelix_native", return_value=REELIX), mock.patch("starboard.services._api") as api:
            activity.take_off([], 5)
        self.assertEqual((api.call_args[0][1], api.call_args.kwargs["method"]), ("/blocklist/5", "DELETE"))


class ChooseADownload(unittest.TestCase):
    def test_accepted_first_and_why_not(self):
        found = [{"guid": "b", "indexer_id": 1, "title": "B", "accepted": False, "rank": 0, "quality": {"quality": "HDTV-720p"},
                  "rejections": [{"reason": "Not wanted: 720p"}]},
                 {"guid": "a", "indexer_id": 2, "title": "A", "accepted": True, "rank": 3, "quality": {"quality": "WEBDL-1080p"}}]
        with mock.patch("starboard.services._api", return_value=found) as api:
            out = library.releases({}, "tv", 3, "season", season=2)
        self.assertEqual(api.call_args[0][2], {"series_id": 3, "season": 2})
        self.assertEqual([r["guid"] for r in out], ["a", "b"])
        self.assertEqual(out[1]["why_not"], ["Not wanted: 720p"])
        with mock.patch("starboard.services._api") as api:
            library.grab({}, "b", 1, force=True)
        self.assertEqual(api.call_args.kwargs["body"], {"guid": "b", "indexer_id": 1, "force": True})


if __name__ == "__main__":
    unittest.main()
