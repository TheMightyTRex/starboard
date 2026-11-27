"""The public API breaking-change check and the weekly compatibility run are in place and pinned (DASH-603)."""
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Setup(unittest.TestCase):
    def read(self, path):
        with open(os.path.join(ROOT, path), encoding="utf-8") as f:
            return f.read()

    def test_the_script_says_not_run_when_oasdiff_is_missing_and_is_never_an_installer(self):
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "oasdiff-check.sh")], capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"}, cwd=ROOT)
        if "oasdiff" in subprocess.run(["bash", "-c", "command -v oasdiff"], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"}).stdout:
            self.skipTest("oasdiff is installed here")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Not run", r.stderr)
        self.assertNotIn("install -", self.read("tools/oasdiff-check.sh"))

    def test_ci_installs_a_pinned_oasdiff_with_its_checksum_and_compares_with_the_last_release(self):
        ci = self.read(".github/workflows/ci.yml")
        self.assertIn("oasdiff_1.41.0_linux_amd64.tar.gz", ci)
        self.assertTrue(re.search(r"[0-9a-f]{64}  oasdiff\.tar\.gz", ci))
        self.assertIn("fetch-depth: 0", ci)
        self.assertIn("OASDIFF=required", ci)
        self.assertIn("--match 'v*'", self.read("tools/oasdiff-check.sh"))
        self.assertIn("--fail-on ERR", self.read("tools/oasdiff-check.sh"))

    def test_the_weekly_run_is_scheduled_pinned_and_short(self):
        w = self.read(".github/workflows/compat-weekly.yml")
        self.assertIn("cron:", w)
        self.assertIn("timeout-minutes: 30", w)
        self.assertEqual(len(re.findall(r"uses: \S+@[0-9a-f]{40}", w)), 3)
        self.assertIn("api_compat.py --frozen", w)
        self.assertIn("smoke_test.py", w)


if __name__ == "__main__":
    unittest.main()
