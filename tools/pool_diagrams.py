#!/usr/bin/env python3
"""Draws the drive pool help diagrams (DASH-87) as plain SVG: docs/help/images/pool-*.svg, and the balance one for
the Pool page (web/images/balance.svg). Every amount is written as words and numbers, and folders are told apart by
their letters and outlines, never by colour alone. Run: python3 tools/pool_diagrams.py"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/help/images"
INK, MUTED, LINE, BG, FILL, NEW = "#1d2238", "#4a5068", "#7d86a8", "#ffffff", "#c9d6f5", "#f3d9a8"
FONT = 'font-family="Atkinson Hyperlegible Next, Atkinson Hyperlegible, Verdana, sans-serif"'


def svg(w, h, body, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-labelledby="t d"><title id="t">{title}</title><desc id="d">{desc}</desc>'
            f'<rect width="{w}" height="{h}" fill="{BG}"/><g {FONT} fill="{INK}">{body}</g></svg>\n')


def text(x, y, s, size=14, weight=400, anchor="start", fill=INK):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{s}</text>'


def drive(x, y, name, size_tb, blocks, h=150, w=90):
    """One drive as an upright box; blocks: [(letter, tb, new)] stacked from the bottom."""
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{LINE}" stroke-width="2" rx="6"/>']
    used = 0
    for letter, tb, new in blocks:
        bh = h * tb / size_tb
        top = y + h - (used / size_tb) * h - bh
        dash = ' stroke-dasharray="5 3"' if new else ""
        out.append(f'<rect x="{x + 6}" y="{top + 1:.1f}" width="{w - 12}" height="{bh - 2:.1f}" fill="{NEW if new else FILL}" '
                   f'stroke="{INK}" stroke-width="1.5"{dash} rx="3"/>')
        if bh > 16:
            out.append(text(x + w / 2, top + bh / 2 + 5, letter, 14, 700, "middle"))
        used += tb
    pct = round(used / size_tb * 100)
    out.append(text(x + w / 2, y + h + 22, name, 14, 700, "middle"))
    out.append(text(x + w / 2, y + h + 40, f"{pct}% full", 13, 400, "middle", MUTED))
    return "".join(out)


def balance():
    before = [("Disk 1", 4, [("A", 1.0, 0), ("B", 0.9, 0), ("C", 0.8, 0), ("D", 0.7, 0)]),
              ("Disk 2", 4, [("E", 1.0, 0), ("F", 0.9, 0)]), ("Disk 3", 4, [("G", 0.7, 0)]), ("Disk 4", 4, [])]
    after = [("Disk 1", 4, [("A", 1.0, 0), ("D", 0.7, 0)]), ("Disk 2", 4, [("E", 1.0, 0), ("F", 0.9, 0)]),
             ("Disk 3", 4, [("G", 0.7, 0), ("C", 0.8, 1)]), ("Disk 4", 4, [("B", 0.9, 1)])]
    body = [text(20, 30, "Before balancing", 18, 700), text(660, 30, "After balancing", 18, 700)]
    for n, (name, size, blocks) in enumerate(before):
        body.append(drive(20 + n * 150, 60, name, size, blocks))
    for n, (name, size, blocks) in enumerate(after):
        body.append(drive(660 + n * 150, 60, name, 4, blocks))
    body.append(f'<path d="M 625 135 l 25 0 m -8 -8 l 8 8 l -8 8" stroke="{INK}" stroke-width="3" fill="none"/>')
    body.append(text(20, 280, "Each letter is one whole folder, such as a series. Folders with a dashed outline were moved. "
                              "Each stays whole on one drive.", 14))
    return svg(1260, 300, "".join(body), "Balancing the files across the drives in a pool",
               "Before: disk 1 is 85% full with folders A, B, C and D, disk 2 is 48% full, disk 3 is 18% full and disk 4 is empty. "
               "After: folder B has moved to disk 4 and folder C to disk 3, so each disk is between 22% and 48% full, and every folder is still whole on one drive.")


def balance_narrow():
    """The same as balance(), before above after, for the Pool page: about 640 pixels wide, so its words are full size."""
    before = [("Disk 1", 4, [("A", 1.0, 0), ("B", 0.9, 0), ("C", 0.8, 0), ("D", 0.7, 0)]),
              ("Disk 2", 4, [("E", 1.0, 0), ("F", 0.9, 0)]), ("Disk 3", 4, [("G", 0.7, 0)]), ("Disk 4", 4, [])]
    after = [("Disk 1", 4, [("A", 1.0, 0), ("D", 0.7, 0)]), ("Disk 2", 4, [("E", 1.0, 0), ("F", 0.9, 0)]),
             ("Disk 3", 4, [("G", 0.7, 0), ("C", 0.8, 1)]), ("Disk 4", 4, [("B", 0.9, 1)])]
    body = [text(20, 30, "Before balancing", 18, 700), text(20, 290, "After balancing", 18, 700)]
    for n, (name, size, blocks) in enumerate(before):
        body.append(drive(20 + n * 150, 50, name, size, blocks, h=150))
    for n, (name, size, blocks) in enumerate(after):
        body.append(drive(20 + n * 150, 310, name, size, blocks, h=150))
    body.append(text(20, 540, "Each letter is one whole folder, such as a series.", 14))
    body.append(text(20, 560, "Dashed folders were moved. Each stays whole on one drive.", 14))
    return svg(640, 580, "".join(body), "Balancing the files across the drives in a pool",
               "Before: disk 1 is 85% full with folders A, B, C and D, disk 2 is 48% full, disk 3 is 18% full and disk 4 is empty. "
               "After: folder B has moved to disk 4 and folder C to disk 3, so each disk is between 22% and 48% full, and every folder is still whole on one drive.")


def without():
    body = [text(20, 30, "Without balancing", 18, 700), text(660, 30, "With Starboard's balancer", 18, 700)]
    body.append(drive(20, 60, "Disk 1", 4, [("A", 1.6, 0), ("B", 1.6, 0), ("C", 0.6, 0)]))
    body.append(drive(170, 60, "Disk 2", 4, [("A+", 0.6, 1), ("B+", 0.5, 1)]))
    body.append(drive(320, 60, "Disk 3", 4, [("A+", 0.5, 1)]))
    body.append(drive(660, 60, "Disk 1", 4, [("A", 1.6, 0), ("A+", 1.1, 1)]))
    body.append(drive(810, 60, "Disk 2", 4, [("B", 1.6, 0), ("B+", 0.5, 1)]))
    body.append(drive(960, 60, "Disk 3", 4, [("C", 0.6, 0)]))
    body.append(text(470, 110, "New episodes go to", 13, 400, "start", MUTED))
    body.append(text(470, 128, "the emptiest drive,", 13, 400, "start", MUTED))
    body.append(text(470, 146, "so series A is spread", 13, 400, "start", MUTED))
    body.append(text(470, 164, "over three drives.", 13, 400, "start", MUTED))
    body.append(text(470, 182, "Disk 1 stays 95% full.", 13, 400, "start", MUTED))
    body.append(text(1110, 110, "Each series is kept", 13, 400, "start", MUTED))
    body.append(text(1110, 128, "together on one drive,", 13, 400, "start", MUTED))
    body.append(text(1110, 146, "and no drive is near", 13, 400, "start", MUTED))
    body.append(text(1110, 164, "full.", 13, 400, "start", MUTED))
    body.append(text(20, 280, "A+ means newer episodes of series A. If disk 2 failed without balancing, series A and B "
                              "would each lose some episodes; with balancing, only series B.", 14))
    return svg(1290, 300, "".join(body), "What happens without balancing",
               "Without balancing, disk 1 stays 95% full and newer episodes of series A land on disks 2 and 3, so one series "
               "is spread over three drives. With Starboard's balancer, each series is together on one drive and no drive is near full.")


def move():
    steps = [("1. Copy", "The folder is copied to the emptier drive, under the pool."),
             ("2. Check", "rsync compares the copy with the original, file by file."),
             ("3. Remove", "Only when they match is the original removed."),
             ("Throughout", "The pool shows the folder in the same place, so the apps notice nothing.")]
    body = []
    for n, (head, say) in enumerate(steps):
        x = 20 + n * 300
        body.append(f'<rect x="{x}" y="20" width="270" height="120" rx="10" fill="{FILL if n < 3 else BG}" stroke="{INK}" stroke-width="1.5"/>')
        body.append(text(x + 16, 52, head, 17, 700))
        words, line, y = say.split(), "", 80
        for w_ in words:
            if len(line) + len(w_) > 30:
                body.append(text(x + 16, y, line.strip(), 14))
                line, y = "", y + 20
            line += w_ + " "
        body.append(text(x + 16, y, line.strip(), 14))
        if n < 2:
            body.append(f'<path d="M {x + 274} 80 l 22 0 m -8 -8 l 8 8 l -8 8" stroke="{INK}" stroke-width="3" fill="none"/>')
    body.append(text(20, 175, "If it is stopped, or the power goes off, the folder is still whole on the drive it came from.", 14))
    return svg(1220, 195, "".join(body), "How one folder is moved",
               "Each folder is copied to the emptier drive, the copy is checked against the original, and only then is the "
               "original removed. The pool shows the folder in the same place throughout.")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("pool-balance", balance), ("pool-without-balancing", without), ("pool-how-a-folder-moves", move)):
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
    (ROOT / "web/images").mkdir(exist_ok=True)
    (ROOT / "web/images/balance.svg").write_text(balance_narrow(), encoding="utf-8")
    print("Drew", ", ".join(p.name for p in sorted(OUT.glob("pool-*.svg"))))
