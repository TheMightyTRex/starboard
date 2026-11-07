"""Reelix radio in Starboard: Coming up and Downloads read Reelix's own API (DASH-93)."""

import datetime as dt
import unittest
from unittest import mock

from starboard import reelix_setup, services, stack

LINK = {"id": "reelix", "name": "Reelix", "type": "link", "url": "http://reelix:7979", "icon": "reelix", "enabled": True}
FILMS = {"id": "reelix-films", "name": "Reelix films", "type": "radarr", "url": "http://reelix:7979/radarr",
         "icon": "reelix", "api_key": "k1", "enabled": True}


class FakeReelix:
    def __init__(self, missing=False):
        self.calls = []
        self.missing = missing

    def __call__(self, service, path, params=None, method="GET", body=None, timeout=None):
        self.calls.append((service["url"], path, params, method))
        if self.missing:
            err = services.ServiceError("Reelix answered with error 404")
            err.status = 404
            raise err
        if path == "/radio/shows":
            return {"items": [{"id": 7, "title": "The Example Hour"}], "total": 1, "page": 1, "page_size": 20}
        if path == "/radio/shows/7/episodes":
            return {"series": [], "episodes": [
                {"id": 1, "series_number": 3, "number": 4, "title": "Tides", "first_broadcast": "2026-11-08T19:00:00Z",
                 "monitored": True, "status": "not_released", "synopsis": "A made-up episode."},
                {"id": 2, "series_number": 3, "number": 3, "title": "Old", "first_broadcast": "2026-10-01T19:00:00Z",
                 "monitored": True, "status": "in_library"},
                {"id": 3, "number": 5, "title": "Skipped", "first_broadcast": "2026-11-09T19:00:00Z",
                 "monitored": False, "status": "not_requested"}]}
        if path == "/queue":
            return {"items": [
                {"id": 11, "title": "Example.Hour.S03E02", "download_client": "NZBGet", "download_id": "x", "state": "downloading",
                 "client_state": "downloading", "progress": 0.5, "size": 1000, "eta_secs": 3725, "messages": [],
                 "media": {"kind": "radio_episode", "id": 2, "title": "Waves", "subtitle": "The Example Hour"},
                 "added": "2026-11-07T10:00:00Z"},
                {"id": 12, "title": "A.Film.2026", "state": "downloading", "progress": 0.1,
                 "media": {"kind": "movie", "id": 5, "title": "A Film"}}]}
        if method == "DELETE":
            return None
        raise AssertionError(path)


class RadioTest(unittest.TestCase):
    def setUp(self):
        services.forget()

    def test_radio_is_a_group_with_its_folder_in_reelix_and_audiobookshelf(self):
        self.assertIn("radio", [g[0] for g in stack.GROUPS])
        self.assertIn("radio", stack.APPS["reelix"]["groups"])
        self.assertIn("radio", stack.APPS["audiobookshelf"]["groups"])
        self.assertEqual(stack.DATA_FOLDERS["radio"], ["media/radio"])
        self.assertIn(("radio", "/radio/rootfolders", {"kind": "radio"}, "/data/media/radio"), reelix_setup.FOLDERS)

    def test_reelix_is_found_once_with_the_key_from_a_compatible_entry(self):
        found = services.reelix_native([LINK, FILMS, {**FILMS, "id": "reelix-series", "type": "sonarr", "url": "http://reelix:7979/sonarr"}])
        self.assertEqual(found, [{"id": "reelix", "name": "Reelix", "type": "link", "url": "http://reelix:7979/api/v1",
                                  "api_key": "k1", "link": "http://reelix:7979"}])

    def test_no_key_means_no_radio(self):
        self.assertEqual(services.reelix_native([LINK]), [])
        self.assertEqual(services.reelix_native([{**FILMS, "enabled": False}]), [])

    def test_coming_up_has_followed_shows_monitored_episodes_in_the_window(self):
        fake = FakeReelix()
        with mock.patch.object(services, "_api", fake), mock.patch.object(services, "_arrs", lambda s: []):
            out = services.calendar([LINK, FILMS], start=dt.date(2026, 11, 6), end=dt.date(2026, 11, 20))
        self.assertEqual(out["errors"], [])
        self.assertEqual(len(out["items"]), 1)
        row = out["items"][0]
        self.assertEqual((row["title"], row["detail"], row["kind"], row["slug"], row["have"], row["service_name"]),
                         ("The Example Hour", "Series 3, episode 4 · Tides", "radio", "7", False, "Reelix"))
        self.assertEqual(fake.calls[0][2]["followed"], "true")

    def test_downloads_has_radio_episodes_only(self):
        fake = FakeReelix()
        with mock.patch.object(services, "_api", fake), mock.patch.object(services, "_arrs", lambda s: []):
            out = services.queue([LINK, FILMS])
        self.assertEqual([r["id"] for r in out["items"]], [11])
        row = out["items"][0]
        self.assertEqual((row["title"], row["progress"], row["status"], row["time_left"], row["client"]),
                         ("The Example Hour · Waves", 50.0, "downloading", "0.01:02:05", "NZBGet"))

    def test_a_reelix_without_radio_adds_nothing_and_no_error(self):
        with mock.patch.object(services, "_api", FakeReelix(missing=True)), mock.patch.object(services, "_arrs", lambda s: []):
            self.assertEqual(services.calendar([LINK, FILMS], 14), {"items": [], "errors": []})
            self.assertEqual(services.queue([LINK, FILMS]), {"items": [], "errors": []})

    def test_one_busy_show_leaves_the_others(self):
        fake = FakeReelix()

        def busy(service, path, params=None, method="GET", body=None, timeout=None):
            if path == "/radio/shows":
                return {"items": [{"id": 6, "title": "Busy"}, {"id": 7, "title": "The Example Hour"}]}
            if path == "/radio/shows/6/episodes":
                raise services.ServiceError("database is locked")
            return fake(service, path, params, method, body, timeout)
        with mock.patch.object(services, "_api", busy), mock.patch.object(services, "_arrs", lambda s: []):
            out = services.calendar([LINK, FILMS], start=dt.date(2026, 11, 6), end=dt.date(2026, 11, 20))
        self.assertEqual(([i["title"] for i in out["items"]], out["errors"]), (["The Example Hour"], []))

    def test_removing_a_radio_download_uses_reelix_own_queue(self):
        fake = FakeReelix()
        reelix = services.reelix_native([LINK, FILMS])[0]
        with mock.patch.object(services, "_api", fake):
            services.radio_queue_action(reelix, 11, "block")
        self.assertEqual(fake.calls[-1], ("http://reelix:7979/api/v1", "/queue/11",
                                          {"remove_from_client": "true", "blocklist": "true", "skip_redownload": "true"}, "DELETE"))
        with self.assertRaises(services.ServiceError):
            services.radio_queue_action(reelix, 11, "explode")


if __name__ == "__main__":
    unittest.main()
