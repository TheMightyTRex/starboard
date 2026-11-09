"""qBittorrent's sign-in made up before its first start, the category folders and the seeds on a browser start
(DASH-232, DASH-184, DASH-258)."""
import base64
import hashlib
import os
import re
import tempfile
import unittest

from starboard import stack


class QbittorrentSeed(unittest.TestCase):
    def test_the_hash_is_qbittorrents_own(self):
        text = stack.qbittorrent_seed("made-up-test-password-123")
        salt, digest = (base64.b64decode(x) for x in re.search(r'@ByteArray\(([^:]+):([^)]+)\)', text).groups())
        self.assertEqual(hashlib.pbkdf2_hmac("sha512", b"made-up-test-password-123", salt, 100000, 64), digest)
        self.assertIn("WebUI\\Username=admin", text)
        self.assertIn("Session\\DefaultSavePath=/data/downloads/torrents", text)
        self.assertNotIn("made-up-test-password-123", text)

    def test_write_leaves_the_seed_and_the_password_in_env(self):
        built = stack.build({"apps": ["qbittorrent"], "groups": ["downloads"], "config_dir": "/srv/config", "data_dir": "/srv/media",
                             "puid": 1000, "pgid": 1000, "tz": "Europe/London"})
        with tempfile.TemporaryDirectory() as d:
            stack.write(d, built)
            seed = os.path.join(stack.folder(d), "seed", "qbittorrent", "qBittorrent__qBittorrent.conf")
            self.assertEqual(os.stat(seed).st_mode & 0o777, 0o600)
            self.assertTrue(stack.qbittorrent_password(d))
        self.assertIn("/srv/media/downloads/torrents/movies-reelix", built["folders"])
        self.assertIn("/srv/media/downloads/usenet/completed/tv", built["folders"])

    def test_the_browser_start_copies_seeds_without_replacing_settings(self):
        script = stack.seed_script("/srv/config", "/srv/media", 1000, 1000)
        self.assertIn('[ -e "$t" ] && continue', script)
        self.assertIn("folders.txt", script)
        self.assertIn("sed 's#__#/#g'", script)


if __name__ == "__main__":
    unittest.main()
