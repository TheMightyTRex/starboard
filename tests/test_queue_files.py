"""A download that needs attention, in full (DASH-496): the folder, plain words, the actions that fit, unpacking,
and deleting only what is the download's own."""
import unittest
from unittest import mock

from starboard import containers, queue_files, services

REELIX = [{"id": "rx", "name": "Reelix", "type": "link", "icon": "reelix", "url": "http://reelix:7878", "api_key": "made-up-reelix-key-5678"},
          {"id": "rx-tv", "name": "Reelix TV", "type": "sonarr", "icon": "reelix", "url": "http://reelix:7878/sonarr", "api_key": "made-up-reelix-key-5678"},
          {"id": "rx-films", "name": "Reelix films", "type": "radarr", "icon": "reelix", "url": "http://reelix:7878/radarr", "api_key": "made-up-reelix-key-5678"}]
SONARR = {"id": "tv", "name": "Example TV", "type": "sonarr", "url": "http://sonarr:8989", "api_key": "made-up-sonarr-key-1234"}
SEASON = "/data/downloads/usenet/completed/tv/Old.Show.S02.1080p.BluRay.x264-GROUP"

QUEUE = {"items": [
    {"id": 16, "title": "Old.Show.S02.1080p.BluRay.x264-GROUP", "download_client": "NZBGet", "download_id": "nzb-16", "state": "import_pending",
     "client_state": "completed", "messages": ["No video files found in the download"], "output_path": SEASON, "can_manual_import": True,
     "size": 2_400_000_000, "media": {"kind": "series", "id": 8, "title": "Old Show"}},
    {"id": 17, "title": "Made.Up.Film.2024.1080p.WEB", "download_client": "qBittorrent", "download_id": "abc17", "state": "import_pending",
     "client_state": "completed", "messages": ["Made.Up.Film.2024.1080p.WEB.mkv: Not an upgrade for the existing file (Bluray-1080p, score 0)"],
     "output_path": "/data/downloads/torrents/films/Made.Up.Film.2024.1080p.WEB", "media": {"kind": "movie", "id": 10, "title": "Made Up Film"}},
    {"id": 18, "title": "Some.Series.S01E04.1080p", "download_client": "qBittorrent", "download_id": "abc18", "state": "import_pending",
     "client_state": "completed", "messages": ["Episodes are not part of the series"], "output_path": "/data/downloads/torrents/tv/Some.Series.S01E04.1080p",
     "media": {"kind": "series", "id": 9, "title": "Some Series"}},
]}

FIND_SEASON = "\n".join([
    "d\t4096\t1000:1000\t",
    "d\t4096\t1000:1000\tOld.Show.S02E17.1080p.BluRay.x264-GROUP",
    "f\t100000000\t1000:1000\tOld.Show.S02E17.1080p.BluRay.x264-GROUP/old.show.s02e17.rar",
    "f\t100000000\t1000:1000\tOld.Show.S02E17.1080p.BluRay.x264-GROUP/old.show.s02e17.r00",
    "f\t290\t1000:1000\tOld.Show.S02E17.1080p.BluRay.x264-GROUP/old.show.s02e17.nfo",
    "d\t4096\t1000:1000\tOld.Show.S02E19.1080p.BluRay.x264-GROUP",
    "f\t100000000\t1000:1000\tOld.Show.S02E19.1080p.BluRay.x264-GROUP/old.show.s02e19.part01.rar",
    "f\t100000000\t1000:1000\tOld.Show.S02E19.1080p.BluRay.x264-GROUP/old.show.s02e19.part02.rar",
]) + "\n"


def item(n, services_list=REELIX):
    with mock.patch.object(services, "_api", return_value=QUEUE):
        return queue_files.find(services_list, "rx-tv", n)


def folder(listing, path="/x"):
    files, owner, single = queue_files.parse_listing(listing, path)
    return {"files": files, "owner": owner, "single": single, "missing": not files, "summary": queue_files.summary(files, not files)}


class KindsTest(unittest.TestCase):
    def test_each_file_is_sorted(self):
        k = queue_files.kind_of
        self.assertEqual(k("Show.S01E01.mkv"), "media")
        self.assertEqual(k("Show.S01E01.Sample.mkv"), "sample")
        self.assertEqual(k("sample/show-sample.mkv"), "sample")
        self.assertEqual(k("Show.S01E01.exe"), "program")
        self.assertEqual(k("Show.S01E01.mkv.lnk"), "program")
        self.assertEqual(k("a.rar"), "archive")
        self.assertEqual(k("a.r07"), "archive")
        self.assertEqual(k("a.zip"), "archive")
        self.assertEqual(k("a.epub"), "media")
        self.assertEqual(k("a.srt"), "subtitle")
        self.assertEqual(k("a.nfo"), "other")
        self.assertEqual(k("Samplers.Of.Time.S01E01.mkv"), "media")  # "sample" only as a word

    def test_the_listing_and_its_summary(self):
        f = folder(FIND_SEASON, SEASON)
        self.assertEqual(f["owner"], "1000:1000")
        self.assertEqual(len(f["files"]), 5)
        self.assertEqual(f["summary"]["verdict"], "archive")
        self.assertEqual(f["summary"]["archive"], 4)
        self.assertEqual(f["summary"]["total_size"], 400_000_290)

    def test_a_single_file_download(self):
        f = folder("f\t5000\t1000:1000\t\n", "/data/downloads/Show.S01E01.exe")
        self.assertTrue(f["single"])
        self.assertEqual(f["files"][0]["name"], "Show.S01E01.exe")
        self.assertEqual(f["summary"]["verdict"], "program")

    def test_first_volumes_only(self):
        vols, other = queue_files.first_volumes(folder(FIND_SEASON)["files"])
        self.assertEqual([v["name"].split("/")[-1] for v in vols], ["old.show.s02e17.rar", "old.show.s02e19.part01.rar"])
        _, other = queue_files.first_volumes([{"name": "a.7z"}, {"name": "b.001"}])
        self.assertEqual(other, ["a.7z", "b.001"])

    def test_each_rar_set_is_one_row(self):
        rows = queue_files.grouped(folder(FIND_SEASON)["files"])
        sets = {r["name"].split("/")[-1]: r for r in rows if r["kind"] == "archive"}
        self.assertEqual(sets["old.show.s02e17.rar"]["parts"], 2)
        self.assertEqual(sets["old.show.s02e17.rar"]["size"], 200_000_000)
        self.assertEqual(sets["old.show.s02e19.rar"]["parts"], 2)
        self.assertEqual(len(rows), 3)

    def test_sizes_in_words(self):
        self.assertEqual(queue_files.size_words(290), "290 bytes")
        self.assertEqual(queue_files.size_words(2 * 1024 ** 3), "2 GB")
        self.assertEqual(queue_files.size_words(1.5 * 1024 ** 2), "1.5 MB")


class WordsAndActionsTest(unittest.TestCase):
    def test_archives_suggest_unpacking(self):
        i, f = item(16), folder(FIND_SEASON, SEASON)
        d = queue_files.diagnose(i, f)
        self.assertEqual(d[0]["title"], "The files are inside archives")
        self.assertIn("Unpack the archives", d[0]["text"])
        acts, suggest = queue_files.actions(i, f, {"rar": True, "zip": True})
        self.assertEqual(suggest, "unpack")
        self.assertEqual(acts[0], "unpack")
        for a in ("import", "ignore", "block-search", "remove-keep", "delete", "delete-block"):
            self.assertIn(a, acts)

    def test_after_unpacking_it_is_ready_to_import(self):
        listing = FIND_SEASON + "f\t1400000000\t1000:1000\tOld.Show.S02E17.1080p.BluRay.x264-GROUP/Old.Show.S02E17.mkv\n"
        i, f = item(16), folder(listing, SEASON)
        self.assertEqual(queue_files.diagnose(i, f)[0]["title"], "The files are ready to import")
        acts, suggest = queue_files.actions(i, f, {"rar": True, "zip": True})
        self.assertNotIn("unpack", acts)
        self.assertEqual(suggest, "import")

    def test_no_unrar_no_unpack(self):
        acts, suggest = queue_files.actions(item(16), folder(FIND_SEASON, SEASON), {"rar": False, "zip": True})
        self.assertNotIn("unpack", acts)
        self.assertEqual(suggest, "import")

    def test_a_program_comes_first_and_suggests_the_blocklist(self):
        f = folder("d\t1\t0:0\t\nf\t9000\t0:0\tShow.S01E04.exe\nf\t100\t0:0\tShow.S01E04.txt\n")
        d = queue_files.diagnose(item(16), f)
        self.assertEqual(d[0]["tone"], "danger")
        self.assertIn(".exe", d[0]["text"])
        acts, suggest = queue_files.actions(item(16), f, {"rar": True, "zip": True})
        self.assertEqual(suggest, "delete-block")
        self.assertNotIn("import", acts)

    def test_a_sample_only_suggests_finding_another(self):
        f = folder("d\t1\t0:0\t\nf\t40000000\t0:0\tSample/show.s02-sample.mkv\nf\t100\t0:0\tshow.nfo\n")
        self.assertEqual(queue_files.diagnose(item(16), f)[0]["title"], "Only a sample was downloaded")
        self.assertEqual(queue_files.actions(item(16), f, {})[1], "block-search")

    def test_missing_files(self):
        f = {"files": [], "owner": "", "single": False, "missing": True, "summary": queue_files.summary([], True)}
        self.assertEqual(queue_files.diagnose(item(16), f)[0]["title"], "The files are missing")
        self.assertEqual(queue_files.actions(item(16), f, {})[1], "block-search")

    def test_not_an_upgrade_suggests_deleting(self):
        i = item(17)
        f = folder("d\t1\t0:0\t\nf\t9000000000\t0:0\tMade.Up.Film.2024.1080p.WEB.mkv\n")
        self.assertEqual(queue_files.diagnose(i, f)[0]["title"], "You already have a copy that is as good or better")
        acts, suggest = queue_files.actions(i, f, {})
        self.assertEqual(suggest, "delete")
        self.assertIn("choose-film", acts)
        self.assertEqual(i["kind"], "film")

    def test_renumbered_episode(self):
        i = item(18)
        acts, suggest = queue_files.actions(i, None, {})
        self.assertEqual(suggest, "choose-episode")
        self.assertEqual(queue_files.diagnose(i, None)[0]["title"], "The episode is numbered differently")

    def test_words_follow_the_content_rules(self):
        banned = ("click", " see ", " look", "just", "please", "above", "below", "—", "n't", "'re", "'ll", "you'")
        for n, listing in ((16, FIND_SEASON), (17, "d\t1\t0:0\t\nf\t9\t0:0\ta.exe\n"), (16, "d\t1\t0:0\t\nf\t9\t0:0\tsample.mkv\n")):
            for x in queue_files.diagnose(item(n), folder(listing)):
                text = f" {x['title']} {x['text']} ".lower()
                for b in banned:
                    self.assertNotIn(b, text, x)


class FindTest(unittest.TestCase):
    def test_reelix_rows_come_from_reelix_own_queue(self):
        i = item(16)
        self.assertEqual(i["output_path"], SEASON)
        self.assertEqual(i["kind"], "episode")
        self.assertTrue(i["reelix"])
        self.assertEqual(i["native"]["id"], "rx")

    def test_an_app_like_sonarr_from_its_queue(self):
        page = {"records": [{"id": 3, "title": "Old.Show.S05E01", "status": "completed", "trackedDownloadState": "importPending",
                             "trackedDownloadStatus": "warning", "outputPath": "/data/downloads/complete/Old.Show.S05E01", "downloadId": "nzb3",
                             "statusMessages": [{"messages": ["No files found are eligible for import"]}]}]}
        with mock.patch.object(services, "_api", return_value=page):
            i = queue_files.find([SONARR], "tv", 3)
        self.assertFalse(i["reelix"])
        self.assertEqual(i["messages"], ["No files found are eligible for import"])
        self.assertEqual(queue_files.actions(i, None, {})[0], ["block-search", "remove-keep", "delete", "delete-block"])

    def test_gone(self):
        with mock.patch.object(services, "_api", return_value={"items": [], "records": []}):
            with self.assertRaises(LookupError):
                queue_files.find(REELIX, "rx-tv", 99)
        with self.assertRaises(LookupError):
            queue_files.find(REELIX, "rx-tv", "1; rm")


class DetailsTest(unittest.TestCase):
    def test_without_docker_the_words_and_queue_actions_still_come(self):
        with mock.patch.object(services, "_api", return_value=QUEUE), mock.patch.object(containers, "available", return_value=False):
            d = queue_files.details(REELIX, "rx-tv", 16)
        self.assertIsNone(d["summary"])
        self.assertIn("Docker connection", d["folder_problem"])
        self.assertIn("delete", d["actions"])
        self.assertNotIn("unpack", d["actions"])
        self.assertNotIn("made-up-reelix-key", repr(d))

    def test_with_the_folder(self):
        def run(container, cmd, user="", timeout=60):
            self.assertEqual(container, "reelix")
            if cmd[0] == "find":
                self.assertEqual(cmd[1], SEASON)
                return 0, FIND_SEASON, ""
            return 0, "/usr/bin/unrar\n", ""
        with mock.patch.object(services, "_api", return_value=QUEUE), mock.patch.object(containers, "available", return_value=True), \
                mock.patch.object(containers, "containers", return_value=[{"id": "1", "name": "reelix"}]), \
                mock.patch.object(queue_files, "run_in", side_effect=run):
            d = queue_files.details(REELIX, "rx-tv", 16)
        self.assertEqual(d["summary"]["verdict"], "archive")
        self.assertEqual(d["archives"]["to_unpack"], 2)
        self.assertEqual(d["suggest"], "unpack")
        self.assertEqual(d["files"][0]["kind_words"], "Archive")


class UnsafeTest(unittest.TestCase):
    def test_only_the_download_own_folder(self):
        u = queue_files.unsafe
        self.assertEqual(u(SEASON, "Old.Show.S02.1080p.BluRay.x264-GROUP"), "")
        self.assertEqual(u("/data/downloads/Show.S01E01.mkv", "Show.S01E01"), "")
        self.assertIn("too near", u("/downloads/Show.S01", "Show.S01"))
        self.assertIn("not named", u("/data/downloads/tv", "Old.Show.S02"))
        self.assertIn("not named", u("/data/downloads/usenet/completed", "Old.Show.S02"))
        self.assertIn("plain", u("/data/downloads/../x/Old.Show.S02", "Old.Show.S02"))
        self.assertIn("plain", u("relative/Old.Show.S02", "Old.Show.S02"))
        self.assertIn("another download", u(SEASON, "Old.Show.S02.1080p.BluRay.x264-GROUP", [SEASON + "/inner"]))


class DeleteTest(unittest.TestCase):
    def setUp(self):
        self.calls, self.runs = [], []
        self.listings = []

    def api(self, service, path, params=None, method="GET", body=None, timeout=10):
        self.calls.append((method, path, params))
        if path == "/queue" and method == "GET":
            return QUEUE
        return None

    def fake_run(self, container, cmd, user="", timeout=60):
        self.runs.append((cmd, user))
        if cmd[0] == "find" and "-printf" in cmd:
            return 0, self.listings.pop(0) if len(self.listings) > 1 else self.listings[0], ""
        return 0, "", ""

    def go(self, block=False, n=16):
        with mock.patch.object(services, "_api", side_effect=self.api), mock.patch.object(containers, "available", return_value=True), \
                mock.patch.object(containers, "containers", return_value=[{"id": "1", "name": "reelix"}]), \
                mock.patch.object(queue_files, "run_in", side_effect=self.fake_run), mock.patch.object(queue_files.time, "sleep"):
            return queue_files.delete(REELIX, "rx-tv", n, block=block, wait=2)

    def test_the_client_deletes_and_starboard_checks(self):
        self.listings = [FIND_SEASON, ""]
        out = self.go(block=True)
        removed = [c for c in self.calls if c[0] == "DELETE"]
        self.assertEqual(removed[0][2], {"remove_from_client": "true", "blocklist": "true", "skip_redownload": "true"})
        self.assertEqual(out["deleted"], 5)
        self.assertEqual(out["freed"], 400_000_290)
        self.assertFalse([r for r in self.runs if r[0][0] == "rm"])
        self.assertIn("blocklist", out["words"])

    def test_what_is_left_is_deleted_by_starboard(self):
        self.listings = [FIND_SEASON, FIND_SEASON, FIND_SEASON, ""]
        out = self.go()
        rm = [r for r in self.runs if r[0][0] == "rm"]
        self.assertEqual(len(rm), 1)
        self.assertEqual(rm[0][1], "1000:1000")
        self.assertTrue(all(p.startswith(SEASON + "/") for p in rm[0][0][3:]))
        self.assertEqual(len(rm[0][0]) - 3, 5)
        self.assertEqual(out["left"], [])
        self.assertIn("5 files deleted", out["words"])

    def test_a_folder_that_is_not_its_own_is_left(self):
        shared = {"items": [dict(QUEUE["items"][0], output_path="/data/downloads/usenet/completed")]}
        self.listings = [FIND_SEASON]
        with mock.patch.object(services, "_api", side_effect=lambda s, p, params=None, method="GET", **k: shared if method == "GET" else None), \
                mock.patch.object(containers, "available", return_value=True), \
                mock.patch.object(containers, "containers", return_value=[{"id": "1", "name": "reelix"}]), \
                mock.patch.object(queue_files, "run_in", side_effect=self.fake_run), mock.patch.object(queue_files.time, "sleep"):
            out = queue_files.delete(REELIX, "rx-tv", 16, wait=2)
        self.assertFalse([r for r in self.runs if r[0][0] == "rm"])
        self.assertEqual(len(out["left"]), 5)
        self.assertIn("did not delete what was left", out["words"])

    def test_when_the_client_cannot_remove_it(self):
        def api(service, path, params=None, method="GET", body=None, timeout=10):
            self.calls.append((method, path, params))
            if method == "DELETE" and params["remove_from_client"] == "true":
                raise services.ServiceError("NZBGet: not found")
            return QUEUE if method == "GET" else None
        self.listings = [FIND_SEASON, FIND_SEASON, FIND_SEASON, ""]
        with mock.patch.object(services, "_api", side_effect=api), mock.patch.object(containers, "available", return_value=True), \
                mock.patch.object(containers, "containers", return_value=[{"id": "1", "name": "reelix"}]), \
                mock.patch.object(queue_files, "run_in", side_effect=self.fake_run), mock.patch.object(queue_files.time, "sleep"):
            out = queue_files.delete(REELIX, "rx-tv", 16, wait=2)
        deletes = [c[2]["remove_from_client"] for c in self.calls if c[0] == "DELETE"]
        self.assertEqual(deletes, ["true", "false"])
        self.assertIn("could not remove it", out["words"])
        self.assertEqual(out["deleted"], 5)


class UnpackTest(unittest.TestCase):
    def test_nested_rounds_then_import(self):
        inner = FIND_SEASON + "f\t50\t1000:1000\tOld.Show.S02E17.1080p.BluRay.x264-GROUP/inner.zip\n"
        listings = [FIND_SEASON, inner, inner]
        runs, calls = [], []

        def run(container, cmd, user="", timeout=60):
            runs.append((cmd, user))
            if cmd[0] == "find":
                return 0, listings.pop(0) if len(listings) > 1 else listings[0], ""
            if cmd[0] == "sh":
                return 0, "/usr/bin/unrar", ""
            return 0, "", ""
        helper = []
        it = item(16)
        with mock.patch.object(queue_files, "run_in", side_effect=run), \
                mock.patch.object(queue_files, "run_helper", side_effect=lambda c, cmd, user="", **k: helper.append((cmd, user)) or (0, "")), \
                mock.patch.object(services, "_api", side_effect=lambda s, p, *a, **k: calls.append(p)):
            queue_files._unpack(it, "reelix", "rx-tv|16", None)
        unrar = [r for r in runs if r[0][:2] == ["unrar", "x"]]
        self.assertEqual(len(unrar), 2)
        self.assertEqual(unrar[0][0][:6], ["unrar", "x", "-o-", "-y", "-idq", "--"])
        self.assertEqual(unrar[0][1], "1000:1000")
        self.assertEqual([r[0][:2] for r in runs if r[0][0] == "unrar"][0], ["unrar", "lb"])  # listed before unpacking
        self.assertEqual([h[0][:2] for h in helper], [["unzip", "-l"], ["unzip", "-n"]])
        self.assertEqual(calls, ["/queue/16/import"])
        job = queue_files.unpack_state("rx-tv", 16)
        self.assertEqual(job["state"], "done")
        self.assertIn("Unpacked 3 archives", job["words"])

    def test_an_archive_that_escapes_the_folder_is_never_unpacked(self):
        runs = []

        def run(container, cmd, user="", timeout=60):
            runs.append(cmd)
            if cmd[0] == "find":
                return 0, FIND_SEASON, ""
            if cmd[0] == "sh":
                return 0, "/usr/bin/unrar", ""
            if cmd[:2] == ["unrar", "lb"]:
                return 0, "Old.Show.S02E17.mkv\n../../config/reelix.db\n", ""
            return 0, "", ""
        with mock.patch.object(queue_files, "run_in", side_effect=run), mock.patch.object(services, "_api"):
            queue_files._unpack(item(16), "reelix", "rx-tv|16c", None)
        job = queue_files._jobs["rx-tv|16c"]
        self.assertEqual(job["state"], "failed")
        self.assertIn("outside the download folder", job["words"])
        self.assertFalse([c for c in runs if c[:2] == ["unrar", "x"]])

    def test_unsafe_entries_and_zip_listing(self):
        self.assertEqual(queue_files.unsafe_entries(["a/b.mkv", "/etc/passwd", "x/../../y", "C:\\x", "..\\y", "ok..mkv"]),
                         ["/etc/passwd", "x/../../y", "C:\\x", "..\\y"])
        listing = ("Archive:  /x/a.zip\n  Length      Date    Time    Name\n---------  ---------- -----   ----\n"
                   "  1000  2026-11-19 10:00   Book One.epub\n   10  2026-11-19 10:00   ../evil.sh\n---------                     -------\n   1010   2 files\n")
        self.assertEqual(queue_files._zip_names(listing), ["Book One.epub", "../evil.sh"])

    def test_a_failed_archive_says_why(self):
        def run(container, cmd, user="", timeout=60):
            if cmd[0] == "find":
                return 0, FIND_SEASON, ""
            if cmd[0] == "sh":
                return 0, "/usr/bin/unrar", ""
            if cmd[:2] == ["unrar", "lb"]:
                return 0, "Old.Show.S02E17.mkv\n", ""
            return 3, "", "CRC failed in the encrypted file\n"
        with mock.patch.object(queue_files, "run_in", side_effect=run), mock.patch.object(services, "_api"):
            queue_files._unpack(item(16), "reelix", "rx-tv|16b", None)
        job = queue_files._jobs["rx-tv|16b"]
        self.assertEqual(job["state"], "failed")
        self.assertIn("CRC failed", job["words"])


class QueueActionTest(unittest.TestCase):
    def test_remove_and_keep_the_files(self):
        calls = []
        with mock.patch.object(services, "_api", side_effect=lambda s, p, params=None, method="GET", **k: calls.append((p, params, method))):
            services.queue_action(SONARR, 3, "remove-keep")
            services.radio_queue_action(REELIX[0], 33, "remove-keep")
        self.assertEqual(calls[0], ("/queue/3", {"removeFromClient": "false", "blocklist": "false"}, "DELETE"))
        self.assertEqual(calls[1], ("/queue/33", {"remove_from_client": "false", "blocklist": "false"}, "DELETE"))


if __name__ == "__main__":
    unittest.main()
