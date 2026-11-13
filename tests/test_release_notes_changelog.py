"""The release notes slide-out (UX-50, DASH-110) shows the newest 3 releases from starboard/releases.py, which keeps
the same words as CHANGELOG.md (the design system's changelog rule 6.1). These tests keep the two in step, so the
slide-out's releases are the changelog's newest releases, with the same versions and dates."""
import pathlib
import re
import unittest

from starboard import releases

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADING = re.compile(r"^## \[(\d+\.\d+\.\d+)\] \((\d{1,2} [A-Z][a-z]+ \d{4})\)", re.M)


def changelog():
    """The released versions in CHANGELOG.md, newest first, as (version, date)."""
    return HEADING.findall((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))


class ReleaseNotesFollowTheChangelogTest(unittest.TestCase):
    def test_the_newest_three_are_the_changelogs_newest_three(self):
        newest = [(r["version"], r["date"]) for r in reversed(releases.RELEASES)][:3]
        self.assertEqual(newest, changelog()[:3])

    def test_every_release_in_the_app_is_in_the_changelog_with_its_date(self):
        listed = dict(changelog())
        for r in releases.RELEASES:
            with self.subTest(version=r["version"]):
                self.assertIn(r["version"], listed)
                self.assertEqual(r["date"], listed[r["version"]])

    def test_the_changelog_is_newest_first(self):
        key = [tuple(int(n) for n in v.split(".")) for v, _ in changelog()]
        self.assertEqual(key, sorted(key, reverse=True))


if __name__ == "__main__":
    unittest.main()
