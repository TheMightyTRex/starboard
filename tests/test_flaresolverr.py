"""FlareSolverr is given to Reelix whenever Starboard installed it, through Gluetun when the stack has the VPN (DASH-219)."""
import unittest
from unittest import mock

from starboard import reelix_sites, stack


class FakeReelix:
    def __init__(self, settings):
        self.settings = dict(settings)
        self.puts = []

    def call(self, method, path, body=None):
        if method == "GET":
            return 200, dict(self.settings)
        self.puts.append(body)
        self.settings = dict(body)
        return 200, body


class FlareSolverr(unittest.TestCase):
    def run_with(self, keys, settings=None):
        r = FakeReelix(settings or {"flaresolverr_url": None, "allow_private_addresses": False})
        with mock.patch.object(stack, "chosen_keys", return_value=keys):
            line = reelix_sites.connect_flaresolverr(r, "/data")
        return r, line

    def test_through_the_vpn_when_the_stack_has_gluetun(self):
        r, line = self.run_with(["reelix", "gluetun", "flaresolverr"])
        self.assertEqual(r.settings["flaresolverr_url"], "http://gluetun:8191")
        self.assertTrue(r.settings["allow_private_addresses"])
        self.assertIn("FlareSolverr", line)

    def test_by_its_own_name_without_a_vpn(self):
        r, _ = self.run_with(["reelix", "flaresolverr"])
        self.assertEqual(r.settings["flaresolverr_url"], "http://flaresolverr:8191")

    def test_nothing_when_it_is_not_installed(self):
        r, line = self.run_with(["reelix", "gluetun"])
        self.assertEqual(r.puts, [])
        self.assertIsNone(line)

    def test_an_address_someone_typed_is_kept(self):
        r, line = self.run_with(["reelix", "flaresolverr"], {"flaresolverr_url": "http://other:8191"})
        self.assertEqual(r.puts, [])
        self.assertIsNone(line)


if __name__ == "__main__":
    unittest.main()
