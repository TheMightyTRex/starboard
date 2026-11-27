#!/usr/bin/env python3
"""Turns the media server measurement into the file Starboard shows on the Plug-ins page (DASH-580).

    python3 -I comparison_json.py bench-results > ../../starboard/media_server_comparison.json

Reads summary.tsv (summarise.py), startup.txt (`bench.sh startup`) and image-sizes.txt (`name bytes` a line) from the folder."""
import json
import os
import statistics
import sys

NAMES = {"jellyfin": "Jellyfin", "plex": "Plex", "emby": "Emby"}


def main():
    folder = sys.argv[1]
    summary = {}
    with open(os.path.join(folder, "summary.tsv")) as f:
        for line in f.read().splitlines()[1:]:
            c = line.split("\t")
            summary[c[0].removeprefix("bench-")] = {"memory_mib": float(c[2]), "memory_peak_mib": float(c[3]), "cpu_pct": float(c[4]), "cpu_peak_pct": float(c[6]), "threads": c[7]}
    start = {}
    with open(os.path.join(folder, "startup.txt")) as f:
        for line in f:
            p = line.split()
            if len(p) == 4 and p[3] != "timeout":
                start.setdefault(p[0], []).append(float(p[3]))
    size = {}
    with open(os.path.join(folder, "image-sizes.txt")) as f:
        for line in f:
            p = line.split()
            if len(p) == 2 and p[1].isdigit():
                size[p[0]] = round(int(p[1]) / 1_000_000)
    servers = []
    for key, name in NAMES.items():
        if key not in summary:
            continue
        s = summary[key]
        servers.append({"id": key, "name": name, "memory_mib": round(s["memory_mib"]), "memory_peak_mib": round(s["memory_peak_mib"]),
                        "cpu_pct": s["cpu_pct"], "cpu_peak_pct": s["cpu_peak_pct"], "threads": s["threads"],
                        "startup_s": round(statistics.median(start[key])) if start.get(key) else None, "image_mb": size.get(key)})
    out = {"measured": os.environ.get("MEASURED", ""), "servers": servers,
           "method": "Each server was started on its own, with an empty settings folder, on a closed Docker network with no limits. After 120 seconds to settle, Docker's own figures were read every 5 seconds for 180 seconds, 36 readings. Starboard did not measure anything for this page: the figures are kept in a small file.",
           "caveat": "These are idle figures with no library, no viewers and no one watching. Memory and processor with people watching, and with a large library, are higher and were not measured. The servers were the latest linuxserver.io images on the day, and each shows only its first-run screen."}
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
