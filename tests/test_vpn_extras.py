"""Gluetun's control server key, port forwarding into qBittorrent, and NordVPN's key from a token (DASH-233)."""
import io
import json
import unittest
import urllib.error
from unittest import mock

from starboard import setup_answers, stack, vpn_ports


class Opener:
    def __init__(self, status=200, body=None):
        self.status, self.body, self.seen = status, body, []

    def open(self, req, timeout=None):
        self.seen.append(req)
        if self.status != 200:
            raise urllib.error.HTTPError(req.full_url, self.status, "no", {}, io.BytesIO(b""))
        return io.BytesIO(json.dumps(self.body).encode())


class NordVpn(unittest.TestCase):
    def test_the_token_fetches_the_key_and_the_fixed_address(self):
        o = Opener(body={"nordlynx_private_key": "made-up-key="})
        self.assertEqual(setup_answers.nordvpn_key("a" * 64, opener=o), ("made-up-key=", "10.5.0.2/32"))
        self.assertTrue(o.seen[0].get_header("Authorization").startswith("Basic "))
        with self.assertRaisesRegex(ValueError, "did not accept"):
            setup_answers.nordvpn_key("a" * 64, opener=Opener(status=401))
        with self.assertRaisesRegex(ValueError, "Paste the access token"):
            setup_answers.nordvpn_key("not a token")


class PortForwarding(unittest.TestCase):
    def cfg(self):
        return mock.Mock(data={"services": [{"type": "gluetun", "name": "Gluetun", "url": "http://x:8000", "api_key": "k"},
                                            {"type": "qbittorrent", "name": "qBittorrent", "url": "http://x:8080", "api_key": "q"}]})

    def test_qbittorrent_follows_the_forwarded_port(self):
        sent = []
        with mock.patch("starboard.services._gluetun", return_value={"port": 51413}), \
                mock.patch("starboard.services.qbit", side_effect=lambda s, path, data=None: sent.append((path, data)) or {"listen_port": 6881}):
            self.assertIn("51413", vpn_ports.sync(self.cfg()))
        self.assertEqual(json.loads(sent[-1][1]["json"])["listen_port"], 51413)

    def test_nothing_until_a_port_is_forwarded(self):
        with mock.patch("starboard.services._gluetun", return_value={"port": 0}), mock.patch("starboard.services.qbit") as q:
            vpn_ports.sync(self.cfg())
        q.assert_not_called()

    def test_forwarding_only_for_providers_that_offer_it(self):
        base = {"apps": ["gluetun"], "groups": ["vpn"], "config_dir": "/srv/c", "data_dir": "/srv/m", "puid": 1000, "pgid": 1000, "tz": "Europe/London"}
        for provider, on in (("protonvpn", "on"), ("surfshark", "off")):
            built = stack.build({**base, "vpn": {"provider": provider, "type": "wireguard", "wireguard_private_key": "k", "wireguard_addresses": "10.2.0.2/32"}})
            self.assertIn(f"VPN_PORT_FORWARDING={on}", built["env"])
            self.assertIn("GLUETUN_API_KEY=", built["env"])
            self.assertIn('"8000:8000"', built["compose"])
            self.assertEqual(built["compose"].count("    ports:"), 1)


if __name__ == "__main__":
    unittest.main()
