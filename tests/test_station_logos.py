"""Station logos (owner, 12 November 2026): matched by name with the files' short forms, kept, and added from a zip."""
import io
import os
import tempfile
import unittest
import zipfile

from starboard import station_logos as sl

PNG = b"\\x89PNG\\r\\n\\x1a\\n".decode("unicode_escape").encode("latin-1") + b"\\0" * 32
FILES = ["BBC-Radio-4.png", "BBC-Radio-4Extra.png", "BBC-Radio-Brist.png", "BBC-R-Scotland.png", "BBC-3CR.png", "LBC-UK.png",
         "LBC-London.png", "BBC-H-W.png", "Capital.png", "Capital-UK.png"]


class Match(unittest.TestCase):
    def test_names(self):
        for station, want in [("BBC Radio 4 Extra", "BBC-Radio-4Extra.png"), ("BBC Radio 4", "BBC-Radio-4.png"),
                              ("BBC Radio Bristol", "BBC-Radio-Brist.png"), ("BBC Radio Scotland", "BBC-R-Scotland.png"),
                              ("BBC Three Counties Radio", "BBC-3CR.png"), ("LBC", "LBC-UK.png"),
                              ("BBC Hereford & Worcester", "BBC-H-W.png"), ("Capital", "Capital.png"), ("Nowhere FM", "")]:
            self.assertEqual(sl.match(station, FILES), want, station)


class Folder(unittest.TestCase):
    def test_zip_kept_and_served(self):
        with tempfile.TemporaryDirectory() as d:
            raw = io.BytesIO()
            with zipfile.ZipFile(raw, "w") as z:
                z.writestr("logos/BBC-Radio-4.png", PNG)
                z.writestr("logos/notes.txt", b"hello")
                z.writestr("logos/fake.png", b"not a picture")
                z.writestr("../escape.png", PNG)
            out = sl.add_zip(d, raw.getvalue())
            self.assertEqual((out["added"], out["skipped"]), (2, 2))  # escape.png lands inside the folder by its base name
            self.assertFalse(os.path.exists(os.path.join(d, "escape.png")))
            self.assertEqual(sl.logo_of(d, "BBC Radio 4")["file"], "BBC-Radio-4.png")
            self.assertEqual(sl.picture(d, "BBC Radio 4")[1], "image/png")
            sl.set_tone(d, "BBC Radio 4", "light")
            self.assertEqual(sl.logo_of(d, "BBC Radio 4")["tone"], "light")
            with self.assertRaises(LookupError):
                sl.set_tone(d, "Nowhere FM", "dark")
            self.assertEqual(sl.summary(d, ["BBC Radio 4", "Nowhere FM"])["missing"], ["Nowhere FM"])
        with self.assertRaises(ValueError):
            sl.add_zip(tempfile.mkdtemp(), b"not a zip")


if __name__ == "__main__":
    unittest.main()
