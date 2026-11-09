"""A Gluetun already on the computer: its VPN offered to the set-up without its key, and copied in when the files are
written (DASH-132)."""
import unittest
from unittest import mock

from starboard import takeover

INFO = {"Image": "sha256:x", "Config": {"Env": ["VPN_SERVICE_PROVIDER=surfshark", "VPN_TYPE=wireguard",
                                                 "WIREGUARD_PRIVATE_KEY=made-up-key=", "WIREGUARD_ADDRESSES=10.2.0.2/32",
                                                 "SERVER_COUNTRIES=Netherlands"]}}


class ExistingVpn(unittest.TestCase):
    def setUp(self):
        for target, value in (("found", [{"name": "old-gluetun", "key": "gluetun", "running": True}]),
                              ("_inspect", INFO), ("_image_env", {})):
            p = mock.patch.object(takeover, target, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def test_the_set_up_sees_no_key(self):
        shown = takeover.existing_vpn()
        self.assertEqual(shown, {"name": "old-gluetun", "provider": "surfshark", "type": "wireguard",
                                 "countries": "Netherlands", "complete": True})
        self.assertNotIn("made-up-key", str(shown))

    def test_writing_copies_the_details_in(self):
        out = takeover.fill_vpn({"apps": ["gluetun"], "vpn": {"use_existing": "old-gluetun"}})
        self.assertEqual(out["vpn"]["wireguard_private_key"], "made-up-key=")
        self.assertEqual(out["vpn"]["wireguard_addresses"], "10.2.0.2/32")
        with self.assertRaisesRegex(ValueError, "Type them instead"):
            takeover.fill_vpn({"vpn": {"use_existing": "another"}})
        self.assertEqual(takeover.fill_vpn({"vpn": {"provider": "nordvpn"}}), {"vpn": {"provider": "nordvpn"}})


if __name__ == "__main__":
    unittest.main()
