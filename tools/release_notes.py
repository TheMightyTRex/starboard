#!/usr/bin/env python3
"""Writes a release's notes for GitHub from starboard/releases.py, the same words the app shows.

    python3 tools/release_notes.py            # the version in VERSION
    python3 tools/release_notes.py 0.4.0      # another one

Writes docs/releases/vX.Y.Z.md. See docs/RELEASING.md for the whole process.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from starboard import releases  # noqa: E402

version = sys.argv[1] if len(sys.argv) > 1 else (ROOT / "VERSION").read_text().strip()
release = next((r for r in releases.RELEASES if r["version"] == version.lstrip("v")), None)
if not release:
    sys.exit(f"No entry for {version} in starboard/releases.py. Add one first.")
out = ROOT / "docs" / "releases" / f"v{release['version']}.md"
out.write_text(releases.markdown(release))
print(f"Wrote {out.relative_to(ROOT)}")
