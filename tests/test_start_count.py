"""Downloading and starting the apps shows how far it has got after the timer: "5 of 12 installed", then
"12 of 12 running", from Docker itself (stack.progress)."""

import os
import tempfile
import unittest
from unittest import mock

from starboard import containers, stack

COMPOSE = """# Written by Starboard
services:
  sonarr:
    image: lscr.io/linuxserver/sonarr:latest
    container_name: sonarr
  jellyfin:
    image: jellyfin/jellyfin
    container_name: jellyfin
  jellystat-db:
    image: postgres:16
    container_name: jellystat-db
  storyarr-db:
    image: postgres:16
    container_name: storyarr-db
  later-app:
    image: example/later:1
    container_name: later-app
    profiles: ["later"]  # needs its own settings file first
networks:
  default:
    name: media
"""


class StartCountTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(stack.folder(self.tmp.name), exist_ok=True)
        with open(os.path.join(stack.folder(self.tmp.name), "compose.yaml"), "w") as f:
            f.write(COMPOSE)

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self, images, running):
        def docker(method, path, **kw):
            return [{"RepoTags": [t]} for t in images] if path.startswith("/images") else \
                [{"Labels": {"com.docker.compose.service": n}} for n in running]
        return mock.patch.object(containers, "docker", side_effect=docker)

    def test_apps_that_start_now_are_counted_and_later_ones_are_not(self):
        self.assertEqual([n for n, _ in stack._services(self.tmp.name)], ["sonarr", "jellyfin", "jellystat-db", "storyarr-db"])

    def test_installed_counts_each_app_and_an_untagged_image_is_latest(self):
        with self.fake(["jellyfin/jellyfin:latest", "postgres:16"], []):
            self.assertEqual(stack.progress(self.tmp.name), {"total": 4, "installed": 3, "running": 0})

    def test_running_comes_from_the_project_containers(self):
        with self.fake(["lscr.io/linuxserver/sonarr:latest", "jellyfin/jellyfin:latest", "postgres:16"], ["sonarr", "jellyfin"]):
            self.assertEqual(stack.progress(self.tmp.name), {"total": 4, "installed": 4, "running": 2})

    def test_nothing_when_docker_cannot_be_asked_or_there_is_no_file(self):
        with mock.patch.object(containers, "docker", side_effect=containers.DockerError("no access")):
            self.assertIsNone(stack.progress(self.tmp.name))
        self.assertIsNone(stack.progress(os.path.join(self.tmp.name, "none")))


if __name__ == "__main__":
    unittest.main()
