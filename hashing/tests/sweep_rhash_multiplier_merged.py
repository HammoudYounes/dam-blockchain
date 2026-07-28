import csv
import os
import sys
import numpy as np
from collections import defaultdict
import tqdm
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.rhash import RadialHash

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "merged")
GROUND_TRUTH_CSV = os.path.join(DATASET_DIR, "filtered_ground_truth.csv")
QUERIES_DIR = os.path.join(DATASET_DIR, "queries")
REFERENCES_DIR = os.path.join(DATASET_DIR, "references")

def load_ground_truth():
    pairs = []
    with open(GROUND_TRUTH_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append({
                "query": row["query"],
                "reference": row["reference"],
                "label": 1  # From ground truth, these are pairs
            })
    return pairs

def build_different_pairs(ground_truth_pairs, num_negatives=5):
    # This is a simplified approach for building negatives on the merged dataset
    # We create random mismatches
    import random

    references = list(set(p["reference"] for p in ground_truth_pairs))
    queries = list(set(p["query"] for p in ground_truth_pairs))

    different_pairs = []

    # Simple strategy: pair queries with random references that aren't the ground truth reference
    # Need to know the actual ground truth for efficient negative sampling
    ground_truth_map = defaultdict(set)
    for p in ground_truth_pairs:
        ground_truth_map[p["query"]].add(p["reference"])

    for q in queries:
        attempts = 0
        while attempts < num_negatives:
            ref = random.choice(references)
            if ref not in ground_truth_map[q]:
                different_pairs.append({
                    "query": q,
                    "reference": ref,
                    "label": 0
                })
                attempts += 1

    return different_pairs

def evaluate_multiplier(multiplier, similar_pairs, different_pairs):
    rhash = RadialHash(multiplier=multiplier)

    # Need helper to resolve paths
    def get_path(filename, is_query):
        base_dir = QUERIES_DIR if is_query else REFERENCES_DIR
        return os.path.join(base_dir, filename)

    # Collect unique image paths
    hash_cache = {}

    # Precompute hashes for all involved images
    for p in similar_pairs + different_pairs:
        # Query
        if p["query"] not in hash_cache:
            path = get_path(p["query"], True)
            if os.path.exists(path):
                hash_cache[p["query"]] = rhash.compute(path)
        # Reference
        if p["reference"] not in hash_cache:
            path = get_path(p["reference"], False)
            if os.path.exists(path):
                hash_cache[p["reference"]] = rhash.compute(path)

    # Compute distances
    results = []
    for p in similar_pairs + different_pairs:
        if p["query"] not in hash_cache or p["reference"] not in hash_cache:
            continue
        dist = rhash.hamming_distance(hash_cache[p["query"]], hash_cache[p["reference"]])
        results.append({
            "label": p["label"],
            "hamming_distance": dist
        })

    total = len(results)
    if total == 0:
        return {"f1": 0}

    best_f1 = -1.0
    best_metrics = {}

    for threshold in range(65):
        tp = sum(1 for r in results if r["label"] == 1 and r["hamming_distance"] <= threshold)
        tn = sum(1 for r in results if r["label"] == 0 and r["hamming_distance"] > threshold)
        fp = sum(1 for r in results if r["label"] == 0 and r["hamming_distance"] <= threshold)
        fn = sum(1 for r in results if r["label"] == 1 and r["hamming_distance"] > threshold)

        accuracy = (tp + tn) / total if total > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        if f1 > best_f1 or (
            abs(f1 - best_f1) < 1e-9
            and accuracy > best_metrics.get("accuracy", -1.0)
        ):
            best_f1 = f1
            best_metrics = {
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

    return best_metrics

if __name__ == "__main__":
    similar_pairs = load_ground_truth()
    different_pairs = build_different_pairs(similar_pairs)

    print(f"Loaded {len(similar_pairs)} similar pairs and {len(different_pairs)} negative pairs.")
    print("Sweeping multiplier from 0.10 to 2.00...")

    sweep_results = []
    for m in tqdm.tqdm(np.arange(0.10, 2.01, 0.01), desc="Sweeping multipliers"):
        metrics = evaluate_multiplier(m, similar_pairs, different_pairs)
        sweep_results.append({
            "multiplier": m,
            **metrics
        })

    sweep_results.sort(
        key=lambda x: (
            x.get("f1", 0),
            x.get("accuracy", 0),
            -x.get("multiplier", 0),
        ),
        reverse=True,
    )

    print("\nTop 20 Multipliers by F1 Score and Accuracy:")
    print("-" * 105)
    print(
        f"{'Multiplier':<12s} | {'Threshold':<10s} | {'F1 Score':<10s} | "
        f"{'Accuracy':<10s} | {'Precision':<10s} | {'Recall':<10s} | "
        f"{'TP/TN/FP/FN':<15s}"
    )
    print("-" * 105)

    for res in sweep_results[:20]:
        tp, tn, fp, fn = (
            res.get("tp", 0),
            res.get("tn", 0),
            res.get("fp", 0),
            res.get("fn", 0),
        )
        print(
            f"{res['multiplier']:.2f}         | "
            f"{res.get('threshold', 0):<10d} | "
            f"{res.get('f1', 0):.4f}   | "
            f"{res.get('accuracy', 0):.4f}   | "
            f"{res.get('precision', 0):.4f}    | "
            f"{res.get('recall', 0):.4f} | "
            f"{tp}/{tn}/{fp}/{fn}"
        )

    print("-" * 105)

    best_m = sweep_results[0]["multiplier"]
    print(
        f"\nBest multiplier: {best_m:.2f} "
        f"with F1 score {sweep_results[0].get('f1', 0):.4f}"
    )