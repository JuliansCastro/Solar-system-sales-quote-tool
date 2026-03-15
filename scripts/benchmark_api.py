"""Simple benchmark script for API latency percentiles (P95/P99)."""

import argparse
import statistics
import time

import requests


def percentile(values, p):
    if not values:
        return 0
    ordered = sorted(values)
    k = max(0, min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[k]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--cookie", default="")
    args = parser.parse_args()

    timings = []
    headers = {}
    if args.cookie:
        headers["Cookie"] = args.cookie

    for _ in range(args.iterations):
        start = time.perf_counter()
        response = requests.get(args.url, headers=headers, timeout=20)
        response.raise_for_status()
        timings.append((time.perf_counter() - start) * 1000)

    p95 = percentile(timings, 95)
    p99 = percentile(timings, 99)

    print(f"Samples: {len(timings)}")
    print(f"Mean ms: {statistics.mean(timings):.2f}")
    print(f"P95 ms: {p95:.2f}")
    print(f"P99 ms: {p99:.2f}")


if __name__ == "__main__":
    main()
