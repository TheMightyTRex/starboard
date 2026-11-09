"""Reelix's own requests on Downloads, Requests, when there is no Seerr (DASH-157)."""
import unittest
from unittest import mock

from starboard import services

REELIX = {"type": "link", "icon": "reelix", "name": "Reelix", "url": "http://r", "api_key": "k", "enabled": True}


class ReelixRequests(unittest.TestCase):
    def test_rows_and_actions(self):
        calls = []

        def fake(service, path, params=None, method="GET", body=None, timeout=None):
            calls.append((method, path, body))
            if path == "/requests":
                return {"items": [{"id": 4, "kind": "series", "title": "Ghosts", "year": 2021, "seasons": [6], "status": "failed",
                                   "failure_reason": "no root folder", "requested_by": {"display_name": "Sam"}, "created_at": "2026-11-09T10:00:00Z"}]}
            if path == "/requests/count":
                return {"pending": 2}
            return {}
        with mock.patch.object(services, "reelix_native", return_value=[{**REELIX, "url": "http://r/api/v1"}]), \
                mock.patch.object(services, "_api", side_effect=fake):
            out = services.requests([REELIX])
            services.request_action([REELIX], 4, "retry")
            services.request_action([REELIX], 4, "decline", "Already have it")
        self.assertEqual(out["source"], "reelix")
        self.assertEqual(out["pending"], 2)
        row = out["items"][0]
        self.assertEqual((row["status"], row["retry"], row["by"], row["media"]), ("Failed", True, "Sam", "no root folder"))
        self.assertIn(("POST", "/requests/4/retry", None), calls)
        self.assertIn(("POST", "/requests/4/decline", {"reason": "Already have it"}), calls)


if __name__ == "__main__":
    unittest.main()
