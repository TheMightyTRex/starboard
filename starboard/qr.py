"""A QR code encoder, standard library only, for the terminal set-up's feedback (ISO/IEC 18004).

Byte mode (the text as UTF-8), error correction level L or M, every version from 1 to 40, Reed-Solomon error
correction, the mask with the lowest penalty, and the format and version information. draw() gives the code as
text lines of half-block characters, two module rows to a line, dark on light with a 4-module quiet zone and the
colours forced, so it scans on a dark terminal as well.

    code = qr.encode("https://example.org/")
    print("\\n".join(qr.draw(code)))
"""

# Error correction codewords in each block, and the number of blocks, by level and version (index 0 is unused).
ECC_PER_BLOCK = {
    "L": (0, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "M": (0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28,
          28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
}
BLOCKS = {
    "L": (0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18,
          19, 19, 20, 21, 22, 24, 25),
    "M": (0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31,
          33, 35, 37, 38, 40, 43, 45, 47, 49),
}
LEVEL_BITS = {"L": 1, "M": 0}
QUIET = 4

# Arithmetic in GF(256) with the QR polynomial x^8 + x^4 + x^3 + x^2 + 1.
_EXP, _LOG = [0] * 512, [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i], _LOG[_x] = _x, _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a, b):
    return 0 if a == 0 or b == 0 else _EXP[_LOG[a] + _LOG[b]]


def _generator(degree):
    """The Reed-Solomon generator polynomial, highest power first: the product of (x - a^i) for i below degree."""
    poly = [1]
    for i in range(degree):
        nxt = [0] * (len(poly) + 1)
        for j, c in enumerate(poly):
            nxt[j] ^= c
            nxt[j + 1] ^= _mul(c, _EXP[i])
        poly = nxt
    return poly


def reed_solomon(data, degree):
    """The error correction codewords for one block of data codewords."""
    gen, rem = _generator(degree), [0] * degree
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        for j in range(degree):
            rem[j] ^= _mul(gen[j + 1], factor)
    return rem


def size_of(version):
    return 17 + 4 * version


def raw_modules(version):
    """The modules left for data and error correction once the fixed patterns are drawn."""
    n = (16 * version + 128) * version + 64
    if version >= 2:
        align = version // 7 + 2
        n -= (25 * align - 10) * align - 55
        if version >= 7:
            n -= 36
    return n


def data_codewords(version, level):
    return raw_modules(version) // 8 - ECC_PER_BLOCK[level][version] * BLOCKS[level][version]


def byte_capacity(version, level="L"):
    """How many bytes of text fit, in byte mode."""
    header = 4 + (8 if version < 10 else 16)
    return (data_codewords(version, level) * 8 - header) // 8


def alignment_positions(version):
    if version == 1:
        return []
    count = version // 7 + 2
    step = (version * 8 + count * 3 + 5) // (count * 4 - 4) * 2
    size = size_of(version)
    return [6] + sorted(size - 7 - i * step for i in range(count - 1))


def version_for(length, level="L", largest=40):
    """The smallest version that holds length bytes, or None when even the largest allowed does not."""
    for v in range(1, largest + 1):
        if length <= byte_capacity(v, level):
            return v
    return None


class Code:
    """A finished QR code: modules[y][x] is True for a dark module."""

    def __init__(self, version, level, mask, modules):
        self.version, self.level, self.mask, self.modules = version, level, mask, modules
        self.size = len(modules)


def _bits(value, n):
    return [(value >> i) & 1 for i in range(n - 1, -1, -1)]


def _codewords(data, version, level):
    bits = [0, 1, 0, 0] + _bits(len(data), 8 if version < 10 else 16)
    for byte in data:
        bits += _bits(byte, 8)
    room = data_codewords(version, level) * 8
    bits += [0] * min(4, room - len(bits))
    bits += [0] * (-len(bits) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(words) < room // 8:
        words.append(pad)
        pad ^= 0xEC ^ 0x11
    # Split into blocks (the short ones first), add the error correction, then interleave.
    count, ecc = BLOCKS[level][version], ECC_PER_BLOCK[level][version]
    total = raw_modules(version) // 8
    short, short_len = count - total % count, total // count
    blocks, k = [], 0
    for i in range(count):
        n = short_len - ecc + (0 if i < short else 1)
        part = words[k:k + n]
        k += n
        blocks.append((part, reed_solomon(part, ecc)))
    out = []
    for i in range(max(len(d) for d, _ in blocks)):
        out += [d[i] for d, _ in blocks if i < len(d)]
    for i in range(ecc):
        out += [e[i] for _, e in blocks]
    return out


MASKS = [
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
]


def format_bits(level, mask):
    data = LEVEL_BITS[level] << 3 | mask
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return (data << 10 | rem) ^ 0x5412


def version_bits(version):
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
    return version << 12 | rem


class _Grid:
    def __init__(self, version):
        self.version, self.size = version, size_of(version)
        self.dark = [[False] * self.size for _ in range(self.size)]
        self.fixed = [[False] * self.size for _ in range(self.size)]

    def put(self, x, y, dark):
        self.dark[y][x], self.fixed[y][x] = bool(dark), True

    def patterns(self):
        size = self.size
        for i in range(size):  # timing
            self.put(6, i, i % 2 == 0)
            self.put(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):  # finders, with their light separators
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < size and 0 <= y < size:
                        self.put(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = alignment_positions(self.version)
        last = len(pos) - 1
        for i, ax in enumerate(pos):
            for j, ay in enumerate(pos):
                if (i, j) in ((0, 0), (0, last), (last, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.put(ax + dx, ay + dy, max(abs(dx), abs(dy)) != 1)
        self.format("L", 0)  # reserves the places; drawn again with the chosen mask
        if self.version >= 7:
            bits = version_bits(self.version)
            for i in range(18):
                bit = (bits >> i) & 1
                a, b = size - 11 + i % 3, i // 3
                self.put(a, b, bit)
                self.put(b, a, bit)

    def format(self, level, mask):
        bits, size = format_bits(level, mask), self.size
        bit = lambda i: (bits >> i) & 1  # noqa: E731
        for i in range(6):
            self.put(8, i, bit(i))
        self.put(8, 7, bit(6))
        self.put(8, 8, bit(7))
        self.put(7, 8, bit(8))
        for i in range(9, 15):
            self.put(14 - i, 8, bit(i))
        for i in range(8):
            self.put(size - 1 - i, 8, bit(i))
        for i in range(8, 15):
            self.put(8, size - 15 + i, bit(i))
        self.put(8, size - 8, True)  # the dark module

    def place(self, words):
        size, i, total = self.size, 0, len(words) * 8
        right = size - 1
        while right >= 1:
            if right == 6:
                right = 5
            upward = ((right + 1) & 2) == 0
            for vert in range(size):
                y = size - 1 - vert if upward else vert
                for x in (right, right - 1):
                    if not self.fixed[y][x] and i < total:
                        self.dark[y][x] = bool((words[i >> 3] >> (7 - (i & 7))) & 1)
                        i += 1
            right -= 2

    def apply(self, mask):
        test = MASKS[mask]
        for y in range(self.size):
            row, fixed = self.dark[y], self.fixed[y]
            for x in range(self.size):
                if not fixed[x] and test(x, y):
                    row[x] = not row[x]


def penalty(dark):
    """The standard penalty: long runs, 2 by 2 blocks, finder-like patterns and an uneven share of dark."""
    size, score = len(dark), 0
    lines = ["".join("1" if v else "0" for v in row) for row in dark]
    lines += ["".join(lines[y][x] for y in range(size)) for x in range(size)]
    for line in lines:
        run = 1
        for i in range(1, size + 1):
            if i < size and line[i] == line[i - 1]:
                run += 1
                continue
            if run >= 5:
                score += run - 2
            run = 1
        padded = "0000" + line + "0000"
        for pattern in ("10111010000", "00001011101"):
            at = padded.find(pattern)
            while at != -1:
                score += 40
                at = padded.find(pattern, at + 1)
    for y in range(size - 1):
        a, b = dark[y], dark[y + 1]
        for x in range(size - 1):
            if a[x] == a[x + 1] == b[x] == b[x + 1]:
                score += 3
    total = size * size
    count = sum(map(sum, dark))
    score += ((abs(count * 20 - total * 10) + total - 1) // total - 1) * 10
    return score


def encode(text, level="L", boost=True, largest=40, mask=None):
    """The QR code for text (str as UTF-8, or bytes), in the smallest version that holds it. With boost, level L
    becomes M when M fits in the same version. Raises ValueError when it is too long."""
    data = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    version = version_for(len(data), level, largest)
    if version is None:
        raise ValueError(f"{len(data)} bytes do not fit in a QR code up to version {largest}")
    if boost and level == "L" and len(data) <= byte_capacity(version, "M"):
        level = "M"
    grid = _Grid(version)
    grid.patterns()
    grid.place(_codewords(data, version, level))
    if mask is None:
        best = None
        for m in range(8):
            grid.apply(m)
            grid.format(level, m)
            score = penalty(grid.dark)
            if best is None or score < best[0]:
                best = (score, m)
            grid.apply(m)  # masking twice undoes it
        mask = best[1]
    grid.apply(mask)
    grid.format(level, mask)
    return Code(version, level, mask, grid.dark)


def width_of(version, quiet=QUIET):
    """Characters across, with the quiet zone."""
    return size_of(version) + 2 * quiet


def lines_of(version, quiet=QUIET):
    """Text lines down, with the quiet zone: two module rows to a line."""
    return (size_of(version) + 2 * quiet + 1) // 2


def largest_version(columns, lines, quiet=QUIET):
    """The largest version whose drawing fits columns by lines, or 0 when none does."""
    v = 0
    while v < 40 and width_of(v + 1, quiet) <= columns and lines_of(v + 1, quiet) <= lines:
        v += 1
    return v


def draw(code, colour=True, quiet=QUIET):
    """Text lines: dark modules on a light background, two module rows to a line with half blocks, a 4-module
    quiet zone all round. With colour, black on white is forced with ANSI codes, so the code is the right way round
    on a dark terminal too."""
    n = code.size + 2 * quiet

    def dark(x, y):
        x, y = x - quiet, y - quiet
        return 0 <= x < code.size and 0 <= y < code.size and code.modules[y][x]
    out = []
    for y in range(0, n, 2):
        chars = []
        for x in range(n):
            top, bottom = dark(x, y), dark(x, y + 1)
            chars.append("█" if top and bottom else "▀" if top else "▄" if bottom else " ")
        line = "".join(chars)
        out.append(f"\033[38;5;16;48;5;231m{line}\033[0m" if colour else line)
    return out
