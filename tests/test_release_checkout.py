"""A fresh install gets the newest release, not the main branch (DASH-416): Run first after its clone, and install.sh
on a first install from a clone of main; --main keeps main, for testing, and ./update.sh then follows main too."""
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "init.defaultBranch=main"]


def part(path, begin, end):
    text = (ROOT / path).read_text()
    return re.search(rf"# {begin}[^\n]*\n(.*?)# {end}", text, re.S).group(1)


@unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "needs git and bash")
class ReleaseCheckoutTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.origin = os.path.join(self.tmp, "origin")
        os.makedirs(self.origin)
        run = lambda *a: subprocess.run(GIT + list(a), cwd=self.origin, check=True, capture_output=True)  # noqa: E731
        run("init", "-q")
        for name in ("v0.9.0", "v0.10.0", "v0.11.0-dev.1", None):
            pathlib.Path(self.origin, "VERSION").write_text(f"{name or 'main'}\n")
            run("add", "VERSION")
            run("commit", "-q", "-m", name or "not released yet")
            if name:
                run("tag", name)
        self.clone = os.path.join(self.tmp, "starboard")
        subprocess.run(GIT + ["clone", "-q", self.origin, self.clone], check=True, capture_output=True)

    def version(self):
        return pathlib.Path(self.clone, "VERSION").read_text().strip()

    def run_first(self, channel):
        script = part("run-first.sh", "release-functions-begin", "release-functions-end")
        return subprocess.run(["bash", "-c", f"set -uo pipefail\nDIR={self.clone!r}\nCHANNEL={channel}\n{script}\nget_release"],
                              capture_output=True, text=True)

    def test_run_first_checks_out_the_newest_release_not_a_test_build(self):
        self.assertEqual(self.version(), "main")
        r = self.run_first("release")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.version(), "v0.10.0")  # numbers, not letters: 0.10 is after 0.9; -dev.1 is never picked
        self.assertIn("Release v0.10.0", r.stdout)

    def test_run_first_with_no_release_says_so(self):
        subprocess.run(["git", "-C", self.clone, "tag", "-d", "v0.9.0", "v0.10.0"], check=True, capture_output=True)
        subprocess.run(["git", "-C", self.origin, "tag", "-d", "v0.9.0", "v0.10.0"], check=True, capture_output=True)
        self.assertEqual(self.run_first("release").returncode, 1)
        self.assertEqual(self.version(), "main")

    def run_first_flow(self):
        text = (ROOT / "run-first.sh").read_text()
        self.assertIn("--main) CHANNEL=main ;;", text)
        self.assertIn('[ "$CHANNEL" = main ] && cmd+=(--main)', text)
        self.assertRegex(text, r'if \[ "\$CHANNEL" = main \]; then note .*\n\s+elif ! work "Getting the newest release" get_release')

    def test_run_first_offers_main_and_hands_it_to_the_installer(self):
        self.run_first_flow()
        self.assertNotIn("pull --ff-only", (ROOT / "run-first.sh").read_text())  # a release is not on a branch

    def install(self, env_file=None, channel="release", picked=""):
        if env_file is not None:
            pathlib.Path(self.clone, ".env").write_text(env_file)
        script = part("install.sh", "newest-release-begin", "newest-release-end")
        again = os.path.join(self.tmp, "again.sh")
        pathlib.Path(again).write_text('echo "again with $STARBOARD_RELEASE_PICKED $*"\n')
        env = {k: v for k, v in os.environ.items() if k != "STARBOARD_RELEASE_PICKED"}
        if picked:
            env["STARBOARD_RELEASE_PICKED"] = picked
        return subprocess.run(["bash", "-c", f"set -uo pipefail\ncd {self.clone!r}\nCHANNEL={channel}\nARGS=(--yes --port 8100)\n{script}\nnewest_release\necho stayed",
                               again], capture_output=True, text=True, env=env)

    def test_install_on_a_clone_of_main_gets_the_release_and_runs_its_own_installer(self):
        r = self.install()
        self.assertEqual(self.version(), "v0.10.0")
        self.assertIn("again with 1 --yes --port 8100", r.stdout)
        self.assertNotIn("stayed", r.stdout)

    def test_install_keeps_main_when_asked_and_after_the_first_install(self):
        for kwargs in ({"channel": "main"}, {"env_file": "STARBOARD_MODE=docker\n"}, {"picked": "1"}):
            with self.subTest(**kwargs):
                r = self.install(**kwargs)
                self.assertIn("stayed", r.stdout)
                self.assertEqual(self.version(), "main")
                if "env_file" in kwargs:
                    os.remove(os.path.join(self.clone, ".env"))

    def test_install_leaves_changed_files_alone(self):
        pathlib.Path(self.clone, "VERSION").write_text("changed\n")
        r = self.install()
        self.assertIn("stayed", r.stdout)
        self.assertIn("have been changed", r.stdout)

    def test_install_saves_the_channel_and_update_follows_it(self):
        install = (ROOT / "install.sh").read_text()
        self.assertIn('set_env STARBOARD_CHANNEL "$CHANNEL"', install)
        self.assertIn("--main) CHANNEL=main ;;", install)
        self.assertIn("--releases) CHANNEL=release ;;", install)
        update = (ROOT / "update.sh").read_text()
        self.assertIn("s/^STARBOARD_CHANNEL=//p", update)
        self.assertIn("grep -E '^v[0-9]+\\.[0-9]+\\.[0-9]+$'", update)  # update.sh never picks a test build either


if __name__ == "__main__":
    unittest.main()
