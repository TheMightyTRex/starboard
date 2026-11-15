"""DASH-438: Starboard downloads its pinned Docker helper image when it is missing, and says clearly when it cannot."""

import os
import tempfile
import unittest
from unittest import mock

from starboard import containers, folders, plugins_admin, self_update


class FakeDocker:
    """The Docker API as far as images go: `have` says whether the helper is here, `pull` what a download answers."""

    def __init__(self, have=True, pull=b'{"status":"Downloaded newer image"}\n', reach=True):
        self.have, self.pull, self.reach, self.calls = have, pull, reach, []

    def __call__(self, method, path, body=None, raw=False, timeout=30):
        self.calls.append((method, path.split("?")[0]))
        if not self.reach:
            raise containers.DockerError("Cannot reach Docker: [Errno 2] No such file or directory")
        if path.startswith("/images/") and path.endswith("/json"):
            if not self.have:
                raise containers.DockerError("Docker answered 404: {\"message\":\"No such image: docker@sha256:851f91d2\"}")
            return {"Id": "sha256:abc"}
        if path.startswith("/images/create"):
            if isinstance(self.pull, Exception):
                raise self.pull
            if b'"error"' not in self.pull:
                self.have = True
            return self.pull
        if path.startswith("/containers/create"):
            if not self.have:
                raise containers.DockerError("Docker answered 404: No such image")
            return {"Id": "c1"}
        if path.endswith("/wait"):
            return {"StatusCode": 0}
        if path.endswith("/logs"):
            return b""
        return {}


class EnsureImage(unittest.TestCase):
    def test_present_is_one_local_check_and_no_download(self):
        d = FakeDocker(have=True)
        with mock.patch.object(containers, "docker", d):
            self.assertFalse(containers.ensure_image())
        self.assertEqual([m for m, _ in d.calls], ["GET"])

    def test_missing_is_downloaded_by_its_pinned_digest(self):
        d = FakeDocker(have=False)
        with mock.patch.object(containers, "docker", d):
            self.assertTrue(containers.ensure_image())
        self.assertIn(("POST", "/images/create"), d.calls)
        self.assertTrue(d.have)

    def test_download_refused_in_the_stream_says_what_to_do(self):
        d = FakeDocker(have=False, pull=b'{"error":"toomanyrequests: You have reached your pull rate limit"}\n')
        with mock.patch.object(containers, "docker", d), self.assertRaises(containers.ImageMissing) as e:
            containers.ensure_image()
        self.assertIn("could not download its Docker helper image", str(e.exception))
        self.assertIn("Docker Hub", str(e.exception))
        self.assertIn("pull rate limit", str(e.exception))

    def test_no_network_is_the_same_clear_message(self):
        d = FakeDocker(have=False, pull=containers.DockerError("Cannot reach Docker: timed out"))
        with mock.patch.object(containers, "docker", d), self.assertRaises(containers.ImageMissing) as e:
            containers.ensure_image()
        self.assertTrue(str(e.exception).startswith(containers.HELPER_MISSING))

    def test_docker_out_of_reach_is_not_called_a_missing_image(self):
        d = FakeDocker(reach=False)
        with mock.patch.object(containers, "docker", d), self.assertRaises(containers.DockerError) as e:
            containers.ensure_image()
        self.assertNotIsInstance(e.exception, containers.ImageMissing)


class EveryPlaceThatUsesIt(unittest.TestCase):
    def test_compose_helper_downloads_before_it_creates(self):
        d = FakeDocker(have=False)
        with mock.patch.object(containers, "docker", d):
            code, _ = containers._helper("/srv/stack", "true")
        self.assertEqual(code, 0)
        pulled = d.calls.index(("POST", "/images/create"))
        created = d.calls.index(("POST", "/containers/create"))
        self.assertLess(pulled, created)

    def test_plugin_activation_shows_the_message_as_it_is(self):
        data = tempfile.mkdtemp()
        os.makedirs(os.path.join(data, "plugins", "demo"))
        d = FakeDocker(have=False, pull=b'{"error":"no route to host"}\n')
        with mock.patch.object(containers, "docker", d), mock.patch.object(containers, "available", lambda: True), \
                mock.patch.object(plugins_admin, "host_path", lambda dd, pid: "/srv/data/plugins/demo"), \
                mock.patch.object(plugins_admin, "_prepare_folders", lambda dd, pid: ""), \
                mock.patch.object(plugins_admin, "_prepare_media", lambda dd, pid: ("", None)):
            ok, text = plugins_admin._compose_run(data, "demo", "up -d")
        self.assertFalse(ok)
        self.assertTrue(text.startswith(containers.HELPER_MISSING))
        self.assertNotIn("cannot reach Docker", text)

    def test_app_updates_put_the_message_in_the_job_log(self):
        d = FakeDocker(have=False, pull=b'{"error":"no route to host"}\n')
        found = [{"name": "jellyfin", "image": "jellyfin/jellyfin:latest", "image_id": "sha256:old", "project": "media",
                  "folder": "/srv/stack", "files": ["/srv/stack/compose.yaml"], "service": "jellyfin", "state": "running"}]
        containers._state["job"] = {"started": 0, "finished": False, "log": "", "items": {"jellyfin": {"phase": "queued", "pct": 0}}}
        containers._state["check"] = {}
        with mock.patch.object(containers, "docker", d), mock.patch.object(containers, "containers", lambda: found), \
                mock.patch.object(containers, "_pull", lambda ref, item: None), mock.patch("starboard.logs.event"):
            containers._run(["jellyfin"])
        job = containers._state["job"]
        self.assertEqual(job["items"]["jellyfin"]["phase"], "failed")
        self.assertIn(containers.HELPER_MISSING, job["log"])

    def test_starboard_updates_refuse_with_the_message(self):
        d = FakeDocker(have=False, pull=b'{"error":"no route to host"}\n')
        real = d.__call__

        def docker(method, path, *a, **k):
            if path.startswith(f"/images/{self_update.UPDATER_IMAGE}"):
                raise containers.DockerError("Docker answered 404: No such image")
            return real(method, path, *a, **k)
        with mock.patch.object(containers, "docker", docker), self.assertRaises(self_update.Refused) as e:
            self_update._build_updater()
        self.assertIn("could not download its Docker helper image", str(e.exception))

    def test_folder_picker_says_why_it_cannot_look(self):
        d = FakeDocker(have=False, pull=b'{"error":"no route to host"}\n')
        with mock.patch.object(containers, "docker", d):
            out = folders._via_helper("/mnt/disk1/media")
        self.assertIsNone(out["exists"])
        self.assertIn("Docker helper image", out["why"])

    def test_backups_download_it_first(self):
        from starboard import full_backup
        d = FakeDocker(have=False)
        with mock.patch.object(containers, "docker", d):
            code, _ = full_backup._helper("true", [])
        self.assertEqual(code, 0)
        self.assertIn(("POST", "/images/create"), d.calls)


if __name__ == "__main__":
    unittest.main()
