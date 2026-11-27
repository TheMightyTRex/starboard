"""Plug-in API 1.24 (27 November 2026, DASH-572): the permission power:hold with POST /api/v1/plugin/hold (Starboard API
1.12.0), so a plug-in such as UPS and power holds Starboard's heavy automatic jobs and downloads on battery, and the
time setting type. Held work must start again when the hold ends or runs out."""
import http.client
import json
import os
import shutil
import tempfile
import threading
import unittest
from datetime import datetime
from http.server import ThreadingHTTPServer
from unittest import mock

from starboard import api_v1, auth, backup_schedule, jobs, plugin_life, plugin_socket, plugin_tester, plugins, plugins_admin as pa, power_hold
from starboard.config import Config
from starboard.schedule import Schedule
from starboard.server import make_server
from tests.test_plugin_api_socket import UnixConnection
from tests.test_plugins import ON_DEMAND
from tests.test_schedule import FakeClients

UPS = {"id": "ups-power", "name": "UPS and power"}


class Hold(unittest.TestCase):
    def setUp(self):
        power_hold.reset()
        self.addCleanup(power_hold.reset)

    def test_a_hold_lasts_its_minutes_and_ends_by_itself(self):
        out = power_hold.set_hold(UPS, True, "On battery", 5, now=1000)
        self.assertEqual((out["held"], out["reason"], out["until"], out["by"]), (True, "On battery", 1300, "UPS and power"))
        self.assertTrue(power_hold.state(now=1299)["held"])
        self.assertEqual(power_hold.state(now=1300), {"held": False})
        self.assertFalse(power_hold.held())

    def test_asking_again_keeps_it_and_false_lets_it_go(self):
        power_hold.set_hold(UPS, True, "On battery", 1, now=1000)
        out = power_hold.set_hold(UPS, True, "On battery", 10, now=1050)
        self.assertEqual(out["until"], 1650)
        self.assertEqual(power_hold.set_hold(UPS, False, now=1060), {"held": False})
        self.assertEqual(power_hold.set_hold(UPS, False, now=1061), {"held": False})  # letting go twice is fine

    def test_the_default_is_10_minutes_and_30_is_the_most(self):
        self.assertEqual(power_hold.set_hold(UPS, True, "", now=0)["until"], 600)
        self.assertEqual(power_hold.state(now=1)["reason"], "On battery")
        self.assertEqual(power_hold.set_hold(UPS, True, "x", 30, now=0)["until"], 1800)
        for bad in (0, 31, -1, "10", 1.5, True):
            with self.assertRaises(ValueError):
                power_hold.set_hold(UPS, True, "x", bad)

    def test_two_plugins_the_longest_wins_and_one_letting_go_leaves_the_other(self):
        other = {"id": "other", "name": "Other"}
        power_hold.set_hold(UPS, True, "On battery", 5, now=0)
        power_hold.set_hold(other, True, "Hot", 20, now=0)
        self.assertEqual(power_hold.state(now=1)["by"], "Other")
        power_hold.set_hold(other, False, now=2)
        self.assertEqual(power_hold.state(now=3)["by"], "UPS and power")

    def test_a_plugin_that_may_hold_is_not_held_by_its_own_hold(self):
        power_hold.set_hold(UPS, True, "On battery", 5)
        self.assertTrue(power_hold.held())
        self.assertFalse(power_hold.held(exempt="ups-power"))
        power_hold.set_hold({"id": "other", "name": "Other"}, True, "x", 5)
        self.assertTrue(power_hold.held(exempt="ups-power"))

    def test_a_loop_waits_while_held_and_goes_on_when_released(self):
        power_hold.set_hold(UPS, True, "On battery", 5)
        event = threading.Event()
        threading.Timer(0.2, lambda: power_hold.set_hold(UPS, False)).start()
        self.assertTrue(power_hold.wait_released(event, step=30))  # woken by the release, not after 30 seconds
        power_hold.set_hold(UPS, True, "On battery", 5)
        threading.Timer(0.2, event.set).start()  # its own wake-up (a setting changed) ends the wait, still held
        self.assertFalse(power_hold.wait_released(event, step=0.05))

    def test_a_change_wakes_the_loops(self):
        woken = []
        power_hold.on_change(lambda: woken.append(1))
        power_hold.set_hold(UPS, True, "On battery", 5, now=0)
        power_hold.set_hold(UPS, False, now=1)
        self.assertEqual(len(woken), 2)
        power_hold.set_hold(UPS, True, "On battery", 1, now=10)
        power_hold.state(now=100)  # ran out
        self.assertEqual(len(woken), 4)


class WhatIsHeld(unittest.TestCase):
    def setUp(self):
        power_hold.reset()
        self.addCleanup(power_hold.reset)

    def test_background_jobs_wait_and_run_once_released(self):
        j = jobs.Jobs(mock.Mock(config=mock.Mock(data_dir=tempfile.mkdtemp(), data={"extras": {}})))
        ran = []
        passes = []

        def one_pass(held):
            power_hold.set_hold(UPS, held, "On battery", 5)
            j.run = lambda key, force=False: ran.append(key)
            j._load = lambda: {}
            j.enabled = lambda key: not passes

            def stop(_t):
                passes.append(1)
            j.wake.wait = stop
            j._loop()
            passes.clear()

        with mock.patch.object(j, "quiet_now", return_value=True):
            one_pass(True)
            self.assertEqual(ran, ["defaults", "vpnport"])  # the two light ones go on
            ran.clear()
            one_pass(False)
            self.assertEqual(set(ran), set(jobs.JOBS))

    def test_the_loop_looks_again_in_a_minute_while_held_and_in_ten_otherwise(self):
        j = jobs.Jobs(mock.Mock(config=mock.Mock(data_dir=tempfile.mkdtemp(), data={"extras": {}})))
        waits = []
        j.run = lambda key, force=False: None
        j._load = lambda: {}
        j.enabled = lambda key: not waits
        j.wake.wait = lambda t: waits.append(t)
        with mock.patch.object(j, "quiet_now", return_value=True):
            power_hold.set_hold(UPS, True, "On battery", 5)
            j._loop()
            power_hold.set_hold(UPS, False)
            waits.clear()
            j._loop()
        self.assertEqual(waits, [600])

    def test_plugin_jobs_wait_for_the_hold_except_the_one_that_holds(self):
        d = tempfile.mkdtemp()
        clock = plugin_life.Clock(d)
        calls = {"n": 0}
        todo = [("scanner", {"id": "scan", "at_start": True}), ("ups-power", {"id": "poll", "at_start": True})]

        def needed():
            calls["n"] += 1
            return (todo, set()) if calls["n"] % 2 else ([], set())

        clock._needed = needed
        clock._manifests = {"scanner": {"permissions": []}, "ups-power": {"permissions": ["power:hold"]}}
        clock._active_jobs = lambda: []
        ran = []
        clock.wake.wait = lambda t: None
        with mock.patch.object(plugin_life, "run_job", side_effect=lambda dd, pid, job: ran.append(pid)):
            power_hold.set_hold(UPS, True, "On battery", 5)
            clock._loop()
            self.assertEqual(ran, ["ups-power"])
            power_hold.set_hold(UPS, False)
            ran.clear()
            clock._loop()
            self.assertEqual(sorted(ran), ["scanner", "ups-power"])  # it was due all along, so it runs at once

    def test_a_scheduled_backup_that_is_due_waits_for_the_hold_then_is_made(self):
        sched = backup_schedule.Scheduler(mock.Mock(data_dir=tempfile.mkdtemp()))
        made = threading.Event()
        sched.run = lambda: made.set() or "made"
        sched.mode = lambda: "nightly" if not made.is_set() else "off"
        sched._missed = lambda: False
        power_hold.set_hold(UPS, True, "On battery", 5)
        with mock.patch.object(backup_schedule, "next_run", return_value=datetime(2020, 1, 1)):
            t = threading.Thread(target=sched.loop, daemon=True)
            t.start()
            self.assertFalse(made.wait(0.5))  # due, but held
            power_hold.set_hold(UPS, False)
            self.assertTrue(made.wait(5))
            t.join(5)


class Downloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fake = ThreadingHTTPServer(("127.0.0.1", 0), FakeClients)
        threading.Thread(target=cls.fake.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.fake.shutdown()

    def setUp(self):
        power_hold.reset()
        self.addCleanup(power_hold.reset)

    def schedule(self, d, enabled):
        url = f"http://127.0.0.1:{self.fake.server_port}"
        FakeClients.torrents = {"a": (0.5, "downloading"), "b": (0.2, "stoppedDL"), "seed": (1, "uploading")}
        FakeClients.sab_paused = False
        c = Config(d)
        c.data["services"] = [{"id": "qbittorrent", "name": "qBittorrent", "type": "qbittorrent", "url": url, "api_key": "k"},
                              {"id": "sabnzbd", "name": "SABnzbd", "type": "sabnzbd", "url": url, "api_key": "k"}]
        hour = datetime.now().hour
        c.update_general({"download_hours": {"enabled": enabled, "start": hour, "end": (hour + 1) % 24}})  # inside the hours now
        return Schedule(c)

    def test_downloads_pause_on_a_hold_even_with_download_hours_off_and_start_again_after(self):
        with tempfile.TemporaryDirectory() as d:
            s = self.schedule(d, False)
            s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "downloading")  # nothing held, nothing touched
            power_hold.set_hold(UPS, True, "On battery", 5)
            s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "stoppedDL")
            self.assertEqual(FakeClients.torrents["seed"][1], "uploading")  # seeding is left alone
            self.assertTrue(FakeClients.sab_paused)
            self.assertTrue(s.status()["held"]["held"])
            self.assertTrue(s.needed())
            power_hold.set_hold(UPS, False)
            s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "downloading")  # what Starboard stopped starts again
            self.assertEqual(FakeClients.torrents["b"][1], "stoppedDL")  # what a person stopped stays stopped
            self.assertFalse(FakeClients.sab_paused)
            self.assertFalse(s.needed())

    def test_a_hold_that_runs_out_lets_downloads_go_and_beats_resume_now(self):
        with tempfile.TemporaryDirectory() as d:
            s = self.schedule(d, True)
            s.act("resume")
            power_hold.set_hold(UPS, True, "On battery", 1, now=0)
            with mock.patch.object(power_hold, "time") as t:
                t.time.return_value = 10
                s.tick()
                self.assertEqual(FakeClients.torrents["a"][1], "stoppedDL")  # the person's Resume now does not beat the battery
                self.assertEqual(s.status()["reason"], "power")
                t.time.return_value = 100  # the plug-in stopped asking
                s.tick()
            self.assertEqual(FakeClients.torrents["a"][1], "downloading")
            self.assertEqual(s.status()["held"], {"held": False})


HOLDING = {**ON_DEMAND, "id": "ups-power", "name": "UPS and power", "permissions": [*ON_DEMAND["permissions"], "network:lan", "alerts:send", "power:hold"],
           "containers": [{**ON_DEMAND["containers"][0], "network": "lan"}], "resources": {"main": {"memory": 40}}}
PLAIN = {**HOLDING, "id": "plain-one", "name": "Plain one", "permissions": ["network:lan"]}


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sbhold")
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        cls.host_path = mock.patch.object(pa, "host_path", side_effect=lambda d, pid: f"/srv/sb/plugins/{pid}")
        cls.host_path.start()
        cls.keys = {}
        for m in (HOLDING, PLAIN):
            pa.install(cls.tmp, m, "/srv/media")
            pa.set_state(cls.tmp, m["id"], "enabled")
            with open(os.path.join(pa.folder(cls.tmp, m["id"]), "key")) as f:
                cls.keys[m["id"]] = f.read().strip()
        cls.manager, _ = api_v1.create_key(cls.tmp, "Home Assistant", "manage", [], 90)
        plugin_socket.start(cls.app)

    @classmethod
    def tearDownClass(cls):
        plugin_socket._reset_for_tests()
        cls.host_path.stop()
        cls.server.shutdown()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        power_hold.reset()
        self.addCleanup(power_hold.reset)
        pa.set_state(self.tmp, "ups-power", "enabled")

    def post(self, body, key=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("POST", "/api/v1/plugin/hold", body=json.dumps(body).encode(),
                     headers={"Authorization": f"Bearer {key or self.keys['ups-power']}", "Content-Type": "application/json"})
        r = conn.getresponse()
        out = json.loads(r.read() or b"null")
        conn.close()
        return r, out

    def test_hold_renew_and_release(self):
        r, body = self.post({"on": True, "reason": "On battery", "minutes": 10})
        self.assertEqual((r.status, body["ok"], body["held"], body["reason"], body["by"]), (200, True, True, "On battery", "UPS and power"))
        self.assertTrue(power_hold.held())
        self.assertEqual(self.post({"on": True})[1]["reason"], "On battery")
        r, body = self.post({"on": False})
        self.assertEqual((r.status, body["held"]), (200, False))
        self.assertFalse(power_hold.held())
        with open(os.path.join(self.tmp, "logs", "audit.jsonl")) as f:
            self.assertTrue(any('"api_write"' in line and "/api/v1/plugin/hold" in line for line in f))

    def test_through_the_plugins_own_socket(self):
        c = UnixConnection(plugin_socket.path_for(self.tmp, "ups-power"))
        try:
            c.request("POST", "/api/v1/plugin/hold", body=json.dumps({"on": True}).encode(),
                      headers={"Authorization": f"Bearer {self.keys['ups-power']}"})
            r = c.getresponse()
            self.assertEqual((r.status, json.loads(r.read())["held"]), (200, True))
        finally:
            c.close()

    def test_any_other_key_gets_404(self):
        for key in (self.manager, self.keys["plain-one"]):  # a person's key, a plug-in without power:hold
            r, body = self.post({"on": True}, key)
            self.assertEqual((r.status, body["code"]), (404, "not_found"))
        pa.set_state(self.tmp, "ups-power", "disabled")
        r, body = self.post({"on": True})
        self.assertEqual((r.status, body["code"]), (404, "not_found"))
        self.assertFalse(power_hold.held())

    def test_a_bad_body_gets_400_in_plain_words(self):
        for bad, words in (({}, "Send on"), ({"on": "yes"}, "Send on"), ({"on": True, "reason": "r" * 81}, "up to 80"),
                           ({"on": True, "reason": "two\nlines"}, "one line"), ({"on": True, "reason": 5}, "one line"),
                           ({"on": True, "minutes": 31}, "from 1 to 30"), ({"on": True, "minutes": "5"}, "from 1 to 30")):
            r, body = self.post(bad)
            self.assertEqual((r.status, body["code"]), (400, "bad_request"), bad)
            self.assertIn(words, body["title"])
        self.assertFalse(power_hold.held())

    def test_the_download_hours_answer_says_what_is_held(self):
        self.post({"on": True, "reason": "On battery"})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("GET", "/api/v1/download-hours", headers={"Authorization": f"Bearer {self.manager}"})
        out = json.loads(conn.getresponse().read())
        conn.close()
        self.assertEqual((out["held"]["held"], out["held"]["reason"]), (True, "On battery"))


class Manifest(unittest.TestCase):
    def test_the_permission_and_the_time_setting_are_known(self):
        m = {**ON_DEMAND, "starboard_api": ">=1.24 <2.0", "permissions": [*ON_DEMAND["permissions"], "network:lan", "power:hold"],
             "settings": [{"key": "quiet_from", "label": "Quiet from", "type": "time", "default": "22:00"}]}
        self.assertEqual(plugins.check(m), [])
        self.assertEqual(plugins.PERMISSIONS["power:hold"][1:], ("low", None))
        self.assertEqual(plugins.key_scopes(m), plugins.key_scopes({**m, "permissions": ON_DEMAND["permissions"]}))  # power:hold adds no key scope
        self.assertTrue(any(x.startswith("Heavy jobs") for x in plugins.install_warning(m)["change"]))
        self.assertGreaterEqual(tuple(map(int, plugins.API_VERSION.split("."))), (1, 23, 0))
        self.assertTrue(any("22:00" in x for x in plugins.check({**m, "settings": [{**m["settings"][0], "default": "25:00"}]})))
        schema = json.load(open(os.path.join(os.path.dirname(plugins.__file__), "plugin-manifest.schema.json")))
        self.assertIn("power:hold", schema["properties"]["permissions"]["items"]["enum"])
        self.assertIn("time", schema["properties"]["settings"]["items"]["properties"]["type"]["enum"])
        self.assertFalse([i for i in plugin_tester.run(m) if i["severity"] == "error"])

    def test_a_time_setting_keeps_only_a_time_of_day(self):
        d = tempfile.mkdtemp()
        try:
            m = {**ON_DEMAND, "id": "timed", "settings": [{"key": "quiet_from", "label": "Quiet from", "type": "time", "default": "22:00"}]}
            with mock.patch.object(pa, "host_path", side_effect=lambda dd, pid: f"/srv/sb/plugins/{pid}"):
                pa.install(d, m, "/srv/media")
            self.assertEqual(pa.public_settings(d, "timed")[0]["value"], "22:00")  # the default, until one is saved
            self.assertEqual(pa.save_settings(d, "timed", {"quiet_from": "06:30"})[0]["value"], "06:30")
            for bad in ("6:30", "24:00", "noon", 630, None, "06:30:00"):
                with self.assertRaises(ValueError):
                    pa.save_settings(d, "timed", {"quiet_from": bad})
            self.assertEqual(pa.public_settings(d, "timed")[0]["value"], "06:30")
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
