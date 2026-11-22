"""The VPN card reads a Gluetun that has no connection entry from its container (22 November 2026)."""
import unittest
from unittest import mock

from starboard import containers, server


class VpnFromContainer(unittest.TestCase):
    def state(self, **state):
        return mock.patch.object(containers, "docker", return_value={"State": state})

    def test_healthy_is_running(self):
        with self.state(Running=True, Status="running", Health={"Status": "healthy"}):
            v = containers.vpn_from_container()
        self.assertEqual((v["running"], v["status"], v["from"]), (True, "healthy", "container"))

    def test_unhealthy_or_starting_is_not_running(self):
        for health in ("unhealthy", "starting"):
            with self.state(Running=True, Status="running", Health={"Status": health}):
                self.assertFalse(containers.vpn_from_container()["running"], health)

    def test_stopped_is_not_running(self):
        with self.state(Running=False, Status="exited"):
            v = containers.vpn_from_container()
        self.assertEqual((v["running"], v["status"]), (False, "exited"))

    def test_no_health_check_counts_running(self):
        with self.state(Running=True, Status="running"):
            self.assertTrue(containers.vpn_from_container()["running"])

    def test_no_container_is_none(self):
        with mock.patch.object(containers, "docker", side_effect=containers.DockerError("no such container")):
            self.assertIsNone(containers.vpn_from_container())


class TransferWithVpn(unittest.TestCase):
    def run_it(self, vpn, keys, found):
        with mock.patch.object(server.services, "transfer", return_value={"clients": [], "vpn": list(vpn), "errors": []}), \
             mock.patch.object(server.stack, "chosen_keys", return_value=keys), \
             mock.patch.object(server.containers, "vpn_from_container", return_value=found) as asked:
            return server.transfer_with_vpn("/data", []), asked

    def test_kept_gluetun_without_an_entry_is_read_from_its_container(self):
        out, _ = self.run_it([], ["qbittorrent", "gluetun"], {"name": "Gluetun", "running": True})
        self.assertEqual(out["vpn"], [{"name": "Gluetun", "running": True}])

    def test_an_entry_that_answers_is_kept_and_docker_is_not_asked(self):
        out, asked = self.run_it([{"name": "VPN", "running": True, "country": "Netherlands"}], ["gluetun"], {"name": "Gluetun"})
        self.assertEqual(len(out["vpn"]), 1)
        self.assertEqual(out["vpn"][0]["country"], "Netherlands")
        asked.assert_not_called()

    def test_no_gluetun_in_the_stack_stays_empty(self):
        out, asked = self.run_it([], ["qbittorrent"], {"name": "Gluetun", "running": True})
        self.assertEqual(out["vpn"], [])
        asked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
