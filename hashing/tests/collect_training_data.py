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
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from algorithms.ahash import compute as ahash_compute, hamming_distance as ahash_hamming
from algorithms.phash import compute as phash_compute, hamming_distance as phash_hamming
from algorithms.dhash import compute as dhash_compute, hamming_distance as dhash_hamming
from algorithms.HSVHash import hsv_hash, hamming as hsv_hamming

DATA_DIR = SCRIPT_DIR.parent / "data" / "own"
VARIANTS_CSV = DATA_DIR / "variants.csv"
RESULTS_DIR = SCRIPT_DIR.parent / "benchmark_results"
OUTPUT_CSV = RESULTS_DIR / "training_data.csv"

AHASH_BITS = 64
PHASH_BITS = 63   # 8×8 DCT block minus the DC coefficient
DHASH_BITS = 72   # 9×8 gradient grid
HSV_BITS = 42     # 14 bins × 3 bits


# ---------------------------------------------------------------------------
# Per-algorithm hash caches (keyed by relative path string)
# ---------------------------------------------------------------------------

_ahash_cache: dict[str, str] = {}
_phash_cache: dict[str, str] = {}
_dhash_cache: dict[str, str] = {}
_hsv_cache: dict[str, np.ndarray] = {}


def _load_rgb(rel_path: str) -> np.ndarray:
    return np.asarray(Image.open(DATA_DIR / rel_path).convert("RGB"))


def get_ahash(rel_path: str) -> str:
    if rel_path not in _ahash_cache:
        _ahash_cache[rel_path] = ahash_compute(str(DATA_DIR / rel_path))
    return _ahash_cache[rel_path]


def get_phash(rel_path: str) -> str:
    if rel_path not in _phash_cache:
        _phash_cache[rel_path] = phash_compute(str(DATA_DIR / rel_path))
    return _phash_cache[rel_path]


def get_dhash(rel_path: str) -> str:
    if rel_path not in _dhash_cache:
        _dhash_cache[rel_path] = dhash_compute(str(DATA_DIR / rel_path))
    return _dhash_cache[rel_path]


def get_hsv(rel_path: str) -> np.ndarray:
    if rel_path not in _hsv_cache:
        _hsv_cache[rel_path] = hsv_hash(_load_rgb(rel_path))
    return _hsv_cache[rel_path]


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
    return {
        "ahash_dist":   ahash_hamming(get_ahash(path_a), get_ahash(path_b)) / AHASH_BITS,
        "phash_dist":   phash_hamming(get_phash(path_a), get_phash(path_b)) / PHASH_BITS,
        "dhash_dist":   dhash_hamming(get_dhash(path_a), get_dhash(path_b)) / DHASH_BITS,
        "hsvhash_dist": hsv_hamming(get_hsv(path_a), get_hsv(path_b)) / HSV_BITS,
    }


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
