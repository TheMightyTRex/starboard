"""What is new in Reelix: reading a Keep a Changelog file, choosing the versions, and the notice after an update."""
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from starboard import changes  # noqa: E402

# Made-up entries, in Keep a Changelog's own layout (ISO dates) and in the design system's ("4 November 2026").
LOG = """# Changelog

## [Unreleased]

### Added
- Not released yet.

## [0.7.2] - 2026-11-06

### Fixed
- **Imports** of a folder with `&` in its name no longer stop half way.

### Added
- **Shelves for radio:** stations and series on one page.
  - **Follow** on each, [as a link](https://example.com/follow).
    It carries on here.

## [0.7.1] (4 November 2026)

A summary line.

### Security
- Saved keys stay with their address.

## [0.7.0] - 2026-11-03 [YANKED]

### Added
- An installer.

[Unreleased]: https://example.com/compare/v0.7.2...HEAD
"""
REELIX = "ghcr.io/themightytrex/reelix:lite"


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.versions = changes.parse(LOG)

    def test_every_release_newest_first_without_unreleased(self):
        self.assertEqual([v["version"] for v in self.versions], ["0.7.2", "0.7.1", "0.7.0"])

    def test_dates_are_written_out(self):
        self.assertEqual([v["date"] for v in self.versions], ["6 November 2026", "4 November 2026", "3 November 2026"])

    def test_types_in_keep_a_changelog_order(self):
        self.assertEqual([s["type"] for s in self.versions[0]["sections"]], ["Added", "Fixed"])

    def test_nested_and_wrapped_entries_with_bold_code_and_link_words(self):
        top = self.versions[0]["sections"][0]["items"][0]
        self.assertEqual(top["parts"][0], ["strong", "Shelves for radio:"])
        child = top["items"][0]
        self.assertEqual(child["parts"][0], ["strong", "Follow"])
        text = "".join(t for _, t in child["parts"])
        self.assertIn("as a link", text)
        self.assertNotIn("https://", text)  # a link keeps only its words
        self.assertIn("It carries on here.", text)
        fixed = self.versions[0]["sections"][1]["items"][0]["parts"]
        self.assertIn(["code", "&"], fixed)

    def test_summary_and_withdrawn(self):
        self.assertEqual("".join(t for _, t in self.versions[1]["summary"]).strip(), "A summary line.")
        self.assertTrue(self.versions[2]["withdrawn"])
        self.assertFalse(self.versions[0]["withdrawn"])


class VersionsTest(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(changes.clean("0.7.1-lite"), "0.7.1")
        self.assertEqual(changes.clean("v0.7.2"), "0.7.2")
        for v in ("lite", "latest", "dev", "", None, "0.4.9-dev.6"):
            self.assertIsNone(changes.clean(v))

    def test_source_only_for_reelix(self):
        self.assertEqual(changes.source(REELIX)[0], "Reelix")
        self.assertEqual(changes.source("ghcr.io/demonzoned/reelix:0.7.1")[0], "Reelix")
        self.assertIsNone(changes.source("ghcr.io/themightytrex/storyarr:v0.6.0"))
        self.assertIsNone(changes.source("example/notreelix:1"))

    def test_between(self):
        with mock.patch.object(changes, "_fetch", return_value=changes.parse(LOG)):
            pick = lambda a, b: [v["version"] for v in changes.between(REELIX, a, b)["versions"]]
            self.assertEqual(pick("0.7.0", "0.7.2"), ["0.7.2", "0.7.1"])
            self.assertEqual(pick("0.7.1", "0.7.2"), ["0.7.2"])
            self.assertEqual(pick("lite", "0.7.1"), ["0.7.1"])  # no version known before: only the new one
            self.assertEqual(pick("0.7.0", ""), ["0.7.2", "0.7.1"])
            self.assertEqual(pick("", ""), ["0.7.2"])
            with self.assertRaises(ValueError):
                changes.between("example/other:1", "0.1.0", "0.2.0")

    def test_fetch_refuses_more_than_1_mb_and_caches(self):
        changes._cache.clear()
        big = io.BytesIO(b"x" * (changes.LIMIT + 10))
        with mock.patch("urllib.request.urlopen", return_value=mock.MagicMock(__enter__=lambda s: big, __exit__=lambda *a: None)):
            with self.assertRaises(ValueError):
                changes._fetch("https://example.com/big")
        calls = []

        def opener(req, timeout):
            calls.append(req.full_url)
            body = io.BytesIO(LOG.encode())
            return mock.MagicMock(__enter__=lambda s: body, __exit__=lambda *a: None)
        with mock.patch("urllib.request.urlopen", side_effect=opener):
            changes._fetch("https://example.com/log")
            changes._fetch("https://example.com/log")
        self.assertEqual(len(calls), 1)
        changes._cache.clear()


class NoticeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def rows(self, version, image=REELIX):
        return [{"id": "reelix", "name": "Reelix", "container": {"image": image, "version": version}},
                {"id": "tv", "name": "Example TV", "container": {"image": "example/sonarr:4", "version": "4.0.16"}}]

    def test_first_look_records_without_a_notice(self):
        rows = changes.observe(self.dir, self.rows("0.7.1"))
        self.assertTrue(rows[0]["changelog"])
        self.assertNotIn("changelog", rows[1])
        self.assertEqual(changes.notices(self.dir), [])

    def test_a_newer_version_gives_one_notice_from_the_first_version(self):
        changes.observe(self.dir, self.rows("0.7.0"))
        changes.observe(self.dir, self.rows("0.7.1"))
        changes.observe(self.dir, self.rows("0.7.2"))
        [n] = changes.notices(self.dir)
        self.assertEqual((n["app"], n["from"], n["to"]), ("reelix", "0.7.0", "0.7.2"))
        changes.seen(self.dir, "reelix")
        self.assertEqual(changes.notices(self.dir), [])

    def test_no_notice_going_back_or_without_a_version(self):
        changes.observe(self.dir, self.rows("0.7.2"))
        changes.observe(self.dir, self.rows("0.7.1"))
        changes.observe(self.dir, self.rows("lite"))
        self.assertEqual(changes.notices(self.dir), [])

    def test_file_is_private(self):
        changes.observe(self.dir, self.rows("0.7.0"))
        path = os.path.join(self.dir, "app-changes.json")
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["seen"], {"reelix": "0.7.0"})


if __name__ == "__main__":
    unittest.main()
