"""Host alerts (DASH-556): each rule is off until switched on, needs its time over the limit, sends once and clears,
tells an outside address change without the address, and a container that stopped with an error."""
import threading
import time
import unittest
from unittest import mock

from starboard import config, host_alerts, watch

DEFAULT = {"cpu_temp": {"on": False, "limit": 85, "minutes": 10}, "load": {"on": False, "limit": 90, "minutes": 10},
           "memory": {"on": False, "limit": 90, "minutes": 10}, "disk_space": {"on": False, "limit": 95, "minutes": 60},
           "disk_rate": {"on": False, "limit": 200, "minutes": 10}, "address": {"on": False}, "container": {"on": False}}


class FakeConfig:
    def __init__(self, host):
        self.data = {"site_name": "Harbour", "watch": {"host": host, "channel": {}, "alerts": {}}, "services": []}


class FakeApp:
    def __init__(self, host):
        self.config = FakeConfig(host)
        self.disks = [("Media", "/media")]
        self.data_dir = "/nonexistent"
        self.watch = watch.Watch.__new__(watch.Watch)
        self.watch.app, self.watch.state, self.watch.lock = self, {"alerted": {}}, threading.Lock()
        self.watch.settings = lambda: self.config.data["watch"]
        self.watch._save = lambda: None


def reading(t, temp=None, used=50.0, busy_idle=(1000, 900), moved=0):
    return {"time": t, "temps": [{"chip": "k10temp", "label": "Tctl", "c": temp}] if temp is not None else [],
            "memory": {"total": 1000, "available": int(1000 - used * 10)},
            "cpu": {"total": [busy_idle[0], busy_idle[1]], "cores": [], "load": [0.1]}, "disks": {"sda": [moved, 0]}}


def make(**on):
    host = {k: dict(v) for k, v in DEFAULT.items()}
    for k, v in on.items():
        host[k].update(v)
    app = FakeApp(host)
    return app, host_alerts.HostWatch(app)


class Rules(unittest.TestCase):
    def setUp(self):
        self.sent = []
        patch = mock.patch.object(watch, "send", lambda *a, **k: self.sent.append(a))
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch("starboard.api_v1.publish", lambda *a, **k: None)
        patch.start()
        self.addCleanup(patch.stop)
        patch = mock.patch("starboard.activity_log.note", lambda *a, **k: None)
        patch.start()
        self.addCleanup(patch.stop)

    def alerted(self, app):
        return sorted(app.watch.state["alerted"])

    def test_everything_is_off_at_first_and_nothing_runs(self):
        app, h = make()
        self.assertFalse(h.any_on())
        h.ensure()
        self.assertIsNone(h.thread)
        h.tick(1000, reading(1000, temp=120, used=99))
        self.assertEqual(self.alerted(app), [])

    def test_a_rule_waits_for_its_time_over_the_limit(self):
        app, h = make(cpu_temp={"on": True, "limit": 85, "minutes": 10})
        t = 10_000
        for minute in range(0, 9):
            h.tick(t + minute * 60, reading(t + minute * 60, temp=90))
        self.assertEqual(self.alerted(app), [])  # 8 minutes over: not yet
        h.tick(t + 10 * 60, reading(t + 600, temp=90))
        self.assertEqual(self.alerted(app), ["host:cpu_temp"])
        h.tick(t + 11 * 60, reading(t + 660, temp=91))
        self.assertEqual(len(self.alerted(app)), 1)  # once until it clears

    def test_a_dip_under_the_limit_starts_the_time_again(self):
        app, h = make(memory={"on": True, "limit": 90, "minutes": 5})
        t = 0
        h.tick(t, reading(t, used=95))
        h.tick(t + 180, reading(t + 180, used=95))
        h.tick(t + 240, reading(t + 240, used=50))   # back under
        h.tick(t + 300, reading(t + 300, used=95))
        h.tick(t + 540, reading(t + 540, used=95))   # 4 minutes since the new start
        self.assertEqual(self.alerted(app), [])
        h.tick(t + 600, reading(t + 600, used=95))
        self.assertEqual(self.alerted(app), ["host:memory"])

    def test_it_clears_when_back_under(self):
        app, h = make(memory={"on": True, "limit": 90, "minutes": 1})
        h.tick(0, reading(0, used=95))
        h.tick(60, reading(60, used=95))
        self.assertEqual(self.alerted(app), ["host:memory"])
        h.tick(120, reading(120, used=40))
        self.assertEqual(self.alerted(app), [])
        self.assertEqual([m[1] for m in self.sent], [])  # no channel set, so nothing is posted; the alert itself is kept

    def test_the_processor_load_comes_from_two_readings(self):
        app, h = make(load={"on": True, "limit": 90, "minutes": 1})
        h.tick(0, reading(0, busy_idle=(1000, 500)))
        h.tick(60, reading(60, busy_idle=(2000, 550)))   # 95% busy in between
        h.tick(120, reading(120, busy_idle=(3000, 600)))
        self.assertEqual(self.alerted(app), ["host:load"])

    def test_drive_speed_is_read_and_write_together_in_megabytes_a_second(self):
        app, h = make(disk_rate={"on": True, "limit": 100, "minutes": 1})
        h.tick(0, reading(0, moved=0))
        h.tick(60, reading(60, moved=60 * 150_000_000))
        h.tick(120, reading(120, moved=120 * 150_000_000))
        self.assertEqual(self.alerted(app), ["host:disk_rate"])

    def test_a_full_folder_names_the_fullest(self):
        app, h = make(disk_space={"on": True, "limit": 95, "minutes": 1})
        disks = {"disks": [{"label": "Media", "total": 100, "used": 97, "free": 3}, {"label": "Backups", "total": 100, "used": 10, "free": 90},
                           {"label": "Gone", "missing": True}]}
        with mock.patch("starboard.sysinfo.snapshot", return_value=disks), \
                mock.patch.object(app.watch, "alert", wraps=app.watch.alert) as alert:
            h.tick(0)
            h.tick(61)
        self.assertEqual(self.alerted(app), ["host:disk_space"])
        self.assertIn("Media is 97% full", alert.call_args[0][2])

    def test_a_reading_is_made_only_for_a_rule_that_is_on(self):
        app, h = make(disk_space={"on": True, "limit": 95, "minutes": 1})
        with mock.patch("starboard.sysinfo.monitor") as monitor, mock.patch("starboard.sysinfo.snapshot", return_value={"disks": []}):
            h.tick(0)
        monitor.assert_not_called()

    def test_the_outside_address_change_is_told_without_the_address(self):
        app, h = make(address={"on": True})
        with mock.patch.object(h, "outside_addresses", return_value={"gluetun": "203.0.113.5"}):
            h.tick(1000, reading(0))
            h.tick(1000 + host_alerts.ADDRESS_EVERY, reading(1))  # the same: nothing
        self.assertEqual(self.alerted(app), [])
        with mock.patch.object(h, "outside_addresses", return_value={"gluetun": "203.0.113.9"}), \
                mock.patch.object(app.watch, "alert", wraps=app.watch.alert) as alert:
            h.tick(1000 + 2 * host_alerts.ADDRESS_EVERY, reading(2))
        self.assertEqual(self.alerted(app), ["host:address:gluetun"])
        text = " ".join(str(x) for x in alert.call_args[0])
        self.assertNotIn("203.0.113", text)
        with mock.patch.object(h, "outside_addresses", return_value={"gluetun": "203.0.113.7"}), \
                mock.patch.object(app.watch, "alert", wraps=app.watch.alert) as alert:
            h.tick(1000 + 3 * host_alerts.ADDRESS_EVERY, reading(3))
        self.assertEqual(alert.call_count, 1)  # a second change is told too

    def test_the_address_is_looked_at_every_ten_minutes_only(self):
        app, h = make(address={"on": True})
        with mock.patch.object(h, "outside_addresses", return_value={"gluetun": "203.0.113.5"}) as look:
            for i in range(5):
                h.tick(1000 + i * 60)
        self.assertEqual(look.call_count, 1)

    def test_a_container_that_stopped_with_an_error_is_told_and_one_stopped_on_purpose_is_not(self):
        app, h = make(container={"on": True})
        up = [{"Names": ["/jellyfin"], "State": "running", "Status": "Up"}, {"Names": ["/sonarr"], "State": "running", "Status": "Up"},
              {"Names": ["/plugin-a"], "State": "running", "Status": "Up"}, {"Names": ["/old"], "State": "running", "Status": "Up"}]
        h.check_containers("Harbour", up)
        down = [{"Names": ["/jellyfin"], "State": "exited", "Status": "Exited (137) 2 minutes ago"},
                {"Names": ["/sonarr"], "State": "exited", "Status": "Exited (0) 2 minutes ago"},
                {"Names": ["/plugin-a"], "State": "exited", "Status": "Exited (0) a minute ago"}]  # old was removed
        h.check_containers("Harbour", down)
        self.assertEqual(self.alerted(app), ["host:container:jellyfin"])
        h.check_containers("Harbour", up)
        self.assertEqual(self.alerted(app), [])

    def test_clean_checks_limits_and_times(self):
        out = host_alerts.clean({"cpu_temp": {"on": True, "limit": 80, "minutes": 15}, "address": {"on": True}, "other": {"on": True}}, DEFAULT)
        self.assertEqual(out["cpu_temp"], {"on": True, "limit": 80, "minutes": 15})
        self.assertTrue(out["address"]["on"])
        self.assertNotIn("other", out)
        for bad in ({"cpu_temp": {"limit": 20}}, {"cpu_temp": {"minutes": 7}}, {"memory": {"limit": 100}}, {"load": 5}):
            with self.assertRaises(config.ConfigError):
                host_alerts.clean(bad, DEFAULT)

    def test_the_settings_are_kept_and_an_older_config_gains_them(self):
        import json
        import os
        import tempfile
        d = tempfile.mkdtemp()
        cfg = config.Config(d)
        self.assertFalse(any(v.get("on") for v in cfg.data["watch"]["host"].values()))  # all off at first
        cfg.update_general({"watch": {"host": {"memory": {"on": True, "limit": 80, "minutes": 5}}}})
        self.assertEqual(cfg.data["watch"]["host"]["memory"], {"on": True, "limit": 80, "minutes": 5})
        self.assertEqual(config.public_watch(cfg.data["watch"])["host"]["memory"]["limit"], 80)
        path = os.path.join(d, "config.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        del data["watch"]["host"]  # a config saved before 0.31.0
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.assertEqual(config.Config(d).data["watch"]["host"]["cpu_temp"], {"on": False, "limit": 85, "minutes": 10})
        with self.assertRaises(config.ConfigError):
            cfg.update_general({"watch": {"host": {"cpu_temp": {"limit": 5}}}})

    def test_a_reading_costs_little(self):
        app, h = make(cpu_temp={"on": True}, load={"on": True}, memory={"on": True}, disk_rate={"on": True})
        h.tick(0)
        started = time.process_time()
        for i in range(200):
            h.tick(60 * (i + 1))
        per = (time.process_time() - started) / 200
        self.assertLess(per, 0.01, f"{per * 1000:.2f} ms a reading")


if __name__ == "__main__":
    unittest.main()
