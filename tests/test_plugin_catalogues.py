"""Plug-in catalogues (owner, 12 November 2026): Starboard's own collection, and others added from a link."""
import io
import json
import unittest
from unittest import mock

from starboard import plugins_admin as pa


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Opener:
    def __init__(self, answers):
        self.answers, self.asked = answers, []

    def open(self, req, timeout=None):
        self.asked.append(req.full_url)
        a = self.answers.get(req.full_url)
        if a is None:
            raise OSError("no answer")
        return Resp(json.dumps(a).encode())


class Cfg:
    def __init__(self):
        self.data, self.saved = {}, 0

    def save(self):
        self.saved += 1


OTHER = "https://example.org/catalogue.json"
ENTRY = {"id": "hello", "name": "Hello", "description": "Says hello", "kind": "Look", "manifest": "https://example.org/hello.json",
         "permissions": ["network:lan", "made:up"]}


@mock.patch("starboard.outside.check_url", lambda url: None)
class Catalogues(unittest.TestCase):
    def setUp(self):
        pa._catalogues.clear()

    def test_add_read_remove(self):
        cfg = Cfg()
        op = Opener({OTHER: {"name": "Friend's plug-ins", "plugins": [ENTRY, {"id": "BAD ID"}]},
                     pa.CATALOGUE_URL: {"name": "Starboard plug-ins", "plugins": []}})
        got = pa.add_source(cfg, OTHER, op)
        self.assertEqual((got["name"], len(got["items"])), ("Friend's plug-ins", 1))
        self.assertEqual(cfg.data["plugin_catalogues"], [{"url": OTHER, "name": "Friend's plug-ins"}])
        with self.assertRaises(ValueError):
            pa.add_source(cfg, OTHER, op)  # already there
        cats, items = pa.catalogue(cfg, op, now=1000)
        self.assertEqual([c["own"] for c in cats], [True, False])
        self.assertEqual(items[0]["permissions"], ["network:lan"])  # unknown permissions dropped
        self.assertEqual(items[0]["catalogue"], "Friend's plug-ins")
        pa.remove_source(cfg, OTHER)
        self.assertEqual(cfg.data["plugin_catalogues"], [])
        with self.assertRaises(LookupError):
            pa.remove_source(cfg, OTHER)

    def test_refuses_what_is_not_a_catalogue(self):
        for bad in ("http://example.org/c.json", "not an address"):
            with self.assertRaises(ValueError):
                pa.fetch_catalogue(bad, Opener({}))
        with self.assertRaises(ValueError):
            pa.fetch_catalogue(OTHER, Opener({OTHER: {"hello": 1}}))
        with self.assertRaises(ValueError):
            pa.fetch_catalogue(OTHER, Opener({}))

    def test_own_falls_back_to_shipped_copy_and_others_keep_last_list(self):
        cfg = Cfg()
        cfg.data["plugin_catalogues"] = [{"url": OTHER, "name": "x"}]
        op = Opener({OTHER: {"name": "Friend", "plugins": [ENTRY]}})
        cats, items = pa.catalogue(cfg, op, now=1000)
        self.assertGreater(cats[0]["count"], 0)  # the copy Starboard ships
        self.assertEqual(cats[0]["error"], "")
        cats, items = pa.catalogue(cfg, Opener({}), now=1000 + 90000)  # a day later, nothing answers
        self.assertTrue(cats[1]["error"])
        self.assertEqual(cats[1]["count"], 1)  # the last good list

    def test_read_once_a_day(self):
        op = Opener({pa.CATALOGUE_URL: {"name": "S", "plugins": [ENTRY]}})
        pa.catalogue(None, op, now=1000)
        pa.catalogue(None, op, now=2000)
        self.assertEqual(len(op.asked), 1)


if __name__ == "__main__":
    unittest.main()
