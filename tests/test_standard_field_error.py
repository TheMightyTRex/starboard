"""One field error line, said the library's way (Starboard patterns audit, 26 November 2026).

Nine places built the icon and the words of a field's error by hand, and none of them wrote the hidden "Error: " the
design system asks for, so a screen reader read only the sentence. common.js has errorWords(); every page uses it."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parents[1] / "web"


class OneFieldError(unittest.TestCase):
    def test_errorwords_says_error_to_screen_readers(self):
        text = (WEB / "js/common.js").read_text()
        body = text[text.index("function errorWords("):]
        body = body[:body.index("\n}\n")]
        self.assertIn('class: "visually-hidden", text: "Error: "', body)
        self.assertIn('icon("circle-alert")', body)

    def test_no_page_builds_an_error_line_by_hand(self):
        hand = sorted(p.name for p in (WEB / "js").glob("*.js") if p.name not in ("common.js", "components.js", "snaglist.js")
                      and re.search(r'replaceChildren\(icon\("circle-alert"\), el\("span", \{ text', p.read_text()))
        self.assertEqual(hand, [], f"use errorWords(): {hand}")
        inline = sorted(p.name for p in (WEB / "js").glob("*.js") if p.name not in ("common.js", "components.js", "snaglist.js")
                        and re.search(r'class: "field-error"[^)]*\}, icon\("circle-alert"\)', p.read_text()))
        self.assertEqual(inline, [], f"use errorWords(): {inline}")


if __name__ == "__main__":
    unittest.main()
