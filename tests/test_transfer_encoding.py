"""A request with a Transfer-Encoding is refused with 400 and the connection closes (DASH-603, security fix)."""
import socket
import tempfile
import threading
import unittest

from starboard.server import make_server


def ask(port, raw):
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    s.sendall(raw)
    data = b""
    try:
        while True:
            d = s.recv(65536)
            if not d:
                break
            data += d
    except OSError:
        pass
    s.close()
    return data


class TransferEncodingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    def test_chunked_body_is_refused_and_nothing_is_smuggled(self):
        hidden = b"GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
        body = hex(len(hidden))[2:].encode() + b"\r\n" + hidden + b"\r\n0\r\n\r\n"
        for path in (b"/api/login", b"/api/v1/mcp", b"/healthz"):
            data = ask(self.port, b"POST " + path + b" HTTP/1.1\r\nHost: 127.0.0.1\r\nX-Starboard: 1\r\n"
                       b"Transfer-Encoding: chunked\r\n\r\n" + body)
            self.assertEqual(data.count(b"HTTP/1.1 "), 1, path)
            self.assertTrue(data.startswith(b"HTTP/1.1 400"), path)
            self.assertNotIn(b"\r\nok", data)

    def test_any_transfer_encoding_value_is_refused(self):
        data = ask(self.port, b"GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\nTransfer-Encoding: identity\r\n\r\n")
        self.assertTrue(data.startswith(b"HTTP/1.1 400"))

    def test_a_normal_request_still_works(self):
        data = ask(self.port, b"GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        self.assertTrue(data.startswith(b"HTTP/1.1 200"))
        self.assertTrue(data.endswith(b"ok"))


if __name__ == "__main__":
    unittest.main()
