"""
benchmark_own_timing.py
-----------------------
Runtime cost of each hashing algorithm on the own benchmark dataset.

The accuracy benchmarks (benchmark_own_*.py) say which algorithm is *right*.
This one says what it costs, which is the other half of the decision — the
API recomputes hashes on every /similarity request rather than caching them,
so per-hash latency lands directly in the endpoint's response time.

Three quantities are measured separately, because they scale differently:

  decode      Image.open + load. Paid ONCE per image no matter how many
              algorithms run, so it is a shared constant, not per-algorithm cost.
  hash        compute(path) end to end — decode + resize + transform + threshold.
              This is what the API actually pays today.
  compare     hamming_distance() on two precomputed hash strings. Pure CPU on
              short strings; the unit is microseconds, so it is timed in batches.

`hash_net` (hash - decode) is the part that is genuinely attributable to the
algorithm. Reporting only the end-to-end figure would credit fast algorithms for
sharing the same JPEG decoder as the slow ones.

Outputs (written to benchmark_results/):
    timing_per_algorithm.csv   — one row per algorithm
    timing_per_image.csv       — every (algorithm, image) sample, for distributions

Usage:
    python tests/benchmark_own_timing.py
    python tests/benchmark_own_timing.py --repeats 5
"""

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from PIL import Image

from utils.hash_utils import HASHERS

DATA_DIR = SCRIPT_DIR.parent / "data" / "own"
VARIANTS_CSV = DATA_DIR / "variants.csv"
RESULTS_DIR = SCRIPT_DIR.parent / "benchmark_results"

# Enough iterations that the timer's resolution is not the thing being measured.
COMPARE_BATCH = 2000


def collect_images() -> list[Path]:
    """Every distinct image referenced by variants.csv — originals and variants."""
    seen: dict[str, Path] = {}
    with open(VARIANTS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            for col in ("original_image", "variant_image"):
                rel = row[col]
                if rel not in seen:
                    seen[rel] = DATA_DIR / rel
    return [p for p in seen.values() if p.exists()]


def megapixels(path: Path) -> float:
    with Image.open(path) as im:
        w, h = im.size
    return (w * h) / 1e6


def time_decode(paths: list[Path], repeats: int) -> dict[Path, float]:
    """Median seconds to open and fully decode each image."""
    out = {}
    for p in paths:
        samples = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            with Image.open(p) as im:
                im.load()
            samples.append(time.perf_counter() - t0)
        out[p] = statistics.median(samples)
    return out


def time_hashing(paths: list[Path], repeats: int) -> dict[str, dict[Path, float]]:
    """Median seconds for compute() per (algorithm, image)."""
    out = {}
    for algo, hasher in HASHERS.items():
        # Warm up: first call pays scipy/numpy lazy imports and CPU cache misses.
        for p in paths[:3]:
            hasher.compute(str(p))

        per_image = {}
        for p in paths:
            samples = []
            for _ in range(repeats):
                t0 = time.perf_counter()
                hasher.compute(str(p))
                samples.append(time.perf_counter() - t0)
            per_image[p] = statistics.median(samples)
        out[algo] = per_image
        print(f"  {algo:8s} done")
    return out


def time_compare(sample_path: Path) -> dict[str, float]:
    """Median seconds for one hamming_distance() call, timed in batches."""
    out = {}
    for algo, hasher in HASHERS.items():
        h = hasher.compute(str(sample_path))
        # Flip one bit so the comparison cannot be short-circuited by identity.
        other = ("1" if h[0] == "0" else "0") + h[1:]

        for _ in range(COMPARE_BATCH // 10):
            hasher.hamming_distance(h, other)

        samples = []
        for _ in range(5):
            t0 = time.perf_counter()
            for _ in range(COMPARE_BATCH):
                hasher.hamming_distance(h, other)
            samples.append((time.perf_counter() - t0) / COMPARE_BATCH)
        out[algo] = statistics.median(samples)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3,
                    help="timed runs per image; the median is kept (default 3)")
    args = ap.parse_args()

    print("=" * 78)
    print("Hashing runtime benchmark - own dataset")
    print(f"Dataset : {VARIANTS_CSV}")
    print("=" * 78)

    paths = collect_images()
    if not paths:
        print("[ERROR] no images found; run data/own/generate_variants.py first", file=sys.stderr)
        sys.exit(1)

    total_mp = sum(megapixels(p) for p in paths)
    print(f"\nImages          : {len(paths)}")
    print(f"Total pixels    : {total_mp:.2f} MP  (mean {total_mp / len(paths):.3f} MP/image)")
    print(f"Repeats/image   : {args.repeats}  (median kept)\n")

    print("Timing decode baseline...")
    decode = time_decode(paths, args.repeats)
    decode_median_ms = statistics.median(decode.values()) * 1e3
    print(f"  decode median : {decode_median_ms:.2f} ms/image\n")

    print("Timing hash computation...")
    hashing = time_hashing(paths, args.repeats)

    print("\nTiming hamming distance...")
    compare = time_compare(paths[0])

    # -- per-algorithm aggregate -------------------------------------------
    rows = []
    for algo, hasher in HASHERS.items():
        per_image = hashing[algo]
        ms = [per_image[p] * 1e3 for p in paths]
        mp_rate = [per_image[p] * 1e3 / megapixels(p) for p in paths]
        net = [max(0.0, (per_image[p] - decode[p]) * 1e3) for p in paths]

        rows.append({
            "algorithm": algo,
            "hash_bits": hasher.HASH_BITS,
            "hash_mean_ms": round(statistics.mean(ms), 3),
            "hash_median_ms": round(statistics.median(ms), 3),
            "hash_std_ms": round(statistics.pstdev(ms), 3),
            "hash_min_ms": round(min(ms), 3),
            "hash_max_ms": round(max(ms), 3),
            "hash_net_median_ms": round(statistics.median(net), 3),
            "decode_share_pct": round(100 * decode_median_ms / statistics.median(ms), 1),
            "ms_per_megapixel": round(statistics.median(mp_rate), 2),
            "throughput_img_per_s": round(1.0 / statistics.mean([per_image[p] for p in paths]), 1),
            "compare_us": round(compare[algo] * 1e6, 3),
        })

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    agg_csv = RESULTS_DIR / "timing_per_algorithm.csv"
    with open(agg_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    per_image_csv = RESULTS_DIR / "timing_per_image.csv"
    with open(per_image_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["algorithm", "image", "megapixels", "decode_ms", "hash_ms"])
        for algo in HASHERS:
            for p in paths:
                w.writerow([algo, p.relative_to(DATA_DIR).as_posix(),
                            round(megapixels(p), 4),
                            round(decode[p] * 1e3, 3),
                            round(hashing[algo][p] * 1e3, 3)])

    # -- report ------------------------------------------------------------
    order = sorted(rows, key=lambda r: r["hash_median_ms"])

    print("\n" + "=" * 78)
    print("PER-ALGORITHM RUNTIME")
    print("=" * 78)
    head = f"{'Algorithm':10s} {'Bits':>5s} {'Hash ms':>9s} {'sigma':>7s} {'Net ms':>8s} {'ms/MP':>8s} {'img/s':>8s} {'Cmp us':>8s}"
    print(head)
    print("-" * len(head))
    for r in order:
        print(f"{r['algorithm']:10s} {r['hash_bits']:5d} {r['hash_median_ms']:9.2f} "
              f"{r['hash_std_ms']:7.2f} {r['hash_net_median_ms']:8.2f} "
              f"{r['ms_per_megapixel']:8.2f} {r['throughput_img_per_s']:8.1f} {r['compare_us']:8.2f}")
    print("-" * len(head))
    print(f"{'decode':10s} {'-':>5s} {decode_median_ms:9.2f} {'(shared by all six)':>34s}")

    # -- what this costs the API ------------------------------------------
    all_six_ms = sum(r["hash_median_ms"] for r in rows)
    all_six_net_ms = sum(r["hash_net_median_ms"] for r in rows)
    # One decode reused across the six transforms, instead of six decodes.
    shared_decode_ms = decode_median_ms + all_six_net_ms

    print("\n" + "=" * 78)
    print("PROJECTED COST OF ONE /similarity REQUEST  (k=5)")
    print("=" * 78)
    print("api/similarity.py calls compute_features AND compute_similarities per")
    print("candidate; each computes all six hashes for BOTH images. The query image is")
    print("rehashed for every candidate instead of once.")
    print()
    current = 4 * 5 * all_six_ms          # 2 helpers x 2 images x k, all six algos
    minimal = (1 + 5) * shared_decode_ms  # query once + k candidates, one decode each
    print(f"  all six hashes, one image        : {all_six_ms:8.1f} ms")
    print(f"  same, sharing one decode         : {shared_decode_ms:8.1f} ms")
    print(f"  current implementation (k=5)     : {current:8.1f} ms   <- 4 x 5 x six-hash")
    print(f"  minimal correct equivalent (k=5) : {minimal:8.1f} ms   <- (1 + 5) x six-hash")
    if minimal > 0:
        print(f"  wasted                           : {current - minimal:8.1f} ms  ({current / minimal:.1f}x)")
    print()
    print("Excludes the DINOv2 embedding and the FAISS search (recall stage), and the")
    print("disk read of each candidate's original file.")

    print(f"\n[OK] {agg_csv}")
    print(f"[OK] {per_image_csv}")


if __name__ == "__main__":
    main()
