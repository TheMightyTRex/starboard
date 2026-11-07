"""SABnzbd's news servers into NZBGet (usenet_move): parsing sabnzbd.ini and the NZBGet options written."""
import unittest

from starboard import usenet_move

INI = """
[misc]
api_key = abc123
[servers]
[[news.example.test]]
name = news.example.test
displayname = Main provider
host = news.example.test
port = 563
username = someone
password = made-up-test-password
connections = 20
ssl = 1
enable = 1
priority = 0
retention = 3000
[[fill.example.test]]
host = fill.example.test
port = 119
username = other
password = another-made-up
connections = 4
ssl = 0
enable = 0
priority = 1
[categories]
[[tv]]
name = tv
"""


class UsenetMoveTest(unittest.TestCase):
    def test_servers_are_read_from_sabnzbd_ini(self):
        servers = usenet_move.parse_sab_servers(INI)
        self.assertEqual([s["host"] for s in servers], ["news.example.test", "fill.example.test"])
        self.assertNotIn("tv", [s.get("__section__") for s in servers])  # categories are not servers

    def test_nzbget_options_match_each_server(self):
        opts = dict(usenet_move.nzbget_server_options(usenet_move.parse_sab_servers(INI)))
        self.assertEqual(opts["Server1.Host"], "news.example.test")
        self.assertEqual((opts["Server1.Port"], opts["Server1.Encryption"], opts["Server1.Connections"]), ("563", "yes", "20"))
        self.assertEqual(opts["Server1.Name"], "Main provider")
        self.assertEqual(opts["Server1.Retention"], "3000")
        self.assertEqual((opts["Server2.Active"], opts["Server2.Level"], opts["Server2.Encryption"]), ("no", "1", "no"))

    def test_the_rest_of_nzbgets_settings_stay_and_old_servers_go(self):
        current = [{"Name": "MainDir", "Value": "/data/downloads/usenet"}, {"Name": "Server1.Host", "Value": "old.test"},
                   {"Name": "Server1.Port", "Value": "119"}]
        merged = usenet_move.merged_config(current, [("Server1.Host", "news.example.test")])
        self.assertIn({"Name": "MainDir", "Value": "/data/downloads/usenet"}, merged)
        self.assertNotIn({"Name": "Server1.Host", "Value": "old.test"}, merged)
        self.assertNotIn("Server1.Port", [o["Name"] for o in merged])

    def test_write_saves_and_reloads(self):
        calls = []

        def rpc(method, params=None):
            calls.append(method)
            return [] if method == "config" else True
        moved = usenet_move.write_to_nzbget(rpc, usenet_move.parse_sab_servers(INI))
        self.assertEqual(moved, 2)
        self.assertEqual(calls, ["config", "saveconfig", "reload"])


if __name__ == "__main__":
    unittest.main()
