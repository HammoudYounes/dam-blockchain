"""
Extend the training dataset with DISC21 image pairs.

Reads:
  - hashing/benchmark_results/training_data.csv        (existing own-dataset pairs)
  - Dataset/disc21/filtered_images/filtered_ground_truth.csv
  - Dataset/disc21/filtered_images/queries/   (Q*.jpg)
  - Dataset/disc21/filtered_images/references/ (R*.jpg)

For every matched pair in the ground-truth CSV:
    reference <-> query  => label=1, transformation="disc21"

For negative pairs (label=0, transformation="disc21_neg"):
    randomly sample `NEG_RATIO` non-matching (reference, query) pairs per
    positive pair, ensuring no sampled pair appears in the ground truth.

Output: hashing/benchmark_results/combined_training_data.csv

Run from the hashing/ directory:
    python tests/collect_disc21_training_data.py
"""

import csv
import random
import sys
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))

from algorithms.ahash import AverageHash
from algorithms.phash import PerceptualHash
from algorithms.dhash import DifferenceHash
from algorithms.HSVHash import HSVColorHash
from algorithms.rhash import RadialHash
from algorithms.Chash import ColorHash

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT      = SCRIPT_DIR.parent.parent          # dam-blockchain/
DATASET_ROOT   = REPO_ROOT.parent.parent / "Dataset" / "disc21" / "filtered_images"
QUERY_DIR      = DATASET_ROOT / "queries"
REF_DIR        = DATASET_ROOT / "references"
GROUND_TRUTH   = DATASET_ROOT / "filtered_ground_truth.csv"

RESULTS_DIR    = SCRIPT_DIR.parent / "benchmark_results"
EXISTING_CSV   = RESULTS_DIR / "training_data.csv"
OUTPUT_CSV     = RESULTS_DIR / "combined_training_data.csv"

# ── Hashers ───────────────────────────────────────────────────────────────────
# The dict key is the CSV column prefix; each hasher carries its own HASH_BITS
# used to normalise the Hamming distance.
HASHERS = {
    "ahash":   AverageHash(),
    "phash":   PerceptualHash(),
    "dhash":   DifferenceHash(),
    "hsvhash": HSVColorHash(),
    "rhash":   RadialHash(),
    "chash":   ColorHash(),
}

# How many negative pairs to generate per positive pair
NEG_RATIO = 1

RANDOM_SEED = 42

# ── Per-image hash caches (one dict per algorithm) ────────────────────────────
_caches: dict[str, dict[str, str]] = {name: {} for name in HASHERS}


def get_hash(algo: str, path: Path) -> str:
    cache = _caches[algo]
    k = str(path)
    if k not in cache:
        cache[k] = HASHERS[algo].compute(k)
    return cache[k]


def compute_features(path_a: Path, path_b: Path) -> dict:
    feats = {}
    for algo, hasher in HASHERS.items():
        dist = hasher.hamming_distance(get_hash(algo, path_a), get_hash(algo, path_b))
        feats[f"{algo}_dist"] = dist / hasher.HASH_BITS
    return feats


# ── Load ground truth ─────────────────────────────────────────────────────────
def load_ground_truth():
    """Returns list of (ref_filename, query_filename) and a set for fast lookup."""
    pairs = []
    with GROUND_TRUTH.open(newline="") as f:
        for row in csv.DictReader(f):
            pairs.append((row["reference"], row["query"]))
    gt_set = set(pairs)
    return pairs, gt_set


# ── Sample negatives ──────────────────────────────────────────────────────────
def sample_negatives(gt_pairs, gt_set, all_refs, all_queries, n_neg, rng):
    """
    Sample n_neg (reference, query) pairs that do NOT appear in gt_set.
    Shuffles globally and keeps the first n_neg non-matching pairs found.
    """
    negatives = []
    refs_shuffled   = list(all_refs)
    queries_shuffled = list(all_queries)
    rng.shuffle(refs_shuffled)
    rng.shuffle(queries_shuffled)

    for ref in refs_shuffled:
        for q in queries_shuffled:
            if (ref, q) not in gt_set:
                negatives.append((ref, q))
                if len(negatives) >= n_neg:
                    return negatives
    return negatives


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("DISC21 Training Data Collection")
    print(f"Ground truth : {GROUND_TRUTH}")
    print(f"Queries dir  : {QUERY_DIR}")
    print(f"References   : {REF_DIR}")
    print("=" * 70)

    if not GROUND_TRUTH.exists():
        sys.exit(f"ERROR: ground truth CSV not found at {GROUND_TRUTH}")
    if not QUERY_DIR.exists() or not REF_DIR.exists():
        sys.exit(f"ERROR: image directories not found under {DATASET_ROOT}")

    gt_pairs, gt_set = load_ground_truth()
    all_refs    = [p.name for p in sorted(REF_DIR.glob("*.jpg"))]
    all_queries = [p.name for p in sorted(QUERY_DIR.glob("*.jpg"))]

    n_pos = len(gt_pairs)
    n_neg = n_pos * NEG_RATIO
    print(f"\nPositive pairs (ground truth) : {n_pos}")
    print(f"Negative pairs to sample      : {n_neg}  (ratio {NEG_RATIO}:1)")

    rng = random.Random(RANDOM_SEED)
    neg_pairs = sample_negatives(gt_pairs, gt_set, all_refs, all_queries, n_neg, rng)
    print(f"Negative pairs sampled        : {len(neg_pairs)}")

    fieldnames = [
        "image_a", "image_b", "transformation", "label",
        "ahash_dist", "phash_dist", "dhash_dist", "hsvhash_dist",
        "rhash_dist", "chash_dist",
    ]

    disc21_rows = []
    all_pairs = (
        [(ref, q, "disc21", 1) for ref, q in gt_pairs] +
        [(ref, q, "disc21_neg", 0) for ref, q in neg_pairs]
    )

    print("\nComputing hash distances for DISC21 pairs...")
    for i, (ref_name, q_name, transform, label) in enumerate(all_pairs, 1):
        ref_path = REF_DIR   / ref_name
        q_path   = QUERY_DIR / q_name
        feats = compute_features(ref_path, q_path)
        disc21_rows.append({
            "image_a": f"references/{ref_name}",
            "image_b": f"queries/{q_name}",
            "transformation": transform,
            "label": label,
            **feats,
        })
        if i % 100 == 0 or i == len(all_pairs):
            print(f"  {i}/{len(all_pairs)} pairs processed")

    # ── Load existing training data ───────────────────────────────────────────
    existing_rows = []
    if EXISTING_CSV.exists():
        with EXISTING_CSV.open(newline="") as f:
            existing_rows = list(csv.DictReader(f))
        print(f"\nExisting training_data.csv : {len(existing_rows)} rows")
    else:
        print(f"\nWARNING: {EXISTING_CSV} not found — output will contain only DISC21 data")

    # ── Write combined CSV ────────────────────────────────────────────────────
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = existing_rows + disc21_rows

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} rows to: {OUTPUT_CSV}")
    print(f"  Own dataset rows  : {len(existing_rows)}")
    print(f"  DISC21 rows       : {len(disc21_rows)}")
    print(f"    positives (dup) : {sum(1 for r in disc21_rows if int(r['label']) == 1)}")
    print(f"    negatives       : {sum(1 for r in disc21_rows if int(r['label']) == 0)}")

    # ── Quick sanity check ────────────────────────────────────────────────────
    pos = [r for r in all_rows if int(r["label"]) == 1]
    neg = [r for r in all_rows if int(r["label"]) == 0]
    print(f"\nCombined label balance: {len(pos)} positives, {len(neg)} negatives "
          f"(positive rate = {len(pos)/len(all_rows):.2%})")
    print("\nMean normalised distances by class (combined):")
    print(f"{'Algorithm':<14} {'Positive (dup)':>15} {'Negative (non-dup)':>19}")
    print("-" * 52)
    for col in ("ahash_dist", "phash_dist", "dhash_dist", "hsvhash_dist",
                "rhash_dist", "chash_dist"):
        pos_mean = np.mean([float(r[col]) for r in pos])
        neg_mean = np.mean([float(r[col]) for r in neg])
        print(f"{col:<14} {pos_mean:>15.4f} {neg_mean:>19.4f}")


if __name__ == "__main__":
    main()
