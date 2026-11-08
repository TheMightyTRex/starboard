"""The Library from Reelix and Search (DASH-163, DASH-162): the slim index, walls, the A to Z list, posters and views."""

import json
import os
import stat
import tempfile
import time
import unittest
from unittest import mock

from starboard import library, services

REELIX = {"id": "reelix", "name": "Reelix", "type": "link", "url": "http://reelix:7700/api/v1", "api_key": "k", "link": "http://reelix:7700"}


def film(i, title, year=2020, has_file=True, status="released", collection=None, added="2026-01-01T00:00:00Z"):
    return {"id": i, "title": title, "sort_title": "", "year": year, "status": status, "has_file": has_file, "monitored": True,
            "images": {"poster": f"https://image.tmdb.org/t/p/w500/p{i}.jpg"}, "added": added,
            "collection": {"id": 1, "title": collection} if collection else None}


class FakeReelix:
    """Reelix's list answers, paged as Reelix pages them."""

    def __init__(self, films=(), series=(), books=(), artists=(), shows=(), radio_missing=False):
        self.lists = {"/movies": list(films), "/series": list(series), "/books": list(books), "/artists": list(artists),
                      "/radio/shows": list(shows)}
        self.radio_missing = radio_missing
        self.calls = []

    def __call__(self, service, path, params=None, method="GET", body=None, timeout=None):
        self.calls.append((path, dict(params or {}), method, body))
        if path == "/radio/shows" and self.radio_missing:
            err = services.ServiceError("Reelix answered with error 404")
            err.status = 404
            raise err
        if path in self.lists and method == "GET":
            items = self.lists[path]
            size, page = params["page_size"], params["page"]
            return {"items": items[(page - 1) * size: page * size], "total": len(items), "page": page, "page_size": size}
        if method == "POST":
            return {"title": "Added thing", "name": "Added thing"}
        raise AssertionError(path)


class LettersTest(unittest.TestCase):
    def test_sort_title_drops_articles_and_folds_accents(self):
        self.assertEqual(library.sort_key("The Expanse"), "expanse")
        self.assertEqual(library.sort_key("Émile"), "emile")
        self.assertEqual(library.sort_key("An Apple"), "apple")
        self.assertEqual(library.sort_key('"Quoted"'), 'quoted"')
        self.assertEqual(library.letter(library.sort_key("24 Hours")), "#")
        self.assertEqual(library.letter(library.sort_key("Über")), "U")

    def test_reelix_sort_title_wins_when_given(self):
        self.assertEqual(library.sort_key("Le Film", "film, le"), "film, le")


class PosterTest(unittest.TestCase):
    def test_small_sizes(self):
        self.assertEqual(library.small("https://image.tmdb.org/t/p/w500/a.jpg"), "https://image.tmdb.org/t/p/w185/a.jpg")
        self.assertEqual(library.small("https://image.tmdb.org/t/p/w500/a.jpg", "page"), "https://image.tmdb.org/t/p/w342/a.jpg")
        self.assertEqual(library.small("https://covers.openlibrary.org/b/id/1-L.jpg"), "https://covers.openlibrary.org/b/id/1-M.jpg")
        self.assertEqual(library.small(None), "")

    def test_only_image_sites_or_reelix_itself(self):
        self.assertTrue(library.poster_allowed("https://image.tmdb.org/t/p/w185/a.jpg"))
        self.assertTrue(library.poster_allowed("https://coverartarchive.org/release-group/x/front-250"))
        self.assertFalse(library.poster_allowed("http://image.tmdb.org/t/p/w185/a.jpg"))  # never plain http to a site
        self.assertFalse(library.poster_allowed("https://evil.example/a.jpg"))
        self.assertFalse(library.poster_allowed("https://user:pw@image.tmdb.org/a.jpg"))
        self.assertFalse(library.poster_allowed("http://192.168.1.2:8080/a.jpg"))
        self.assertTrue(library.poster_allowed("http://reelix:7700/api/v1/radio/shows/1/artwork", "http://reelix:7700"))
        self.assertFalse(library.poster_allowed("http://reelix:7701/x", "http://reelix:7700"))

    def test_no_picture_is_remembered_for_a_day(self):
        with tempfile.TemporaryDirectory() as d:
            calls = []

            def fail(req, timeout=None):
                calls.append(req.full_url)
                raise library.urllib.error.HTTPError(req.full_url, 404, "Not found", {}, None)

            with mock.patch.object(library._image_opener, "open", fail):
                self.assertIsNone(library.poster(d, "https://image.tmdb.org/t/p/w500/a.jpg"))
                self.assertIsNone(library.poster(d, "https://image.tmdb.org/t/p/w500/a.jpg"))
            self.assertEqual(calls, ["https://image.tmdb.org/t/p/w185/a.jpg"])

    def test_a_picture_is_kept_and_served_from_disk(self):
        with tempfile.TemporaryDirectory() as d:
            class Answer:
                headers = {"Content-Type": "image/jpeg"}

                def read(self, n):
                    return b"\xff\xd8jpeg"

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

            with mock.patch.object(library._image_opener, "open", lambda req, timeout=None: Answer()) as _:
                first = library.poster(d, "https://image.tmdb.org/t/p/w500/a.jpg")
            with mock.patch.object(library._image_opener, "open", side_effect=AssertionError("asked again")):
                again = library.poster(d, "https://image.tmdb.org/t/p/w500/a.jpg")
            self.assertEqual(first, (b"\xff\xd8jpeg", "image/jpeg"))
            self.assertEqual(again, first)
            folder = os.path.join(d, "posters", "library")
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(folder, os.listdir(folder)[0])).st_mode), 0o600)


class IndexTest(unittest.TestCase):
    def setUp(self):
        services.forget()
        self.dir = tempfile.TemporaryDirectory()
        self.data = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def test_films_are_read_in_pages_and_kept_slim_on_disk(self):
        films = [film(i, f"Film {i:04d}") for i in range(1, 601)] + [film(601, "The Expanse Film"), film(602, "24 Frames")]
        fake = FakeReelix(films=films)
        with mock.patch.object(services, "_api", fake):
            count = library.refresh(self.data, REELIX, "films")
        self.assertEqual(count, 602)
        pages = [c for c in fake.calls if c[0] == "/movies"]
        self.assertEqual([c[1]["page"] for c in pages], [1, 2, 3])
        self.assertTrue(all(c[1]["page_size"] == library.PAGE for c in pages))
        path = os.path.join(self.data, "library", "films.json")
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        with open(path) as f:
            index = json.load(f)
        self.assertEqual(index["items"][0]["t"], "24 Frames")  # # first, as the letter row
        self.assertEqual(set(index["items"][0]), {"i", "t", "s", "l", "y", "p", "w", "c", "a", "f", "m", "g"})
        expanse = next(e for e in index["items"] if e["i"] == 601)
        self.assertEqual((expanse["l"], expanse["s"]), ("E", "expanse film"))
        self.assertLess(os.path.getsize(path) / 602, 300)  # bytes per film: the index stays small

    def test_status_words_and_chips_for_films(self):
        fake = FakeReelix(films=[film(1, "Have"), film(2, "Missing", has_file=False), film(3, "Soon", has_file=False, status="announced")])
        with mock.patch.object(services, "_api", fake):
            library.refresh(self.data, REELIX, "films")
            out = library.wall(library.load(self.data, REELIX, "films"), "films")
        words = {c["title"]: c["status"] for c in out["items"]}
        self.assertEqual(words, {"Have": "In library", "Missing": "Wanted", "Soon": "Not released"})
        self.assertEqual({c["key"]: c["count"] for c in out["chips"]}, {"released": 2, "coming": 1, "missing": 1})

    def test_books_and_audiobooks_are_split_from_one_list(self):
        books = [{"id": 1, "title": "Both", "monitored_ebook": True, "monitored_audiobook": True, "ebook_file": {"id": 1},
                  "audiobook_file": None, "author_name": "A. Writer", "series": [{"id": 4, "title": "Saga", "position": "1"}]},
                 {"id": 2, "title": "Only listening", "monitored_ebook": False, "monitored_audiobook": True, "audiobook_file": {"id": 2}},
                 {"id": 3, "title": "Later", "monitored_ebook": True, "release_date": "2999-01-01"}]
        fake = FakeReelix(books=books)
        with mock.patch.object(services, "_api", fake):
            library.refresh(self.data, REELIX, "books")
            library.refresh(self.data, REELIX, "audiobooks")
            ebooks = library.wall(library.load(self.data, REELIX, "books"), "books")
            audio = library.wall(library.load(self.data, REELIX, "audiobooks"), "audiobooks")
            authors = library.groups(library.load(self.data, REELIX, "books"), "books", "authors")
        self.assertEqual({c["title"]: c["status"] for c in ebooks["items"]}, {"Both": "In library", "Later": "Not released"})
        self.assertEqual({c["title"]: c["status"] for c in audio["items"]}, {"Both": "Wanted", "Only listening": "In library"})
        self.assertEqual([g["name"] for g in authors], ["A. Writer"])

    def test_series_count_and_radio_without_radio(self):
        series = [{"id": 1, "title": "Show", "status": "continuing", "network": "BBC One", "year": 2020,
                   "statistics": {"episode_file_count": 18, "episode_count": 24}}]
        fake = FakeReelix(series=series, radio_missing=True)
        with mock.patch.object(services, "_api", fake):
            library.refresh(self.data, REELIX, "tv")
            self.assertEqual(library.refresh(self.data, REELIX, "radio"), 0)  # a Reelix without radio: an empty tab
            card = library.wall(library.load(self.data, REELIX, "tv"), "tv")["items"][0]
        self.assertEqual((card["count"], card["status"], card["meta"]), ("18 of 24 episodes", "Partly in library", "BBC One · 2020 to now"))

    def test_wall_search_sort_letters_and_jump(self):
        films = [film(i, t, year=y, added=f"2026-0{m}-01T00:00:00Z") for i, (t, y, m) in enumerate(
            [("Apple", 2001, 1), ("Banana", 1999, 3), ("Cherry", 2010, 2), ("The Date", 2005, 4), ("1984", 1984, 5)], 1)]
        with mock.patch.object(services, "_api", FakeReelix(films=films)):
            library.refresh(self.data, REELIX, "films")
        index = library.load(self.data, REELIX, "films")
        out = library.wall(index, "films")
        self.assertEqual(out["letters"], ["#", "A", "B", "C", "D"])
        self.assertEqual([c["title"] for c in out["items"]], ["1984", "Apple", "Banana", "Cherry", "The Date"])
        self.assertEqual([c["title"] for c in library.wall(index, "films", sort="added")["items"]][0], "1984")
        self.assertEqual([c["title"] for c in library.wall(index, "films", sort="year")["items"]][0], "Cherry")
        self.assertEqual(library.wall(index, "films", sort="year")["letters"], [])
        self.assertEqual([c["title"] for c in library.wall(index, "films", q="dat")["items"]], ["The Date"])
        jump = library.wall(index, "films", until="C", limit=2)
        self.assertEqual((jump["offset"], [c["title"] for c in jump["items"]]), (3, ["Cherry", "The Date"]))
        page = library.wall(index, "films", offset=4, limit=40)
        self.assertEqual(([c["title"] for c in page["items"]], page["shown"], page["total"]), (["The Date"], 5, 5))

    def test_groups_and_a_wall_of_one_group(self):
        films = [film(1, "One", collection="The Saga"), film(2, "Two", collection="The Saga"), film(3, "Alone")]
        with mock.patch.object(services, "_api", FakeReelix(films=films)):
            library.refresh(self.data, REELIX, "films")
        index = library.load(self.data, REELIX, "films")
        self.assertEqual([(g["name"], g["count"], g["letter"]) for g in library.groups(index, "films")], [("The Saga", 2, "S")])
        self.assertEqual(library.wall(index, "films", group="the saga")["shown"], 2)

    def test_a_stale_index_is_refreshed_in_the_background_and_served_meanwhile(self):
        with mock.patch.object(services, "_api", FakeReelix(films=[film(1, "Old")])):
            library.refresh(self.data, REELIX, "films")
        path = os.path.join(self.data, "library", "films.json")
        old = time.time() - library.STALE - 10
        os.utime(path, (old, old))
        with mock.patch.object(library, "_background") as bg, mock.patch.object(services, "_api", side_effect=AssertionError):
            index = library.load(self.data, REELIX, "films")
        self.assertEqual(index["items"][0]["t"], "Old")
        bg.assert_called_once_with(self.data, REELIX, "films")

    def test_search_library_and_overview_read_only_the_files(self):
        with mock.patch.object(services, "_api", FakeReelix(films=[film(1, "Harbour Street"), film(2, "Other")])):
            library.refresh(self.data, REELIX, "films")
        with mock.patch.object(services, "_api", side_effect=AssertionError("no Reelix call")):
            found = library.search_library(self.data, "harbour")
            start = library.overview(self.data)
        self.assertEqual([(g["tab"], g["count"], g["items"][0]["title"]) for g in found], [("films", 1, "Harbour Street")])
        films = next(t for t in start["tabs"] if t["tab"] == "films")
        self.assertEqual(films["count"], 2)
        self.assertIsNone(next(t for t in start["tabs"] if t["tab"] == "tv")["count"])


class AddTest(unittest.TestCase):
    def setUp(self):
        services.forget()

    def test_add_film_sends_only_what_starboard_builds(self):
        fake = FakeReelix()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(library, "_background"), mock.patch.object(services, "_api", fake):
            out = library.add(d, REELIX, "films", "tmdb:603", {"profile_id": 2, "folder_id": 9, "search": False, "extra": "ignored"})
        path, _, method, body = fake.calls[-1]
        self.assertEqual((path, method), ("/movies", "POST"))
        self.assertEqual(body, {"tmdb_id": 603, "quality_profile_id": 2, "root_folder_id": 9, "monitor": "movie_only",
                                "minimum_availability": "released", "tags": [], "search_on_add": False})
        self.assertEqual(out["tab"], "films")

    def test_follow_radio_and_refuse_bad_keys(self):
        fake = FakeReelix()
        with tempfile.TemporaryDirectory() as d, mock.patch.object(library, "_background"), mock.patch.object(services, "_api", fake):
            library.add(d, REELIX, "radio", "radio:bbc:b006qykl", {"follow": "from_now_on"})
            self.assertEqual(fake.calls[-1][3], {"provider": "bbc", "external_id": "b006qykl", "follow": "from_now_on", "monitored": True, "tags": []})
            for kind, key in (("films", "tmdb:abc"), ("books", "olw:not-an-id"), ("music", "mb:x"), ("radio", "radio:BAD provider:x"), ("tv", "imdb:tt1")):
                with self.assertRaises((ValueError, services.ServiceError)):
                    library.add(d, REELIX, kind, key, {"profile_id": 1, "folder_id": 1})


class ViewsTest(unittest.TestCase):
    def test_saved_views_keep_only_known_values_and_reset(self):
        with tempfile.TemporaryDirectory() as d:
            library.save_view(d, "films", {"sort": "added", "layout": "list", "size": "huge", "chip": "missing", "evil": "x"})
            library.save_view(d, "tv", {"chip": "not-a-chip"})
            self.assertEqual(library.views(d), {"films": {"sort": "added", "layout": "list", "chip": "missing"}, "tv": {}})
            with self.assertRaises(ValueError):
                library.save_view(d, "../etc", {})
            library.reset_views(d)
            self.assertEqual(library.views(d), {})


class HandleTest(unittest.TestCase):
    def test_without_reelix_the_library_says_so(self):
        class H:
            path = "/api/library/wall?tab=films"

            def __init__(self, data):
                self.app = mock.Mock()
                self.app.config.data = {"services": [], "show_posters": True}
                self.app.config.data_dir = data
                self.sent = None

            def error(self, status, message, **extra):
                self.sent = (status, message, extra)

        with tempfile.TemporaryDirectory() as d:
            h = H(d)
            library.handle(h, "GET", "/api/library/wall")
        self.assertEqual(h.sent[0], 409)
        self.assertEqual(h.sent[2], {"reelix": False})


if __name__ == "__main__":
    unittest.main()
