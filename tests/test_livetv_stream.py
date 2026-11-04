"""Live TV guides are read while they unpack (DASH-79): a DOCTYPE line is accepted, entities are refused, and the
unpacked size is still capped."""

import gzip
import http.server
import threading
import unittest
from unittest import mock

from starboard import livetv

GUIDE = (b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n<tv>'
         + b"".join(b'<programme channel="c%d" start="1"><title>Show %d</title></programme>' % (i % 3, i) for i in range(2000))
         + b"</tv>")
BOMB = b'<?xml version="1.0"?>\n<!DOCTYPE tv [<!ENTITY a "aaaaaaaaaa">]>\n<tv>&a;</tv>'


class Serve(http.server.BaseHTTPRequestHandler):
    files = {"/guide.xml.gz": gzip.compress(GUIDE), "/bomb.xml.gz": gzip.compress(BOMB)}

    def do_GET(self):
        body = self.files[self.path]
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class GuideStreamTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Serve)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_a_doctype_line_is_read(self):
        titles = [el.findtext("title") for _, el in livetv._guide_events(f"{self.base}/guide.xml.gz") if el.tag == "programme"]
        self.assertEqual(len(titles), 2000)
        self.assertEqual(titles[-1], "Show 1999")

    def test_entities_are_refused(self):
        with self.assertRaises(ValueError):
            list(livetv._guide_events(f"{self.base}/bomb.xml.gz"))

    def test_the_unpacked_size_is_capped(self):
        with mock.patch.object(livetv, "MAX_UNPACKED", 70000):
            with self.assertRaises(ValueError):
                list(livetv._guide_events(f"{self.base}/guide.xml.gz"))

    def test_only_web_addresses(self):
        with self.assertRaises(ValueError):
            list(livetv._guide_events("file:///etc/passwd"))


if __name__ == "__main__":
    unittest.main()
