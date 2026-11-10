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
    """Linux installing its own updates (RF-12): Run first waits with a bar and says where the updates are up to,
    then carries on (owner, 10 November 2026). Ubuntu's always-running unattended-upgrade-shutdown is not updates."""

    SHUTDOWN = "/usr/bin/python3 /usr/share/unattended-upgrades/unattended-upgrade-shutdown --wait-for-signal"
    UPDATER = "/usr/bin/python3 /usr/bin/unattended-upgrade"

    def run_part(self, busy_checks, wait_max, extra=""):
        import os
        import subprocess
        import tempfile
        script = (ROOT / "run-first.sh").read_text()
        start = script.index("UPDATES_WAIT_MAX=")
        part = script[start:script.index("is_package_job()", start)]
        with tempfile.TemporaryDirectory() as d:
            count = os.path.join(d, "count")
            open(count, "w").write("0")
            for name, body in (
                    ("sudo", "#!/bin/sh\nexit 1\n"),  # no sudo without a password: the command-line check
                    ("ps", f'#!/bin/sh\nn=$(cat {count}); echo $((n + 1)) > {count}\necho "{self.SHUTDOWN}"\n'
                           f'[ "$n" -lt {busy_checks} ] && echo "{self.UPDATER}"\nexit 0\n')):
                open(os.path.join(d, name), "w").write(body)
                os.chmod(os.path.join(d, name), 0o755)
            log = os.path.join(d, "dpkg.log")
            open(log, "w").write("2026-11-10 09:59:00 status installed old-one:amd64 1\n"
                                 "2026-11-10 10:01:00 status installed libc6:amd64 2\n"
                                 "2026-11-10 10:02:00 upgrade linux-firmware:all 1 2\n"
                                 "2026-11-10 10:02:01 status unpacked linux-firmware:all 2\n")
            body = (f"UPDATES_WAIT_MAX={wait_max}\nDPKG_LOG={log}\n" + part.replace("UPDATES_WAIT_MAX=\"${UPDATES_WAIT_MAX:-2700}\"", "")
                    .replace("sleep 3", "sleep 0.05").replace("sleep 2", "sleep 0") + extra +
                    "\nWAIT_SINCE='2026-11-10 10:00:00'; updates_busy >/dev/null && echo BUSY; updates_detail; echo; wait_for_updates_job; echo \"status=$?\"\n")
            return subprocess.run(["bash", "-c", body], env={"PATH": f"{d}:/usr/bin:/bin"}, capture_output=True, text=True, timeout=30).stdout

    def test_waits_until_the_updates_finish_then_carries_on(self):
        out = self.run_part(busy_checks=40, wait_max=60)
        self.assertIn("BUSY", out)
        self.assertIn("Linux's automatic updates: installing linux-firmware, 1 done", out)
        self.assertIn("status=0", out)

    def test_the_shutdown_helper_alone_is_not_updates(self):
        out = self.run_part(busy_checks=0, wait_max=60)
        self.assertNotIn("BUSY", out)
        self.assertIn("status=0", out)

    def test_gives_up_after_the_longest_wait_with_the_lock_words(self):
        out = self.run_part(busy_checks=10**6, wait_max=0)
        self.assertIn("Could not get lock", out)  # so explain() still says RF-12
        self.assertIn("status=1", out)

    def test_install_jobs_wait_first_and_retry_on_a_held_lock(self):
        script = (ROOT / "run-first.sh").read_text()
        self.assertIn('if is_package_job "${FIX[$i]}"; then wait_for_updates', script)
        self.assertIn('held_lock && [ "$lock_tries" -lt 2 ]', script)


class InstallerAddsDockerTest(unittest.TestCase):
    """install.sh adds Docker when it is missing, as a requirement (owner, 10 November 2026). Only its install_docker
    step runs here, with sudo, curl and Docker as stand-ins that write down what they are asked: nothing is installed."""

    def run_step(self, os_words, have_curl=True, have_docker=False):
        import os
        import subprocess
        import tempfile
        script = (ROOT / "install.sh").read_text()
        step = script[script.index("DW_N=0"):script.index("if ! command -v docker >/dev/null || ! docker compose version")]
        step = step + "\n" + script[script.index("docker_os() {"):script.index("DW_N=0")] if "docker_os() {" not in step else step
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "log")
            for name in ("sudo", "curl"):
                with open(os.path.join(d, name), "w") as f:
                    f.write(f'#!/bin/sh\necho "{name} $*" >> {log}\nexit 0\n')
                os.chmod(os.path.join(d, name), 0o755)
            missing = "" if have_curl else "curl"
            wrapper = f"""
WORK={d}; ARGS=(); STARBOARD_REGROUPED=1
para() {{ :; }}; ok() {{ echo "OK $1" >> {log}; }}; finish() {{ :; }}
fail() {{ echo "FAIL $1 $2" >> {log}; exit 1; }}
work() {{ [ $# -eq 4 ] || {{ echo "FAIL work needs 4 arguments, got $#" >> {log}; exit 1; }}; echo "WORK $1" >> {log}; bash -c "$2"; }}
command() {{ if [ "$1" = -v ] && {{ [ "$2" = {"docker" if not have_docker else "none"} ] || [ "$2" = "{missing or 'none'}" ]; }}; then return 1; fi; builtin command "$@"; }}
docker() {{ [ "$1" = compose ] && return 1; return 0; }}
{step}
docker_os() {{ echo "{os_words}"; }}
install_docker
"""
            env = dict(os.environ, PATH=f"{d}:/usr/bin:/bin")
            done = subprocess.run(["bash", "-c", wrapper], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30)
            from pathlib import Path
            return done.returncode, Path(log).read_text() if os.path.exists(log) else ""

    def test_docker_is_installed_with_dockers_own_installer(self):
        code, log = self.run_step("ubuntu debian")
        self.assertEqual(code, 0, log)
        self.assertIn("curl -fsSL https://get.docker.com", log)
        self.assertIn("get-docker.sh", log)
        import shutil
        if shutil.which("systemctl"):  # a computer without systemd has no service to start
            self.assertIn("sudo systemctl enable --now docker", log)
        self.assertIn("OK Docker and Docker Compose are installed.", log)

    def test_mint_gets_dockers_packages(self):
        code, log = self.run_step("linuxmint ubuntu")
        self.assertEqual(code, 0, log)
        self.assertIn("apt-get install -y docker.io docker-compose-v2", log)
        self.assertNotIn("get.docker.com", log)

    def test_only_compose_is_added_when_docker_is_there(self):
        code, log = self.run_step("ubuntu debian", have_docker=True)
        self.assertEqual(code, 0, log)
        self.assertIn("apt-get install -y docker-compose-v2", log)
        self.assertNotIn("get-docker", log)


class SetUpHelperTest(unittest.TestCase):
    """starter.sh, the set-up helper (owner, 10 November 2026): it makes the set-up's change when the browser asks, with
    only the set-up's answers, never sudo. A stand-in installer writes down what it is asked; nothing is installed."""

    def test_the_change_is_made_and_disk_health_left_for_the_password(self):
        import json
        import os
        import shutil
        import subprocess
        import tempfile
        import time
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(ROOT / "starter.sh", d)
            with open(os.path.join(d, "install.sh"), "w") as f:
                f.write('#!/bin/sh\necho "$@" > asked\nexit 0\n')
            os.chmod(os.path.join(d, "install.sh"), 0o755)
            bin_dir = os.path.join(d, "bin")
            os.mkdir(bin_dir)
            with open(os.path.join(bin_dir, "sudo"), "w") as f:
                f.write("#!/bin/sh\nexit 1\n")  # no sudo without a password
            os.chmod(os.path.join(bin_dir, "sudo"), 0o755)
            live = os.path.join(d, "livetv")
            os.mkdir(live)
            os.makedirs(os.path.join(d, "data", "stack"))
            with open(os.path.join(d, "data", "setup-host.json"), "w") as f:
                json.dump({"args": ["--livetv-folder", live, "--disk-health", "--disk", "Media=/etc"]}, f)
            open(os.path.join(d, "data", "stack", "host-request"), "w").close()
            env = dict(os.environ, PATH=f"{bin_dir}:/usr/bin:/bin")
            helper = subprocess.Popen(["bash", os.path.join(d, "starter.sh")], cwd=d, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                progress = os.path.join(d, "data", "stack", "host-progress.json")
                for _ in range(40):
                    if os.path.exists(progress) and json.loads(Path(progress).read_text())["state"] != "running":
                        break
                    time.sleep(0.25)
                state = json.loads(Path(progress).read_text())
                asked = Path(d, "asked").read_text().split()
                left = json.loads(Path(d, "data", "setup-host.json").read_text())["args"]
                log = Path(d, "data", "stack", "host.log").read_text()
            finally:
                helper.terminate()
                helper.wait(timeout=5)
        self.assertEqual(state["state"], "needs-password")
        self.assertEqual(asked, ["--yes", "--plain", "--livetv-folder", live])  # /etc is never used
        self.assertEqual(left, ["--disk-health"])
        self.assertIn("Left out: --disk Media=/etc", log)


class DockerStepWithTheRealFrameTest(unittest.TestCase):
    """VM test N2: install_docker runs before the installer's first page, with the real terminal frame and set -u.
    sudo and curl are stand-ins; the frame's own work() runs, so a value it needs that is not set yet fails here."""

    @unittest.skipUnless(__import__("shutil").which("script"), "script (util-linux) is not on this computer")
    def test_the_docker_step_runs_before_any_page(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        script = (ROOT / "install.sh").read_text()
        step = script[script.index("# dwork \"name\""):script.index("if ! command -v docker >/dev/null || ! docker compose version")]
        with tempfile.TemporaryDirectory() as d:
            for name in ("sudo", "curl"):
                Path(d, name).write_text(f'#!/bin/sh\necho "{name} $*" >> {d}/log\nexit 0\n')
                os.chmod(Path(d, name), 0o755)
            wrapper = f"""set -euo pipefail
cd {ROOT}
WORK={d}; LOG={d}/install.log; ARGS=(); STARBOARD_REGROUPED=1; PLAIN=""; IN=/dev/tty; TTY=/dev/tty
stty rows 24 cols 80 < /dev/tty
. lib/terminal-frame.sh
[ "$FANCY" = 1 ] || echo "NOT FANCY" >> {d}/log
fail() {{ echo "FAIL $1 $2" >> {d}/log; exit 1; }}
command() {{ if [ "$1" = -v ] && [ "$2" = docker ]; then return 1; fi; builtin command "$@"; }}
docker() {{ return 1; }}
{step}
docker_os() {{ echo "ubuntu debian"; }}
install_docker
"""
            Path(d, "run.sh").write_text(wrapper)
            # In a pretend terminal (script), as a person runs it: the frame then draws in full, where N2 crashed.
            done = subprocess.run(["script", "-qec", f"bash {d}/run.sh 2>{d}/err", "/dev/null"], env=dict(os.environ, PATH=f"{d}:/usr/bin:/bin", TERM="xterm", LANG="C.UTF-8", LC_ALL="C.UTF-8"),
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
            done.stderr = Path(d, "err").read_text() if Path(d, "err").exists() else ""
            log = Path(d, "log").read_text() if Path(d, "log").exists() else ""
        self.assertNotIn("unbound variable", done.stderr)
        self.assertNotIn("/dev/tty", done.stderr)
        self.assertNotIn("NOT FANCY", log)  # drawn in full, as for a person
        self.assertIn("get-docker.sh", log, done.stderr[-500:])
