"""The Live TV plug-in needs the Live TV folder's place on the computer inside Starboard's container (DASH-285)."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class LiveTvComposeTest(unittest.TestCase):
    def test_starboards_container_is_given_the_live_tv_folder(self):
        text = (ROOT / "compose.yaml").read_text()
        self.assertIn("STARBOARD_LIVETV_PATH=${STARBOARD_LIVETV_PATH:-}", text)
        self.assertIn("STARBOARD_IPTV_DIR=${STARBOARD_IPTV_DIR:-}", text)


if __name__ == "__main__":
    unittest.main()
