"""The 0.31.1 bridge (DASH-596): Starboard 0.40.0 cannot be undone, so the automatic update and Install all updates stop
at it, Update now says so in plain words and needs a yes, and an update from a script is refused with the same words."""
import datetime as dt
import pathlib
import tempfile
import unittest
from unittest import mock

from starboard import self_update, update_batch

NIGHT = dt.datetime(2026, 11, 28, 2)


class Bridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = mock.Mock(data_dir=self.tmp.name, version="0.31.1", watch=None, config=mock.Mock(data={"starboard_auto_update": True}))
        self.app.latest_release.return_value = "v0.40.0"
        mock.patch.object(self_update, "plan", return_value={"how": "native", "folder": "/srv/starboard"}).start()

    def tearDown(self):
        mock.patch.stopall()
        self.tmp.cleanup()

    def test_what_crosses_the_break(self):
        crosses = self_update.crosses_break
        self.assertTrue(crosses("0.31.1", "v0.40.0"))
        self.assertTrue(crosses("0.31.0", "0.41.2"))
        self.assertFalse(crosses("0.31.1", "v0.32.0"))
        self.assertFalse(crosses("0.40.0", "v0.40.1"))
        self.assertFalse(crosses("main", "v0.40.0"))

    def test_the_automatic_update_stops_at_0_40_0_and_still_does_the_rest(self):
        on = {"starboard_auto_update": True}
        action, said = self_update.automatic_decision(on, NIGHT, "v0.40.0", "0.31.1", {})
        self.assertEqual(action, "wait")
        self.assertIn("cannot be undone, so it waits for you", said)
        self.assertEqual(self_update.automatic_decision(on, NIGHT, "v0.31.2", "0.31.1", {}), ("update", "v0.31.2"))

    def test_update_now_needs_the_yes_and_says_the_words(self):
        with self.assertRaises(self_update.Refused) as r:
            self_update.start(self.app, "v0.40.0", by="api")
        self.assertIn("You cannot go back to an older Starboard", str(r.exception))
        with mock.patch.object(self_update, "launch"), mock.patch.object(self_update, "_follow"):
            self_update.start(self.app, "v0.40.0", by="you", one_way_ok=True)
        log = pathlib.Path(self.tmp.name, self_update.LOG).read_text()
        self.assertIn("== This update cannot be undone", log)
        self.assertIn("the update log shows its name", log)
        self.assertLess(log.index("Preparing the update"), log.index("cannot be undone"))

    def test_an_ordinary_update_needs_no_yes_and_has_no_warning(self):
        self.app.version = "0.31.1"
        with mock.patch.object(self_update, "launch"), mock.patch.object(self_update, "_follow"):
            self_update.start(self.app, "v0.32.0")
        self.assertNotIn("cannot be undone", pathlib.Path(self.tmp.name, self_update.LOG).read_text())

    def test_the_page_is_told(self):
        status = self_update.status(self.app)
        self.assertTrue(status["one_way"])
        self.assertIn("cannot be undone", status["one_way_words"])

    def test_install_all_updates_holds_starboard_back(self):
        target = {"id": "starboard", "kind": "starboard", "name": "Starboard", "current": "0.31.1", "latest": "0.40.0",
                  "update_available": True, "can_update": True}
        with mock.patch.object(update_batch.update_runs, "targets", return_value=[target]), \
             mock.patch("starboard.auto_updates._jf", return_value=None):
            plan = update_batch.plan(self.app)
        self.assertEqual(plan["items"], [])
        self.assertIn("cannot be undone", plan["held"][0]["why"])


if __name__ == "__main__":
    unittest.main()
