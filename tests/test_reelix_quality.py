"""Settings, Reelix, Picture quality (DASH-196): levels in words, and changes that keep every row Reelix sent."""
import copy
import unittest

from starboard import reelix_quality as rq
from tests.reelix_stand_in import StandIn


class FakeReelix:
    """The stand-in's answers, as reelix_admin's signed-in client gives them."""

    def __init__(self):
        self.state = StandIn(any_password=True)
        _, _, cookie = self.state.handle("POST", "/auth/login", {"username": "admin", "password": "made-up"})
        self.cookie = cookie.split(";")[0]

    def call(self, method, path, body=None):
        status, answer, _ = self.state.handle(method, path, body, {"Cookie": self.cookie, "x-reelix-request": "1"})
        if status >= 400:
            raise ValueError(f"Reelix said {status}")
        return status, answer


class QualityTest(unittest.TestCase):
    def setUp(self):
        self.reelix = FakeReelix()
        self.hd = copy.deepcopy(self.reelix.state.profiles[0])

    def test_levels_are_the_video_profiles_in_words(self):
        out = rq.state(self.reelix)
        self.assertEqual([lvl["title"] for lvl in out["levels"]], ["HD", "Best"])  # music is left out
        hd = out["levels"][0]
        self.assertTrue(hd["recommended"])
        self.assertEqual(hd["accepts"], ["1080p Blu-ray", "WEB 1080p", "720p web"])
        self.assertEqual(hd["stops_at"], "1080p Blu-ray")
        self.assertEqual(hd["prefers"], ["HEVC (smaller files)"])
        self.assertEqual(hd["never"], ["3D", "files over 20 GB"])
        self.assertEqual(hd["rows"][0], {"key": "q26", "label": "4K Blu-ray", "allowed": False})
        self.assertEqual(hd["stop"], "q21")
        self.assertEqual({x["name"]: x["choice"] for x in hd["extras"]},
                         {"HEVC (smaller files)": "prefer", "HDR": "neutral", "English audio": "neutral", "3D": "never"})

    def order(self, profile):
        rows = rq.describe(profile, [])["rows"]
        keys = [r["key"] for r in rows]
        stop = rq.describe(profile, [])["stop"]
        return keys[:keys.index(stop)] + ["stop"] + keys[keys.index(stop):]

    def test_reordering_keeps_groups_and_moves_the_stop(self):
        order = self.order(self.hd)
        # Put the WEB 1080p group above 1080p Blu-ray, and the stop line above the group.
        order.remove("g1000")
        order.insert(order.index("stop"), "g1000")
        order.remove("stop")
        order.insert(order.index("g1000"), "stop")
        out = rq.change(self.hd, {"order": order})
        group = next(i for i in out["items"] if i.get("items"))
        self.assertEqual(group["items"], ["WEBDL-1080p", "WEBRip-1080p"])  # the group is kept as Reelix sent it
        where = [rq._key(i) for i in out["items"]]  # worst first, as Reelix keeps them
        self.assertGreater(where.index("g1000"), where.index("q21"))  # now above 1080p Blu-ray
        self.assertEqual(out["cutoff"], 1000)  # upgrades stop at the group

    def test_the_stop_must_sit_above_a_ticked_quality(self):
        order = self.order(self.hd)
        order.remove("stop")
        order.append("stop")
        with self.assertRaisesRegex(ValueError, "Stop upgrading here above"):
            rq.change(self.hd, {"order": order})

    def test_at_least_one_quality_is_ticked(self):
        order = self.order(self.hd)
        with self.assertRaisesRegex(ValueError, "Tick at least one"):
            rq.change(self.hd, {"order": order, "allowed": {k: False for k in order if k != "stop"}})

    def test_an_unticked_row_under_the_stop_is_skipped(self):
        order = self.order(self.hd)
        out = rq.change(self.hd, {"order": order, "allowed": {"q21": False}})
        self.assertEqual(out["cutoff"], 1000)  # the next ticked row under the line

    def test_a_changed_list_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Reload the page"):
            rq.change(self.hd, {"order": ["q21", "stop"]})

    def test_extras_keep_their_scores_and_new_ones_get_starboards(self):
        out = rq.change(self.hd, {"extras": {"1": "prefer", "2": "never", "3": "prefer", "4": "neutral"}})
        self.assertEqual(out["format_items"], [{"format_id": 1, "score": 50}, {"format_id": 2, "score": rq.NEVER},
                                               {"format_id": 3, "score": rq.PREFER}])
        with self.assertRaisesRegex(ValueError, "Prefer, Neutral or Never"):
            rq.change(self.hd, {"extras": {"1": "maybe"}})

    def test_largest_file_and_upgrades(self):
        out = rq.change(self.hd, {"largest_gb": "12.5", "upgrades": False})
        self.assertEqual((out["max_size_mb"], out["upgrade_allowed"]), (12500, False))
        self.assertIsNone(rq.change(self.hd, {"largest_gb": ""})["max_size_mb"])
        with self.assertRaisesRegex(ValueError, "between 0.1 and 500"):
            rq.change(self.hd, {"largest_gb": "0"})
        with self.assertRaisesRegex(ValueError, "in GB"):
            rq.change(self.hd, {"largest_gb": "big"})

    def test_save_writes_to_reelix_and_choose_sets_new_films(self):
        out = rq.save(self.reelix, 1, {"upgrades": False})
        self.assertEqual(out["done"], ["HD saved in Reelix"])
        self.assertFalse(self.reelix.state.profiles[0]["upgrade_allowed"])
        self.assertEqual(self.reelix.state.profiles[0]["items"], self.hd["items"])  # nothing else changed
        out = rq.choose(self.reelix, 2)
        self.assertEqual(out["chosen"], 2)
        self.assertEqual(out["done"], ["New films and series use Best"])
        with self.assertRaisesRegex(ValueError, "not in Reelix"):
            rq.save(self.reelix, 3, {"upgrades": True})  # music is not a picture quality


if __name__ == "__main__":
    unittest.main()


class RecommendedTest(unittest.TestCase):
    def test_new_films_use_hd_when_nothing_is_chosen(self):
        reelix = FakeReelix()
        reelix.state.request_settings = {}
        self.assertEqual(rq.state(reelix)["chosen"], 1)  # shown as HD even before it is saved
        self.assertEqual(rq.recommended_for_new(reelix), ["New films and series use HD (1080p)"])
        self.assertEqual(reelix.state.request_settings["movie"]["profile_id"], 1)
        self.assertEqual(rq.recommended_for_new(reelix), [])  # a level already chosen is kept
