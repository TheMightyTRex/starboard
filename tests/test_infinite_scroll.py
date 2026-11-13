"""Load more as you scroll (DASH-277, from the design system's UX-52). The behaviour lives in the design system's
components.js (SharedComponents.loadMore); Starboard's lists use it and keep a real Show more button. The journeys
(INF-01) try it in a browser; these checks keep the pieces in place."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"
JS = WEB / "js"


def read(path):
    return path.read_text(encoding="utf-8")


class LibraryComponentTest(unittest.TestCase):
    def setUp(self):
        self.lib = read(JS / "components.js")
        start = self.lib.index("function loadMore(box")
        self.body = self.lib[start:self.lib.index("function setup(root)", start)]

    def test_it_is_offered_by_the_library(self):
        self.assertRegex(self.lib, r"window\.SharedComponents = \{[^}]*\bloadMore\b")

    def test_one_observer_and_no_scroll_handlers(self):
        self.assertEqual(self.body.count("new IntersectionObserver"), 1)
        self.assertNotIn('addEventListener("scroll"', self.body)
        self.assertNotIn("setInterval", self.body)

    def test_it_pauses_after_three_lots(self):
        self.assertIn("options.maxAuto ?? 3", self.body)
        self.assertIn("Paused here so you can reach the end of the page", self.body)

    def test_it_says_how_many_politely_and_shows_loading(self):
        self.assertIn('announcer("load-more-status", "status")', self.body)
        self.assertIn("more${noun} shown", self.body)
        self.assertIn("Loading the next ", self.body)

    def test_the_button_stays_usable_while_loading(self):
        # aria-disabled, not disabled, so a keyboard user's focus stays on it
        self.assertIn('setAttribute("aria-disabled", "true")', self.body)
        self.assertNotIn(".disabled = true", self.body)

    def test_reduce_motion_and_the_setting_mean_the_button_alone(self):
        self.assertIn("motionStill()", self.body)
        self.assertIn("prefers-reduced-motion: reduce", self.lib)
        self.assertIn("options.auto", self.body)

    def test_only_the_button_moves_focus(self):
        self.assertRegex(self.body, r"if \(byButton\) \{[^}]*loadMoreFocus")


class StarboardUsesItTest(unittest.TestCase):
    def test_no_page_has_its_own_infinite_scroll(self):
        for path in JS.glob("*.js"):
            if path.name in ("components.js", "snaglist.js"):
                continue
            self.assertNotIn("autoLoadMore", read(path), path.name)

    def test_the_setting_decides_through_the_wrapper(self):
        common = read(JS / "common.js")
        self.assertIn('auto: () => listLoading === "auto"', common)
        self.assertIn('listLoading = session.infinite_scroll === false ? "button" : "auto"', common)

    def test_library_walls_wanted_and_history_use_it(self):
        self.assertIn('loadMore($("#lib-more")', read(JS / "library.js"))
        self.assertIn('loadMore($("#wanted-more")', read(JS / "wanted.js"))
        self.assertIn('loadMore($("#history-more")', read(JS / "history.js"))

    def test_a_new_search_filter_or_letter_starts_the_count_again(self):
        lib = read(JS / "library.js")
        self.assertEqual(lib.count("more?.reset()"), 2)

    def test_every_wall_keeps_a_real_show_more_button(self):
        walls = list(WEB.glob("library-*.html"))
        with_more = [p for p in walls if 'id="lib-more"' in read(p)]
        self.assertGreaterEqual(len(with_more), 6)
        for path in with_more:
            box = re.search(r'<div class="load-more" id="lib-more"[^>]*>(.*?)</div>', read(path)).group(1)
            self.assertIn('class="load-more__count"', box, path.name)
            self.assertIn('<button class="btn" type="button">Show 40 more</button>', box, path.name)


if __name__ == "__main__":
    unittest.main()
