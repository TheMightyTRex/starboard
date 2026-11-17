#!/usr/bin/env python3
"""Pictures' pages of Bring in media in the terminal set-up (DASH-455): runs the step against made-up media in a
throwaway folder (nothing real is read, no Reelix), in the boxed window of 90 by 40, and writes each screen as an HTML
page that looks like the terminal: python3 tools/screenshots/bring-in-terminal.py OUT_FOLDER
tools/screenshots/bring-in.sh takes a picture of each. A small screen reader of the terminal's own codes (cursor moves,
clearing, the scroll region) draws what the window shows when each question waits for an answer."""
import html
import io
import os
import re
import shutil
import sys
import tempfile
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from starboard import bring_in as b, folders, terminal_setup as ts  # noqa: E402
from tests.test_terminal_bring_in import LocalApi  # noqa: E402

W, H = 90, 40
PAGE = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<style>html,body{{margin:0;background:#0d1020}}body{{padding:24px}}
.term{{display:inline-block;background:#14182e;color:#e8eaf6;padding:14px 20px;border-radius:8px;font:15px/1.3 "DejaVu Sans Mono","Liberation Mono",monospace;white-space:pre}}</style>
<div class="term">{lines}</div>"""


class Screen:
    def __init__(self):
        self.rows = [[" "] * W for _ in range(H)]
        self.r = self.c = 0
        self.top, self.bottom = 0, H - 1
        self.saved = (0, 0)

    def scroll(self):
        del self.rows[self.top]
        self.rows.insert(self.bottom, [" "] * W)

    def feed(self, text):
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\x1b":
                m = re.match(r"\x1b\[([0-9;]*)([A-Za-z])", text[i:])
                if m:
                    args, cmd = m.group(1), m.group(2)
                    nums = [int(x) if x else 0 for x in args.split(";")] if args else []
                    if cmd == "H":
                        self.r, self.c = (nums[0] - 1 if nums else 0), (nums[1] - 1 if len(nums) > 1 else 0)
                    elif cmd == "J":
                        self.rows = [[" "] * W for _ in range(H)]
                    elif cmd == "K":
                        self.rows[self.r] = [" "] * W
                    elif cmd == "r":
                        self.top, self.bottom = (nums[0] - 1, nums[1] - 1) if len(nums) == 2 else (0, H - 1)
                    i += len(m.group(0))
                    continue
                if text[i:i + 2] == "\x1b7":
                    self.saved = (self.r, self.c)
                elif text[i:i + 2] == "\x1b8":
                    self.r, self.c = self.saved
                i += 2
                continue
            if ch == "\n":
                self.c = 0
                if self.r == self.bottom:
                    self.scroll()
                else:
                    self.r = min(self.r + 1, H - 1)
            elif ch == "\r":
                self.c = 0
            elif self.c < W:
                self.rows[self.r][self.c] = ch
                self.c += 1
            i += 1

    def text(self):
        return "\n".join("".join(r).rstrip() for r in self.rows)


class Recorder(io.StringIO):
    """The window's output; a picture is kept each time a question waits for an answer."""
    def __init__(self):
        super().__init__()
        self.screen, self.shots = Screen(), []

    def write(self, s):
        self.screen.feed(s)
        return super().write(s)


def main(out):
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="bring-in-terminal-")
    root = os.path.join(tmp, "mnt")
    data = os.path.join(tmp, "data")
    os.makedirs(os.path.join(root, "media"))
    os.makedirs(data)
    for rel, gb in {"disk2/Old media/Films/Harbour.Lights.2019.1080p.mkv": 9.2, "disk2/Old media/Films/Paper Planets (2017).mkv": 3.4,
                    "disk2/Old media/Films/Tidewater.mkv": 7.7, "disk2/Old media/Films/Sample/sample.mkv": 0.05,
                    "disk2/Old media/TV/Copper Valley/Season 1/Copper.Valley.S01E01.mkv": 2.1,
                    "disk2/Old media/TV/Copper Valley/Season 1/Copper.Valley.S01E02.mkv": 2.2,
                    "disk2/Old media/Music/Midnight Garden/First Light/01 Morning.flac": 0.04, "disk2/Backups/old.zip": 1.0}.items():
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.truncate(int(gb * 10 ** 9))
    rec = Recorder()
    names = ["1-sources", "2-places", "3-disk", "4-folder", "5-sources-added", "6-what", "7-linking", "8-names", "9-copy"]
    answers = iter(["1", "2", "3", "1", "1", "1", "1", "1", "1", "1"])

    def ask(prompt=""):
        rec.screen.feed(prompt)
        rec.shots.append(rec.screen.text().replace(root, "/mnt"))
        answer = next(answers)
        rec.screen.feed(answer + "\n")  # as the terminal shows what was typed
        return answer
    real_describe = b.describe
    with mock.patch.object(folders, "ROOTS", (root,)), mock.patch.object(b, "_in_docker", lambda: False), \
            mock.patch.object(folders, "_in_docker", lambda: False), mock.patch.object(b, "describe", lambda s: real_describe(s).replace(root, "/mnt")), \
            mock.patch.object(folders, "disk_places", lambda: [{"name": "Disk 2", "path": root + "/disk2"}]):
        term = ts.Terminal(out=rec, ask=ask, secret=ask, fancy=True, colour=False, width=W, rows=H)
        ts.step_bring(LocalApi(data), term, {"start": "new", "media_dir": root + "/media"})
    for name, shot in zip(names, rec.shots):
        with open(os.path.join(out, f"terminal-{name}.html"), "w", encoding="utf-8") as f:
            f.write(PAGE.format(title=f"Bring in media, terminal: {name}", lines=html.escape(shot)))
    shutil.rmtree(tmp, ignore_errors=True)  # the throwaway folder this made
    print(f"{len(rec.shots)} screens written to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
