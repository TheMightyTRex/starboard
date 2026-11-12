"""Settings, Radio: each source with what it is for, and (Reelix RFX-102) how its episodes arrive and its stations."""
import unittest

from starboard import radio_settings


class Fake:
    def __init__(self, providers, settings=None):
        self.answers = {"/radio/providers": providers, "/radio/settings": settings or {}}

    def call(self, method, path, body=None):
        return 200, self.answers[path]


class State(unittest.TestCase):
    def test_new_reelix_says_how_episodes_arrive(self):
        r = Fake([{"id": "bbc", "name": "BBC", "supports_search": True, "enabled": True,
                   "episodes_arrive": "Programme pages; audio from the programme's podcast feed or your download sites",
                   "stations": [{"id": "bbc_radio_kent", "name": "BBC Radio Kent"}] * 66},
                  {"id": "podcastindex", "name": "Podcast Index", "enabled": False, "key_needed": True, "episodes_arrive": "Podcast feeds"}])
        s = radio_settings.state(r)
        bbc, pi = s["sources"]
        self.assertIn("Episodes: programme pages", bbc["about"])
        self.assertIn("66 stations.", bbc["about"])
        self.assertTrue(pi["needs_key"])
        self.assertFalse(pi["works"])

    def test_older_reelix_still_works(self):
        s = radio_settings.state(Fake([{"id": "apple", "name": "Apple Podcasts", "enabled": True}]))
        self.assertTrue(s["sources"][0]["about"].startswith("Apple Podcasts:"))
        self.assertFalse(s["sources"][0]["needs_key"])


if __name__ == "__main__":
    unittest.main()
