"""The Run first script's judgement of this computer (DASH-114, docs/test-plans/setup.md SET-22 to SET-26, SET-35,
SET-41, and install.md INS-07, GEN-04): each check runs on its own with made-up values; nothing is installed."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def checks(call):
    script = (ROOT / "run-first.sh").read_text()
    part = script[script.index("MIN_FREE_GB=10"):script.index("memory_mb() {")]
    done = subprocess.run(["bash", "-c", part + "\n" + call], capture_output=True, text=True, timeout=30)
    return done.stdout


class RunFirstChecksTest(unittest.TestCase):
    def test_a_32_bit_system_stops_with_the_64_bit_words(self):
        for arch in ("armv7l", "armv6l", "i686"):
            self.assertIn("need a 64-bit one", checks(f"arch_stop {arch}"), arch)
            self.assertIn("Raspberry Pi OS (64-bit)", checks(f"arch_stop {arch}"))
        for arch in ("x86_64", "aarch64"):
            self.assertEqual(checks(f"arch_stop {arch}"), "", arch)

    def test_an_older_version_gets_a_note_and_a_newer_or_unnumbered_one_none(self):
        self.assertIn("not tested", checks('version_note debian 12 "Debian 12"'))
        self.assertIn("not tested", checks('version_note ubuntu 24.04 "Ubuntu 24.04"'))
        self.assertIn("not tested", checks('version_note linuxmint 22.1 "Linux Mint 22.1"'))
        for args in ("debian 13 x", "debian 14 x", "ubuntu 26.04 x", "ubuntu 26.10 x", "linuxmint 22.3 x", "linuxmint 23 x",
                     'debian "" "Debian testing"', "fedora 42 x"):
            self.assertEqual(checks(f"version_note {args}"), "", args)

    def test_under_10_gb_free_stops(self):
        self.assertIn("at least 10 GB", checks("space_stop 6"))
        self.assertEqual(checks("space_stop 10"), "")
        self.assertEqual(checks('space_stop ""'), "")  # df gave nothing: no stop

    def test_memory_advice_under_1_and_under_2_gb(self):
        self.assertIn("Less than 1 GB", checks("memory_note 512"))
        self.assertIn("Under 2 GB", checks("memory_note 1800"))
        self.assertEqual(checks("memory_note 4000"), "")

    def test_the_sudo_steps_name_the_user_and_each_command(self):
        out = checks("sudo_steps sam")
        for words in ("su -", "apt install sudo", "usermod -aG sudo sam", "Sign out and back in"):
            self.assertIn(words, out)

    def test_the_stops_come_before_anything_is_installed_and_have_numbers(self):
        script = (ROOT / "run-first.sh").read_text()
        step4 = script[script.index("step_4() {"):script.index("step_5() {")]
        self.assertIn("err RF-06", step4)
        self.assertIn("err RF-07", step4)
        step5 = script[script.index("step_5() {"):script.index("step_6() {")]
        self.assertLess(step5.index("err RF-18"), step5.index("sudo_once"))

    def test_starboard_already_there_offers_update_change_or_keep(self):
        script = (ROOT / "run-first.sh").read_text()
        step6 = script[script.index("step_6() {"):script.index("step_7() {")]
        for words in ("Update it to the newest version (recommended)", "Change the settings", "Keep it as it is"):
            self.assertIn(words, step6)
        self.assertLess(step6.index("(recommended)"), step6.index("Change the settings|"))

    def test_the_hand_over_says_where_the_set_up_continues(self):
        self.assertIn("The set-up continues in your browser", (ROOT / "run-first.sh").read_text())

    def test_the_installer_names_the_ufw_command(self):
        script = (ROOT / "install.sh").read_text()
        self.assertIn("ENABLED=yes' /etc/ufw/ufw.conf", script)
        self.assertIn("sudo ufw allow $PORT/tcp", script)


if __name__ == "__main__":
    unittest.main()
