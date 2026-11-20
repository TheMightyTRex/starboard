"""The cache of files under web/: no disk checks inside the image, and at most one every RECHECK seconds in a checkout."""
import os
import unittest
from unittest import mock

from starboard import server


class StaticCacheTest(unittest.TestCase):
    def setUp(self):
        server._static.clear()
        self.page = os.path.join(server.WEB, "index.html")

    def test_fixed_web_folder_is_never_checked_again(self):
        first = server.static_file(self.page)
        with mock.patch.object(server, "WEB_FIXED", True), mock.patch.object(server.os, "stat", side_effect=AssertionError("checked")):
            self.assertIs(server.static_file(self.page), first)

    def test_checkout_checks_again_only_after_the_interval(self):
        first = server.static_file(self.page)
        with mock.patch.object(server, "WEB_FIXED", False):
            with mock.patch.object(server.os, "stat", side_effect=AssertionError("checked")):
                self.assertIs(server.static_file(self.page), first)  # within RECHECK: from memory
            later = server.time.monotonic() + server.RECHECK + 1
            with mock.patch.object(server.time, "monotonic", return_value=later), mock.patch.object(server.os, "stat", wraps=os.stat) as st:
                self.assertEqual(server.static_file(self.page), first)
                self.assertTrue(st.called)


if __name__ == "__main__":
    unittest.main()
