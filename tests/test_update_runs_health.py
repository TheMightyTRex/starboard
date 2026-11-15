"""The health wait after an app update (DASH-422, release 0.19.0): a version that keeps exiting and being started
again by its restart policy is running for a moment between tries, and must not count as working."""
import unittest
from unittest import mock

from starboard import containers, update_runs


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


class AppHealthWait(unittest.TestCase):
    def wait(self, listing, inspect):
        clock = Clock()
        with mock.patch.object(containers, "containers", side_effect=lambda: listing(clock.t)), \
             mock.patch.object(containers, "docker", side_effect=lambda m, path: inspect(clock.t)):
            return update_runs._app_healthy("app", wait=60, sleep=clock.sleep, clock=clock), clock.t

    def test_a_steady_app_counts_after_a_steady_spell(self):
        (ok, why), took = self.wait(lambda t: [{"id": "c1", "name": "app", "state": "running", "status": "Up"}],
                                    lambda t: {"RestartCount": 0, "State": {"StartedAt": "a"}})
        self.assertTrue(ok, why)
        self.assertGreaterEqual(took, update_runs.APP_STEADY)

    def test_an_app_that_keeps_restarting_does_not(self):
        # Seen running each time it is looked at, but started again in between: a new start each look.
        (ok, why), _ = self.wait(lambda t: [{"id": "c1", "name": "app", "state": "running", "status": "Up Less than a second"}],
                                 lambda t: {"RestartCount": int(t), "State": {"StartedAt": str(t)}})
        self.assertFalse(ok)
        self.assertIn("kept stopping and starting again", why.lower())

    def test_running_only_between_restarts_does_not(self):
        states = lambda t: "running" if int(t) % 10 == 0 else "restarting"  # noqa: E731
        (ok, why), _ = self.wait(lambda t: [{"id": "c1", "name": "app", "state": states(t), "status": ""}],
                                 lambda t: {"RestartCount": int(t), "State": {"StartedAt": str(t)}})
        self.assertFalse(ok)

    def test_an_unhealthy_app_does_not(self):
        (ok, why), _ = self.wait(lambda t: [{"id": "c1", "name": "app", "state": "running", "status": "Up 1 minute (unhealthy)"}],
                                 lambda t: {"RestartCount": 0, "State": {"StartedAt": "a"}})
        self.assertFalse(ok)
        self.assertIn("not healthy", why)


if __name__ == "__main__":
    unittest.main()
