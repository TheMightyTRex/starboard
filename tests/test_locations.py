"""Settings pattern 4, the location picker (DASH-310): an app's folder in words, as the computer sees it, and back."""
import unittest

from starboard import locations

REELIX = {"Mounts": [{"Type": "bind", "Source": "/srv/stack/config/reelix", "Destination": "/config"},
                     {"Type": "bind", "Source": "/mnt/pool", "Destination": "/data"},
                     {"Type": "volume", "Source": "x", "Destination": "/cache"}]}


class Locations(unittest.TestCase):
    def setUp(self):
        self.m = locations.mounts_of("reelix", inspect=lambda name: REELIX)

    def test_mounts_leave_out_reelix_settings_folder(self):
        self.assertEqual(self.m, [("/mnt/pool", "/data")])

    def test_jellyfin_config_is_offered(self):
        m = locations.mounts_of("jellyfin", inspect=lambda name: REELIX)
        self.assertIn(("/srv/stack/config/reelix", "/config"), m)

    def test_unknown_app_refused(self):
        with self.assertRaises(ValueError):
            locations.mounts_of("sonarr", inspect=lambda name: {})

    def test_both_ways(self):
        self.assertEqual(locations.to_host("/data/media/music", self.m), "/mnt/pool/media/music")
        self.assertEqual(locations.to_app("/mnt/pool/downloads/direct", self.m), "/data/downloads/direct")
        self.assertIsNone(locations.to_app("/home/sam", self.m))
        self.assertEqual(locations.to_host("/srv/x", [("/", "/")]), "/srv/x")

    def test_words(self):
        self.assertEqual(locations.words("/data/media/music/direct", self.m), "Media, Music, Direct")
        self.assertEqual(locations.words("/data/media/films-4k", self.m), "Media, Films 4k")
        self.assertEqual(locations.words("/data", self.m), "The whole media folder")

    def test_describe_gives_free_space_and_suggestion(self):
        got = locations.describe("reelix", "/data/media/movies/", "movies", mounts=self.m,
                                 read=lambda host: {"exists": True, "free": 812 * 10 ** 9})
        self.assertEqual(got["path"], "/data/media/movies")
        self.assertEqual(got["host"], "/mnt/pool/media/movies")
        self.assertEqual(got["free"], 812 * 10 ** 9)
        self.assertEqual(got["suggest"], "/data/media/movies")
        self.assertTrue(got["ok"] and got["can_browse"])

    def test_describe_outside_what_the_app_sees(self):
        got = locations.describe("reelix", "/config/x", mounts=self.m, read=lambda host: {})
        self.assertFalse(got["ok"])
        self.assertIn("Reelix cannot see that folder", got["lines"][0])

    def test_without_docker_browse_is_off_and_typing_works(self):
        self.assertEqual(locations.describe("reelix", "/data/media/movies", mounts=[])["words"], "Media, Films")
        got = locations.describe("reelix", "/data/media", "direct", mounts=[])
        self.assertFalse(got["can_browse"])
        self.assertTrue(got["ok"])
        self.assertEqual(got["suggest"], "/data/downloads/direct")

    def test_chosen_in_browse_comes_back_as_the_app_sees_it(self):
        self.assertEqual(locations.chosen("reelix", "/mnt/pool/media/radio/", mounts=self.m), "/data/media/radio")
        with self.assertRaises(ValueError):
            locations.chosen("reelix", "/srv/other", mounts=self.m)

    def test_host_suggestions(self):
        got = locations.describe("host", "", "media", mounts=[("/", "/")], host_defaults={"media": "/srv/media"})
        self.assertEqual(got["suggest"], "/srv/media")
        self.assertEqual(got["words"], "Not set")


if __name__ == "__main__":
    unittest.main()
