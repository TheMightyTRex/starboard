"""Optimisation review (owner, 13 November 2026: "Do a review to ensure everything is as optimised as possible"):
each Library wall page, filter and search read and parsed the whole index file again and folded every title for
each search (10,000 films: a 2.7 MB file, about 94 ms a wall page and 166 ms a search). The parsed index is now kept
while the file is unchanged, for a short time after its last use, with its titles folded once (DASH-397)."""

import json
import os
import tempfile
import time
import unittest
from unittest import mock

from starboard import group_complete, library

REELIX = {"name": "Reelix", "type": "link", "url": "http://127.0.0.1:1/api/v1", "api_key": "k"}


def entry(i, title, meta="", letter="H"):
    return {"i": i, "t": title, "s": library.sort_key(title), "l": letter, "m": meta, "w": "in_library", "f": [], "y": 2000 + i}


class KeptIndex(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.dir, "library"))
        self.write("films", [entry(1, "Harbour Lights", "2001"), entry(2, "Émile's Garden", "Mara Ellison", "E"), entry(3, "Salt Marsh", "Copper")])
        library._drop_kept()

    def tearDown(self):
        library._drop_kept()

    def write(self, tab, items):
        path = library._path(self.dir, tab)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"built": int(time.time()), "v": library.INDEX_VERSION, "items": items}, f)
        os.utime(path, ns=(time.time_ns(), time.time_ns()))

    def test_read_once_while_unchanged(self):
        real = json.load
        with mock.patch("starboard.library.json.load", side_effect=real) as parsed:
            for _ in range(5):
                library.load(self.dir, REELIX, "films")
                library.wall(library.load(self.dir, REELIX, "films"), "films", q="harbour")
                library.search_library(self.dir, "salt")
        self.assertEqual(parsed.call_count, 1)

    def test_a_new_file_is_read_again(self):
        self.assertEqual(library.wall(library.load(self.dir, REELIX, "films"), "films")["total"], 3)
        time.sleep(0.01)
        self.write("films", [entry(1, "Harbour Lights")])
        self.assertEqual(library.wall(library.load(self.dir, REELIX, "films"), "films")["total"], 1)

    def test_matching_is_unchanged(self):
        index = library.load(self.dir, REELIX, "films")
        for q, want in (("emile", [2]), ("ÉMILE garden", [2]), ("ellison", [2]), ("copper salt", [3]), ("harbour 2001", [1]),
                        ("harbour copper", []), ("", [1, 2, 3])):
            got = [c["id"] for c in library.wall(index, "films", q=q)["items"]]
            self.assertEqual(sorted(got), want, q)
        self.assertEqual([t["items"][0]["id"] for t in library.search_library(self.dir, "garden")], [2])

    def test_dropped_after_a_while_and_the_thread_ends(self):
        with mock.patch.object(library, "KEEP_INDEX", 0.2):
            library.load(self.dir, REELIX, "films")
            self.assertEqual(len(library._kept), 1)
            sweeper = library._sweeper
            sweeper.join(3)
        self.assertFalse(sweeper.is_alive())
        self.assertEqual(library._kept, {})
        self.assertIsNone(library._sweeper)

    def test_audiobook_series_do_not_change_the_kept_index(self):
        self.write("audiobooks", [{**entry(1, "One", "A"), "au": "A"}, {**entry(2, "Other", "B"), "au": "B"}])
        index = library.load(self.dir, REELIX, "audiobooks")
        series = {"rivers": {"name": "Rivers", "books": [{"title": "One", "author": "A", "seq": "1", "key": "one|a"}]}}
        with mock.patch.object(group_complete, "abs_series", return_value=series):
            tagged = group_complete.tag_audiobooks(index, [])
        self.assertEqual(tagged["items"][0]["g"], ["Rivers"])
        self.assertNotIn("g", library.load(self.dir, REELIX, "audiobooks")["items"][0])


if __name__ == "__main__":
    unittest.main()
