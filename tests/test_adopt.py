"""After Install apps starts its apps, Starboard adds them once they answer, even when the person left the page."""
import unittest
from unittest import mock

from starboard import server


class AdoptTest(unittest.TestCase):
    def run_now(self, keys, rounds, job=None):
        app = mock.Mock()
        app.config.data = {"services": []}
        searches = iter(rounds)
        with mock.patch.object(server.stack, "job", return_value=job or {"finished": True, "ok": True}), \
                mock.patch.object(server.discovery, "search", side_effect=lambda _s: {"items": next(searches)}), \
                mock.patch.object(server, "add_found", return_value={"added": ["Radarr"], "missing_keys": []}) as add, \
                mock.patch.object(server.threading, "Thread", side_effect=lambda target, **_k: mock.Mock(start=target)), \
                mock.patch.object(server.time, "sleep"):
            server.adopt_started_apps(app, keys)
        return add

    def test_waits_until_each_app_answers_then_adds_the_new_ones(self):
        radarr = {"key": "radarr", "url": "http://127.0.0.1:7878", "already": False, "can_read_key": True}
        sonarr = {"key": "sonarr", "url": "http://127.0.0.1:8989", "already": False, "can_read_key": False}
        old = {"key": "jellyfin", "url": "http://127.0.0.1:8096", "already": True}
        add = self.run_now(["radarr", "sonarr", "unpackerr"], [[radarr], [radarr, old], [radarr, sonarr, old]])
        items = add.call_args[0][1]
        self.assertEqual([i["key"] for i in items], ["radarr", "sonarr"])  # unpackerr has no page; jellyfin is there already
        self.assertTrue(items[0]["read_key"])
        self.assertFalse(items[1]["read_key"])

    def test_nothing_when_the_apps_did_not_start(self):
        add = self.run_now(["radarr"], [], job={"finished": True, "ok": False})
        add.assert_not_called()


if __name__ == "__main__":
    unittest.main()
