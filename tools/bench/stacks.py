#!/usr/bin/env python3
"""Whole-stack totals from summary.tsv (the bench) and summary-live.tsv (the live reading).

    python3 -I stacks.py [folder]      (the folder that holds both files; default the current folder)

Each stack is its own apps from the bench plus the shared apps (Jellyfin, Audiobookshelf, qBittorrent, NZBGet)
from the live reading, counted the same way for every stack. A shared app that is not running on your computer is
left out of every stack, and named on the error output."""
import csv
import pathlib
import sys

READARR = {"mem_median_MiB": 120.0, "mem_peak_MiB": 120.0, "cpu_median_pct": 0.07, "cpu_peak_pct": 0.07,
           "threads_median": "23"}  # estimate from 4 November 2026: Readarr has no image that can be pulled
SHARED = ["jellyfin", "audiobookshelf", "qbittorrent", "nzbget"]

STACKS = {
    "This stack: Starboard, Reelix Lite": ["starboard", "reelix-lite"],
    "This stack: Starboard, Reelix full": ["starboard", "reelix-full"],
    "This stack: Starboard, Reelix Lite, On demand plug-in": ["starboard", "reelix-lite", "on-demand"],
    "Classic *arr stack with Jellyseerr": ["radarr", "sonarr", "lidarr", "prowlarr", "readarr*", "jellyseerr"],
    "Dashboard-led with Homarr": ["radarr", "sonarr", "lidarr", "prowlarr", "readarr*", "jellyseerr", "homarr",
                                  "jellystat", "jellystat-db", "unpackerr", "recyclarr"],
    "Dashboard-led with Homepage": ["radarr", "sonarr", "lidarr", "prowlarr", "readarr*", "jellyseerr", "homepage",
                                    "jellystat", "jellystat-db", "unpackerr", "recyclarr"],
}


def load(path, prefix=""):
    rows = {}
    if not path.exists():
        return rows
    with open(path) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            rows[r["name"].removeprefix(prefix)] = r
    return rows


def totals(bench, live):
    """One output line per stack whose apps were all measured, tab-separated, after a header line."""
    shared = [s for s in SHARED if s in live]
    for s in SHARED:
        if s not in live:
            print(f"not running, left out of every stack: {s}", file=sys.stderr)
    sm = sum(float(live[s]["mem_median_MiB"]) for s in shared)
    sc = sum(float(live[s]["cpu_median_pct"]) for s in shared)
    lines = ["stack\tcontainers\tapps_mem_median\tapps_cpu_median\tapps_threads\tshared_mem\tshared_cpu\t"
             "total_mem_MiB\ttotal_cpu_pct\ttotal_containers"]
    for title, apps in STACKS.items():
        missing = [a for a in apps if a != "readarr*" and a not in bench]
        if missing:
            print(f"not measured, stack left out: {title} ({', '.join(missing)})", file=sys.stderr)
            continue
        rs = [READARR if a == "readarr*" else bench[a] for a in apps]
        m = sum(float(r["mem_median_MiB"]) for r in rs)
        c = sum(float(r["cpu_median_pct"]) for r in rs)
        t = sum(int(r["threads_median"]) for r in rs if str(r["threads_median"]).isdigit())
        lines.append(f"{title}\t{len(apps)}\t{m:.1f}\t{c:.2f}\t{t}\t{sm:.1f}\t{sc:.2f}\t{m + sm:.1f}\t{c + sc:.2f}\t"
                     f"{len(apps) + len(shared)}")
    return lines


def main():
    folder = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    print("\n".join(totals(load(folder / "summary.tsv", "bench-"), load(folder / "summary-live.tsv"))))


if __name__ == "__main__":
    main()
