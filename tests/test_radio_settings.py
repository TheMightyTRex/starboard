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


class Catchup(unittest.TestCase):
    def test_catchup_switches_and_the_list_is_always_sent(self):
        sent = {}

        class R(Fake):
            def call(self, method, path, body=None):
                if method == "PUT":
                    sent.update(body)
                    return 200, body
                return super().call(method, path, body)

        r = R([{"id": "bbc", "name": "BBC", "enabled": True, "catchup": True, "risk": "BBC terms."},
               {"id": "nts", "name": "NTS", "enabled": False, "catchup": True, "risk": "NTS terms."},
               {"id": "apple", "name": "Apple Podcasts", "enabled": True}], {"catchup_providers": []})
        s = radio_settings.state(r)
        nts = [x for x in s["sources"] if x["id"] == "nts"][0]
        self.assertFalse(nts["on"], "off by default")
        self.assertTrue(nts["catchup"] and not nts["catchup_on"])
        radio_settings.save(r, {"on": ["bbc", "nts", "apple"], "catchup": ["nts", "apple"], "country": "", "language": ""})
        self.assertEqual(sent["enabled_providers"], ["bbc", "nts", "apple"], "every source on is still a list")
        self.assertEqual(sent["catchup_providers"], ["nts"], "Apple has no catch-up")

    def test_older_reelix_gets_no_catchup_setting(self):
        sent = {}

        class R(Fake):
            def call(self, method, path, body=None):
                if method == "PUT":
                    sent.update(body)
                    return 200, body
                return super().call(method, path, body)

        radio_settings.save(R([{"id": "bbc", "name": "BBC", "enabled": True}]), {"on": ["bbc"], "country": "", "language": ""})
        self.assertNotIn("catchup_providers", sent)


if __name__ == "__main__":
    unittest.main()
