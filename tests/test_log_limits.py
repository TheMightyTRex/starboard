"""Log limits (DASH-451, owner, 16 November 2026: "Can we also have limits on the logs with a setting for it and a way
to delete them all"): the apps' own limit read from Docker, the limit Starboard writes into the Compose files of the
apps and plug-ins it installs, and the Compose check that keeps an app's log on this computer. Starboard's own limits
and Delete all logs are in test_logs.py; the API's in test_api_v1.py."""
import re
import unittest
from unittest import mock

from starboard import app_logs, compose_check, plugins, stack


class FakeDocker:
    def __init__(self, configs, driver="json-file"):
        self.configs = configs
        self.driver = driver
        self.asked = []

    def __call__(self, method, path, *a, **k):
        self.asked.append(path)
        if path.startswith("/containers/json"):
            return [{"Id": name, "Names": [f"/{name}"]} for name in self.configs]
        if path == "/info":
            return {"LoggingDriver": self.driver}
        m = re.match(r"^/containers/([\w-]+)/json$", path)
        if m:
            return {"HostConfig": {"LogConfig": self.configs[m.group(1)]}}
        raise AssertionError(path)


class AppLimitsTest(unittest.TestCase):
    def test_the_limit_most_apps_have_from_daemon_json(self):
        capped = {"Type": "json-file", "Config": {"max-file": "3", "max-size": "10m"}}
        out = app_logs.limits(FakeDocker({"reelix": capped, "jellyfin": capped, "old-app": {"Type": "json-file", "Config": {}},
                                          "starboard-updater-1": {"Type": "json-file", "Config": {}}}))
        self.assertEqual({k: out[k] for k in ("available", "driver", "max_size", "max_file", "per_app", "capped", "uncapped")},
                         {"available": True, "driver": "json-file", "max_size": "10m", "max_file": "3",
                          "per_app": 30 * 1024 ** 2, "capped": 2, "uncapped": ["old-app"]})

    def test_local_and_journald(self):
        out = app_logs.limits(FakeDocker({"a": {"Type": "local", "Config": {}}, "b": {"Type": "journald", "Config": {}}}, "local"))
        self.assertEqual((out["driver"], out["max_size"], out["max_file"], out["capped"], out["uncapped"]), ("local", "20m", "5", 1, []))
        out = app_logs.limits(FakeDocker({"b": {"Type": "journald", "Config": {}}}, "journald"))
        self.assertEqual((out["driver"], out["max_size"], out["per_app"], out["capped"]), ("journald", "", None, 0))

    def test_without_docker_it_says_so_and_is_kept_10_minutes(self):
        with mock.patch("starboard.containers.available", return_value=False):
            app_logs._limits.update(at=0, out=None)
            self.assertFalse(app_logs.limits()["available"])
        app_logs._limits.update(at=1000, out={"available": True, "kept": True})
        self.assertTrue(app_logs.limits(now=1000 + 599)["kept"])  # no new look within 10 minutes
        app_logs._limits.update(at=0, out=None)


class ComposeLimitTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(stack, "_port_free", lambda port: True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def services(self, text):
        """Each service's block of a Compose file Starboard wrote."""
        return dict(re.findall(r"(?m)^  ([\w-]+):\n((?:    .*\n?)*)", text.split("services:", 1)[1].split("\nnetworks:")[0]))

    def test_every_app_and_database_starboard_installs_has_its_log_capped(self):
        choice = {"apps": ["jellyfin", "reelix", "qbittorrent"], "config_dir": "/srv/config", "data_dir": "/srv/media",
                  "puid": 1000, "pgid": 1000, "tz": "Europe/London", "vpn": None}
        blocks = self.services(stack.build(choice)["compose"])
        self.assertTrue(blocks)
        for name, block in blocks.items():
            self.assertIn('    logging:\n      driver: json-file\n      options:\n        max-size: "10m"\n        max-file: "3"', block, name)

    def test_a_plugin_has_its_log_capped(self):
        manifest = {"id": "made-up", "name": "Made up", "version": "1.0.0",
                    "containers": [{"name": "app", "image": "ghcr.io/example/made-up@sha256:" + "0" * 64}]}
        with mock.patch.object(plugins, "check", return_value=[]):
            text = plugins.compose(manifest, "/srv/p", "/srv/media")
        self.assertIn('    logging:\n      driver: json-file\n      options:\n        max-size: "10m"', text)

    def test_the_check_keeps_an_app_s_log_on_this_computer(self):
        env = {"CONFIG_DIR": "/srv/config", "DATA_DIR": "/srv/media"}
        image = stack.APPS["jellyfin"]["image"]
        for driver, ok in (("json-file", True), ("local", True), ("journald", True), ("syslog", False), ("gelf", False)):
            found = compose_check.problems({"services": {"jellyfin": {"image": image, "logging": {"driver": driver}}}}, env)
            self.assertEqual(found == [], ok, (driver, found))
        self.assertEqual(compose_check.problems({"services": {"jellyfin": {"image": image}}}, env), [])


if __name__ == "__main__":
    unittest.main()
