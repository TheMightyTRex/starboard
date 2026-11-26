"""Emby and Plex as media servers (DASH-566): the same contract as Jellyfin, read only, answered from recorded answers of
each server's documented API (nothing real is asked). The pages keep asking GET /api/jellyfin, so the dashboard, System
and Activity show whichever one is in use."""
import unittest
from unittest import mock

from starboard import mediaserver, services
from starboard.mediaservers import emby, plex

EMBY = {"id": "emby", "name": "Emby", "type": "link", "icon": "emby", "url": "http://192.168.1.9:8096", "api_key": "made-up-emby-key", "enabled": True}
PLEX = {"id": "plex", "name": "Plex", "type": "link", "icon": "plex", "url": "http://192.168.1.9:32400", "api_key": "made-up-plex-token", "enabled": True}
JF = {"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin", "url": "http://192.168.1.9:8097", "api_key": "made-up-jf-key", "enabled": True}

EMBY_ANSWERS = {
    "/emby/System/Info": {"Version": "4.8.10.0", "ServerName": "Den", "HasUpdateAvailable": True, "HasPendingRestart": False},
    "/emby/Sessions": [{"UserName": "Sam", "DeviceName": "Lounge", "Client": "Emby Theater",
                        "NowPlayingItem": {"Name": "Dune", "Type": "Movie", "RunTimeTicks": 2000},
                        "PlayState": {"PositionTicks": 500, "IsPaused": True}, "TranscodingInfo": {"IsVideoDirect": False, "TranscodeReasons": ["ContainerNotSupported"]}},
                       {"UserName": "Alex", "DeviceName": "Phone"}, "junk"],
    "/emby/Items": {"Items": [{"Name": "Pilot", "SeriesName": "Harbour", "Type": "Episode", "DateCreated": "2026-11-20T10:00:00.0000000Z", "ProductionYear": 2026}]},
    "/emby/Library/VirtualFolders": [{"Name": "Films", "ItemId": "7", "CollectionType": "movies"}, {"Name": "Mixed"}, "junk"],
    "/emby/Users": [{"Id": "u1", "Name": "Sam", "Policy": {"IsAdministrator": True}}, {"Id": "u2", "Name": "Alex"}],
    "/emby/Library/Refresh": "",
}
PLEX_ANSWERS = {
    "/": {"MediaContainer": {"friendlyName": "Den", "version": "1.41.3.9314-a0bfb8370"}},
    "/status/sessions": {"MediaContainer": {"size": 2, "Metadata": [
        {"title": "Dune", "type": "movie", "duration": 2000, "viewOffset": 500, "User": {"title": "Sam"},
         "Player": {"title": "Lounge TV", "product": "Plex for Android", "state": "paused"}, "TranscodeSession": {"videoDecision": "transcode"}},
        {"title": "Pilot", "grandparentTitle": "Harbour", "type": "episode", "duration": 0, "User": {"title": "Alex"}, "Player": {"title": "Phone", "state": "playing"}},
        "junk"]}},
    "/library/recentlyAdded": {"MediaContainer": {"Metadata": [{"title": "Pilot", "grandparentTitle": "Harbour", "type": "episode", "addedAt": 1795000000, "year": 2026},
                                                                {"title": "Odd", "type": "weird", "addedAt": "soon"}]}},
    "/library/sections": {"MediaContainer": {"Directory": [{"key": "1", "title": "Films", "type": "movie"}, {"key": "2", "title": "Series", "type": "show"}, {"key": "3", "title": "Odd", "type": "x"}, "junk"]}},
    "/accounts": {"MediaContainer": {"Account": [{"id": 1, "name": "Owner"}, {"id": 2, "name": "Sam"}, {"id": 3}]}},
    "/library/sections/all/refresh": "",
}


class Fetch:
    """services._fetch, answering from a table by path (without its query) and noting what was asked and how."""

    def __init__(self, table):
        self.table, self.seen = table, []

    def __call__(self, service, req, timeout):
        path = req.full_url.split("/", 3)[3] if req.full_url.count("/") >= 3 else ""
        path = "/" + path.split("?", 1)[0]
        self.seen.append((req.get_method(), path, dict(req.header_items()), req.full_url))
        if path not in self.table:
            raise AssertionError(f"asked for {path}")
        answer = self.table[path]
        if isinstance(answer, Exception):
            raise answer
        return answer


class Shared:
    def setUp(self):
        self.fetch = Fetch(self.answers)
        p = mock.patch.object(services, "_fetch", side_effect=self.fetch)
        p.start()
        self.addCleanup(p.stop)

    def test_every_required_call_is_there_and_it_offers_only_what_it_does(self):
        for call in mediaserver.REQUIRED:
            self.assertTrue(callable(getattr(self.one, call)), call)
        self.assertEqual(set(self.one.capabilities) - set(mediaserver.CAPABILITIES), set())
        self.assertEqual(self.one.capabilities, ())  # read only for now
        d = self.one.describe()
        self.assertEqual((d["id"], d["kind"], d["capabilities"]), (self.one.id, "media-server", []))

    def test_not_set_up_is_said_in_words(self):
        for services_list in ([], [{**self.svc, "api_key": ""}], [{**self.svc, "enabled": False}], [{**self.svc, "icon": "other"}], [JF]):
            with self.assertRaises(services.ServiceError) as e:
                self.one.libraries(services_list)
            self.assertIn(f"{self.one.name} is not set up yet", str(e.exception))
            self.assertEqual(self.one.legacy_status(services_list), {"configured": False})
            self.assertFalse(self.one.status(services_list)["configured"])
        self.assertFalse(self.one.sign_in_check([])["ok"])

    def test_the_key_goes_in_a_header_never_in_an_address(self):
        self.one.libraries([self.svc])
        self.assertTrue(self.fetch.seen)
        for _method, _path, headers, url in self.fetch.seen:
            self.assertNotIn(self.svc["api_key"], url)
            self.assertIn(self.svc["api_key"], " ".join(headers.values()))

    def test_the_old_status_has_the_shape_the_pages_draw(self):
        got = self.one.legacy_status([self.svc])
        jelly_keys = {"configured", "name", "version", "update", "restart", "can_restart", "playing", "added", "channels", "guide"}
        self.assertEqual(set(got), jelly_keys)
        for p in got["playing"]:
            self.assertEqual(set(p), {"user", "device", "client", "title", "series", "type", "paused", "progress", "transcoding", "reason"})
        for a in got["added"]:
            self.assertEqual(set(a), {"title", "series", "type", "when", "year"})

    def test_a_server_that_does_not_answer_is_a_down_status_with_its_reason(self):
        self.answers[next(iter(self.answers))] = services.ServiceError("Cannot reach Den")
        got = self.one.status([self.svc])
        self.assertEqual((got["configured"], got["up"], got["why"]), (True, False, "Cannot reach Den"))
        self.assertEqual(self.one.sign_in_check([self.svc]), {"ok": False, "why": "Cannot reach Den"})

    def test_it_is_found_through_the_slot_and_the_pages_ask_it(self):
        data = {"extras": {"media_server": self.one.id}, "services": [JF, self.svc]}
        self.assertEqual(mediaserver.active(data).id, self.one.id)
        self.assertTrue(mediaserver.state(data)["configured"])
        self.assertEqual(mediaserver.status_for_pages(data)["name"], self.svc["name"])
        self.assertFalse(mediaserver.state({"extras": {"media_server": self.one.id}, "services": [JF]})["configured"])


class EmbyTests(Shared, unittest.TestCase):
    one = emby.Emby()
    svc = EMBY

    def setUp(self):
        self.answers = dict(EMBY_ANSWERS)
        super().setUp()

    def test_status_and_what_it_found(self):
        got = self.one.legacy_status([EMBY])
        self.assertEqual((got["name"], got["version"], got["update"], got["restart"], got["can_restart"]), ("Emby", "4.8.10.0", True, False, False))
        self.assertEqual(len(got["playing"]), 1)  # the one with nothing playing, and the junk row, are left out
        p = got["playing"][0]
        self.assertEqual((p["user"], p["title"], p["type"], p["paused"], p["progress"], p["transcoding"], p["reason"]),
                         ("Sam", "Dune", "Movie", True, 25, True, "ContainerNotSupported"))
        self.assertEqual(got["added"][0]["series"], "Harbour")
        self.assertEqual(self.one.status([EMBY]), {"configured": True, "up": True, "name": "Emby", "version": "4.8.10.0", "update_available": True,
                                                   "restart_needed": False, "playing": 1, "why": ""})

    def test_the_calls_use_emby_paths_and_its_header(self):
        self.one.users([EMBY])
        self.assertEqual(self.fetch.seen[0][1], "/emby/Users")
        self.assertEqual({k.lower() for k in self.fetch.seen[0][2]}, {"x-emby-token", "accept", "user-agent"})

    def test_libraries_users_refresh_and_the_check(self):
        self.assertEqual(self.one.libraries([EMBY]), [{"id": "7", "name": "Films", "type": "movies", "count": None},
                                                       {"id": "Mixed", "name": "Mixed", "type": "mixed", "count": None}])
        self.assertEqual(self.one.users([EMBY]), [{"id": "u1", "name": "Sam", "admin": True}, {"id": "u2", "name": "Alex", "admin": False}])
        self.assertEqual(self.one.refresh([EMBY]), {"asked": True})
        self.assertEqual(self.fetch.seen[-1][:2], ("POST", "/emby/Library/Refresh"))
        self.assertEqual(self.one.sign_in_check([EMBY]), {"ok": True, "why": "", "name": "Den", "version": "4.8.10.0"})
        self.assertEqual([x["kind"] for x in self.one.playing([EMBY])], ["Movie"])
        self.assertEqual(self.one.recent([EMBY], limit=1)[0]["title"], "Pilot")

    def test_keys_are_said_in_words(self):
        k = self.one.keys_needed()[0]
        self.assertIn("API key", k["what"])
        self.assertIn("icon emby", k["kept"])


class PlexTests(Shared, unittest.TestCase):
    one = plex.Plex()
    svc = PLEX

    def setUp(self):
        self.answers = dict(PLEX_ANSWERS)
        super().setUp()

    def test_status_and_what_it_found(self):
        got = self.one.legacy_status([PLEX])
        self.assertEqual((got["name"], got["version"], got["update"], got["restart"], got["can_restart"]), ("Plex", "1.41.3.9314", False, False, False))
        self.assertEqual(len(got["playing"]), 2)
        a, b = got["playing"]
        self.assertEqual((a["user"], a["device"], a["title"], a["type"], a["paused"], a["progress"], a["transcoding"]),
                         ("Sam", "Lounge TV", "Dune", "Movie", True, 25, True))
        self.assertEqual((b["series"], b["type"], b["progress"], b["transcoding"], b["paused"]), ("Harbour", "Episode", None, False, False))
        self.assertEqual(got["added"][0], {"title": "Pilot", "series": "Harbour", "type": "Episode", "when": "2026-11-18T11:06:40Z", "year": 2026})
        self.assertEqual((got["added"][1]["type"], got["added"][1]["when"]), ("weird", ""))
        self.assertEqual(self.one.status([PLEX])["playing"], 2)

    def test_libraries_users_refresh_and_the_check(self):
        self.assertEqual(self.one.libraries([PLEX]), [{"id": "1", "name": "Films", "type": "movies", "count": None},
                                                      {"id": "2", "name": "Series", "type": "tvshows", "count": None},
                                                      {"id": "3", "name": "Odd", "type": "mixed", "count": None}])
        self.assertEqual(self.one.users([PLEX]), [{"id": "1", "name": "Owner", "admin": True}, {"id": "2", "name": "Sam", "admin": False}])
        self.assertEqual(self.one.refresh([PLEX]), {"asked": True})
        self.assertEqual(self.fetch.seen[-1][1], "/library/sections/all/refresh")
        self.assertEqual(self.one.sign_in_check([PLEX]), {"ok": True, "why": "", "name": "Den", "version": "1.41.3.9314"})
        self.assertEqual([x["title"] for x in self.one.playing([PLEX])], ["Dune", "Pilot"])
        self.assertEqual(len(self.one.recent([PLEX], limit=1)), 1)

    def test_odd_answers_do_not_break_it(self):
        self.answers["/status/sessions"] = {"MediaContainer": None}
        self.answers["/library/recentlyAdded"] = "nothing"
        self.answers["/"] = {}
        got = self.one.legacy_status([PLEX])
        self.assertEqual((got["version"], got["playing"], got["added"]), ("", [], []))

    def test_the_token_is_asked_for_in_words(self):
        k = self.one.keys_needed()[0]
        self.assertEqual(k["what"], "Plex token")
        self.assertIn("icon plex", k["kept"])


class Registry(unittest.TestCase):
    def test_the_three_are_known_and_named(self):
        self.assertEqual([(i, c.name) for i, c in mediaserver.ADAPTERS.items()], [("jellyfin", "Jellyfin"), ("emby", "Emby"), ("plex", "Plex")])

    def test_each_has_a_built_in_plug_in_record_that_passes_the_checks(self):
        from starboard import plugins, plugins_admin as pa
        for i in mediaserver.ADAPTERS:
            m = pa.builtins()[i]
            self.assertTrue(pa.is_media_server(m), i)
            self.assertEqual(plugins.check(m, builtin=True), [], i)

    def test_a_jellyfin_and_a_plex_saved_together_are_told_apart(self):
        both = [JF, PLEX, EMBY]
        self.assertEqual(mediaserver.Jellyfin().find_service(both)["id"], "jellyfin")
        self.assertEqual(plex.Plex().find_service(both)["id"], "plex")
        self.assertEqual(emby.Emby().find_service(both)["id"], "emby")


if __name__ == "__main__":
    unittest.main()
