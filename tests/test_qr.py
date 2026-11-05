"""The QR encoder (starboard/qr.py): sizes, capacities, the fixed patterns, format and version bits, Reed-Solomon and
the drawing. Whether codes scan was checked with real decoders (OpenCV and zxing-cpp) for every version and both
levels when it was written; these tests keep the known structure from changing."""
import unittest

from starboard import qr


def finder(code, x0, y0):
    return [[code.modules[y0 + y][x0 + x] for x in range(7)] for y in range(7)]


FINDER = [[max(abs(x - 3), abs(y - 3)) != 2 for x in range(7)] for y in range(7)]


def read_format(code, second=False):
    """The 15 format bits, read back from where the encoder put them (bit 0 first)."""
    m, size = code.modules, code.size
    if second:
        places = [(size - 1 - i, 8) for i in range(8)] + [(8, size - 15 + i) for i in range(8, 15)]
    else:
        places = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + [(14 - i, 8) for i in range(9, 15)]
    return sum(int(m[y][x]) << i for i, (x, y) in enumerate(places))


class QrTest(unittest.TestCase):
    def test_sizes_and_capacities(self):
        self.assertEqual([qr.size_of(v) for v in (1, 2, 10, 40)], [21, 25, 57, 177])
        known = {(1, "L"): 17, (1, "M"): 14, (10, "L"): 271, (10, "M"): 213, (25, "L"): 1273, (40, "L"): 2953,
                 (40, "M"): 2331}
        for (v, level), n in known.items():
            self.assertEqual(qr.byte_capacity(v, level), n, (v, level))
        self.assertEqual(qr.version_for(17), 1)
        self.assertEqual(qr.version_for(18), 2)
        self.assertIsNone(qr.version_for(3000))
        with self.assertRaises(ValueError):
            qr.encode("x" * 3000)

    def test_alignment_positions(self):
        self.assertEqual(qr.alignment_positions(1), [])
        self.assertEqual(qr.alignment_positions(2), [6, 18])
        self.assertEqual(qr.alignment_positions(7), [6, 22, 38])
        self.assertEqual(qr.alignment_positions(32), [6, 34, 60, 86, 112, 138])
        self.assertEqual(qr.alignment_positions(40), [6, 30, 58, 86, 114, 142, 170])

    def test_reed_solomon_matches_the_standard_example(self):
        # HELLO WORLD at 1-M, the worked example in the standard's tutorials.
        data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
        self.assertEqual(qr.reed_solomon(data, 10), [196, 35, 39, 119, 235, 215, 231, 226, 93, 23])

    def test_format_and_version_bits(self):
        self.assertEqual(qr.format_bits("M", 0), 0b101010000010010)
        self.assertEqual(qr.format_bits("L", 0), 0b111011111000100)
        self.assertEqual(qr.version_bits(7), 0x07C94)
        self.assertEqual(qr.version_bits(40), 0x28C69)

    def test_fixed_patterns_and_format_in_place(self):
        for text in ("https://github.com/TheMightyTRex/starboard", "Grüße, 日本語 ✓", "x" * 1000):
            code = qr.encode(text)
            size = code.size
            self.assertEqual(size, qr.size_of(code.version))
            for x0, y0 in ((0, 0), (size - 7, 0), (0, size - 7)):
                self.assertEqual(finder(code, x0, y0), FINDER)
            self.assertEqual([code.modules[6][x] for x in range(8, size - 8)], [x % 2 == 0 for x in range(8, size - 8)])
            self.assertTrue(code.modules[size - 8][8])  # the dark module
            bits = qr.format_bits(code.level, code.mask)
            self.assertEqual(read_format(code), bits)
            self.assertEqual(read_format(code, second=True), bits)
        big = qr.encode("x" * 1000)
        self.assertEqual(big.version, 22)
        bits = qr.version_bits(22)
        self.assertEqual([int(big.modules[i // 3][big.size - 11 + i % 3]) for i in range(18)],
                         [(bits >> i) & 1 for i in range(18)])

    def test_level_m_when_it_fits_the_same_version(self):
        self.assertEqual(qr.encode("x" * 14).level, "M")
        self.assertEqual(qr.encode("x" * 17).level, "L")
        self.assertEqual(qr.encode("x" * 14, boost=False).level, "L")

    def test_the_mask_with_the_lowest_penalty_is_chosen(self):
        text = "https://example.org/a-mask-test"
        chosen = qr.encode(text)
        scores = [qr.penalty(qr.encode(text, mask=m).modules) for m in range(8)]
        self.assertEqual(scores[chosen.mask], min(scores))

    def test_drawing_has_a_quiet_zone_and_forced_colours(self):
        code = qr.encode("hello")
        lines = qr.draw(code, colour=False)
        self.assertEqual(len(lines), qr.lines_of(code.version))
        self.assertEqual({len(line) for line in lines}, {qr.width_of(code.version)})
        self.assertEqual(lines[0].strip(), "")  # the top of the quiet zone
        self.assertTrue(lines[2].startswith("    █▀▀▀▀▀█"))  # 4 light columns, then the finder's top row
        coloured = qr.draw(code)
        self.assertTrue(all(line.startswith("\033[38;5;16;48;5;231m") and line.endswith("\033[0m") for line in coloured))

    def test_largest_version_for_a_window(self):
        self.assertEqual(qr.largest_version(78, 29), 8)    # 49 + 8 = 57 rows of modules need 29 lines
        self.assertEqual(qr.largest_version(78, 26), 6)
        self.assertEqual(qr.largest_version(78, 100), 13)  # 69 + 8 = 77 columns
        self.assertEqual(qr.largest_version(20, 20), 0)


if __name__ == "__main__":
    unittest.main()
