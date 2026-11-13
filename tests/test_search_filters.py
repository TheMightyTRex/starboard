"""Search's filters (DASH-301): the facts kept with each Library entry, what Search sends with them, what is
downloading, Reelix's lookups, and the filters remembered for the account."""

import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import library, services

from tests.test_library import REELIX, FakeReelix, film


class FactsTest(unittest.TestCase):
    def setUp(self):
        services.forget()
        self.dir = tempfile.TemporaryDirectory()
        self.data = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def test_films_keep_genre_language_rating_followed_and_below_the_quality_wanted(self):
        a = dict(film(1, "Kept"), genres=["Drama", "Comedy", "War", "History", "Music"], original_language="eng",
                 certification="15", movie_file={"cutoff_met": False})
        b = dict(film(2, "Not followed", has_file=False), monitored=False, original_language="nonsense!")
        c = film(3, "Soon", has_file=False, status="announced", year=2999)
        with mock.patch.object(services, "_api", FakeReelix(films=[a, b, c])):
            library.refresh(self.data, REELIX, "films")
        with open(os.path.join(self.data, "library", "films.json")) as f:
            index = json.load(f)
        self.assertEqual(index["v"], library.INDEX_VERSION)
        got = {e["t"]: e for e in index["items"]}
        self.assertEqual(got["Kept"]["ge"], ["Drama", "Comedy", "War", "History"])  # at most four
        self.assertEqual((got["Kept"]["la"], got["Kept"]["ce"], got["Kept"]["fo"], got["Kept"]["cu"]), ("en", "15", 1, 1))
        self.assertNotIn("la", got["Not followed"])
        self.assertEqual(got["Not followed"]["fo"], 0)
        self.assertEqual((got["Soon"]["rl"], got["Kept"]["rl"]), ("coming", "released"))

    def test_series_below_the_quality_wanted_comes_from_reelix_while_building(self):
        series = [{"id": 1, "title": "One", "status": "continuing", "statistics": {"episode_file_count": 1, "episode_count": 2}},
                  {"id": 2, "title": "Two", "status": "upcoming", "statistics": {"episode_file_count": 0, "episode_count": 0}}]
        fake = FakeReelix(series=series)
        fake.lists["/wanted/cutoff"] = [{"series_id": 1}, {"series_id": 1}]
        with mock.patch.object(services, "_api", fake):
            library.refresh(self.data, REELIX, "tv")
            index = library.load(self.data, REELIX, "tv")
        got = {e["t"]: e for e in index["items"]}
        self.assertEqual(got["One"].get("cu"), 1)
        self.assertNotIn("cu", got["Two"])
        self.assertEqual(got["Two"]["rl"], "coming")
        self.assertIn(("/wanted/cutoff", {"kind": "episode", "page": 1, "page_size": library.PAGE}, "GET", None), fake.calls)

    def test_an_older_reelix_without_cutoff_still_builds(self):
        series = [{"id": 1, "title": "One", "status": "ended", "statistics": {"episode_file_count": 2, "episode_count": 2}}]
        with mock.patch.object(services, "_api", FakeReelix(series=series)):  # no /wanted/cutoff: it raises
            self.assertEqual(library.refresh(self.data, REELIX, "tv"), 1)

    def test_radio_source_and_languages(self):
        self.assertEqual(library.radio_source("bbc"), "BBC Sounds")
        self.assertEqual(library.radio_source("podcastindex"), "Podcasts")
        self.assertEqual(library.radio_source("", podcast=True), "Podcasts")
        self.assertEqual(library.radio_source("other", station="Times Radio"), "Times Radio")
        self.assertEqual([library.lang(x) for x in ("en", "ENG", "fre", "pt-BR", "", "1; drop")], ["en", "en", "fr", "pt", "", ""])

    def test_search_sends_the_facts_and_what_is_downloading(self):
        films = [dict(film(1, "Harbour One"), genres=["Drama"], movie_file={"cutoff_met": False}),
                 film(2, "Harbour Two", has_file=False)]
        with mock.patch.object(services, "_api", FakeReelix(films=films)):
            library.refresh(self.data, REELIX, "films")

        def queue(service, path, params=None, method="GET", body=None, timeout=None):
            self.assertEqual(path, "/queue")
            return {"items": [{"media": {"kind": "movie", "id": 2}}, {"book": {"id": 9}}]}
        with mock.patch.object(services, "_api", queue):
            found = library.search_library(self.data, "harbour", reelix=REELIX)
        cards = {c["title"]: c["fx"] for c in found[0]["items"]}
        self.assertEqual(cards["Harbour One"]["s"], ["have", "below"])
        self.assertEqual(cards["Harbour One"]["g"], ["Drama"])
        self.assertEqual(cards["Harbour Two"]["s"], ["missing", "downloading"])

    def test_search_without_the_queue_still_answers(self):
        with mock.patch.object(services, "_api", FakeReelix(films=[film(1, "Harbour")])):
            library.refresh(self.data, REELIX, "films")
        with mock.patch.object(services, "_api", side_effect=services.ServiceError("down")):
            found = library.search_library(self.data, "harbour", reelix=REELIX)
        self.assertEqual(found[0]["items"][0]["fx"]["s"], ["have"])

    def test_lookups_say_the_year_and_coming_soon(self):
        def answer(service, path, params=None, method="GET", body=None, timeout=None):
            if path == "/movies/lookup":
                return [{"tmdb_id": 1, "title": "Old", "year": 1999}, {"tmdb_id": 2, "title": "New", "year": 2999}]
            return [{"provider": "bbc", "external_id": "b1", "title": "A show"}]
        with mock.patch.object(services, "_api", answer):
            films = library.lookup(REELIX, "something", "films")["groups"][0]["items"]
            radio = library.lookup(REELIX, "something", "radio")["groups"][0]["items"]
        self.assertEqual([(r["fx"]["y"], r["fx"]["r"]) for r in films], [(1999, "released"), (2999, "coming")])
        self.assertEqual(radio[0]["fx"]["so"], "BBC Sounds")


class RememberedTest(unittest.TestCase):
    def test_only_known_filters_are_kept_and_they_come_back(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(library.search_filters(d), {})
            kept = library.save_search_filters(d, {"where": "in", "kind": "nonsense", "status": ["have", "x", "below"],
                                                   "genre": " Drama ", "language": "a\nb", "release": "coming", "followed": "maybe",
                                                   "more": True, "other": "x"})
            self.assertEqual(kept, {"where": "in", "genre": "Drama", "status": ["have", "below"], "release": "coming", "more": True})
            self.assertEqual(library.search_filters(d), kept)
            self.assertEqual(oct(os.stat(os.path.join(d, "library", "search-filters.json")).st_mode & 0o777), "0o600")
            with self.assertRaises(ValueError):
                library.save_search_filters(d, ["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()


class NarratorsTest(unittest.TestCase):
    """Narrator pages (DASH-261): narrators from Reelix's audiobook file, their groups, their page and the summary's links."""

    def test_names_are_split_once_each(self):
        self.assertEqual(library.narrators("Sam Oduya, Priya Lane and sam oduya & Hugh Calder"), ["Sam Oduya", "Priya Lane", "Hugh Calder"])
        self.assertEqual(library.narrators("Andrew Anderson"), ["Andrew Anderson"])
        self.assertEqual(library.narrators(None), [])

    def test_groups_and_a_narrators_page(self):
        books = [{"id": 1, "title": "One", "monitored_audiobook": True, "audiobook_file": {"id": 1, "narrator": "Sam Oduya, Priya Lane"}},
                 {"id": 2, "title": "Two", "monitored_audiobook": True, "audiobook_file": {"id": 2, "narrator": "Sam Oduya"}},
                 {"id": 3, "title": "Three", "monitored_ebook": True, "ebook_file": {"id": 3}}]
        with tempfile.TemporaryDirectory() as d:
            services.forget()
            with mock.patch.object(services, "_api", FakeReelix(books=books)):
                library.refresh(d, REELIX, "audiobooks")
                library.refresh(d, REELIX, "books")
                audio = library.load(d, REELIX, "audiobooks")
                ebooks = library.load(d, REELIX, "books")
        self.assertEqual([(g["name"], g["count"]) for g in library.groups(audio, "audiobooks", "narrators")], [("Priya Lane", 1), ("Sam Oduya", 2)])
        self.assertEqual([c["title"] for c in library.wall(audio, "audiobooks", group="sam oduya", by="narrators")["items"]], ["One", "Two"])
        self.assertNotIn("na", ebooks["items"][0])
        self.assertEqual(library._by({"by": "narrators"}, "audiobooks"), "narrators")
        self.assertEqual(library._by({"by": "narrators"}, "films"), "")

    def test_the_summary_links_each_narrator(self):
        fact = library._fact("Narrated by", "Sam Oduya, Priya Lane")
        self.assertEqual(fact["links"][1], {"text": "Priya Lane", "href": "/library-audiobooks.html?group=Priya%20Lane&by=narrators"})
        self.assertNotIn("links", library._fact("Author", "Someone"))
