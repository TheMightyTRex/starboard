"""One action row on a Library item page (owner, 26 November 2026): the verbs, and the radio Find."""
import pathlib
import unittest
from unittest import mock

from starboard import library

JS = (pathlib.Path(__file__).resolve().parent.parent / "web" / "js" / "library-item.js").read_text()


class RowTest(unittest.TestCase):
    def test_the_verbs(self):
        for word in ('"Find it"', "Find ${g.missing} wanted", "Use this one", "Use it anyway", "findLabel"):
            self.assertIn(word, JS)
        for old in ("Get the missing episodes", '"Get this one"', '"Get it anyway"', "Get the ${g.missing}"):
            self.assertNotIn(old, JS)

    def test_the_order_puts_watched_before_choose_a_download(self):
        self.assertLess(JS.index("watchedButton(item.watched, item.title, false)"), JS.index('"Choose a download") : null,\n    can.change'))

    def test_find_on_a_radio_show_searches_its_wanted_episodes(self):
        calls = []

        def fake(reelix, path, params=None, method="GET", body=None, **k):
            calls.append((method, path, body))
            return {}
        with mock.patch("starboard.services._api", side_effect=fake):
            said = library.act({}, "radio", 7, "get")
        self.assertEqual(calls, [("POST", "/radio/shows/7/search", {})])
        self.assertIn("wanted episodes", said)


if __name__ == "__main__":
    unittest.main()
