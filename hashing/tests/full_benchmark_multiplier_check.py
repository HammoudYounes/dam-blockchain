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

# Ordered (specific-before-general) filename -> category rules.
# First match wins, so e.g. "resized_up" is checked before "resized".
CATEGORY_RULES = [
    (re.compile(r"cropped10"), "crop_10"),
    (re.compile(r"cropped20"), "crop_20"),
    (re.compile(r"cropped30"), "crop_30"),
    (re.compile(r"quality_adjusted_80"), "jpeg_q80"),
    (re.compile(r"quality_adjusted_50"), "jpeg_q50"),
    (re.compile(r"quality_adjusted_20"), "jpeg_q20"),
    (re.compile(r"resized_up"), "resize_up"),
    (re.compile(r"resized"), "resize_down"),
    (re.compile(r"altered"), "pixel_alter"),
    (re.compile(r"grayscale"), "grayscale"),
    (re.compile(r"covered"), "occlusion"),
    (re.compile(r"dropout"), "grid_dropout"),
    (re.compile(r"blurred"), "blur"),
    (re.compile(r"brightened"), "brightness_up"),
    (re.compile(r"darkened"), "brightness_down"),
    (re.compile(r"contrasted"), "contrast"),
    (re.compile(r"filtered"), "edge_filter"),
    (re.compile(r"channel_shifted"), "channel_shift"),
]


def categorize(query_filename):
    for pattern, label in CATEGORY_RULES:
        if pattern.search(query_filename):
            return label
    return None  # unrecognized filename -- reported separately, not silently dropped


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


def build_positive_pairs(all_pairs):
    positives = []
    uncategorized = 0
    for p in all_pairs:
        if p["source"] != SOURCE_FILTER:
            continue
        cat = categorize(p["query"])
        if cat is None:
            uncategorized += 1
            continue
        positives.append({"query": p["query"], "reference": p["reference"],
                           "label": 1, "category": cat})
    if uncategorized:
        print(f"NOTE: {uncategorized} 'Own' rows didn't match any known category "
              f"pattern -- check CATEGORY_RULES against your actual filenames "
              f"if this number is large.")
    return positives


def build_negatives(positives, all_pairs, neg_per_pos, seed):
    own_references = sorted(set(
        p["reference"] for p in all_pairs if p["source"] == SOURCE_FILTER
    ))
    rng = random.Random(seed)
    negatives = []
    for p in positives:
        true_ref = p["reference"]
        candidates = [r for r in own_references if r != true_ref]
        sample_size = min(neg_per_pos, len(candidates))
        sampled = rng.sample(candidates, sample_size) if candidates else []
        for ref in sampled:
            negatives.append({"query": p["query"], "reference": ref,
                               "label": 0, "category": p["category"]})
    return negatives


def get_path(filename, is_query):
    base_dir = QUERIES_DIR if is_query else REFERENCES_DIR
    return os.path.join(base_dir, filename)


def compute_distances(multiplier, positives, negatives):
    rhash = RadialHash(multiplier=multiplier)
    hash_cache = {}
    results = []
    for p in positives + negatives:
        if p["query"] not in hash_cache:
            path = get_path(p["query"], True)
            if os.path.exists(path):
                hash_cache[p["query"]] = rhash.compute(path)
        if p["reference"] not in hash_cache:
            path = get_path(p["reference"], False)
            if os.path.exists(path):
                hash_cache[p["reference"]] = rhash.compute(path)
        if p["query"] not in hash_cache or p["reference"] not in hash_cache:
            continue
        dist = rhash.hamming_distance(hash_cache[p["query"]], hash_cache[p["reference"]])
        results.append({"label": p["label"], "hamming_distance": dist, "category": p["category"]})
    return results


def best_threshold_and_f1(results):
    best_f1, best_thr, best_metrics = -1.0, 0, {}
    total = len(results)
    for threshold in range(65):
        tp = sum(1 for r in results if r["label"] == 1 and r["hamming_distance"] <= threshold)
        tn = sum(1 for r in results if r["label"] == 0 and r["hamming_distance"] > threshold)
        fp = sum(1 for r in results if r["label"] == 0 and r["hamming_distance"] <= threshold)
        fn = sum(1 for r in results if r["label"] == 1 and r["hamming_distance"] > threshold)
        accuracy = (tp + tn) / total if total else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        if f1 > best_f1:
            best_f1, best_thr = f1, threshold
            best_metrics = {"threshold": threshold, "accuracy": accuracy,
                             "precision": precision, "recall": recall, "f1": f1,
                             "tp": tp, "tn": tn, "fp": fp, "fn": fn}
    return best_thr, best_metrics


def per_category_accuracy(results, threshold):
    """For SIMILAR (label==1) pairs only: fraction correctly matched (dist <= threshold)."""
    cats = sorted(set(r["category"] for r in results if r["label"] == 1))
    out = {}
    for cat in cats:
        cat_results = [r for r in results if r["label"] == 1 and r["category"] == cat]
        n = len(cat_results)
        correct = sum(1 for r in cat_results if r["hamming_distance"] <= threshold)
        mean_dist = np.mean([r["hamming_distance"] for r in cat_results]) if n else float("nan")
        out[cat] = {"n": n, "accuracy": correct / n if n else float("nan"), "mean_dist": mean_dist}
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--multipliers", nargs="+", type=float,
                         default=[0.92, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30],
                         help="Candidate multipliers to evaluate (default: %(default)s)")
    parser.add_argument("--neg-per-pos", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    all_pairs = load_ground_truth()
    positives = build_positive_pairs(all_pairs)
    negatives = build_negatives(positives, all_pairs, args.neg_per_pos, args.seed)

    categories = sorted(set(p["category"] for p in positives))
    print(f"Positives: {len(positives)} across {len(categories)} categories: {categories}")
    print(f"Negatives: {len(negatives)} ({args.neg_per_pos} per positive)\n")

    per_multiplier_summary = []
    per_multiplier_categories = {}

    for m in tqdm.tqdm(args.multipliers, desc="Evaluating candidate multipliers"):
        results = compute_distances(m, positives, negatives)
        threshold, metrics = best_threshold_and_f1(results)
        cat_acc = per_category_accuracy(results, threshold)
        per_multiplier_summary.append({"multiplier": m, "threshold": threshold, **metrics})
        per_multiplier_categories[m] = cat_acc

    print("\nAggregate summary (best threshold per multiplier, full 18-category benchmark):")
    print("-" * 80)
    print(f"{'Multiplier':<12s} | {'Thr':<5s} | {'F1':<8s} | {'Acc':<8s} | {'Prec':<8s} | {'Rec':<8s}")
    print("-" * 80)
    for res in per_multiplier_summary:
        print(f"{res['multiplier']:<12.2f} | {res['threshold']:<5d} | "
              f"{res['f1']:<8.4f} | {res['accuracy']:<8.4f} | "
              f"{res['precision']:<8.4f} | {res['recall']:<8.4f}")
    print("-" * 80)

    print("\nPer-category accuracy at each multiplier's best threshold:")
    header = f"{'Category':<16s}" + "".join(f"| {m:<8.2f}" for m in args.multipliers)
    print(header)
    print("-" * len(header))
    for cat in categories:
        row = f"{cat:<16s}"
        for m in args.multipliers:
            acc = per_multiplier_categories[m].get(cat, {}).get("accuracy", float("nan"))
            row += f"| {acc:<8.2%}" if acc == acc else f"| {'--':<8s}"
        print(row)

if __name__ == "__main__":
    main()
