"""Restart an app from Manage apps, and apps sharing Gluetun's network rejoin it after it restarts (12 November 2026)."""
import unittest
from unittest import mock

from starboard import containers, server

LISTED = [
    {"Id": "g1", "Names": ["/gluetun"], "HostConfig": {"NetworkMode": "bridge"}},
    {"Id": "b1", "Names": ["/bazarr"], "HostConfig": {"NetworkMode": "container:g1"}},
    {"Id": "q1", "Names": ["/qbittorrent"], "HostConfig": {"NetworkMode": "container:g1"}},
]
STARTED = {"g1": "2026-11-12T13:58:33Z", "b1": "2026-11-12T13:58:30Z", "q1": "2026-11-12T14:01:31Z"}


def fake_docker(calls):
    def docker(method, path, body=None, raw=False, timeout=30):
        calls.append((method, path))
        if path.startswith("/containers/json"):
            return LISTED
        if method == "GET" and path.endswith("/json"):
            ref = path.split("/")[2]
            c = next((x for x in LISTED if ref in (x["Id"], x["Names"][0][1:])), None)
            if not c:
                raise containers.DockerError("No such container")
            return {"Id": c["Id"], "Name": c["Names"][0], "State": {"StartedAt": STARTED[c["Id"]]}}
        return {}
    return docker


class Rejoin(unittest.TestCase):
    def test_only_a_sharer_older_than_its_network_is_restarted(self):
        calls = []
        with mock.patch.object(containers, "docker", side_effect=fake_docker(calls)):
            self.assertEqual(containers.stale_sharers(), [{"name": "bazarr", "shares": "gluetun"}])
            self.assertEqual(containers.rejoin(), ["bazarr"])
        self.assertIn(("POST", "/containers/bazarr/restart?t=20"), calls)
        self.assertNotIn(("POST", "/containers/qbittorrent/restart?t=20"), calls)

    def test_sharers_of_gluetun(self):
        with mock.patch.object(containers, "docker", side_effect=fake_docker([])):
            self.assertEqual(containers.sharers("gluetun"), ["bazarr", "qbittorrent"])


class GluetunMadeAgain(unittest.TestCase):
    """Gluetun made again has a new ID: the apps on the old one are made again by their Compose project, as a restart
    keeps the old ID (13 November 2026)."""

    def test_apps_on_a_gone_gluetun_are_made_again_once_per_project(self):
        labels = {"com.docker.compose.project": "media-stack", "com.docker.compose.project.working_dir": "/srv/stack",
                  "com.docker.compose.project.config_files": "/srv/stack/compose.yaml"}
        listed = [{"Id": "g2", "Names": ["/gluetun"], "HostConfig": {"NetworkMode": "bridge"}},
                  {"Id": "b1", "Names": ["/bazarr"], "HostConfig": {"NetworkMode": "container:gone"},
                   "Labels": {**labels, "com.docker.compose.service": "bazarr"}},
                  {"Id": "q1", "Names": ["/qbittorrent"], "HostConfig": {"NetworkMode": "container:gone"},
                   "Labels": {**labels, "com.docker.compose.service": "qbittorrent"}}]
        started = {"g2": "2026-11-13T10:48:00Z", "b1": "2026-11-12T13:58:30Z", "q1": "2026-11-12T14:01:31Z"}

        def docker(method, path, body=None, raw=False, timeout=30):
            if path.startswith("/containers/json"):
                return listed
            ref = path.split("/")[2]
            c = next((x for x in listed if ref in (x["Id"], x["Names"][0][1:])), None)
            if not c:
                raise containers.DockerError("No such container")
            return {"Id": c["Id"], "Name": c["Names"][0], "State": {"StartedAt": started[c["Id"]]}}
        with mock.patch.object(containers, "docker", side_effect=docker), \
                mock.patch.object(containers, "_helper", return_value=(0, "")) as helper:
            gone = containers.stale_sharers()
            self.assertEqual([(c["name"], c.get("gone"), c["service"]) for c in gone], [("bazarr", True, "bazarr"), ("qbittorrent", True, "qbittorrent")])
            self.assertEqual(containers.rejoin(), ["media-stack (made again)"])
        helper.assert_called_once()
        script = helper.call_args[0][1]
        self.assertIn("up -d --force-recreate --no-deps", script)
        self.assertIn("bazarr", script)
        self.assertIn("qbittorrent", script)


class RestartApp(unittest.TestCase):
    def run_restart(self, service):
        calls = []
        with mock.patch.object(containers, "available", return_value=True), \
             mock.patch.object(containers, "docker", side_effect=fake_docker(calls)), \
             mock.patch.object(containers, "containers", return_value=[{"id": c["Id"], "name": c["Names"][0][1:]} for c in LISTED]):
            return server.restart_app(service), calls

    def test_restarts_the_app(self):
        said, calls = self.run_restart({"id": "bazarr", "name": "Bazarr"})
        self.assertEqual(said, "Bazarr restarted")
        self.assertIn(("POST", "/containers/bazarr/restart?t=20"), calls)

    def test_gluetun_restarts_the_apps_on_its_network_after_it(self):
        said, calls = self.run_restart({"id": "gluetun", "name": "Gluetun"})
        posts = [p for m, p in calls if m == "POST"]
        self.assertEqual(posts, ["/containers/gluetun/restart?t=20", "/containers/bazarr/restart?t=20", "/containers/qbittorrent/restart?t=20"])
        self.assertIn("bazarr, qbittorrent", said)

    def test_no_container_says_what_to_do(self):
        with self.assertRaisesRegex(ValueError, "Choose it under Container in Edit"):
            self.run_restart({"id": "jellyseerr", "name": "Jellyseerr"})

    def test_no_docker(self):
        with mock.patch.object(containers, "available", return_value=False), self.assertRaisesRegex(ValueError, "no access to Docker"):
            server.restart_app({"id": "bazarr", "name": "Bazarr"})


if __name__ == "__main__":
    unittest.main()
