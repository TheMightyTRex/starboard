"""Your drives in the terminal set-up (DASH-87): answers typed in turn against a pretend pool helper, which records
what it was asked to do."""
import io
import unittest

from starboard import terminal_setup as ts
from tests.test_terminal_setup import Answers

TB = 1000 ** 4


def drive(n, size, ends, files=0, use="free"):
    return {"name": f"sd{n}", "by_id": f"/dev/disk/by-id/ata-D{n}_{ends}", "model": f"Drive {n}", "size": size,
            "ends": ends, "files": files, "use": use, "parts": []}


class Helper:
    def __init__(self, drives):
        self.drives, self.calls = drives, []

    def __call__(self, args):
        self.calls.append(args)
        if args[0] == "drives":
            return self.drives
        if args[0] == "plan":
            return {"id": f"{len(self.calls):012x}", "steps": [{"say": "Moves 1 folder"}], "moves": [1]}
        return {"state": "done", "steps": [{"say": f"Done: {' '.join(args)}", "state": "done"}]}


class DrivesStepTest(unittest.TestCase):
    def run_step(self, helper, typed):
        out = io.StringIO()
        term = ts.Terminal(out=out, ask=Answers(typed), secret=Answers([]), fancy=False)
        state = {"pool_run": helper}
        ts.add_drives_step(True)
        try:
            self.assertTrue(ts.step_drives(None, term, state))
        finally:
            ts.STEP_FUNCTIONS.remove(ts.step_drives)
            ts.STEPS.remove("Your drives")
        return out.getvalue(), state

    def test_a_pool_with_a_parity_drive_and_kept_files(self):
        h = Helper([drive(1, 4 * TB, "7Q2K", files=3 * TB), drive(2, 3 * TB, "A81F"), drive(3, 4 * TB, "55B0")])
        # Yes; drives 1 and 2 (the biggest empty one is kept back for parity); keep 1's files; parity on drive 3;
        # serial endings for drives 2 and 3; yes; no balancing now.
        text, state = self.run_step(h, ["", "", "", "", "a81f", "55B0", "y", ""])
        self.assertIn("step 4 of 14", text)  # after Your password, How to start and Storage
        self.assertIn("Check before anything changes", text)
        plans = [c for c in h.calls if c[0] == "plan"]
        self.assertEqual(plans[0], ["plan", "add", h.drives[0]["by_id"], "--as", "pool"])
        self.assertEqual(plans[1], ["plan", "add", h.drives[1]["by_id"], "--as", "pool", "--erase"])
        self.assertEqual(plans[2], ["plan", "add", h.drives[2]["by_id"], "--as", "parity", "--erase"])
        applies = [c for c in h.calls if c[0] == "apply"]
        self.assertEqual(applies[1][-1], f"{h.drives[1]['by_id']}=A81F")
        self.assertEqual(state["pool_dir"], "/mnt/pool")

    def test_a_wrong_serial_is_asked_again_and_no_changes_nothing(self):
        h = Helper([drive(1, 2 * TB, "0C3D")])
        text, state = self.run_step(h, ["", "", "1234", "0c3d", "n"])
        self.assertIn("That is not 0C3D", text)
        self.assertIn("Nothing was changed", text)
        self.assertEqual([c[0] for c in h.calls], ["drives"])
        self.assertNotIn("pool_dir", state)

    def test_saying_no_to_a_pool_asks_nothing_else(self):
        h = Helper([drive(1, 2 * TB, "0C3D")])
        self.run_step(h, ["2"])
        self.assertEqual(h.calls, [["drives"]])


if __name__ == "__main__":
    unittest.main()
