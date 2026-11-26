"""Find all wanted (26 November 2026): the count, the limits and the run."""
import tempfile
import time
import unittest
from unittest import mock

from starboard import find_wanted as fw


def listing(total):
    def fake(all_services, which, kind, page=1):
        start = (page - 1) * 50
        ids = list(range(start + 1, min(total, start + 50) + 1))
        return {"items": [{"id": i} for i in ids], "total": total, "page": page, "page_size": 50}
    return fake


def wait_done(timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        if fw.status().get("state") in ("done", "stopped", "failed"):
            return fw.status()
        time.sleep(0.01)
    raise AssertionError("the run did not end")


class FindWantedTest(unittest.TestCase):
    def setUp(self):
        fw._reset_for_tests()
        self.dir = tempfile.TemporaryDirectory()
        self.data = self.dir.name
        self.patches = [mock.patch.object(fw, "GAP", 0), mock.patch.object(fw.wanted, "listing", side_effect=listing(35))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        fw._reset_for_tests()
        self.dir.cleanup()

    def test_the_count_comes_first(self):
        plan = fw.preview({}, self.data, "tv")
        self.assertEqual((plan["wanted"], plan["to_search"], plan["left_out"], plan["more"]), (35, 35, 0, 0))
        self.assertEqual(plan["group"], 10)

    def test_a_run_is_ten_at_a_time_and_remembers_what_it_searched(self):
        with mock.patch.object(fw.wanted, "search") as search:
            fw.start({}, self.data, "tv")
            done = wait_done()
        self.assertEqual([len(c.args[3]) for c in search.call_args_list], [10, 10, 10, 5])
        self.assertEqual((done["state"], done["searched"], done["total"]), ("done", 35, 35))
        again = fw.preview({}, self.data, "tv")
        self.assertEqual((again["to_search"], again["left_out"]), (0, 35))  # nothing is searched twice in a day

    def test_at_most_a_hundred_in_a_run(self):
        with mock.patch.object(fw.wanted, "listing", side_effect=listing(340)):
            plan = fw.preview({}, self.data, "films")
        self.assertEqual((plan["to_search"], plan["more"], plan["wanted"]), (100, 240, 340))

    def test_one_run_at_a_time_and_a_rest_after_it(self):
        gate = mock.Mock(side_effect=lambda *a: time.sleep(0.2))
        with mock.patch.object(fw.wanted, "search", gate):
            fw.start({}, self.data, "tv")
            with self.assertRaisesRegex(ValueError, "running already"):
                fw.start({}, self.data, "films")
            wait_done()
        with self.assertRaisesRegex(ValueError, "Try again in"):
            fw.start({}, self.data, "films")

    def test_stop_ends_it_after_the_group_that_is_going(self):
        def slow(*a):
            time.sleep(0.05)
        with mock.patch.object(fw.wanted, "search", side_effect=slow), mock.patch.object(fw, "GAP", 30):
            fw.start({}, self.data, "tv")
            time.sleep(0.1)
            fw.stop()
            done = wait_done()
        self.assertEqual(done["state"], "stopped")
        self.assertLess(done["searched"], 35)

    def test_download_hours_make_it_wait_then_carry_on(self):
        hours = iter([True, True, False] + [False] * 20)
        with mock.patch.object(fw.wanted, "search") as search, mock.patch.object(fw, "HOURS_POLL", 0.01):
            fw.start({}, self.data, "tv", paused=lambda: next(hours))
            done = wait_done(8)
        self.assertEqual(done["state"], "done")
        self.assertEqual(search.call_count, 4)

    def test_a_failure_says_so_and_leaves_the_rest(self):
        with mock.patch.object(fw.wanted, "search", side_effect=fw.services.ServiceError("Reelix is down")):
            fw.start({}, self.data, "tv")
            done = wait_done()
        self.assertEqual((done["state"], done["said"]), ("failed", "Reelix is down"))

    def test_radio_searches_each_show_that_has_wanted_episodes(self):
        shows = [[{"id": 1, "statistics": {"wanted_count": 2}}, {"id": 2, "statistics": {"wanted_count": 0}},
                  {"id": 3, "statistics": {"wanted_count": 4}, "follow": "none"}, {"id": 4, "statistics": {"wanted_count": 1}}]]
        calls = []
        with mock.patch.object(fw.library, "reelix_of", return_value={"name": "r"}), \
                mock.patch.object(fw.library, "_pages", return_value=iter(shows)), \
                mock.patch.object(fw.services, "_api", side_effect=lambda r, path, params=None, method="GET", body=None, **k: calls.append((method, path))):
            plan = fw.preview({}, self.data, "radio")
            self.assertEqual((plan["wanted"], plan["to_search"]), (3, 2))
        with mock.patch.object(fw.library, "reelix_of", return_value={"name": "r"}), \
                mock.patch.object(fw.library, "_pages", side_effect=lambda *a, **k: iter(shows)), \
                mock.patch.object(fw.services, "_api", side_effect=lambda r, path, params=None, method="GET", body=None, **k: calls.append((method, path))):
            fw.start({}, self.data, "radio")
            wait_done()
        self.assertEqual([c for c in calls if c[0] == "POST"], [("POST", "/radio/shows/1/search"), ("POST", "/radio/shows/4/search")])


if __name__ == "__main__":
    unittest.main()
