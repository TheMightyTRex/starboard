"""Play in Jellyfin (DASH-480): the address for browsers, Jellyfin's ids kept in the Films index, and the Play data on
walls and item pages."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import jellyfin_play, library, services
from tests.test_library import REELIX, FakeReelix, film

JF = {"id": "jf1", "type": "jellyfin", "name": "Jellyfin", "url": "http://127.0.0.1:8096", "api_key": "k", "enabled": True}
A, B = "a" * 32, "b" * 32


class AddressTest(unittest.TestCase):
    def test_only_addresses_a_browser_can_open(self):
        for url in ("http://127.0.0.1:8096", "http://localhost:8096", "http://host.docker.internal:8096", "http://jellyfin:8096",
                    "http://0.0.0.0:8096", "http://[::1]:8096", "", "not an address"):
            self.assertFalse(jellyfin_play.for_browsers(url), url)
        for url in ("http://192.168.1.20:8096", "https://films.example.org", "http://trex-server:8096"):
            self.assertTrue(jellyfin_play.for_browsers(url), url)

    def test_the_address_for_browsers_never_the_one_starboard_uses(self):
        got = jellyfin_play.address([{**JF, "link": "http://192.168.1.20:8096/", "outside_link": "https://watch.example.org"}])
        self.assertEqual(got, {"app": "jf1", "home": "http://192.168.1.20:8096", "outside": "https://watch.example.org", "local": None})

    def test_a_local_only_address_gives_its_port_for_the_browsers_host(self):
        # As Install apps saves Jellyfin (http://127.0.0.1:8096, no browser address): the page puts the host it was
        # opened with in front of the port, as Starboard's other Open buttons do.
        self.assertEqual(jellyfin_play.address([JF]), {"app": "jf1", "home": "", "outside": "", "local": {"scheme": "http", "port": 8096, "path": ""}})
        self.assertEqual(jellyfin_play.address([{**JF, "url": "http://127.0.0.1:8096/jellyfin/"}])["local"]["path"], "/jellyfin")  # a base path is kept
        for url, port in (("http://localhost:8097", 8097), ("http://[::1]:8096", 8096), ("http://0.0.0.0:8096", 8096),
                          ("http://127.0.0.2", 80), ("https://127.0.0.1", 443)):
            self.assertEqual(jellyfin_play.address([{**JF, "url": url}])["local"]["port"], port, url)
        # A browser address that is itself local works the same way.
        got = jellyfin_play.address([{**JF, "url": "http://jellyfin:8096", "link": "http://127.0.0.1:8920"}])
        self.assertEqual((got["home"], got["local"]), ("", {"scheme": "http", "port": 8920, "path": ""}))
        # An outside address is kept beside it, for away from home.
        self.assertEqual(jellyfin_play.address([{**JF, "outside_link": "https://watch.example.org"}])["outside"], "https://watch.example.org")

    def test_no_address_can_be_made_so_the_page_says_where_to_add_one(self):
        # Jellyfin on another computer, or reached by a container's name, with no browser address saved.
        for svc in ({**JF, "url": "http://192.168.1.30:8096"}, {**JF, "url": "http://host.docker.internal:8096"},
                    {**JF, "url": "http://jellyfin:8096"}, {**JF, "link": "http://host.docker.internal:8096"}):
            self.assertEqual(jellyfin_play.address([svc]), {"app": "jf1", "home": "", "outside": "", "local": None}, svc)

    def test_no_jellyfin_no_play(self):
        self.assertIsNone(jellyfin_play.address([]))
        self.assertIsNone(jellyfin_play.address([{**JF, "api_key": ""}]))
        self.assertIsNone(jellyfin_play.address([{**JF, "enabled": False}]))

    def test_the_web_link_opens_the_item_page(self):
        self.assertEqual(jellyfin_play.web_link("http://192.168.1.20:8096/", A), f"http://192.168.1.20:8096/web/#/details?id={A}")


class FilmIdsTest(unittest.TestCase):
    def setUp(self):
        services.forget()
        self.dir = tempfile.TemporaryDirectory()
        self.data = self.dir.name
        self.asked = []

    def tearDown(self):
        self.dir.cleanup()

    def jellyfin(self, service, path, method="GET", body=None, timeout=120):
        self.asked.append(path)
        start = int(path.split("StartIndex=")[1].split("&")[0])
        everything = [{"Id": A, "ProviderIds": {"Tmdb": "101"}}, {"Id": B, "ProviderIds": {"Imdb": "tt0000002"}},
                      {"Id": "not-an-id", "ProviderIds": {"Tmdb": "103"}}]
        return {"Items": everything[start:start + 1000], "TotalRecordCount": len(everything)}

    def write_config(self, services_list):
        with open(os.path.join(self.data, "config.json"), "w", encoding="utf-8") as f:
            json.dump({"services": services_list}, f)

    def test_one_paged_list_matched_by_tmdb_then_imdb(self):
        self.write_config([JF])
        films = [{**film(1, "By TMDB"), "tmdb_id": 101}, {**film(2, "By IMDb"), "tmdb_id": 999, "imdb_id": "tt0000002"},
                 {**film(3, "Bad id"), "tmdb_id": 103}, {**film(4, "Not in Jellyfin", has_file=True), "tmdb_id": 104}]
        with mock.patch.object(services, "_api", FakeReelix(films=films)), mock.patch("starboard.migrate._mb", side_effect=self.jellyfin):
            library.refresh(self.data, REELIX, "films")
            index = library.load(self.data, REELIX, "films")
        self.assertEqual(len(self.asked), 1)  # one list for the whole tab, not one question per film
        self.assertIn("IncludeItemTypes=Movie", self.asked[0])
        self.assertIn("EnableImages=false", self.asked[0])
        self.assertEqual(index["v"], library.INDEX_VERSION)
        jf = {e["t"]: e.get("jf") for e in index["items"]}
        self.assertEqual(jf, {"By TMDB": A, "By IMDb": B, "Bad id": None, "Not in Jellyfin": None})
        cards = {c["title"]: c for c in library.wall(index, "films")["items"]}
        self.assertEqual(cards["By TMDB"]["jf"], A)
        self.assertNotIn("jf", cards["Not in Jellyfin"])  # nothing sent for a film Jellyfin does not have

    def test_without_jellyfin_or_when_it_fails_the_index_is_still_written(self):
        with mock.patch.object(services, "_api", FakeReelix(films=[{**film(1, "Alone"), "tmdb_id": 101}])):
            self.assertEqual(library.refresh(self.data, REELIX, "films"), 1)  # no Jellyfin app: nothing asked
            self.write_config([JF])
            with mock.patch("starboard.migrate._mb", side_effect=services.ServiceError("Cannot reach Jellyfin")):
                self.assertEqual(library.refresh(self.data, REELIX, "films"), 1)
            index = library.load(self.data, REELIX, "films")
        self.assertNotIn("jf", index["items"][0])

    def test_other_tabs_never_ask_jellyfin(self):
        self.write_config([JF])
        with mock.patch.object(services, "_api", FakeReelix(series=[])), mock.patch("starboard.migrate._mb") as mb:
            library.refresh(self.data, REELIX, "tv")
        mb.assert_not_called()


class ItemTest(unittest.TestCase):
    """The item page: the film's Jellyfin id from the watched lookup it does already, and the address."""

    def setUp(self):
        services.forget()
        self.cfg = mock.Mock(data={"services": [{**JF, "link": "http://192.168.1.20:8096"}], "extras": {}})

    def reelix(self, service, path, params=None, method="GET", body=None, timeout=None):
        if path == "/movies/7":
            return {"id": 7, "title": "The Lost Valley", "tmdb_id": 101, "has_file": True, "status": "released", "monitored": True}
        if path == "/series/3":
            return {"id": 3, "title": "Harbour", "tmdb_id": 55, "statistics": {"episode_file_count": 2, "episode_count": 3}}
        if path == "/series/3/episodes":
            return [{"id": 31, "season_number": 1, "episode_number": 1, "title": "One", "has_file": True, "air_date": "2020-01-01"},
                    {"id": 32, "season_number": 1, "episode_number": 2, "title": "Two", "has_file": True, "air_date": "2020-01-08"},
                    {"id": 33, "season_number": 1, "episode_number": 3, "title": "Three", "has_file": False, "air_date": "2020-01-15"}]
        if path in ("/queue", "/collections"):
            return []
        raise AssertionError(path)

    def test_a_film_and_its_episodes_carry_their_jellyfin_ids(self):
        with mock.patch.object(services, "_api", side_effect=self.reelix), \
                mock.patch("starboard.watched.film", return_value={"id": A, "watched": False, "user": "admin"}), \
                mock.patch("starboard.watched.series", return_value={"id": B, "user": "admin",
                                                                       "episodes": {(1, 1): {"id": A, "watched": True}}}):
            f = library.item("/nowhere", REELIX, "films", 7, self.cfg)
            s = library.item("/nowhere", REELIX, "tv", 3, self.cfg)
        self.assertEqual(f["jf"], A)
        self.assertEqual(f["play"], {"app": "jf1", "home": "http://192.168.1.20:8096", "outside": "", "local": None})
        rows = s["lists"][0]["rows"]
        self.assertEqual([(r["jf"], r["has_file"]) for r in rows], [(A, True), (None, True), (None, False)])  # Two: not in Jellyfin yet
        self.assertEqual(s["play"]["home"], "http://192.168.1.20:8096")

    def test_not_in_jellyfin_and_no_jellyfin(self):
        with mock.patch.object(services, "_api", side_effect=self.reelix), mock.patch("starboard.watched.film", return_value=None):
            self.assertEqual(library.item("/nowhere", REELIX, "films", 7, self.cfg)["jf"], "")
            self.cfg.data["services"] = []
            self.assertIsNone(library.item("/nowhere", REELIX, "films", 7, self.cfg)["play"])


if __name__ == "__main__":
    unittest.main()
