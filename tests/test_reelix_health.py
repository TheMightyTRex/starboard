"""Reelix's warnings come from its own health route, not the empty Sonarr-style one (DASH-176, DASH-160)."""
import unittest
from unittest import mock

from starboard import services

REELIX = [
    {"id": "rx-films", "name": "Reelix films", "type": "radarr", "icon": "reelix", "enabled": True,
     "url": "http://reelix:7700/radarr", "api_key": "made-up-key"},
    {"id": "rx-series", "name": "Reelix series", "type": "sonarr", "icon": "reelix", "enabled": True,
     "url": "http://reelix:7700/sonarr", "api_key": "made-up-key"},
]
REPORT = {"status": "error", "checks": [
    {"source": "database", "level": "ok", "message": "Database is reachable"},
    {"source": "indexers", "level": "warning", "message": "Indexer YTS is unavailable"},
    {"source": "indexers", "level": "error", "message": "All indexers are unavailable due to failures"},
    {"source": "something_new", "level": "warning", "message": "A check Starboard does not know"},
]}


class ReelixHealth(unittest.TestCase):
    def setUp(self):
        services.FIRST_SEEN.clear()

    def asked(self, answer):
        calls = []

        def fake(service, path, *a, **k):
            calls.append((service["url"], path))
            return answer if path == "/system/health" else []
        with mock.patch.object(services, "_api", side_effect=fake):
            result = services.health(REELIX)
        return result, calls

    def test_reelix_is_asked_once_on_its_own_route(self):
        _, calls = self.asked(REPORT)
        self.assertEqual(calls, [("http://reelix:7700/api/v1", "/system/health")])

    def test_only_problems_come_back_with_their_level(self):
        result, _ = self.asked(REPORT)
        levels = [(i["level"], i["message"]) for i in result["items"]]
        self.assertEqual(levels, [("warning", "Indexer YTS is unavailable"),
                                  ("error", "All indexers are unavailable due to failures"),
                                  ("warning", "A check Starboard does not know")])

    def test_each_problem_says_where_to_put_it_right(self):
        result, _ = self.asked(REPORT)
        fixes = [i["fix"] for i in result["items"]]
        self.assertEqual(fixes[0], {"label": "Sites to search", "href": "/settings-reelix.html#rx-indexers"})
        self.assertIsNone(fixes[2])

    def test_a_cloudflare_check_offers_flaresolverr_until_it_is_installed(self):
        report = {"checks": [{"source": "indexers", "level": "warning",
                              "message": "Indexer 1337x is unavailable due to failures until 2026-11-10 09:00 UTC (Cloudflare challenge: challenge detected; configure FlareSolverr)"}]}
        result, _ = self.asked(report)
        self.assertEqual(result["items"][0]["fix"]["href"], "/install-apps.html?wizard=1&add=flaresolverr")
        with mock.patch.object(services, "_api", return_value=report):
            again = services.health(REELIX, ["reelix", "flaresolverr"])
        self.assertEqual(again["items"][0]["fix"]["label"], "Sites to search")

    def test_a_healthy_reelix_gives_nothing(self):
        result, _ = self.asked({"status": "ok", "checks": [{"source": "database", "level": "ok", "message": "fine"}]})
        self.assertEqual(result, {"items": [], "errors": []})

    def test_reelix_not_answering_is_an_error_not_a_crash(self):
        def fail(service, path, *a, **k):
            raise services.ServiceError("Cannot reach Reelix")
        with mock.patch.object(services, "_api", side_effect=fail):
            result = services.health(REELIX)
        self.assertEqual(result["items"], [])
        self.assertEqual(len(result["errors"]), 1)



class ReelixLogo(unittest.TestCase):
    """The icon collection has no Reelix, so its cards use the running Reelix's own logo (DASH-255)."""

    def test_the_logo_comes_from_reelix_itself(self):
        import tempfile
        from starboard import icons
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 20
        asked = []

        def fake(url):
            asked.append(url)
            return png if url.endswith("/logo.png") else None
        with tempfile.TemporaryDirectory() as d, mock.patch.object(icons, "_fetch", side_effect=fake):
            got = icons.get({"name": "Reelix films", "icon": "reelix", "url": "http://reelix:7700/radarr"}, d)
        self.assertEqual(asked[0], "http://reelix:7700/logo.png")
        self.assertEqual(got, (png, "image/png"))


if __name__ == "__main__":
    unittest.main()
