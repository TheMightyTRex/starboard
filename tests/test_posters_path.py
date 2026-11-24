"""DASH-531: a poster's file name is built from strict matches and the final path must stay in the posters folder."""
import os
import tempfile
import unittest
from unittest import mock

from starboard import posters


class PosterPath(unittest.TestCase):
    def test_a_normal_poster_is_one_file_in_the_folder(self):
        with tempfile.TemporaryDirectory() as d:
            path = posters.poster_path(d, "radarr", "movie", "123")
            self.assertEqual(path, os.path.join(os.path.realpath(d), "radarr-movie-123.jpg"))
            self.assertEqual(posters.poster_path(d, "radarr-2", "movie", 7), os.path.join(os.path.realpath(d), "radarr-2-movie-7.jpg"))
            self.assertEqual(posters.poster_path(d, "radarr", "movie", "0042"), os.path.join(os.path.realpath(d), "radarr-movie-42.jpg"))

    def test_hostile_ids_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            for item in ("../../etc/passwd", "1/../2", "12\n", "\n12", "", "12345678901", "-1", "1.5", "٣", "１", "1 ", " 1", "0x10", None):
                self.assertIsNone(posters.poster_path(d, "radarr", "movie", item), repr(item))
            for sid in ("../x", "a/b", "..", "", "A", "-a", "a" * 41, "a\n", "a.b", "a\\b", "/etc/x", "a\x00b"):
                self.assertIsNone(posters.poster_path(d, sid, "movie", "1"), repr(sid))
            for kind in ("../movie", "Movie", "", "movie/", "movie\n", "song", None):
                self.assertIsNone(posters.poster_path(d, "radarr", kind, "1"), repr(kind))

    def test_a_link_that_leaves_the_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
            os.symlink(os.path.join(outside, "stolen.jpg"), os.path.join(d, "radarr-movie-5.jpg"))
            self.assertIsNone(posters.poster_path(d, "radarr", "movie", "5"))

    def test_a_folder_that_is_itself_a_link_is_the_root(self):
        with tempfile.TemporaryDirectory() as d:
            real = os.path.join(d, "real")
            os.mkdir(real)
            os.symlink(real, os.path.join(d, "posters"))
            self.assertEqual(posters.poster_path(os.path.join(d, "posters"), "radarr", "movie", "5"), os.path.join(os.path.realpath(real), "radarr-movie-5.jpg"))

    def test_get_and_address_refuse_hostile_ids_before_any_file_or_request(self):
        svc = {"id": "radarr", "type": "radarr", "url": "http://127.0.0.1:1", "api_key": "k"}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(posters.urllib.request, "urlopen") as opened:
            for item in ("../../x", "12\n", "٣", "99999999999"):
                self.assertIsNone(posters.get(svc, "movie", item, d), repr(item))
                self.assertEqual(posters.address(svc, "movie", item), "")
            self.assertIsNone(posters.get({**svc, "id": "../evil"}, "movie", "1", d))
            opened.assert_not_called()
            self.assertEqual(os.listdir(d), [])
            self.assertEqual(posters.address(svc, "movie", 12), "/api/posters/radarr/movie/12")

    def test_a_kept_poster_is_read_back_from_the_same_path(self):
        svc = {"id": "radarr", "type": "radarr", "url": "http://127.0.0.1:1", "api_key": "k"}
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "radarr-movie-9.jpg"), "wb") as f:
                f.write(b"JPEG")
            self.assertEqual(posters.get(svc, "movie", "9", d), (b"JPEG", "image/jpeg"))


if __name__ == "__main__":
    unittest.main()
