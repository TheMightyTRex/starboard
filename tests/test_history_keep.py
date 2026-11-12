"""History: how much to keep, and Delete history (12 November 2026)."""
import unittest
from unittest import mock

from starboard import activity, services

ROWS = [{"id": 3, "event_type": "grabbed", "date": "2026-11-12T10:00:00Z"},
        {"id": 2, "event_type": "grabbed", "date": "2026-11-01T10:00:00Z"},
        {"id": 1, "event_type": "grabbed", "date": "2025-01-01T10:00:00Z"}]
SVC = [{"id": "reelix", "type": "link"}]


@mock.patch.object(services, "reelix_native", return_value=SVC)
class Keep(unittest.TestCase):
    def test_keep_days_and_clear(self, *_):
        with mock.patch.object(services, "_api", return_value={"items": ROWS, "total": 3}):
            self.assertEqual(len(activity.history(SVC, "all", 1, {})["items"]), 3)
            out = activity.history(SVC, "all", 1, {"history_cleared_at": "2026-11-05T00:00:00Z"})
            self.assertEqual(([i["id"] for i in out["items"]], out["total"]), ([3], 1))
            out = activity.history(SVC, "all", 1, {"history_keep_days": 365, "history_cleared_at": ""})
            self.assertEqual([i["id"] for i in out["items"]], [3, 2])

    def test_delete_falls_back_to_hiding(self, *_):
        prefs = {}
        with mock.patch.object(services, "_api", side_effect=services.ServiceError("405")):
            said = activity.delete_history(SVC, prefs, "2026-11-12T12:00:00Z")
        self.assertIn("cleared here", said)
        self.assertEqual(prefs["history_cleared_at"], "2026-11-12T12:00:00Z")
        with mock.patch.object(services, "_api", return_value={}):
            self.assertEqual(activity.delete_history(SVC, prefs, "2026-11-12T13:00:00Z"), "History deleted")


if __name__ == "__main__":
    unittest.main()
