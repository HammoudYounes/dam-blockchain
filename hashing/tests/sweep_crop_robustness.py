import csv
import os
import re
import sys
import random
import argparse
import numpy as np
import tqdm
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algorithms.rhash import RadialHash

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "merged")
GROUND_TRUTH_CSV = os.path.join(DATASET_DIR, "filtered_ground_truth.csv")
QUERIES_DIR = os.path.join(DATASET_DIR, "queries")
REFERENCES_DIR = os.path.join(DATASET_DIR, "references")

SOURCE_FILTER = "Own"
QUERY_PATTERN = "cropped"
CROP_LEVEL_RE = re.compile(r"cropped(\d+)")


def load_ground_truth():
    pairs = []
    with open(GROUND_TRUTH_CSV, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append({
                "query": row["query"],
                "reference": row["reference"],
                "source": row["source"],
            })
    return pairs


def crop_level_of(query_filename):
    m = CROP_LEVEL_RE.search(query_filename)
    return int(m.group(1)) if m else None


def build_crop_pairs(all_pairs):
    """Positive pairs: source == 'Own' and query filename contains 'cropped'."""
    crop_pairs = [
        {"query": p["query"], "reference": p["reference"], "label": 1,
         "crop_level": crop_level_of(p["query"])}
        for p in all_pairs
        if p["source"] == SOURCE_FILTER and QUERY_PATTERN in p["query"]
    ]
    return crop_pairs


def build_crop_negatives(crop_pairs, all_pairs, neg_per_pos, seed):
    """
    Negatives: each cropped query paired with a capped random sample of
    OTHER reference images from the 'Own' pool (i.e. wrong-but-plausible
    matches), rather than every other reference (unrealistic imbalance)
    or a random reference from the whole merged corpus (mixes in
    unrelated sources).
    """
    own_references = sorted(set(
        p["reference"] for p in all_pairs if p["source"] == SOURCE_FILTER
    ))
    rng = random.Random(seed)

    negatives = []
    for p in crop_pairs:
        true_ref = p["reference"]
        candidates = [r for r in own_references if r != true_ref]
        sample_size = min(neg_per_pos, len(candidates))
        sampled = rng.sample(candidates, sample_size) if candidates else []
        for ref in sampled:
            negatives.append({
                "query": p["query"],
                "reference": ref,
                "label": 0,
                "crop_level": p["crop_level"],
            })
    return negatives


def compute_best_metrics(results):
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
            if (precision + recall) > 0 else 0.0
        )

        if f1 > best_f1 or (
            abs(f1 - best_f1) < 1e-9 and accuracy > best_metrics.get("accuracy", -1.0)
        ):
            best_f1 = f1
            pos_dists = [r["hamming_distance"] for r in results if r["label"] == 1]
            neg_dists = [r["hamming_distance"] for r in results if r["label"] == 0]
            best_metrics = {
                "threshold": threshold, "accuracy": accuracy, "precision": precision,
                "recall": recall, "f1": f1, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                "mean_dist_pos": np.mean(pos_dists) if pos_dists else float("nan"),
                "mean_dist_neg": np.mean(neg_dists) if neg_dists else float("nan"),
            }

    return best_metrics


def print_top_table(sweep_results, title, top_n=20):
    print(f"\n{title}")
    print("-" * 115)
    print(
        f"{'Multiplier':<12s} | {'Thr':<5s} | {'F1':<8s} | {'Acc':<8s} | "
        f"{'Prec':<8s} | {'Rec':<8s} | {'MeanDpos':<9s} | {'MeanDneg':<9s} | {'TP/TN/FP/FN'}"
    )
    print("-" * 115)
    for res in sweep_results[:top_n]:
        tp, tn, fp, fn = res.get("tp", 0), res.get("tn", 0), res.get("fp", 0), res.get("fn", 0)
        print(
            f"{res['multiplier']:.2f}         | "
            f"{res.get('threshold', 0):<5d} | "
            f"{res.get('f1', 0):.4f}  | "
            f"{res.get('accuracy', 0):.4f}  | "
            f"{res.get('precision', 0):.4f}  | "
            f"{res.get('recall', 0):.4f}  | "
            f"{res.get('mean_dist_pos', 0):<9.2f} | "
            f"{res.get('mean_dist_neg', 0):<9.2f} | "
            f"{tp}/{tn}/{fp}/{fn}"
        )
    print("-" * 115)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--neg-per-pos", type=int, default=10,
                         help="Max wrong-reference negatives sampled per positive pair "
                              "(default: 10, closer to real top-k retrieval scale than 'all')")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for negative sampling")
    parser.add_argument("--min-mult", type=float, default=0.10)
    parser.add_argument("--max-mult", type=float, default=2.00)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    all_pairs = load_ground_truth()
    crop_pairs = build_crop_pairs(all_pairs)
    crop_negatives = build_crop_negatives(crop_pairs, all_pairs, args.neg_per_pos, args.seed)

    print(f"Crop-specific positives: {len(crop_pairs)}")
    print(f"Crop-specific negatives ({args.neg_per_pos} wrong-references sampled per positive): {len(crop_negatives)}")
    if len(crop_pairs) < 15:
        print(
            "WARNING: very small positive set. Treat this curve as indicative; "
            "consider adding more source images with the same crop transforms "
            "before using this as the paper's sole justification.\n"
        )

    levels_present = sorted(set(p["crop_level"] for p in crop_pairs if p["crop_level"] is not None))
    print(f"Crop levels present: {levels_present}")

    multipliers = np.arange(args.min_mult, args.max_mult + args.step / 2, args.step)

    print(f"\nSweeping multiplier from {args.min_mult} to {args.max_mult} "
          f"(aggregate + per-level, crop-only subset)...")
    aggregate_results = []
    per_level_results = {lvl: [] for lvl in levels_present}

    def get_path(filename, is_query):
        base_dir = QUERIES_DIR if is_query else REFERENCES_DIR
        return os.path.join(base_dir, filename)

    for m in tqdm.tqdm(multipliers, desc="Sweeping multipliers"):
        rhash = RadialHash(multiplier=m)

        hash_cache = {}
        all_results = []
        for p in crop_pairs + crop_negatives:
            if p["query"] not in hash_cache:
                path = get_path(p["query"], True)
                if os.path.exists(path):
                    hash_cache[p["query"]] = rhash.compute(path)
            if p["reference"] not in hash_cache:
                path = get_path(p["reference"], False)
                if os.path.exists(path):
                    hash_cache[p["reference"]] = rhash.compute(path)

        for p in crop_pairs + crop_negatives:
            if p["query"] not in hash_cache or p["reference"] not in hash_cache:
                continue
            dist = rhash.hamming_distance(hash_cache[p["query"]], hash_cache[p["reference"]])
            all_results.append({
                "label": p["label"],
                "hamming_distance": dist,
                "crop_level": p.get("crop_level"),
            })

        aggregate_results.append({"multiplier": m, **compute_best_metrics(all_results)})

        for lvl in levels_present:
            level_results = [r for r in all_results if r["label"] == 0 or r["crop_level"] == lvl]
            per_level_results[lvl].append({"multiplier": m, **compute_best_metrics(level_results)})

    aggregate_results.sort(key=lambda x: (x.get("f1", 0), x.get("accuracy", 0), -x.get("multiplier", 0)), reverse=True)
    print_top_table(aggregate_results, "Top multipliers -- AGGREGATE across all crop levels:", args.top_n)
    print(f"\nBest aggregate multiplier: {aggregate_results[0]['multiplier']:.2f} "
          f"with F1 {aggregate_results[0].get('f1', 0):.4f}")

    for lvl in levels_present:
        results = per_level_results[lvl]
        results.sort(key=lambda x: (x.get("f1", 0), x.get("accuracy", 0), -x.get("multiplier", 0)), reverse=True)
        print_top_table(results, f"Top multipliers -- crop level {lvl}% ONLY:", top_n=10)
        print(f"\nBest multiplier at {lvl}% crop: {results[0]['multiplier']:.2f} "
              f"with F1 {results[0].get('f1', 0):.4f}")



if __name__ == "__main__":
    main()