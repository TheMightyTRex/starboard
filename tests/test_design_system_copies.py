"""Starboard's copies of the shared design system files must match the library (suggestion of 10 November 2026: 0.15.4
and 0.15.5 had changed the copies directly, and the next sync would have undone it). Change the library, then sync.
The library is found at STARBOARD_DESIGN_SYSTEM or next to this checkout; without it (on GitHub) the check is skipped."""
import os
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIBRARY = pathlib.Path(os.environ.get("STARBOARD_DESIGN_SYSTEM") or os.path.expanduser("~/src/design-system"))


@unittest.skipUnless((LIBRARY / "tools" / "sync.py").exists(), "the design system library is not on this computer")
class CopiesMatchTest(unittest.TestCase):
    def test_every_copy_matches_the_library(self):
        done = subprocess.run(["python3", str(LIBRARY / "tools" / "sync.py"), "--check"], capture_output=True, text=True, timeout=60,
                              env={**os.environ, "STARBOARD_WEB": str(ROOT / "web")})
        differs = [line for line in done.stdout.splitlines() if line.startswith("differs") and str(ROOT) in line]
        self.assertEqual(differs, [], "Change these in the design system, then run its tools/sync.py: " + "; ".join(differs))


if __name__ == "__main__":
    unittest.main()
