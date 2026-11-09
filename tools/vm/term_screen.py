"""A small terminal emulator for testing what the Run first script and the set-up wizards draw.

It keeps a grid of cells the size of the window and follows the escape codes those scripts write: cursor moves,
clearing, erasing lines, a scrolling area (DECSTBM), save and restore, and colours. It also counts what would look
wrong to a person: text written past the right edge (the terminal would wrap it onto the next line) and codes it
does not know (they could show as stray characters). tools/vm/drive.py uses it. 6 November 2026.
"""
import html
import re

PART = re.compile(r"\x1b(?:[()78]?|\[[0-9;?<=>]*|\][^\x07\x1b]*\x1b?)")
CSI = re.compile(r"\x1b\[([?>=]?)([0-9;]*)([@-~])")
OSC = re.compile(r"\x1b\][^\x07\x1b]*(\x07|\x1b\\)")


class Screen:
    def __init__(self, rows=24, cols=80):
        self.rows, self.cols = rows, cols
        self.cells = [self._blank() for _ in range(rows)]
        self.r = self.c = 0
        self.top, self.bottom = 0, rows - 1
        self.style = ""
        self.saved = (0, 0)
        self.wrapped = 0       # characters that ran past the right edge
        self.wrapped_lines = []  # the lines they ran past the edge of
        self.unknown = set()   # escape codes this emulator does not follow
        self.pending = ""      # an escape code cut off at the end of one read, finished by the next

    def _blank(self):
        return [(" ", "") for _ in range(self.cols)]

    def resize(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.cells = [self._blank() for _ in range(rows)]
        self.r = self.c = 0
        self.top, self.bottom = 0, rows - 1

    def _down(self):
        if self.r == self.bottom:
            del self.cells[self.top]
            self.cells.insert(self.bottom, self._blank())
        else:
            self.r = min(self.r + 1, self.rows - 1)

    def feed(self, data):
        data, self.pending = self.pending + data, ""
        i = 0
        while i < len(data):
            ch = data[i]
            if ch == "\x1b":
                m = OSC.match(data, i)
                if m:
                    i = m.end()
                    continue
                if i + 1 < len(data) and data[i + 1] in "78":
                    if data[i + 1] == "7":
                        self.saved = (self.r, self.c)
                    else:
                        self.r, self.c = self.saved
                    i += 2
                    continue
                if i + 1 < len(data) and data[i + 1] in "()":  # character set choice: no effect here
                    i += 3
                    continue
                m = CSI.match(data, i)
                if not m and PART.fullmatch(data, i):
                    self.pending = data[i:]   # the rest of this code comes in the next read
                    break
                if not m:
                    self.unknown.add(repr(data[i:i + 4]))
                    i += 1
                    continue
                self._csi(m.group(1), m.group(2), m.group(3))
                i = m.end()
                continue
            if ch == "\r":
                self.c = 0
            elif ch == "\n":
                self._down()
            elif ch == "\x08":
                self.c = max(self.c - 1, 0)
            elif ch == "\t":
                self.c = min((self.c // 8 + 1) * 8, self.cols - 1)
            elif ch >= " ":
                if self.c >= self.cols:
                    # An address runs on by design (it is never cut, so it copies whole): not a fault.
                    row = "".join(cell[0] for cell in self.cells[self.r])
                    words = row.split()
                    self.url_run = bool(words and (re.match(r"https?://", words[-1])
                                                   or (getattr(self, "url_run", False) and len(words) == 1)))
                    if not self.url_run:
                        self.wrapped += 1
                        self.wrapped_lines.append(row.rstrip())  # which line ran over, for the fault's details
                    self.c = 0
                    self._down()
                self.cells[self.r][self.c] = (ch, self.style)
                self.c += 1
            i += 1

    def _csi(self, private, args, cmd):
        nums = [int(x) for x in args.split(";") if x] if args else []
        n = nums[0] if nums else 1
        if private:  # ?25l, ?25h, ?1049h and the like: modes, nothing to draw
            return
        if cmd in "Hf":
            self.r = min(max((nums[0] - 1) if nums else 0, 0), self.rows - 1)
            self.c = min(max((nums[1] - 1) if len(nums) > 1 else 0, 0), self.cols - 1)
        elif cmd == "A":
            self.r = max(self.r - n, 0)
        elif cmd == "B":
            self.r = min(self.r + n, self.rows - 1)
        elif cmd == "C":
            self.c = min(self.c + n, self.cols - 1)
        elif cmd == "D":
            self.c = max(self.c - n, 0)
        elif cmd == "G":
            self.c = min(max(n - 1, 0), self.cols - 1)
        elif cmd == "J":
            mode = nums[0] if nums else 0
            if mode in (2, 3):
                self.cells = [self._blank() for _ in range(self.rows)]
            elif mode == 0:
                self.cells[self.r][self.c:] = [(" ", "")] * (self.cols - self.c)
                for row in range(self.r + 1, self.rows):
                    self.cells[row] = self._blank()
        elif cmd == "K":
            mode = nums[0] if nums else 0
            if mode == 2:
                self.cells[self.r] = self._blank()
            elif mode == 1:
                self.cells[self.r][:self.c + 1] = [(" ", "")] * (self.c + 1)
            else:
                self.cells[self.r][self.c:] = [(" ", "")] * (self.cols - self.c)
        elif cmd == "r":
            self.top, self.bottom = ((nums[0] - 1, nums[1] - 1) if len(nums) == 2 else (0, self.rows - 1))
            self.r = self.c = 0
        elif cmd == "m":
            self.style = "" if args in ("", "0") else args
        elif cmd in "sh":
            if cmd == "s":
                self.saved = (self.r, self.c)
        elif cmd == "u":
            self.r, self.c = self.saved
        else:
            self.unknown.add(f"CSI {args}{cmd}")

    def lines(self):
        return ["".join(ch for ch, _ in row).rstrip() for row in self.cells]

    def text(self):
        return "\n".join(self.lines())

    def html(self):
        colours = {"1": "color:#fff;font-weight:700", "1;36": "color:#5fd7ff;font-weight:700", "36": "color:#5fd7ff",
                   "2": "color:#7d86a8", "32": "color:#7ee2a8", "33": "color:#ffd36b", "31": "color:#ff8787",
                   "1;31": "color:#ff8787;font-weight:700", "1;32": "color:#7ee2a8;font-weight:700"}
        out = []
        for row in self.cells:
            line, cur, buf = "", None, ""
            for ch, st in row:
                if st != cur and buf:
                    line += f'<span style="{colours.get(cur, "")}">{html.escape(buf)}</span>'
                    buf = ""
                cur = st
                buf += ch
            if buf:
                line += f'<span style="{colours.get(cur, "")}">{html.escape(buf)}</span>'
            out.append(line)
        return "\n".join(out)
