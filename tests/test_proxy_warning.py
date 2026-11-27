"""A forwarded request from a proxy Starboard does not trust is noticed once (DASH-603, audit F6)."""
import tempfile
import unittest
from unittest import mock

from starboard import server


class Warn(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        _, self.app = server.make_server("127.0.0.1", 0, tmp.name)

    def test_once_for_each_address(self):
        with mock.patch.object(server.logs, "event") as ev:
            for _ in range(3):
                self.app.warn_unlisted_proxy("192.168.1.21")
            self.app.warn_unlisted_proxy("192.168.1.22")
        self.assertEqual(ev.call_count, 2)
        self.assertIn("STARBOARD_PROXY_ADDRESSES", ev.call_args[0][2])
        self.assertEqual(ev.call_args[0][0], "warning")

    def test_the_handler_asks_only_for_a_forwarded_request_from_elsewhere(self):
        def handler(peer, header, trust=False):
            h = server.Handler.__new__(server.Handler)
            h.app = self.app
            h.client_address = (peer, 1)
            h.headers = {"X-Forwarded-For": header} if header else {}
            self.app.trust_proxy = trust
            return h
        with mock.patch.object(self.app, "warn_unlisted_proxy") as w:
            self.assertEqual(handler("10.0.0.5", "1.2.3.4").client_address_text(), "10.0.0.5")  # not believed
            w.assert_called_once_with("10.0.0.5")
            w.reset_mock()
            handler("10.0.0.5", "").client_address_text()
            handler("127.0.0.1", "1.2.3.4").client_address_text()  # this computer is a proxy it knows
            w.assert_not_called()
            self.assertEqual(handler("127.0.0.1", "1.2.3.4", trust=True).client_address_text(), "1.2.3.4")


if __name__ == "__main__":
    unittest.main()
