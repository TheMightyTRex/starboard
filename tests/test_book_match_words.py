"""Audiobook and book matches read well in the drop-down (owner, 13 November 2026: the names displayed badly)."""

import unittest

from starboard import media_import


def ol(name, works=None, top=None, oid="OL1A"):
    return {"openlibrary_id": oid, "name": name, "work_count": works, "top_work": top}


class BookMatchWords(unittest.TestCase):
    def test_count_first_then_a_short_best_known_work(self):
        got = media_import.book_matches([
            ol("Harry Harrison", 425, "Deathworld 1"),
            ol("Harry Harrison Power", 3, "The analysis of absorbed gas in crude oil, sampled at reservoir pressures, and its application to production problems ..", "OL2A"),
            ol("Henry Kuttner", 1, "Earth's last citadel", "OL3A")])
        self.assertEqual([f"{m['title']}, {m['detail']}" for m in got], [
            "Harry Harrison, 425 works, best known for Deathworld 1",
            "Harry Harrison Power, 3 works, best known for The analysis of absorbed gas in crude oil…",
            "Henry Kuttner, 1 work, best known for Earth's last citadel"])
        self.assertTrue(all(len(m["detail"]) <= 70 for m in got))

    def test_long_names_cut_and_spaces_tidied(self):
        got = media_import.book_matches([
            ol("Avram (editor) (P. M. Hubbard; Don White; J. G. Ballard; Jack Vance; Harry Harrison; Karen Anderson; Richard McKenna)", 1, "The Best", "OL4A"),
            ol("Howard  Pyle ", 3, "Robin Hood", "OL5A")])
        self.assertLessEqual(len(got[0]["title"]), 60)
        self.assertTrue(got[0]["title"].endswith("…"))
        self.assertEqual(got[1]["title"], "Howard Pyle")

    def test_a_repeated_name_with_no_works_is_left_out(self):
        got = media_import.book_matches([ol("Harry Harrison", 425, "Deathworld 1"), ol("Harry Harrison", None, None, "OL9A"),
                                         ol("J. G. Ballard", None, None, "OL8A")])
        self.assertEqual([(m["id"], m["detail"]) for m in got], [("OL1A", "425 works, best known for Deathworld 1"), ("OL8A", "no works listed")])

    def test_at_most_five(self):
        self.assertEqual(len(media_import.book_matches([ol(f"Author {i}", i + 2, None, f"OL{i}A") for i in range(8)])), 5)


if __name__ == "__main__":
    unittest.main()
