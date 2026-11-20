"""Libraries fetched on first use (pylib): checked downloads, checked files on every load, and clear words offline."""
import base64
import hashlib
import io
import os
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

from starboard import pylib


def _wheel(files):
    """A small wheel with a RECORD, as PyPI's have: (bytes, wheel SHA-256, RECORD SHA-256)."""
    rows = []
    for name, body in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(body).digest()).rstrip(b"=").decode()
        rows.append(f"{name},sha256={digest},{len(body)}")
    rows.append("fakepil-1.0.dist-info/RECORD,,")
    record = ("\n".join(rows) + "\n").encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in files.items():
            z.writestr(name, body)
        z.writestr("fakepil-1.0.dist-info/RECORD", record)
    data = buf.getvalue()
    return data, hashlib.sha256(data).hexdigest(), hashlib.sha256(record).hexdigest()


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class PylibTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data, wheel_sha, record_sha = _wheel({"fakepil/__init__.py": b"VALUE = 42\n"})
        spec = ("x/fakepil-1.0-py3-none-any.whl", wheel_sha, record_sha)
        wheels = {"fake": {"label": "FakePil", "import": "fakepil", "version": "1.0", "download": "about 1 KB"}}
        patches = [mock.patch.dict(os.environ, {"STARBOARD_DATA": self.tmp.name}), mock.patch.object(pylib, "WHEELS", wheels),
                   mock.patch.object(pylib, "_spec", lambda name: spec)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._forget)
        self.calls = 0

    def _forget(self):
        sys.modules.pop("fakepil", None)
        sys.path[:] = [p for p in sys.path if not p.startswith(self.tmp.name)]

    def _open(self, body):
        def opener(req, timeout=None):
            self.calls += 1
            return Answer(body)
        return mock.patch.object(pylib.urllib.request, "urlopen", opener)

    def test_fetched_once_checked_and_kept(self):
        with self._open(self.data):
            pylib.load("fake")
        import fakepil
        self.assertEqual(fakepil.VALUE, 42)
        self.assertEqual(self.calls, 1)
        self._forget()
        with self._open(self.data):
            pylib.load("fake")  # already unpacked and intact: no download
        self.assertEqual(self.calls, 1)

    def test_a_changed_or_added_file_is_fetched_again(self):
        with self._open(self.data):
            pylib.load("fake")
        where = next(p for p in sys.path if p.startswith(self.tmp.name))
        self._forget()
        with open(os.path.join(where, "fakepil", "__init__.py"), "w", encoding="utf-8") as f:
            f.write("VALUE = 666\n")
        with self._open(self.data):
            pylib.load("fake")
        import fakepil
        self.assertEqual(fakepil.VALUE, 42)
        self.assertEqual(self.calls, 2)
        self._forget()
        with open(os.path.join(where, "fakepil", "extra.py"), "w", encoding="utf-8") as f:
            f.write("")
        self.assertFalse(pylib._intact(where, pylib._spec("fake")[2]))

    def test_a_different_download_is_refused(self):
        other, _, _ = _wheel({"fakepil/__init__.py": b"VALUE = 1\n"})
        with self._open(other), self.assertRaisesRegex(pylib.Unavailable, "not the file Starboard expected"):
            pylib.load("fake")

    def test_offline_says_why(self):
        def offline(req, timeout=None):
            raise urllib.error.URLError("no route to host")
        with mock.patch.object(pylib.urllib.request, "urlopen", offline), self.assertRaisesRegex(pylib.Unavailable, "could not download FakePil"):
            pylib.load("fake")

    def test_no_wheel_for_this_processor(self):
        with mock.patch.object(pylib, "_spec", lambda name: None), self.assertRaisesRegex(pylib.Unavailable, "no ready-made version"):
            pylib.load("fake")
        with mock.patch.object(pylib, "_spec", lambda name: None):
            self.assertFalse(pylib.available("fake"))


if __name__ == "__main__":
    unittest.main()
