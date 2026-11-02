"""Updates for an image pinned to a version: newer releases are found, also from a test build (v0.4.9-dev.6)
that is not in the registry."""

import io
import json
import unittest
import urllib.error
from unittest import mock

from starboard import containers

TAGS = ["latest", "edge", "candidate-1", "v0.4.8", "v0.4.9", "v0.5.8", "v0.6.0-dev.1"]


def registry(reg, repo, path, accept=None):
    if path.startswith("tags/list"):
        return {}, json.dumps({"tags": TAGS}).encode()
    raise urllib.error.HTTPError(path, 404, "Not Found", {}, io.BytesIO())  # the running tag is a local build


class PinnedTest(unittest.TestCase):
    def test_newest_release_after_a_version(self):
        with mock.patch.object(containers, "_registry", registry):
            self.assertEqual(containers.newer_pinned("ghcr.io/example/app:v0.4.8"), "v0.5.8")
            self.assertIsNone(containers.newer_pinned("ghcr.io/example/app:v0.5.8"))
            self.assertIsNone(containers.newer_pinned("ghcr.io/example/app:latest"))

    def test_a_test_build_is_older_than_its_release(self):
        with mock.patch.object(containers, "_registry", registry):
            self.assertEqual(containers.newer_pinned("ghcr.io/example/app:v0.4.9-dev.6"), "v0.5.8")
            with mock.patch.object(containers, "_registry", lambda *a, **k: ({}, json.dumps({"tags": ["v0.4.9"]}).encode())):
                self.assertEqual(containers.newer_pinned("ghcr.io/example/app:v0.4.9-dev.6"), "v0.4.9")

    def test_a_build_missing_from_the_registry_still_offers_the_release(self):
        c = {"image": "ghcr.io/example/app:v0.4.9-dev.6", "version": "", "digests": []}
        with mock.patch.object(containers, "_registry", registry):
            out = containers._check_one(c)
        self.assertEqual((out["latest"], out["update"], out.get("target_tag")), ("v0.5.8", True, "v0.5.8"))
        with mock.patch.object(containers, "_registry", lambda *a, **k: ({}, json.dumps({"tags": []}).encode()) if "tags" in a[2] else registry(*a)):
            self.assertIn("local or test build", containers._check_one(c)["error"])


if __name__ == "__main__":
    unittest.main()
