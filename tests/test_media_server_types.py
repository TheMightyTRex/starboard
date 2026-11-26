"""Plex and Emby as service types of their own (DASH-566, owner, 26 November 2026): the old "Other app" with the icon
plex or emby moves to the type without losing anything, an install that never had one is not written to, the checks
say what they found (answers recorded from each server's documented API), discovery and the icons know the types."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import backup, config, discovery, icons, plugin_systems, services


def folder_with(services_list):
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "config.json"), "w") as f:
        json.dump({**json.loads(json.dumps(config.DEFAULTS)), "schema": config.SCHEMA, "services": services_list}, f)
    return d


OLD_PLEX = {"id": "plex", "name": "Family Plex", "type": "link", "icon": "plex", "url": "http://192.168.1.9:32400", "api_key": "made-up-token", "enabled": True}
OLD_EMBY = {"id": "emby", "name": "Emby", "type": "link", "icon": "Emby", "url": "http://192.168.1.9:8096", "api_key": "made-up-key", "enabled": True}
OTHER = {"id": "wiki", "name": "Wiki", "type": "link", "icon": "wiki", "url": "http://192.168.1.9:3000", "enabled": True}


class Migration(unittest.TestCase):
    def test_an_other_app_with_the_plex_or_emby_icon_becomes_that_type_and_keeps_everything(self):
        d = folder_with([OLD_PLEX, OLD_EMBY, OTHER])
        got = {s["id"]: s for s in config.Config(d).data["services"]}
        self.assertEqual((got["plex"]["type"], got["emby"]["type"], got["wiki"]["type"]), ("plex", "emby", "link"))
        for old in (OLD_PLEX, OLD_EMBY):
            for key in ("name", "url", "api_key", "enabled", "icon"):
                self.assertEqual(got[old["id"]][key], old[key])
        with open(os.path.join(d, "config.json")) as f:  # saved, so it happens once
            self.assertEqual([s["type"] for s in json.load(f)["services"]], ["plex", "emby", "link"])

    def test_an_install_that_never_had_one_is_not_written_to(self):
        for before in ([], [OTHER], [{"id": "j", "name": "Jellyfin", "type": "jellyfin", "url": "http://x", "enabled": True}]):
            d = folder_with(before)
            path = os.path.join(d, "config.json")
            config.Config(d)  # settles anything older Starboards left (not this change's)
            os.utime(path, (1000, 1000))
            config.Config(d)
            self.assertEqual(os.stat(path).st_mtime, 1000, before)

    def test_a_second_start_changes_nothing(self):
        d = folder_with([OLD_PLEX])
        config.Config(d)
        path = os.path.join(d, "config.json")
        os.utime(path, (1000, 1000))
        config.Config(d)
        self.assertEqual(os.stat(path).st_mtime, 1000)

    def test_a_settings_backup_from_before_restores_to_the_types(self):
        cfg = config.Config(folder_with([]))
        old = {"format": backup.FORMAT, "version": "0.31.0", "schema": config.SCHEMA, "settings": {}, "services": [dict(OLD_PLEX), dict(OTHER)]}
        backup.restore(cfg, old)
        self.assertEqual([s["type"] for s in cfg.data["services"]], ["plex", "link"])
        saved = json.loads(json.dumps(backup.export(cfg, "0.32.0")))
        self.assertEqual(saved["services"][0]["type"], "plex")
        self.assertEqual(saved["services"][0]["api_key"], "made-up-token")  # a full backup carries the key, as for every app

    def test_the_types_are_known_to_the_form_checks(self):
        for kind in ("plex", "emby"):
            self.assertEqual(config.SERVICE_TYPES[kind]["label"], kind.title())
            clean = config.validate_service({"name": "My server", "type": kind, "url": "http://192.168.1.9:32400", "api_key": "k"})
            self.assertEqual(clean["type"], kind)


class Checks(unittest.TestCase):
    def setUp(self):
        self.asked = []

    def fetch(self, answers):
        def one(service, req, timeout):
            path = "/" + req.full_url.split("/", 3)[3].split("?", 1)[0]
            self.asked.append((path, dict(req.header_items())))
            got = answers[path]
            if isinstance(got, Exception):
                raise got
            return got
        return mock.patch.object(services, "_fetch", side_effect=one)

    def test_plex_says_its_version_and_checks_the_token(self):
        svc = {"id": "p", "name": "Plex", "type": "plex", "url": "http://x:32400", "api_key": "tok", "enabled": True}
        with self.fetch({"/identity": {"MediaContainer": {"version": "1.41.3.9314-abc"}}, "/library/sections": {"MediaContainer": {}}}):
            got = services.check(svc)
        self.assertEqual((got["state"], got["version"]), ("up", "1.41.3.9314"))
        self.assertEqual([p for p, _ in self.asked], ["/identity", "/library/sections"])
        self.assertTrue(all("tok" not in p for p, _ in self.asked))  # never in an address

    def test_plex_with_a_wrong_token_is_down_in_words(self):
        svc = {"id": "p", "name": "Plex", "type": "plex", "url": "http://x:32400", "api_key": "bad", "enabled": True}
        with self.fetch({"/identity": {"MediaContainer": {"version": "1.41.3"}}, "/library/sections": services.ServiceError("Plex refused the API key")}):
            got = services.check(svc)
        self.assertEqual((got["state"], got["message"]), ("down", "Plex refused the API key"))

    def test_emby_says_its_version_and_checks_the_key(self):
        svc = {"id": "e", "name": "Emby", "type": "emby", "url": "http://x:8096", "api_key": "k", "enabled": True}
        with self.fetch({"/emby/System/Info/Public": {"Version": "4.8.10.0"}, "/emby/System/Info": {"Version": "4.8.10.0"}}):
            got = services.check(svc)
        self.assertEqual((got["state"], got["version"]), ("up", "4.8.10.0"))
        self.assertEqual(self.asked[-1][1].get("X-emby-token"), "k")

    def test_a_server_with_no_key_yet_is_up_and_asks_for_nothing_private(self):
        svc = {"id": "e", "name": "Emby", "type": "emby", "url": "http://x:8096", "api_key": "", "enabled": True}
        with self.fetch({"/emby/System/Info/Public": {"Version": "4.8.10.0"}}):
            got = services.check(svc)
        self.assertEqual(got["state"], "up")
        self.assertEqual(len(self.asked), 1)

    def test_not_reached_is_said(self):
        svc = {"id": "e", "name": "Emby", "type": "emby", "url": "http://x:8096", "api_key": "k", "enabled": True}
        with self.fetch({"/emby/System/Info/Public": services.ServiceError("Cannot reach Emby")}):
            got = services.check(svc)
        self.assertEqual((got["state"], got["message"]), ("down", "Cannot reach Emby"))


class Around(unittest.TestCase):
    def test_discovery_adds_them_as_their_own_type_and_wants_a_key(self):
        for key in ("plex", "emby"):
            name, kind, _ports, _rule, needs_key, background = discovery.CATALOGUE[key]
            self.assertEqual((kind, needs_key, background), (key, True, False))
        self.assertNotIn("plex", discovery.READABLE)  # DASH-595: its token is never read from its container
        self.assertNotIn("plex", discovery.KEY_FILES)

    def test_an_app_already_added_is_not_offered_again(self):
        with mock.patch.object(discovery, "_probe", side_effect=lambda port: ["plex"] if port == 32400 else []), \
                mock.patch.object(discovery.containers, "available", return_value=False):
            got = discovery.search([{"id": "p", "name": "Family room", "type": "plex", "url": "http://elsewhere:9", "link": ""}])
        self.assertTrue([i for i in got["items"] if i["key"] == "plex"][0]["already"])

    def test_the_icon_is_its_own_whatever_the_app_is_called(self):
        self.assertEqual(icons.default_name({"name": "Family room", "type": "plex"}), "plex")
        self.assertEqual(icons.default_name({"name": "Family room", "type": "emby"}), "emby")
        self.assertEqual(icons.default_name({"name": "Family room", "type": "link"}), "family-room")
        self.assertEqual(icons.source({"name": "Den", "type": "plex", "icon": "https://example.com/p.svg"}), ("url", "https://example.com/p.svg"))

    def test_a_plug_in_that_needs_plex_finds_it_by_type(self):
        have = plugin_systems.present_in([{"type": "plex", "url": "http://x", "enabled": True}])
        self.assertIn("plex", have)
        self.assertNotIn("plex", plugin_systems.present_in([{"type": "plex", "url": "http://x", "enabled": False}]))


if __name__ == "__main__":
    unittest.main()
