"""The dashboard's saved layout and cards (DASH-239)."""
import unittest

from starboard import config


class Dashboard(unittest.TestCase):
    def test_layouts_and_cards_are_checked(self):
        self.assertEqual(config.clean_dashboard({"layout": "watch", "cards": None}), {"layout": "watch", "cards": None})
        out = config.clean_dashboard({"layout": "compact", "cards": [{"id": "vpn", "size": "small", "extra": 1}]})
        self.assertEqual(out["cards"], [{"id": "vpn", "size": "small"}])
        for bad in ({"layout": "grid"}, {"layout": "glance", "cards": [{"id": "weather", "size": "small"}]},
                    {"layout": "glance", "cards": [{"id": "vpn", "size": "small"}, {"id": "vpn", "size": "half"}]},
                    {"layout": "glance", "cards": [{"id": "vpn", "size": "huge"}]}):
            with self.assertRaises(config.ConfigError):
                config.clean_dashboard(bad)

    def test_the_dashboard_list_matches_the_page(self):
        import pathlib
        import re
        js = (pathlib.Path(__file__).resolve().parent.parent / "web" / "js" / "dashboard.js").read_text(encoding="utf-8")
        titles = set(re.findall(r"(\w+): \"", js.split("const CARD_TITLES = {")[1].split("};")[0]))
        self.assertEqual(titles, set(config.DASHBOARD_CARDS))


if __name__ == "__main__":
    unittest.main()
