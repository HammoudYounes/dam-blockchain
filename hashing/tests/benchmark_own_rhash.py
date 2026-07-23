"""
Benchmark RHash against the 'own' dataset.

Produces three CSVs in hashing/benchmark_results/ matching the
exact schema of existing algorithm benchmark outputs:

    rhash_pair_distances.csv   — one row per pair (SIMILAR + DIFFERENT)
    rhash_per_transform.csv    — per-transformation accuracy at best threshold
    rhash_threshold_sweep.csv  — precision/recall/F1 across all thresholds

Run from the repo root (dam-blockchain/):
    python hashing/tests/benchmark_own_rhash.py
"""

import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.rhash import RadialHash

# Initialize RadialHash
rhash = RadialHash()

# ── Paths ──────────────────────────────────────────────────────────────────
DATASET_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "own")
VARIANTS_CSV = os.path.join(DATASET_DIR, "variants.csv")
RESULTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "benchmark_results")

PAIR_DISTANCES_CSV  = os.path.join(RESULTS_DIR, "rhash_pair_distances.csv")
PER_TRANSFORM_CSV   = os.path.join(RESULTS_DIR, "rhash_per_transform.csv")
THRESHOLD_SWEEP_CSV = os.path.join(RESULTS_DIR, "rhash_threshold_sweep.csv")

os.makedirs(RESULTS_DIR, exist_ok=True)

HASH_BITS = 64


# ── Step 1: load variants.csv — SIMILAR pairs ─────────────────────────────

def load_similar_pairs():
    pairs = []
    with open(VARIANTS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append({
                "image_a":        row["original_image"],
                "image_b":        row["variant_image"],
                "label":          1,
                "transformation": row["transformation"],
            })
    return pairs


# ── Step 2: build DIFFERENT cross-image pairs ─────────────────────────────

def build_different_pairs(similar_pairs):
    """
    Pair each original against all images (originals + variants) of every
    other original — matching the cross_image structure in existing CSVs.
    Deduplicate (A,B) / (B,A) pairs.
    """
    originals = {}
    for p in similar_pairs:
        orig = p["image_a"]
        if orig not in originals:
            originals[orig] = []
        originals[orig].append(p["image_b"])

    original_list = list(originals.keys())
    different_pairs = []

    for orig_a in original_list:
        for orig_b in original_list:
            if orig_a == orig_b:
                continue
            different_pairs.append({
                "image_a":        orig_a,
                "image_b":        orig_b,
                "label":          0,
                "transformation": "cross_image",
            })
            for var_b in originals[orig_b]:
                different_pairs.append({
                    "image_a":        orig_a,
                    "image_b":        var_b,
                    "label":          0,
                    "transformation": "cross_image",
                })

    seen = set()
    deduped = []
    for p in different_pairs:
        key = tuple(sorted([p["image_a"], p["image_b"]]))
        if key not in seen:
            seen.add(key)
            deduped.append(p)

    return deduped


# ── Step 3: compute hashes and distances ──────────────────────────────────

def compute_all_distances(pairs):
    hash_cache = {}
    results = []

    for p in pairs:
        path_a = os.path.join(DATASET_DIR, p["image_a"])
        path_b = os.path.join(DATASET_DIR, p["image_b"])

        if not os.path.exists(path_a) or not os.path.exists(path_b):
            print(f"  [SKIP] {p['image_a']} or {p['image_b']}")
            continue

        if p["image_a"] not in hash_cache:
            hash_cache[p["image_a"]] = rhash.compute(path_a)
        if p["image_b"] not in hash_cache:
            hash_cache[p["image_b"]] = rhash.compute(path_b)

        dist = rhash.hamming_distance(hash_cache[p["image_a"]], hash_cache[p["image_b"]])

        results.append({
            "image_a":          p["image_a"],
            "image_b":          p["image_b"],
            "label":            p["label"],
            "transformation":   p["transformation"],
            "hamming_distance": dist,
        })

        label_str = "SIMILAR  " if p["label"] == 1 else "DIFFERENT"
        print(f"  [{label_str}]  {os.path.basename(p['image_a']):28s} "
              f"vs {os.path.basename(p['image_b']):32s}  dist={dist:2d}")

    return results


# ── Step 4: threshold sweep ────────────────────────────────────────────────

def run_threshold_sweep(results):
    total = len(results)
    sweep = []

    for threshold in range(HASH_BITS):
        tp = sum(1 for r in results if r["label"] == 1 and r["hamming_distance"] <= threshold)
        tn = sum(1 for r in results if r["label"] == 0 and r["hamming_distance"] >  threshold)
        fp = sum(1 for r in results if r["label"] == 0 and r["hamming_distance"] <= threshold)
        fn = sum(1 for r in results if r["label"] == 1 and r["hamming_distance"] >  threshold)

        accuracy  = (tp + tn) / total if total > 0 else 0.0
        precision = tp / (tp + fp)    if (tp + fp) > 0 else 1.0
        recall    = tp / (tp + fn)    if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)

        sweep.append({
            "threshold":     threshold,
            "accuracy":      accuracy,
            "precision":     precision,
            "recall":        recall,
            "f1":            f1,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            "best_accuracy": False,
            "best_f1":       False,
        })

    best_acc_val = max(s["accuracy"] for s in sweep)
    best_f1_val  = max(s["f1"]       for s in sweep)

    first_best_acc = True
    first_best_f1  = True
    for s in sweep:
        if s["accuracy"] == best_acc_val and first_best_acc:
            s["best_accuracy"] = True
            first_best_acc = False
        if s["f1"] == best_f1_val and first_best_f1:
            s["best_f1"] = True
            first_best_f1 = False

    return sweep


# ── Step 5: per-transformation accuracy at best threshold ─────────────────

def compute_per_transform(results, sweep):
    best_threshold = next(s["threshold"] for s in sweep if s["best_f1"])
    similar_only   = [r for r in results if r["label"] == 1]

    groups = defaultdict(list)
    for r in similar_only:
        groups[r["transformation"]].append(r)

    per_transform = []
    for transform, group in sorted(groups.items()):
        correct      = sum(1 for r in group if r["hamming_distance"] <= best_threshold)
        total        = len(group)
        accuracy_pct = round(correct / total * 100, 2) if total > 0 else 0.0
        mean_dist    = round(sum(r["hamming_distance"] for r in group) / total, 4)
        max_dist     = max(r["hamming_distance"] for r in group)

        per_transform.append({
            "transformation": transform,
            "correct":        correct,
            "total":          total,
            "accuracy_pct":   accuracy_pct,
            "mean_dist":      mean_dist,
            "max_dist":       max_dist,
        })

    return per_transform, best_threshold


# ── Step 6: write CSVs ─────────────────────────────────────────────────────

def write_csvs(results, per_transform, sweep):
    with open(PAIR_DISTANCES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "image_a", "image_b", "label", "transformation", "hamming_distance"
        ])
        writer.writeheader()
        writer.writerows(results)

    with open(PER_TRANSFORM_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "transformation", "correct", "total",
            "accuracy_pct", "mean_dist", "max_dist"
        ])
        writer.writeheader()
        writer.writerows(per_transform)

    with open(THRESHOLD_SWEEP_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "threshold", "accuracy", "precision", "recall", "f1",
            "tp", "tn", "fp", "fn", "best_accuracy", "best_f1"
        ])
        writer.writeheader()
        writer.writerows(sweep)

    print(f"\n  → {PAIR_DISTANCES_CSV}")
    print(f"  → {PER_TRANSFORM_CSV}")
    print(f"  → {THRESHOLD_SWEEP_CSV}")


# ── Console summary ────────────────────────────────────────────────────────

def print_summary(per_transform, sweep, best_threshold):
    best = next(s for s in sweep if s["best_f1"])

    print("\n" + "=" * 70)
    print(f"  Best threshold : {best_threshold}")
    print(f"  Accuracy       : {best['accuracy']:.4f}")
    print(f"  Precision      : {best['precision']:.4f}")
    print(f"  Recall         : {best['recall']:.4f}")
    print(f"  F1             : {best['f1']:.4f}")
    print(f"  TP={best['tp']}  TN={best['tn']}  "
          f"FP={best['fp']}  FN={best['fn']}")
    print("=" * 70)
    print(f"\n  {'Transformation':<25s} {'Correct':>7s} {'Total':>6s} "
          f"{'Accuracy':>9s} {'Mean Dist':>10s} {'Max Dist':>9s}")
    print("  " + "-" * 68)
    for row in per_transform:
        print(f"  {row['transformation']:<25s} {row['correct']:>7d} "
              f"{row['total']:>6d} {row['accuracy_pct']:>8.2f}% "
              f"{row['mean_dist']:>10.4f} {row['max_dist']:>9d}")
    print()


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nRHash benchmark — own dataset")
    print("─" * 70)

    similar_pairs   = load_similar_pairs()
    different_pairs = build_different_pairs(similar_pairs)
    all_pairs       = similar_pairs + different_pairs

    print(f"\n  {len(similar_pairs)} SIMILAR + "
          f"{len(different_pairs)} DIFFERENT = {len(all_pairs)} total pairs\n")

    results = compute_all_distances(all_pairs)

    if not results:
        print("No results. Check variants.csv and image paths.")
        sys.exit(1)

    sweep                         = run_threshold_sweep(results)
    per_transform, best_threshold = compute_per_transform(results, sweep)

    print_summary(per_transform, sweep, best_threshold)
    write_csvs(results, per_transform, sweep)

    print("Done.\n")