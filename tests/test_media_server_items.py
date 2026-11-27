"""Play and Watched for Emby and Plex (DASH-566): links, the film list, watched state and marking, answered from recorded
answers of each server's documented API. Nothing real is asked: neither server was available to try."""
import unittest
from unittest import mock

from starboard import jellyfin_play, library, mediaserver, services, watched
from starboard.mediaservers import emby, plex
from tests.test_media_servers_other import EMBY, PLEX, JF, Fetch


class Cfg:
    def __init__(self, data):
        self.data = data


def cfg_for(server, svc):
    return Cfg({"services": [svc, JF], "extras": {"media_server": server}})


EMBY_TABLE = {
    "/emby/System/Info/Public": {"Id": "abc123", "Version": "4.8.10.0"},
    "/emby/Users": [{"Id": "u9", "Name": "Alex"}, {"Id": "u1", "Name": "Sam", "Policy": {"IsAdministrator": True}}],
    "/emby/Items": {"Items": [{"Id": "100", "ProviderIds": {"Tmdb": "603", "Imdb": "tt0133093"}}, {"Id": "bad id", "ProviderIds": {"Tmdb": "1"}}, "junk"], "TotalRecordCount": 3},
    "/emby/Users/u1/Items": {"Items": [{"Id": "100", "ProviderIds": {"Tmdb": "603"}, "UserData": {"Played": True}},
                                       {"Id": "101", "ProviderIds": {"Tmdb": "604"}}]},
    "/emby/Shows/55/Episodes": {"Items": [{"Id": "e1", "ParentIndexNumber": 1, "IndexNumber": 2, "UserData": {"Played": True}},
                                          {"Id": "e2", "ParentIndexNumber": 1, "IndexNumber": 3}, {"Id": "x"}]},
    "/emby/Users/u1/PlayedItems/e1": "",
}
PLEX_TABLE = {
    "/identity": {"MediaContainer": {"machineIdentifier": "0123456789abcdef", "version": "1.41.3.9314-a0bfb8370"}},
    "/": {"MediaContainer": {"friendlyName": "Den", "myPlexUsername": "owner@example.test"}},
    "/library/sections": {"MediaContainer": {"Directory": [{"key": "1", "title": "Films", "type": "movie"}, {"key": "2", "title": "Series", "type": "show"}]}},
    "/library/sections/1/all": {"MediaContainer": {"totalSize": 2, "Metadata": [
        {"ratingKey": "301", "Guid": [{"id": "tmdb://603"}, {"id": "imdb://tt0133093"}, {"id": "tvdb://5"}]}, {"ratingKey": "x", "Guid": []}]}},
    "/library/sections/2/all": {"MediaContainer": {"totalSize": 1, "Metadata": [{"ratingKey": "400", "Guid": [{"id": "tmdb://1396"}]}]}},
    "/library/metadata/301": {"MediaContainer": {"Metadata": [{"ratingKey": "301", "viewCount": 2}]}},
    "/library/metadata/400/allLeaves": {"MediaContainer": {"Metadata": [
        {"ratingKey": "401", "parentIndex": 1, "index": 1, "viewCount": 1}, {"ratingKey": "402", "parentIndex": 1, "index": 2}, {"ratingKey": "403"}]}},
    "/:/scrobble": "", "/:/unscrobble": "",
}


class EmbyItems(unittest.TestCase):
    def setUp(self):
        self.fetch = Fetch(EMBY_TABLE)
        p = mock.patch.object(services, "_fetch", side_effect=self.fetch)
        p.start()
        self.addCleanup(p.stop)
        self.one, self.list = emby.Emby(), [EMBY]

    def test_the_link_needs_the_server_id_and_a_plain_item_id(self):
        self.assertEqual(self.one.play_info(self.list), {"server_id": "abc123"})
        self.assertNotIn("made-up-emby-key", self.fetch.seen[-1][3])
        self.assertEqual(self.one.play_link("http://emby.home/", "100", "abc123"), "http://emby.home/web/index.html#!/item?id=100&serverId=abc123")
        for bad in (("../x", "abc"), ("100", ""), ("a b", "abc")):
            self.assertEqual(self.one.play_link("http://emby.home", *bad), "")

    def test_films_are_matched_by_tmdb_and_imdb_and_bad_ids_are_left_out(self):
        self.assertEqual(self.one.film_ids(self.list), {("tmdb", "603"): "100", ("imdb", "tt0133093"): "100"})

    def test_watched_is_the_first_admins_unless_a_name_is_given(self):
        self.assertEqual(self.one.watched_user(self.list), ("u1", "Sam"))
        self.assertEqual(self.one.watched_user(self.list, "Alex"), ("u9", "Alex"))
        who = ("u1", "Sam")
        self.assertEqual(self.one.watched_film(self.list, who, "603"), {"id": "100", "watched": True, "user": "Sam"})
        self.assertIsNone(self.one.watched_film(self.list, who, "999"))

    def test_a_series_gives_its_episodes_and_marking_uses_the_right_verbs(self):
        EMBY_TABLE["/emby/Users/u1/Items"]["Items"].append({"Id": "55", "ProviderIds": {"Tmdb": "1396"}})
        self.addCleanup(EMBY_TABLE["/emby/Users/u1/Items"]["Items"].pop)
        got = self.one.watched_series(self.list, ("u1", "Sam"), "1396")
        self.assertEqual(got["episodes"], {(1, 2): {"id": "e1", "watched": True}, (1, 3): {"id": "e2", "watched": False}})
        self.assertEqual(self.one.mark(self.list, ("u1", "Sam"), ["e1"], True), 1)
        self.assertEqual(self.one.mark(self.list, ("u1", "Sam"), ["e1"], False), 1)
        self.assertEqual([m for m, p, *_ in self.fetch.seen if "PlayedItems" in p], ["POST", "DELETE"])
        with self.assertRaises(ValueError):
            self.one.mark(self.list, ("u1", "Sam"), ["../etc"], True)


class PlexItems(unittest.TestCase):
    def setUp(self):
        services.forget()
        self.fetch = Fetch(PLEX_TABLE)
        p = mock.patch.object(services, "_fetch", side_effect=self.fetch)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(services.forget)
        self.one, self.list = plex.Plex(), [PLEX]

    def test_the_link_opens_the_item_in_plexs_web_app(self):
        self.assertEqual(self.one.play_info(self.list), {"server_id": "0123456789abcdef"})
        self.assertEqual(self.fetch.seen[-1][2].get("X-plex-token", ""), "", "the public identity is asked without the token")
        self.assertEqual(self.one.play_link("http://plex.home", "301", "0123456789abcdef"),
                         "http://plex.home/web/index.html#!/server/0123456789abcdef/details?key=%2Flibrary%2Fmetadata%2F301")
        for bad in (("301", ""), ("30/1", "0123456789abcdef"), ("301", "not hex!")):
            self.assertEqual(self.one.play_link("http://plex.home", *bad), "")

    def test_films_come_from_one_read_of_each_film_section_and_are_kept(self):
        want = {("tmdb", "603"): "301", ("imdb", "tt0133093"): "301"}
        self.assertEqual(self.one.film_ids(self.list), want)
        n = len(self.fetch.seen)
        self.assertEqual(self.one.film_ids(self.list), want)
        self.assertEqual(len(self.fetch.seen), n, "the second look asks nothing")

    def test_watched_is_the_owners_and_comes_from_the_view_count(self):
        who = self.one.watched_user(self.list)
        self.assertEqual(who, ("owner", "owner@example.test"))
        self.assertEqual(self.one.watched_film(self.list, who, "603"), {"id": "301", "watched": True, "user": "owner@example.test"})
        self.assertIsNone(self.one.watched_film(self.list, who, "1"))
        got = self.one.watched_series(self.list, who, "1396")
        self.assertEqual(got["episodes"], {(1, 1): {"id": "401", "watched": True}, (1, 2): {"id": "402", "watched": False}})

    def test_marking_uses_scrobble_and_unscrobble_and_refuses_odd_ids(self):
        self.assertEqual(self.one.mark(self.list, ("owner", "x"), ["301"], True), 1)
        self.assertEqual(self.one.mark(self.list, ("owner", "x"), ["301"], False), 1)
        self.assertEqual([p for m, p, *_ in self.fetch.seen if "scrobble" in p], ["/:/scrobble", "/:/unscrobble"])
        with self.assertRaises(ValueError):
            self.one.mark(self.list, ("owner", "x"), ["1;2"], True)


class Routing(unittest.TestCase):
    """watched.py, the Play address and the films index follow the media server in use."""

    def setUp(self):
        services.forget()
        self.addCleanup(services.forget)

    def test_watched_asks_the_server_in_use(self):
        with mock.patch.object(services, "_fetch", side_effect=Fetch({**EMBY_TABLE})):
            self.assertEqual(watched.film(cfg_for("emby", EMBY), "603")["id"], "100")
        with mock.patch.object(services, "_fetch", side_effect=Fetch({**PLEX_TABLE})):
            self.assertEqual(watched.film(cfg_for("plex", PLEX), "603")["id"], "301")
            self.assertEqual(watched.mark(cfg_for("plex", PLEX), ["301"], True), 1)

    def test_no_media_server_draws_nothing(self):
        c = cfg_for("", PLEX)
        with mock.patch.object(services, "_fetch", side_effect=AssertionError("nothing is asked")):
            self.assertIsNone(watched.film(c, "603"))
            self.assertIsNone(watched.series(c, "1"))
            self.assertIsNone(jellyfin_play.address_for(c.data))
            with self.assertRaises(ValueError):
                watched.mark(c, ["301"], True)

    def test_a_server_that_does_not_answer_draws_nothing_instead_of_failing(self):
        with mock.patch.object(services, "_fetch", side_effect=services.ServiceError("Cannot reach Plex")):
            self.assertIsNone(watched.film(cfg_for("plex", PLEX), "603"))

    def test_the_play_address_names_the_server_and_carries_its_id(self):
        svc = {**PLEX, "link": "http://plex.home:32400"}
        with mock.patch.object(services, "_fetch", side_effect=Fetch({**PLEX_TABLE})):
            got = jellyfin_play.address_for(cfg_for("plex", svc).data)
        self.assertEqual((got["kind"], got["name"], got["server_id"], got["home"]), ("plex", "Plex", "0123456789abcdef", "http://plex.home:32400"))

    def test_the_films_index_leaves_out_ids_from_another_server_and_builds_again(self):
        index = {"v": library.INDEX_VERSION, "ms": "jellyfin", "items": [{"i": 1, "jf": "abc"}, {"i": 2}]}
        with mock.patch.object(library, "_background") as again:
            same = library._for_server(index, {"extras": {}}, "/d", {}, "films")
            self.assertEqual(same, index)
            again.assert_not_called()
            got = library._for_server(index, {"extras": {"media_server": "plex"}}, "/d", {}, "films")
            self.assertEqual(got["items"], [{"i": 1}, {"i": 2}])
            again.assert_called_once()

    def test_the_index_is_read_from_the_server_in_use(self):
        import json, os, tempfile
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "config.json"), "w") as f:
                json.dump({"services": [PLEX], "extras": {"media_server": "plex"}}, f)
            with mock.patch.object(services, "_fetch", side_effect=Fetch({**PLEX_TABLE})):
                self.assertEqual(jellyfin_play.index_ids(d), ("plex", {("tmdb", "603"): "301", ("imdb", "tt0133093"): "301"}))


if __name__ == "__main__":
    unittest.main()
