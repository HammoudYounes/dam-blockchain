"""
Benchmark pHash against the 'own' dataset.

Reads variants.csv, computes pHash for each (original, variant) pair,
records Hamming distance and similarity score per transformation type,
and outputs results to benchmark_results/ folder.

Usage (from the hashing/ directory):
    python tests/benchmark_own_phash.py
"""

import csv
import os
import sys
import time
from collections import defaultdict

# Add parent directory to path so we can import phash
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.phash import compute, hamming_distance, similarity

# Paths — relative to the hashing/ directory
DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "own")
VARIANTS_CSV = os.path.join(DATASET_DIR, "variants.csv")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "benchmark_results")


def run_benchmark():
    """Run pHash on every (original, variant) pair in variants.csv."""

    # Create results directory if it doesn't exist
    os.makedirs(RESULTS_DIR, exist_ok=True)

    results = []

    with open(VARIANTS_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_path = os.path.join(DATASET_DIR, row["original_image"])
            variant_path = os.path.join(DATASET_DIR, row["variant_image"])
            transformation = row["transformation"]

            if not os.path.exists(original_path):
                print(f"  [SKIP] Original not found: {original_path}")
                continue
            if not os.path.exists(variant_path):
                print(f"  [SKIP] Variant not found: {variant_path}")
                continue

            hash_original = compute(original_path)
            hash_variant = compute(variant_path)

            dist = hamming_distance(hash_original, hash_variant)
            score = similarity(hash_original, hash_variant)

            original_name = os.path.basename(row["original_image"])
            variant_name = os.path.basename(row["variant_image"])

            results.append({
                "original": original_name,
                "variant": variant_name,
                "transformation": transformation,
                "hamming_distance": dist,
                "similarity_score": round(score, 4),
                "hash_original": hash_original,
                "hash_variant": hash_variant,
            })

            print(f"  {original_name:25s} -> {transformation:25s}  dist={dist:2d}  sim={score:.1%}")

    # Write detailed results CSV
    output_csv = os.path.join(RESULTS_DIR, "own_phash_detailed_results.csv")
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "original", "variant", "transformation",
            "hamming_distance", "similarity_score",
            "hash_original", "hash_variant"
        ])
        writer.writeheader()
        writer.writerows(results)

    return results


def print_summary(results):
    """Group results by transformation and print average distance + score."""
    from collections import defaultdict

    groups = defaultdict(list)
    for r in results:
        groups[r["transformation"]].append(r)

    print("\n" + "=" * 80)
    print(f"{'Transformation':<25s} {'Pairs':>5s} {'Avg Dist':>10s} {'Avg Sim':>10s} {'Min Sim':>10s} {'Max Dist':>10s}")
    print("=" * 80)

    sorted_groups = sorted(
        groups.items(),
        key=lambda x: sum(r["hamming_distance"] for r in x[1]) / len(x[1])
    )

    summary_rows = []
    for transform, group in sorted_groups:
        avg_dist = sum(r["hamming_distance"] for r in group) / len(group)
        avg_sim = sum(r["similarity_score"] for r in group) / len(group)
        min_sim = min(r["similarity_score"] for r in group)
        max_dist = max(r["hamming_distance"] for r in group)

        print(f"{transform:<25s} {len(group):>5d} {avg_dist:>10.1f} {avg_sim:>10.1%} {min_sim:>10.1%} {max_dist:>10d}")

        summary_rows.append({
            "transformation": transform,
            "pairs": len(group),
            "avg_hamming_distance": round(avg_dist, 1),
            "avg_similarity": round(avg_sim, 4),
            "min_similarity": round(min_sim, 4),
            "max_hamming_distance": max_dist,
        })

    print("=" * 80)

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

    # Write summary CSV
    summary_csv = os.path.join(RESULTS_DIR, "own_phash_summary_by_transformation.csv")
    with open(summary_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "transformation", "pairs", "avg_hamming_distance",
            "avg_similarity", "min_similarity", "max_hamming_distance"
        ])
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nSummary saved to: {summary_csv}")


if __name__ == "__main__":
    print("Running pHash benchmark on 'own' dataset...\n")
    start = time.time()
    results = run_benchmark()
    elapsed = time.time() - start
    print_summary(results)
    print(f"\nCompleted in {elapsed:.2f}s")