"""The No-IP updater (DASH-170): its state from its log, and its sign-in in noip.env, never in Starboard's settings."""
import os
import stat
import tempfile
import unittest

from starboard import noip, stack

LOG = """[2026-11-09T10:19:01Z INFO  noip_duc::observer] got new ip; current=203.0.113.7, previous=0.0.0.0
[2026-11-09T10:19:01Z INFO  noip_duc::observer] update successful; current=203.0.113.7, previous=0.0.0.0
[2026-11-09T10:24:01Z INFO  noip_duc::observer] checking ip again in 5m
"""


class NoipTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        noip.forget()

    def test_the_log_says_when_and_where(self):
        out = noip.parse(LOG)
        self.assertEqual((out["state"], out["last_update"], out["address"]), ("ok", "2026-11-09T10:19:01Z", "203.0.113.7"))
        refused = noip.parse(LOG + "[2026-11-09T11:00:00Z ERROR noip_duc] Incorrect credentials\n")
        self.assertEqual(refused["state"], "refused")
        self.assertIn("DDNS key", refused["said"])
        self.assertEqual(noip.parse("[2026-11-09T10:00:00Z INFO  noip_duc] checking ip again in 5m")["state"], "waiting")

    def test_saving_keeps_the_password_and_the_file_private(self):
        with self.assertRaisesRegex(ValueError, "password"):
            noip.save(self.tmp.name, "key-user", "", "home.example.net")
        noip.save(self.tmp.name, "key-user", "made-up-secret", "home.example.net")
        noip.save(self.tmp.name, "key-user2", "", "home.example.net,other.example.net")
        with open(noip.path(self.tmp.name)) as f:
            self.assertIn("NOIP_PASSWORD=made-up-secret", f.read())
        self.assertEqual(stat.S_IMODE(os.stat(noip.path(self.tmp.name)).st_mode), 0o600)
        self.assertEqual(noip.read(self.tmp.name), {"username": "key-user2", "hostnames": "home.example.net,other.example.net", "password_set": True})
        with self.assertRaises(ValueError):
            noip.save(self.tmp.name, "key user\nX=1", "p", "home.example.net")

    def test_install_apps_writes_it_with_its_file(self):
        built = stack.build({"apps": ["noip-duc"], "config_dir": "/srv/config", "data_dir": "/srv/media"})
        self.assertIn("    env_file: ./noip.env", built["compose"])
        stack.write(self.tmp.name, built)
        self.assertEqual(noip.read(self.tmp.name)["password_set"], False)
        self.assertTrue(os.path.exists(noip.path(self.tmp.name)))

    def test_not_installed_says_so(self):
        from starboard import containers

        def docker(method, path, *a, **k):
            raise containers.DockerError("No such container")
        self.assertFalse(noip.status(self.tmp.name, docker=docker)["installed"])


if __name__ == "__main__":
    unittest.main()
