"""
Benchmark cHash: find the Hamming-distance threshold that maximizes accuracy/F1
on the variants.csv dataset.

Run from the hashing/ directory:
    python benchmark_chash.py
"""

import csv
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from algorithms.Chash import CHash


HASH_BITS = 64
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "own"
VARIANTS_CSV = DATA_DIR / "variants.csv"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "benchmark_results"

_hash_cache: dict[str, CHash] = {}

def get_hash(relative_path: str) -> CHash:
    if relative_path not in _hash_cache:
        _hash_cache[relative_path] = CHash(str(DATA_DIR / relative_path))
    return _hash_cache[relative_path]

def load_pairs():
    positives = []
    groups = {}

    with VARIANTS_CSV.open(newline="") as variants_file:
        for row in csv.DictReader(variants_file):
            original = row["original_image"]
            variant = row["variant_image"]
            transformation = row["transformation"]
            positives.append((original, variant, transformation))
            groups.setdefault(original, []).append(variant)

    negatives = []
    for original_a, original_b in combinations(groups.keys(), 2):
        variants_a = groups[original_a]
        variants_b = groups[original_b]

        negatives.append((original_a, original_b, "cross_image"))
        negatives.extend((original_a, variant_b, "cross_image") for variant_b in variants_b)
        negatives.extend((original_b, variant_a, "cross_image") for variant_a in variants_a)

    return positives, negatives


def evaluate_threshold(distances, labels, threshold):
    predictions = (distances <= threshold).astype(int)
    tp = int(((predictions == 1) & (labels == 1)).sum())
    tn = int(((predictions == 0) & (labels == 0)).sum())
    fp = int(((predictions == 1) & (labels == 0)).sum())
    fn = int(((predictions == 0) & (labels == 1)).sum())
    accuracy = (tp + tn) / len(labels)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def print_threshold_table(results, best_accuracy, best_f1):
    print("-" * 78)
    print(
        f"{'Thresh':>6} {'Accuracy':>9} {'Precision':>10} "
        f"{'Recall':>8} {'F1':>8} {'TP':>5} {'TN':>5} {'FP':>5} {'FN':>5}"
    )
    print("-" * 78)

    for result in results:
        marker = ""
        if result["threshold"] == best_accuracy["threshold"]:
            marker += " <-- best acc"
        if (
            result["threshold"] == best_f1["threshold"]
            and best_f1["threshold"] != best_accuracy["threshold"]
        ):
            marker += " <-- best F1"

        print(
            f"{result['threshold']:>6} "
            f"{result['accuracy']:>9.4f} "
            f"{result['precision']:>10.4f} "
            f"{result['recall']:>8.4f} "
            f"{result['f1']:>8.4f} "
            f"{result['tp']:>5} "
            f"{result['tn']:>5} "
            f"{result['fp']:>5} "
            f"{result['fn']:>5}"
            f"{marker}"
        )


def print_summary(title, result):
    print("\n" + "=" * 78)
    print(title)
    print(f"  Threshold : {result['threshold']}")
    print(f"  Accuracy  : {result['accuracy']:.4f} ({result['accuracy'] * 100:.2f} %)")
    print(f"  Precision : {result['precision']:.4f}")
    print(f"  Recall    : {result['recall']:.4f}")
    print(f"  F1        : {result['f1']:.4f}")
    print(f"  TP={result['tp']}  TN={result['tn']}  FP={result['fp']}  FN={result['fn']}")


def per_transform_report(positives, threshold):
    stats = {}
    for orig, variant, transform in positives:
        d = CHash(str(DATA_DIR / orig)).hamming_distance(get_hash(variant))
        if transform not in stats:
            stats[transform] = {"correct": 0, "total": 0, "distances": []}
        stats[transform]["correct"] += int(d <= threshold)
        stats[transform]["total"] += 1
        stats[transform]["distances"].append(d)
    return stats


def main():
    print("=" * 78)
    print("cHash Benchmark - Hamming Threshold Sweep")
    print(f"Dataset: {VARIANTS_CSV}")
    print("=" * 78)

    positives, negatives = load_pairs()
    print(f"\nPositive pairs (same image)  : {len(positives)}")
    print(f"Negative pairs (cross-image) : {len(negatives)}")
    print(f"Total pairs                  : {len(positives) + len(negatives)}")

    print("\nComputing hashes and distances...")
    positive_distances = np.array(
        [CHash(str(DATA_DIR / original)).hamming_distance(get_hash(variant)) for original, variant, _ in positives]
    )
    negative_distances = np.array(
        [CHash(str(DATA_DIR / path_a)).hamming_distance(get_hash(path_b)) for path_a, path_b, _ in negatives]
    )

    distances = np.concatenate([positive_distances, negative_distances])
    labels = np.concatenate(
        [np.ones(len(positive_distances), dtype=int), np.zeros(len(negative_distances), dtype=int)]
    )

    print(
        f"\nPositive distances - mean: {positive_distances.mean():.2f}  "
        f"std: {positive_distances.std():.2f}  "
        f"min: {positive_distances.min()}  max: {positive_distances.max()}"
    )
    print(
        f"Negative distances - mean: {negative_distances.mean():.2f}  "
        f"std: {negative_distances.std():.2f}  "
        f"min: {negative_distances.min()}  max: {negative_distances.max()}"
    )

    results = [evaluate_threshold(distances, labels, threshold) for threshold in range(HASH_BITS + 1)]
    best_accuracy = max(results, key=lambda result: (result["accuracy"], result["f1"]))
    best_f1 = max(results, key=lambda result: (result["f1"], result["accuracy"]))

    print_threshold_table(results, best_accuracy, best_f1)
    print_summary("OPTIMAL THRESHOLD (highest accuracy)", best_accuracy)

    if best_f1["threshold"] != best_accuracy["threshold"]:
        print_summary("OPTIMAL THRESHOLD (highest F1)", best_f1)

    full_recall_threshold = int(positive_distances.max())
    print_summary("FULL-RECALL THRESHOLD (covers every variant)", results[full_recall_threshold])

    print("\n" + "=" * 70)
    print(f"PER-TRANSFORMATION BREAKDOWN  (threshold = {best_accuracy['threshold']})")
    print("-" * 70)
    print(f"{'Transformation':<25} {'Correct':>8} {'Total':>7} "
          f"{'Acc %':>7} {'Mean Dist':>10} {'Max Dist':>9}")
    print("-" * 70)

    transform_stats = per_transform_report(positives, best_accuracy["threshold"])
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

    sweep_csv = RESULTS_DIR / "chash_threshold_sweep.csv"
    with open(sweep_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "threshold", "accuracy", "precision", "recall", "f1",
            "tp", "tn", "fp", "fn", "best_accuracy", "best_f1"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({**r,
                             "best_accuracy": r["threshold"] == best_accuracy["threshold"],
                             "best_f1": r["threshold"] == best_f1["threshold"]})
    print(f"\nThreshold sweep saved to : {sweep_csv}")

    transform_csv = RESULTS_DIR / "chash_per_transform.csv"
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

    pairs_csv = RESULTS_DIR / "chash_pair_distances.csv"
    with open(pairs_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "image_a", "image_b", "label", "transformation", "hamming_distance"
        ])
        writer.writeheader()
        for (o, v, t), d in zip(positives, positive_distances):
            writer.writerow({"image_a": o, "image_b": v, "label": 1,
                             "transformation": t, "hamming_distance": int(d)})
        for (a, b, t), d in zip(negatives, negative_distances):
            writer.writerow({"image_a": a, "image_b": b, "label": 0,
                             "transformation": t, "hamming_distance": int(d)})
    print(f"Pair distances saved to          : {pairs_csv}")


if __name__ == "__main__":
    main()
