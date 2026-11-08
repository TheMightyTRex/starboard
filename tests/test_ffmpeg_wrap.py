"""Live TV fix (DASH-169): Jellyfin runs FFmpeg through starboard/ffmpeg-wrap.sh, which adds -extension_picky 0 for
Live TV inputs only, and Install apps points Jellyfin at it and puts it in Jellyfin's settings folder."""

import base64
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from starboard import containers, stack, takeover

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A stand-in for Jellyfin's FFmpeg: writes the arguments it was given, one a line, and exits with $FAKE_EXIT, or
# with 8 (option not found) when $FAKE_PICKY_FAILS is set and it was given -extension_picky.
FAKE = """#!/bin/bash
printf '%s\\n' "$@" >> "$FAKE_LOG"
echo --- >> "$FAKE_LOG"
if [[ -n "${FAKE_PICKY_FAILS:-}" && " $* " == *" -extension_picky "* ]]; then exit 8; fi
exit "${FAKE_EXIT:-0}"
"""

LIVE = ["https://jmp2.uk/sam-GBBD1300011DB.m3u8", "http://192.168.1.3:8000/iptv/channel/42",
        "https://example.amagi.tv/playlist/index.m3u8?ads=1", "https://jmp2.uk/plu-5f1af6a4b0f9e1000777ed1c"]
NOT_LIVE = ["/data/media/films/Film (2020)/Film (2020).mkv", "/media/tv/Show/Season 1/S01E01.mp4",
            "https://cdn.example.com/films/film.mp4", "http://192.168.1.3:8096/videos/abc/stream.mkv",
            "file:/data/media/radio/show.m4a"]


class WrapperTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        real = os.path.join(self.dir, "real")
        wrap = os.path.join(self.dir, "wrap")
        os.makedirs(real)
        os.makedirs(wrap)
        for name in ("ffmpeg", "ffprobe"):
            with open(os.path.join(real, name), "w") as f:
                f.write(FAKE)
            os.chmod(os.path.join(real, name), 0o755)
        with open(stack.FFMPEG_WRAP) as f:
            text = f.read()
        self.assertIn("REAL=/usr/lib/jellyfin-ffmpeg/", text)
        with open(os.path.join(wrap, "ffmpeg"), "w") as f:
            f.write(text.replace("/usr/lib/jellyfin-ffmpeg/", real + "/"))
        os.chmod(os.path.join(wrap, "ffmpeg"), 0o755)
        os.symlink("ffmpeg", os.path.join(wrap, "ffprobe"))
        self.wrap = wrap
        self.log = os.path.join(self.dir, "log")

    def run_tool(self, tool, args, **env):
        if os.path.exists(self.log):
            os.remove(self.log)
        rc = subprocess.run([os.path.join(self.wrap, tool), *args], env={**os.environ, "FAKE_LOG": self.log, **env},
                            timeout=20).returncode
        with open(self.log) as f:
            calls = [c.strip("\n").split("\n") for c in f.read().split("---\n") if c.strip()]
        return rc, calls

    def ffmpeg_args(self, url):
        return ["-hide_banner", "-analyzeduration", "3000000", "-i", url, "-map", "0:v:0", "-c:v", "copy", "-f", "hls",
                "/config/transcodes/out.m3u8"]

    def test_live_tv_inputs_get_the_option_just_before_their_input(self):
        for url in LIVE:
            with self.subTest(url=url):
                rc, calls = self.run_tool("ffmpeg", self.ffmpeg_args(url))
                self.assertEqual(rc, 0)
                self.assertEqual(len(calls), 1)
                args = calls[0]
                i = args.index(url)
                self.assertEqual(args[i - 3:i], ["-extension_picky", "0", "-i"])
                self.assertEqual(args.count("-extension_picky"), 1)
                # Everything else is passed on as it was, in order.
                self.assertEqual(args[:i - 3] + args[i - 1:], self.ffmpeg_args(url))

    def test_local_files_and_on_demand_links_are_passed_on_untouched(self):
        for url in NOT_LIVE:
            with self.subTest(url=url):
                rc, calls = self.run_tool("ffmpeg", self.ffmpeg_args(url))
                self.assertEqual(rc, 0)
                self.assertEqual(calls, [self.ffmpeg_args(url)])

    def test_a_live_tv_word_in_an_output_or_option_is_not_an_input(self):
        args = ["-i", "/data/media/films/a.mkv", "-f", "hls", "-hls_base_url", "https://jmp2.uk/x.m3u8", "/config/out.m3u8"]
        _, calls = self.run_tool("ffmpeg", args)
        self.assertEqual(calls, [args])

    def test_ffprobe_gets_the_option_once_at_the_front_for_live_tv_only(self):
        _, calls = self.run_tool("ffprobe", ["-print_format", "json", "-show_streams", LIVE[0]])
        self.assertEqual(calls, [["-extension_picky", "0", "-print_format", "json", "-show_streams", LIVE[0]]])
        for url in NOT_LIVE:
            with self.subTest(url=url):
                _, calls = self.run_tool("ffprobe", ["-print_format", "json", "-show_streams", url])
                self.assertEqual(calls, [["-print_format", "json", "-show_streams", url]])

    def test_an_input_that_refuses_the_option_runs_again_as_given(self):
        rc, calls = self.run_tool("ffmpeg", self.ffmpeg_args(LIVE[0]), FAKE_PICKY_FAILS="1")
        self.assertEqual(rc, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn("-extension_picky", calls[0])
        self.assertEqual(calls[1], self.ffmpeg_args(LIVE[0]))

    def test_other_failures_keep_their_exit_code_and_are_not_run_again(self):
        rc, calls = self.run_tool("ffmpeg", self.ffmpeg_args(LIVE[0]), FAKE_EXIT="1")
        self.assertEqual(rc, 1)
        self.assertEqual(len(calls), 1)
        rc, calls = self.run_tool("ffmpeg", self.ffmpeg_args(NOT_LIVE[0]), FAKE_EXIT="8")
        self.assertEqual(rc, 8)
        self.assertEqual(len(calls), 1)


CHOICE = {"apps": ["jellyfin"], "config_dir": "/srv/stack/config", "data_dir": "/srv/media", "puid": 1000, "pgid": 1000,
          "tz": "Europe/London"}


def service(compose, name):
    return re.search(rf"^  {name}:\n((?:    .*\n)*)", compose, re.M).group(1)


class ComposeTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(stack, "_port_free", lambda port: True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_jellyfin_runs_ffmpeg_through_the_wrapper(self):
        b = stack.build({**CHOICE, "apps": ["jellyfin", "qbittorrent"]})
        jf = service(b["compose"], "jellyfin")
        self.assertIn('      FFMPEG_PATH: "/config/ffmpeg-wrap/ffmpeg"\n', jf)
        self.assertIn('"${CONFIG_DIR}/jellyfin:/config"', jf)
        self.assertEqual(b["compose"].count("FFMPEG_PATH"), 1)

    def test_running_the_guide_again_after_a_takeover_keeps_it(self):
        keep = {"jellyfin": {"volumes": ["/mnt/pool/media:/media"], "port_map": {"8096": 8096},
                             "env": {"JELLYFIN_PublishedServerUrl": {"value": "http://192.168.1.3:8096"}}}}
        jf = service(stack.build({**CHOICE, "keep": keep})["compose"], "jellyfin")
        self.assertIn('FFMPEG_PATH: "/config/ffmpeg-wrap/ffmpeg"', jf)
        self.assertIn("JELLYFIN_PublishedServerUrl", jf)

    def test_not_when_config_is_another_folder_or_another_image(self):
        other = {"jellyfin": {"volumes": ["/opt/old-jellyfin:/config"]}}
        self.assertNotIn("FFMPEG_PATH", stack.build({**CHOICE, "keep": other})["compose"])
        image = {"jellyfin": {"image": "jellyfin/jellyfin:10.11"}}
        self.assertNotIn("FFMPEG_PATH", stack.build({**CHOICE, "keep": image})["compose"])

    def test_an_ffmpeg_path_of_your_own_is_kept(self):
        own = {"jellyfin": {"env": {"FFMPEG_PATH": {"value": "/usr/lib/jellyfin-ffmpeg/ffmpeg"}}}}
        jf = service(stack.build({**CHOICE, "keep": own})["compose"], "jellyfin")
        self.assertIn('FFMPEG_PATH: "/usr/lib/jellyfin-ffmpeg/ffmpeg"', jf)
        self.assertNotIn("/config/ffmpeg-wrap", jf)


class PutInPlaceTest(unittest.TestCase):
    """The wrapper reaches Jellyfin's settings folder on every way the apps are started."""

    def test_the_helper_script_writes_the_wrapper_and_the_ffprobe_link(self):
        cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg)
        work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, work)
        with open(os.path.join(work, "compose.yaml"), "w") as f:
            f.write('  jellyfin:\n    environment:\n      FFMPEG_PATH: "/config/ffmpeg-wrap/ffmpeg"\n')
        script = stack.ffmpeg_wrap_script(cfg, os.getuid(), os.getgid())
        subprocess.run(["sh", "-c", script], cwd=work, check=True, timeout=20)
        wrap = os.path.join(cfg, "jellyfin", "ffmpeg-wrap")
        with open(os.path.join(wrap, "ffmpeg")) as f, open(stack.FFMPEG_WRAP) as g:
            self.assertEqual(f.read(), g.read())
        self.assertTrue(os.access(os.path.join(wrap, "ffmpeg"), os.X_OK))
        self.assertEqual(os.readlink(os.path.join(wrap, "ffprobe")), "ffmpeg")
        # Run again (the guide run again): replaced, not refused.
        subprocess.run(["sh", "-c", script], cwd=work, check=True, timeout=20)

    def test_nothing_is_written_when_compose_does_not_ask_for_it(self):
        cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg)
        work = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, work)
        with open(os.path.join(work, "compose.yaml"), "w") as f:
            f.write("  jellyfin:\n    image: jellyfin/jellyfin\n")
        subprocess.run(["sh", "-c", stack.ffmpeg_wrap_script(cfg, os.getuid(), os.getgid())], cwd=work, check=True, timeout=20)
        self.assertFalse(os.path.exists(os.path.join(cfg, "jellyfin")))

    def test_starting_from_starboard_puts_it_in_place_before_compose_up(self):
        seen = {}

        def helper(folder, script, extra_binds=()):
            seen["script"] = script
            return 0, ""
        env = {"PUID": "1000", "PGID": "1000", "CONFIG_DIR": "/srv/stack/config", "DATA_DIR": "/srv/media"}
        with mock.patch.object(containers, "_helper", helper), mock.patch.object(containers, "docker", lambda *a, **k: None):
            stack._start("/srv/stack/starboard/data/stack", env)
        s = seen["script"]
        self.assertLess(s.index("ffmpeg-wrap"), s.index("up -d"))
        data = re.search(r"echo ([A-Za-z0-9+/=]+) \| base64 -d", s).group(1)
        with open(stack.FFMPEG_WRAP) as f:
            self.assertEqual(base64.b64decode(data).decode(), f.read())

    def test_taking_over_puts_it_in_place_after_the_settings_are_copied(self):
        rec = {"containers": [{"name": "jellyfin", "project": "old", "folder": "/opt/old", "files": ["/opt/old/compose.yaml"],
                               "service": "jellyfin"}], "copies": [("/opt/old/jellyfin", "/srv/stack/config/jellyfin")]}
        s = takeover.takeover_script(rec, "/srv/stack/data/stack", "/srv/stack/config", "/srv/media", [])
        self.assertLess(s.index("cp -a"), s.index("ffmpeg-wrap"))
        self.assertLess(s.index("ffmpeg-wrap"), s.index("up -d"))

    def test_the_installer_puts_it_in_place_from_starboards_own_copy(self):
        with open(os.path.join(ROOT, "install.sh")) as f:
            text = f.read()
        seed = text.split("sa_seed() {")[1].split("\n}\n")[0]
        self.assertIn("""grep -qF 'FFMPEG_PATH: "/config/ffmpeg-wrap/ffmpeg"' "$SA_FILE\"""", seed)
        self.assertIn("< starboard/ffmpeg-wrap.sh", seed)
        self.assertIn("ln -sfn ffmpeg '$top/ffprobe'", seed)

    def test_the_wrapper_is_in_the_image(self):
        with open(os.path.join(ROOT, "Dockerfile")) as f:
            self.assertIn("COPY --chown=root:root starboard ./starboard", f.read())
        self.assertTrue(os.access(stack.FFMPEG_WRAP, os.X_OK))


if __name__ == "__main__":
    unittest.main()
