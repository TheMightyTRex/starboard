"""After a move into Reelix, qBittorrent (DASH-129): whether the old apps reached it without a password (its address
allow list), whether it runs through the VPN container, and a fixed address in Reelix changed to the name it has
on Starboard's stack. Made-up settings files only; Docker is never called."""
import unittest
from unittest import mock

from starboard import reelix_move
from tests.test_reelix_move import FakeAdmin


class AllowListTest(unittest.TestCase):
    def test_both_layouts(self):
        five = "[WebUI]\nAuthSubnetWhitelistEnabled=true\nAuthSubnetWhitelist=10.88.0.0/16\n"
        older = "[Preferences]\nWebUI\\AuthSubnetWhitelistEnabled=true\nWebUI\\AuthSubnetWhitelist=172.18.0.0/16, 10.0.0.0/8\n"
        self.assertEqual(reelix_move.conf_allow_list(five), ["10.88.0.0/16"])
        self.assertEqual(reelix_move.conf_allow_list(older), ["172.18.0.0/16", "10.0.0.0/8"])

    def test_off_or_empty_is_none(self):
        self.assertEqual(reelix_move.conf_allow_list("[WebUI]\nAuthSubnetWhitelistEnabled=false\nAuthSubnetWhitelist=10.88.0.0/16\n"), [])
        self.assertEqual(reelix_move.conf_allow_list("[WebUI]\nAuthSubnetWhitelistEnabled=true\nAuthSubnetWhitelist=\n"), [])
        self.assertEqual(reelix_move.conf_allow_list("[Network]\nAuthSubnetWhitelistEnabled=true\n"), [])

    def test_the_settings_file_says_it(self):
        text = "[WebUI]\nUsername=harbour\nAuthSubnetWhitelistEnabled=true\nAuthSubnetWhitelist=10.88.0.0/16\n"
        with mock.patch.object(reelix_move, "_read_files") as read, \
                mock.patch("builtins.open", mock.mock_open(read_data=text)), \
                mock.patch.object(reelix_move.os, "listdir", return_value=[]), mock.patch.object(reelix_move.os, "rmdir"):
            read.return_value = ({"/config/qBittorrent/qBittorrent.conf": "/made/up/qBittorrent.conf"}, "/made/up")
            conf = reelix_move.qbit_conf()
        self.assertEqual(conf["allow_list"], ["10.88.0.0/16"])
        self.assertEqual(conf["user"], "harbour")


class ThroughTheVpnTest(unittest.TestCase):
    def test_container_network_mode_is_the_vpn(self):
        with mock.patch.object(reelix_move, "_inspect", return_value={"HostConfig": {"NetworkMode": "container:4f2a"}}):
            self.assertTrue(reelix_move.qbit_through_vpn())
        with mock.patch.object(reelix_move, "_inspect", return_value={"HostConfig": {"NetworkMode": "media_default"}}):
            self.assertFalse(reelix_move.qbit_through_vpn())

    def test_unknown_when_docker_cannot_say(self):
        with mock.patch.object(reelix_move, "_inspect", side_effect=reelix_move.containers.DockerError("no")):
            self.assertIsNone(reelix_move.qbit_through_vpn())


class FixedAddressTest(unittest.TestCase):
    def client(self, i, host, kind="qbittorrent"):
        return {"id": i, "implementation": kind, "name": f"c{i}", "enabled": True, "priority": 25, "tags": [],
                "settings": {"host": host, "port": 8080, "password": "********"}}

    def test_a_fixed_address_becomes_the_name(self):
        admin = FakeAdmin(clients=[self.client(1, "10.88.0.2"), self.client(2, "qbittorrent"), self.client(3, "10.88.0.3", "nzbget")])
        changed = reelix_move.fix_qbit_address(admin, "gluetun")
        puts = [(p, b) for m, p, b in admin.calls if m == "PUT"]
        self.assertEqual([p for p, _ in puts], ["/downloadclients/1"])
        self.assertEqual(puts[0][1]["settings"]["host"], "gluetun")
        self.assertEqual(puts[0][1]["settings"]["password"], "********")  # kept: Reelix keeps a masked one as it is
        self.assertEqual(changed, ["c1"])

    def test_nothing_to_change(self):
        admin = FakeAdmin(clients=[self.client(2, "gluetun")])
        self.assertEqual(reelix_move.fix_qbit_address(admin, "gluetun"), [])
        self.assertFalse(any(m == "PUT" for m, _, _ in admin.calls))

    def test_the_move_lists_the_step_even_without_a_password(self):
        items = dict(reelix_move.move_tasks([{"source": "radarr", "app": "Radarr"}], hold=False, qbit=False))
        self.assertEqual(items["qbittorrent"], "Check qBittorrent's address in Reelix")
        items = dict(reelix_move.move_tasks([{"source": "radarr", "app": "Radarr"}], hold=False, qbit=True))
        self.assertEqual(items["qbittorrent"], "Connect Reelix to qBittorrent")


if __name__ == "__main__":
    unittest.main()
