"""After Install apps starts its apps, Starboard adds them as they answer, even when the person left the page,
and carries on after a restart."""
import os
import tempfile
import time
import unittest
from unittest import mock

from starboard import server, stack


class AdoptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = mock.Mock()
        self.app.data_dir = self.tmp.name
        self.app.config.data = {"services": []}

    def tearDown(self):
        self.tmp.cleanup()

    def run_now(self, keys, rounds, job=None, after_job=True):
        searches = iter(rounds)
        with mock.patch.object(server.stack, "job", return_value=job or {"finished": True, "ok": True}), \
                mock.patch.object(server.discovery, "search", side_effect=lambda _s: {"items": next(searches)}), \
                mock.patch.object(server, "add_found", return_value={"added": ["Radarr"], "missing_keys": []}) as add, \
                mock.patch.object(server.threading, "Thread", side_effect=lambda target, args=(), **_k: mock.Mock(start=lambda: target(*args))), \
                mock.patch.object(server.time, "sleep"):
            server.adopt_started_apps(self.app, keys, after_job=after_job)
        return add

    def test_adds_each_app_as_it_answers(self):
        radarr = {"key": "radarr", "url": "http://127.0.0.1:7878", "already": False, "can_read_key": True}
        sonarr = {"key": "sonarr", "url": "http://127.0.0.1:8989", "already": False, "can_read_key": False}
        old = {"key": "jellyfin", "url": "http://127.0.0.1:8096", "already": True}
        add = self.run_now(["radarr", "sonarr", "unpackerr"], [[radarr], [{**radarr, "already": True}, old], [radarr, sonarr, old]])
        added = [[i["key"] for i in c[0][1]] for c in add.call_args_list]
        self.assertEqual(added, [["radarr"], ["sonarr"]])  # unpackerr has no page; jellyfin was there already
        self.assertTrue(add.call_args_list[0][0][1][0]["read_key"])
        self.assertIsNone(stack.adopting(self.tmp.name))  # nothing left to add

    def test_what_is_left_survives_a_restart(self):
        stack.want_adopted(self.tmp.name, ["radarr"], time.time() + 60)
        self.assertEqual(stack.adopting(self.tmp.name)[0], ["radarr"])
        stack.want_adopted(self.tmp.name, ["radarr"], time.time() - 1)
        self.assertIsNone(stack.adopting(self.tmp.name))  # the time is up
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "stack", "adopt.json.new")))

    def test_nothing_without_apps_it_can_recognise(self):
        add = self.run_now(["unpackerr"], [])
        add.assert_not_called()
        self.assertIsNone(stack.adopting(self.tmp.name))


if __name__ == "__main__":
    unittest.main()
