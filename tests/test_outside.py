"""Addresses Starboard is told to call (DASH-279)."""
import socket
import unittest

from starboard import config, outside


class OutsideTest(unittest.TestCase):
    def test_home_addresses_and_app_names_are_fine(self):
        for url in ("http://127.0.0.1:8096", "http://192.168.1.20:7700", "http://10.0.0.5", "http://[::1]:8080",
                    "https://jellyfin.example.net", "http://not-resolvable.invalid:8096"):
            outside.check_url(url, resolve=lambda *a, **k: (_ for _ in ()).throw(socket.gaierror("no")) if "invalid" in a[0]
                              else [(2, 1, 6, "", ("192.0.2.10", 80))])

    def test_metadata_and_link_local_are_refused(self):
        for url in ("http://169.254.169.254/latest/meta-data", "http://metadata.google.internal/", "http://[fe80::1]/",
                    "http://0.0.0.0:80", "http://224.0.0.1", "http://[fd00:ec2::254]/", "http://[::ffff:169.254.169.254]/"):
            with self.assertRaises(ValueError, msg=url):
                outside.check_url(url)
        with self.assertRaisesRegex(ValueError, "link-local"):
            outside.check_url("http://sneaky.example", resolve=lambda *a, **k: [(2, 1, 6, "", ("169.254.169.254", 80))])

    def test_manage_apps_refuses_them(self):
        with self.assertRaises(config.ConfigError):
            config.validate_service({"name": "x", "type": "sonarr", "url": "http://169.254.169.254"})
        self.assertEqual(config.validate_service({"name": "x", "type": "sonarr", "url": "http://127.0.0.1:8989"})["url"], "http://127.0.0.1:8989")


if __name__ == "__main__":
    unittest.main()
