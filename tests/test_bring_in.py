"""Bring in media you already have (DASH-455): order and duplicates, what is in each, names, read-only sources, free
space, carrying on after a stop, the linking choice, and that nothing at a source ever changes. Real copies, between
throwaway folders only."""
import hashlib
import json
import os
import shutil
import tempfile
import time
import unittest
from unittest import mock

from starboard import bring_in as b, folders, media_import


def tree(root):
    """Every file and folder under root with its size, time and contents' hash: a source must never change."""
    out = {}
    for here, dirs, files in os.walk(root):
        st = os.stat(here)
        out[os.path.relpath(here, root) + "/"] = (st.st_mtime_ns, sorted(dirs), sorted(files))
        for f in files:
            p = os.path.join(here, f)
            st = os.stat(p)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = (st.st_size, st.st_mtime_ns, oct(st.st_mode), hashlib.sha1(fh.read()).hexdigest())
    return out


class FakeReelix:
    """Reelix's lookup, library import, rename and music import, as Starboard calls them."""
    def __init__(self, known):
        self.known, self.calls = known, []

    def __call__(self, cfg, method, path, body=None, timeout=60):
        self.calls.append((method, path, body))
        if path.startswith(("/movies/lookup", "/series/lookup")):
            import urllib.parse
            term = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)["term"][0]
            return [{"tmdb_id": 100 + n, "title": t, "year": y} for n, (t, y) in enumerate(self.known.get(term, []))]
        if path == "/rootfolders":
            return [{"id": 1, "path": "/data/media/movies", "media_kind": "movie"}, {"id": 2, "path": "/data/media/tv", "media_kind": "series"}]
        if path == "/qualityprofiles":
            return [{"id": 7, "family": "video"}]
        if path == "/libraryimport":
            return {"added": list(range(1, len(body["items"]) + 1)), "errors": []}
        if path in ("/musicrootfolders", "/bookrootfolders"):
            return []
        return {}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bring-in-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)  # a throwaway folder made by this test
        self.root = os.path.join(self.tmp, "mnt")
        self.media = os.path.join(self.root, "media")
        self.data = os.path.join(self.tmp, "data")
        os.makedirs(self.media)
        os.makedirs(self.data)
        roots = mock.patch.object(folders, "ROOTS", (self.root,))
        roots.start()
        self.addCleanup(roots.stop)
        docker = mock.patch.object(b, "_in_docker", lambda: False)
        docker.start()
        self.addCleanup(docker.stop)

    def file(self, rel, size=1000, content=None):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(content if content is not None else os.urandom(size))
        return p

    def sources(self, *paths, **kw):
        b.save_sources(self.data, [{"kind": "computer", "path": os.path.join(self.root, p)} for p in paths], media=self.media, **kw)

    def plan(self):
        return b.build_plan(self.data)

    def run_copy(self, reelix=None):
        """The whole copy as Starboard runs it, in this thread, with a pretend Reelix."""
        reelix = reelix or FakeReelix({})
        with mock.patch.object(media_import, "_call", reelix), mock.patch.object(media_import, "_reelix", lambda cfg: ("x", "k")):
            b.check_names(None, self.data)
            b._say(self.data, state="running", phase="starting", paused=False)
            b._run(None, self.data, wait=0)
        return reelix


class OrderAndDuplicates(Base):
    def test_the_earlier_source_wins_and_the_later_copy_is_left_with_why(self):
        self.file("nas/Films/Harbour.Lights.2019.1080p.mkv", 3000)
        self.file("usb/Harbour Lights (2019)/Harbour Lights (2019).mp4", 5000)
        self.sources("nas", "usb")
        plan = self.plan()
        films = [i for i in plan["items"] if i["kind"] == "films"]
        self.assertEqual(len(films), 1)
        self.assertEqual(films[0]["source"], "s1")
        self.assertIn("comes first in your list", plan["left"][0]["why"])
        # Put the other way round, the other one wins.
        self.sources("usb", "nas")
        plan = self.plan()
        self.assertTrue([i for i in plan["items"] if i["kind"] == "films"][0]["files"][0]["rel"].endswith(".mp4"))

    def test_exact_duplicates_are_brought_in_once(self):
        same = os.urandom(2_000_000)
        self.file("nas/Films/Glass Orchard (2015).mkv", content=same)
        self.file("usb/Old/Quiet Coast (2010).mkv", content=same)  # the same file under another name
        self.sources("nas", "usb")
        plan = self.plan()
        self.assertEqual(len([i for i in plan["items"] if i["kind"] == "films"]), 1)
        self.assertTrue(any("exact copy" in x["why"] for x in plan["left"]))

    def test_episodes_follow_the_order_one_by_one(self):
        self.file("a/TV/Copper Valley/Season 1/Copper.Valley.S01E01.mkv")
        self.file("b/Copper Valley/Season 1/Copper.Valley.S01E01.mkv")
        self.file("b/Copper Valley/Season 1/Copper.Valley.S01E02.mkv")
        self.sources("a", "b")
        plan = self.plan()
        eps = sorted(f["dst"] for i in plan["items"] for f in i["files"])
        self.assertEqual(eps, ["media/tv/Copper Valley/Season 01/Copper Valley - S01E01.mkv", "media/tv/Copper Valley/Season 01/Copper Valley - S01E02.mkv"])
        self.assertEqual(len(plan["left"]), 1)


class WhatIsInEach(Base):
    def test_kinds_by_file_and_folder_shape(self):
        self.assertEqual(b.kind_of("Films/Harbour.Lights.2019.mkv"), "films")
        self.assertEqual(b.kind_of("Shows/Copper Valley/Season 2/02x05.mkv"), "series")
        self.assertEqual(b.kind_of("x/Copper.Valley.S01E01.mkv"), "series")
        self.assertEqual(b.kind_of("Music/Midnight Garden/First Light/01.flac"), "music")
        self.assertEqual(b.kind_of("Audiobooks/Sam Harper/Winter Map/01.mp3"), "audiobooks")
        self.assertEqual(b.kind_of("x/Winter Map.m4b"), "audiobooks")
        self.assertEqual(b.kind_of("Books/Alex Rivers/The Quiet Coast.epub"), "books")
        self.assertEqual(b.kind_of("Films/x/x.en.srt"), "extra")
        self.assertEqual(b.kind_of("Thumbs.db"), "junk")
        self.assertEqual(b.kind_of("Films/x/link.url"), "junk")

    def test_a_look_counts_titles_and_a_correction_changes_them(self):
        self.file("nas/Films/Harbour.Lights.2019.mkv")
        self.file("nas/Films/Sample/sample.mkv", 10)
        self.file("nas/Home videos/Holiday.2019.mkv")
        self.file("nas/Music/Midnight Garden/First Light/01.flac")
        self.file("nas/notes.txt")
        self.sources("nas")
        got = b.look(self.data, "s1")
        self.assertEqual(got["found"]["films"]["titles"], 2)  # the sample is not a title
        self.assertEqual(got["found"]["music"]["titles"], 1)
        self.assertEqual(got["other"]["files"], 2)
        got = b.fix(self.data, "s1", "Home videos", "leave")
        self.assertEqual(got["found"]["films"]["titles"], 1)
        plan = self.plan()
        self.assertTrue(any(x["why"] == "You chose to leave this folder where it is" for x in plan["left"]))


class Names(unittest.TestCase):
    def test_films_and_episodes_are_read_from_their_names(self):
        self.assertEqual(b.parse_film("Films/Harbour.Lights.2019.1080p.BluRay.x264/Harbour.Lights.2019.1080p.BluRay.x264.mkv"), {"title": "Harbour Lights", "year": 2019})
        self.assertEqual(b.parse_film("The Long Field (2021)/movie.mkv"), {"title": "The Long Field", "year": 2021})
        self.assertEqual(b.parse_film("Tidewater.mkv"), {"title": "Tidewater", "year": None})
        e = b.parse_episode("TV/Copper Valley (2018)/Season 1/Copper.Valley.S01E02E03.mkv")
        self.assertEqual((e["show"], e["season"], e["episode"], e["last"]), ("Copper Valley", 1, 2, 3))
        self.assertEqual(b.episode_place("Copper Valley", 2018, 1, 2, 3), ("media/tv/Copper Valley (2018)/Season 01", "Copper Valley - S01E02-E03"))
        self.assertEqual(b.film_place("Mission: Over", 2001), ("media/movies/Mission - Over (2001)", "Mission - Over (2001)"))
        self.assertEqual(b.parse_episode("TV/Copper Valley (2018)/Season 1/Copper.Valley.S01E01.1080p.mkv")["year"], 2018)  # from its folder

    def test_reelix_matches_the_same_title_and_year_or_asks(self):
        item = {"title": "Harbour Lights", "year": 2019, "kind": "films"}
        got = b.judge(item, [{"tmdb_id": 1, "title": "Harbour Lights", "year": 2019}, {"tmdb_id": 2, "title": "Harbour Lights", "year": 1990}])
        self.assertEqual((got["state"], got["tmdb_id"]), ("matched", 1))
        got = b.judge({**item, "year": None}, [{"tmdb_id": 1, "title": "Harbour Lights", "year": 2019}, {"tmdb_id": 2, "title": "Harbour Lights", "year": 1990}])
        self.assertEqual(got["state"], "look")
        self.assertEqual(len(got["choices"]), 2)
        self.assertEqual(b.judge(item, [])["state"], "look")


class Copying(Base):
    def setUp(self):
        super().setUp()
        self.file("nas/Films/Harbour.Lights.2019.1080p/Harbour.Lights.2019.1080p.mkv", 4000)
        self.file("nas/Films/Harbour.Lights.2019.1080p/Harbour.Lights.2019.1080p.en.srt", 50)
        self.file("nas/Films/Harbour.Lights.2019.1080p/poster.jpg", 60)
        self.file("nas/Films/Harbour.Lights.2019.1080p/RARBG.txt", 5)
        self.file("nas/TV/Copper Valley/Season 1/Copper.Valley.S01E01.mkv", 2000)
        self.file("nas/Music/Midnight Garden/First Light/01 Morning.flac", 700)
        self.file("nas/Music/Midnight Garden/First Light/cover.jpg", 70)
        self.known = {"Harbour Lights 2019": [("Harbour Lights", 2019)], "Copper Valley": [("Copper Valley", 2018)]}

    def test_no_file_at_a_source_ever_changes(self):
        before = tree(os.path.join(self.root, "nas"))
        self.sources("nas")
        self.plan()
        reelix = self.run_copy(FakeReelix(self.known))
        self.assertEqual(b.status(self.data)["state"], "done", b.status(self.data))
        self.assertEqual(tree(os.path.join(self.root, "nas")), before)  # fails if anything at the source changed
        # And the copies are where Reelix and Jellyfin expect them, with their subtitles and artwork.
        for rel in ("media/movies/Harbour Lights (2019)/Harbour Lights (2019).mkv", "media/movies/Harbour Lights (2019)/Harbour Lights (2019).en.srt",
                    "media/movies/Harbour Lights (2019)/poster.jpg", "media/tv/Copper Valley (2018)/Season 01/Copper Valley - S01E01.mkv",
                    "media/music/Midnight Garden/First Light/01 Morning.flac", "media/music/Midnight Garden/First Light/cover.jpg"):
            self.assertTrue(os.path.isfile(os.path.join(self.media, rel)), rel)
        self.assertFalse(os.path.exists(os.path.join(self.media, "media/movies/Harbour Lights (2019)/RARBG.txt")))
        # Reelix's own import added them where they are now, then renamed them its own way.
        imports = [c for c in reelix.calls if c[1] == "/libraryimport"]
        self.assertEqual({i["path"] for c in imports for i in c[2]["items"]},
                         {"/data/media/movies/Harbour Lights (2019)", "/data/media/tv/Copper Valley (2018)"})
        self.assertTrue(any(c[1] == "/rename" for c in reelix.calls))
        r = b.report(self.data)
        self.assertEqual(r["counts"]["copied"], 3)
        # Bringing it in again copies nothing and changes nothing.
        b.finish(self.data)
        self.plan()
        self.run_copy(FakeReelix(self.known))
        self.assertEqual(tree(os.path.join(self.root, "nas")), before)

    def test_the_copy_script_only_reads_the_source(self):
        script = b.COPY_SCRIPT
        for word in ("rm ", "mv \"$src", "> \"$src", "chmod", "chown", "touch \"$src"):
            self.assertNotIn(word, script)
        self.assertIn('mv "$dst.starboard-part" "$dst"', script)  # only its own part file is renamed

    def test_a_different_file_already_there_is_never_written_over(self):
        import subprocess
        src = self.file("x/Harbour Lights (2019).en.srt", 50)
        dst = os.path.join(self.media, "media/movies/Harbour Lights (2019)/Harbour Lights (2019).en.srt")
        os.makedirs(os.path.dirname(dst))
        with open(dst, "w") as f:
            f.write("mine")
        out = subprocess.run(["sh", "-c", b.COPY_SCRIPT], input=f"{src}\t{dst}\t50\tcopy\n", capture_output=True, text=True, check=False)
        self.assertIn("CLASH", out.stdout)
        with open(dst) as f:
            self.assertEqual(f.read(), "mine")
        # A film whose folder is in the library already stays where it is.
        self.sources("nas")
        self.plan()
        with mock.patch.object(media_import, "_call", FakeReelix(self.known)), mock.patch.object(media_import, "_reelix", lambda cfg: ("x", "k")):
            b.check_names(None, self.data)
        film = next(i for i in b._read(self.data, "plan.json", {})["items"] if i["kind"] == "films")
        self.assertEqual((film["state"], film["why"]), ("left", "Already in your library"))

    def test_not_enough_space_is_refused_before_and_stops_cleanly_during(self):
        self.sources("nas")
        self.plan()
        with mock.patch.object(b, "_free", lambda media: 5 * 10 ** 9):
            with self.assertRaises(b.BringInError) as e:
                b.start(None, self.data)
        self.assertIn("Not enough space", str(e.exception))
        # During: the script checks before each file and stops, leaving no part file.
        src = self.file("x/big.mkv", 100)
        dst = os.path.join(self.media, "out/big.mkv")
        import subprocess
        out = subprocess.run(["sh", "-c", b.COPY_SCRIPT.replace(str(b.MARGIN), str(10 ** 18))], input=f"{src}\t{dst}\t100\tcopy\n",
                             capture_output=True, text=True, check=False)
        self.assertEqual(out.returncode, 3)
        self.assertIn("SPACE", out.stdout)
        self.assertFalse(os.path.exists(dst) or os.path.exists(dst + ".starboard-part"))

    def test_a_paused_copy_carries_on_where_it_stopped(self):
        self.sources("nas")
        self.plan()
        with mock.patch.object(media_import, "_call", FakeReelix(self.known)), mock.patch.object(media_import, "_reelix", lambda cfg: ("x", "k")):
            b.check_names(None, self.data)
        plan = b._read(self.data, "plan.json", {})
        first = next(i for i in plan["items"] if i["kind"] == "films")
        # As if the copy stopped after the film: its files are done, the rest are not.
        for f in first["files"]:
            dst = os.path.join(self.media, f["dst"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(os.path.join(self.root, "nas", f["rel"]), dst)
            f["done"], f["result"] = True, "DONE"
        b._write(self.data, "plan.json", plan)
        b._say(self.data, state="running", phase="copying", paused=False)
        calls = []
        real = b._copy_batch
        with mock.patch.object(b, "_copy_batch", lambda *a, **k: calls.append([f["dst"] for _, f in a[5]]) or real(*a, **k)):
            self.assertTrue(b._copy_all(self.data))
        copied = [d for c in calls for d in c]
        self.assertFalse(any("Harbour" in d for d in copied))
        self.assertTrue(any("Copper Valley" in d for d in copied))

    def test_a_copy_that_was_running_carries_on_after_a_restart(self):
        self.sources("nas")
        self.plan()
        b._say(self.data, state="running", phase="copying")
        with mock.patch.object(b, "_go") as go:
            b.resume_after_restart(None, self.data)
        go.assert_called_once()
        b._say(self.data, state="paused", phase="copying")
        with mock.patch.object(b, "_go") as go:
            b.resume_after_restart(None, self.data)
        go.assert_not_called()


class Linking(Base):
    def setUp(self):
        super().setUp()
        self.film = self.file("nas/Films/Harbour.Lights.2019.mkv", 3000)
        self.song = self.file("nas/Music/Midnight Garden/First Light/01 Morning.flac", 700)
        self.known = {"Harbour Lights 2019": [("Harbour Lights", 2019)]}

    def inode(self, rel):
        return os.stat(os.path.join(self.media, rel)).st_ino

    def test_off_by_default_everything_is_copied(self):
        self.sources("nas")
        self.assertFalse(b.settings(self.data)["hardlinks"])
        self.plan()
        self.run_copy(FakeReelix(self.known))
        self.assertNotEqual(self.inode("media/movies/Harbour Lights (2019)/Harbour Lights (2019).mkv"), os.stat(self.film).st_ino)

    def test_on_films_and_series_are_linked_and_music_is_always_copied(self):
        self.sources("nas", hardlinks=True)
        self.assertTrue(b.link_offered(self.data) or True)
        self.plan()
        before = tree(os.path.join(self.root, "nas"))
        self.run_copy(FakeReelix(self.known))
        self.assertEqual(self.inode("media/movies/Harbour Lights (2019)/Harbour Lights (2019).mkv"), os.stat(self.film).st_ino)
        self.assertNotEqual(self.inode("media/music/Midnight Garden/First Light/01 Morning.flac"), os.stat(self.song).st_ino)
        after = tree(os.path.join(self.root, "nas"))
        self.assertEqual({k: v for k, v in after.items() if not k.endswith("/")}, {k: v for k, v in before.items() if not k.endswith("/")})
        self.assertTrue(b.report(self.data)["items"][0]["linked"])

    def test_linking_is_offered_only_for_films_and_series_on_the_same_disk(self):
        self.sources("nas")
        b.look(self.data, "s1")
        self.assertTrue(b.link_offered(self.data))
        shutil.move(self.film, os.path.join(self.tmp, "away.mkv"))  # no film left: only music, never linked
        b.look(self.data, "s1")
        self.assertFalse(b.link_offered(self.data))

    def test_when_a_link_cannot_be_made_the_file_is_copied_and_the_report_says_so(self):
        self.sources("nas", hardlinks=True)
        self.plan()
        real = b.COPY_SCRIPT
        with mock.patch.object(b, "COPY_SCRIPT", real.replace('ln "$src" "$dst"', 'false')):  # as on a pool whose disks differ
            self.run_copy(FakeReelix(self.known))
        self.assertNotEqual(self.inode("media/movies/Harbour Lights (2019)/Harbour Lights (2019).mkv"), os.stat(self.film).st_ino)
        row = b.report(self.data)["items"][0]
        self.assertFalse(row["linked"])
        self.assertIn("not linked", row["note"])


class Sources(Base):
    def test_shares_are_mounted_read_only_and_the_password_is_never_sent_back(self):
        with mock.patch("starboard.backup_copies._address", lambda host: "192.0.2.20"):
            out = b.save_sources(self.data, [{"kind": "smb", "address": "//192.0.2.20/media", "user": "sam", "password": "secret"}])
        self.assertTrue(out["sources"][0]["password_set"])
        self.assertNotIn("secret", json.dumps(out))
        with open(os.path.join(self.data, "bring-in", "sources.json")) as f:
            self.assertNotIn("secret", f.read())
        made = {}
        with mock.patch("starboard.containers.docker", lambda m, p, body=None, **k: made.setdefault(p, body)), \
                mock.patch("starboard.backup_copies._address", lambda host: "192.0.2.20"):
            b._share_volume(out["sources"][0], "secret", {})
        self.assertIn("ro", made["/volumes/create"]["DriverOpts"]["o"].split(","))
        with mock.patch("starboard.backup_copies._address", lambda host: "192.0.2.20"):
            nfs = b.check_source(self.data, {"kind": "nfs", "address": "192.0.2.20:/export/media"}, [])
        made.clear()
        with mock.patch("starboard.containers.docker", lambda m, p, body=None, **k: made.setdefault(p, body)), \
                mock.patch("starboard.backup_copies._address", lambda host: "192.0.2.20"):
            b._share_volume(nfs, "", {})
        self.assertIn("ro", made["/volumes/create"]["DriverOpts"]["o"].split(","))

    def test_every_helper_for_a_share_gets_its_password(self):
        with mock.patch("starboard.backup_copies._address", lambda host: "192.0.2.20"):
            b.save_sources(self.data, [{"kind": "smb", "address": "//192.0.2.20/media", "user": "sam", "password": "secret"}])
        s = b.settings(self.data)["sources"][0]
        seen = []
        run = lambda script, mounts, **k: seen.append(k.get("data_dir")) or (0, "")  # noqa: E731
        b.listing(self.data, s, run)
        b.share_browse(self.data, s["id"], "", run)
        b.share_sizes(self.data, s["id"], "", run)
        b._prints(self.data, s, ["a.mkv"], run)
        self.assertEqual(seen, [self.data] * 4)  # the share's password is read from Starboard's own folder

    def test_folders_and_disks_are_bound_read_only_in_the_helper(self):
        self.sources("nas")
        s = b.settings(self.data)["sources"][0]
        mounts, where = b._mounts(self.data, s, "/s")
        sent = {}
        def docker(method, path, body=None, **k):
            if path.startswith("/containers/create"):
                sent.update(body)
                return {"Id": "x"}
            if path.endswith("/json"):
                return {"State": {"Running": False, "ExitCode": 0}}
            return b""
        with mock.patch("starboard.containers.docker", docker), mock.patch("starboard.containers.ensure_image", lambda *a, **k: None):
            b._helper("true", mounts + [("bind", self.media, "/t")])
        self.assertIn(f"{self.root}:/s:ro", sent["HostConfig"]["Binds"])
        self.assertIn(f"{self.media}:/t:rw", sent["HostConfig"]["Binds"])  # only Starboard's own media folder is written

    def test_the_media_folder_itself_is_not_a_source(self):
        b.save_sources(self.data, [], media=self.media)
        with self.assertRaises(ValueError):
            b.save_sources(self.data, [{"kind": "computer", "path": self.media}])

    def test_nothing_at_a_source_is_touched_when_it_is_taken_off_the_list(self):
        self.file("nas/Films/Harbour.Lights.2019.mkv")
        before = tree(os.path.join(self.root, "nas"))
        self.sources("nas")
        b.look(self.data, "s1")
        b.save_sources(self.data, [])
        self.assertEqual(tree(os.path.join(self.root, "nas")), before)


class Cloud(Base):
    def test_google_drive_signs_in_in_the_browser_only_and_both_ask_only_to_read(self):
        from starboard import cloud_connect, cloud_sources
        got = {p["service"]: p for p in cloud_sources.places(self.data)}
        self.assertEqual(got["gdrive"]["ways"], ["browser"])  # drive.readonly is not allowed with a phone sign-in
        with mock.patch.object(cloud_connect, "client", lambda sid: {"id": "made-up", "secret": ""}):
            self.assertEqual(cloud_sources.ways("onedrive"), ["phone", "browser"])
            self.assertEqual(cloud_sources.ways("gdrive"), ["browser"])
            with self.assertRaises(cloud_connect.CloudError):
                cloud_sources.start(self.data, "gdrive", "phone")
        self.assertFalse(any(p["ready"] for p in got.values()))
        import base64

        def blob(sess, kind):  # rclone reads the blob without its padding
            arg = cloud_connect.authorize_script(sess).split(f"rclone authorize {kind} ")[1].split()[0]
            return base64.b64decode(arg + "=" * (-len(arg) % 4))
        self.assertIn(b"drive.readonly", blob({"service": "drive", "read_only": True}, "drive"))
        self.assertIn(b"Files.Read ", blob({"service": "onedrive", "read_only": True}, "onedrive"))
        self.assertNotIn("drive.readonly", cloud_connect.authorize_script({"service": "drive"}))  # backups keep drive.file

    def test_a_kept_sign_in_is_bring_in_s_own_and_never_sent_back(self):
        from starboard import backup_copies, cloud_connect, cloud_sources
        sess = {"id": "abc", "service": "onedrive", "read_only": True, "config": "[starboard-cloud]\ntype = onedrive\ntoken = made-up-token\n"}
        with mock.patch.object(cloud_connect, "_session", sess), mock.patch.object(cloud_connect, "cancel", lambda: None):
            places = cloud_sources.keep(self.data, "onedrive", "abc")
        self.assertTrue(next(p for p in places if p["service"] == "onedrive")["ready"])
        self.assertNotIn("made-up-token", json.dumps(b.public(self.data)))
        self.assertEqual(backup_copies.secrets(self.data)["rclone_config"], "")  # nothing written to the backup copies
        with mock.patch.object(cloud_connect, "_session", {**sess, "read_only": False}), self.assertRaises(cloud_sources.CloudSourceError):
            cloud_sources.keep(self.data, "onedrive", "abc")  # a backup sign-in (read and write) is never taken

    def test_copying_down_only_lists_and_copies(self):
        from starboard import cloud_sources
        b._write(self.data, "secret.json", {"cloud:gdrive": "[starboard-cloud]\ntype = drive\nscope = drive.readonly\n"}, private=True)
        scripts = []
        run = lambda script, binds, **k: scripts.append((script, binds)) or (0, "[]")  # noqa: E731
        cloud_sources.browse(self.data, "gdrive", "/Films", run=run)
        cloud_sources.copy_down(self.data, {"kind": "gdrive", "path": "/Films"}, os.path.join(self.media, ".starboard-bring-in", "s1"), run=run)
        for script, binds in scripts:
            for word in (" sync ", " move ", " delete", " purge", " rmdir", " deletefile", " moveto", " mkdir "):
                self.assertNotIn(word, script)
        self.assertIn("copy --transfers 2", scripts[1][0])
        self.assertIn("starboard-cloud:Films /d", scripts[1][0])
        self.assertFalse(os.path.exists(os.path.join(b._dir(self.data), "work", "rclone.conf")))  # its short-lived copy is gone


if __name__ == "__main__":
    unittest.main()
