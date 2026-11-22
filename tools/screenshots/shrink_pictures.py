#!/usr/bin/env python3
"""Makes pictures smaller when pngquant is not installed: 256 colours with dithering, about 60% smaller for a
screenshot, with no change a reader can see. Needs Pillow; without it the pictures are left as they are.

    python3 tools/screenshots/shrink_pictures.py picture.png [picture.png ...]
"""
import sys

try:
    from PIL import Image
except ImportError:
    print("Pillow is not installed: the pictures are left as they are", file=sys.stderr)
    sys.exit(0)

for path in sys.argv[1:]:
    picture = Image.open(path).convert("RGB")
    picture.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).save(path, "PNG", optimize=True)
