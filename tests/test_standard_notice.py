"""One notice, one builder (Starboard patterns audit, 26 November 2026).

Before this, ten page scripts each defined their own notice() with its own icons and live-region role. The library has
SharedComponents.notice, common.js has the one notice() that calls it, and no page script may define another."""
import pathlib
import re
import unittest

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"
DEFINES = re.compile(r"^(?:async )?function (notice|tdNotice)\(|^const (notice|tdNotice) =", re.M)


class OneNotice(unittest.TestCase):
    def test_only_common_js_defines_notice(self):
        found = {p.name for p in (WEB / "js").glob("*.js") if p.name not in ("components.js", "snaglist.js") and DEFINES.search(p.read_text())}
        self.assertEqual(found, {"common.js"}, f"a page script has its own notice(): {sorted(found - {'common.js'})}")

    def test_common_notice_uses_the_library(self):
        text = (WEB / "js/common.js").read_text()
        self.assertIn("SharedComponents.notice(", text)
        self.assertIn("function notice(", text)

    def test_the_library_builds_it(self):
        text = (WEB / "js/components.js").read_text()
        self.assertIn("function notice(", text)
        self.assertIn("{ notice }", text)
        # one icon for each tone, an error that blocks is an alert, anything else a status
        for pair in ("success: \"circle-check\"", "warning: \"triangle-alert\"", "danger: \"circle-alert\""):
            self.assertIn(pair, text)
        self.assertIn('options.alert ? "alert" : "status"', text)


if __name__ == "__main__":
    unittest.main()
