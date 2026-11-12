"""Kavita in Install apps (owner, 12 November 2026): the ebook reader, reading the media folder only."""
import unittest

from starboard import setup_left, stack


class Kavita(unittest.TestCase):
    def test_offered_with_ebooks(self):
        k = stack.APPS["kavita"]
        self.assertIn("ebooks", k["groups"])
        self.assertIn("${DATA_DIR}/media:/media:ro", k["volumes"])  # reads, never writes, the library
        self.assertEqual(k["ports"], ["5000:5000"])
        self.assertTrue(all(":5000" not in p for key, a in stack.APPS.items() if key != "kavita" for p in a.get("ports", [])))

    def test_has_a_set_up_step(self):
        self.assertIn("kavita", {k for k, _, _ in setup_left.GUIDED})


if __name__ == "__main__":
    unittest.main()
