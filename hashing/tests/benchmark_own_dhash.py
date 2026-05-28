"""
Quick benchmark: dHash against the 'own' dataset.

Usage (from the hashing/ directory):
    python tests/benchmark_own_dhash.py
"""

import csv
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.dhash import compute, hamming_distance, similarity

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "own")
VARIANTS_CSV = os.path.join(DATASET_DIR, "variants.csv")


def run_benchmark():
    results = []

    with open(VARIANTS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_path = os.path.join(DATASET_DIR, row["original_image"])
            variant_path = os.path.join(DATASET_DIR, row["variant_image"])
            transformation = row["transformation"]

            if not os.path.exists(original_path) or not os.path.exists(variant_path):
                continue

            hash_original = compute(original_path)
            hash_variant = compute(variant_path)

            dist = hamming_distance(hash_original, hash_variant)
            score = similarity(hash_original, hash_variant)

            original_name = os.path.basename(row["original_image"])

            results.append({
                "original": original_name,
                "transformation": transformation,
                "hamming_distance": dist,
                "similarity_score": round(score, 4),
            })

            print(f"  {original_name:25s} -> {transformation:25s}  dist={dist:2d}  sim={score:.1%}")

    return results


def print_summary(results):
    groups = defaultdict(list)
    for r in results:
        groups[r["transformation"]].append(r)

    print("\n" + "=" * 75)
    print(f"{'Transformation':<25s} {'Pairs':>5s} {'Avg Dist':>10s} {'Avg Sim':>10s} {'Min Sim':>10s} {'Max Dist':>10s}")
    print("=" * 75)

    for transform, group in sorted(
        groups.items(),
        key=lambda x: sum(r["hamming_distance"] for r in x[1]) / len(x[1])
    ):
        avg_dist = sum(r["hamming_distance"] for r in group) / len(group)
        avg_sim = sum(r["similarity_score"] for r in group) / len(group)
        min_sim = min(r["similarity_score"] for r in group)
        max_dist = max(r["hamming_distance"] for r in group)

        print(f"{transform:<25s} {len(group):>5d} {avg_dist:>10.1f} {avg_sim:>10.1%} {min_sim:>10.1%} {max_dist:>10d}")

    print("=" * 75)

    # Overall stats
    all_dists = [r["hamming_distance"] for r in results]
    all_sims = [r["similarity_score"] for r in results]
    print(f"\nTotal pairs: {len(results)}")
    print(f"Overall avg Hamming distance: {sum(all_dists)/len(all_dists):.1f}")
    print(f"Overall avg similarity: {sum(all_sims)/len(all_sims):.1%}")
    print(f"Worst case: dist={max(all_dists)}, sim={min(all_sims):.1%}")

    # Threshold analysis
    print("\n--- Threshold Analysis ---")
    for threshold in [5, 8, 10, 12, 15, 20, 25]:
        correct = sum(1 for d in all_dists if d <= threshold)
        print(f"  Threshold {threshold:>2d}: {correct}/{len(all_dists)} pairs declared SIMILAR ({correct/len(all_dists):.1%})")


if __name__ == "__main__":
    print("Running dHash benchmark on 'own' dataset...\n")
    start = time.time()
    results = run_benchmark()
    elapsed = time.time() - start
    print_summary(results)
    print(f"\nCompleted in {elapsed:.2f}s")