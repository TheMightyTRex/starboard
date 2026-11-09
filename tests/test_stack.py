"""Install apps: the Compose file it writes, the folders it accepts, and the password before Start."""

import json
import os
import tempfile
import unittest
from unittest import mock

from starboard import stack

CHOICE = {"apps": ["radarr", "qbittorrent", "gluetun", "storyarr", "unpackerr"], "config_dir": "/srv/stack/config",
          "data_dir": "/srv/media", "puid": 1000, "pgid": 1000, "tz": "Europe/London",
          "vpn": {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "secret+key=",
                  "wireguard_addresses": "10.0.0.2/32", "openvpn_user": "not-used"}}


class StackTest(unittest.TestCase):
    def setUp(self):
        image = mock.patch.dict(stack.APPS["storyarr"], {"image": "example/storyarr:1"})
        image.start()
        self.addCleanup(image.stop)
        patcher = mock.patch.object(stack, "_port_free", lambda port: True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_vpn_apps_go_through_gluetun_and_publish_its_ports(self):
        b = stack.build(CHOICE)
        q = b["compose"].split("  qbittorrent:")[1].split("\n  gluetun:")[0]
        self.assertIn('network_mode: "service:gluetun"', q)
        self.assertNotIn("ports:", q)
        self.assertIn('"8080:8080"', b["compose"].split("  gluetun:")[1].split("\n  storyarr:")[0])

    def test_reelix_waits_for_the_vpn_to_be_ready(self):
        b = stack.build({**CHOICE, "apps": ["reelix", "qbittorrent", "gluetun"]})
        r = b["compose"].split("  reelix:")[1].split("\n  qbittorrent:")[0]
        self.assertIn("    depends_on:\n      gluetun:\n        condition: service_healthy", r)

    def test_reelix_without_a_vpn_waits_for_nothing(self):
        b = stack.build({**CHOICE, "apps": ["reelix", "qbittorrent"], "vpn": None})
        r = b["compose"].split("  reelix:")[1].split("\n  qbittorrent:")[0]
        self.assertNotIn("depends_on", r)

    def test_secrets_are_made_and_hidden_from_the_page(self):
        b = stack.build(CHOICE)
        self.assertIn("STORYARR_DB_PASSWORD=", b["env"])
        self.assertEqual(b["env_shown"]["WIREGUARD_PRIVATE_KEY"], "(hidden)")
        self.assertNotIn("secret+key=", json.dumps(b["env_shown"]))
        self.assertIn("  storyarr-db:", b["compose"])
        self.assertEqual(b["later"], ["Unpackerr"])
        self.assertIn('profiles: ["later"]', b["compose"].split("  unpackerr:")[1])

    def test_folders_must_be_safe(self):
        for bad in ("relative/path", "/", "/etc", "/etc/x", "/srv/../etc", "/srv/a b", "/srv/$(id)", "/var/lib/docker/x"):
            with self.assertRaises(ValueError, msg=bad):
                stack.build({**CHOICE, "data_dir": bad})

    def test_only_known_apps_and_safe_vpn_values(self):
        with self.assertRaises(ValueError):
            stack.build({**CHOICE, "apps": ["evil"]})
        with self.assertRaises(ValueError):
            stack.build({**CHOICE, "vpn": {**CHOICE["vpn"], "wireguard_addresses": "a\nB=1"}})
        with self.assertRaises(ValueError):
            stack.build({**CHOICE, "tz": "Europe/London; rm"})

    def test_taken_ports_move_to_the_next_free_one(self):
        with mock.patch.object(stack, "_port_free", lambda port: port != 7878):
            b = stack.build({**CHOICE, "apps": ["radarr"]})
        self.assertIn('"7879:7878"', b["compose"])
        self.assertEqual(len(b["moved"]), 1)

    def test_write_keeps_the_old_files_and_hides_env(self):
        with tempfile.TemporaryDirectory() as d:
            stack.write(d, stack.build(CHOICE))
            stack.write(d, stack.build(CHOICE))
            names = os.listdir(os.path.join(d, "stack"))
            self.assertEqual(sum(n.startswith("compose.yaml.before-") for n in names), 1)
            self.assertEqual(os.stat(os.path.join(d, "stack", ".env")).st_mode & 0o777, 0o600)


    def test_storyarr_gets_a_database_backup_before_updates(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            built = stack.build(dict(CHOICE))
            self.assertEqual(list(built["hooks"]), ["storyarr"])
            script = built["hooks"]["storyarr"]
            self.assertIn("docker exec storyarr-db pg_dump -U storyarr storyarr", script)
            self.assertEqual(subprocess.run(["sh", "-n"], input=script, text=True).returncode, 0)
            path = stack.write(d, built)
            hook = os.path.join(path, "starboard-before-update", "storyarr.sh")
            self.assertEqual(os.stat(hook).st_mode & 0o777, 0o700)
            with open(hook, "w") as f:
                f.write("mine\n")
            stack.write(d, stack.build(dict(CHOICE)))
            with open(hook) as f:
                self.assertEqual(f.read(), "mine\n")  # a hook you changed is kept

    def test_only_the_chosen_vpn_connection_is_written_and_needed(self):
        env = stack.build(dict(CHOICE))["env"]
        self.assertIn("WIREGUARD_ADDRESSES", env)
        self.assertNotIn("OPENVPN_USER", env)
        with self.assertRaisesRegex(ValueError, "OpenVPN password"):
            stack.build(dict(CHOICE, vpn={"provider": "mullvad", "type": "openvpn", "openvpn_user": "me"}))

    def test_storyarr_is_offered_unless_turned_off(self):
        self.assertIn("storyarr", [a["key"] for a in stack.catalogue(set())["apps"]])
        with mock.patch.dict(stack.APPS["storyarr"], {"image": "none"}):
            self.assertNotIn("storyarr", [a["key"] for a in stack.catalogue(set())["apps"]])


if __name__ == "__main__":
    unittest.main()


class StarterTest(unittest.TestCase):
    """Without Docker access, the Run first window starts the apps: a request file, then the result next to it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = self.tmp.name
        os.makedirs(os.path.join(self.data, "stack"))
        stack._job.clear()

    def tearDown(self):
        stack._job.clear()
        self.tmp.cleanup()

    def test_waiting_only_while_the_window_touches_its_file(self):
        self.assertFalse(stack.starter_waiting(self.data))
        open(os.path.join(self.data, "starter"), "w").close()
        self.assertTrue(stack.starter_waiting(self.data))
        old = os.path.getmtime(os.path.join(self.data, "starter")) - 60
        os.utime(os.path.join(self.data, "starter"), (old, old))
        self.assertFalse(stack.starter_waiting(self.data))

    def test_request_then_result(self):
        open(os.path.join(self.data, "starter"), "w").close()
        job = stack.start_via_starter(self.data)
        self.assertFalse(job["finished"])
        self.assertNotIn("request", job)
        with open(os.path.join(self.data, "stack", "start-request")) as f:
            request = f.read()
        self.assertFalse(stack.job()["finished"])
        with self.assertRaises(ValueError):
            stack.start_via_starter(self.data)
        with open(os.path.join(self.data, "stack", "start-result.json"), "w") as f:
            json.dump({"request": "an older one", "ok": True, "log": ""}, f)
        self.assertFalse(stack.job()["finished"])  # not the answer to this request
        with open(os.path.join(self.data, "stack", "start-result.json"), "w") as f:
            json.dump({"request": request, "ok": True, "log": "18 of 18 apps are running."}, f)
        job = stack.job()
        self.assertTrue(job["finished"])
        self.assertTrue(job["ok"])
        self.assertIn("18 of 18", job["log"])

    def test_window_closed_before_it_answered(self):
        open(os.path.join(self.data, "starter"), "w").close()
        stack.start_via_starter(self.data)
        os.remove(os.path.join(self.data, "starter"))
        stack._job["started"] -= 60
        job = stack.job()
        self.assertTrue(job["finished"])
        self.assertFalse(job["ok"])
        self.assertIn("--start-apps", job["log"])
