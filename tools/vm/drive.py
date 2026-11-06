#!/usr/bin/env python3
"""Drives the Run first script and the terminal set-up on a test machine, as a person would, and records every step.

It starts the script over SSH in a real terminal of a chosen size, the way the quick start does (the script is piped
into bash), and answers each question: Enter for the recommended answer, the passwords where they are asked, every
app ticked where the set-up asks which apps to install, and made-up VPN details. Before each answer it keeps a
picture of the window and checks it for what would look wrong to a person: text past the right edge, a line
repeated down the window, other programs' output (apt, Docker) inside the frame, and codes the terminal would show
as stray characters.

  tools/vm/drive.py --out DIR [--cols 80 --rows 24] [--plain] [--browser] [--resize-after N] [--stop-after TEXT]

It writes DIR/screens.html (every picture, with what was typed) and DIR/result.json (the faults found and how it
ended). The test machine comes from tools/vm/vm.sh new <system>. 6 November 2026.
"""
import argparse
import fcntl
import html
import json
import os
import pty
import re
import select
import struct
import sys
import termios
import time

sys.path.insert(0, os.path.dirname(__file__))
from term_screen import Screen  # noqa: E402

LEAKS = re.compile(r"^\s*(Get:\d|Hit:\d|Ign:\d|Reading package lists|Building dependency tree|Setting up |Unpacking |"
                   r"Selecting previously|Preparing to unpack|Processing triggers|Executing docker install|\+ sh -c|"
                   r"WARNING: apt does not have|debconf: |dpkg: |E: |W: |Created symlink|Synchronizing state of)")
FRAME = set("─│┌┐└┘├┤┬┴┼═║╔╗╚╝━┃╭╮╰╯ ")
FAKE_WG_KEY = "c3RhcmJvYXJkLXRlc3Qta2V5LW5vdC1yZWFsLTAwMDA="  # made up: no VPN provider knows it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=int(os.environ.get("VM_SSH_PORT", 2222)))
    ap.add_argument("--key", default=os.path.join(os.environ.get("STARBOARD_VM_DIR", "/mnt/pool/build-cache/starboard-vm"), "id_ed25519"))
    ap.add_argument("--cols", type=int, default=80)
    ap.add_argument("--rows", type=int, default=24)
    ap.add_argument("--plain", action="store_true", help="answer the first question with accessible mode")
    ap.add_argument("--browser", action="store_true", help="as on a desktop: DISPLAY set and the stand-in browser")
    ap.add_argument("--resize-after", type=int, default=0, help="change the window size after this many answers")
    ap.add_argument("--stop-after", default="", help="stop once this text is on the screen")
    ap.add_argument("--password", default=os.environ.get("VM_PASSWORD", "starboard-test-pw"))
    ap.add_argument("--starboard-password", default="correct horse battery staple")
    ap.add_argument("--apps", default="all", choices=["all", "recommended"])
    ap.add_argument("--timeout", type=int, default=5400)
    ap.add_argument("--command", default="", help="run this instead of the quick start")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    env = "export PATH=$HOME/.local/bin:$PATH; " + ("export DISPLAY=:0; " if a.browser else "unset DISPLAY WAYLAND_DISPLAY; ")
    command = a.command or "cat run-first.sh | STARBOARD_REPO=$HOME/starboard.bundle bash"
    ssh = ["ssh", "-tt", "-q", "-i", a.key, "-p", str(a.port), "-o", "StrictHostKeyChecking=no", "-o",
           "UserKnownHostsFile=/dev/null", "-o", "ServerAliveInterval=30", "tester@127.0.0.1", f"bash -lc '{env}{command}'"]

    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"
        os.execvp(ssh[0], ssh)

    def set_size(rows, cols):
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))

    rows, cols = a.rows, a.cols
    set_size(rows, cols)
    screen = Screen(rows, cols)
    shots, faults, typed, raw = [], [], [], ""
    answers, last_out, started = 0, time.time(), time.time()
    resized = False
    shown_more = False
    ended = "timeout"
    seen_faults = set()

    def fault(kind, detail):
        key = (kind, detail[:60])
        if key not in seen_faults:
            seen_faults.add(key)
            faults.append({"kind": kind, "detail": detail, "after_answers": answers, "screen": len(shots)})

    def check(screen_lines):
        for i, line in enumerate(screen_lines):
            if LEAKS.match(line.strip("│ ")):
                fault("other output in the frame", line.strip())
        body = [l for l in screen_lines if l.strip() and not set(l) <= FRAME]
        for x, y in zip(body, body[1:]):
            if x == y and len(x.strip()) > 8:
                fault("line repeated", x.strip())
        if screen.wrapped:
            fault("text past the right edge", f"{screen.wrapped} characters wrapped onto the next line")
            screen.wrapped = 0
        for u in sorted(screen.unknown):
            fault("unknown terminal code", u)
        screen.unknown.clear()

    def send(text, label=None):
        nonlocal answers
        os.write(fd, text.encode())
        typed.append(label or repr(text))
        answers += 1

    def tick_all(lines):
        """In the arrow-key list: move to each unticked line and press Space, then Enter."""
        items = [i for i, l in enumerate(lines) if re.search(r"\[( |x)\]", l)]
        cur = next((n for n, i in enumerate(items) if "›" in lines[i]), 0)
        keys = ""
        for n, i in enumerate(items):
            if "[ ]" in lines[i]:
                keys += ("\x1b[B" * (n - cur) if n >= cur else "\x1b[A" * (cur - n)) + " "
                cur = n
        return keys + "\r", f"ticked every unticked line ({sum('[ ]' in lines[i] for i in items)}), then Enter"

    while time.time() - started < a.timeout:
        r, _, _ = select.select([fd], [], [], 0.3)
        if r:
            try:
                chunk = os.read(fd, 65536).decode(errors="replace")
            except OSError:
                ended = "finished"
                break
            if not chunk:
                ended = "finished"
                break
            screen.feed(chunk)
            raw += chunk
            raw = raw[-20000:]
            last_out = time.time()
            continue
        if time.time() - last_out < 1.5:
            continue
        lines = screen.lines()
        text = "\n".join(lines)
        check(lines)
        here = lines[screen.r] if 0 <= screen.r < len(lines) else ""
        low = here.lower()
        heading = next((m.group(1).strip() for l in lines[:4] for m in [re.search(r"Starboard \| ([^│]+?)\s{2,}", l)] if m), "")
        shots.append({"title": heading or here.strip()[:80], "html": screen.html(), "size": f"{cols} x {rows}"})
        if a.stop_after and a.stop_after in text:
            ended = f"stopped at '{a.stop_after}'"
            break

        if a.resize_after and answers == a.resize_after and not resized:
            resized = True
            rows, cols = (40, 120) if cols < 120 else (24, 80)
            screen.resize(rows, cols)
            set_size(rows, cols)
            typed.append(f"(window changed to {cols} x {rows})")
            last_out = time.time()
            continue

        if "still working:" in low:  # the apps are downloading: a person waits
            last_out = time.time()
            continue
        # The answer, as a person would give it.
        if "[sudo] password" in low or re.search(r"password for \w+:", low):
            send(a.password + "\r", "the computer's password")
        elif re.search(r"choose a password|type it again|your starboard password|^\W*password:", low):
            send(a.starboard_password + "\r", "Starboard's password")
        elif "wireguard private key" in low:
            send(FAKE_WG_KEY + "\r", "a made-up WireGuard key")
        elif "wireguard address" in low:
            send("192.0.2.2/32\r", "192.0.2.2/32")
        elif a.apps == "all" and "Space ticks" in text and re.search(r"(?i)apps|what do you want|media server|use starboard's", text):
            keys, label = tick_all(lines)
            send(keys, label)
        elif a.apps == "all" and re.search(r"Type the numbers, separated by commas", text) and re.search(r"(?i)apps|what do you want", text):
            more = next((int(m.group(1)) for l in lines for m in [re.search(r"(\d+) more: type m", l)] if m), 0)
            if more and not shown_more:
                shown_more = True
                send("m\r", "m (see the rest of the list)")
            else:
                nums = sorted({int(m.group(1)) for l in lines for m in [re.match(r"\s*(?:●\s+)?(\d+)(?:\.|\s{2})\s*\S", l)] if m})
                shown_more = False
                nums = list(range(1, max(nums) + 1)) if nums else nums
                send(",".join(map(str, nums)) + "\r", "every number: " + ",".join(map(str, nums)))
        elif a.apps == "all" and "Install these?" in text and "your choice" in low:
            send("2\r", "2 (choose app by app)")
        elif a.apps == "all" and re.search(r"install [^?]+\? \[y/n\]", " ".join(l.strip() for l in lines[max(screen.r - 3, 0):screen.r + 1]).lower()) \
                and re.search(r"\[y/n\]: ?$", low.rstrip() + " "):
            send("y\r", "y (install this app)")
        elif a.plain and answers == 0:
            send("a\r", "a (accessible mode)")
        elif "press enter to finish, or type r" in low:
            send("\r", "Enter (finish)")
        else:
            send("\r", "Enter")
        last_out = time.time()

    try:
        os.kill(pid, 9)
    except OSError:
        pass
    lines = screen.lines()
    check(lines)
    shots.append({"title": "The end", "html": screen.html(), "size": f"{cols} x {rows}"})
    result = {"ended": ended, "answers": answers, "minutes": round((time.time() - started) / 60, 1), "faults": faults,
              "typed": typed, "last_screen": "\n".join(lines)}
    with open(os.path.join(a.out, "result.json"), "w") as f:
        json.dump(result, f, indent=2)
    with open(os.path.join(a.out, "screens.html"), "w") as f:
        f.write('<!doctype html><meta charset="utf-8"><title>Run first, step by step</title><style>'
                "body{margin:0;background:#0d1020;padding:24px;color:#cfd3ea;font:15px sans-serif}"
                "h2{margin:28px 0 8px;font-size:15px}pre{margin:0;display:inline-block;background:#14182e;color:#e8eaf6;"
                'font:13px/1.22 "DejaVu Sans Mono",monospace;padding:12px 18px;white-space:pre;border-radius:8px}'
                ".f{color:#ff8787}</style>")
        f.write(f"<p>Ended: {html.escape(ended)} after {answers} answers, {result['minutes']} minutes.</p>")
        for fl in faults:
            f.write(f'<p class="f">{html.escape(fl["kind"])}: {html.escape(fl["detail"])} (picture {fl["screen"]})</p>')
        for n, s in enumerate(shots):
            answer = typed[n] if n < len(typed) else ""
            f.write(f"<h2>{n}. {html.escape(s['title'])} ({s['size']}) → {html.escape(answer)}</h2><pre>{s['html']}</pre>")
    print(json.dumps({k: result[k] for k in ("ended", "answers", "minutes")}), f"{len(faults)} faults")
    for fl in faults:
        print(" -", fl["kind"], ":", fl["detail"])


if __name__ == "__main__":
    main()
