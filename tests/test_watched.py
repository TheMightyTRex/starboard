"""Watched or not watched, from Jellyfin (DASH-276)."""
import unittest
from unittest import mock

from starboard import services, watched

JF = {"type": "jellyfin", "name": "Jellyfin", "url": "http://jf", "api_key": "k", "enabled": True}
EP = "a" * 32


class Watched(unittest.TestCase):
    def setUp(self):
        services.forget()
        self.cfg = mock.Mock(data={"services": [JF], "extras": {"jellyfin_user": ""}})
        self.calls = []

    def fake(self, service, path, method="GET", body=None, timeout=120):
        self.calls.append((method, path))
        if path == "/Users":
            return [{"Id": "u1", "Name": "sam", "Policy": {}}, {"Id": "u2", "Name": "admin", "Policy": {"IsAdministrator": True}}]
        if path.startswith("/Items?"):
            return {"Items": [{"Id": "s" * 32, "ProviderIds": {"Tmdb": "99"}}, {"Id": "x" * 32, "ProviderIds": {"Tmdb": "999"}}]}
        if path.startswith("/Shows/"):
            return {"Items": [{"Id": EP, "ParentIndexNumber": 1, "IndexNumber": 2, "UserData": {"Played": True}}]}
        return None

    def test_the_first_admin_and_the_exact_tmdb_id(self):
        with mock.patch("starboard.migrate._mb", side_effect=self.fake):
            s = watched.series(self.cfg, 99)
        self.assertEqual(s["user"], "admin")
        self.assertEqual(s["id"], "s" * 32)
        self.assertEqual(s["episodes"][(1, 2)], {"id": EP, "watched": True})

    def test_the_chosen_user_and_marking(self):
        self.cfg.data["extras"]["jellyfin_user"] = "sam"
        with mock.patch("starboard.migrate._mb", side_effect=self.fake):
            self.assertEqual(watched.mark(self.cfg, [EP, "not-an-id"], False), 1)
        self.assertIn(("DELETE", f"/UserPlayedItems/{EP}?userId=u1"), self.calls)

    def test_no_jellyfin_says_how(self):
        self.cfg.data["services"] = []
        self.assertIsNone(watched.film(self.cfg, 5))
        with self.assertRaisesRegex(ValueError, "Add Jellyfin"):
            watched.mark(self.cfg, [EP], True)


if __name__ == "__main__":
    unittest.main()
