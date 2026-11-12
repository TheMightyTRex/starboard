"""Books and music actions, quality and folder, several at once (DASH-206) and the item extras (DASH-209)."""
import unittest
from unittest import mock

from starboard import item_extras, library


def recording(answers=None):
    calls = []

    def fake(service, path, params=None, method="GET", body=None, timeout=None):
        calls.append((method, path, body, params))
        for key, value in (answers or {}).items():
            if path == key:
                return value
        return {}
    return calls, fake


class BooksAndMusic(unittest.TestCase):
    def test_get_an_audiobook_follows_and_searches_that_format(self):
        calls, fake = recording()
        with mock.patch("starboard.services._api", side_effect=fake):
            said = library.act({}, "audiobooks", 9, "get")
        self.assertEqual([(m, p, b) for m, p, b, _ in calls], [
            ("PUT", "/books/monitor", {"book_ids": [9], "format": "audiobook", "monitored": True}),
            ("POST", "/books/search", {"kind": "item", "ids": [9], "format": "audiobook"})])
        self.assertIn("audiobook", said)

    def test_get_an_artist_searches_only_wanted_albums(self):
        albums = {"items": [{"id": 1, "monitored": True, "statistics": {"track_file_count": 0}},
                            {"id": 2, "monitored": True, "statistics": {"track_file_count": 5}},
                            {"id": 3, "monitored": False, "statistics": {"track_file_count": 0}}]}
        calls, fake = recording({"/albums": albums})
        with mock.patch("starboard.services._api", side_effect=fake):
            said = library.act({}, "music", 4, "get")
        self.assertEqual([p for m, p, b, _ in calls if p.endswith("/search")], ["/albums/1/search"])
        self.assertIn("1 album", said)


class QualityFolderAndBulk(unittest.TestCase):
    def test_change_sends_only_what_changed(self):
        calls, fake = recording()
        with mock.patch("starboard.services._api", side_effect=fake):
            said = library.change({}, "films", 7, profile_id=None, folder_id=2, move_files=False)
        self.assertEqual(calls[0][:3], ("PUT", "/movies/7", {"root_folder_id": 2, "move_files": False}))
        self.assertTrue(said.startswith("Folder changed"))
        with self.assertRaises(ValueError):
            library.change({}, "films", 7)
        with self.assertRaises(ValueError):
            library.change({}, "music", 7, profile_id=1)

    def test_bulk_follow_and_delete(self):
        calls, fake = recording()
        with mock.patch("starboard.services._api", side_effect=fake):
            library.bulk({}, "tv", ["3", "1", "3", "x"], "follow")
            said = library.bulk({}, "films", [5], "delete", delete_files=True)
        self.assertEqual(calls[0][:3], ("PUT", "/series/bulk", {"ids": [1, 3], "edit": {"monitored": True}}))
        self.assertEqual(calls[1][:3], ("DELETE", "/movies/bulk", {"ids": [5], "delete_files": True}))
        self.assertIn("with their files", said)
        with self.assertRaises(ValueError):
            library.bulk({}, "films", [], "follow")


class Extras(unittest.TestCase):
    def test_refresh_and_rescan(self):
        calls, fake = recording()
        with mock.patch("starboard.services._api", side_effect=fake):
            item_extras.refresh({}, "films", 7)
            item_extras.refresh({}, "tv", 3, rescan=True)
        self.assertEqual([(m, p) for m, p, *_ in calls], [("POST", "/movies/7/refresh"), ("POST", "/series/3/rescan")])

    def test_files_for_a_film_and_a_series(self):
        film = [{"file": {"id": 11, "relative_path": "Film (2020).mkv", "size": 5, "quality_name": "Bluray-1080p"}}]
        series = {"items": [{"id": 22, "path": "/tv/S/Season 2/b.mkv", "season_number": 2}, {"id": 21, "relative_path": "a.mkv", "season_number": 1}]}
        _, fake = recording({"/movies/7/files": film, "/episodefiles": series})
        with mock.patch("starboard.services._api", side_effect=fake):
            self.assertEqual(item_extras.files({}, "films", 7)[0]["quality"], "Bluray-1080p")
            names = [f["name"] for f in item_extras.files({}, "tv", 3)]
        self.assertEqual(names, ["a.mkv", "b.mkv"])

    def test_rename_preview_leaves_out_unchanged_files(self):
        preview = [{"file_id": 1, "existing_path": "a.mkv", "new_path": "A (2020).mkv"}, {"file_id": 2, "existing_path": "b.mkv", "new_path": "b.mkv"}]
        calls, fake = recording({"/rename/preview": preview})
        with mock.patch("starboard.services._api", side_effect=fake):
            changes = item_extras.rename_preview({}, "tv", 3)
            item_extras.rename({}, "tv", 3, [c["file_id"] for c in changes])
        self.assertEqual(calls[0][3], {"series_id": 3})
        self.assertEqual(changes, [{"file_id": 1, "now": "a.mkv", "after": "A (2020).mkv"}])
        self.assertEqual(calls[1][:3], ("POST", "/rename", {"kind": "series", "ids": [3], "file_ids": [1]}))

    def test_delete_a_file(self):
        calls, fake = recording()
        with mock.patch("starboard.services._api", side_effect=fake):
            item_extras.delete_file({}, "tv", 21)
        self.assertEqual(calls[0][:2], ("DELETE", "/episodefiles/21"))
        with self.assertRaises(ValueError):
            item_extras.delete_file({}, "books", 21)

    def test_history_in_plain_words(self):
        rows = {"items": [{"event_type": "download_folder_imported", "date": "2026-11-01T10:00:00Z", "source_title": "Show.S01E02",
                           "episode": {"season_number": 1, "episode_number": 2}, "indexer": "Site", "download_client": "qBittorrent"},
                          {"event_type": "something_new"}]}
        calls, fake = recording({"/history": rows})
        with mock.patch("starboard.services._api", side_effect=fake):
            got = item_extras.history({}, "music", 4)
        self.assertEqual(calls[0][3]["artist_id"], 4)
        self.assertEqual(got[0]["what"], "Imported")
        self.assertEqual(got[0]["episode"], "S1 E2")
        self.assertEqual(got[0]["where"], "Site · qBittorrent")
        self.assertEqual(got[1]["what"], "Something new")


class Podcasts(unittest.TestCase):
    """DASH-319: podcasts in the Radio tab, and how many episodes to keep."""

    def test_a_podcast_is_grouped_and_filtered(self):
        e = library._show({"id": 1, "title": "A", "provider": "podcastindex", "statistics": {}}, "http://r")
        self.assertIn("podcast", e["f"])
        self.assertEqual(e["g"], ["Podcasts"])
        e = library._show({"id": 2, "title": "B", "provider": "bbc", "station_name": "BBC Radio 4", "statistics": {}}, "http://r")
        self.assertIn("radio_show", e["f"])
        self.assertEqual(e["g"], ["BBC Radio 4"])

    def test_keep(self):
        calls, fake = recording()
        with mock.patch("starboard.services._api", side_effect=fake):
            said = library.act({}, "radio", 5, "keep", "10")
            library.act({}, "radio", 5, "keep", "all")
        self.assertEqual([c[2] for c in calls], [{"keep_episodes": 10}, {"keep_episodes": None}])
        self.assertIn("newest 10", said)
        with self.assertRaises(ValueError):
            library.act({}, "radio", 5, "keep", "7")
        with self.assertRaises(ValueError):
            library.act({}, "films", 5, "keep", "10")


if __name__ == "__main__":
    unittest.main()
