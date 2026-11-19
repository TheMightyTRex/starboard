"""Plug-ins on the home network reach Starboard's API at host.docker.internal and Starboard's own port, and Starboard
answers to that name (owner's server, 18 November 2026: Remote access could not reach starboard:8095)."""
import os
import unittest
from unittest import mock

from starboard import plugins


class ApiAddress(unittest.TestCase):
    def test_home_network_plugins_use_this_computer_at_starboards_port(self):
        with mock.patch.dict(os.environ, {"STARBOARD_PORT": "8090"}):
            self.assertEqual(plugins.api_address("lan"), "http://host.docker.internal:8090/api/v1/")
        with mock.patch.dict(os.environ, {"STARBOARD_PORT": ""}):
            self.assertEqual(plugins.api_address("lan"), "http://host.docker.internal:8095/api/v1/")

    def test_other_plugins_keep_their_own_network_address(self):
        self.assertEqual(plugins.api_address("default"), "http://starboard:8095/api/v1/")
        self.assertEqual(plugins.api_address("vpn"), "http://starboard:8095/api/v1/")


class HostName(unittest.TestCase):
    def test_starboard_answers_to_host_docker_internal_only_as_that_exact_name(self):
        from starboard import server
        app = server.App.__new__(server.App)
        app.allowed_hosts, app.machine_name = set(), "harbour"
        self.assertTrue(app.host_allowed("host.docker.internal"))
        self.assertFalse(app.host_allowed("host.docker.internal.attacker.example"))
        self.assertFalse(app.host_allowed("evil.example"))


if __name__ == "__main__":
    unittest.main()
