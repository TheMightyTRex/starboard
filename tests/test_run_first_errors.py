"""Every error number Run first and the installer print is on the help page, and the page has no others."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class RunFirstErrorsTest(unittest.TestCase):
    def test_script_and_help_page_list_the_same_numbers(self):
        script = (ROOT / "run-first.sh").read_text()
        page = (ROOT / "docs/help/topics/run-first-errors.md").read_text()
        installer = (ROOT / "install.sh").read_text() + (ROOT / "starboard/terminal_setup.py").read_text()
        used = set(re.findall(r"\bRF-\d\d\b", script)) | set(re.findall(r"\bIN-\d\d\b", installer))
        explained = set(re.findall(r"^### ((?:RF|IN)-\d\d)$", page, re.M))
        self.assertTrue(used)
        self.assertEqual(used, explained)

    def test_the_link_points_at_the_page(self):
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('ERR_URL="https://themightytrex.github.io/starboard/help/topics/run-first-errors.html"', script)


class InstallerStopNoteTest(unittest.TestCase):
    """DASH-147: the installer writes how it stopped for the Run first script, which then ends on that number."""

    def test_the_installer_writes_its_error_number(self):
        import os
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            note = os.path.join(d, "stopped-with")
            env = dict(os.environ, STARBOARD_ERROR_FILE=note)
            done = subprocess.run([str(ROOT / "install.sh"), "--not-an-option"], env=env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=30)
            self.assertEqual(done.returncode, 2)
            self.assertIn("Error IN-01. What it means and how to fix it:", done.stderr)
            self.assertEqual(open(note).read().strip(), "IN-01")

    def test_run_first_ends_on_the_installers_number_not_its_own(self):
        script = (ROOT / "run-first.sh").read_text()
        ending = script[script.index('inner="$(head -n 1 "$STARBOARD_ERROR_FILE"'):]
        ending = ending[:ending.index("esac")]
        self.assertIn('err "$inner"', ending)
        self.assertLess(ending.index("stopped)"), ending.index("err RF-40"))
        self.assertEqual(ending.count("err RF-40"), 1)  # only when the installer gave no number

    def test_a_person_stopping_is_noted_without_a_number(self):
        frame = (ROOT / "lib/terminal-frame.sh").read_text()
        self.assertIn("stopped_by_person; exit 1", frame)
        self.assertIn("stopped_by_person; exit 130", frame)



class PlainCarriesOnTest(unittest.TestCase):
    def test_second_installer_run_keeps_accessible_mode(self):
        # Run first runs the installer again for the set-up's changes to this computer; in accessible mode that run
        # must be plain too, or the very last page is boxed (night of 8 November 2026).
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('[ -z "$PLAIN" ] || again+=(--plain)', script)
        plain_choice = 'case "$first" in a|A) FANCY=0; PLAIN=1'
        self.assertIn(plain_choice, script)


class DockerGroupRestartTest(unittest.TestCase):
    def test_settings_survive_sudo_rs(self):
        # sudo-rs (Ubuntu 26.04) ignores --preserve-env, so the settings go through env by name (8 November 2026).
        for name in ("install.sh", "run-first.sh"):
            script = (ROOT / name).read_text()
            self.assertNotIn("sudo --preserve-env", script, name)
            self.assertIn('-g docker -- env "${keep[@]}"', script, name)
            self.assertIn("STARBOARD_*|TERM|", script, name)


if __name__ == "__main__":
    unittest.main()


class WaitForUpdatesTest(unittest.TestCase):
    """Linux installing its own updates (RF-12): Run first waits with a bar, then carries on (owner, 10 November 2026)."""

    def run_part(self, busy_checks, wait_max):
        import os
        import subprocess
        import tempfile
        script = (ROOT / "run-first.sh").read_text()
        start = script.index("UPDATES_WAIT_MAX=")
        part = script[start:script.index("is_package_job()", start)]
        with tempfile.TemporaryDirectory() as d:
            count = os.path.join(d, "count")
            open(count, "w").write("0")
            fake = os.path.join(d, "pgrep")  # says unattended-upgrades runs for the first few checks
            open(fake, "w").write(f'#!/bin/sh\nn=$(cat {count}); echo $((n + 1)) > {count}\n'
                                  f'[ "$2" = unattended-upgr ] && [ "$n" -lt {busy_checks} ] && exit 0\nexit 1\n')
            os.chmod(fake, 0o755)
            body = (f"UPDATES_WAIT_MAX={wait_max}\n" + part.replace("UPDATES_WAIT_MAX=\"${UPDATES_WAIT_MAX:-2700}\"", "")
                    .replace("sleep 3", "sleep 0.05").replace("sleep 2", "sleep 0") +
                    "\nupdates_busy && echo BUSY; updates_detail; echo; wait_for_updates_job; echo \"status=$?\"\n")
            return subprocess.run(["bash", "-c", body], env={"PATH": f"{d}:/usr/bin:/bin"}, capture_output=True, text=True, timeout=30).stdout

    def test_waits_until_the_updates_finish_then_carries_on(self):
        out = self.run_part(busy_checks=40, wait_max=60)
        self.assertIn("BUSY", out)
        self.assertIn("automatic updates are running", out)
        self.assertIn("status=0", out)

    def test_gives_up_after_the_longest_wait_with_the_lock_words(self):
        out = self.run_part(busy_checks=10**6, wait_max=0)
        self.assertIn("Could not get lock", out)  # so explain() still says RF-12
        self.assertIn("status=1", out)

    def test_install_jobs_wait_first_and_retry_on_a_held_lock(self):
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('if is_package_job "${FIX[$i]}"; then wait_for_updates', script)
        self.assertIn('held_lock && [ "$lock_tries" -lt 2 ]', script)
