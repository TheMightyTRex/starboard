"""The picture cache (12 November 2026): counted, swept after four weeks unused, cleared on request."""
import os
import tempfile
import time
import unittest

from starboard import picture_cache as pc


class Cache(unittest.TestCase):
    def test_stats_sweep_clear(self):
        with tempfile.TemporaryDirectory() as d:
            lib = os.path.join(d, "posters", "library")
            os.makedirs(lib)
            for name, age_days in (("posters/a.jpg", 1), ("posters/library/b.img", 40), ("posters/library/c.img", 3)):
                p = os.path.join(d, name)
                open(p, "wb").write(b"x" * 10)
                t = time.time() - age_days * 86400
                os.utime(p, (t, t))
            open(os.path.join(d, "keep.json"), "w").write("{}")  # outside the cache: never touched
            self.assertEqual(pc.stats(d)["pictures"], 3)
            self.assertEqual(pc.sweep(d), 1)
            self.assertEqual(pc.clear(d), 2)
            self.assertEqual(pc.stats(d)["pictures"], 0)
            self.assertTrue(os.path.isdir(lib))
            self.assertTrue(os.path.exists(os.path.join(d, "keep.json")))


if __name__ == "__main__":
    unittest.main()
