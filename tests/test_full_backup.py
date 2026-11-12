"""Full without media (DASH-260): the encrypted file, and what goes in."""
import base64
import io
import os
import tarfile
import tempfile
import unittest

from starboard import full_backup as fb

try:
    import cryptography  # noqa: F401
    HAVE = True
except ImportError:
    HAVE = False


def sealed(data, password="a long backup password"):
    salt, nonce = b"s" * 16, b"n" * 8
    header = {"format": 1, "kind": "full", "created": "2026-11-12T22:00:00", "apps": ["reelix"], "pictures": False,
              "salt": base64.b64encode(salt).decode(), "nonce": base64.b64encode(nonce).decode()}
    out = io.BytesIO()
    w = fb.Sealed(out, fb.key_of(password, salt), header)
    w.write(data)
    w.close()
    return out.getvalue()


@unittest.skipUnless(HAVE, "cryptography is not installed here")
class Encryption(unittest.TestCase):
    def test_round_trip_over_several_parts(self):
        data = os.urandom(fb.CHUNK * 2 + 123)
        got = fb.Opened(io.BytesIO(sealed(data)), "a long backup password")
        self.assertEqual(io.BufferedReader(got).read(), data)
        self.assertEqual(got.header["apps"], ["reelix"])

    def test_the_header_is_readable_without_the_password(self):
        head, _ = fb.read_header(io.BytesIO(sealed(b"x")))
        self.assertEqual(head["created"], "2026-11-12T22:00:00")

    def test_wrong_password(self):
        with self.assertRaisesRegex(fb.BackupError, "password does not open"):
            io.BufferedReader(fb.Opened(io.BytesIO(sealed(b"secret")), "another long password")).read()

    def test_cut_short_or_changed(self):
        whole = sealed(os.urandom(fb.CHUNK + 10))
        with self.assertRaisesRegex(fb.BackupError, "cut short"):
            io.BufferedReader(fb.Opened(io.BytesIO(whole[:-200]), "a long backup password")).read()
        changed = bytearray(whole)
        changed[-5] ^= 1
        with self.assertRaisesRegex(fb.BackupError, "damaged"):
            io.BufferedReader(fb.Opened(io.BytesIO(bytes(changed)), "a long backup password")).read()

    def test_a_dropped_last_part_is_noticed(self):
        data = os.urandom(fb.CHUNK * 2 + 5)
        whole = sealed(data)
        # Drop the last part (the sealed final one): reading ends early and says so.
        r = io.BytesIO(whole)
        head = fb.read_header(r)
        cut = r.tell()
        parts = []
        while True:
            raw = r.read(4)
            if not raw:
                break
            n = int.from_bytes(raw, "big")
            parts.append(raw + r.read(n))
        with self.assertRaises(fb.BackupError):
            io.BufferedReader(fb.Opened(io.BytesIO(whole[:cut] + b"".join(parts[:-1])), "a long backup password")).read()
        self.assertTrue(head)

    def test_short_password_refused(self):
        with self.assertRaisesRegex(fb.BackupError, "10 characters"):
            fb.key_of("short", b"s" * 16)


class WhatGoesIn(unittest.TestCase):
    def test_starboard_files(self):
        with tempfile.TemporaryDirectory() as d:
            for rel in ("config.json", "sessions.json", "logs/x.log", "posters/a.jpg", "icons/b.png", "library/films.json",
                        "library/station-logos/bbc.png", "library/station-logos.json", "stack/.env", "stack/compose.yaml",
                        "plugins/styles/settings.json", "plugins/on-demand/data/on-demand/p.jpg", "plugins/.removed/old/manifest.json",
                        "backup-work/x", "config.json.before-server-name-20261109"):
                os.makedirs(os.path.dirname(os.path.join(d, rel)) or d, exist_ok=True)
                open(os.path.join(d, rel), "w").close()
            without = {rel for _, rel in fb._starboard_files(d, False)}
            self.assertEqual(without, {"config.json", "library/station-logos.json", "stack/.env", "stack/compose.yaml", "plugins/styles/settings.json"})
            self.assertIn("library/station-logos/bbc.png", {rel for _, rel in fb._starboard_files(d, True)})

    def test_app_excludes_leave_out_what_comes_back(self):
        import fnmatch
        always = fb.APP_SKIP
        out = lambda rel: any(fnmatch.fnmatch(rel, p) for p in always)  # noqa: E731
        for rel in ("jellyfin/data/metadata/library/a.jpg", "jellyfin/cache/images/x", "jellyfin/data/data/introskipper/introskipper-cache.db",
                    "jellyfin/data/plugins/configurations/Jellyfin.Plugin.JellyfinEnhanced/tag-cache.json", "reelix/MediaCover/1/poster.jpg",
                    "nzbget/nzb/a.nzb", "tdarr/cache/x", "jellyfin/log/a.txt", "nzbget/nzbget-2026-11-11.log"):
            self.assertTrue(out(rel), rel)
        for rel in ("jellyfin/data/data/jellyfin.db", "reelix/reelix.db", "audiobookshelf/config/absdatabase.sqlite",
                    "qbittorrent/qBittorrent/qBittorrent.conf", "jellyfin/data/plugins/configurations/Jellyfin.Plugin.JellyfinEnhanced.xml"):
            self.assertFalse(out(rel), rel)

    def test_names(self):
        self.assertTrue(fb.NAME_RE.match("starboard-full-2026-11-12-220000.starboard"))
        self.assertTrue(fb.NAME_RE.match("starboard-full-2026-11-12-220000-pictures.starboard"))
        self.assertFalse(fb.NAME_RE.match("../starboard-full-2026-11-12-220000.starboard"))


if __name__ == "__main__":
    unittest.main()
