"""The job scheduler uses a bounded worker pool and deduplicates queued work."""
import queue
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace

from starboard.jobs import Jobs


class JobDispatchTest(unittest.TestCase):
    def test_distinct_jobs_run_without_one_long_job_blocking_the_other(self):
        with tempfile.TemporaryDirectory() as data_dir:
            app = SimpleNamespace(config=SimpleNamespace(data_dir=data_dir, data={"extras": {}, "services": {}}),
                                  data_dir=data_dir)
            jobs = Jobs(app)
            started = queue.Queue()
            release = threading.Event()

            def work(key, force=False):
                started.put(key)
                release.wait(3)

            jobs._execute = work
            jobs.run_soon("livetv")
            jobs.run_soon("import")
            self.assertEqual({started.get(timeout=1), started.get(timeout=1)}, {"livetv", "import"})
            release.set()
            deadline = time.monotonic() + 2
            while jobs.running and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(jobs.running)

    def test_repeated_requests_do_not_queue_duplicate_jobs(self):
        with tempfile.TemporaryDirectory() as data_dir:
            app = SimpleNamespace(config=SimpleNamespace(data_dir=data_dir, data={"extras": {}, "services": {}}),
                                  data_dir=data_dir)
            jobs = Jobs(app)
            started = threading.Event()
            release = threading.Event()
            calls = []

            def work(key, force=False):
                calls.append(key)
                started.set()
                release.wait(3)

            jobs._execute = work
            jobs.run_soon("livetv")
            self.assertTrue(started.wait(1))
            for _ in range(20):
                jobs.run_soon("livetv")
            self.assertEqual(calls, ["livetv"])
            release.set()
            deadline = time.monotonic() + 2
            while jobs.running and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(jobs.running)
            self.assertEqual(calls, ["livetv"])

    def test_unknown_job_is_ignored(self):
        with tempfile.TemporaryDirectory() as data_dir:
            app = SimpleNamespace(config=SimpleNamespace(data_dir=data_dir, data={"extras": {}, "services": {}}),
                                  data_dir=data_dir)
            jobs = Jobs(app)
            jobs.run_soon("not-a-job")
            self.assertEqual(jobs.pending, set())
            self.assertEqual(jobs.work.qsize(), 0)


if __name__ == "__main__":
    unittest.main()
