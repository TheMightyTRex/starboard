"""Discover settings and Recently added (DASH-303): which rows each area shows and their order, kept for the account,
and Library walls sorted by Recently added following what arrived."""
import os
import tempfile
import unittest

from starboard import discover_feeds as df, library

LISTED = [{"id": "trending", "title": "Trending this week"}, {"id": "popular", "title": "Popular"},
          {"id": "soon", "title": "Coming soon"}]


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.data = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def test_nothing_saved_keeps_reelix_order(self):
        self.assertEqual(df.arrange(LISTED, None), LISTED)
        got = df.describe(self.data, LISTED, "films")
        self.assertEqual([(r["id"], r["shown"]) for r in got["rows"]], [("trending", True), ("popular", True), ("soon", True)])
        self.assertFalse(got["changed"])

    def test_order_and_hidden_are_saved_cleaned_and_applied(self):
        got = df.save_layout(self.data, LISTED, "films", ["soon", "made-up", "trending"], ["popular", "made-up"])
        self.assertEqual([(r["id"], r["shown"]) for r in got["rows"]], [("soon", True), ("trending", True), ("popular", False)])
        self.assertTrue(got["changed"])
        saved = df.layout(self.data)["films"]
        self.assertEqual(saved, {"order": ["soon", "trending", "popular"], "hidden": ["popular"]})
        self.assertEqual([r["id"] for r in df.arrange(LISTED, saved)], ["soon", "trending"])
        self.assertEqual(oct(os.stat(os.path.join(self.data, "library", "discover-layout.json")).st_mode & 0o777), "0o600")
        # A row Reelix adds later comes at the end; the other area is untouched.
        more = LISTED + [{"id": "new", "title": "New row"}]
        self.assertEqual([r["id"] for r in df.arrange(more, saved)], ["soon", "trending", "new"])
        self.assertNotIn("tv", df.layout(self.data))

    def test_at_least_one_row_and_put_back(self):
        with self.assertRaises(ValueError):
            df.save_layout(self.data, LISTED, "films", [], ["trending", "popular", "soon"])
        df.save_layout(self.data, LISTED, "films", ["soon"], [])
        got = df.reset_layout(self.data, LISTED, "films")
        self.assertFalse(got["changed"])
        self.assertEqual([r["id"] for r in got["rows"]], ["trending", "popular", "soon"])


GENRES = [{"id": "genre/movie/35", "title": "Comedy", "genre": True}, {"id": "genre/movie/878", "title": "Science fiction", "genre": True}]


class GenreRowsTest(unittest.TestCase):
    """DASH-395: a row for each genre, in the same list, unticked until the person ticks it."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.data = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def test_genre_rows_start_hidden_and_listed_at_the_end(self):
        self.assertEqual([r["id"] for r in df.arrange(LISTED + GENRES, None)], ["trending", "popular", "soon"])
        got = df.describe(self.data, LISTED + GENRES, "films")
        self.assertEqual([(r["id"], r["shown"], r.get("genre", False)) for r in got["rows"]],
                         [("trending", True, False), ("popular", True, False), ("soon", True, False),
                          ("genre/movie/35", False, True), ("genre/movie/878", False, True)])

    def test_a_ticked_genre_shows_where_it_is_put(self):
        listed = LISTED + GENRES
        df.save_layout(self.data, listed, "films", ["genre/movie/35", "trending", "popular", "soon", "genre/movie/878"], ["genre/movie/878"])
        saved = df.layout(self.data)["films"]
        self.assertEqual([r["id"] for r in df.arrange(listed, saved)], ["genre/movie/35", "trending", "popular", "soon"])
        # A genre Reelix adds later starts hidden, though it is not in the saved hidden list.
        later = listed + [{"id": "genre/movie/37", "title": "Western", "genre": True}]
        self.assertNotIn("genre/movie/37", [r["id"] for r in df.arrange(later, saved)])
        self.assertFalse([r for r in df.describe(self.data, later, "films")["rows"] if r["id"] == "genre/movie/37"][0]["shown"])

    def test_a_layout_saved_before_genre_rows_keeps_them_hidden(self):
        df.save_layout(self.data, LISTED, "films", ["soon"], ["popular"])
        saved = df.layout(self.data)["films"]
        self.assertEqual([r["id"] for r in df.arrange(LISTED + GENRES, saved)], ["soon", "trending"])

    def test_genres_alone_cannot_be_the_last_row_hidden(self):
        with self.assertRaises(ValueError):
            df.save_layout(self.data, LISTED + GENRES, "films", [], [r["id"] for r in LISTED + GENRES])


class RecentlyAddedWallTest(unittest.TestCase):
    def test_the_wall_follows_what_arrived_then_when_listed(self):
        index = {"items": [{"i": 1, "t": "Brought in long ago", "s": "a", "l": "A", "a": 100, "w": "in_library", "f": []},
                           {"i": 2, "t": "Listed later", "s": "b", "l": "B", "a": 200, "w": "in_library", "f": []},
                           {"i": 3, "t": "Same day", "s": "c", "l": "C", "a": 100, "w": "in_library", "f": []}]}
        plain = library.wall(index, "tv", sort="added")
        self.assertEqual([c["title"] for c in plain["items"]][0], "Listed later")
        arrived = library.wall(index, "tv", sort="added", arrived={("tv", 3): 300})
        self.assertEqual([c["title"] for c in arrived["items"]], ["Same day", "Listed later", "Brought in long ago"])


if __name__ == "__main__":
    unittest.main()
