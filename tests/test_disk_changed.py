"""disk.changed (plug-in API 1.16, owner, 19 November 2026, issue #187 accepted as a known risk with an alert): every
pool job the root helper finishes is reported, however it was asked for, from the job record only the helper writes."""
import unittest
from unittest import mock

from starboard import plugin_life, plugins, pool_helper


class DiskChanged(unittest.TestCase):
    def setUp(self):
        self.w = plugin_life.EventWatch()
        self.sent = []
        self.send = lambda name, data: self.sent.append((name, data)) or 1
        self.job = {"id": "abc123", "action": "add", "state": "running", "drive": "pool3", "erased": ["pool3"]}

    def check(self):
        return self.w._pool({"disk.changed"}, self.send, lambda: dict(self.job))

    def test_a_finished_job_is_sent_once_and_never_at_the_first_check(self):
        self.job.update(state="done", finished="2026-11-19T10:00:00Z")
        with mock.patch.object(plugin_life.logs, "event"):
            self.assertEqual(self.check(), 0)  # the first check sets the starting point: nothing old is sent
            self.job.update(id="def456", finished="2026-11-19T11:00:00Z")
            self.assertEqual(self.check(), 1)
            self.assertEqual(self.check(), 0)  # the same job is not sent again
        name, data = self.sent[0]
        self.assertEqual(name, "disk.changed")
        self.assertEqual(data, {"action": "add", "state": "done", "disk": "pool3", "erased": ["pool3"], "result": ""})

    def test_a_running_job_is_not_sent_and_an_erase_is_logged_as_a_warning(self):
        with mock.patch.object(plugin_life.logs, "event") as log:
            self.check()
            self.assertEqual(self.check(), 0)
            self.job.update(state="done", finished="2026-11-19T11:00:00Z")
            self.check()
        self.assertEqual(log.call_args[0][0], "warning")
        self.assertIn("erased pool3", log.call_args[0][2])

    def test_nothing_without_a_listener_or_a_pool(self):
        self.assertEqual(self.w._pool(set(), self.send, lambda: self.job), 0)
        self.assertEqual(self.w._pool({"disk.changed"}, self.send, None), 0)
        self.assertEqual(self.w._pool({"disk.changed"}, self.send, lambda: (_ for _ in ()).throw(OSError("no helper"))), 0)

    def test_the_event_is_known_and_polled(self):
        self.assertEqual(plugins.EVENTS["disk.changed"][0], "system:read")
        self.assertIn("disk.changed", plugin_life.POLLED)

    def test_the_helper_records_the_disk_and_what_it_erases(self):
        class Host:
            state = "/nonexistent"

            def publish(self, *a):
                pass
        plan = {"id": "p1", "action": "add", "entry": {"label": "pool3"},
                "steps": [{"do": "unmount"}, {"do": "erase", "label": "pool3", "by_id": "/dev/disk/by-id/x"}]}
        with mock.patch.object(pool_helper, "write_json"):
            job = pool_helper.Job(Host(), plan)
        self.assertEqual(job.data["drive"], "pool3")
        self.assertEqual(job.data["erased"], ["pool3"])
