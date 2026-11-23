"""The hardware transcoding check (DASH-515), against a fake ffmpeg run by a real shell, with no Docker."""

import http.client
import json
import os
import stat
import threading
import subprocess
import tempfile
import unittest
import unittest.mock

from starboard import auth
from starboard import transcode_check as tc
from starboard.server import make_server

SERVICES = [{"id": "jellyfin", "name": "Jellyfin", "type": "jellyfin"}]
LISTING = [{"id": "a", "name": "jellyfin"}, {"id": "b", "name": "plugin-livetv-main"}]
INFO = {"State": {"Running": True}, "Config": {"Env": ["PUID=1000", "PGID=1000"]}}

FAKE = """#!/bin/sh
# A fake ffmpeg: FAKE_ENCODERS lists what it claims; FAKE_FAIL names encoders that fail, with FAKE_SAY as the message.
case "$*" in
  *-version*) echo "ffmpeg version fake-1.0"; exit 0;;
  *-encoders*) for e in $FAKE_ENCODERS; do echo " V..... $e   fake"; done; exit 0;;
esac
for e in $FAKE_FAIL; do
  case "$*" in *"$e"*) echo "$FAKE_SAY" >&2; exit 1;; esac
done
exit 0
"""


class Fake:
    def __init__(self, test, encoders="libx264 h264_vaapi h264_qsv h264_nvenc", fail="", say="", nodes=True):
        self.dir = tempfile.mkdtemp()
        test.addCleanup(lambda: __import__("shutil").rmtree(self.dir, ignore_errors=True))
        path = os.path.join(self.dir, "ffmpeg")
        with open(path, "w") as f:
            f.write(FAKE)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        self.env = dict(os.environ, PATH=self.dir + os.pathsep + os.environ["PATH"], FAKE_ENCODERS=encoders, FAKE_FAIL=fail, FAKE_SAY=say)
        self.scripts = []
        self.dri = os.path.join(self.dir, "dri")
        self.sys = os.path.join(self.dir, "sys")
        os.makedirs(self.sys)
        if nodes:
            os.makedirs(self.dri)
        patch = unittest.mock.patch.multiple(tc, DRI_DIR=self.dri, SYS_DRM=self.sys)
        patch.start()
        test.addCleanup(patch.stop)

    def __call__(self, script):
        self.scripts.append(script)
        p = subprocess.run(["sh", "-c", script], capture_output=True, text=True, env=self.env, timeout=30)
        return p.returncode, p.stdout + p.stderr


def run(fake, **kw):
    return tc.check(SERVICES, listing=LISTING, inspect=lambda n: INFO, exec_fn=fake, **kw)


class Check(unittest.TestCase):
    def node(self, fake, name="renderD128", vendor="0x8086", readable=True):
        path = os.path.join(fake.dri, name)
        open(path, "w").close()
        os.chmod(path, 0o600 if readable else 0o000)
        os.makedirs(os.path.join(fake.sys, name, "device"), exist_ok=True)
        with open(os.path.join(fake.sys, name, "device", "vendor"), "w") as f:
            f.write(vendor + "\n")
        return path

    def by(self, result, key):
        return next(e for e in result["encoders"] if e["key"] == key)

    def test_everything_works_names_the_device(self):
        fake = Fake(self)
        self.node(fake)
        r = run(fake)
        self.assertEqual(r["state"], "ok")
        self.assertEqual(self.by(r, "vaapi")["status"], "works")
        self.assertTrue(self.by(r, "vaapi")["device"].endswith("renderD128"))
        self.assertEqual(self.by(r, "qsv")["status"], "works")
        self.assertEqual(self.by(r, "software")["status"], "works")
        self.assertEqual(r["user"], "abc")  # LinuxServer's image runs Jellyfin as abc

    def test_no_dri_says_how_to_pass_the_chip(self):
        fake = Fake(self, encoders="libx264 h264_vaapi", nodes=False)
        r = run(fake)
        v = self.by(r, "vaapi")
        self.assertEqual(v["status"], "fails")
        self.assertIn("no /dev/dri", v["why"])
        self.assertIn("/dev/dri:/dev/dri", v["fix"])
        self.assertEqual(r["state"], "software")
        self.assertEqual(self.by(r, "nvenc")["status"], "skipped")

    def test_permission_denied_names_the_group(self):
        fake = Fake(self, encoders="libx264 h264_vaapi", fail="vaapi", say="Failed to open /dev/dri/renderD128: Permission denied")
        self.node(fake)
        r = run(fake)
        v = self.by(r, "vaapi")
        self.assertEqual(v["status"], "fails")
        self.assertIn("group_add", v["fix"])
        self.assertEqual(r["state"], "software")

    def test_missing_driver(self):
        fake = Fake(self, encoders="libx264 h264_vaapi", fail="vaapi", say="libva: va_openDriver() returns -1\nFailed to initialise VAAPI connection")
        self.node(fake, vendor="0x1002")
        v = self.by(run(fake), "vaapi")
        self.assertIn("driver", v["why"])

    def test_old_chip_with_no_h264_encoder_is_not_called_a_permission_problem(self):
        say = "Failed to create /root/.cache for shader cache (Permission denied)---disabling.\n[h264_vaapi] No usable encoding profile found."
        fake = Fake(self, encoders="libx264 h264_vaapi", fail="vaapi", say=say)
        self.node(fake, vendor="0x1002")
        v = self.by(run(fake), "vaapi")
        self.assertIn("cannot encode H.264", v["why"])
        self.assertNotIn("group_add", v["fix"])
        self.assertNotIn("shader", v["detail"])

    def test_quick_sync_is_not_offered_on_amd(self):
        fake = Fake(self, encoders="libx264 h264_vaapi h264_qsv")
        self.node(fake, vendor="0x1002")
        r = run(fake)
        self.assertEqual(self.by(r, "qsv")["status"], "skipped")
        self.assertIn("Intel", self.by(r, "qsv")["why"])
        self.assertEqual(self.by(r, "vaapi")["status"], "works")

    def test_nvenc_without_a_card(self):
        fake = Fake(self, encoders="libx264 h264_nvenc", fail="nvenc", say="Cannot load libcuda.so.1")
        r = run(fake)
        n = self.by(r, "nvenc")
        self.assertEqual(n["status"], "fails")
        self.assertIn("NVIDIA Container Toolkit", n["fix"])

    def test_only_hardware_and_software_clips_are_synthetic_and_write_nowhere(self):
        fake = Fake(self)
        self.node(fake)
        run(fake)
        tests = [s for s in fake.scripts if "-f lavfi" in s]
        self.assertEqual(len(tests), 4)
        for s in tests:
            self.assertIn("testsrc2", s)
            self.assertIn("-f null -", s)
            self.assertIn("-t 2", s)
            self.assertIn("timeout 25", s)
            self.assertNotIn(" -i /", s)  # no media file is opened

    def test_nothing_ffmpeg_stops_the_check_in_words(self):
        with self.assertRaises(tc.CheckError) as e:
            tc.check(SERVICES, listing=LISTING, inspect=lambda n: INFO, exec_fn=lambda s: (0, "FFMPEG=\n"))
        self.assertIn("no ffmpeg", str(e.exception))

    def test_jellyfin_not_found_and_not_running(self):
        with self.assertRaises(tc.CheckError):
            tc.check(SERVICES, listing=[{"id": "x", "name": "other"}], inspect=lambda n: INFO, exec_fn=lambda s: (0, ""))
        with self.assertRaises(tc.CheckError):
            tc.check(SERVICES, listing=LISTING, inspect=lambda n: {"State": {"Running": False}}, exec_fn=lambda s: (0, ""))

    def test_one_check_at_a_time(self):
        fake = Fake(self)
        def inner(script):
            with self.assertRaises(tc.CheckError):
                run(Fake(self))
            return fake(script)
        run(inner)

    def test_user_comes_from_the_container(self):
        self.assertEqual(tc.run_user({"Config": {"User": "1000:1000"}}), "1000:1000")
        self.assertEqual(tc.run_user({"Config": {"Env": ["PUID=911"]}}), "abc")
        self.assertEqual(tc.run_user({"Config": {}}), "")

    def test_finds_the_container_named_in_settings(self):
        self.assertEqual(tc.find_container([{"type": "jellyfin", "container": "jf-main"}], [{"name": "jf-main"}, {"name": "jellyfin"}]), "jf-main")


class RouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        auth.ITERATIONS = 1000
        for k in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
            os.environ[k] = "0"
        os.environ["STARBOARD_DOCKER"] = "/nonexistent/docker.sock"
        cls.server, cls.app = make_server("127.0.0.1", 0, cls.tmp.name)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.port = cls.server.server_address[1]
        _, _, h = cls.call("POST", "/api/setup", {"token": cls.app.setup_token, "password": "correct horse battery"}, cookie=None)
        cls.cookie = h.split(";")[0]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    @classmethod
    def call(cls, method, path, body=None, cookie=""):
        conn = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        headers = {"Content-Type": "application/json", "X-Starboard": "1"}
        if cookie != None:  # noqa: E711
            headers["Cookie"] = cookie or getattr(cls, "cookie", "")
        conn.request(method, path, json.dumps(body) if body is not None else None, headers)
        r = conn.getresponse()
        raw = r.read()
        conn.close()
        return r.status, json.loads(raw or b"{}"), r.getheader("Set-Cookie") or ""

    def test_nothing_runs_unless_asked_and_you_must_be_signed_in(self):
        with unittest.mock.patch.object(tc, "check") as check:
            status, body, _ = self.call("GET", "/api/system/transcode-check")
            self.assertEqual(status, 200)
            check.assert_not_called()  # reading the last answer never starts a test
            status, _, _ = self.call("GET", "/api/system/transcode-check", cookie="x=y")
            self.assertEqual(status, 401)
            status, _, _ = self.call("POST", "/api/system/transcode-check", cookie="x=y")
            self.assertEqual(status, 401)
            check.assert_not_called()

    def test_pressing_the_button_runs_one_check_and_writes_the_audit_log(self):
        with unittest.mock.patch.object(tc, "check", return_value={"state": "software", "summary": "x", "encoders": []}) as check:
            status, body, _ = self.call("POST", "/api/system/transcode-check")
        self.assertEqual((status, body["result"]["state"]), (200, "software"))
        check.assert_called_once()
        with open(os.path.join(self.tmp.name, "logs", "audit.jsonl")) as f:
            self.assertIn("transcode_check", f.read())

    def test_a_problem_is_said_in_words(self):
        status, body, _ = self.call("POST", "/api/system/transcode-check")  # no Docker socket here
        self.assertEqual(status, 409)
        self.assertIn("Docker", body["error"])


if __name__ == "__main__":
    unittest.main()
