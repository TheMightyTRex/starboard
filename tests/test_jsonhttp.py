"""The shared JSON request (jsonhttp): JSON in and out, the size limit, and what an app said with its error."""
import io
import json
import unittest
import urllib.error

from starboard import jsonhttp


class Answer(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Opener:
    def __init__(self, body):
        self.body, self.sent = body, None

    def open(self, req, timeout=None):
        self.sent = req
        return Answer(self.body)


def http_error(body):
    return urllib.error.HTTPError("http://app", 400, "Bad", {}, io.BytesIO(body))


class JsonHttpTest(unittest.TestCase):
    def test_json_in_and_out(self):
        o = Opener(b'{"ok": true}')
        self.assertEqual(jsonhttp.request("http://app/x", "POST", {"a": 1}, {"X-Api-Key": "k"}, opener=o), {"ok": True})
        self.assertEqual(json.loads(o.sent.data), {"a": 1})
        self.assertEqual(o.sent.get_header("Content-type"), "application/json")
        self.assertEqual(o.sent.get_header("X-api-key"), "k")
        self.assertEqual(o.sent.get_header("User-agent"), "Starboard")

    def test_empty_text_limit_and_status(self):
        self.assertIsNone(jsonhttp.request("http://app", opener=Opener(b"")))
        self.assertEqual(jsonhttp.request("http://app", opener=Opener(b"plain words"), text=True), "plain words")
        with self.assertRaises(ValueError):
            jsonhttp.request("http://app", opener=Opener(b"plain words"))
        with self.assertRaises(ValueError):  # cut at the limit, so not whole JSON
            jsonhttp.request("http://app", opener=Opener(b'{"a": "' + b"x" * 100 + b'"}'), limit=50)
        self.assertEqual(jsonhttp.request("http://app", opener=Opener(b"[1]"), full=True), (200, [1]))

    def test_what_the_app_said(self):
        self.assertEqual(jsonhttp.error_message(http_error(b'{"message": "No such series"}')), "No such series")
        self.assertEqual(jsonhttp.error_message(http_error(b'[{"errorMessage": "Path is not valid"}]')), "Path is not valid")
        self.assertEqual(jsonhttp.error_message(http_error(b"<html>")), "")
        self.assertEqual(jsonhttp.error_message(http_error(b'["x"]')), "")
        self.assertEqual(jsonhttp.error_words(http_error(b"  Not allowed here  ")), "Not allowed here")


if __name__ == "__main__":
    unittest.main()
