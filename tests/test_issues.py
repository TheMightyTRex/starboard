"""Issues, from Reelix (DASH-208)."""
import unittest
from unittest import mock

from starboard import issues

REELIX = [{"id": "rx", "url": "http://r/api/v1", "api_key": "k", "name": "Reelix"}]
ISSUE = {"id": 4, "kind": "series", "title": "Ghosts", "issue_type": "audio", "status": "open", "season": 6, "episode": 1,
         "message": "No sound", "reported_by": {"display_name": "Sam"}, "comment_count": 0, "comments": []}


class Issues(unittest.TestCase):
    def test_list_in_words(self):
        def fake(s, path, params=None, method="GET", body=None, timeout=None):
            return {"open": 1} if path == "/issues/count" else {"items": [ISSUE], "total": 1}
        with mock.patch("starboard.services.reelix_native", return_value=REELIX), mock.patch("starboard.services._api", side_effect=fake):
            out = issues.listing([], "open")
        row = out["items"][0]
        self.assertEqual((row["type"], row["where"], row["by"], out["open"]), ("Sound", "Season 6, episode 1", "Sam", 1))

    def test_comment_resolve_reopen(self):
        with mock.patch("starboard.services.reelix_native", return_value=REELIX), mock.patch("starboard.services._api", return_value=ISSUE) as api:
            issues.act([], 4, "comment", "On it")
            self.assertEqual((api.call_args[0][1], api.call_args.kwargs["body"]), ("/issues/4/comments", {"message": "On it"}))
            issues.act([], 4, "resolve")
            self.assertEqual(api.call_args[0][1], "/issues/4/resolve")
            with self.assertRaisesRegex(ValueError, "Type a comment"):
                issues.act([], 4, "comment", "  ")


if __name__ == "__main__":
    unittest.main()
