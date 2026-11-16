"""Run once while the image is built (Dockerfile): every file and folder under a path made readable by everyone and
writable only by its owner, as chmod -R a+rX,go-w would, but only where that changes something. A file whose
permissions are changed is copied into the new image layer, so leaving right ones alone keeps the image smaller.

    python fix_modes.py /app
"""
import os
import stat
import sys


def wanted(mode, is_dir):
    """The permission bits chmod a+rX,go-w gives: read for all, search (x) for all on folders and on files that
    anyone may already run, and no write for group or others."""
    bits = stat.S_IMODE(mode) | 0o444
    if is_dir or mode & 0o111:
        bits |= 0o111
    return bits & ~0o022


def fix(top):
    """Changes what needs it under top (top included). Returns how many were changed."""
    changed = 0
    for path in [top] + [os.path.join(d, n) for d, dirs, files in os.walk(top) for n in dirs + files]:
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode):
            continue  # chmod -R leaves links themselves alone too
        want = wanted(st.st_mode, stat.S_ISDIR(st.st_mode))
        if stat.S_IMODE(st.st_mode) != want:
            os.chmod(path, want)
            changed += 1
    return changed


if __name__ == "__main__":
    for top in sys.argv[1:]:
        fix(top)
