"""Each key of the general settings has its right (DASH-278): security settings are never changed by an API key."""
import os
import re
import unittest

from starboard import config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GeneralRightsTest(unittest.TestCase):
    def test_every_key_the_settings_take_has_a_right(self):
        with open(os.path.join(ROOT, "starboard", "config.py")) as f:
            body = f.read().split("def update_general", 1)[1].split("\nPERF_CHOICES", 1)[0].split("\nGENERAL_RIGHTS", 1)[0]
        taken = set(re.findall(r'"([a-z_]+)" in incoming', body)) | set(re.findall(r'incoming\.get\("([a-z_]+)"', body))
        for group in re.findall(r'for key in \(([^)]*)\):\s*\n\s*if key in incoming', body):
            taken |= set(re.findall(r'"([a-z_]+)"', group))
        self.assertTrue({"site_name", "network_access", "watch", "infinite_scroll"} <= taken)
        self.assertEqual(sorted(taken - set(config.GENERAL_RIGHTS)), [], "Give each new setting its right in GENERAL_RIGHTS")

    def test_security_and_the_alert_channel_are_never_by_key(self):
        for change in ({"network_access": False}, {"secure_cookies": True}, {"session_days": 30}, {"last_version": "1.0.0"},
                       {"watch": {"channel": {"kind": "ntfy"}}}, {"site_name": "x", "session_days": 7}):
            need = config.general_right(change)
            self.assertEqual(need, "never", change)
            self.assertFalse(config.allowed("admin", need))
        self.assertEqual(config.general_right({"watch": {"enabled": True}}), "admin")
        self.assertEqual(config.general_right({"upcoming_view": "list", "design": "harbour"}), "manage")
        self.assertTrue(config.allowed("admin", "manage"))
        self.assertFalse(config.allowed("read", "manage"))

    def test_an_unknown_key_is_refused(self):
        with self.assertRaises(config.ConfigError):
            config.general_right({"made_up": 1})


if __name__ == "__main__":
    unittest.main()
