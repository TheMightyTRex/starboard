#!/usr/bin/env python3
"""Summarise docker stats samples: one row per container, with the median and highest of its samples.

    python3 -I summarise.py samples.txt [more files] > summary.tsv

Lines look like: HH:MM:SS name 0.12% 150.3MiB / 15.53GiB 23"""
import statistics
import sys

UNITS = {"B": 1 / 1048576, "KiB": 1 / 1024, "kB": 1 / 1024, "MiB": 1, "MB": 1, "GiB": 1024, "GB": 1024}


def mib(text):
    for unit in sorted(UNITS, key=len, reverse=True):
        if text.endswith(unit):
            return float(text[: -len(unit)]) * UNITS[unit]
    raise ValueError(text)


def collect(lines):
    data = {}
    for line in lines:
        parts = line.split()
        if len(parts) < 7 or not parts[2].endswith("%"):
            continue
        name, cpu, mem, pids = parts[1], float(parts[2][:-1]), mib(parts[3]), parts[6]
        d = data.setdefault(name, {"cpu": [], "mem": [], "pids": []})
        d["cpu"].append(cpu)
        d["mem"].append(mem)
        if pids.isdigit():
            d["pids"].append(int(pids))
    return data


def rows(data):
    out = ["name\tsamples\tmem_median_MiB\tmem_peak_MiB\tcpu_median_pct\tcpu_mean_pct\tcpu_peak_pct\tthreads_median"]
    for name, d in sorted(data.items()):
        out.append(
            f"{name}\t{len(d['cpu'])}\t{statistics.median(d['mem']):.1f}\t{max(d['mem']):.1f}\t"
            f"{statistics.median(d['cpu']):.2f}\t{statistics.mean(d['cpu']):.2f}\t{max(d['cpu']):.2f}\t"
            f"{int(statistics.median(d['pids'])) if d['pids'] else '-'}"
        )
    return out


def main():
    lines = []
    for path in sys.argv[1:]:
        with open(path) as f:
            lines += f.readlines()
    print("\n".join(rows(collect(lines))))


if __name__ == "__main__":
    main()
