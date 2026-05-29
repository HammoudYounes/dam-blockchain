"""
Benchmark HSVHash: find the optimal Hamming-distance threshold that maximises
accuracy on the variants.csv ground-truth dataset.

Dataset layout (relative to this script):
  ../data/own/variants.csv          — positive pairs (original → variant)
  ../data/own/images/               — 3 original images
  ../data/own/images_variants/      — transformed variants

Ground-truth labels:
  positive (label=1) : every (original, variant) row in variants.csv
  negative (label=0) : all cross-source-image pairs
                       (original_A vs original_B/variants_B, etc.)

The hash is 42 bits (binbits=3), so threshold sweeps over 0..42.
"""

import sys
import csv
from pathlib import Path
from itertools import combinations, product

import numpy as np
from PIL import Image

# Allow running from any working directory
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "own"
VARIANTS_CSV = DATA_DIR / "variants.csv"
RESULTS_DIR = SCRIPT_DIR.parent / "benchmark_results"

sys.path.insert(0, str(SCRIPT_DIR.parent / "algorithms"))
from HSVHash import hsv_hash, hamming

MAX_BITS = 42  # 14 bins × 3 binbits


# ---------------------------------------------------------------------------
# Image cache so each file is loaded and hashed only once
# ---------------------------------------------------------------------------

_hash_cache: dict[str, np.ndarray] = {}


def get_hash(rel_path: str) -> np.ndarray:
    if rel_path not in _hash_cache:
        abs_path = DATA_DIR / rel_path
        img = np.asarray(Image.open(abs_path).convert("RGB"))
        _hash_cache[rel_path] = hsv_hash(img)
    return _hash_cache[rel_path]


# ---------------------------------------------------------------------------
# Build pairs
# ---------------------------------------------------------------------------

def load_pairs():
    """
    Returns:
        positives : list of (orig_path, variant_path, transformation)
        negatives : list of (path_a, path_b, "cross_image")
    """
    positives = []
    # group -> (original_path, [variant_paths])
    groups: dict[str, tuple[str, list[str]]] = {}

    with open(VARIANTS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            orig = row["original_image"]
            variant = row["variant_image"]
            transform = row["transformation"]
            positives.append((orig, variant, transform))
            if orig not in groups:
                groups[orig] = (orig, [])
            groups[orig][1].append(variant)

    # Negatives: all cross-group pairs
    # For each pair of different source images, compare:
    #   original_A vs original_B
    #   original_A vs every variant_B
    #   original_B vs every variant_A
    group_keys = list(groups.keys())
    negatives = []

    for orig_a, orig_b in combinations(group_keys, 2):
        variants_a = groups[orig_a][1]
        variants_b = groups[orig_b][1]

        negatives.append((orig_a, orig_b, "cross_image"))

        for v in variants_b:
            negatives.append((orig_a, v, "cross_image"))
        for v in variants_a:
            negatives.append((orig_b, v, "cross_image"))

    return positives, negatives


# ---------------------------------------------------------------------------
# Threshold sweep
# ---------------------------------------------------------------------------

def evaluate_threshold(distances: np.ndarray, labels: np.ndarray, threshold: int):
    preds = (distances <= threshold).astype(int)
    tp = int(((preds == 1) & (labels == 1)).sum())
    tn = int(((preds == 0) & (labels == 0)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    total = len(labels)
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"threshold": threshold, "accuracy": accuracy,
            "precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn}


# ---------------------------------------------------------------------------
# Per-transformation breakdown at a given threshold
# ---------------------------------------------------------------------------

def per_transform_report(positives, threshold: int):
    """For each transformation type, report whether the hash correctly identifies
    the variant as 'same image' (distance <= threshold)."""
    transform_stats: dict[str, dict] = {}
    for orig, variant, transform in positives:
        d = hamming(get_hash(orig), get_hash(variant))
        correct = d <= threshold
        if transform not in transform_stats:
            transform_stats[transform] = {"correct": 0, "total": 0, "distances": []}
        transform_stats[transform]["correct"] += int(correct)
        transform_stats[transform]["total"] += 1
        transform_stats[transform]["distances"].append(d)
    return transform_stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("HSVHash Benchmark — Hamming Threshold Optimisation")
    print(f"Dataset : {VARIANTS_CSV}")
    print("=" * 70)

    positives, negatives = load_pairs()
    n_pos = len(positives)
    n_neg = len(negatives)
    print(f"\nPositive pairs (same image)   : {n_pos}")
    print(f"Negative pairs (cross-image)  : {n_neg}")
    print(f"Total pairs                   : {n_pos + n_neg}")

    # Pre-compute all Hamming distances
    print("\nComputing hashes and distances …")
    pos_distances = np.array([
        hamming(get_hash(o), get_hash(v)) for o, v, _ in positives
    ])
    neg_distances = np.array([
        hamming(get_hash(a), get_hash(b)) for a, b, _ in negatives
    ])

    all_distances = np.concatenate([pos_distances, neg_distances])
    all_labels = np.concatenate([np.ones(n_pos, dtype=int),
                                  np.zeros(n_neg, dtype=int)])

    print(f"\nPositive distances — mean: {pos_distances.mean():.2f}  "
          f"std: {pos_distances.std():.2f}  "
          f"min: {pos_distances.min()}  max: {pos_distances.max()}")
    print(f"Negative distances — mean: {neg_distances.mean():.2f}  "
          f"std: {neg_distances.std():.2f}  "
          f"min: {neg_distances.min()}  max: {neg_distances.max()}")

    # Sweep all thresholds
    results = [evaluate_threshold(all_distances, all_labels, t)
               for t in range(MAX_BITS + 1)]

    # Best by accuracy, then by F1 (tie-break)
    best_acc = max(results, key=lambda r: (r["accuracy"], r["f1"]))
    best_f1 = max(results, key=lambda r: (r["f1"], r["accuracy"]))

    # Print sweep table
    print("\n" + "-" * 70)
    print(f"{'Thresh':>6} {'Accuracy':>9} {'Precision':>10} "
          f"{'Recall':>8} {'F1':>8} {'TP':>5} {'TN':>5} {'FP':>5} {'FN':>5}")
    print("-" * 70)
    for r in results:
        marker = ""
        if r["threshold"] == best_acc["threshold"]:
            marker += " <-- best acc"
        if r["threshold"] == best_f1["threshold"] and best_f1["threshold"] != best_acc["threshold"]:
            marker += " <-- best F1"
        print(f"{r['threshold']:>6} {r['accuracy']:>9.4f} {r['precision']:>10.4f} "
              f"{r['recall']:>8.4f} {r['f1']:>8.4f} "
              f"{r['tp']:>5} {r['tn']:>5} {r['fp']:>5} {r['fn']:>5}{marker}")

    # Summary
    print("\n" + "=" * 70)
    print("OPTIMAL THRESHOLD (highest accuracy)")
    print(f"  Threshold : {best_acc['threshold']}")
    print(f"  Accuracy  : {best_acc['accuracy']:.4f} ({best_acc['accuracy']*100:.2f} %)")
    print(f"  Precision : {best_acc['precision']:.4f}")
    print(f"  Recall    : {best_acc['recall']:.4f}")
    print(f"  F1        : {best_acc['f1']:.4f}")
    print(f"  TP={best_acc['tp']}  TN={best_acc['tn']}  FP={best_acc['fp']}  FN={best_acc['fn']}")

    if best_f1["threshold"] != best_acc["threshold"]:
        print("\nOPTIMAL THRESHOLD (highest F1)")
        print(f"  Threshold : {best_f1['threshold']}")
        print(f"  Accuracy  : {best_f1['accuracy']:.4f} ({best_f1['accuracy']*100:.2f} %)")
        print(f"  Precision : {best_f1['precision']:.4f}")
        print(f"  Recall    : {best_f1['recall']:.4f}")
        print(f"  F1        : {best_f1['f1']:.4f}")
        print(f"  TP={best_f1['tp']}  TN={best_f1['tn']}  FP={best_f1['fp']}  FN={best_f1['fn']}")

    # Per-transformation breakdown at best-accuracy threshold
    print("\n" + "=" * 70)
    print(f"PER-TRANSFORMATION BREAKDOWN  (threshold = {best_acc['threshold']})")
    print("-" * 70)
    print(f"{'Transformation':<25} {'Correct':>8} {'Total':>7} "
          f"{'Acc %':>7} {'Mean Dist':>10} {'Max Dist':>9}")
    print("-" * 70)

    transform_stats = per_transform_report(positives, best_acc["threshold"])
    for transform, stats in sorted(transform_stats.items()):
        dists = stats["distances"]
        acc_pct = stats["correct"] / stats["total"] * 100
        mean_d = np.mean(dists)
        max_d = max(dists)
        print(f"{transform:<25} {stats['correct']:>8} {stats['total']:>7} "
              f"{acc_pct:>7.1f} {mean_d:>10.2f} {max_d:>9}")

    total_correct = sum(s["correct"] for s in transform_stats.values())
    total_pairs = sum(s["total"] for s in transform_stats.values())
    print("-" * 70)
    print(f"{'TOTAL':<25} {total_correct:>8} {total_pairs:>7} "
          f"{total_correct/total_pairs*100:>7.1f}")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # Export CSV results
    # -----------------------------------------------------------------------
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Threshold sweep
    sweep_csv = RESULTS_DIR / "hsv_threshold_sweep.csv"
    with open(sweep_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "threshold", "accuracy", "precision", "recall", "f1",
            "tp", "tn", "fp", "fn", "best_accuracy", "best_f1"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                **r,
                "best_accuracy": r["threshold"] == best_acc["threshold"],
                "best_f1": r["threshold"] == best_f1["threshold"],
            })
    print(f"\nThreshold sweep saved to : {sweep_csv}")

    # 2. Per-transformation breakdown at best-accuracy threshold
    transform_csv = RESULTS_DIR / "hsv_per_transform.csv"
    with open(transform_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "transformation", "correct", "total", "accuracy_pct",
            "mean_dist", "max_dist"
        ])
        writer.writeheader()
        for transform, stats in sorted(transform_stats.items()):
            dists = stats["distances"]
            writer.writerow({
                "transformation": transform,
                "correct": stats["correct"],
                "total": stats["total"],
                "accuracy_pct": round(stats["correct"] / stats["total"] * 100, 2),
                "mean_dist": round(float(np.mean(dists)), 4),
                "max_dist": int(max(dists)),
            })
    print(f"Per-transform breakdown saved to : {transform_csv}")

    # 3. Individual pair distances
    pairs_csv = RESULTS_DIR / "hsv_pair_distances.csv"
    with open(pairs_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "image_a", "image_b", "label", "transformation", "hamming_distance"
        ])
        writer.writeheader()
        for (o, v, t), d in zip(positives, pos_distances):
            writer.writerow({"image_a": o, "image_b": v, "label": 1,
                             "transformation": t, "hamming_distance": int(d)})
        for (a, b, t), d in zip(negatives, neg_distances):
            writer.writerow({"image_a": a, "image_b": b, "label": 0,
                             "transformation": t, "hamming_distance": int(d)})
    print(f"Pair distances saved to          : {pairs_csv}")


if __name__ == "__main__":
    main()
