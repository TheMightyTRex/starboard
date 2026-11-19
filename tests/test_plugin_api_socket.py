"""A plug-in on its own internal network reaches Starboard's API through a Unix socket in its run folder (DASH-482,
issue 202): Starboard runs on the computer's own network, so it cannot join the plug-in's network. The socket answers
only /api/v1 and only to that plug-in's own key, and its network stays internal."""
import http.client
import json
import os
import shutil
import socket
import stat
import tempfile
import time
import unittest
from unittest import mock

from starboard import api_v1, auth, plugin_socket, plugins, plugins_admin as pa
from starboard.server import make_server
from tests.test_plugins import ON_DEMAND


class UnixConnection(http.client.HTTPConnection):
    """HTTP over the plug-in's socket, as the plug-ins' helper sends it."""

    def __init__(self, path):
        super().__init__("localhost", timeout=10)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect(self.path)


class ComposeTellsWhere(unittest.TestCase):
    def manifest(self, network):
        perms = {"default": [], "lan": ["network:lan"], "vpn": ["network:vpn"]}[network]
        c = {**ON_DEMAND["containers"][0], "network": network}
        return {**ON_DEMAND, "permissions": ["media:read", "jellyfin:key", *perms], "containers": [c],
                "resources": {"main": {"memory": 40}}}

    def test_every_network_is_given_the_socket_and_the_network_stays_internal(self):
        for net in ("default", "lan", "vpn"):
            text = plugins.compose(self.manifest(net), "/srv/sb/plugins/on-demand", "/srv/media")
            self.assertIn('STARBOARD_API_SOCKET: "/run/starboard/api.sock"', text, net)
            self.assertIn('"/srv/sb/plugins/on-demand/run:/run/starboard:ro"', text, net)
        own = plugins.compose(self.manifest("default"), "/srv/sb/plugins/on-demand", "/srv/media")
        self.assertIn("internal: true", own)
        self.assertNotIn("host.docker.internal", own)  # no way out to the computer, Starboard's port included
        self.assertNotIn("extra_hosts", own)

    def test_an_older_compose_file_is_written_again_with_the_socket(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}"):
            pa.install(tmp.name, ON_DEMAND, "/srv/media")
            path = os.path.join(pa.folder(tmp.name, "on-demand"), "compose.yaml")
            with open(path) as f:
                text = f.read()
            self.assertFalse(pa.write_compose(tmp.name, "on-demand"))  # already has it: left alone
            with open(path, "w") as f:
                f.write(text.replace('      STARBOARD_API_SOCKET: "/run/starboard/api.sock"\n', ""))
            self.assertTrue(pa.write_compose(tmp.name, "on-demand"))
            with open(path) as f:
                self.assertIn("STARBOARD_API_SOCKET", f.read())


class SocketAnswers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # A short folder: a Unix socket's address holds at most 107 bytes
        cls.tmp = tempfile.mkdtemp(prefix="sbsock")
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp)
        cls.host_path = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}")
        cls.host_path.start()
        pa.install(cls.tmp, ON_DEMAND, "/srv/media")
        pa.set_state(cls.tmp, "on-demand", "enabled")
        with open(os.path.join(pa.folder(cls.tmp, "on-demand"), "key")) as f:
            cls.key = f.read().strip()
        cls.person_key, _ = api_v1.create_key(cls.tmp, "Home Assistant", "read", [], 90)
        plugin_socket.start(cls.app)
        cls.path = plugin_socket.path_for(cls.tmp, "on-demand")

    @classmethod
    def tearDownClass(cls):
        plugin_socket._reset_for_tests()
        cls.host_path.stop()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def ask(self, path, key=None, method="GET"):
        c = UnixConnection(self.path)
        try:
            c.request(method, path, body=b"{}" if method != "GET" else None,
                      headers={"Authorization": f"Bearer {key}"} if key else {})
            r = c.getresponse()
            return r.status, r.read()
        finally:
            c.close()

    def test_an_active_plugin_has_its_socket_in_its_run_folder_open_to_its_containers(self):
        self.assertTrue(stat.S_ISSOCK(os.lstat(self.path).st_mode))
        self.assertEqual(os.path.dirname(self.path), os.path.join(pa.folder(self.tmp, "on-demand"), "run"))
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o666)  # any user a container runs as
        self.assertEqual(os.stat(pa.folder(self.tmp, "on-demand")).st_mode & 0o777, 0o700)  # nobody else

    def test_its_own_key_reads_what_was_approved(self):
        status, body = self.ask("/api/v1/me", self.key)
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["scopes"], ["media"])

    def test_no_key_another_key_or_another_address_is_refused(self):
        self.assertEqual(self.ask("/api/v1/me")[0], 401)
        status, body = self.ask("/api/v1/me", self.person_key)
        self.assertEqual(status, 401)
        self.assertIn(b"own key", body)
        self.assertEqual(self.ask("/api/status", self.key)[0], 404)  # only the API, never the dashboard's own
        self.assertEqual(self.ask("/", self.key)[0], 404)
        self.assertEqual(self.ask("/api/v1/plugins/on-demand/enable", self.key, "POST")[0] // 100, 4)  # a read key

    def test_disable_closes_it_and_enable_opens_it_again(self):
        pa.disable(self.tmp, "on-demand", helper=lambda folder, script, *a: (0, ""))
        self.assertFalse(os.path.exists(self.path))
        with mock.patch("starboard.plugin_life.can_enable"):
            pa.enable(self.tmp, "on-demand", helper=lambda folder, script, *a: (0, ""))
        self.assertTrue(stat.S_ISSOCK(os.lstat(self.path).st_mode))
        self.assertEqual(self.ask("/api/v1/me", self.key)[0], 200)

    def test_a_stale_socket_from_a_previous_start_is_replaced(self):
        plugin_socket.stop("on-demand")
        stale = socket.socket(socket.AF_UNIX)
        stale.bind(self.path)
        stale.close()  # the file stays, as after Starboard stopped without tidying up
        self.assertTrue(plugin_socket.serve(self.tmp, "on-demand"))
        self.assertEqual(self.ask("/api/v1/me", self.key)[0], 200)

    def test_nothing_but_a_socket_is_ever_removed(self):
        other = os.path.join(pa.folder(self.tmp, "on-demand"), "run", "not-a-socket")
        with open(other, "w") as f:
            f.write("kept")
        plugin_socket._remove_socket(other)
        self.assertTrue(os.path.exists(other))

    def test_waiting_for_a_plugin_costs_no_processor_time(self):
        before = time.process_time()
        time.sleep(0.5)
        self.assertLess(time.process_time() - before, 0.05)


class DeepFolder(unittest.TestCase):
    def test_a_folder_too_deep_for_a_socket_address_still_gets_one(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = mock.Mock(data_dir=os.path.join(tmp.name, "a" * 60, "b" * 60))
        os.makedirs(os.path.join(app.data_dir, "plugins", "on-demand", "run"))
        plugin_socket.start(app)
        self.addCleanup(plugin_socket._reset_for_tests)
        path = plugin_socket.path_for(app.data_dir, "on-demand")
        self.assertGreater(len(path), plugin_socket.MAX_PATH)
        self.assertTrue(plugin_socket.serve(app.data_dir, "on-demand"))
        self.assertTrue(stat.S_ISSOCK(os.lstat(path).st_mode))
        plugin_socket.stop("on-demand")
        self.assertFalse(os.path.exists(path))


class NotServing(unittest.TestCase):
    def test_without_starboard_running_serve_does_nothing(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.assertFalse(plugin_socket.serve(tmp.name, "on-demand"))


if __name__ == "__main__":
    unittest.main()
