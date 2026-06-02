"""
Benchmark dHash: find the optimal Hamming-distance threshold that maximises
accuracy on the variants.csv ground-truth dataset.

Usage (from the hashing/ directory):
    python tests/benchmark_own_dhash.py
"""

import csv
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data" / "own"
VARIANTS_CSV = DATA_DIR / "variants.csv"
RESULTS_DIR = SCRIPT_DIR.parent / "benchmark_results"

sys.path.insert(0, str(SCRIPT_DIR.parent))
from algorithms.dhash import compute, hamming_distance

HASH_BITS = 72  # 9×8 horizontal gradients

_hash_cache = {}


def get_hash(rel_path):
    if rel_path not in _hash_cache:
        _hash_cache[rel_path] = compute(str(DATA_DIR / rel_path))
    return _hash_cache[rel_path]


def load_pairs():
    positives = []
    groups = {}

    with open(VARIANTS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            orig = row["original_image"]
            variant = row["variant_image"]
            transform = row["transformation"]
            positives.append((orig, variant, transform))
            groups.setdefault(orig, []).append(variant)

    negatives = []
    for orig_a, orig_b in combinations(groups.keys(), 2):
        negatives.append((orig_a, orig_b, "cross_image"))
        for v in groups[orig_b]:
            negatives.append((orig_a, v, "cross_image"))
        for v in groups[orig_a]:
            negatives.append((orig_b, v, "cross_image"))

    return positives, negatives


def evaluate_threshold(distances, labels, threshold):
    preds = (distances <= threshold).astype(int)
    tp = int(((preds == 1) & (labels == 1)).sum())
    tn = int(((preds == 0) & (labels == 0)).sum())
    fp = int(((preds == 1) & (labels == 0)).sum())
    fn = int(((preds == 0) & (labels == 1)).sum())
    accuracy = (tp + tn) / len(labels)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"threshold": threshold, "accuracy": accuracy,
            "precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "tn": tn, "fp": fp, "fn": fn}


def per_transform_report(positives, threshold):
    stats = {}
    for orig, variant, transform in positives:
        d = hamming_distance(get_hash(orig), get_hash(variant))
        if transform not in stats:
            stats[transform] = {"correct": 0, "total": 0, "distances": []}
        stats[transform]["correct"] += int(d <= threshold)
        stats[transform]["total"] += 1
        stats[transform]["distances"].append(d)
    return stats


def main():
    print("=" * 70)
    print("dHash Benchmark — Hamming Threshold Optimisation")
    print(f"Dataset : {VARIANTS_CSV}")
    print("=" * 70)

    positives, negatives = load_pairs()
    print(f"\nPositive pairs (same image)   : {len(positives)}")
    print(f"Negative pairs (cross-image)  : {len(negatives)}")
    print(f"Total pairs                   : {len(positives) + len(negatives)}")

    print("\nComputing hashes and distances...")
    pos_distances = np.array([hamming_distance(get_hash(o), get_hash(v)) for o, v, _ in positives])
    neg_distances = np.array([hamming_distance(get_hash(a), get_hash(b)) for a, b, _ in negatives])

    all_distances = np.concatenate([pos_distances, neg_distances])
    all_labels = np.concatenate([np.ones(len(positives), dtype=int),
                                  np.zeros(len(negatives), dtype=int)])

    print(f"\nPositive distances — mean: {pos_distances.mean():.2f}  "
          f"std: {pos_distances.std():.2f}  "
          f"min: {pos_distances.min()}  max: {pos_distances.max()}")
    print(f"Negative distances — mean: {neg_distances.mean():.2f}  "
          f"std: {neg_distances.std():.2f}  "
          f"min: {neg_distances.min()}  max: {neg_distances.max()}")

    results = [evaluate_threshold(all_distances, all_labels, t) for t in range(HASH_BITS + 1)]
    best_acc = max(results, key=lambda r: (r["accuracy"], r["f1"]))
    best_f1 = max(results, key=lambda r: (r["f1"], r["accuracy"]))

    print("\n" + "-" * 78)
    print(f"{'Thresh':>6} {'Accuracy':>9} {'Precision':>10} "
          f"{'Recall':>8} {'F1':>8} {'TP':>5} {'TN':>5} {'FP':>5} {'FN':>5}")
    print("-" * 78)
    for r in results:
        marker = ""
        if r["threshold"] == best_acc["threshold"]:
            marker += " <-- best acc"
        if r["threshold"] == best_f1["threshold"] and best_f1["threshold"] != best_acc["threshold"]:
            marker += " <-- best F1"
        print(f"{r['threshold']:>6} {r['accuracy']:>9.4f} {r['precision']:>10.4f} "
              f"{r['recall']:>8.4f} {r['f1']:>8.4f} "
              f"{r['tp']:>5} {r['tn']:>5} {r['fp']:>5} {r['fn']:>5}{marker}")

    print("\n" + "=" * 78)
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

    full_recall_threshold = int(pos_distances.max())
    r = results[full_recall_threshold]
    print("\nFULL-RECALL THRESHOLD (covers every variant)")
    print(f"  Threshold : {r['threshold']}")
    print(f"  Accuracy  : {r['accuracy']:.4f} ({r['accuracy']*100:.2f} %)")
    print(f"  Precision : {r['precision']:.4f}")
    print(f"  Recall    : {r['recall']:.4f}")
    print(f"  F1        : {r['f1']:.4f}")
    print(f"  TP={r['tp']}  TN={r['tn']}  FP={r['fp']}  FN={r['fn']}")

    print("\n" + "=" * 70)
    print(f"PER-TRANSFORMATION BREAKDOWN  (threshold = {best_acc['threshold']})")
    print("-" * 70)
    print(f"{'Transformation':<25} {'Correct':>8} {'Total':>7} "
          f"{'Acc %':>7} {'Mean Dist':>10} {'Max Dist':>9}")
    print("-" * 70)

    transform_stats = per_transform_report(positives, best_acc["threshold"])
    for transform, stats in sorted(transform_stats.items()):
        dists = stats["distances"]
        print(f"{transform:<25} {stats['correct']:>8} {stats['total']:>7} "
              f"{stats['correct']/stats['total']*100:>7.1f} {np.mean(dists):>10.2f} {max(dists):>9}")

    total_correct = sum(s["correct"] for s in transform_stats.values())
    total_pairs = sum(s["total"] for s in transform_stats.values())
    print("-" * 70)
    print(f"{'TOTAL':<25} {total_correct:>8} {total_pairs:>7} "
          f"{total_correct/total_pairs*100:>7.1f}")
    print("=" * 70)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    sweep_csv = RESULTS_DIR / "dhash_threshold_sweep.csv"
    with open(sweep_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "threshold", "accuracy", "precision", "recall", "f1",
            "tp", "tn", "fp", "fn", "best_accuracy", "best_f1"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({**r,
                             "best_accuracy": r["threshold"] == best_acc["threshold"],
                             "best_f1": r["threshold"] == best_f1["threshold"]})
    print(f"\nThreshold sweep saved to : {sweep_csv}")

    transform_csv = RESULTS_DIR / "dhash_per_transform.csv"
    with open(transform_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "transformation", "correct", "total", "accuracy_pct", "mean_dist", "max_dist"
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

    pairs_csv = RESULTS_DIR / "dhash_pair_distances.csv"
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
