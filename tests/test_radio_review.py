"""Radio library review and add a show from a link (DASH-212): files that match no episode grouped by podcast, matched
by hand to an episode of the show that covers them, Read the library again, and a show followed by its link."""
import unittest
from unittest import mock

from starboard import radio_import, radio_review

REVIEW = {"synced_at": "2026-11-13T06:00:00Z",
          "unmatched_shows": [{"abs_item_id": "li_a", "title": "Waiting", "file_count": 4}],
          "unmatched_files": [
              {"id": 1, "abs_item_id": "li_x", "item_title": "Example Hour", "title": "Tides", "size": 10},
              {"id": 2, "abs_item_id": "li_x", "item_title": "Example Hour", "title": "Storms", "size": 5},
              {"id": 3, "abs_item_id": "li_q", "item_title": "Quiz", "title": "Round one"}]}
SHOWS = {"items": [{"id": 7, "title": "Example Hour", "abs_item_id": "li_x"}, {"id": 8, "title": "Other"}], "total": 2}
EPISODES = {"episodes": [
    {"id": 70, "series_number": 4, "number": 1, "title": "Tides", "first_broadcast": "2026-11-05T19:00:00Z", "status": "in_library", "file_id": 9},
    {"id": 71, "series_number": 4, "number": 2, "title": "Storms", "first_broadcast": "2026-11-12T19:00:00Z", "status": "wanted"},
    {"id": 72, "number": 3, "title": "Islands", "status": "not_released"}]}


class Review(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def fake(cfg, method, path, body=None, timeout=60):
            self.calls.append((method, path, body))
            if path == "/radio/library/review":
                return REVIEW
            if path.startswith("/radio/shows?"):
                return SHOWS
            if path == "/radio/shows/7/episodes":
                return EPISODES
            if path.startswith("/radio/episodes/"):
                return {"id": 71, "title": "Storms"}
            if path == "/command":
                return {"job_id": 3}
            if path.startswith("/radio/preview"):
                return {"show": {"provider": "bbc", "external_id": "b0", "title": "Keepers", "station_name": "Radio 4", "artwork_url": "http://plain.invalid/a.jpg",
                                 "web_url": "https://www.bbc.co.uk/programmes/b0"},
                        "series_count": 2, "episode_count": 14, "latest_episodes": [{"title": "One", "duration_secs": 60}]}
            if path == "/radio/rootfolders":
                return [{"id": 4, "path": "/data/media/radio", "accessible": True}]
            if path == "/radio/shows":
                return {"id": 12, "title": "Keepers"}
            return {}
        self.patch = mock.patch.object(radio_import, "_call", side_effect=fake)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_files_are_grouped_by_podcast_with_the_show_that_covers_them(self):
        r = radio_review.review(None)
        self.assertTrue(r["read"])
        self.assertEqual((r["shows_waiting"], r["shows_waiting_files"], r["files"]), (1, 4, 3))
        first, second = r["groups"]
        self.assertEqual((first["podcast"], first["files"], first["size"], first["show_id"]), ("Example Hour", 2, 15, 7))
        self.assertIsNone(second["show_id"])

    def test_a_podcasts_files_offer_only_episodes_with_no_file(self):
        r = radio_review.files(None, "li_x")
        self.assertEqual([f["id"] for f in r["files"]], [1, 2])
        self.assertEqual(r["episodes"], [{"id": 71, "label": "S04E02 · Storms · 12 November 2026"}, {"id": 72, "label": "Episode 3 · Islands"}])
        with self.assertRaises(ValueError):
            radio_review.files(None, "li_none")

    def test_match_and_read_again_ask_reelix(self):
        self.assertEqual(radio_review.match(None, "2", 71)["done"], "Matched to Storms")
        self.assertIn(("PUT", "/radio/episodes/71/file", {"file_id": 2}), self.calls)
        with self.assertRaises(ValueError):
            radio_review.match(None, "x", 71)
        self.assertEqual(radio_review.rescan(None)["done"], "Reelix is reading the library again")
        self.assertIn(("POST", "/command", {"name": "RescanRadioLibrary", "show_ids": []}), self.calls)

    def test_a_link_is_previewed_without_saving_and_pictures_only_over_https(self):
        p = radio_review.preview(None, " https://www.bbc.co.uk/programmes/b0 ")
        self.assertEqual((p["title"], p["from"], p["episodes"], p["picture"]), ("Keepers", "Radio 4", 14, ""))
        self.assertTrue(self.calls[-1][1].startswith("/radio/preview?link=https%3A%2F%2Fwww.bbc.co.uk"))
        for bad in ("", "bbc.co.uk/programmes/b0", "javascript:alert(1)", "https://x.invalid/" + "a" * 2100):
            with self.assertRaises(ValueError):
                radio_review.preview(None, bad)

    def test_follow_adds_by_link_into_the_radio_folder_and_searches(self):
        out = radio_review.add(None, "https://www.bbc.co.uk/programmes/b0", "from_now_on")
        self.assertEqual(out["show_id"], 12)
        self.assertIn(("POST", "/radio/shows", {"link": "https://www.bbc.co.uk/programmes/b0", "follow": "from_now_on", "monitored": True,
                                                "root_folder_id": 4}), self.calls)
        self.assertIn(("POST", "/radio/shows/12/search", {}), self.calls)
        self.assertEqual(out["done"], "Keepers added. Reelix is looking for its episodes")
        with self.assertRaises(ValueError):
            radio_review.add(None, "https://x.invalid/feed", "everything")


if __name__ == "__main__":
    unittest.main()
