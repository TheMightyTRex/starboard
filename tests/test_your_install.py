"""Trying to break Install apps' three installs and Settings, Your install through the API (7 November 2026):
bad names, a hand-edited set-up file, a VPN that was never set up, a change while apps are starting, and asking for
what already runs. Nothing here starts containers: Starboard has no Docker access in tests."""
import os
import tempfile
import threading
import unittest
from unittest import mock

from starboard import auth, stack, terminal_setup
from starboard.server import make_server

WORDS = "correct horse battery"
VPN = {"provider": "mullvad", "type": "wireguard", "wireguard_private_key": "made-up", "wireguard_addresses": "192.168.1.20/32"}


class YourInstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k, v in {"STARBOARD_HISTORY": "0", "STARBOARD_SCHEDULE": "0", "STARBOARD_WATCH": "0", "STARBOARD_JOBS": "0",
                     "STARBOARD_DOCKER": "/nonexistent/docker.sock"}.items():
            os.environ[k] = v
        for p in (mock.patch("starboard.server.discovery.search", return_value={"items": []}),
                  mock.patch("starboard.stack.can_download", return_value=True)):
            p.start()
            self.addCleanup(p.stop)
        self.server, self.app = make_server("127.0.0.1", 0, self.tmp.name)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = terminal_setup.Api(self.server.server_address[1])
        self.api.call("POST", "/api/setup", {"token": self.app.setup_token, "password": WORDS})
        stack._job.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()
        stack._job.clear()

    def fails(self, method, path, body, words):
        with self.assertRaises(terminal_setup.Problem) as e:
            self.api.call(method, path, body)
        self.assertIn(words, str(e.exception))

    def write(self, install="basics", usenet="nzbget", vpn=True):
        c = stack.install_choice(install, usenet=usenet)
        apps = c["apps"] if vpn else [k for k in c["apps"] if k != "gluetun"]
        choice = {"apps": apps, "config_dir": "/srv/config", "data_dir": "/srv/media", "reelix_edition": c["reelix_edition"]}
        if vpn:
            choice["vpn"] = VPN
        stack.write(self.tmp.name, stack.build(choice))

    def test_an_unknown_install_is_refused_in_words(self):
        self.fails("POST", "/api/stack/install", {"install": "huge"}, "Choose Basics, Full install or Everything")

    def test_an_unknown_usenet_app_becomes_nzbget(self):
        c = self.api.call("POST", "/api/stack/install", {"install": "full", "usenet": "../../etc/passwd"})
        self.assertIn("nzbget", c["apps"])

    def test_your_install_with_nothing_written_says_so(self):
        d = self.api.call("GET", "/api/install")
        self.assertFalse(d["written"])
        self.fails("POST", "/api/install/change", {"password": WORDS, "install": "full"}, "Install apps did not set up")

    def test_the_wrong_password_changes_nothing(self):
        self.write()
        before = open(os.path.join(stack.folder(self.tmp.name), "compose.yaml")).read()
        self.fails("POST", "/api/install/change", {"password": "wrong", "install": "full"}, "not right")
        self.assertEqual(before, open(os.path.join(stack.folder(self.tmp.name), "compose.yaml")).read())

    def test_asking_for_what_runs_already_is_refused(self):
        self.write()
        self.fails("POST", "/api/install/change", {"password": WORDS, "install": "basics"}, "what runs already")

    def test_an_install_with_a_vpn_needs_the_vpn_details(self):
        self.write(vpn=False)  # a server set up before the VPN was in every install
        self.fails("POST", "/api/install/change", {"password": WORDS, "install": "full"}, "VPN")

    def test_no_change_is_written_while_apps_are_starting(self):
        self.write()
        before = open(os.path.join(stack.folder(self.tmp.name), "compose.yaml")).read()
        stack._job.update(started=1, finished=False)
        self.fails("POST", "/api/install/change", {"password": WORDS, "install": "full"}, "already starting")
        self.assertEqual(before, open(os.path.join(stack.folder(self.tmp.name), "compose.yaml")).read())

    def test_a_change_without_docker_access_writes_and_gives_the_command(self):
        self.write()
        r = self.api.call("POST", "/api/install/change", {"password": WORDS, "install": "full"})
        self.assertIsNone(r["started"])
        self.assertIn("--start-apps", r["command"])
        self.assertEqual(stack.which_install(stack.current_choice(self.tmp.name)["apps"]), "full")

    def test_an_app_added_by_hand_is_kept_through_a_change(self):
        self.write()
        path = os.path.join(stack.folder(self.tmp.name), "compose.yaml")
        with open(path, "a") as f:
            f.write("  mystery:\n    image: example/mystery:1\n    container_name: mystery\n")
        self.api.call("POST", "/api/install/change", {"password": WORDS, "install": "full"})
        after = open(path).read()
        self.assertIn("  mystery:\n    image: example/mystery:1", after)  # kept, so --remove-orphans leaves it alone
        self.assertIn("container_name: tdarr", after)

    def test_running_install_apps_again_keeps_an_app_added_by_hand(self):
        self.write()
        path = os.path.join(stack.folder(self.tmp.name), "compose.yaml")
        with open(path, "a") as f:
            f.write("  mystery:\n    image: example/mystery:1\n    container_name: mystery\n")
        c = stack.install_choice("basics")
        self.api.call("POST", "/api/stack/write", {"apps": c["apps"], "config_dir": "/srv/config", "data_dir": "/srv/media", "vpn": VPN})
        self.assertIn("container_name: mystery", open(path).read())

    def test_a_set_up_file_with_sections_starboard_did_not_write_is_left_alone(self):
        self.write()
        path = os.path.join(stack.folder(self.tmp.name), "compose.yaml")
        with open(path, "a") as f:
            f.write("networks:\n  mine:\n    external: true\n")
        self.fails("POST", "/api/install/change", {"password": WORDS, "install": "full"}, "sections Starboard did not write")

    def test_your_install_lists_three_changes_with_what_each_adds(self):
        self.write()
        d = self.api.call("GET", "/api/install")
        self.assertEqual(d["current"]["install"], "basics")
        full = next(i for i in d["installs"] if i["key"] == "full")
        self.assertIn("Tdarr", full["add"])
        self.assertEqual(next(i for i in d["installs"] if i["key"] == "basics")["add"], [])


if __name__ == "__main__":
    unittest.main()
