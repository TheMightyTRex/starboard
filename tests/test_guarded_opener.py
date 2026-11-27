"""One guarded opener for manifest, catalogue and logo fetches (DASH-603, security audit F4): redirects and the connection
are checked again, so a redirect or a name that changes its answer cannot reach a refused address."""
import unittest
from unittest import mock
import urllib.request

from starboard import outside


def answer(*ips):
    return lambda host, port, **kw: [(2, 1, 6, "", (ip, port)) for ip in ips]


class Connect(unittest.TestCase):
    def test_a_name_that_resolves_to_a_refused_address_is_not_connected_to(self):
        with mock.patch("socket.getaddrinfo", answer("169.254.169.254")), mock.patch("socket.create_connection") as c:
            with self.assertRaises(ValueError):
                outside.checked_connect(("example.org", 443), 5)
            c.assert_not_called()

    def test_the_connection_goes_to_the_address_that_was_checked(self):
        asked = []
        with mock.patch("socket.getaddrinfo", lambda h, p, **kw: asked.append(h) or [(2, 1, 6, "", ("93.184.216.34", p))]), \
                mock.patch("socket.create_connection", return_value="sock") as c:
            self.assertEqual(outside.checked_connect(("example.org", 443), 5), "sock")
        self.assertEqual(asked, ["example.org"])  # the name is looked up once
        self.assertEqual(c.call_args[0][0], ("93.184.216.34", 443))  # and the connection uses the number, not the name again

    def test_a_home_address_is_still_allowed(self):
        with mock.patch("socket.getaddrinfo", answer("192.168.1.20")), mock.patch("socket.create_connection", return_value="s"):
            self.assertEqual(outside.checked_connect(("nas.local", 443), 5), "s")

    def test_ipv4_mapped_metadata_address_is_refused(self):
        with mock.patch("socket.getaddrinfo", answer("::ffff:169.254.169.254")), mock.patch("socket.create_connection") as c:
            with self.assertRaises(ValueError):
                outside.checked_connect(("example.org", 443), 5)
            c.assert_not_called()


class Redirects(unittest.TestCase):
    def follow(self, new):
        h = outside._GuardedRedirect()
        req = urllib.request.Request("https://example.org/starboard-plugin.json")
        with mock.patch("socket.getaddrinfo", answer("93.184.216.34")):
            return h.redirect_request(req, None, 302, "Found", {}, new)

    def test_https_to_a_checked_address_is_followed(self):
        self.assertIsNotNone(self.follow("https://example.com/next.json"))

    def test_https_to_http_is_not_followed(self):
        self.assertIsNone(self.follow("http://example.com/next.json"))

    def test_a_redirect_to_the_metadata_address_is_not_followed(self):
        self.assertIsNone(self.follow("https://169.254.169.254/latest/meta-data"))
        self.assertIsNone(self.follow("https://metadata.google.internal/x"))

    def test_at_most_three_redirects(self):
        self.assertEqual(outside._GuardedRedirect.max_redirections, 3)


class Opener(unittest.TestCase):
    def test_no_plain_http_handler(self):
        o = outside.guarded_opener()
        self.assertFalse(any(isinstance(h, urllib.request.HTTPHandler) for h in o.handlers))
        self.assertTrue(any(isinstance(h, outside._GuardedHTTPS) for h in o.handlers))

    def test_the_three_fetches_use_it(self):
        import inspect
        from starboard import plugin_logo, plugins_admin
        for fn in (plugins_admin.fetch_manifest, plugins_admin.fetch_catalogue, plugin_logo.fetch):
            self.assertIn("guarded_opener", inspect.getsource(fn))


if __name__ == "__main__":
    unittest.main()
