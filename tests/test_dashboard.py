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

    def test_every_built_in_card_has_its_band(self):
        """DASH-442: one table gives every built-in card its logo; the own icons are in the design system's sprite."""
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parent.parent
        js = (root / "web" / "js" / "dashboard.js").read_text(encoding="utf-8")
        table = js.split("const CARD_BAND = {")[1].split("};")[0]
        rows = dict(re.findall(r"^\s*(\w+): (\{.*\}),$", table, re.M))
        self.assertEqual(set(rows), set(config.DASHBOARD_CARDS))
        sprite = (root / "web" / "icons" / "sprite.svg").read_text(encoding="utf-8")
        apps = set(config.SERVICE_TYPES) | {"reelix"}
        for card, row in rows.items():
            own = re.search(r'own: "([a-z0-9-]+)"', row)
            self.assertTrue(own and f'id="i-{own.group(1)}"' in sprite, card)
            for app in re.findall(r'"([a-z]+)"', (re.search(r"apps: (\[[^\]]*\]|ARR_APPS)", row) or [None, "[]"])[1]):
                self.assertIn(app, apps, card)
        self.assertNotIn("headChip(", js)  # every state chip is in the band now


if __name__ == "__main__":
    unittest.main()
