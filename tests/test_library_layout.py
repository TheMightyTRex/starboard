"""DASH-607: a Library card shrinks to its column and wraps what is inside, so large text never scrolls the page sideways."""
import pathlib
import unittest

CSS = (pathlib.Path(__file__).resolve().parent.parent / "web" / "css" / "library.css").read_text()


class CardWrapTest(unittest.TestCase):
    def test_a_card_can_shrink_to_its_column(self):
        self.assertIn(".lib-card { min-width: 0; }", CSS)

    def test_its_status_chip_and_meta_wrap(self):
        self.assertIn("white-space: normal", CSS)
        self.assertIn("overflow-wrap: anywhere", CSS)


if __name__ == "__main__":
    unittest.main()
