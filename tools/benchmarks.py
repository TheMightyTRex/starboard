#!/usr/bin/env python3
"""Repeatable, local Starboard performance baselines (no external media apps or Docker required).

Run from the repository root:
    python3 tools/benchmarks.py --iterations 500 --concurrency 8

The output is descriptive rather than a pass/fail threshold: compare JSON reports from the same host,
Python version and configuration. It measures HTTP health/session/static paths, shared-cache hit/miss,
background-job queue dispatch and the cache's bounded memory footprint.
"""
import argparse
import concurrent.futures
import http.client
import json
import os
import platform
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def summary(samples):
    ordered = sorted(samples)
    at = lambda p: ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]
    total = sum(samples)
    return {
        "count": len(samples),
        "mean_ms": round(statistics.mean(samples) * 1000, 3),
        "p50_ms": round(at(0.50) * 1000, 3),
        "p95_ms": round(at(0.95) * 1000, 3),
        "throughput_per_second": round(len(samples) / total, 1) if total else 0,
    }


def http_sample(port, path):
    started = time.perf_counter()
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path, headers={"Host": f"127.0.0.1:{port}"})
        response = conn.getresponse()
        response.read()
        if response.status != 200:
            raise RuntimeError(f"{path} returned HTTP {response.status}")
    finally:
        conn.close()
    return time.perf_counter() - started


def run(args):
    # Keep the benchmark hermetic: app startup must not launch background maintenance jobs.
    for key in ("STARBOARD_HISTORY", "STARBOARD_SCHEDULE", "STARBOARD_WATCH", "STARBOARD_JOBS"):
        os.environ[key] = "0"
    from starboard import services
    from starboard.jobs import JOBS, Jobs
    from starboard.server import make_server

    with tempfile.TemporaryDirectory(prefix="starboard-bench-") as data_dir:
        server, app = make_server("127.0.0.1", 0, data_dir)
        thread = threading.Thread(target=server.serve_forever, name="starboard-benchmark-server", daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            http = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                for name, path in (("healthz", "/healthz"), ("session_api", "/api/session"), ("login_static", "/login.html")):
                    started = time.perf_counter()
                    samples = list(pool.map(lambda _: http_sample(port, path), range(args.iterations)))
                    http[name] = {**summary(samples), "wall_seconds": round(time.perf_counter() - started, 3)}

            services.forget()
            services.cache_stats(reset=True)
            services.cached("benchmark-hit", 60, lambda: {"ok": True})
            started = time.perf_counter()
            for _ in range(args.iterations):
                services.cached("benchmark-hit", 60, lambda: {"ok": False})
            cache_hit = time.perf_counter() - started

            started = time.perf_counter()
            for i in range(args.iterations):
                services.cached(f"benchmark-miss-{i}", 60, lambda: i)
            cache_miss = time.perf_counter() - started
            cache_memory = services.cache_stats()

            # Isolate queue/scheduler overhead from the cost and variability of real jobs.
            fake_app = SimpleNamespace(config=SimpleNamespace(data_dir=data_dir, data={"extras": {}, "services": {}}), data_dir=data_dir)
            jobs = Jobs(fake_app)
            jobs._execute = lambda key, force=False: None
            batches = max(1, args.iterations // len(JOBS))
            started = time.perf_counter()
            for _ in range(batches):
                for key in JOBS:
                    jobs.run_soon(key)
                jobs.work.join()
            job_elapsed = time.perf_counter() - started

            tracemalloc.start()
            services.forget()
            for i in range(args.iterations * 4):
                services.cached(f"benchmark-memory-{i}", 600, lambda: "x" * 256)
            _, peak_memory = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            return {
                "environment": {"python": platform.python_version(), "platform": platform.platform(),
                                "iterations": args.iterations, "concurrency": args.concurrency},
                "http": http,
                "cache": {"hit_total_ms": round(cache_hit * 1000, 3),
                          "miss_total_ms": round(cache_miss * 1000, 3),
                          "stats_after_misses": cache_memory,
                          "bounded_cache_peak_tracemalloc_bytes": peak_memory},
                "background_jobs": {"batches": batches, "jobs_per_batch": len(JOBS),
                                     "total_jobs": batches * len(JOBS), "wall_seconds": round(job_elapsed, 3),
                                     "jobs_per_second": round(batches * len(JOBS) / job_elapsed, 1) if job_elapsed else 0},
            }
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--json", dest="json_path", help="also write the report to this path")
    args = parser.parse_args()
    if args.iterations < 1 or args.concurrency < 1 or args.concurrency > 64:
        parser.error("iterations must be positive and concurrency must be between 1 and 64")
    report = run(args)
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            f.write(rendered + "\n")


if __name__ == "__main__":
    main()
