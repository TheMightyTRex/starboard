"""Soulseek through slskd (DASH-94): installed with its key, connected to Reelix, paused by download hours."""
import unittest
from unittest import mock

from starboard import schedule, services, stack


class SlskdTest(unittest.TestCase):
    def test_install_apps_writes_it_with_its_key_and_shared_folder(self):
        built = stack.build({"apps": ["slskd"], "config_dir": "/srv/config", "data_dir": "/srv/media"})
        self.assertIn("SLSKD_API_KEY=", built["env"])
        self.assertIn("SLSKD_DOWNLOADS_DIR", built["compose"])
        self.assertTrue(stack.APPS["slskd"]["vpn"])  # through Gluetun when the install has the VPN
        self.assertIn("downloads/soulseek", str(built["folders"]))
        self.assertNotIn("slskd", stack.install_choice("basics", check=lambda image: True)["apps"])

    def test_download_hours_disconnect_and_connect_it(self):
        sched = schedule.Schedule.__new__(schedule.Schedule)
        calls = []
        state = {"isLoggedIn": True}

        def fake(service, method, path, timeout=None):
            calls.append((method, path))
            if method == "DELETE":
                state["isLoggedIn"] = False
            if method == "PUT":
                state["isLoggedIn"] = True
            return dict(state) if method == "GET" else None
        mine = {}
        with mock.patch.object(services, "slskd", side_effect=fake):
            sched._slskd({"name": "slskd"}, mine, "pause", False)
            sched._slskd({"name": "slskd"}, mine, "run", False)
            state["isLoggedIn"] = False
            sched._slskd({"name": "slskd"}, mine, "run", False)  # not paused by Starboard: left alone
        self.assertEqual(calls, [("GET", "server"), ("DELETE", "server"), ("GET", "server"), ("PUT", "server"), ("GET", "server")])


if __name__ == "__main__":
    unittest.main()
