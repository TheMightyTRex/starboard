"""DASH-543: the full security scan carries its own ZAP tuning, and says what it will do without doing it."""
import os
import subprocess
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "security-scan.sh")


def run(*args, **env):
    return subprocess.run(["bash", SCRIPT, *args], capture_output=True, text=True, timeout=30, env={**os.environ, **env})


class ScanTuning(unittest.TestCase):
    def test_the_defaults_need_no_tuning(self):
        out = run("--full", "--dry-run").stdout
        self.assertIn("--memory 8g --memory-swap 8g", out)
        self.assertIn("-XX:CompileCommand=exclude,java.net.URLDecoder::decode", out)
        self.assertIn("time limit 150 minutes", out)

    def test_each_setting_can_be_changed(self):
        out = run("--dry-run", ZAP_MEMORY="10g", ZAP_TIME_LIMIT="90", ZAP_HEAP="3g").stdout
        self.assertIn("--memory 10g", out)
        self.assertIn("-Xmx3g", out)
        out = run("--full", "--dry-run", ZAP_TIME_LIMIT="90").stdout
        self.assertIn("time limit 90 minutes", out)

    def test_a_bad_option_or_limit_stops_with_words(self):
        for args, env in ((("--nonsense",), {}), (("--dry-run",), {"ZAP_TIME_LIMIT": "soon"})):
            r = run(*args, **env)
            self.assertEqual(r.returncode, 2)
            self.assertTrue(r.stderr.strip())

    def test_the_time_limit_fails_clearly(self):
        text = open(SCRIPT).read()
        self.assertIn('timeout --foreground "${ZAP_TIME_LIMIT}m"', text)
        self.assertIn("did not finish in time", text)


if __name__ == "__main__":
    unittest.main()
