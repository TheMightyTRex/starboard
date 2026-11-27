"""The row of controls on a Library item page (26 November 2026): the Following choice shares the buttons' height token."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"


class FollowChoiceTest(unittest.TestCase):
    def rule(self, selector):
        css = (WEB / "css" / "components.css").read_text()  # the design system's component (PR 44), synced
        return "\n".join(re.findall(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css))

    def test_frame_uses_the_control_height_token(self):
        frame = self.rule(".series-head__follow")
        self.assertIn("min-height: var(--control-h)", frame)
        self.assertNotRegex(frame, r"(?:height|padding)[^;]*\d+px")  # no hand-typed sizes

    def test_list_inside_has_no_frame_of_its_own(self):
        self.assertIn("border: 0", self.rule(".series-head__follow .select"))

    def test_it_is_a_real_label_with_a_name_for_the_list(self):
        js = (WEB / "js" / "library-item.js").read_text()
        self.assertIn('"aria-label": "Following"', js)
        self.assertIn('el("label", { class: "series-head__follow" }', js)

    def test_it_wraps_on_a_phone(self):
        css = (WEB / "css" / "components.css").read_text()
        self.assertRegex(css, r"max-width: 560px\) \{\s*\.series-head__follow \{\s*flex: 1 1 100%")


if __name__ == "__main__":
    unittest.main()
