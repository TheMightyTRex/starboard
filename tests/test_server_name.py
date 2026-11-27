"""The server name at the start of the level 1 menu (DASH-75): up to 10 characters."""

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



if __name__ == "__main__":
    unittest.main()
