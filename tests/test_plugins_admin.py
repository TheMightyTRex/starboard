"""Settings, Plug-ins (DASH-149): add, settings, enable, disable, Stop all and remove, with a stand-in Docker."""
import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import api_v1, plugins_admin as pa
from tests.test_plugins import ON_DEMAND


class PluginsAdminTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runs = []
        p = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/starboard/data/plugins/{pid}")
        p.start()
        self.addCleanup(p.stop)

    def helper(self, ok=True):
        def run(folder, script):
            self.runs.append((folder, script))
            return (0 if ok else 1), ("" if ok else "Error: no such image")
        return run

    def test_add_makes_its_folder_key_and_compose_file(self):
        item = pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        self.assertEqual((item["id"], item["state"]), ("on-demand", "installed"))
        where = pa.folder(self.tmp.name, "on-demand")
        with open(os.path.join(where, "key")) as f:
            key = f.read()
        self.assertTrue(key.startswith("sb_read_"))
        self.assertEqual(oct(os.stat(os.path.join(where, "key")).st_mode & 0o777), "0o600")
        made = api_v1.find_key(self.tmp.name, f"Bearer {key}")
        self.assertEqual(made["scopes"], ["media"])
        with open(os.path.join(where, "settings.json")) as f:
            self.assertEqual(json.load(f), {"quality": "1080p", "min_seeders": 5})
        with self.assertRaisesRegex(ValueError, "already added"):
            pa.install(self.tmp.name, ON_DEMAND, "/srv/media")

    def test_a_missing_media_folder_is_made_for_the_user_it_runs_as(self):  # API 1.12 (DASH-410)
        os.makedirs(os.path.join(self.tmp.name, "stack"), exist_ok=True)
        with open(os.path.join(self.tmp.name, "stack", ".env"), "w") as f:
            f.write("PUID=1001\nPGID=1002\nDATA_DIR=/srv/data\n")
        m = {**ON_DEMAND, "id": "tracks", "permissions": ["network:lan"],
             "containers": [{"name": "main", "image": ON_DEMAND["containers"][0]["image"], "network": "lan",
                             "volumes": ["data", "media/movies", "media/audio-description"], "user": "media"}], "resources": {}}
        with mock.patch("starboard.stack.folder", side_effect=lambda d: os.path.join(d, "stack")):
            self.assertEqual(pa.media_owner(self.tmp.name), "1001:1002")
            pa.install(self.tmp.name, m, "/srv/data/media")
            with open(os.path.join(pa.folder(self.tmp.name, "tracks"), "compose.yaml")) as f:
                self.assertIn('user: "1001:1002"', f.read())
            seen = []
            pa._compose_run(self.tmp.name, "tracks", "up -d", helper=lambda folder, script, binds=(): seen.append((script, binds)) or (0, ""))
        script, binds = seen[0]
        self.assertIn("[ -d '/srv/data/media/audio-description' ] || { mkdir -p '/srv/data/media/audio-description' && chown 1001:1002", script)
        self.assertEqual(binds, ["/srv/data/media:/srv/data/media"])
        self.assertIn("chown 1001:1002 'data/main'", script)  # its own data folder belongs to the same user
        # A plug-in with no folder in the media folder shows the helper nothing more.
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        with mock.patch.object(pa, "media_host_dir", return_value=None):
            pa._compose_run(self.tmp.name, "on-demand", "up -d", helper=self.helper())
        self.assertNotIn("mkdir -p '/srv", self.runs[-1][1])
    def test_a_folder_outside_the_plugins_folder_is_refused(self):
        base = os.path.join(self.tmp.name, "plugins")
        self.assertEqual(pa.folder(self.tmp.name, "on-demand"), os.path.join(base, "on-demand"))
        for bad in ("../etc", "..", "on-demand/../../x", "/etc/passwd", "a/b", "", None, ".removed"):
            with self.assertRaises(ValueError):
                pa.folder(self.tmp.name, bad)
        with self.assertRaises(ValueError):
            pa.uninstall(self.tmp.name, "../../outside")
        with mock.patch.object(pa.plugins, "ID", r"^.+$"):  # the second check holds even if the id pattern did not
            for bad in ("../etc", "..", "a/../../b", "a/b"):
                with self.assertRaises(ValueError):
                    pa.folder(self.tmp.name, bad)

    def test_a_bad_manifest_is_refused_with_its_problems(self):
        with self.assertRaisesRegex(ValueError, "Unknown field privileged"):
            pa.install(self.tmp.name, {**ON_DEMAND, "privileged": True}, "/srv/media")

    def test_settings_are_checked_and_secrets_never_shown(self):
        m = {**ON_DEMAND, "settings": ON_DEMAND["settings"] + [{"key": "token", "label": "Token", "type": "secret"}]}
        pa.install(self.tmp.name, m, "/srv/media")
        out = pa.save_settings(self.tmp.name, "on-demand", {"min_seeders": 10, "token": "made-up-token"})
        token = next(s for s in out if s["key"] == "token")
        self.assertEqual((token["value"], token["set"]), (None, True))
        for bad in ({"min_seeders": 500}, {"quality": "8K"}, {"made_up": 1}, {"catalogues": {}}):
            with self.assertRaises(ValueError):
                pa.save_settings(self.tmp.name, "on-demand", bad)
        pa.save_settings(self.tmp.name, "on-demand", {"token": ""})  # empty keeps it
        with open(os.path.join(pa.folder(self.tmp.name, "on-demand"), "settings.json")) as f:
            self.assertEqual(json.load(f)["token"], "made-up-token")

    def test_enable_disable_stop_all_and_remove(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        pa.enable(self.tmp.name, "on-demand", self.helper())
        self.assertIn("up -d", self.runs[-1][1])
        self.assertIn("docker network connect", self.runs[-1][1])
        self.assertEqual(pa.listing(self.tmp.name)[0]["state"], "enabled")
        self.assertEqual(pa.stop_all(self.tmp.name, self.helper()), ["On demand"])
        self.assertEqual(pa.listing(self.tmp.name)[0]["state"], "disabled")
        with self.assertRaisesRegex(ValueError, "did not start"):
            pa.enable(self.tmp.name, "on-demand", self.helper(ok=False))
        self.assertEqual(pa.listing(self.tmp.name)[0]["state"], "failed")
        key_file = os.path.join(pa.folder(self.tmp.name, "on-demand"), "key")
        with open(key_file) as f:
            key = f.read()
        kept = pa.uninstall(self.tmp.name, "on-demand", self.helper())
        self.assertTrue(os.path.isdir(kept) and "/.removed/on-demand-" in kept)
        self.assertEqual(pa.listing(self.tmp.name), [])
        self.assertIsNone(api_v1.find_key(self.tmp.name, f"Bearer {key}"))

    def test_a_failed_start_is_not_hidden_by_the_script(self):
        import subprocess
        import tempfile as tf
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        scripts = []
        pa._compose_run(self.tmp.name, "on-demand", "up -d", lambda folder, script: (scripts.append(script) or (0, "")))
        with tf.TemporaryDirectory() as bin_dir:
            fake = os.path.join(bin_dir, "docker")
            with open(fake, "w") as f:
                f.write("#!/bin/sh\necho 'Error: pull access denied'\nexit 1\n")
            os.chmod(fake, 0o755)
            # The helper runs as root; chown stands in, so the test runs the same as any user (GitHub's runner is
            # not user 1000), in a folder of its own.
            chown = os.path.join(bin_dir, "chown")
            with open(chown, "w") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(chown, 0o755)
            with tf.TemporaryDirectory() as work:
                r = subprocess.run(["sh", "-c", scripts[0]], env={"PATH": f"{bin_dir}:/usr/bin:/bin"}, cwd=work, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pull access denied", r.stdout)

    def test_starting_makes_the_data_folder_for_the_plugins_user(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        scripts = []
        pa._compose_run(self.tmp.name, "on-demand", "up -d", lambda folder, script: (scripts.append(script) or (0, "")))
        self.assertIn("mkdir -p 'data/main' && chown 1000:1000 'data/main' && chmod 700 'data/main'", scripts[0])
        self.assertIn("mkdir -p 'data/engine' && chown 1000:1000 'data/engine'", scripts[0])
        pa._compose_run(self.tmp.name, "on-demand", "stop", lambda folder, script: (scripts.append(script) or (0, "")))
        self.assertNotIn("chown", scripts[1])

    def test_no_docker_access_says_so(self):
        pa.install(self.tmp.name, ON_DEMAND, "/srv/media")
        with mock.patch("starboard.containers.available", return_value=False):
            with self.assertRaisesRegex(ValueError, "no access to Docker"):
                pa.enable(self.tmp.name, "on-demand")

    def test_preview_from_an_address_is_checked(self):
        with self.assertRaises(ValueError):
            pa.fetch_manifest("http://example.invalid/starboard-plugin.json")
        with self.assertRaises(ValueError):
            pa.fetch_manifest("https://169.254.169.254/x.json")
        self.assertEqual(pa.summary(ON_DEMAND)["problems"], [])


if __name__ == "__main__":
    unittest.main()
