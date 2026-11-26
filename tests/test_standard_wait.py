"""One short wait: the ring with words (DASH-493, Starboard patterns audit, 26 November 2026).

A page script that waits for an answer shows SharedComponents.wait("Loading the releases"), never a plain "Loading…"
paragraph. A select box (an option cannot hold a ring) and a preformatted block are the exceptions."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
PLAIN = re.compile(r'el\("(?:p|li)", \{ class: "muted(?: small)?", text: "Loading(?:…|\.\.\.)" \}\)')


class OneWait(unittest.TestCase):
    def test_no_plain_loading_paragraph_in_page_scripts(self):
        # plugins.js and settings-setup.js are being changed by other work at the time of writing: listed, not forgotten.
        waiting = {"plugins.js", "settings-setup.js", "components.js", "snaglist.js"}
        found = sorted(p.name for p in (WEB / "js").glob("*.js") if p.name not in waiting and PLAIN.search(p.read_text()))
        self.assertEqual(found, [], f"a plain Loading… line: {found}")

    def test_no_plain_loading_item_in_pages(self):
        found = sorted(p.name for p in WEB.glob("*.html") if re.search(r'<li class="muted">Loading', p.read_text()))
        self.assertEqual(found, [])

    def test_the_library_builds_it(self):
        text = (WEB / "js/components.js").read_text()
        self.assertIn("function wait(", text)
        self.assertIn("{ wait }", text)
        self.assertIn('"wait__mark"', text)


if __name__ == "__main__":
    unittest.main()
