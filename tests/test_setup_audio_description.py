"""Audio description in the first set-up (DASH-399): both set-ups offer it in the same words, unticked; ticking saves a
wish only; the Plug-ins pages offer to install it from the catalogue, with its permissions and the password, until it
is added or someone chooses Not now."""
import json
import os
import tempfile
import unittest

from starboard import config as config_mod
from starboard import plugins_admin as pa
from starboard import setup_answers
from starboard import terminal_setup as ts
from tests.test_terminal_setup_rules import FakeApi, plain

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
WORDS = setup_answers.WORDS["audio_description"]


class Cfg:
    def __init__(self, extras):
        import threading
        self.data, self.lock, self.saved = {"extras": dict(extras)}, threading.Lock(), 0

    def save(self):
        self.saved += 1


class TerminalSetup(unittest.TestCase):
    def test_offered_unticked_in_the_same_words(self):
        config = {"services": [{"type": "jellyfin"}], "extras": dict(config_mod.DEFAULTS["extras"])}
        api = FakeApi({("GET", "/api/config"): config})
        term, out = plain(["0"])  # Enter or 0: none ticked
        self.assertTrue(ts.step_connect(api, term, {}))
        text = " ".join(out.getvalue().split())
        self.assertIn(WORDS["label"], text)
        self.assertIn(" ".join(WORDS["hint"].split()[:6]), text)
        self.assertIn("Your choice [", "\n".join(term._ask.prompts))
        self.assertNotIn("Your choice [4", "\n".join(term._ask.prompts))  # not ticked to start with
        self.assertIs(api.calls[-1][2]["extras"]["audio_description"], False)

    def test_ticked_saves_the_wish_and_says_where_to_install(self):
        config = {"services": [{"type": "jellyfin"}], "extras": dict(config_mod.DEFAULTS["extras"])}
        api = FakeApi({("GET", "/api/config"): config})
        term, out = plain(["4"])
        self.assertTrue(ts.step_connect(api, term, {}))
        self.assertEqual(api.calls[-1][2]["extras"], {"livetv": False, "import_keep": False, "defaults": False, "audio_description": True})
        self.assertIn(" ".join(WORDS["chosen"].split()[:5]), " ".join(out.getvalue().split()))


class BrowserSetup(unittest.TestCase):
    def test_the_browser_set_up_reads_the_same_words(self):
        with open(os.path.join(ROOT, "web", "js", "settings.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertIn('.audio_description;', js)
        self.assertIn('box("audio_description", ad.label, ad.hint)', js)


class Config(unittest.TestCase):
    def test_unticked_by_default_and_saved_as_true_or_false(self):
        self.assertIs(config_mod.DEFAULTS["extras"]["audio_description"], False)
        out = config_mod.clean_extras({"audio_description": 1}, config_mod.DEFAULTS["extras"])
        self.assertIs(out["audio_description"], True)


class Offer(unittest.TestCase):
    def test_offered_until_added_or_not_now(self):
        cfg = Cfg({"audio_description": True})
        got = pa.wanted_from_setup(cfg, set())
        self.assertEqual([w["id"] for w in got], ["audio-description"])
        self.assertEqual(got[0]["title"], WORDS["notice_title"])
        self.assertEqual(pa.wanted_from_setup(cfg, {"audio-description"}), [])  # already added
        self.assertEqual(pa.drop_wanted(cfg, "audio-description"), WORDS["later_done"])
        self.assertIs(cfg.data["extras"]["audio_description"], False)
        self.assertEqual(pa.wanted_from_setup(cfg, set()), [])
        with self.assertRaises(ValueError):
            pa.drop_wanted(cfg, "styles")

    def test_not_ticked_is_never_offered(self):
        self.assertEqual(pa.wanted_from_setup(Cfg({"audio_description": False}), set()), [])

    def test_the_shipped_catalogue_lists_it_as_coming(self):
        with open(os.path.join(ROOT, "plugins", "catalogue.json"), encoding="utf-8") as f:
            entry = next(p for p in json.load(f)["plugins"] if p["id"] == "audio-description")
        self.assertEqual(entry["kind"], "Accessibility")
        self.assertFalse(entry["published"])  # until the shared image is built with it and pinned


class Words(unittest.TestCase):
    def test_plain_words(self):
        text = json.dumps(WORDS, ensure_ascii=False)
        self.assertNotIn("—", text)
        for bad in ("n't", "turn on", "turn off", "switch on", "switch off", "enable", "disable"):
            self.assertNotIn(bad, text.lower())


if __name__ == "__main__":
    unittest.main()
