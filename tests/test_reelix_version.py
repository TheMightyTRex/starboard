"""Which exact Reelix Starboard installed (DASH-419)."""
import datetime as dt
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import changes, reelix_version, stack

LABELS = {"io.github.themightytrex.reelix.tag": "full-0.8.7-trex.2", "io.github.themightytrex.reelix.edition": "full",
          "org.opencontainers.image.version": "0.8.7", "org.opencontainers.image.revision": "abc123"}
IMAGE = {"Id": "sha256:new", "Config": {"Labels": LABELS},
         "RepoDigests": ["ghcr.io/themightytrex/reelix@sha256:d1"]}
OLD = {"Id": "sha256:old", "Config": {"Labels": {"org.opencontainers.image.version": "0.8.6"}},
       "RepoDigests": ["ghcr.io/themightytrex/reelix@sha256:d0"]}
WHEN = dt.datetime(2026, 11, 15, 9, 0, tzinfo=dt.timezone.utc)


def fake_docker(image_ref, image):
    def docker(method, path, *a, **k):
        if path.startswith("/containers/json"):
            assert "filters=" in path  # one container asked for, not every one
            return [{"Names": ["/reelix"], "Image": image_ref, "ImageID": image["Id"]}]
        if path.startswith("/images/"):
            return image
        raise AssertionError(path)
    return docker


class Tags(unittest.TestCase):
    def test_parse_tag(self):
        self.assertEqual(reelix_version.parse_tag("lite-0.8.7-trex.1"), ("lite", "0.8.7", 1))
        self.assertEqual(reelix_version.parse_tag("full-0.10.0-trex.12"), ("full", "0.10.0", 12))
        for t in ("lite", "full", "0.8.6-lite", "lite-0.8.7", "lite-0.8.7-trex.", "beta-0.8.7-trex.1", None):
            self.assertIsNone(reelix_version.parse_tag(t))

    def test_edition_of_version_tags(self):
        self.assertEqual(stack.edition_of("ghcr.io/themightytrex/reelix:lite-0.8.7-trex.1"), "lite")
        self.assertEqual(stack.edition_of("ghcr.io/themightytrex/reelix:full-0.8.7-trex.1"), "full")
        self.assertEqual(stack.edition_of("ghcr.io/themightytrex/reelix:0.8.6-lite"), "lite")
        self.assertEqual(stack.edition_of("ghcr.io/themightytrex/reelix:lite"), "lite")
        self.assertEqual(stack.edition_of("ghcr.io/themightytrex/reelix:full"), "full")

    def test_changelog_follows_the_edition(self):
        self.assertIn("/fork/lite/", changes.source("ghcr.io/themightytrex/reelix:lite-0.8.7-trex.1")[1])
        self.assertIn("/master/", changes.source("ghcr.io/themightytrex/reelix:full-0.8.7-trex.1")[1])


class Describe(unittest.TestCase):
    def test_labelled_image(self):
        d = reelix_version.describe("ghcr.io/themightytrex/reelix:full", IMAGE)
        self.assertEqual((d["edition"], d["version"], d["tag"], d["revision"], d["digest"]),
                         ("full", "0.8.7", "full-0.8.7-trex.2", "abc123", "sha256:d1"))
        self.assertEqual(reelix_version.exact_image(d), "ghcr.io/themightytrex/reelix:full-0.8.7-trex.2")
        self.assertEqual(reelix_version.label(d), "full-0.8.7-trex.2")

    def test_image_from_before_the_tags_is_named_by_digest(self):
        d = reelix_version.describe("ghcr.io/themightytrex/reelix:lite", OLD)
        self.assertEqual((d["edition"], d["version"], d["tag"]), ("lite", "0.8.6", ""))
        self.assertEqual(reelix_version.exact_image(d), "ghcr.io/themightytrex/reelix@sha256:d0")
        self.assertEqual(reelix_version.label(d), "0.8.6 (Lite, sha256:d0)")

    def test_pinned_tag_without_labels(self):
        d = reelix_version.describe("ghcr.io/themightytrex/reelix:lite-0.8.7-trex.3", {"Id": "sha256:x"})
        self.assertEqual((d["edition"], d["version"], d["tag"]), ("lite", "0.8.7", "lite-0.8.7-trex.3"))

    def test_a_made_up_tag_label_is_ignored(self):
        bad = {"Id": "sha256:x", "Config": {"Labels": {"io.github.themightytrex.reelix.tag": "x; rm -rf /"}}}
        self.assertEqual(reelix_version.describe("ghcr.io/themightytrex/reelix:full", bad)["tag"], "")

    def test_no_reelix_container(self):
        self.assertIsNone(reelix_version.running(lambda *a, **k: []))
        self.assertIsNone(reelix_version.exact_image(None))


class Record(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_nothing_noted_yet(self):
        self.assertEqual(reelix_version.read(self.tmp.name), {"current": None, "history": []})

    def test_install_then_update_keeps_the_one_before(self):
        old = reelix_version.describe("ghcr.io/themightytrex/reelix:lite", OLD)
        new = reelix_version.describe("ghcr.io/themightytrex/reelix:full", IMAGE)
        self.assertEqual(reelix_version.record(self.tmp.name, old, "install", now=WHEN)["how"], "install")
        noted = reelix_version.record(self.tmp.name, new, "update", now=WHEN)
        self.assertEqual(noted["at"], "2026-11-15T09:00:00+00:00")
        data = reelix_version.read(self.tmp.name)
        self.assertEqual(data["current"]["tag"], "full-0.8.7-trex.2")
        self.assertEqual([e["image_id"] for e in data["history"]], ["sha256:old"])

    def test_the_same_build_is_noted_once(self):
        new = reelix_version.describe("ghcr.io/themightytrex/reelix:full", IMAGE)
        self.assertIsNotNone(reelix_version.record(self.tmp.name, new, "install"))
        self.assertIsNone(reelix_version.record(self.tmp.name, new, "seen"))
        self.assertEqual(reelix_version.read(self.tmp.name)["history"], [])

    def test_history_is_capped(self):
        for n in range(reelix_version.KEEP + 5):
            reelix_version.record(self.tmp.name, {"image_id": f"sha256:{n}", "image": "x", "tag": "", "digest": ""}, "update")
        data = reelix_version.read(self.tmp.name)
        self.assertEqual(data["current"]["image_id"], f"sha256:{reelix_version.KEEP + 4}")
        self.assertEqual(len(data["history"]), reelix_version.KEEP)

    def test_unknown_how_is_refused(self):
        with self.assertRaises(ValueError):
            reelix_version.record(self.tmp.name, {}, "guess")

    def test_a_damaged_file_reads_as_nothing(self):
        with open(os.path.join(self.tmp.name, reelix_version.FILE), "w", encoding="utf-8") as f:
            f.write("{not json")
        self.assertEqual(reelix_version.read(self.tmp.name)["current"], None)

    def test_note_reads_the_running_container(self):
        docker = fake_docker("ghcr.io/themightytrex/reelix:full", IMAGE)
        with mock.patch("starboard.logs.event") as event:
            noted = reelix_version.note(self.tmp.name, "install", docker=docker)
        self.assertEqual(noted["tag"], "full-0.8.7-trex.2")
        self.assertIn("full-0.8.7-trex.2", event.call_args[0][2])
        with open(os.path.join(self.tmp.name, reelix_version.FILE), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["current"]["digest"], "sha256:d1")

    def test_note_never_raises(self):
        def broken(*a, **k):
            raise OSError("Docker is not answering")
        with mock.patch("starboard.logs.event") as event:
            self.assertIsNone(reelix_version.note(self.tmp.name, "update", docker=broken))
        self.assertEqual(event.call_args[0][0], "warning")

    def test_note_when_started_waits_for_the_install(self):
        states = iter([{"finished": False}, {"finished": True}])
        with mock.patch("starboard.stack.job", side_effect=lambda d: next(states)), \
                mock.patch.object(reelix_version, "note") as note:
            reelix_version.note_when_started(self.tmp.name, "switch", sleep=lambda s: None).join(5)
        note.assert_called_once_with(self.tmp.name, "switch")


if __name__ == "__main__":
    unittest.main()
