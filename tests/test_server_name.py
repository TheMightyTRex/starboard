"""The server name at the start of the level 1 menu (DASH-75): up to 10 characters, and copied once from a short
dashboard name when an older settings file is opened."""

import json
import os
import tempfile
import unittest

from starboard.config import Config, ConfigError


class ServerNameTest(unittest.TestCase):
    def test_empty_by_default_and_at_most_ten_characters(self):
        with tempfile.TemporaryDirectory() as d:
            c = Config(d)
            self.assertEqual(c.public()["server_name"], "")
            c.update_general({"server_name": "  T-Rex  "})
            self.assertEqual(c.public()["server_name"], "T-Rex")
            c.update_general({"server_name": "Ten chars!"})
            self.assertEqual(c.data["server_name"], "Ten chars!")
            with self.assertRaises(ConfigError):
                c.update_general({"server_name": "Elevenchars"})
            self.assertEqual(c.data["server_name"], "Ten chars!")
            c.update_general({"server_name": ""})
            self.assertEqual(c.data["server_name"], "")

    def test_an_older_file_keeps_a_short_dashboard_name_as_the_server_name(self):
        for site_name, expected in (("T-Rex", "T-Rex"), ("Starboard", ""), ("The family media server", "")):
            with tempfile.TemporaryDirectory() as d:
                Config(d)
                path = os.path.join(d, "config.json")
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                data.pop("server_name")
                data["site_name"] = site_name
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                self.assertEqual(Config(d).data["server_name"], expected, site_name)


if __name__ == "__main__":
    unittest.main()
