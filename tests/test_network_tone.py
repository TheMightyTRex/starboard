"""Network logos measured once (12 November 2026): the tone is kept for everyone and refused when unknown."""
import tempfile
import unittest

from starboard import networks


class Tone(unittest.TestCase):
    def test_kept_once(self):
        with tempfile.TemporaryDirectory() as d:
            networks._save(d, {"bbc one": {"url": "https://x/bbc.png"}})
            self.assertEqual(networks.tone_of(d, "BBC One"), "")
            networks.set_tone(d, "BBC One", "light")
            self.assertEqual(networks.tone_of(d, "bbc one"), "light")
            self.assertEqual(networks.logo_of(d, "BBC One"), "https://x/bbc.png")
            with self.assertRaises(ValueError):
                networks.set_tone(d, "BBC One", "purple")
            with self.assertRaises(LookupError):
                networks.set_tone(d, "Nowhere TV", "dark")

    def test_solid_from_the_older_rule_is_measured_again(self):  # issues #12 and #13
        with tempfile.TemporaryDirectory() as d:
            networks._save(d, {"cinemax": {"url": "https://x/c.png", "tone": "solid"}, "bbc one": {"url": "https://x/b.png", "tone": "dark"}})
            self.assertEqual(networks.tone_of(d, "Cinemax"), "")  # measured again under the new rule
            self.assertEqual(networks.tone_of(d, "BBC One"), "dark")  # one ink colour was right before too
            networks.set_tone(d, "Cinemax", "invert")
            self.assertEqual(networks.tone_of(d, "Cinemax"), "invert")
            networks.set_tone(d, "Cinemax", "solid")
            self.assertEqual(networks.tone_of(d, "Cinemax"), "solid")  # measured by the new rule: kept


if __name__ == "__main__":
    unittest.main()
