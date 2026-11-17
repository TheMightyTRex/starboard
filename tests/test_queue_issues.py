"""Copy issues for an AI helper (DASH-434): what is gathered, what is taken out, and the Markdown."""
import datetime as dt
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import queue_issues, services

NOW = dt.datetime(2026, 11, 15, 12, 0, tzinfo=dt.timezone.utc)
SONARR = {"id": "tv", "name": "Example TV", "type": "sonarr", "url": "http://sonarr:8989", "api_key": "made-up-sonarr-key-1234"}
NZBGET = {"id": "nzb", "name": "NZBGet", "type": "nzbget", "url": "http://nzbget:6789", "api_key": "nzbuser:made-up-nzb-password"}
REELIX = [{"id": "rx", "name": "Reelix", "type": "link", "icon": "reelix", "url": "http://reelix:7878", "api_key": "made-up-reelix-key-5678"},
          {"id": "rx-tv", "name": "Reelix TV", "type": "sonarr", "icon": "reelix", "url": "http://reelix:7878/sonarr", "api_key": "made-up-reelix-key-5678"}]

SECRETS = ["made-up-sonarr-key-1234", "made-up-nzb-password", "made-up-reelix-key-5678", "made-up-indexer-key-9c1e",
           "made-up-passkey-77", "made-up-bearer-abcdef", "192.168.1.20", "10.0.0.5", "fe80::1", "nas.local", "someone@example.com",
           "/home/someone", "SECRETRSS42", "made-up-cookie-value"]

ARR_QUEUE = {"records": [
    {"id": 1, "title": "Fine.Show.S01E01", "size": 100, "sizeleft": 50, "status": "downloading", "trackedDownloadState": "downloading"},
    {"id": 3, "title": "Old.Show.S05E01", "size": 3 * 1024 ** 3, "sizeleft": 0, "status": "completed", "trackedDownloadState": "importPending",
     "trackedDownloadStatus": "warning", "added": "2026-11-14T09:00:00Z", "indexer": "Harbour Usenet", "protocol": "usenet",
     "downloadClient": "NZBGet", "downloadId": "nzb-ex-0003", "outputPath": "/data/downloads/complete/Old.Show.S05E01",
     "seriesId": 1, "episodeId": 501, "seasonNumber": 5, "quality": {"quality": {"name": "HDTV-1080p"}},
     "series": {"title": "Old Show"}, "episode": {"seasonNumber": 5, "episodeNumber": 1, "title": "The Return"},
     "statusMessages": [{"title": "Old.Show.S05E01", "messages": ["No files found are eligible for import"]}]},
    {"id": 4, "title": "Example.Show.S02E04", "size": 2000, "sizeleft": 1000, "status": "failed", "trackedDownloadState": "failedPending",
     "trackedDownloadStatus": "error", "added": "2026-11-12T21:15:00Z", "indexer": "Lighthouse Torrents", "protocol": "torrent",
     "downloadClient": "qBittorrent", "downloadId": "8F0C2A4E9B1D7C3A5E6F8091A2B3C4D5E6F70812", "outputPath": "/home/someone/private/incomplete",
     "errorMessage": "Download failed: http://192.168.1.20:9696/1/api?t=get&apikey=made-up-indexer-key-9c1e",
     "statusMessages": [{"title": "Example.Show.S02E04", "messages": [
         "Tracker said: passkey=made-up-passkey-77 is not registered",
         "Sonarr used the key made-up-sonarr-key-1234 and NZBGet's made-up-nzb-password",
         "Authorization: Bearer made-up-bearer-abcdef at 10.0.0.5:8080 and fe80::1 and nas.local:5000",
         "magnet:?xt=urn:btih:abc&tr=udp://tracker.example:1337&dn=x",
         "Feed https://feeds.example.org/rss/rsskey/SECRETRSS42/feed.xml from someone@example.com",
         "Cookie: made-up-cookie-value"]}]},
]}

REELIX_QUEUE = {"items": [
    {"id": 32, "title": "Fine.Film.2025", "state": "downloading", "client_state": "downloading", "progress": 0.5, "messages": []},
    {"id": 33, "title": "Sample.Science.Weekly.3.mp3", "download_client": "NZBGet", "download_client_id": 2, "download_id": "nzb-ex-0033",
     "protocol": "usenet", "state": "import_pending", "client_state": "completed", "progress": 1.0, "size": 48_000_000, "indexer": "Harbour Usenet",
     "messages": ["No audio files were found in /data/downloads/complete/Sample.Science.Weekly.3"], "output_path": "/data/downloads/complete/Sample.Science.Weekly.3",
     "added": "2026-11-15T07:30:00Z", "media": {"kind": "radio_episode", "id": 203, "title": "Ask a scientist 3", "subtitle": "Sample Science Weekly", "show_id": 2}},
    {"id": 34, "title": "Some.Series.S01E02", "state": "failed_pending", "client_state": "failed", "progress": 0.2, "size": 1000,
     "messages": ["Episodes are not part of the series"], "media": {"kind": "series", "id": 8, "title": "Some Series"},
     "episodes": [{"id": 81, "season_number": 1, "episode_number": 2}], "added": "2026-11-15T11:00:00Z"},
]}


def fake_api(service, path, params=None, **kw):
    if service.get("type") == "link":
        return REELIX_QUEUE
    if service["id"] == "rx-tv":
        raise AssertionError("Reelix's Sonarr-style address is asked when its own queue is read")
    return ARR_QUEUE


class GatherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        services.forget()
        self.addCleanup(services.forget)  # nothing made up here is left for other tests' shared answers
        patcher = mock.patch.object(services, "_api", side_effect=fake_api)
        self.api = patcher.start()
        self.addCleanup(patcher.stop)

    def gather(self, stuck=None):
        return queue_issues.gather([SONARR, NZBGET] + REELIX, self.tmp.name, stuck, NOW)

    def test_only_downloads_that_need_attention_or_failed(self):
        out = self.gather()
        self.assertEqual(out["count"], 4)
        self.assertEqual(out["apps_asked"], 2)  # Example TV and Reelix's own queue, not Reelix TV as well
        titles = [i["title"] for i in out["items"]]
        self.assertNotIn("Fine.Show.S01E01", titles)
        self.assertNotIn("Fine.Film.2025", titles)
        self.assertEqual([i["status"] for i in out["items"]][:2], ["Failed", "Failed"])  # failed first

    def test_full_details(self):
        old = next(i for i in self.gather()["items"] if i["title"] == "Old.Show.S05E01")
        self.assertEqual(old["app"], "Example TV")
        self.assertEqual(old["what"], "Old Show S05E01 · The Return")
        self.assertEqual(old["app_state"], {"status": "completed", "tracked_state": "importPending", "tracked_status": "warning"})
        self.assertEqual(old["messages"], ["No files found are eligible for import"])
        self.assertEqual((old["indexer"], old["protocol"], old["quality"], old["download_client"]), ("Harbour Usenet", "usenet", "HDTV-1080p", "NZBGet"))
        self.assertEqual(old["download_client_ids"], {"download_id": "nzb-ex-0003"})
        self.assertEqual(old["paths"], {"output": "/data/downloads/complete/Old.Show.S05E01"})
        self.assertEqual(old["ids"], {"queue": 3, "series": 1, "episode": 501, "season number": 5})
        self.assertEqual(old["age"], "1 day 3 hours")
        self.assertEqual(old["progress"], 100)

    def test_reelix_ids_and_paths(self):
        radio = next(i for i in self.gather()["items"] if i["ids"]["queue"] == 33)
        self.assertTrue(radio["reelix"])
        self.assertEqual(radio["ids"], {"queue": 33, "radio episode": 203, "radio show": 2})
        self.assertEqual(radio["download_client_ids"], {"download_id": "nzb-ex-0033", "client_id_in_reelix": 2})
        self.assertEqual(radio["what"], "Sample Science Weekly · Ask a scientist 3")
        series = next(i for i in self.gather()["items"] if i["ids"]["queue"] == 34)
        self.assertEqual(series["ids"]["episodes"], [81])
        self.assertEqual(series["status"], "Failed")

    def test_scrubs_keys_passwords_tokens_and_private_addresses(self):
        out = self.gather()
        text = json.dumps(out) + queue_issues.markdown(out)
        for s in SECRETS:
            self.assertNotIn(s, text, s)
        failed = next(i for i in out["items"] if i["title"] == "Example.Show.S02E04")
        self.assertEqual(failed["paths"], {}, "a home folder is never shown")
        self.assertIn("8F0C2A4E9B1D7C3A5E6F8091A2B3C4D5E6F70812", text)  # the download client's id stays
        self.assertIn("[magnet link removed]", text)
        self.assertIn("https://feeds.example.org/[rest of the address removed]", text)
        self.assertIn("gluetun", queue_issues.clean("at gluetun:8080"))  # a container's name is not private

    def test_clean_and_path(self):
        self.assertEqual(queue_issues.clean("time 00:12:00, Sonarr 4.0.16.2944"), "time 00:12:00, Sonarr 4.0.16.2944")
        self.assertEqual(queue_issues.clean("from http://reelix:7878/api/v1/x?apikey=abc"), "from [private address]")
        self.assertEqual(queue_issues.clean("C:\\Users\\Someone\\Downloads"), "C:\\Users\\[user]\\Downloads")
        self.assertIsNone(queue_issues.path("/config/logs"))
        self.assertIsNone(queue_issues.path("relative/folder"))
        self.assertEqual(queue_issues.path("/downloads/complete/x"), "/downloads/complete/x")

    def test_what_starboard_tried(self):
        services._cache["queue"] = (1e12, {"items": [{"service": "rx-tv", "id": 34, "download_id": "", "title": "Some.Series.S01E02"}]}, 10)
        queue_issues.note_action(self.tmp.name, "rx-tv", 34, "import")
        queue_issues.note_tried(self.tmp.name, "Chose the episode by hand", "rx", None, "nzb-ex-0033")
        out = self.gather({"Example TV|Old.Show.S05E01": NOW.timestamp() - 3600})
        by = {i["ids"]["queue"]: i["tried"] for i in out["items"]}
        self.assertEqual([t["what"] for t in by[34]], ["Asked Reelix to try the import again, from the Downloads page"])
        self.assertEqual([t["what"] for t in by[33]], ["Chose the episode by hand"])
        self.assertIn("The watch has found it needing attention", by[3][0]["what"])
        self.assertEqual(by[4], [])
        with open(os.path.join(self.tmp.name, queue_issues.TRIED_FILE)) as f:
            self.assertEqual(len(json.load(f)["items"]), 2)

    def test_tried_keeps_the_newest(self):
        for n in range(queue_issues.TRIED_KEEP + 5):
            queue_issues.note_tried(self.tmp.name, f"try {n}", "tv", n)
        rows = queue_issues._tried_load(self.tmp.name)
        self.assertEqual(len(rows), queue_issues.TRIED_KEEP)
        self.assertEqual(rows[-1]["what"], f"try {queue_issues.TRIED_KEEP + 4}")

    def test_markdown_has_the_prompt_and_each_issue(self):
        md = queue_issues.markdown(self.gather(), "0.19.0")
        self.assertTrue(md.startswith("# Download issues from Starboard\n"))
        for words in ("Diagnose the issue", "most likely cause", "fix to try first", "what to check", "Ask me before suggesting anything that deletes files"):
            self.assertIn(words, md)
        self.assertIn("4 downloads from 2 apps", md)
        self.assertEqual(md.count("\n## "), 4)
        self.assertIn("- **Reelix ids:** queue 33, radio episode 203, radio show 2", md)
        self.assertIn("- **Ids in Example TV:** queue 3, series 1, episode 501, season number 5", md)
        self.assertIn("**Paths, inside the container:** output `/data/downloads/complete/Old.Show.S05E01`", md)
        self.assertIn("none given, or outside the media folders", md)
        self.assertIn("- **What Starboard already tried:** nothing yet", md)
        self.assertNotIn("—", md)

    def test_empty_and_apps_that_did_not_answer(self):
        def down(service, path, params=None, **kw):
            if service.get("type") == "link":
                raise services.ServiceError("Cannot reach Reelix at http://192.168.1.20:7878")
            return {"records": [ARR_QUEUE["records"][0]]}
        self.api.side_effect = down
        out = self.gather()
        self.assertEqual(out["count"], 0)
        md = queue_issues.markdown(out)
        self.assertIn("Nothing in the queue needs attention or failed", md)
        self.assertIn("did not answer", md)
        self.assertNotIn("192.168.1.20", md)
        self.assertNotIn("Diagnose", md)

    def test_asked_only_when_called_and_at_most_every_10_seconds(self):
        app = mock.Mock(data_dir=self.tmp.name, version="0.19.0", watch=mock.Mock(state={}))
        app.config.data = {"services": [SONARR]}
        first = queue_issues.export(app)
        calls = self.api.call_count
        queue_issues.export(app)
        self.assertEqual(self.api.call_count, calls, "a second call within 10 seconds is answered from the first")
        services.forget("queue-issues")  # after 10 seconds, or Copy pressed again after half a second, it asks again
        queue_issues.export(app, fresh=True)
        self.assertGreater(self.api.call_count, calls)
        self.assertIn("markdown", first)


if __name__ == "__main__":
    unittest.main()
