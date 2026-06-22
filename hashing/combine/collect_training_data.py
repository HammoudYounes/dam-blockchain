"""
Collect training data for logistic regression combining all hash algorithms.

For every pair (img_A, img_B) — both positive (duplicate) and negative (non-duplicate) —
compute the four normalised Hamming distances and write one row to a CSV:

    ahash_dist   = hamming(aHash_A,   aHash_B)   / 64
    phash_dist   = hamming(pHash_A,   pHash_B)   / 63
    dhash_dist   = hamming(dHash_A,   dHash_B)   / 72
    hsvhash_dist = hamming(HSVHash_A, HSVHash_B) / 42
    label        = 1 (duplicate) | 0 (non-duplicate)

Output: hashing/benchmark_results/training_data.csv 

Run from the hashing/ directory:
    python tests/collect_training_data.py
"""

import csv
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from algorithms.ahash import AverageHash
from algorithms.phash import PerceptualHash
from algorithms.dhash import DifferenceHash
from algorithms.HSVHash import HSVColorHash

DATA_DIR = SCRIPT_DIR.parent / "data" / "own"
VARIANTS_CSV = DATA_DIR / "variants.csv"
RESULTS_DIR = SCRIPT_DIR.parent / "benchmark_results"
OUTPUT_CSV = RESULTS_DIR / "training_data.csv"

# One hasher per algorithm. The dict key is the CSV column prefix; each hasher
# carries its own HASH_BITS used to normalise the Hamming distance.
HASHERS = {
    "ahash":   AverageHash(),
    "phash":   PerceptualHash(),
    "dhash":   DifferenceHash(),
    "hsvhash": HSVColorHash(),
}


# ---------------------------------------------------------------------------
# Per-algorithm hash caches (keyed by relative path string)
# ---------------------------------------------------------------------------

_caches: dict[str, dict[str, str]] = {name: {} for name in HASHERS}


def get_hash(algo: str, rel_path: str) -> str:
    cache = _caches[algo]
    if rel_path not in cache:
        cache[rel_path] = HASHERS[algo].compute(str(DATA_DIR / rel_path))
    return cache[rel_path]


# ---------------------------------------------------------------------------
# Pair loading (identical logic to the per-algorithm benchmarks)
# ---------------------------------------------------------------------------

def load_pairs():
    """
    Returns:
        positives : list of (orig_path, variant_path, transformation)  label=1
        negatives : list of (path_a, path_b, "cross_image")             label=0
    """
    positives = []
    groups: dict[str, list[str]] = {}

    with VARIANTS_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            orig = row["original_image"]
            variant = row["variant_image"]
            transform = row["transformation"]
            positives.append((orig, variant, transform))
            groups.setdefault(orig, []).append(variant)

    negatives = []
    for orig_a, orig_b in combinations(groups.keys(), 2):
        variants_a = groups[orig_a]
        variants_b = groups[orig_b]
        negatives.append((orig_a, orig_b, "cross_image"))
        negatives.extend((orig_a, vb, "cross_image") for vb in variants_b)
        negatives.extend((orig_b, va, "cross_image") for va in variants_a)

    return positives, negatives


# ---------------------------------------------------------------------------
# Feature computation
# ---------------------------------------------------------------------------

def compute_features(path_a: str, path_b: str) -> dict:
    feats = {}
    for algo, hasher in HASHERS.items():
        dist = hasher.hamming_distance(get_hash(algo, path_a), get_hash(algo, path_b))
        feats[f"{algo}_dist"] = dist / hasher.HASH_BITS
    return feats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Training Data Collection — Combined Hash Features")
    print(f"Dataset : {VARIANTS_CSV}")
    print("=" * 70)

    positives, negatives = load_pairs()
    print(f"\nPositive pairs : {len(positives)}")
    print(f"Negative pairs : {len(negatives)}")
    print(f"Total pairs    : {len(positives) + len(negatives)}")

    print("\nComputing features for all pairs...")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "image_a", "image_b", "transformation", "label",
        "ahash_dist", "phash_dist", "dhash_dist", "hsvhash_dist",
    ]

    rows = []

    all_pairs = (
        [(a, b, t, 1) for a, b, t in positives] +
        [(a, b, t, 0) for a, b, t in negatives]
    )

    for i, (path_a, path_b, transform, label) in enumerate(all_pairs, 1):
        feats = compute_features(path_a, path_b)
        rows.append({
            "image_a": path_a,
            "image_b": path_b,
            "transformation": transform,
            "label": label,
            **feats,
        })
        if i % 50 == 0 or i == len(all_pairs):
            print(f"  {i}/{len(all_pairs)} pairs processed")

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved {len(rows)} rows to: {OUTPUT_CSV}")

    # Quick sanity check: mean distances per class
    pos_rows = [r for r in rows if r["label"] == 1]
    neg_rows = [r for r in rows if r["label"] == 0]
    print("\nMean normalised distances by class:")
    print(f"{'Algorithm':<14} {'Positive (dup)':>15} {'Negative (non-dup)':>19}")
    print("-" * 52)
    for col in ("ahash_dist", "phash_dist", "dhash_dist", "hsvhash_dist"):
        pos_mean = np.mean([r[col] for r in pos_rows])
        neg_mean = np.mean([r[col] for r in neg_rows])
        print(f"{col:<14} {pos_mean:>15.4f} {neg_mean:>19.4f}")


if __name__ == "__main__":
    main()
